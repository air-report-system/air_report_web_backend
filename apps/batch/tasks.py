"""
批量处理异步任务 - 移植自GUI项目的batch_image_process_dialog.py
"""
import os
import time
import logging
from datetime import datetime, timedelta
from celery import shared_task, group
from django.utils import timezone
from django.db import transaction
from .models import BatchJob, BatchFileItem

logger = logging.getLogger(__name__)


# WebSocket通信函数
def send_batch_progress_update(batch_job_id: int, progress_data: dict):
    """发送批量任务进度更新"""
    try:
        from .consumers import send_batch_progress_update as ws_send_progress
        ws_send_progress(batch_job_id, progress_data)
    except ImportError:
        # 如果WebSocket依赖不可用，记录警告但不影响功能
        logger.warning("WebSocket依赖不可用，跳过实时进度更新")
    except Exception as e:
        logger.error(f"发送WebSocket进度更新失败: {e}")

def send_file_processing_update(batch_job_id: int, file_data: dict):
    """发送文件处理状态更新"""
    try:
        from .consumers import send_file_processing_update as ws_send_file
        ws_send_file(batch_job_id, file_data)
    except ImportError:
        logger.warning("WebSocket依赖不可用，跳过文件状态更新")
    except Exception as e:
        logger.error(f"发送WebSocket文件更新失败: {e}")

def send_batch_job_completed(batch_job_id: int, completion_data: dict):
    """发送批量任务完成消息"""
    try:
        from .consumers import send_batch_job_completed as ws_send_completed
        ws_send_completed(batch_job_id, completion_data)
    except ImportError:
        logger.warning("WebSocket依赖不可用，跳过任务完成通知")
    except Exception as e:
        logger.error(f"发送WebSocket任务完成通知失败: {e}")


