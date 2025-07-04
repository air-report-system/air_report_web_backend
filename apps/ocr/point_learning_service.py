"""
点位学习和智能判断服务
"""
import logging
from typing import Dict, List, Tuple, Optional, Any
from django.db import transaction
from django.utils import timezone
from .models import PointLearning, PointValue, OCRResult

logger = logging.getLogger(__name__)


class PointLearningService:
    """点位学习服务"""
    
    DEFAULT_THRESHOLD = 0.080
    DEFAULT_POINTS = [
        "客厅", "主卧", "次卧", "次卧1", "次卧2", 
        "儿童房", "书房", "衣帽间", "厨房", "餐厅"
    ]
    
    @classmethod
    def infer_check_type_from_points(
        cls, 
        points_data: Dict[str, float], 
        threshold: float = DEFAULT_THRESHOLD
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        根据点位值推断检测类型
        
        Args:
            points_data: 点位数据字典 {'点位名称': 检测值}
            threshold: 判断阈值，默认0.080
            
        Returns:
            Tuple[检测类型, 置信度, 统计信息]
        """
        if not points_data:
            logger.warning("没有点位数据，默认为初检")
            return 'initial', 0.0, {
                'high_count': 0,
                'low_count': 0,
                'threshold': threshold,
                'total_points': 0,
                'valid_values': []
            }
        
        # 收集有效的点位值
        valid_values = []
        high_count = 0
        low_count = 0
        
        for point_name, point_value in points_data.items():
            try:
                value = float(point_value)
                valid_values.append(value)
                
                if value > threshold:
                    high_count += 1
                else:
                    low_count += 1
                    
                logger.debug(f"有效点位: {point_name} = {value}")
            except (ValueError, TypeError):
                logger.warning(f"无效点位值: {point_name} = {point_value}")
                continue
        
        # 如果没有有效值，默认为初检
        if not valid_values:
            logger.warning("没有找到有效的点位值，默认为初检")
            return 'initial', 0.0, {
                'high_count': 0,
                'low_count': 0,
                'threshold': threshold,
                'total_points': 0,
                'valid_values': []
            }
        
        # 根据众数判断初检/复检
        total_count = high_count + low_count
        if high_count > low_count:
            check_type = 'initial'
            confidence = high_count / total_count
            logger.info(f"大于{threshold}的点位更多({high_count} > {low_count})，判断为: 初检")
        elif low_count > high_count:
            check_type = 'recheck'
            confidence = low_count / total_count
            logger.info(f"小于等于{threshold}的点位更多({low_count} > {high_count})，判断为: 复检")
        else:
            check_type = 'initial'  # 数量相等时默认为初检
            confidence = 0.5
            logger.info(f"两类点位数量相等({high_count} = {low_count})，默认判断为: 初检")
        
        statistics = {
            'high_count': high_count,
            'low_count': low_count,
            'threshold': threshold,
            'total_points': len(valid_values),
            'valid_values': valid_values,
            'avg_value': sum(valid_values) / len(valid_values),
            'max_value': max(valid_values),
            'min_value': min(valid_values)
        }
        
        return check_type, confidence, statistics
    
    @classmethod
    def update_point_learning(
        cls, 
        points_data: Dict[str, float], 
        check_type: str = 'initial',
        ocr_result: Optional[OCRResult] = None
    ) -> Dict[str, Any]:
        """
        更新点位学习数据
        
        Args:
            points_data: 点位数据字典
            check_type: 检测类型
            ocr_result: OCR结果对象（可选）
            
        Returns:
            更新结果统计
        """
        if not points_data:
            return {'updated_count': 0, 'created_count': 0, 'error': '点位数据为空'}
        
        updated_count = 0
        created_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for point_name, value in points_data.items():
                    try:
                        float_value = float(value)
                        
                        # 更新或创建点位学习记录
                        point_learning, created = PointLearning.objects.get_or_create(
                            point_name=point_name.strip(),
                            defaults={
                                'usage_count': 0,
                                'total_value': 0.0,
                                'avg_value': 0.0,
                                'initial_count': 0,
                                'recheck_count': 0,
                            }
                        )
                        
                        # 更新统计信息
                        point_learning.update_statistics(float_value, check_type)
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                        
                        # 如果有OCR结果，创建点位值记录（不重复更新学习统计）
                        if ocr_result:
                            PointValue.objects.create(
                                ocr_result=ocr_result,
                                point_name=point_name.strip(),
                                value=float_value,
                                check_type=check_type,
                                update_learning=False  # 避免重复更新
                            )
                        
                        logger.debug(f"更新点位学习: {point_name} = {float_value} ({check_type})")
                        
                    except (ValueError, TypeError) as e:
                        error_msg = f"无效点位值: {point_name} = {value}, 错误: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                        
        except Exception as e:
            logger.error(f"更新点位学习数据失败: {str(e)}")
            return {
                'updated_count': 0,
                'created_count': 0,
                'error': f'更新失败: {str(e)}'
            }
        
        result = {
            'updated_count': updated_count,
            'created_count': created_count,
            'total_processed': updated_count + created_count,
            'errors': errors
        }
        
        logger.info(f"点位学习更新完成: {result}")
        return result
    
    @classmethod
    def get_point_suggestions(
        cls, 
        existing_points: List[str] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取点位建议
        
        Args:
            existing_points: 已存在的点位列表
            limit: 返回数量限制
            
        Returns:
            建议点位列表
        """
        existing_points = existing_points or []
        
        # 从学习数据中获取建议
        learned_suggestions = PointLearning.objects.exclude(
            point_name__in=existing_points
        ).order_by('-usage_count', '-last_used_at')[:limit]
        
        suggestions = []
        for point in learned_suggestions:
            suggestions.append({
                'point_name': point.point_name,
                'usage_count': point.usage_count,
                'avg_value': point.avg_value,
                'confidence': min(point.usage_count / 10.0, 1.0),  # 基于使用次数的置信度
                'source': 'learned'
            })
        
        # 如果学习数据不足，补充默认点位
        if len(suggestions) < limit:
            remaining_limit = limit - len(suggestions)
            existing_names = existing_points + [s['point_name'] for s in suggestions]
            
            default_suggestions = [
                point for point in cls.DEFAULT_POINTS 
                if point not in existing_names
            ][:remaining_limit]
            
            for point in default_suggestions:
                suggestions.append({
                    'point_name': point,
                    'usage_count': 0,
                    'avg_value': 0.0,
                    'confidence': 0.3,  # 默认点位的置信度较低
                    'source': 'default'
                })
        
        return suggestions[:limit]
    
    @classmethod
    def get_point_statistics(cls) -> Dict[str, Any]:
        """获取点位统计信息"""
        total_points = PointLearning.objects.count()
        from django.db import models
        total_usage = PointLearning.objects.aggregate(
            total=models.Sum('usage_count')
        )['total'] or 0
        
        # 获取最常用的点位
        popular_points = PointLearning.objects.order_by('-usage_count')[:10]
        
        # 获取最近使用的点位
        recent_points = PointLearning.objects.order_by('-last_used_at')[:10]
        
        return {
            'total_points': total_points,
            'total_usage': total_usage,
            'avg_usage_per_point': total_usage / total_points if total_points > 0 else 0,
            'popular_points': [
                {
                    'name': p.point_name,
                    'usage_count': p.usage_count,
                    'avg_value': p.avg_value
                } for p in popular_points
            ],
            'recent_points': [
                {
                    'name': p.point_name,
                    'last_used_at': p.last_used_at,
                    'usage_count': p.usage_count
                } for p in recent_points
            ]
        }
