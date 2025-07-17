"""
Test suite for JSON format order records
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date
import json
from unittest.mock import patch, MagicMock

from apps.ocr.models import CSVRecord
from apps.orders.serializers import OrderRecordSerializer

User = get_user_model()


class OrderRecordModelTestCase(TestCase):
    """Test the CSVRecord model with JSON format"""

    def setUp(self):
        self.test_data = {
            '客户姓名': '张三',
            '客户电话': '13812345678',
            '客户地址': '北京市朝阳区某某小区',
            '商品类型': '国标',
            '成交金额': Decimal('5000.00'),
            '面积': '100',
            '履约时间': date(2024, 1, 15),
            'CMA点位数量': '5',
            '备注赠品': {'除醛宝': 15, '炭包': 3}
        }

    def test_create_record_with_json_gifts(self):
        """Test creating record with JSON format gifts"""
        record = CSVRecord.objects.create(**self.test_data)
        
        self.assertEqual(record.客户姓名, '张三')
        self.assertEqual(record.备注赠品, {'除醛宝': 15, '炭包': 3})
        self.assertIsInstance(record.备注赠品, dict)

    def test_empty_gifts_default_to_dict(self):
        """Test that empty gifts default to empty dict"""
        data = self.test_data.copy()
        data['备注赠品'] = {}
        
        record = CSVRecord.objects.create(**data)
        self.assertEqual(record.备注赠品, {})
        self.assertIsInstance(record.备注赠品, dict)

    def test_complex_gifts_format(self):
        """Test complex gifts with multiple items"""
        complex_gifts = {
            '除醛宝': 20,
            '炭包': 5,
            '除醛机': 2,
            '除醛喷雾': 3
        }
        
        data = self.test_data.copy()
        data['备注赠品'] = complex_gifts
        
        record = CSVRecord.objects.create(**data)
        self.assertEqual(record.备注赠品, complex_gifts)


class OrderRecordSerializerTestCase(TestCase):
    """Test the OrderRecordSerializer with JSON format"""

    def setUp(self):
        self.valid_data = {
            '客户姓名': '李四',
            '客户电话': '13900139000',
            '客户地址': '上海市浦东新区',
            '商品类型': '母婴',
            '成交金额': 3000,
            '面积': '80',
            '履约时间': '2024-02-15',
            'CMA点位数量': '3',
            '备注赠品': {'除醛宝': 10, '炭包': 5}
        }

    def test_valid_serializer(self):
        """Test serializer with valid data"""
        serializer = OrderRecordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        record = serializer.save()
        self.assertEqual(record.客户姓名, '李四')
        self.assertEqual(record.备注赠品, {'除醛宝': 10, '炭包': 5})

    def test_gift_type_validation(self):
        """Test gift type validation"""
        invalid_data = self.valid_data.copy()
        invalid_data['备注赠品'] = {'无效赠品': 5}
        
        serializer = OrderRecordSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('备注赠品', serializer.errors)
        self.assertIn('不支持的赠品类型', str(serializer.errors['备注赠品']))

    def test_gift_quantity_validation(self):
        """Test gift quantity validation"""
        invalid_data = self.valid_data.copy()
        invalid_data['备注赠品'] = {'除醛宝': -5}
        
        serializer = OrderRecordSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('备注赠品', serializer.errors)
        self.assertIn('赠品数量必须是非负整数', str(serializer.errors['备注赠品']))

    def test_gift_format_validation(self):
        """Test gift format validation"""
        invalid_data = self.valid_data.copy()
        invalid_data['备注赠品'] = "invalid string format"
        
        serializer = OrderRecordSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('备注赠品', serializer.errors)

    def test_phone_validation(self):
        """Test phone number validation"""
        invalid_data = self.valid_data.copy()
        invalid_data['客户电话'] = '123456'
        
        serializer = OrderRecordSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('客户电话', serializer.errors)

    def test_product_type_validation(self):
        """Test product type validation"""
        invalid_data = self.valid_data.copy()
        invalid_data['商品类型'] = '无效类型'
        
        serializer = OrderRecordSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('商品类型', serializer.errors)

    def test_serializer_output(self):
        """Test serializer output format"""
        record = CSVRecord.objects.create(**{
            '客户姓名': '王五',
            '客户电话': '13700137000',
            '客户地址': '广州市天河区',
            '商品类型': '国标',
            '成交金额': Decimal('4000.00'),
            '备注赠品': {'除醛宝': 8, '炭包': 2, '除醛机': 1}
        })
        
        serializer = OrderRecordSerializer(record)
        data = serializer.data
        
        self.assertEqual(data['客户姓名'], '王五')
        self.assertEqual(data['备注赠品'], {'除醛宝': 8, '炭包': 2, '除醛机': 1})
        self.assertIsInstance(data['备注赠品'], dict)


class OrderInfoProcessorTestCase(TestCase):
    """Test the OrderInfoProcessor with JSON format"""

    @patch('apps.orders.services.ai_service_manager')
    def test_extract_gift_notes_to_dict(self, mock_ai_service):
        """Test gift extraction returns dict format"""
        # Mock AI service manager
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        
        test_text = "赠品：除醛宝15个，炭包3个，除醛机1台"
        result = processor._extract_gift_notes(test_text)
        
        expected = {'除醛宝': 15, '炭包': 3, '除醛机': 1}
        self.assertEqual(result, expected)
        self.assertIsInstance(result, dict)

    @patch('apps.orders.services.ai_service_manager')
    def test_parse_gift_text_to_dict(self, mock_ai_service):
        """Test parsing old format gift text to dict"""
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        
        # Test old format
        old_format = "{除醛宝:15;炭包:3}"
        result = processor._parse_gift_text_to_dict(old_format)
        
        expected = {'除醛宝': 15, '炭包': 3}
        self.assertEqual(result, expected)

    @patch('apps.orders.services.ai_service_manager')
    def test_local_format_order_message_returns_dict(self, mock_ai_service):
        """Test local format returns dict with JSON gifts"""
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        
        order_text = """
        客户：张三
        电话：13812345678
        地址：北京市朝阳区
        金额：5000元
        面积：100平方米
        履约时间：2024-01-15
        CMA点位：5个
        赠品：除醛宝15个，炭包3个
        """
        
        result = processor._local_format_order_message(order_text)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['客户姓名'], '张三')
        self.assertEqual(result['备注赠品'], {'除醛宝': 15, '炭包': 3})
        self.assertIsInstance(result['备注赠品'], dict)

    @patch('apps.orders.services.ai_service_manager')
    def test_validate_order_data_with_json_gifts(self, mock_ai_service):
        """Test order data validation with JSON gifts"""
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        
        valid_data = {
            '客户姓名': '李四',
            '客户电话': '13900139000',
            '备注赠品': {'除醛宝': 10, '炭包': 5}
        }
        
        errors = processor._validate_order_data(valid_data)
        self.assertEqual(errors, [])

    @patch('apps.orders.services.ai_service_manager')
    def test_validate_order_data_with_invalid_gifts(self, mock_ai_service):
        """Test validation with invalid gift data"""
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        
        invalid_data = {
            '客户姓名': '王五',
            '备注赠品': {'无效赠品': 5}
        }
        
        errors = processor._validate_order_data(invalid_data)
        self.assertTrue(any('不支持的赠品类型' in error for error in errors))


class OrderAPITestCase(APITestCase):
    """Test Order API endpoints with JSON format"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_submit_order_with_json_gifts(self):
        """Test submitting order with JSON format gifts"""
        order_data = {
            'order_data': {
                '客户姓名': '赵六',
                '客户电话': '13600136000',
                '客户地址': '深圳市南山区',
                '商品类型': '母婴',
                '成交金额': '2500',
                '面积': '60',
                '履约时间': '2024-03-10',
                'CMA点位数量': '4',
                '备注赠品': {'除醛宝': 12, '炭包': 4}
            }
        }
        
        response = self.client.post('/api/v1/orders/submit/', order_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check the created record
        record = CSVRecord.objects.get(客户姓名='赵六')
        self.assertEqual(record.备注赠品, {'除醛宝': 12, '炭包': 4})
        self.assertIsInstance(record.备注赠品, dict)

    def test_order_records_list_api(self):
        """Test order records list API returns JSON format"""
        # Create test record
        CSVRecord.objects.create(
            客户姓名='测试用户',
            客户电话='13800138000',
            客户地址='测试地址',
            商品类型='国标',
            成交金额=Decimal('1000.00'),
            备注赠品={'除醛宝': 5, '炭包': 2},
            created_by=self.user
        )
        
        response = self.client.get('/api/v1/orders/records/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        record_data = response.data['results'][0]
        self.assertEqual(record_data['客户姓名'], '测试用户')
        self.assertEqual(record_data['备注赠品'], {'除醛宝': 5, '炭包': 2})
        self.assertIsInstance(record_data['备注赠品'], dict)

    def test_submit_order_with_invalid_gifts(self):
        """Test submitting order with invalid gift data"""
        order_data = {
            'order_data': {
                '客户姓名': '无效测试',
                '客户电话': '13500135000',
                '备注赠品': {'无效赠品': 5}
            }
        }
        
        response = self.client.post('/api/v1/orders/submit/', order_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('apps.orders.services.ai_service_manager')
    def test_process_order_returns_json_format(self, mock_ai_service):
        """Test process order API returns JSON format"""
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        # Test the local processing fallback
        order_text = """
        客户：本地测试
        电话：13400134000
        地址：测试城市
        赠品：除醛宝10个
        """
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        result = processor._local_format_order_message(order_text)
        
        self.assertIsInstance(result, dict)
        self.assertIn('备注赠品', result)
        self.assertIsInstance(result['备注赠品'], dict)


class MigrationTestCase(TestCase):
    """Test data migration from old format to new format"""

    @patch('apps.orders.services.ai_service_manager')
    def test_gift_text_to_json_conversion(self, mock_ai_service):
        """Test conversion from old text format to JSON"""
        mock_ai_service.get_current_service_config.return_value = {
            'name': 'test',
            'api_format': 'openai',
            'api_key': 'test-key',
            'api_base_url': 'http://test.com',
            'model_name': 'test-model'
        }
        
        from apps.orders.services import OrderInfoProcessor
        processor = OrderInfoProcessor()
        
        # Test various old formats
        test_cases = [
            ('{除醛宝:15;炭包:3}', {'除醛宝': 15, '炭包': 3}),
            ('{除醛机:1}', {'除醛机': 1}),
            ('', {}),
            ('invalid format', {}),
        ]
        
        for old_format, expected in test_cases:
            result = processor._parse_gift_text_to_dict(old_format)
            self.assertEqual(result, expected, f"Failed for input: {old_format}")


if __name__ == '__main__':
    pytest.main([__file__])