def start_batch_ocr_processing(batch_job_id, force_reprocess=False):
    """
    启动批量OCR处理（非异步版本，用于立即启动）
    增强错误处理和超时管理

    Args:
        batch_job_id: 批量任务ID
        force_reprocess: 是否强制重新处理（不使用已有OCR结果）
    """
    import os

    try:
        # 获取批量任务
        batch_job = BatchJob.objects.get(id=batch_job_id)

        # 更新任务状态
        batch_job.status = 'running'
        batch_job.started_at = timezone.now()
        batch_job.save()

        print(f"开始批量OCR处理: {batch_job.name}")

        # 获取待处理的文件项
        file_items = batch_job.batchfileitem_set.filter(
            status='pending'
        ).order_by('processing_order')

        if not file_items.exists():
            batch_job.status = 'completed'
            batch_job.completed_at = timezone.now()
            batch_job.save()
            print("没有待处理的文件")
            return

        # 获取处理设置
        settings = batch_job.settings or {}
        use_multi_ocr = settings.get('use_multi_ocr', False)
        ocr_count = settings.get('ocr_count', 3)

        # 在部署环境中使用更保守的处理方式
        is_deployment = os.getenv('REPL_DEPLOYMENT') == '1'
        if is_deployment:
            print("部署环境：使用保守的批量处理模式")
            # 减少并发，增加延迟
            ocr_count = min(ocr_count, 2)  # 限制OCR次数

        # 为每个文件项启动OCR处理
        for file_item in file_items:
            try:
                print(f"开始处理文件: {file_item.file.original_name}")

                # 更新文件项状态
                file_item.status = 'processing'
                file_item.save()
                
                # 发送WebSocket文件状态更新
                send_file_processing_update(batch_job.id, {
                    'file_id': file_item.id,
                    'batch_job_id': batch_job.id,
                    'status': 'processing',
                    'filename': file_item.file.original_name
                })

                # 直接进行OCR处理，不再进行复用检查
                from apps.ocr.models import OCRResult

                # 如果强制重新处理，删除现有的OCR结果
                if force_reprocess:
                    print(f"强制重新识别: {file_item.file.original_name}")
                    existing_ocr = OCRResult.objects.filter(
                        file=file_item.file
                    ).first()
                    if existing_ocr:
                        existing_ocr.delete()

                # 创建新的OCR结果记录
                ocr_result = OCRResult.objects.create(
                    file=file_item.file,
                    status='pending',
                    ocr_attempts=ocr_count if use_multi_ocr else 1,
                    created_by=batch_job.created_by
                )
                file_item.ocr_result = ocr_result
                file_item.save()

                # 调用现有的OCR处理任务 - 增强错误处理
                from apps.ocr.tasks import process_image_ocr

                try:
                    if is_deployment:
                        # 部署环境：同步处理以避免超时问题
                        print(f"部署环境：同步处理 {file_item.file.original_name}")

                        # 直接调用OCR处理函数
                        if use_multi_ocr:
                            from apps.ocr.tasks import enhanced_multi_ocr_process
                            result = enhanced_multi_ocr_process(
                                file_item.file.file.path,
                                ocr_count
                            )
                        else:
                            from apps.ocr.tasks import single_ocr_process
                            result = single_ocr_process(file_item.file.file.path)

                        # 创建OCR结果记录
                        from apps.ocr.models import OCRResult
                        ocr_result = OCRResult.objects.create(
                            file=file_item.file,
                            phone=result.get('phone', ''),
                            date=result.get('date', ''),
                            temperature=result.get('temperature', ''),
                            humidity=result.get('humidity', ''),
                            check_type=result.get('check_type', 'initial'),
                            points_data=result.get('points_data', {}),
                            raw_response=result.get('raw_response', ''),
                            confidence_score=result.get('confidence_score', 0.0),
                            ocr_attempts=result.get('ocr_attempts', 1),
                            has_conflicts=result.get('has_conflicts', False),
                            conflict_details=result.get('conflict_details', {}),
                            status='completed',
                            created_by=batch_job.created_by
                        )

                        # 包装结果
                        result = {
                            'status': 'success',
                            'ocr_result_id': ocr_result.id
                        }

                        # 更新文件项状态
                        if result.get('status') == 'success':
                            file_item.status = 'completed'
                            # 关联OCR结果
                            if 'ocr_result_id' in result:
                                from apps.ocr.models import OCRResult
                                try:
                                    ocr_result_obj = OCRResult.objects.get(id=result['ocr_result_id'])
                                    file_item.ocr_result = ocr_result_obj
                                except OCRResult.DoesNotExist:
                                    logger.warning(f"OCR结果 {result['ocr_result_id']} 不存在")
                            
                            # 发送WebSocket文件完成更新
                            send_file_processing_update(batch_job.id, {
                                'file_id': file_item.id,
                                'batch_job_id': batch_job.id,
                                'status': 'completed',
                                'filename': file_item.file.original_name,
                                'ocr_result_id': result.get('ocr_result_id')
                            })
                        else:
                            file_item.status = 'failed'
                            file_item.error_message = result.get('error', '处理失败')
                            
                            # 发送WebSocket文件失败更新
                            send_file_processing_update(batch_job.id, {
                                'file_id': file_item.id,
                                'batch_job_id': batch_job.id,
                                'status': 'failed',
                                'filename': file_item.file.original_name,
                                'error_message': result.get('error', '处理失败')
                            })

                        file_item.save()

                    else:
                        # 开发环境：异步处理
                        task = process_image_ocr.delay(
                            file_item.file.id,
                            batch_job.created_by.id,
                            use_multi_ocr,
                            ocr_count,
                            force_reprocess
                        )
                        print(f"启动OCR任务: {task.id} for {file_item.file.original_name}")

                except Exception as ocr_error:
                    print(f"OCR处理失败: {ocr_error}")
                    file_item.status = 'failed'
                    file_item.error_message = str(ocr_error)
                    file_item.save()

                # 更新批量任务进度
                update_batch_job_progress(batch_job)

                # 在部署环境中添加延迟以避免API限制
                if is_deployment:
                    import time
                    time.sleep(2)  # 2秒延迟

            except Exception as e:
                print(f"处理文件失败: {file_item.file.original_name}, 错误: {e}")
                file_item.status = 'failed'
                file_item.error_message = str(e)
                file_item.save()

                # 更新批量任务进度
                update_batch_job_progress(batch_job)
                continue

        print(f"批量OCR处理启动完成: {batch_job.name}")

    except Exception as e:
        print(f"启动批量OCR处理失败: {e}")
        try:
            batch_job = BatchJob.objects.get(id=batch_job_id)
            batch_job.status = 'failed'
            batch_job.save()
        except:
            pass


