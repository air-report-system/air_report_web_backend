"""
Tests for order export functionality
"""
import csv
import io
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from apps.ocr.models import CSVRecord


class OrderExportViewTest(TestCase):
    """测试订单导出功能"""
    
    def setUp(self):
        """设置测试数据"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # 创建测试订单数据
        self.test_records = [
            CSVRecord.objects.create(
                客户姓名='张三',
                客户电话='13800138001',
                客户地址='北京市朝阳区测试地址1号',
                商品类型='国标',
                成交金额=Decimal('1500.00'),
                面积='100',
                履约时间=date(2024, 1, 15),
                CMA点位数量='5',
                备注赠品='赠送检测报告',
                created_by=self.user
            ),
            CSVRecord.objects.create(
                客户姓名='李四',
                客户电话='13800138002',
                客户地址='上海市浦东新区测试地址2号',
                商品类型='母婴',
                成交金额=Decimal('2000.00'),
                面积='120',
                履约时间=date(2024, 1, 20),
                CMA点位数量='6',
                备注赠品='',
                created_by=self.user
            ),
            # 不同月份的数据（用于测试筛选）
            CSVRecord.objects.create(
                客户姓名='王五',
                客户电话='13800138003',
                客户地址='广州市天河区测试地址3号',
                商品类型='国标',
                成交金额=Decimal('1800.00'),
                面积='110',
                履约时间=date(2024, 2, 10),
                CMA点位数量='5',
                备注赠品='赠送甲醛检测仪',
                created_by=self.user
            )
        ]
    
    def test_export_success(self):
        """测试成功导出CSV"""
        url = reverse('orders:order-export')
        response = self.client.get(url, {'month': '2024-01'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
        
        # 验证CSV内容
        content = response.content.decode('utf-8-sig')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # 验证头部
        headers = rows[0]
        expected_headers = [
            '订单ID', '客户姓名', '客户电话', '客户地址', '商品类型',
            '成交金额', '面积', '履约时间', 'CMA点位数量', '备注赠品', '创建时间'
        ]
        self.assertEqual(headers, expected_headers)
        
        # 验证数据行数（应该有2条2024年1月的记录）
        data_rows = rows[1:]
        self.assertEqual(len(data_rows), 2)
        
        # 验证第一条记录的内容
        first_row = data_rows[0]
        self.assertEqual(first_row[1], '张三')  # 客户姓名
        self.assertEqual(first_row[2], '13800138001')  # 客户电话
        self.assertEqual(first_row[4], '国标')  # 商品类型
        self.assertEqual(first_row[5], '1500.0')  # 成交金额
        self.assertEqual(first_row[7], '2024-01-15')  # 履约时间
    
    def test_export_missing_month_parameter(self):
        """测试缺少month参数"""
        url = reverse('orders:order-export')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('缺少month参数', response.data['error'])
    
    def test_export_invalid_month_format(self):
        """测试无效的月份格式"""
        url = reverse('orders:order-export')
        
        # 测试无效格式
        response = self.client.get(url, {'month': '2024/01'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('month参数格式错误', response.data['error'])
        
        # 测试无效月份
        response = self.client.get(url, {'month': '2024-13'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('month参数格式错误', response.data['error'])
    
    def test_export_no_data(self):
        """测试没有数据的月份"""
        url = reverse('orders:order-export')
        response = self.client.get(url, {'month': '2024-03'})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('没有订单数据', response.data['error'])
    
    def test_export_unauthenticated(self):
        """测试未认证用户"""
        self.client.force_authenticate(user=None)
        url = reverse('orders:order-export')
        response = self.client.get(url, {'month': '2024-01'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_export_inactive_records_excluded(self):
        """测试不导出已删除的记录"""
        # 软删除一条记录
        self.test_records[0].is_active = False
        self.test_records[0].save()
        
        url = reverse('orders:order-export')
        response = self.client.get(url, {'month': '2024-01'})
        
        # 验证CSV内容只包含1条记录（排除了软删除的记录）
        content = response.content.decode('utf-8-sig')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        data_rows = rows[1:]
        
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0][1], '李四')  # 确认是李四的记录