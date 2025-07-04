"""
核心服务模块测试用例

基于GUI项目的实际业务场景设计，验证核心服务功能与原程序的一致性
"""
import os
from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from fuzzywuzzy import fuzz

from apps.core.services import AddressMatchingService, PointMemoryService, DataFilterService

User = get_user_model()


class AddressMatchingServiceTestCase(TestCase):
    """地址匹配服务测试用例"""
    
    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.service = AddressMatchingService()
        
        # 测试地址数据（基于GUI项目的真实地址）
        self.test_addresses = [
            {
                'csv_address': '北京市朝阳区建国路88号SOHO现代城A座1501室',
                'log_address': '北京市朝阳区建国路88号SOHO现代城A座1501室',
                'expected_similarity': 1.0
            },
            {
                'csv_address': '北京市朝阳区建国路88号SOHO现代城A座1501室',
                'log_address': '北京市朝阳区建国路88号SOHO现代城',
                'expected_similarity': 0.85
            },
            {
                'csv_address': '北京市海淀区中关村大街1号海龙大厦B座2301室',
                'log_address': '北京市海淀区中关村大街1号海龙大厦',
                'expected_similarity': 0.9
            },
            {
                'csv_address': '上海市浦东新区世纪大道1000号某某大厦A座2501室',
                'log_address': '北京市朝阳区建国路88号SOHO现代城',
                'expected_similarity': 0.2
            }
        ]
    
    def test_calculate_address_similarity(self):
        """测试地址相似度计算（移植GUI项目的地址匹配算法）"""
        for test_case in self.test_addresses:
            similarity = self.service.calculate_address_similarity(
                test_case['csv_address'],
                test_case['log_address']
            )

            # 验证相似度在预期范围内（转换为0-1范围）
            expected_similarity = test_case['expected_similarity'] * 100  # 转换为0-100范围
            self.assertAlmostEqual(
                similarity,
                expected_similarity,
                delta=15.0,  # 允许15分的误差
                msg=f"地址相似度计算错误: {test_case['csv_address']} vs {test_case['log_address']}"
            )
    
    def test_address_cleaning(self):
        """测试地址清理功能"""
        test_cases = [
            {
                'input': '收货地址:北京市朝阳区建国路88号SOHO现代城A座1501室',
                'expected': '北京市朝阳区建国路88号SOHO现代城A座1501室'
            },
            {
                'input': '  地址: 上海市浦东新区世纪大道1000号  ',
                'expected': '上海市浦东新区世纪大道1000号'
            }
        ]

        for test_case in test_cases:
            cleaned = self.service.clean_address(test_case['input'])
            self.assertEqual(cleaned, test_case['expected'])

    def test_batch_address_matching(self):
        """测试批量地址匹配"""
        csv_addresses = [
            "北京市朝阳区建国路88号SOHO现代城A座1501室",
            "北京市海淀区中关村大街1号海龙大厦B座2301室"
        ]

        log_addresses = [
            "北京市朝阳区建国路88号SOHO现代城",
            "北京市海淀区中关村大街1号海龙大厦"
        ]

        # 执行批量匹配
        matches = self.service.match_addresses(csv_addresses, log_addresses)

        # 验证匹配结果
        self.assertEqual(len(matches), 2)

        for match in matches:
            self.assertIn('csv_address', match)
            self.assertIn('log_address', match)
            self.assertIn('similarity_score', match)
            self.assertIn('is_matched', match)
            self.assertGreater(match['similarity_score'], 70.0)