def update_batch_job_progress(batch_job):
    """更新批量任务进度"""
    from django.db import transaction
    
    with transaction.atomic():
        # 刷新批量任务以获取最新状态
        batch_job.refresh_from_db()
        
        # 重新计算所有文件项的状态
        file_items = batch_job.batchfileitem_set.all()
        total_files = file_items.count()

        if total_files == 0:
            return

        # 统计各种状态的文件数量
        completed_files = file_items.filter(status='completed').count()
        failed_files = file_items.filter(status='failed').count()
        skipped_files = file_items.filter(status='skipped').count()
        processing_files = file_items.filter(status='processing').count()
        
        # 已处理的文件数量（包括完成、失败、跳过）
        processed_files = completed_files + failed_files + skipped_files
        
        # 更新批量任务的统计信息
        batch_job.total_files = total_files
        batch_job.processed_files = processed_files
        batch_job.failed_files = failed_files

        # 如果所有文件都处理完成（没有pending或processing状态），更新任务状态
        if processed_files == total_files and processing_files == 0:
            if batch_job.status == 'running':
                batch_job.status = 'completed'
                batch_job.completed_at = timezone.now()
        
        batch_job.save()
        
        progress_percentage = batch_job.progress_percentage
        print(f"任务进度更新: {processed_files}/{total_files} ({progress_percentage:.1f}%) - 完成:{completed_files}, 失败:{failed_files}, 跳过:{skipped_files}, 处理中:{processing_files}")
        
        # 发送WebSocket进度更新
        send_batch_progress_update(batch_job.id, {
            'batch_job_id': batch_job.id,
            'progress_percentage': progress_percentage,
            'processed_files': processed_files,
            'failed_files': failed_files,
            'status': batch_job.status,
            'total_files': total_files,
            'completed_files': completed_files,
            'processing_files': processing_files
        })
        
        # 如果任务完成，发送完成通知
        if batch_job.status == 'completed':
            send_batch_job_completed(batch_job.id, {
                'batch_job_id': batch_job.id,
                'total_files': total_files,
                'completed_files': completed_files,
                'failed_files': failed_files,
                'completion_time': batch_job.completed_at.isoformat() if batch_job.completed_at else None
            })


