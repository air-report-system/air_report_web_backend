"""
批量处理模块测试用例

基于GUI项目的实际业务场景设计，验证批量处理功能与原程序的一致性
"""
import os
import tempfile
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from PIL import Image
import io

from apps.files.models import UploadedFile
from apps.ocr.models import OCRResult
from apps.batch.models import BatchJob, BatchFileItem

User = get_user_model()


class BatchProcessingTestCase(TestCase):
    """批量处理测试用例"""
    
    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建测试图片文件
        self.test_images = []
        for i in range(5):
            image_file = self.create_test_image(f'test_image_{i}.jpg')
            uploaded_file = UploadedFile.objects.create(
                file=image_file,
                original_name=f'detection_report_{i}.jpg',
                file_size=1024,
                file_type='image',
                mime_type='image/jpeg',
                hash_md5=f'test_hash_{i}',
                created_by=self.user
            )
            self.test_images.append(uploaded_file)
        
        # 创建批量任务
        self.batch_job = BatchJob.objects.create(
            name='2024年12月批量检测报告处理',
            total_files=5,
            settings={
                'ocr_provider': 'gemini',
                'enable_multi_ocr': True,
                'ocr_attempts': 3,
                'auto_retry_failed': True,
                'parallel_processing': False,
                'batch_size': 10
            },
            created_by=self.user
        )
        
        # 创建批量文件项
        for i, uploaded_file in enumerate(self.test_images):
            BatchFileItem.objects.create(
                batch_job=self.batch_job,
                file=uploaded_file,
                processing_order=i + 1
            )
    
    def create_test_image(self, filename):
        """创建测试图片文件"""
        image = Image.new('RGB', (800, 600), color='white')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            name=filename,
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )
    
    def test_batch_job_creation(self):
        """测试批量任务创建"""
        # 验证批量任务创建
        self.assertEqual(self.batch_job.name, '2024年12月批量检测报告处理')
        self.assertEqual(self.batch_job.total_files, 5)
        self.assertEqual(self.batch_job.status, 'created')
        self.assertEqual(self.batch_job.processed_files, 0)
        self.assertEqual(self.batch_job.failed_files, 0)
        
        # 验证设置
        settings = self.batch_job.settings
        self.assertEqual(settings['ocr_provider'], 'gemini')
        self.assertTrue(settings['enable_multi_ocr'])
        self.assertEqual(settings['ocr_attempts'], 3)
    
    def test_batch_file_items_creation(self):
        """测试批量文件项创建"""
        file_items = BatchFileItem.objects.filter(batch_job=self.batch_job)
        
        # 验证文件项数量
        self.assertEqual(file_items.count(), 5)
        
        # 验证处理顺序
        for i, item in enumerate(file_items.order_by('processing_order')):
            self.assertEqual(item.processing_order, i + 1)
            self.assertEqual(item.status, 'pending')
            self.assertIsNone(item.ocr_result)
    
    def test_batch_job_progress_calculation(self):
        """测试批量任务进度计算"""
        # 初始进度应该为0
        self.assertEqual(self.batch_job.progress_percentage, 0)
        
        # 更新处理进度
        self.batch_job.processed_files = 2
        self.batch_job.save()
        
        # 验证进度计算
        expected_progress = (2 / 5) * 100  # 40%
        self.assertEqual(self.batch_job.progress_percentage, expected_progress)
        
        # 完成所有文件
        self.batch_job.processed_files = 5
        self.batch_job.save()
        
        # 验证完成进度
        self.assertEqual(self.batch_job.progress_percentage, 100)
    
    def test_batch_job_processing_duration(self):
        """测试批量任务处理耗时计算"""
        start_time = timezone.now()
        end_time = start_time + timedelta(minutes=10)
        
        self.batch_job.started_at = start_time
        self.batch_job.completed_at = end_time
        self.batch_job.save()
        
        # 验证耗时计算
        expected_duration = 10 * 60  # 10分钟 = 600秒
        self.assertEqual(self.batch_job.processing_duration, expected_duration)
    
    @patch('apps.ocr.services.get_ocr_service')
    def test_batch_processing_success_scenario(self, mock_get_service):
        """测试批量处理成功场景"""
        # 模拟OCR服务
        mock_service = Mock()
        mock_service.process_image.return_value = {
            'phone': '13812345678',
            'date': '12-25',
            'temperature': '24.5',
            'humidity': '48.2',
            'check_type': 'initial',
            'points_data': {'客厅': 0.085, '主卧': 0.092},
            'confidence_score': 0.9,
            'raw_response': 'test response'
        }
        mock_get_service.return_value = mock_service
        
        # 模拟批量处理逻辑
        file_items = BatchFileItem.objects.filter(batch_job=self.batch_job)
        processed_count = 0
        
        for item in file_items:
            # 创建OCR结果
            ocr_result = OCRResult.objects.create(
                file=item.file,
                phone='13812345678',
                date='12-25',
                check_type='initial',
                points_data={'客厅': 0.085, '主卧': 0.092},
                status='completed',
                confidence_score=0.9,
                created_by=self.user
            )
            
            # 更新文件项状态
            item.ocr_result = ocr_result
            item.status = 'completed'
            item.processing_time_seconds = 15.5
            item.save()
            
            processed_count += 1
        
        # 更新批量任务状态
        self.batch_job.processed_files = processed_count
        self.batch_job.status = 'completed'
        self.batch_job.completed_at = timezone.now()
        self.batch_job.save()
        
        # 验证处理结果
        self.assertEqual(self.batch_job.status, 'completed')
        self.assertEqual(self.batch_job.processed_files, 5)
        self.assertEqual(self.batch_job.failed_files, 0)
        self.assertEqual(self.batch_job.progress_percentage, 100)
        
        # 验证所有文件项都已完成
        completed_items = BatchFileItem.objects.filter(
            batch_job=self.batch_job,
            status='completed'
        )
        self.assertEqual(completed_items.count(), 5)
        
        # 验证OCR结果已创建
        for item in completed_items:
            self.assertIsNotNone(item.ocr_result)
            self.assertEqual(item.ocr_result.status, 'completed')
    
    def test_batch_processing_failure_scenario(self):
        """测试批量处理失败场景"""
        file_items = BatchFileItem.objects.filter(batch_job=self.batch_job)
        
        # 模拟部分文件处理失败
        for i, item in enumerate(file_items):
            if i < 3:  # 前3个成功
                ocr_result = OCRResult.objects.create(
                    file=item.file,
                    phone='13812345678',
                    status='completed',
                    created_by=self.user
                )
                item.ocr_result = ocr_result
                item.status = 'completed'
                item.processing_time_seconds = 12.3
            else:  # 后2个失败
                item.status = 'failed'
                item.error_message = 'OCR处理失败：API调用超时'
            
            item.save()
        
        # 更新批量任务状态
        self.batch_job.processed_files = 3
        self.batch_job.failed_files = 2
        self.batch_job.status = 'completed'  # 即使有失败也可以标记为完成
        self.batch_job.save()
        
        # 验证处理结果
        self.assertEqual(self.batch_job.processed_files, 3)
        self.assertEqual(self.batch_job.failed_files, 2)
        self.assertEqual(self.batch_job.progress_percentage, 60)  # 3/5 = 60%
        
        # 验证失败文件项
        failed_items = BatchFileItem.objects.filter(
            batch_job=self.batch_job,
            status='failed'
        )
        self.assertEqual(failed_items.count(), 2)
        
        for failed_item in failed_items:
            self.assertIn('OCR处理失败', failed_item.error_message)
            self.assertIsNone(failed_item.ocr_result)
    
    def test_batch_processing_with_conflicts(self):
        """测试包含冲突的批量处理（模拟GUI项目的多重OCR验证）"""
        file_item = BatchFileItem.objects.filter(batch_job=self.batch_job).first()
        
        # 创建有冲突的OCR结果
        ocr_result = OCRResult.objects.create(
            file=file_item.file,
            phone='13812345678',
            date='12-25',
            check_type='initial',
            points_data={'客厅': 0.085, '主卧': 0.092},
            status='completed',
            confidence_score=0.85,
            ocr_attempts=3,
            has_conflicts=True,
            conflict_details={
                'phone': ['13812345678', '13812345679'],
                'date': ['12-25', '12-26'],
                'points_data': {
                    '客厅': [0.085, 0.087, 0.086]
                }
            },
            created_by=self.user
        )
        
        # 更新文件项
        file_item.ocr_result = ocr_result
        file_item.status = 'completed'
        file_item.save()
        
        # 验证冲突处理
        self.assertTrue(ocr_result.has_conflicts)
        self.assertEqual(ocr_result.ocr_attempts, 3)
        self.assertIn('phone', ocr_result.conflict_details)
        self.assertEqual(len(ocr_result.conflict_details['phone']), 2)
    
    def test_batch_job_cancellation(self):
        """测试批量任务取消"""
        # 开始任务
        self.batch_job.status = 'running'
        self.batch_job.started_at = timezone.now()
        self.batch_job.save()
        
        # 处理部分文件
        file_items = BatchFileItem.objects.filter(batch_job=self.batch_job)[:2]
        for item in file_items:
            item.status = 'completed'
            item.save()
        
        self.batch_job.processed_files = 2
        self.batch_job.save()
        
        # 取消任务
        self.batch_job.status = 'cancelled'
        self.batch_job.completed_at = timezone.now()
        self.batch_job.save()
        
        # 将剩余文件标记为跳过
        remaining_items = BatchFileItem.objects.filter(
            batch_job=self.batch_job,
            status='pending'
        )
        remaining_items.update(status='skipped')
        
        # 验证取消结果
        self.assertEqual(self.batch_job.status, 'cancelled')
        self.assertEqual(self.batch_job.processed_files, 2)
        
        skipped_items = BatchFileItem.objects.filter(
            batch_job=self.batch_job,
            status='skipped'
        )
        self.assertEqual(skipped_items.count(), 3)  # 剩余3个文件被跳过
    
    def test_batch_processing_performance_tracking(self):
        """测试批量处理性能跟踪"""
        file_items = BatchFileItem.objects.filter(batch_job=self.batch_job)
        
        # 模拟不同的处理时间
        processing_times = [10.5, 15.2, 8.7, 12.1, 9.8]
        
        for i, item in enumerate(file_items):
            item.status = 'completed'
            item.processing_time_seconds = processing_times[i]
            item.save()
        
        # 计算性能统计
        completed_items = BatchFileItem.objects.filter(
            batch_job=self.batch_job,
            status='completed'
        )
        
        total_time = sum(item.processing_time_seconds for item in completed_items)
        avg_time = total_time / completed_items.count()
        min_time = min(item.processing_time_seconds for item in completed_items)
        max_time = max(item.processing_time_seconds for item in completed_items)
        
        # 验证性能统计
        self.assertEqual(completed_items.count(), 5)
        self.assertAlmostEqual(total_time, sum(processing_times), places=1)
        self.assertAlmostEqual(avg_time, sum(processing_times) / len(processing_times), places=1)
        self.assertEqual(min_time, min(processing_times))
        self.assertEqual(max_time, max(processing_times))
    
    def test_batch_job_str_representation(self):
        """测试批量任务字符串表示"""
        expected_str = f"{self.batch_job.name} (已创建)"
        self.assertEqual(str(self.batch_job), expected_str)
    
    def test_batch_file_item_str_representation(self):
        """测试批量文件项字符串表示"""
        file_item = BatchFileItem.objects.filter(batch_job=self.batch_job).first()
        expected_str = f"{self.batch_job.name} - {file_item.file.original_name}"
        self.assertEqual(str(file_item), expected_str)
