"""
报告生成模块测试用例

基于GUI项目的实际业务场景设计，验证报告生成功能与原程序的一致性
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
from apps.reports.models import Report, ReportTemplate
from apps.reports.services import ReportGenerationService

User = get_user_model()


class ReportGenerationServiceTestCase(TestCase):
    """报告生成服务测试用例"""
    
    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建测试文件
        self.uploaded_file = UploadedFile.objects.create(
            original_name='test_report.jpg',
            file_size=1024,
            file_type='image',
            mime_type='image/jpeg',
            hash_md5='test_hash_123',
            created_by=self.user
        )
        
        # 创建OCR结果（模拟GUI项目的真实数据）
        self.ocr_result = OCRResult.objects.create(
            file=self.uploaded_file,
            phone='13812345678',
            date='06-15',
            temperature='23.5',
            humidity='45.2',
            check_type='initial',
            points_data={
                '客厅': 0.085,
                '主卧': 0.092,
                '次卧': 0.078,
                '厨房': 0.065,
                '书房': 0.088
            },
            confidence_score=0.9,
            status='completed',
            created_by=self.user
        )
        
        # 创建表单数据（模拟GUI项目的用户输入）
        self.form_data = {
            'customer_name': '张三',
            'customer_phone': '13812345678',
            'detection_address': '北京市朝阳区某某小区1号楼2单元301室',
            'detection_date': '2024-06-15',
            'detection_area': '120',
            'company_name': '北京某某检测公司',
            'report_number': 'BJ20240615001',
            'detection_standard': 'GB/T 18883-2022',
            'detection_method': '酚试剂分光光度法',
            'sampling_person': '李四',
            'analysis_person': '王五',
            'review_person': '赵六',
            'approval_person': '钱七'
        }
    
    def test_generate_report_success(self):
        """测试报告生成成功"""
        service = ReportGenerationService()

        # 准备OCR数据
        ocr_data = {
            'phone': '13812345678',
            'temperature': '24.2',
            'humidity': '48.5',
            'points_data': {
                '客厅': 0.085,
                '主卧': 0.092,
                '次卧': 0.078,
                '厨房': 0.065
            }
        }

        # 执行报告生成
        docx_content, pdf_content = service.generate_report(ocr_data, self.form_data)

        # 验证生成结果
        self.assertIsInstance(docx_content, bytes)
        self.assertIsInstance(pdf_content, bytes)
        self.assertGreater(len(docx_content), 0)
        self.assertGreater(len(pdf_content), 0)
    
    def test_check_type_determination(self):
        """测试检测类型判断"""
        service = ReportGenerationService()

        # 测试初检数据（大多数点位值>0.080）
        initial_points = {
            '客厅': 0.095,
            '主卧': 0.088,
            '次卧': 0.092,
            '厨房': 0.085,
            '书房': 0.078
        }

        check_type = service._determine_check_type(initial_points)
        self.assertEqual(check_type, 'recheck')  # 大多数>0.080，判断为复检

        # 测试复检数据（大多数点位值≤0.080）
        recheck_points = {
            '客厅': 0.065,
            '主卧': 0.072,
            '次卧': 0.058,
            '厨房': 0.078,
            '书房': 0.085
        }

        check_type = service._determine_check_type(recheck_points)
        self.assertEqual(check_type, 'initial')  # 大多数≤0.080，判断为初检
    
    def test_date_info_preparation(self):
        """测试日期信息准备"""
        service = ReportGenerationService()

        # 测试有效日期
        date_info = service._prepare_date_info('12-25')
        self.assertEqual(date_info['month'], '12')
        self.assertEqual(date_info['day'], '25')

        # 测试无效日期（使用当前日期）
        date_info = service._prepare_date_info('')
        self.assertIn('month', date_info)
        self.assertIn('day', date_info)
    
    def test_report_data_preparation(self):
        """测试报告数据准备"""
        service = ReportGenerationService()

        ocr_data = {
            'phone': '13812345678',
            'temperature': '24.2',
            'humidity': '48.5',
            'points_data': {
                '客厅': 0.085,
                '主卧': 0.092
            }
        }

        form_data = {
            'project_address': '北京市朝阳区某某小区',
            'contact_person': '张三',
            'sampling_date': '12-25'
        }

        # 准备报告数据
        report_data = service._prepare_report_data(ocr_data, form_data)

        # 验证数据准备结果
        self.assertEqual(report_data['project_address'], '北京市朝阳区某某小区')
        self.assertEqual(report_data['contact_person'], '张三')
        self.assertEqual(report_data['phone'], '13812345678')
        self.assertIn('points_data', report_data)
        self.assertIn('date_info', report_data)


class ReportModelTestCase(TestCase):
    """报告模型测试用例"""

    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # 创建测试文件
        self.uploaded_file = UploadedFile.objects.create(
            original_name='test_report.jpg',
            file_size=1024,
            file_type='image',
            mime_type='image/jpeg',
            hash_md5='test_hash_123',
            created_by=self.user
        )

        # 创建OCR结果
        self.ocr_result = OCRResult.objects.create(
            file=self.uploaded_file,
            phone='13812345678',
            created_by=self.user
        )

    def test_report_creation(self):
        """测试报告创建"""
        report = Report.objects.create(
            ocr_result=self.ocr_result,
            report_type='detection',
            title='室内空气检测报告',
            form_data={
                'customer_name': '张三',
                'customer_phone': '13812345678',
                'detection_address': '北京市朝阳区某某小区'
            },
            template_data={
                'customer_name': '张三',
                'detection_results': '部分超标',
                'points_table': [
                    {'room_name': '客厅', 'value': 0.085, 'result': '超标'}
                ]
            },
            created_by=self.user
        )

        # 验证创建结果
        self.assertEqual(report.report_type, 'detection')
        self.assertEqual(report.title, '室内空气检测报告')
        self.assertEqual(report.form_data['customer_name'], '张三')
        self.assertEqual(report.template_data['customer_name'], '张三')
        self.assertFalse(report.is_generated)

    def test_report_generation_duration(self):
        """测试报告生成耗时计算"""
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=45)

        report = Report.objects.create(
            ocr_result=self.ocr_result,
            report_type='detection',
            title='测试报告',
            generation_started_at=start_time,
            generation_completed_at=end_time,
            created_by=self.user
        )

        # 验证耗时计算
        self.assertEqual(report.generation_duration, 45.0)

    def test_report_str_representation(self):
        """测试报告字符串表示"""
        report = Report.objects.create(
            ocr_result=self.ocr_result,
            report_type='detection',
            title='室内空气检测报告',
            created_by=self.user
        )

        expected_str = "室内空气检测报告 (检测报告)"
        self.assertEqual(str(report), expected_str)

    def test_report_template_creation(self):
        """测试报告模板创建"""
        template = ReportTemplate.objects.create(
            name='标准检测报告模板',
            description='用于室内空气检测的标准Word模板',
            template_config={
                'page_size': 'A4',
                'font_family': '宋体',
                'font_size': 12,
                'line_spacing': 1.5
            },
            created_by=self.user
        )

        # 验证创建结果
        self.assertEqual(template.name, '标准检测报告模板')
        self.assertTrue(template.is_active)
        self.assertEqual(template.template_config['page_size'], 'A4')

    def test_report_template_str_representation(self):
        """测试报告模板字符串表示"""
        template = ReportTemplate.objects.create(
            name='标准检测报告模板',
            created_by=self.user
        )

        self.assertEqual(str(template), '标准检测报告模板')


class ReportIntegrationTestCase(TestCase):
    """报告生成集成测试用例"""

    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_service_integration(self):
        """测试服务集成"""
        service = ReportGenerationService()

        # 测试服务基本功能
        self.assertIsInstance(service, ReportGenerationService)
        self.assertTrue(hasattr(service, 'generate_report'))
        self.assertTrue(hasattr(service, 'template_dir'))

        # 测试模板目录创建
        self.assertTrue(service.template_dir.exists())