@shared_task(bind=True)
def start_batch_processing(self, batch_job_id, force_reprocess=False):
    """
    启动批量处理任务

    Args:
        batch_job_id: 批量任务ID
        force_reprocess: 是否强制重新处理（不使用已有OCR结果）
    """
    try:
        # 获取批量任务
        batch_job = BatchJob.objects.get(id=batch_job_id)
        
        # 更新任务状态
        batch_job.status = 'running'
        batch_job.started_at = timezone.now()
        batch_job.save()
        
        # 获取待处理的文件项
        file_items = BatchFileItem.objects.filter(
            batch_job=batch_job,
            status='pending'
        ).order_by('processing_order')
        
        if not file_items.exists():
            batch_job.status = 'completed'
            batch_job.completed_at = timezone.now()
            batch_job.save()
            return {
                'status': 'completed',
                'message': '没有待处理的文件'
            }
        
        # 获取处理设置
        settings = batch_job.settings or {}
        use_multi_ocr = settings.get('use_multi_ocr', False)
        ocr_count = settings.get('ocr_count', 3)
        
        # 创建子任务组
        job_group = group(
            process_batch_item.s(
                item.id,
                batch_job_id,
                use_multi_ocr,
                ocr_count,
                force_reprocess
            ) for item in file_items
        )
        
        # 执行子任务组
        result = job_group.apply_async()
        
        # 启动监控任务
        monitor_batch_progress.delay(batch_job_id, result.id)
        
        return {
            'status': 'started',
            'batch_job_id': batch_job_id,
            'total_files': file_items.count(),
            'group_id': result.id
        }
        
    except BatchJob.DoesNotExist:
        return {
            'status': 'error',
            'error': '批量任务不存在'
        }
    except Exception as e:
        # 更新错误状态
        if 'batch_job' in locals():
            batch_job.status = 'failed'
            batch_job.completed_at = timezone.now()
            batch_job.save()
        
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, max_retries=3)
def process_batch_item(self, item_id, batch_job_id, use_multi_ocr=False, ocr_count=3, force_reprocess=False):
    """
    处理批量文件项 - 移植自GUI项目的批量处理逻辑

    Args:
        item_id: 文件项ID
        batch_job_id: 批量任务ID
        use_multi_ocr: 是否使用多重OCR
        ocr_count: OCR次数
        force_reprocess: 是否强制重新处理（不使用已有OCR结果）
    """
    start_time = time.time()

    try:
        # 获取文件项
        file_item = BatchFileItem.objects.get(id=item_id)

        # 更新处理状态
        file_item.status = 'processing'
        file_item.save()

        # 代理设置已移除

        # 调用OCR处理任务
        from apps.ocr.tasks import process_image_ocr

        # 获取用户ID（如果文件项没有创建者，使用批量任务的创建者）
        user_id = getattr(file_item, 'created_by_id', None) or getattr(file_item.batch_job, 'created_by_id', 1)

        ocr_task = process_image_ocr.delay(
            file_item.file.id,
            user_id,
            use_multi_ocr,
            ocr_count,
            force_reprocess
        )

        # 等待OCR任务完成
        ocr_result = ocr_task.get(timeout=300)  # 5分钟超时

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

            # 更新点位学习数据（移植自GUI项目）
            try:
                from apps.core.services import update_point_memory
                points_data = ocr_result.get('points_data', {})
                if points_data:
                    update_point_memory(points_data)
            except Exception as e:
                logger.warning(f"点位学习更新失败: {e}")
        else:
            file_item.status = 'failed'
            file_item.error_message = ocr_result.get('error', '处理失败')

        file_item.processing_time_seconds = time.time() - start_time
        file_item.save()

        # 更新批量任务统计
        update_batch_job_stats(batch_job_id)

        # 添加延迟避免API调用过于频繁（移植自GUI项目）
        time.sleep(1)

        return {
            'status': 'success',
            'item_id': item_id,
            'ocr_result_id': ocr_result.get('ocr_result_id'),
            'processing_time': file_item.processing_time_seconds,
            'points_data': ocr_result.get('points_data', {})
        }

    except BatchFileItem.DoesNotExist:
        return {
            'status': 'error',
            'error': '文件项不存在'
        }
    except Exception as e:
        # 更新错误状态
        if 'file_item' in locals():
            file_item.status = 'failed'
            file_item.error_message = str(e)
            file_item.processing_time_seconds = time.time() - start_time
            file_item.save()

            # 更新批量任务统计
            update_batch_job_stats(batch_job_id)

        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {
            'status': 'error',
            'error': str(e),
            'item_id': item_id
        }


