"""
微信CSV处理测试
基于GUI项目的真实业务场景设计测试用例
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from rest_framework import status

from .models import WechatCsvRecord, ProcessingHistory, ValidationResult, LoginAttempt
from .services import WechatMessageProcessor, CsvDataProcessor, DuplicateDetector, GitHubService


class WechatMessageProcessorTest(TestCase):
    """微信消息处理器测试"""
    
    def setUp(self):
        self.processor = WechatMessageProcessor()
    
    @patch('google.generativeai.GenerativeModel')
    def test_format_wechat_message(self, mock_model_class):
        """测试微信消息格式化"""
        # 模拟Gemini API响应
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "张三,13800138000,北京市朝阳区某小区,国标,5000,100,2024-01-15,5,{除醛宝:2}"
        mock_model.generate_content.return_value = mock_response
        
        with patch('apps.wechat_csv.services.genai.GenerativeModel', return_value=mock_model):
            # 真实业务场景的微信消息
            wechat_text = """
            客户信息：
            姓名：张三
            电话：13800138000
            地址：北京市朝阳区某小区
            检测类型：国标
            成交金额：5000元
            面积：100平方米
            履约时间：2024年1月15日
            CMA点位：5个
            赠品：除醛宝2个
            """
            
            result = self.processor.format_wechat_message(wechat_text)
            self.assertIn("张三", result)
            self.assertIn("13800138000", result)
            self.assertIn("北京市朝阳区某小区", result)
    
    def test_extract_gift_notes(self):
        """测试备注赠品提取"""
        test_cases = [
            ("赠送除醛宝2个", "{除醛宝:2}"),
            ("炭包3包", "{炭包:3}"),
            ("除醛机一台", "{除醛机:1}"),
            ("除醛喷雾1瓶", "{除醛喷雾:1}"),
            ("除醛宝2个，炭包1包", "{除醛宝:2;炭包:1}"),
            ("没有赠品", ""),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.processor._extract_gift_notes(text)
                self.assertEqual(result, expected)
    
    def test_extract_cma_points(self):
        """测试CMA点位提取"""
        test_cases = [
            ("CMA检测5个点位", "5"),
            ("检测点位8个", "8"),
            ("CMA 3个", "3"),
            ("没有CMA", ""),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.processor._extract_cma_points(text)
                self.assertEqual(result, expected)
    
    def test_get_current_month_file(self):
        """测试月份文件路径生成"""
        fulfillment_dates = ["2024-01-15", "2024-01-20"]
        result = self.processor.get_current_month_file(fulfillment_dates)
        self.assertEqual(result, "to csv/1月.csv")


class CsvDataProcessorTest(TestCase):
    """CSV数据处理器测试"""
    
    def setUp(self):
        self.processor = CsvDataProcessor()
    
    def test_parse_csv_to_table_data(self):
        """测试CSV解析为表格数据"""
        csv_content = '张三,13800138000,北京市朝阳区某小区,国标,5000,100,2024-01-15,5,"{除醛宝:2}"'
        
        result = self.processor.parse_csv_to_table_data(csv_content)
        
        self.assertEqual(len(result['table_data']), 1)
        row = result['table_data'][0]
        self.assertEqual(row['客户姓名'], '张三')
        self.assertEqual(row['客户电话'], '13800138000')
        self.assertEqual(row['备注赠品'], '{除醛宝:2}')
    
    def test_validate_table_data(self):
        """测试表格数据验证"""
        # 有效数据
        valid_data = [{
            '客户姓名': '张三',
            '客户电话': '13800138000',
            '客户地址': '北京市朝阳区某小区',
            '商品类型': '国标',
            '成交金额': '5000',
            '面积': '100',
            '履约时间': '2024-01-15',
            'CMA点位数量': '5',
            '备注赠品': '{除醛宝:2}'
        }]
        
        result = self.processor.validate_table_data(valid_data)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        
        # 无效数据
        invalid_data = [{
            '客户姓名': '',  # 空姓名
            '客户电话': '123',  # 无效电话
            '客户地址': '',  # 空地址
            '商品类型': '其他',  # 无效类型
            '成交金额': 'abc',  # 无效金额
            '面积': 'xyz',  # 无效面积
            '履约时间': '2024/01/15',  # 无效日期格式
            'CMA点位数量': '5',
            '备注赠品': '{无效赠品:2}'  # 无效赠品
        }]
        
        result = self.processor.validate_table_data(invalid_data)
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_table_data_to_csv(self):
        """测试表格数据转换为CSV"""
        table_data = [{
            '客户姓名': '张三',
            '客户电话': '13800138000',
            '客户地址': '北京市朝阳区某小区',
            '商品类型': '国标',
            '成交金额': '5000',
            '面积': '100',
            '履约时间': '2024-01-15',
            'CMA点位数量': '5',
            '备注赠品': '{除醛宝:2}'
        }]
        
        result = self.processor.table_data_to_csv(table_data)
        self.assertIn('张三', result)
        self.assertIn('13800138000', result)
        self.assertIn('{除醛宝:2}', result)
    
    def test_validate_and_fix_csv_line(self):
        """测试CSV行格式修正"""
        # 需要修正的CSV行（大括号字段未被引号包围）
        csv_line = "张三,13800138000,北京市朝阳区某小区,国标,5000,100,2024-01-15,5,{除醛宝:2}"
        
        fixed_line, fix_info = self.processor._validate_and_fix_csv_line(csv_line)
        
        self.assertIn('"{除醛宝:2}"', fixed_line)
        self.assertEqual(len(fix_info), 1)
        self.assertIn('大括号字段已添加双引号包围', fix_info[0]['message'])


class DuplicateDetectorTest(TestCase):
    """重复检测器测试"""
    
    def setUp(self):
        self.detector = DuplicateDetector()
    
    def test_check_for_duplicates_phone(self):
        """测试电话号码重复检测"""
        new_entries = ["张三,13800138000,北京市朝阳区某小区,国标,5000,100,2024-01-15,5,"]
        existing_content = "李四,13800138000,上海市浦东新区,母婴,3000,80,2024-01-10,3,"
        
        result = self.detector.check_for_duplicates(new_entries, existing_content)
        
        self.assertEqual(len(result['duplicate_indexes']), 1)
        self.assertEqual(result['duplicate_indexes'][0], 0)
        self.assertEqual(result['match_details'][0]['matched_rows'][0]['match_type'], '电话号码相同')
    
    def test_check_for_duplicates_name_address(self):
        """测试姓名地址模糊匹配"""
        new_entries = ["张三先生,13900139000,北京市朝阳区某小区1号楼,国标,5000,100,2024-01-15,5,"]
        existing_content = "张三,13800138000,北京市朝阳区某小区,母婴,3000,80,2024-01-10,3,"
        
        result = self.detector.check_for_duplicates(new_entries, existing_content)
        
        self.assertEqual(len(result['duplicate_indexes']), 1)
        self.assertEqual(result['match_details'][0]['matched_rows'][0]['match_type'], '姓名和地址相似')
    
    def test_clean_name(self):
        """测试姓名清理"""
        test_cases = [
            ("张三先生", "张三"),
            ("李四女士", "李四"),
            ("王五总", "王五"),
            ("赵六", "赵六"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = self.detector._clean_name(original)
                self.assertEqual(result, expected)
    
    def test_extract_core_address(self):
        """测试地址核心提取"""
        test_cases = [
            ("北京市朝阳区某小区1号楼2单元301", "北京市朝阳区某小区"),
            ("上海市浦东新区某花园3栋", "上海市浦东新区某花园"),
            ("广州市天河区某大厦", "广州市天河区某大厦"),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                result = self.detector._extract_core_address(original)
                self.assertIn(expected.split('某')[1] if '某' in expected else expected, result)


class GitHubServiceTest(TestCase):
    """GitHub服务测试"""

    def setUp(self):
        # 使用真实的GitHub配置进行测试
        self.service = GitHubService()
    
    @patch.object(GitHubService, '__init__', lambda x: None)
    @patch('github.Github')
    def test_get_file_content(self, mock_github):
        """测试获取GitHub文件内容"""
        # 创建服务实例并设置属性
        service = GitHubService()
        service.github_token = 'test_token'
        service.github_repo = 'test/repo'
        service.github = mock_github.return_value
        service.base64 = __import__('base64')

        # 模拟GitHub API响应
        mock_repo = MagicMock()
        mock_file = MagicMock()
        mock_file.content = "dGVzdCBjb250ZW50"  # base64编码的"test content"
        mock_file.sha = "abc123"
        mock_repo.get_contents.return_value = mock_file
        mock_github.return_value.get_repo.return_value = mock_repo

        content, sha = service.get_file_content("to csv/1月.csv")

        self.assertEqual(content, "test content")
        self.assertEqual(sha, "abc123")
    
    def test_submit_to_github(self):
        """测试提交到GitHub"""
        # 模拟GitHub API响应
        with patch.object(self.service, 'github') as mock_github:
            mock_repo = MagicMock()
            mock_commit_result = {
                'commit': MagicMock()
            }
            mock_commit_result['commit'].sha = "def456"
            mock_repo.create_file.return_value = mock_commit_result
            mock_github.get_repo.return_value = mock_repo

            # 模拟get_file_content返回空内容（新文件）
            with patch.object(self.service, 'get_file_content', return_value=("", "")):
                result = self.service.submit_to_github("to csv/1月.csv", "test,data")

            self.assertTrue(result['success'])
            self.assertIn("成功添加记录", result['message'])


class WechatCsvAPITest(APITestCase):
    """微信CSV API测试"""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('wechat_csv:login')
        self.process_url = reverse('wechat_csv:process')
        self.update_table_url = reverse('wechat_csv:update_table')
        self.submit_url = reverse('wechat_csv:submit')
        self.logout_url = reverse('wechat_csv:logout')

    def test_login_success(self):
        """测试登录成功"""
        data = {'password': settings.WECHAT_CSV_PASSWORD}
        response = self.client.post(self.login_url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(self.client.session.get('wechat_csv_authenticated'))

    def test_login_failure(self):
        """测试登录失败"""
        data = {'password': 'wrong_password'}
        response = self.client.post(self.login_url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.client.session.get('wechat_csv_authenticated'))

    def test_login_lockout(self):
        """测试登录锁定"""
        # 连续失败登录
        data = {'password': 'wrong_password'}
        for _ in range(settings.WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT):
            response = self.client.post(self.login_url, json.dumps(data), content_type='application/json')

        # 再次尝试应该被锁定
        response = self.client.post(self.login_url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def _login(self):
        """辅助方法：登录"""
        data = {'password': settings.WECHAT_CSV_PASSWORD}
        self.client.post(self.login_url, json.dumps(data), content_type='application/json')

    @patch('apps.wechat_csv.services.WechatMessageProcessor.format_wechat_message')
    @patch('apps.wechat_csv.services.GitHubService.get_file_content')
    def test_process_message(self, mock_get_file, mock_format):
        """测试处理微信消息"""
        self._login()

        # 模拟服务响应
        mock_format.return_value = "张三,13800138000,北京市朝阳区某小区,国标,5000,100,2024-01-15,5,{除醛宝:2}"
        mock_get_file.return_value = ("", "")

        data = {
            'wechat_text': """
            客户信息：
            姓名：张三
            电话：13800138000
            地址：北京市朝阳区某小区
            检测类型：国标
            成交金额：5000元
            面积：100平方米
            履约时间：2024年1月15日
            """
        }

        response = self.client.post(self.process_url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('table_data', response.data)
        self.assertIn('validation', response.data)
        self.assertIn('csv_filename', response.data)

        # 验证数据库记录
        self.assertTrue(ProcessingHistory.objects.exists())
        self.assertTrue(WechatCsvRecord.objects.exists())

    def test_process_message_unauthorized(self):
        """测试未授权处理消息"""
        data = {'wechat_text': 'test message'}
        response = self.client.post(self.process_url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_table(self):
        """测试更新表格数据"""
        self._login()

        data = {
            'table_data': [{
                '客户姓名': '张三',
                '客户电话': '13800138000',
                '客户地址': '北京市朝阳区某小区',
                '商品类型': '国标',
                '成交金额': '5000',
                '面积': '100',
                '履约时间': '2024-01-15',
                'CMA点位数量': '5',
                '备注赠品': '{除醛宝:2}'
            }]
        }

        response = self.client.post(self.update_table_url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('validation', response.data)
        self.assertIn('csv_content', response.data)

    @patch('apps.wechat_csv.services.GitHubService.submit_to_github')
    def test_submit_to_github(self, mock_submit):
        """测试提交到GitHub"""
        self._login()

        # 模拟GitHub服务响应
        mock_submit.return_value = {
            'success': True,
            'message': '成功添加记录到 to csv/1月.csv',
            'commit_info': {'sha': 'abc123'},
            'file_path': 'to csv/1月.csv'
        }

        data = {
            'csv_filename': 'to csv/1月.csv',
            'csv_content': '张三,13800138000,北京市朝阳区某小区,国标,5000,100,2024-01-15,5,{除醛宝:2}'
        }

        response = self.client.post(self.submit_url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_logout(self):
        """测试登出"""
        self._login()

        response = self.client.post(self.logout_url, content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(self.client.session.get('wechat_csv_authenticated'))


class ModelTest(TestCase):
    """模型测试"""

    def test_wechat_csv_record_creation(self):
        """测试CSV记录创建"""
        record = WechatCsvRecord.objects.create(
            customer_name='张三',
            customer_phone='13800138000',
            customer_address='北京市朝阳区某小区',
            product_type='国标',
            transaction_amount=5000.00,
            area=100.00,
            cma_points='5',
            gift_notes='{除醛宝:2}'
        )

        self.assertEqual(record.customer_name, '张三')
        self.assertEqual(record.customer_phone, '13800138000')
        self.assertEqual(record.transaction_amount, 5000.00)
        self.assertIn('张三', str(record))

    def test_processing_history_creation(self):
        """测试处理历史创建"""
        history = ProcessingHistory.objects.create(
            original_message='test message',
            formatted_csv='test,csv',
            status='completed'
        )

        self.assertEqual(history.original_message, 'test message')
        self.assertEqual(history.status, 'completed')
        self.assertEqual(history.records_count, 0)

    def test_validation_result_creation(self):
        """测试验证结果创建"""
        history = ProcessingHistory.objects.create(
            original_message='test message',
            status='completed'
        )

        validation = ValidationResult.objects.create(
            processing_history=history,
            is_valid=True,
            errors=[],
            warnings=[]
        )

        self.assertTrue(validation.is_valid)
        self.assertEqual(len(validation.errors), 0)

    def test_login_attempt_creation(self):
        """测试登录尝试创建"""
        attempt = LoginAttempt.objects.create(
            ip_address='127.0.0.1',
            attempts=1
        )

        self.assertEqual(attempt.ip_address, '127.0.0.1')
        self.assertEqual(attempt.attempts, 1)
        self.assertFalse(attempt.is_locked)
