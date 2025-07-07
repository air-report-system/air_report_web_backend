"""
OCR处理异步任务
"""
import os
import json
import time
import hashlib
import logging
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from .models import OCRResult, ContactInfo
from apps.files.models import UploadedFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_image_ocr(self, file_id, user_id, use_multi_ocr=False, ocr_count=3):
    """
    处理图片OCR任务
    
    Args:
        file_id: 文件ID
        user_id: 用户ID
        use_multi_ocr: 是否使用多重OCR
        ocr_count: OCR次数
    """
    try:
        # 获取文件和OCR结果记录
        file_obj = UploadedFile.objects.get(id=file_id)
        ocr_result = OCRResult.objects.filter(file=file_obj).first()
        
        if not ocr_result:
            ocr_result = OCRResult.objects.create(
                file=file_obj,
                status='processing',
                ocr_attempts=ocr_count if use_multi_ocr else 1,
                created_by_id=user_id
            )
        
        # 更新处理状态
        ocr_result.status = 'processing'
        ocr_result.processing_started_at = timezone.now()
        ocr_result.save()
        
        # 检查文件是否存在
        if not file_obj.file or not os.path.exists(file_obj.file.path):
            raise Exception("文件不存在")
        
        # 执行OCR处理
        if use_multi_ocr:
            result = enhanced_multi_ocr_process(file_obj.file.path, ocr_count)
        else:
            result = single_ocr_process(file_obj.file.path)
        
        # 更新OCR结果
        ocr_result.status = 'completed'
        ocr_result.phone = result.get('phone', '')
        ocr_result.date = result.get('date', '')
        ocr_result.temperature = result.get('temperature', '')
        ocr_result.humidity = result.get('humidity', '')
        ocr_result.check_type = result.get('check_type', 'initial')
        ocr_result.points_data = result.get('points_data', {})
        ocr_result.raw_response = result.get('raw_response', '')
        ocr_result.confidence_score = result.get('confidence_score', 0.0)
        ocr_result.has_conflicts = result.get('has_conflicts', False)
        ocr_result.conflict_details = result.get('conflict_details', {})
        ocr_result.processing_completed_at = timezone.now()
        ocr_result.save()
        
        # 创建或更新联系人信息
        try:
            if ocr_result.phone:
                create_or_update_contact_info_enhanced(ocr_result)
        except Exception as contact_error:
            logger.warning(f"联系人信息创建失败: {contact_error}")
            # 不影响主要的OCR处理流程
        
        # 标记文件为已处理
        file_obj.is_processed = True
        file_obj.save()
        
        return {
            'status': 'success',
            'ocr_result_id': ocr_result.id,
            'phone': ocr_result.phone,
            'date': ocr_result.date,
            'check_type': ocr_result.check_type,
            'points_count': len(ocr_result.points_data) if ocr_result.points_data else 0
        }
        
    except Exception as e:
        # 更新错误状态
        if 'ocr_result' in locals():
            ocr_result.status = 'failed'
            ocr_result.error_message = str(e)
            ocr_result.processing_completed_at = timezone.now()
            ocr_result.save()
        
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {
            'status': 'error',
            'error': str(e),
            'ocr_result_id': ocr_result.id if 'ocr_result' in locals() else None
        }


def single_ocr_process(image_path):
    """
    单次OCR处理

    Args:
        image_path: 图片路径

    Returns:
        dict: OCR结果
    """
    from .services import get_ocr_service

    try:
        # 获取OCR服务实例
        ocr_service = get_ocr_service()

        # 调用OCR服务处理图片
        result = ocr_service.process_image(image_path)

        # 确保结果包含所有必需字段
        default_result = {
            'phone': '',
            'date': '',
            'temperature': '',
            'humidity': '',
            'check_type': 'initial',
            'points_data': {},
            'raw_response': '',
            'confidence_score': 0.0,
            'has_conflicts': False,
            'conflict_details': {}
        }

        # 合并结果，确保所有字段都存在
        final_result = {**default_result, **result}

        return final_result

    except Exception as e:
        # OCR处理失败时抛出异常，让上层处理
        raise Exception(f'OCR处理失败: {str(e)}')


def enhanced_multi_ocr_process(image_path, ocr_count):
    """
    增强的多重OCR处理

    Args:
        image_path: 图片路径
        ocr_count: OCR次数

    Returns:
        dict: OCR结果
    """
    from .services import get_enhanced_ocr_service

    try:
        # 获取增强OCR服务实例
        enhanced_ocr_service = get_enhanced_ocr_service()

        # 调用多重OCR处理
        result = enhanced_ocr_service.process_image_multi_ocr(image_path, ocr_count)

        # 提取最佳结果
        best_result = result.get('best_result', {})

        # 添加多重OCR特有的信息
        best_result.update({
            'has_conflicts': result.get('has_conflicts', False),
            'conflict_details': result.get('analysis', {}),
            'ocr_attempts': result.get('ocr_attempts', ocr_count)
        })

        return best_result

    except Exception:
        # 如果增强OCR失败，回退到原有的多重OCR
        return multi_ocr_process(image_path, ocr_count)


