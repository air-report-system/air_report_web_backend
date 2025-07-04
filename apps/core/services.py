"""
核心服务模块 - 移植自GUI项目的各种工具函数
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from django.conf import settings
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)


class PointMemoryService:
    """
    点位学习服务 - 移植自GUI项目的point_memory.py
    """
    
    def __init__(self):
        self.memory_file = Path(settings.BASE_DIR) / 'data' / 'point_memory.json'
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.point_memory = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """加载点位记忆数据"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"加载点位记忆失败: {e}")
            return {}
    
    def _save_memory(self):
        """保存点位记忆数据"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.point_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存点位记忆失败: {e}")
    
    def update_points(self, points_data: Dict[str, Any]):
        """
        更新点位学习数据 - 移植自GUI项目的update_points函数
        
        Args:
            points_data: 点位数据字典 {点位名称: 数值}
        """
        try:
            for point_name, point_value in points_data.items():
                if point_name not in self.point_memory:
                    self.point_memory[point_name] = {
                        'count': 0,
                        'values': [],
                        'avg_value': 0.0
                    }
                
                # 更新统计信息
                memory_item = self.point_memory[point_name]
                memory_item['count'] += 1
                
                try:
                    value_float = float(point_value)
                    memory_item['values'].append(value_float)
                    
                    # 保持最近100个值
                    if len(memory_item['values']) > 100:
                        memory_item['values'] = memory_item['values'][-100:]
                    
                    # 计算平均值
                    memory_item['avg_value'] = sum(memory_item['values']) / len(memory_item['values'])
                    
                except (ValueError, TypeError):
                    logger.warning(f"点位值转换失败: {point_name}={point_value}")
            
            # 保存更新后的数据
            self._save_memory()
            logger.info(f"点位学习数据已更新，共 {len(points_data)} 个点位")
            
        except Exception as e:
            logger.error(f"点位学习更新失败: {e}")
    
    def get_point_suggestions(self, partial_name: str, limit: int = 5) -> List[str]:
        """获取点位名称建议"""
        try:
            suggestions = []
            for point_name in self.point_memory.keys():
                if partial_name.lower() in point_name.lower():
                    suggestions.append(point_name)
            
            # 按相似度排序
            suggestions.sort(key=lambda x: fuzz.ratio(partial_name, x), reverse=True)
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"获取点位建议失败: {e}")
            return []


class AddressMatchingService:
    """
    地址匹配服务 - 移植自GUI项目的地址匹配算法
    """
    
    @staticmethod
    def clean_address(address: str) -> str:
        """
        清理地址字符串 - 移植自GUI项目的地址清洗逻辑
        
        Args:
            address: 原始地址
            
        Returns:
            str: 清理后的地址
        """
        if not address:
            return ""
        
        # 移除常见的干扰词
        noise_words = [
            "收货地址:", "地址:", "详细地址:", "送货地址:",
            "联系地址:", "收件地址:", "配送地址:", "寄送地址:",
            "请填写详细地址", "具体地址", "准确地址"
        ]
        
        cleaned = address
        for noise in noise_words:
            cleaned = cleaned.replace(noise, "")
        
        # 移除多余的空格和标点
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    @staticmethod
    def calculate_address_similarity(addr1: str, addr2: str) -> float:
        """
        计算地址相似度 - 移植自GUI项目的相似度算法
        
        Args:
            addr1: 地址1
            addr2: 地址2
            
        Returns:
            float: 相似度分数 (0-100)
        """
        if not addr1 or not addr2:
            return 0.0
        
        # 清理地址
        clean_addr1 = AddressMatchingService.clean_address(addr1)
        clean_addr2 = AddressMatchingService.clean_address(addr2)
        
        # 计算多种相似度
        ratio = fuzz.ratio(clean_addr1, clean_addr2)
        partial_ratio = fuzz.partial_ratio(clean_addr1, clean_addr2)
        token_sort_ratio = fuzz.token_sort_ratio(clean_addr1, clean_addr2)
        token_set_ratio = fuzz.token_set_ratio(clean_addr1, clean_addr2)
        
        # 取最高分
        max_similarity = max(ratio, partial_ratio, token_sort_ratio, token_set_ratio)
        
        return max_similarity
    
    @staticmethod
    def match_addresses(csv_addresses: List[str], log_addresses: List[str], 
                       threshold: float = 80.0) -> List[Dict[str, Any]]:
        """
        批量地址匹配 - 移植自GUI项目的双向筛选逻辑
        
        Args:
            csv_addresses: CSV中的地址列表
            log_addresses: 日志中的地址列表
            threshold: 相似度阈值
            
        Returns:
            List[Dict]: 匹配结果列表
        """
        matches = []
        
        for csv_addr in csv_addresses:
            best_match = None
            best_score = 0.0
            
            for log_addr in log_addresses:
                score = AddressMatchingService.calculate_address_similarity(csv_addr, log_addr)
                
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = log_addr
            
            matches.append({
                'csv_address': csv_addr,
                'log_address': best_match,
                'similarity_score': best_score,
                'is_matched': best_match is not None
            })
        
        return matches


class PhoneMatchingService:
    """
    电话号码匹配服务 - 移植自GUI项目的电话匹配逻辑
    """
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        标准化电话号码
        
        Args:
            phone: 原始电话号码
            
        Returns:
            str: 标准化后的电话号码
        """
        if not phone:
            return ""
        
        # 移除所有非数字字符
        digits_only = re.sub(r'\D', '', phone)
        
        # 处理不同格式的电话号码
        if len(digits_only) == 11 and digits_only.startswith('1'):
            return digits_only
        elif len(digits_only) == 10:
            return '1' + digits_only
        elif len(digits_only) > 11:
            # 可能包含国家代码，取后11位
            return digits_only[-11:]
        
        return digits_only
    
    @staticmethod
    def match_phones(phone1: str, phone2: str) -> bool:
        """
        匹配两个电话号码
        
        Args:
            phone1: 电话号码1
            phone2: 电话号码2
            
        Returns:
            bool: 是否匹配
        """
        norm_phone1 = PhoneMatchingService.normalize_phone(phone1)
        norm_phone2 = PhoneMatchingService.normalize_phone(phone2)
        
        if not norm_phone1 or not norm_phone2:
            return False
        
        return norm_phone1 == norm_phone2