@shared_task
def monitor_batch_progress(batch_job_id, group_id):
    """
    监控批量处理进度
    
    Args:
        batch_job_id: 批量任务ID
        group_id: 任务组ID
    """
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        
        # 等待所有子任务完成
        from celery.result import GroupResult
        group_result = GroupResult.restore(group_id)
        
        # 定期检查进度
        while not group_result.ready():
            time.sleep(10)  # 每10秒检查一次
            
            # 更新进度
            update_batch_job_stats(batch_job_id)
            
            # 检查是否被取消
            batch_job.refresh_from_db()
            if batch_job.status == 'cancelled':
                group_result.revoke(terminate=True)
                break
        
        # 最终更新状态
        update_batch_job_stats(batch_job_id)
        
        # 设置完成状态
        batch_job.refresh_from_db()
        if batch_job.status == 'running':
            if batch_job.failed_files > 0:
                batch_job.status = 'completed_with_errors'
            else:
                batch_job.status = 'completed'
            batch_job.completed_at = timezone.now()
            batch_job.save()
        
        return {
            'status': 'completed',
            'batch_job_id': batch_job_id,
            'processed_files': batch_job.processed_files,
            'failed_files': batch_job.failed_files
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def update_batch_job_stats(batch_job_id):
    """
    更新批量任务统计信息
    
    Args:
        batch_job_id: 批量任务ID
    """
    try:
        with transaction.atomic():
            batch_job = BatchJob.objects.select_for_update().get(id=batch_job_id)
            
            # 统计文件项状态
            file_items = BatchFileItem.objects.filter(batch_job=batch_job)
            processed_count = file_items.filter(status='completed').count()
            failed_count = file_items.filter(status='failed').count()
            
            # 更新统计
            batch_job.processed_files = processed_count
            batch_job.failed_files = failed_count
            
            # 计算预计完成时间
            if batch_job.started_at and processed_count > 0:
                elapsed_time = (timezone.now() - batch_job.started_at).total_seconds()
                avg_time_per_file = elapsed_time / processed_count
                remaining_files = batch_job.total_files - processed_count - failed_count
                
                if remaining_files > 0:
                    estimated_remaining_time = avg_time_per_file * remaining_files
                    batch_job.estimated_completion = timezone.now() + timedelta(seconds=estimated_remaining_time)
            
            batch_job.save()
            
    except Exception as e:
        print(f"更新批量任务统计失败: {e}")


@shared_task
def retry_failed_items(batch_job_id):
    """
    重试失败的文件项
    
    Args:
        batch_job_id: 批量任务ID
    """
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        
        # 获取失败的文件项
        failed_items = BatchFileItem.objects.filter(
            batch_job=batch_job,
            status='failed'
        )
        
        if not failed_items.exists():
            return {
                'status': 'no_failed_items',
                'message': '没有失败的文件需要重试'
            }
        
        # 重置失败项状态
        failed_items.update(
            status='pending',
            error_message='',
            processing_time_seconds=None
        )
        
        # 重新启动批量处理
        result = start_batch_processing.delay(batch_job_id)
        
        return {
            'status': 'retry_started',
            'batch_job_id': batch_job_id,
            'retry_count': failed_items.count(),
            'task_id': result.id
        }
        
    except BatchJob.DoesNotExist:
        return {
            'status': 'error',
            'error': '批量任务不存在'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task
def cancel_batch_processing(batch_job_id):
    """
    取消批量处理
    
    Args:
        batch_job_id: 批量任务ID
    """
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        
        # 更新任务状态
        batch_job.status = 'cancelled'
        batch_job.completed_at = timezone.now()
        batch_job.save()
        
        # 取消待处理的文件项
        BatchFileItem.objects.filter(
            batch_job=batch_job,
            status='pending'
        ).update(status='skipped')
        
        return {
            'status': 'cancelled',
            'batch_job_id': batch_job_id
        }
        
    except BatchJob.DoesNotExist:
        return {
            'status': 'error',
            'error': '批量任务不存在'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task
def cleanup_old_batch_jobs():
    """清理旧的批量任务"""
    # 删除30天前完成的批量任务
    cutoff_date = timezone.now() - timedelta(days=30)
    old_jobs = BatchJob.objects.filter(
        status__in=['completed', 'failed', 'cancelled'],
        completed_at__lt=cutoff_date
    )
    
    count = old_jobs.count()
    old_jobs.delete()
    
    return f"清理了 {count} 个旧的批量任务"