def multi_ocr_process(image_path, ocr_count):
    """
    多重OCR处理（原有实现）

    Args:
        image_path: 图片路径
        ocr_count: OCR次数

    Returns:
        dict: OCR结果
    """
    results = []
    errors = []

    # 执行多次OCR
    for i in range(ocr_count):
        try:
            result = single_ocr_process(image_path)
            results.append(result)
        except Exception as e:
            errors.append(f"第{i+1}次OCR失败: {str(e)}")
        time.sleep(1)  # 间隔1秒

    # 如果所有OCR都失败了，抛出异常
    if not results:
        raise Exception(f"所有OCR尝试都失败了: {'; '.join(errors)}")

    # 分析多重OCR结果
    final_result = analyze_multi_ocr_results(results)

    # 如果有部分失败，记录在结果中
    if errors:
        final_result['partial_errors'] = errors

    return final_result


def analyze_multi_ocr_results(results):
    """
    分析多重OCR结果
    
    Args:
        results: OCR结果列表
        
    Returns:
        dict: 最终OCR结果
    """
    if not results:
        return {}
    
    # 如果只有一个结果，直接返回
    if len(results) == 1:
        return results[0]
    
    # 统计各字段的出现频率
    phone_counts = {}
    date_counts = {}
    temp_counts = {}
    humidity_counts = {}
    check_type_counts = {}
    
    for result in results:
        phone = result.get('phone', '')
        if phone:
            phone_counts[phone] = phone_counts.get(phone, 0) + 1
        
        date = result.get('date', '')
        if date:
            date_counts[date] = date_counts.get(date, 0) + 1
        
        temp = result.get('temperature', '')
        if temp:
            temp_counts[temp] = temp_counts.get(temp, 0) + 1
        
        humidity = result.get('humidity', '')
        if humidity:
            humidity_counts[humidity] = humidity_counts.get(humidity, 0) + 1
        
        check_type = result.get('check_type', 'initial')
        check_type_counts[check_type] = check_type_counts.get(check_type, 0) + 1
    
    # 选择出现频率最高的值
    final_result = {
        'phone': max(phone_counts, key=phone_counts.get) if phone_counts else '',
        'date': max(date_counts, key=date_counts.get) if date_counts else '',
        'temperature': max(temp_counts, key=temp_counts.get) if temp_counts else '',
        'humidity': max(humidity_counts, key=humidity_counts.get) if humidity_counts else '',
        'check_type': max(check_type_counts, key=check_type_counts.get) if check_type_counts else 'initial',
        'points_data': results[0].get('points_data', {}),  # 使用第一个结果的点位数据
        'raw_response': json.dumps([r.get('raw_response', '') for r in results]),
        'confidence_score': sum(r.get('confidence_score', 0) for r in results) / len(results),
        'has_conflicts': len(set(r.get('phone', '') for r in results)) > 1,
        'conflict_details': {
            'phone_variants': list(phone_counts.keys()),
            'date_variants': list(date_counts.keys()),
            'ocr_count': len(results)
        }
    }
    
    return final_result


def create_or_update_contact_info_enhanced(ocr_result):
    """
    创建或更新联系人信息（增强版）- 使用数据库表

    Args:
        ocr_result: OCR结果对象
    """
    if not ocr_result.phone:
        return

    try:
        from .services import get_contact_matching_service
        from .models import ContactInfo

        # 获取联系人匹配服务
        contact_service = get_contact_matching_service()

        # 使用数据库表进行匹配
        match_result = contact_service.match_contact_info_from_db(
            ocr_result.phone,
            ocr_result.date or '',
            ocr_result.points_data or {}
        )

        # 查找是否已存在联系人信息
        contact_info, created = ContactInfo.objects.get_or_create(
            ocr_result=ocr_result,
            defaults={
                'contact_name': match_result.get('contact_name', ''),
                'full_phone': match_result.get('full_phone', ocr_result.phone),
                'address': match_result.get('address', ''),
                'match_type': match_result.get('match_type', 'manual'),
                'similarity_score': match_result.get('similarity_score', 0.0),
                'match_source': match_result.get('match_source', 'manual'),
                'csv_record': match_result.get('csv_record')
            }
        )

        if not created:
            # 更新现有联系人信息
            contact_info.contact_name = match_result.get('contact_name', contact_info.contact_name)
            contact_info.full_phone = match_result.get('full_phone', ocr_result.phone)
            contact_info.address = match_result.get('address', contact_info.address)
            contact_info.match_type = match_result.get('match_type', contact_info.match_type)
            contact_info.similarity_score = match_result.get('similarity_score', contact_info.similarity_score)
            contact_info.match_source = match_result.get('match_source', contact_info.match_source)
            contact_info.save()

    except Exception:
        # 如果增强匹配失败，回退到原有方法
        create_or_update_contact_info(ocr_result)


