"""
批量处理服务 - 移植自GUI项目的batch_image_process_dialog.py
"""
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import BatchJob, BatchFileItem
from apps.files.models import UploadedFile

logger = logging.getLogger(__name__)


class BatchProcessingService:
    """批量处理服务 - 移植自GUI项目功能"""
    
    def __init__(self):
        self.processing_delay = 1  # 处理间隔（秒）
        self.max_concurrent_tasks = getattr(settings, 'BATCH_MAX_CONCURRENT_TASKS', 5)
    
    def create_batch_job(self, name: str, file_paths: List[str], settings: Dict[str, Any], user_id: int) -> BatchJob:
        """
        创建批量处理任务
        
        Args:
            name: 任务名称
            file_paths: 文件路径列表
            settings: 处理设置
            user_id: 用户ID
            
        Returns:
            BatchJob: 创建的批量任务
        """
        try:
            with transaction.atomic():
                # 创建批量任务
                batch_job = BatchJob.objects.create(
                    name=name,
                    total_files=len(file_paths),
                    settings=settings,
                    created_by_id=user_id
                )
                
                # 创建文件项
                file_items = []
                for i, file_path in enumerate(file_paths):
                    # 查找或创建上传文件记录
                    uploaded_file = self._get_or_create_uploaded_file(file_path, user_id)
                    
                    file_item = BatchFileItem(
                        batch_job=batch_job,
                        file=uploaded_file,
                        processing_order=i,
                        created_by_id=user_id
                    )
                    file_items.append(file_item)
                
                BatchFileItem.objects.bulk_create(file_items)
                
                logger.info(f"创建批量任务 {batch_job.id}，包含 {len(file_items)} 个文件")
                return batch_job
                
        except Exception as e:
            logger.error(f"创建批量任务失败: {e}")
            raise e
    
    def _get_or_create_uploaded_file(self, file_path: str, user_id: int) -> UploadedFile:
        """获取或创建上传文件记录"""
        file_path_obj = Path(file_path)
        
        # 尝试查找现有文件
        existing_file = UploadedFile.objects.filter(
            original_name=file_path_obj.name,
            created_by_id=user_id
        ).first()
        
        if existing_file:
            return existing_file
        
        # 创建新的文件记录
        uploaded_file = UploadedFile.objects.create(
            original_name=file_path_obj.name,
            file_size=file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            file_type='image',
            created_by_id=user_id
        )
        
        # 复制文件到媒体目录
        self._copy_file_to_media(file_path, uploaded_file)
        
        return uploaded_file
    
    def _copy_file_to_media(self, source_path: str, uploaded_file: UploadedFile):
        """复制文件到媒体目录"""
        try:
            import shutil
            from django.core.files.storage import default_storage
            
            source_path_obj = Path(source_path)
            if not source_path_obj.exists():
                logger.warning(f"源文件不存在: {source_path}")
                return
            
            # 生成目标路径
            target_path = f"uploads/{timezone.now().strftime('%Y/%m')}/{uploaded_file.id}_{source_path_obj.name}"
            
            # 复制文件
            with open(source_path, 'rb') as source_file:
                uploaded_file.file.save(target_path, source_file, save=True)
            
            logger.info(f"文件复制成功: {source_path} -> {target_path}")
            
        except Exception as e:
            logger.error(f"文件复制失败: {e}")
    
    # 代理相关方法已移除
    
    def process_single_file(self, file_item: BatchFileItem, use_multi_ocr: bool = False, ocr_count: int = 3) -> Dict[str, Any]:
        """
        处理单个文件 - 移植自GUI项目的处理逻辑
        
        Args:
            file_item: 文件项
            use_multi_ocr: 是否使用多重OCR
            ocr_count: OCR次数
            
        Returns:
            dict: 处理结果
        """
        start_time = time.time()
        
        try:
            # 更新处理状态
            file_item.status = 'processing'
            file_item.save()
            
            # 调用OCR处理
            from apps.ocr.tasks import process_image_ocr
            
            user_id = getattr(file_item, 'created_by_id', 1)
            
            # 同步调用OCR处理
            ocr_task = process_image_ocr.delay(
                file_item.file.id,
                user_id,
                use_multi_ocr,
                ocr_count
            )
            
            # 等待结果
            ocr_result = ocr_task.get(timeout=300)
            
            # 更新文件项状态
            if ocr_result.get('status') == 'success':
                file_item.status = 'completed'
                
                # 关联OCR结果
                if 'ocr_result_id' in ocr_result:
                    from apps.ocr.models import OCRResult
                    try:
                        ocr_result_obj = OCRResult.objects.get(id=ocr_result['ocr_result_id'])
                        file_item.ocr_result = ocr_result_obj
                    except OCRResult.DoesNotExist:
                        logger.warning(f"OCR结果 {ocr_result['ocr_result_id']} 不存在")
                
                # 更新点位学习数据
                self._update_point_memory(ocr_result.get('points_data', {}))
                
            else:
                file_item.status = 'failed'
                file_item.error_message = ocr_result.get('error', '处理失败')
            
            file_item.processing_time_seconds = time.time() - start_time
            file_item.save()
            
            # 添加处理延迟
            time.sleep(self.processing_delay)
            
            return {
                'status': 'success' if file_item.status == 'completed' else 'failed',
                'file_item_id': file_item.id,
                'processing_time': file_item.processing_time_seconds,
                'ocr_result': ocr_result
            }
            
        except Exception as e:
            file_item.status = 'failed'
            file_item.error_message = str(e)
            file_item.processing_time_seconds = time.time() - start_time
            file_item.save()
            
            logger.error(f"文件处理失败 {file_item.id}: {e}")
            
            return {
                'status': 'failed',
                'file_item_id': file_item.id,
                'error': str(e),
                'processing_time': file_item.processing_time_seconds
            }
    
    def _update_point_memory(self, points_data: Dict[str, Any]):
        """更新点位学习数据 - 移植自GUI项目"""
        try:
            if not points_data:
                return
            
            # 这里可以实现点位学习逻辑
            # 例如：记录常见的点位名称和值的模式
            logger.info(f"更新点位学习数据: {len(points_data)} 个点位")
            
        except Exception as e:
            logger.warning(f"点位学习更新失败: {e}")
    
    def calculate_progress(self, batch_job: BatchJob) -> Dict[str, Any]:
        """计算批量任务进度"""
        file_items = BatchFileItem.objects.filter(batch_job=batch_job)
        
        total = file_items.count()
        completed = file_items.filter(status='completed').count()
        failed = file_items.filter(status='failed').count()
        processing = file_items.filter(status='processing').count()
        pending = file_items.filter(status='pending').count()
        
        progress_percentage = (completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'processing': processing,
            'pending': pending,
            'progress_percentage': progress_percentage,
            'success_rate': (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
        }
    
    def generate_batch_report(self, batch_job: BatchJob) -> Dict[str, Any]:
        """生成批量处理报告"""
        progress = self.calculate_progress(batch_job)
        
        # 获取处理时间统计
        file_items = BatchFileItem.objects.filter(
            batch_job=batch_job,
            processing_time_seconds__isnull=False
        )
        
        processing_times = [item.processing_time_seconds for item in file_items]
        
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
        else:
            avg_time = min_time = max_time = 0
        
        return {
            'batch_job_id': batch_job.id,
            'batch_job_name': batch_job.name,
            'status': batch_job.status,
            'progress': progress,
            'timing': {
                'started_at': batch_job.started_at,
                'completed_at': batch_job.completed_at,
                'total_duration': batch_job.processing_duration,
                'avg_file_time': avg_time,
                'min_file_time': min_time,
                'max_file_time': max_time
            },
            'settings': batch_job.settings
        }


def get_batch_processing_service() -> BatchProcessingService:
    """获取批量处理服务实例"""
    return BatchProcessingService()