class PointMemoryServiceTestCase(TestCase):
    """点位记忆服务测试用例"""

    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.service = PointMemoryService()
        
        # 测试点位数据（基于GUI项目的真实点位名称）
        self.test_points_data = [
            {
                'points': {'客厅': 0.085, '主卧': 0.092, '次卧': 0.078, '厨房': 0.065},
                'expected_suggestions': ['书房', '卫生间', '阳台']
            },
            {
                'points': {'living_room': 0.085, 'bedroom1': 0.092, 'bedroom2': 0.078},
                'expected_suggestions': ['客厅', '主卧', '次卧']
            },
            {
                'points': {'房间1': 0.085, '房间2': 0.092, '房间3': 0.078},
                'expected_suggestions': ['客厅', '主卧', '次卧', '厨房']
            }
        ]
    
    def test_point_memory_update(self):
        """测试点位记忆更新"""
        # 清空之前的记忆
        self.service.point_memory.clear()

        # 更新点位数据
        points_data = {'客厅': 0.085, '主卧': 0.092, '次卧': 0.078, '厨房': 0.065}

        self.service.update_points(points_data)

        # 验证点位记忆已更新
        memory = self.service.point_memory

        # 验证点位名称已记录
        for point_name in points_data.keys():
            self.assertIn(point_name, memory)
            self.assertEqual(memory[point_name]['count'], 1)
            self.assertIn(points_data[point_name], memory[point_name]['values'])
    
    def test_point_suggestions(self):
        """测试点位建议"""
        # 先更新一些点位数据
        self.service.update_points({'客厅': 0.085, '主卧': 0.092, '次卧': 0.078, '厨房': 0.065})

        # 获取点位建议
        suggestions = self.service.get_point_suggestions('客', limit=3)

        # 验证建议结果
        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 3)

        # 验证建议包含相关点位
        if suggestions:
            self.assertTrue(any('客' in suggestion for suggestion in suggestions))
    
    def test_point_memory_persistence(self):
        """测试点位记忆持久化"""
        # 清空之前的记忆
        self.service.point_memory.clear()

        # 更新点位数据
        points_data = {'客厅': 0.085, '主卧': 0.092}
        self.service.update_points(points_data)

        # 验证数据已保存到内存
        memory = self.service.point_memory
        self.assertIn('客厅', memory)
        self.assertIn('主卧', memory)

        # 验证统计信息
        self.assertEqual(memory['客厅']['count'], 1)
        self.assertEqual(memory['主卧']['count'], 1)
        self.assertAlmostEqual(memory['客厅']['avg_value'], 0.085, places=3)
        self.assertAlmostEqual(memory['主卧']['avg_value'], 0.092, places=3)


class DataFilterServiceTestCase(TestCase):
    """数据筛选服务测试用例"""

    def setUp(self):
        """测试数据准备"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.service = DataFilterService()
        
        # 测试数据
        self.csv_data = [
            {'姓名': '张三', '电话': '13812345678', '地址': '北京市朝阳区某某小区', '日期': '2024-12-01'},
            {'姓名': '李四', '电话': '13987654321', '地址': '北京市海淀区某某花园', '日期': '2024-12-02'},
            {'姓名': '王五', '电话': '13612345678', '地址': '北京市西城区某某大厦', '日期': '2024-12-03'},
            {'姓名': '赵六', '电话': '13712345678', '地址': '北京市东城区某某胡同', '日期': '2024-12-04'},
        ]
        
        self.log_data = [
            {'姓名': '张三', '电话': '13812345678', '地址': '北京市朝阳区某某小区', '检测类型': '初检', '日期': '2024-12-01'},
            {'姓名': '李四', '电话': '13987654321', '地址': '北京市海淀区某某花园', '检测类型': '初检', '日期': '2024-12-02'},
            {'姓名': '王五', '电话': '13612345678', '地址': '北京市西城区某某大厦', '检测类型': '复检', '日期': '2024-12-03'},
        ]
    
    def test_date_range_filtering_basic(self):
        """测试基本日期范围筛选"""
        # 筛选12月的数据
        filtered_data = self.service.filter_by_date_range(
            self.csv_data,
            date_field='日期',
            month_filter='12月'
        )

        # 验证筛选结果
        self.assertEqual(len(filtered_data), 4)  # 所有数据都是12月的

        for record in filtered_data:
            self.assertIn('2024-12', record['日期'])
    
    def test_date_matching(self):
        """测试日期匹配功能"""
        # 测试日期匹配逻辑
        test_date = "2024-12-01"
        month_filter = "12月"

        # 使用内部方法测试日期匹配
        result = self.service._match_date_filter(test_date, month_filter, False)
        self.assertTrue(result)

        # 测试不匹配的情况
        test_date2 = "2024-11-01"
        result2 = self.service._match_date_filter(test_date2, month_filter, False)
        self.assertFalse(result2)