class DataFilterService:
    """
    数据筛选服务 - 移植自GUI项目的双向筛选功能
    """
    
    @staticmethod
    def filter_by_date_range(data: List[Dict[str, Any]], 
                           date_field: str, 
                           month_filter: str,
                           allow_cross_month: bool = False) -> List[Dict[str, Any]]:
        """
        按日期范围筛选数据
        
        Args:
            data: 数据列表
            date_field: 日期字段名
            month_filter: 月份筛选条件 (如 "5月" 或 "2024-05")
            allow_cross_month: 是否允许跨月匹配
            
        Returns:
            List[Dict]: 筛选后的数据
        """
        if not month_filter:
            return data
        
        filtered_data = []
        
        for item in data:
            date_str = item.get(date_field, "")
            if DataFilterService._match_date_filter(date_str, month_filter, allow_cross_month):
                filtered_data.append(item)
        
        return filtered_data
    
    @staticmethod
    def _match_date_filter(date_str: str, month_filter: str, allow_cross_month: bool) -> bool:
        """检查日期是否匹配筛选条件"""
        if not date_str or not month_filter:
            return True
        
        # 提取月份信息
        if "月" in month_filter:
            # 格式如 "5月"
            month_num = re.search(r'(\d+)月', month_filter)
            if month_num:
                target_month = int(month_num.group(1))
                
                # 从日期字符串中提取月份
                date_month = re.search(r'-(\d+)-', date_str)
                if date_month:
                    current_month = int(date_month.group(1))
                    
                    if allow_cross_month:
                        # 允许前后一个月
                        return abs(current_month - target_month) <= 1
                    else:
                        return current_month == target_month
        
        elif "-" in month_filter:
            # 格式如 "2024-05"
            return month_filter in date_str
        
        return True


# 全局服务实例
point_memory_service = PointMemoryService()


def update_point_memory(points_data: Dict[str, Any]):
    """更新点位学习数据的全局函数"""
    point_memory_service.update_points(points_data)