def create_or_update_contact_info(ocr_result):
    """
    创建或更新联系人信息（原有实现）

    Args:
        ocr_result: OCR结果对象
    """
    if not ocr_result.phone:
        return

    try:
        # 查找是否已存在联系人信息
        contact_info, created = ContactInfo.objects.get_or_create(
            ocr_result=ocr_result,
            defaults={
                'full_phone': ocr_result.phone,
                'match_type': 'manual',
                'match_source': 'ocr_processing'
            }
        )

        if not created:
            # 更新现有联系人信息
            contact_info.full_phone = ocr_result.phone
            contact_info.save()

    except Exception as e:
        print(f"创建联系人信息失败: {e}")


@shared_task
def cleanup_failed_ocr_results():
    """清理失败的OCR结果"""
    from datetime import timedelta
    
    # 删除7天前失败的OCR结果
    cutoff_date = timezone.now() - timedelta(days=7)
    failed_results = OCRResult.objects.filter(
        status='failed',
        created_at__lt=cutoff_date
    )
    
    count = failed_results.count()
    failed_results.delete()
    
    return f"清理了 {count} 个失败的OCR结果"


def process_image_ocr_sync(file_id, user_id, use_multi_ocr=False, ocr_count=3):
    """
    同步处理图片OCR任务（用于Replit等环境）
    
    Args:
        file_id: 文件ID
        user_id: 用户ID
        use_multi_ocr: 是否使用多重OCR
        ocr_count: OCR次数
    
    Returns:
        dict: 处理结果
    """
    try:
        logger.info(f"开始同步OCR处理: file_id={file_id}, user_id={user_id}")
        
        # 获取文件和OCR结果记录
        file_obj = UploadedFile.objects.get(id=file_id)
        ocr_result = OCRResult.objects.filter(file=file_obj).first()
        
        if not ocr_result:
            ocr_result = OCRResult.objects.create(
                file=file_obj,
                status='processing',
                ocr_attempts=ocr_count if use_multi_ocr else 1,
                created_by_id=user_id
            )
        
        # 更新处理状态
        ocr_result.status = 'processing'
        ocr_result.processing_started_at = timezone.now()
        ocr_result.save()
        
        # 检查文件是否存在
        if not file_obj.file or not os.path.exists(file_obj.file.path):
            raise Exception("文件不存在")
        
        logger.info(f"文件路径: {file_obj.file.path}")
        
        # 执行OCR处理
        if use_multi_ocr:
            logger.info("使用多重OCR处理")
            result = enhanced_multi_ocr_process(file_obj.file.path, ocr_count)
        else:
            logger.info("使用单次OCR处理")
            result = single_ocr_process(file_obj.file.path)
        
        logger.info(f"OCR处理结果: {result}")
        
        # 更新OCR结果
        ocr_result.status = 'completed'
        ocr_result.phone = result.get('phone', '')
        ocr_result.date = result.get('date', '')
        ocr_result.temperature = result.get('temperature', '')
        ocr_result.humidity = result.get('humidity', '')
        ocr_result.check_type = result.get('check_type', 'initial')
        ocr_result.points_data = result.get('points_data', {})
        ocr_result.raw_response = result.get('raw_response', '')
        ocr_result.confidence_score = result.get('confidence_score', 0.0)
        ocr_result.has_conflicts = result.get('has_conflicts', False)
        ocr_result.conflict_details = result.get('conflict_details', {})
        ocr_result.processing_completed_at = timezone.now()
        ocr_result.save()
        
        logger.info(f"OCR结果已更新: {ocr_result.id}")
        
        # 创建或更新联系人信息
        try:
            if ocr_result.phone:
                create_or_update_contact_info_enhanced(ocr_result)
                logger.info("联系人信息已创建/更新")
        except Exception as contact_error:
            logger.warning(f"联系人信息创建失败: {contact_error}")
            # 不影响主要的OCR处理流程
        
        # 标记文件为已处理
        file_obj.is_processed = True
        file_obj.save()
        
        return {
            'status': 'success',
            'ocr_result_id': ocr_result.id,
            'phone': ocr_result.phone,
            'date': ocr_result.date,
            'check_type': ocr_result.check_type,
            'points_count': len(ocr_result.points_data) if ocr_result.points_data else 0
        }
        
    except Exception as e:
        logger.error(f"同步OCR处理失败: {str(e)}", exc_info=True)
        
        # 更新错误状态
        if 'ocr_result' in locals():
            ocr_result.status = 'failed'
            ocr_result.error_message = str(e)
            ocr_result.processing_completed_at = timezone.now()
            ocr_result.save()
        
        return {
            'status': 'error',
            'error': str(e),
            'ocr_result_id': ocr_result.id if 'ocr_result' in locals() else None
        }
