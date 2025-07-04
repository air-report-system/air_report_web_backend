"""
数据同步和持久化服务
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import PointLearning, PointValue, OCRResult
from .point_learning_service import PointLearningService

logger = logging.getLogger(__name__)


class DataSyncService:
    """数据同步服务"""
    
    def __init__(self):
        self.data_dir = Path(settings.BASE_DIR) / 'data'
        self.data_dir.mkdir(exist_ok=True)
        self.point_memory_file = self.data_dir / 'point_memory.json'
        self.learned_points_file = self.data_dir / 'learned_points.txt'
    
    def sync_from_gui_data(self) -> Dict[str, Any]:
        """
        从GUI版本的数据文件同步点位学习数据
        
        Returns:
            同步结果统计
        """
        result = {
            'synced_from_json': 0,
            'synced_from_txt': 0,
            'errors': [],
            'total_synced': 0
        }
        
        try:
            # 同步JSON格式的点位记忆数据
            if self.point_memory_file.exists():
                json_result = self._sync_from_point_memory_json()
                result['synced_from_json'] = json_result['synced_count']
                result['errors'].extend(json_result.get('errors', []))
            
            # 同步TXT格式的学习点位数据
            if self.learned_points_file.exists():
                txt_result = self._sync_from_learned_points_txt()
                result['synced_from_txt'] = txt_result['synced_count']
                result['errors'].extend(txt_result.get('errors', []))
            
            result['total_synced'] = result['synced_from_json'] + result['synced_from_txt']
            
            logger.info(f"数据同步完成: {result}")
            return result
            
        except Exception as e:
            error_msg = f"数据同步失败: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
    
    def _sync_from_point_memory_json(self) -> Dict[str, Any]:
        """从point_memory.json同步数据"""
        synced_count = 0
        errors = []
        
        try:
            with open(self.point_memory_file, 'r', encoding='utf-8') as f:
                point_data = json.load(f)
            
            with transaction.atomic():
                for point_name, data in point_data.items():
                    try:
                        count = data.get('count', 1)
                        values = data.get('values', [])
                        avg_value = data.get('avg_value', 0.0)
                        
                        # 创建或更新点位学习记录
                        point_learning, created = PointLearning.objects.get_or_create(
                            point_name=point_name,
                            defaults={
                                'usage_count': count,
                                'total_value': avg_value * count,
                                'avg_value': avg_value,
                                'initial_count': count,  # 假设都是初检
                                'recheck_count': 0,
                            }
                        )
                        
                        if not created:
                            # 更新现有记录
                            point_learning.usage_count = max(point_learning.usage_count, count)
                            point_learning.total_value = avg_value * point_learning.usage_count
                            point_learning.avg_value = avg_value
                            point_learning.save()
                        
                        synced_count += 1
                        logger.debug(f"同步点位数据: {point_name} = {avg_value} (使用{count}次)")
                        
                    except Exception as e:
                        error_msg = f"同步点位{point_name}失败: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                        
        except Exception as e:
            error_msg = f"读取point_memory.json失败: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return {'synced_count': synced_count, 'errors': errors}
    
    def _sync_from_learned_points_txt(self) -> Dict[str, Any]:
        """从learned_points.txt同步数据"""
        synced_count = 0
        errors = []
        
        try:
            with open(self.learned_points_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with transaction.atomic():
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        if ',' in line:
                            point_name, count_str = line.split(',', 1)
                            count = int(count_str.strip())
                        else:
                            point_name = line
                            count = 1
                        
                        point_name = point_name.strip()
                        if not point_name:
                            continue
                        
                        # 创建或更新点位学习记录
                        point_learning, created = PointLearning.objects.get_or_create(
                            point_name=point_name,
                            defaults={
                                'usage_count': count,
                                'total_value': 0.0,
                                'avg_value': 0.0,
                                'initial_count': count,
                                'recheck_count': 0,
                            }
                        )
                        
                        if not created:
                            # 更新使用次数（取最大值）
                            point_learning.usage_count = max(point_learning.usage_count, count)
                            point_learning.save()
                        
                        synced_count += 1
                        logger.debug(f"同步学习点位: {point_name} (使用{count}次)")
                        
                    except Exception as e:
                        error_msg = f"解析行'{line}'失败: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                        
        except Exception as e:
            error_msg = f"读取learned_points.txt失败: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return {'synced_count': synced_count, 'errors': errors}
    
    def export_to_gui_format(self) -> Dict[str, Any]:
        """
        导出数据为GUI版本兼容的格式
        
        Returns:
            导出结果
        """
        result = {
            'exported_json': False,
            'exported_txt': False,
            'point_count': 0,
            'errors': []
        }
        
        try:
            # 导出为JSON格式
            json_result = self._export_to_point_memory_json()
            result['exported_json'] = json_result['success']
            result['point_count'] = json_result['point_count']
            result['errors'].extend(json_result.get('errors', []))
            
            # 导出为TXT格式
            txt_result = self._export_to_learned_points_txt()
            result['exported_txt'] = txt_result['success']
            result['errors'].extend(txt_result.get('errors', []))
            
            logger.info(f"数据导出完成: {result}")
            return result
            
        except Exception as e:
            error_msg = f"数据导出失败: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
    
    def _export_to_point_memory_json(self) -> Dict[str, Any]:
        """导出为point_memory.json格式"""
        try:
            point_data = {}
            points = PointLearning.objects.all()
            
            for point in points:
                point_data[point.point_name] = {
                    'count': point.usage_count,
                    'values': [point.avg_value] * point.usage_count,  # 简化处理
                    'avg_value': point.avg_value
                }
            
            with open(self.point_memory_file, 'w', encoding='utf-8') as f:
                json.dump(point_data, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'point_count': len(point_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'point_count': 0,
                'errors': [f"导出JSON失败: {str(e)}"]
            }
    
    def _export_to_learned_points_txt(self) -> Dict[str, Any]:
        """导出为learned_points.txt格式"""
        try:
            points = PointLearning.objects.order_by('-usage_count', 'point_name')
            
            with open(self.learned_points_file, 'w', encoding='utf-8') as f:
                for point in points:
                    f.write(f"{point.point_name},{point.usage_count}\n")
            
            return {
                'success': True,
                'point_count': points.count()
            }
            
        except Exception as e:
            return {
                'success': False,
                'point_count': 0,
                'errors': [f"导出TXT失败: {str(e)}"]
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'database_points': PointLearning.objects.count(),
            'database_values': PointValue.objects.count(),
            'json_file_exists': self.point_memory_file.exists(),
            'txt_file_exists': self.learned_points_file.exists(),
            'json_file_size': self.point_memory_file.stat().st_size if self.point_memory_file.exists() else 0,
            'txt_file_size': self.learned_points_file.stat().st_size if self.learned_points_file.exists() else 0,
            'last_sync_time': timezone.now().isoformat(),
        }
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, Any]:
        """清理旧数据"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # 清理旧的点位值记录
        old_values = PointValue.objects.filter(created_at__lt=cutoff_date)
        deleted_values = old_values.count()
        old_values.delete()
        
        # 清理未使用的点位学习记录
        unused_points = PointLearning.objects.filter(
            usage_count=0,
            created_at__lt=cutoff_date
        )
        deleted_points = unused_points.count()
        unused_points.delete()
        
        return {
            'deleted_values': deleted_values,
            'deleted_points': deleted_points,
            'cutoff_date': cutoff_date.isoformat()
        }


def get_data_sync_service() -> DataSyncService:
    """获取数据同步服务实例"""
    return DataSyncService()
