"""
OCR处理服务
"""
import os
import json
import base64
import requests
import pandas as pd
import re
import time
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)


class OCRService:
    """OCR处理服务基类"""
    
    def __init__(self):
        self.timeout = getattr(settings, 'OCR_TIMEOUT_SECONDS', 60)
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        处理图片OCR
        
        Args:
            image_path: 图片路径
            
        Returns:
            dict: OCR结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """
        将图片编码为base64
        
        Args:
            image_path: 图片路径
            
        Returns:
            str: base64编码的图片
        """
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def parse_ocr_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析OCR响应文本

        Args:
            response_text: 响应文本

        Returns:
            dict: 解析后的结果
        """
        try:
            # 清理响应文本，移除markdown代码块标记
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]  # 移除 ```json
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]  # 移除 ```
            cleaned_text = cleaned_text.strip()

            # 尝试解析JSON
            if cleaned_text.startswith('{'):
                data = json.loads(cleaned_text)

                # 标准化数据类型
                result = {
                    'phone': str(data.get('phone', '')),
                    'date': self._normalize_date(str(data.get('date', ''))),
                    'temperature': str(data.get('temperature', '')),
                    'humidity': str(data.get('humidity', '')),
                    'check_type': str(data.get('check_type', 'initial')),
                    'points_data': data.get('points_data', {}),
                    'raw_response': response_text,
                    'confidence_score': 0.8
                }

                # 如果电话号码为空，尝试从原始文本中提取
                if not result['phone']:
                    phone_match = re.search(r'1[3-9]\d{9}', response_text)
                    if phone_match:
                        result['phone'] = phone_match.group()

                return result

            # 如果不是JSON，尝试从文本中提取信息
            return self.extract_info_from_text(response_text)

        except json.JSONDecodeError:
            # JSON解析失败，使用文本解析
            return self.extract_info_from_text(response_text)

    def _normalize_date(self, date_str: str) -> str:
        """
        标准化日期格式

        Args:
            date_str: 原始日期字符串 (如: "06-21")

        Returns:
            str: 标准化的日期字符串 (如: "2025-06-21")
        """
        if not date_str or date_str.strip() == '':
            return ''

        try:
            # 如果已经是完整日期格式，直接返回
            if len(date_str) > 7 and date_str.count('-') == 2:
                return date_str

            # 处理 MM-DD 格式
            if '-' in date_str and len(date_str) <= 5:
                from datetime import datetime
                current_year = datetime.now().year
                month, day = date_str.split('-')
                return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"

            return date_str
        except Exception:
            return date_str
    
    def extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取信息
        
        Args:
            text: 文本内容
            
        Returns:
            dict: 提取的信息
        """
        import re
        
        result = {
            'phone': '',
            'date': '',
            'temperature': '',
            'humidity': '',
            'check_type': 'initial',
            'points_data': {},
            'raw_response': text,
            'confidence_score': 0.8
        }
        
        # 提取电话号码 (11位数字)
        phone_pattern = r'1[3-9]\d{9}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            result['phone'] = phone_match.group()
        
        # 提取日期 (MM-DD格式)
        date_pattern = r'(\d{1,2})-(\d{1,2})'
        date_match = re.search(date_pattern, text)
        if date_match:
            month, day = date_match.groups()
            result['date'] = f"{month.zfill(2)}-{day.zfill(2)}"
        
        # 提取温度
        temp_pattern = r'温度[：:]\s*(\d+\.?\d*)'
        temp_match = re.search(temp_pattern, text)
        if temp_match:
            result['temperature'] = temp_match.group(1)
        
        # 提取湿度
        humidity_pattern = r'湿度[：:]\s*(\d+\.?\d*)'
        humidity_match = re.search(humidity_pattern, text)
        if humidity_match:
            result['humidity'] = humidity_match.group(1)
        
        # 提取检测类型
        if '复检' in text or '复查' in text:
            result['check_type'] = 'recheck'
        
        # 提取点位数据 (简单的数字提取)
        point_pattern = r'(\d+\.?\d*)'
        numbers = re.findall(point_pattern, text)
        
        # 过滤掉电话号码和日期中的数字，保留可能的点位值
        filtered_numbers = []
        for num in numbers:
            try:
                value = float(num)
                if 0.001 <= value <= 1.0:  # 假设点位值在这个范围内
                    filtered_numbers.append(value)
            except ValueError:
                continue
        
        # 为点位数据分配名称
        point_names = ['客厅', '主卧', '次卧', '厨房', '书房', '卫生间']
        for i, value in enumerate(filtered_numbers[:len(point_names)]):
            result['points_data'][point_names[i]] = value
        
        return result


class GeminiOCRService(OCRService):
    """Gemini OCR服务"""

    def __init__(self):
        super().__init__()
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = getattr(settings, 'GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com')
        self.model_name = getattr(settings, 'GEMINI_MODEL_NAME', 'gemini-2.0-flash-exp')

        # 代理设置已移除
        self.proxies = None

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY未设置")
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        使用Gemini处理图片OCR
        
        Args:
            image_path: 图片路径
            
        Returns:
            dict: OCR结果
        """
        try:
            logger.info(f"开始Gemini OCR处理: {image_path}")
            
            # 检查网络连接
            if not self._check_network_connectivity():
                raise Exception("网络连接不可用")
            
            # 编码图片
            image_base64 = self.encode_image_to_base64(image_path)
            logger.info(f"图片编码完成，大小: {len(image_base64)} 字符")
            
            # 构建请求
            url = f"{self.base_url}/v1beta/models/{self.model_name}:generateContent"
            
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.api_key
            }
            
            # 构建提示词
            prompt = self.build_ocr_prompt()
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            }
            
            # 发送请求 - 增加重试机制
            logger.info(f"发送请求到 {url}")

            max_retries = 3
            retry_delay = 1

            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )
                    break  # 成功则跳出重试循环
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}, {retry_delay}秒后重试...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        logger.error(f"请求失败，已达到最大重试次数: {e}")
                        raise
            
            logger.info(f"请求响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info("API响应成功，解析结果...")

                # 提取生成的文本
                if 'candidates' in response_data and response_data['candidates']:
                    candidate = response_data['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        generated_text = candidate['content']['parts'][0]['text']
                        logger.info(f"生成的文本: {generated_text[:200]}...")

                        # 解析OCR结果
                        result = self.parse_ocr_response(generated_text)
                        result['confidence_score'] = 0.9  # Gemini通常有较高的准确率

                        logger.info(f"Gemini OCR处理成功: {image_path}")
                        return result
                
                logger.error(f"Gemini响应格式异常: {response_data}")
                raise Exception("Gemini响应格式异常")
            else:
                error_msg = f"Gemini API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"网络连接错误: {e}")
            raise Exception(f"网络连接错误: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {e}")
            raise Exception(f"请求超时: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise Exception(f"请求异常: {e}")
        except Exception as e:
            logger.error(f"Gemini OCR处理失败: {e}")
            raise e
    
    def _check_network_connectivity(self) -> bool:
        """检查网络连接性"""
        try:
            # 尝试连接到Google的DNS服务器
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            try:
                # 尝试连接到备用DNS服务器
                socket.create_connection(("1.1.1.1", 53), timeout=5)
                return True
            except OSError:
                return False
    
    def build_ocr_prompt(self) -> str:
        """
        构建OCR提示词

        Returns:
            str: 提示词
        """
        return """
请仔细分析这张室内空气检测报告图片，提取以下信息并以JSON格式返回：

**重要：请特别仔细查找电话号码，它可能是手写的，位置可能在：**
- 客户姓名旁边
- 联系人信息区域
- 表格的任何位置
- 可能写得比较潦草或不清楚

1. 联系电话（11位手机号码，通常以1开头，如：17778632107、13812345678）
2. 检测日期（MM-DD格式，如：06-21）
3. 现场温度（数字，如：25）
4. 现场湿度（数字，如：60）
5. 检测类型（初检或复检）
6. 各个房间的甲醛检测数值（mg/m³）

**电话号码识别要点：**
- 仔细查看所有数字，特别是11位连续数字
- 电话号码可能分行书写或有空格
- 即使字迹不清楚也要尽力识别
- 常见格式：177 7863 2107 或 17778632107

请按以下JSON格式返回结果：
{
    "phone": "11位手机号码（如果找到的话）",
    "date": "MM-DD",
    "temperature": "温度数值",
    "humidity": "湿度数值",
    "check_type": "initial或recheck",
    "points_data": {
        "房间名称1": 数值1,
        "房间名称2": 数值2
    }
}

注意：
- 如果某项信息无法识别，请留空字符串
- 数值请保留小数点后3位
- 检测类型：初检用"initial"，复检用"recheck"
- 房间名称使用中文（如：客厅、主卧、次卧、厨房等）
"""


class OpenAIOCRService(OCRService):
    """OpenAI OCR服务（备用）"""

    def __init__(self):
        super().__init__()
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model_name = getattr(settings, 'OPENAI_MODEL_NAME', 'gpt-4-vision-preview')

        # 代理设置已移除
        self.proxies = None

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY未设置")
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        使用OpenAI处理图片OCR
        
        Args:
            image_path: 图片路径
            
        Returns:
            dict: OCR结果
        """
        try:
            # 编码图片
            image_base64 = self.encode_image_to_base64(image_path)
            
            # 构建请求
            url = f"{self.base_url}/chat/completions"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.build_ocr_prompt()
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            # 发送请求
            print(f"[DEBUG] OpenAIOCRService.process_image: 发送请求到 {url}")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                if 'choices' in response_data and response_data['choices']:
                    generated_text = response_data['choices'][0]['message']['content']
                    
                    # 解析OCR结果
                    result = self.parse_ocr_response(generated_text)
                    result['confidence_score'] = 0.85
                    
                    logger.info(f"OpenAI OCR处理成功: {image_path}")
                    return result
                
                raise Exception("OpenAI响应格式异常")
            else:
                error_msg = f"OpenAI API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"OpenAI OCR处理失败: {e}")
            raise e
    
    def build_ocr_prompt(self) -> str:
        """构建OCR提示词"""
        return GeminiOCRService().build_ocr_prompt()  # 使用相同的提示词


class EnhancedOCRService:
    """增强的OCR服务，集成原项目功能"""

    def __init__(self):
        self.timeout = getattr(settings, 'OCR_TIMEOUT_SECONDS', 60)
        self.base_service = get_ocr_service()

    def process_image_multi_ocr(self, image_path: str, ocr_count: int = 3) -> Dict[str, Any]:
        """
        多重OCR处理，提高准确性

        Args:
            image_path: 图片路径
            ocr_count: OCR尝试次数

        Returns:
            dict: 包含最佳结果和冲突分析的OCR结果
        """
        results = []

        # 执行多次OCR
        for i in range(ocr_count):
            try:
                result = self.base_service.process_image(image_path)
                result['attempt'] = i + 1
                results.append(result)

                # 短暂延迟避免API限制
                if i < ocr_count - 1:
                    time.sleep(1)

            except Exception as e:
                logger.warning(f"OCR尝试 {i+1} 失败: {e}")
                continue

        if not results:
            raise Exception("所有OCR尝试都失败了")

        # 分析差异和选择最佳结果
        analysis = self._analyze_ocr_differences(results)
        best_result = self._select_best_result(results, analysis)

        return {
            'best_result': best_result,
            'all_results': results,
            'analysis': analysis,
            'has_conflicts': analysis.get('has_differences', False),
            'ocr_attempts': len(results)
        }

    def _analyze_ocr_differences(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析多个OCR结果的差异"""
        if len(results) <= 1:
            return {'has_differences': False, 'conflicts': {}}

        conflicts = {}
        fields_to_check = ['phone', 'date', 'temperature', 'humidity', 'check_type']

        for field in fields_to_check:
            values = [result.get(field, '') for result in results]
            unique_values = list(set(filter(None, values)))

            if len(unique_values) > 1:
                conflicts[field] = {
                    'values': unique_values,
                    'occurrences': {val: values.count(val) for val in unique_values}
                }

        # 分析点位数据差异
        points_conflicts = self._analyze_points_differences(results)
        if points_conflicts:
            conflicts['points_data'] = points_conflicts

        return {
            'has_differences': bool(conflicts),
            'conflicts': conflicts,
            'total_attempts': len(results),
            'success_rate': len([r for r in results if r.get('confidence_score', 0) > 0.7]) / len(results)
        }

    def _analyze_points_differences(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析点位数据差异"""
        all_points = {}

        for result in results:
            points_data = result.get('points_data', {})
            for room, value in points_data.items():
                if room not in all_points:
                    all_points[room] = []
                all_points[room].append(value)

        conflicts = {}
        for room, values in all_points.items():
            if len(set(values)) > 1:  # 有不同的值
                conflicts[room] = {
                    'values': list(set(values)),
                    'average': sum(values) / len(values) if values else 0,
                    'variance': max(values) - min(values) if values else 0
                }

        return conflicts

    def _select_best_result(self, results: List[Dict[str, Any]], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """选择最佳OCR结果"""
        if len(results) == 1:
            return results[0]

        # 按置信度排序
        sorted_results = sorted(results, key=lambda x: x.get('confidence_score', 0), reverse=True)
        best_result = sorted_results[0].copy()

        # 如果有冲突，使用投票机制选择最常见的值
        if analysis.get('has_differences', False):
            conflicts = analysis.get('conflicts', {})

            for field, conflict_info in conflicts.items():
                if field == 'points_data':
                    # 对点位数据使用平均值
                    best_points = {}
                    for room, room_conflict in conflict_info.items():
                        best_points[room] = room_conflict['average']
                    best_result['points_data'] = best_points
                else:
                    # 对其他字段使用最常见的值
                    occurrences = conflict_info.get('occurrences', {})
                    if occurrences:
                        most_common_value = max(occurrences.items(), key=lambda x: x[1])[0]
                        best_result[field] = most_common_value

        # 添加分析信息
        best_result['has_conflicts'] = analysis.get('has_differences', False)
        best_result['conflict_details'] = analysis

        return best_result


def get_ocr_service() -> OCRService:
    """
    获取OCR服务实例

    Returns:
        OCRService: OCR服务实例
    """
    use_openai = getattr(settings, 'USE_OPENAI_OCR', False)

    if use_openai:
        return OpenAIOCRService()
    else:
        return GeminiOCRService()


class ContactMatchingService:
    """联系人信息匹配服务"""

    def __init__(self):
        self.similarity_threshold = 0.8

    def match_contact_info(self, phone: str, csv_file_path: Optional[str] = None, log_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        匹配联系人信息

        Args:
            phone: 电话号码
            csv_file_path: CSV文件路径
            log_file_path: 日志文件路径

        Returns:
            dict: 匹配结果
        """
        result = {
            'contact_name': '',
            'full_phone': phone,
            'address': '',
            'match_type': 'manual',
            'similarity_score': 0.0,
            'match_source': 'manual'
        }

        if not phone:
            return result

        # 尝试CSV文件匹配
        if csv_file_path and os.path.exists(csv_file_path):
            csv_match = self._match_from_csv(phone, csv_file_path)
            if csv_match['match_type'] != 'manual':
                result.update(csv_match)
                return result

        # 尝试日志文件匹配
        if log_file_path and os.path.exists(log_file_path):
            log_match = self._match_from_log(phone, log_file_path)
            if log_match['match_type'] != 'manual':
                result.update(log_match)
                return result

        return result

    def _match_from_csv(self, phone: str, csv_file_path: str) -> Dict[str, Any]:
        """从CSV文件匹配联系人信息"""
        try:
            df = pd.read_csv(csv_file_path, encoding='utf-8')

            # 查找电话号码列
            phone_columns = ['客户电话', '联系电话', '电话', 'phone']
            phone_col = None
            for col in phone_columns:
                if col in df.columns:
                    phone_col = col
                    break

            if not phone_col:
                return {'match_type': 'manual'}

            # 精确匹配
            exact_match = df[df[phone_col].astype(str).str.contains(phone, na=False)]
            if not exact_match.empty:
                row = exact_match.iloc[0]
                return {
                    'contact_name': str(row.get('客户姓名', row.get('姓名', ''))),
                    'full_phone': str(row.get(phone_col, phone)),
                    'address': str(row.get('客户地址', row.get('地址', ''))),
                    'match_type': 'exact',
                    'similarity_score': 1.0,
                    'match_source': 'csv'
                }

            # 部分匹配（后8位）
            if len(phone) >= 8:
                phone_suffix = phone[-8:]
                partial_match = df[df[phone_col].astype(str).str.contains(phone_suffix, na=False)]
                if not partial_match.empty:
                    row = partial_match.iloc[0]
                    return {
                        'contact_name': str(row.get('客户姓名', row.get('姓名', ''))),
                        'full_phone': str(row.get(phone_col, phone)),
                        'address': str(row.get('客户地址', row.get('地址', ''))),
                        'match_type': 'partial',
                        'similarity_score': 0.8,
                        'match_source': 'csv'
                    }

        except Exception as e:
            logger.warning(f"CSV匹配失败: {e}")

        return {'match_type': 'manual'}

    def _match_from_log(self, phone: str, log_file_path: str) -> Dict[str, Any]:
        """从日志文件匹配联系人信息"""
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找包含电话号码的行
            lines = content.split('\n')
            for line in lines:
                if phone in line or (len(phone) >= 8 and phone[-8:] in line):
                    # 尝试从日志行中提取信息
                    # 格式通常是: [时间] 姓名 电话 地址+检测类型+日期.docx
                    match = re.search(r'\[(.*?)\]\s+(.+?)\s+(\d+)\s+(.+)', line)
                    if match:
                        timestamp, name, log_phone, address_info = match.groups()

                        # 提取地址（去掉文件名部分）
                        address = re.sub(r'\+.*?\.docx$', '', address_info)

                        similarity = 1.0 if phone == log_phone else 0.8
                        match_type = 'exact' if phone == log_phone else 'similarity'

                        return {
                            'contact_name': name.strip(),
                            'full_phone': log_phone,
                            'address': address.strip(),
                            'match_type': match_type,
                            'similarity_score': similarity,
                            'match_source': 'log'
                        }

        except Exception as e:
            logger.warning(f"日志匹配失败: {e}")

        return {'match_type': 'manual'}

    def match_contact_info_from_db(self, phone: str, date: str = '', points_data: dict = None) -> Dict[str, Any]:
        """
        从数据库表匹配联系人信息

        Args:
            phone: 电话号码
            date: 采样日期
            points_data: 点位数据

        Returns:
            dict: 匹配结果
        """
        from .models import CSVRecord

        result = {
            'contact_name': '',
            'full_phone': phone,
            'address': '',
            'match_type': 'manual',
            'similarity_score': 0.0,
            'match_source': 'manual',
            'csv_record': None
        }

        if not phone:
            return result

        # 标准化电话号码
        normalized_phone = self._normalize_phone(phone)

        # 从CSV记录表匹配
        csv_match = self._match_from_csv_records(normalized_phone)
        if csv_match['match_type'] != 'manual':
            result.update(csv_match)
            return result

        return result

    def _normalize_phone(self, phone: str) -> str:
        """标准化电话号码"""
        if not phone:
            return ""

        # 移除所有非数字字符
        digits_only = ''.join(c for c in str(phone) if c.isdigit())

        # 处理不同格式的电话号码
        if len(digits_only) == 11 and digits_only.startswith('1'):
            return digits_only
        elif len(digits_only) == 10:
            return '1' + digits_only
        elif len(digits_only) > 11:
            # 可能包含国家代码，取后11位
            return digits_only[-11:]

        return digits_only

    def _match_from_csv_records(self, phone: str) -> Dict[str, Any]:
        """从CSV记录表匹配"""
        try:
            from .models import CSVRecord

            if not phone:
                return {'match_type': 'manual'}

            # 精确匹配
            exact_match = CSVRecord.objects.filter(
                客户电话__icontains=phone,
                is_active=True
            ).first()

            if exact_match:
                return {
                    'contact_name': exact_match.客户姓名 or '',
                    'full_phone': exact_match.客户电话 or phone,
                    'address': exact_match.客户地址 or '',
                    'match_type': 'exact',
                    'similarity_score': 1.0,
                    'match_source': 'csv',
                    'csv_record': exact_match
                }

            # 部分匹配（后8位）
            if len(phone) >= 8:
                phone_suffix = phone[-8:]
                partial_match = CSVRecord.objects.filter(
                    客户电话__icontains=phone_suffix,
                    is_active=True
                ).first()

                if partial_match:
                    return {
                        'contact_name': partial_match.客户姓名 or '',
                        'full_phone': partial_match.客户电话 or phone,
                        'address': partial_match.客户地址 or '',
                        'match_type': 'partial',
                        'similarity_score': 0.8,
                        'match_source': 'csv',
                        'csv_record': partial_match
                    }

        except Exception as e:
            logger.warning(f"CSV记录匹配失败: {e}")

        return {'match_type': 'manual'}


def get_enhanced_ocr_service() -> EnhancedOCRService:
    """
    获取增强OCR服务实例

    Returns:
        EnhancedOCRService: 增强OCR服务实例
    """
    return EnhancedOCRService()


def get_contact_matching_service() -> ContactMatchingService:
    """
    获取联系人匹配服务实例

    Returns:
        ContactMatchingService: 联系人匹配服务实例
    """
    return ContactMatchingService()


class PointLearningEnhancedOCRService(EnhancedOCRService):
    """集成点位学习的增强OCR服务"""

    def __init__(self):
        super().__init__()
        from .point_learning_service import PointLearningService
        self.point_learning_service = PointLearningService

    def process_image_with_learning(
        self,
        image_path: str,
        use_multi_ocr: bool = False,
        ocr_count: int = 3
    ) -> Dict[str, Any]:
        """
        使用点位学习增强的OCR处理

        Args:
            image_path: 图片路径
            use_multi_ocr: 是否使用多重OCR
            ocr_count: OCR次数

        Returns:
            dict: 增强的OCR结果
        """
        try:
            # 获取点位建议用于提示词增强
            popular_points = self.point_learning_service.get_point_suggestions(limit=20)
            point_names = [p['point_name'] for p in popular_points]

            # 构建增强的提示词
            enhanced_prompt = self._build_enhanced_prompt(point_names)

            # 执行OCR处理
            if use_multi_ocr:
                result = self.process_multiple_ocr(image_path, ocr_count, enhanced_prompt)
            else:
                result = self.process_single_ocr(image_path, enhanced_prompt)

            # 如果有点位数据，进行智能判断
            if result.get('points_data'):
                inferred_type, confidence, statistics = self.point_learning_service.infer_check_type_from_points(
                    result['points_data']
                )

                # 更新结果
                result['inferred_check_type'] = inferred_type
                result['check_type_confidence'] = confidence
                result['check_type_statistics'] = statistics

                # 如果OCR识别的检测类型与推断不一致，记录冲突
                if result.get('check_type') and result['check_type'] != inferred_type:
                    result['has_check_type_conflict'] = True
                    result['ocr_check_type'] = result['check_type']
                    result['check_type'] = inferred_type  # 使用推断结果
                    logger.warning(f"检测类型冲突: OCR识别={result['ocr_check_type']}, 推断={inferred_type}")
                else:
                    result['check_type'] = inferred_type

            return result

        except Exception as e:
            logger.error(f"点位学习增强OCR处理失败: {str(e)}")
            # 回退到普通OCR处理
            if use_multi_ocr:
                return self.process_multiple_ocr(image_path, ocr_count)
            else:
                return self.process_single_ocr(image_path)

    def _build_enhanced_prompt(self, learned_points: List[str]) -> str:
        """构建包含学习点位的增强提示词"""
        points_str = "、".join(learned_points) if learned_points else "客厅、主卧、次卧、厨房"

        return f"""
        请从这张室内空气检测登记表中提取以下信息，并严格按照JSON格式返回：
        {{
            "phone": "联系电话",
            "date": "采样日期",
            "temperature": "采样温度值",
            "humidity": "采样湿度值",
            "check_type": "初检或复检",
            "points": {{
                "点位名称1": "检测值1",
                "点位名称2": "检测值2",
                "点位名称3": "检测值3",
                "点位名称4": "检测值4"
            }}
        }}

        注意：
        1. 联系电话是11位数字
        2. 检测值应为小数格式，通常为0.1xx(如0.103)或0.0xx(如0.043)的格式
        3. 点位名称通常是以下位置之一（基于历史学习数据）：{points_str}
        4. 日期格式为MM-DD
        5. 温度和湿度只需要数值，不要单位
        6. check_type是"初检"或"复检"，请查看表格左上角或表头部分的选择框
        7. 只返回JSON格式数据，不要有其他说明文字
        8. 辅助判断规则：根据点位值的众数判断，若大部分点位值>0.080通常是初检，若大部分点位值≤0.080通常是复检
        """

    def update_learning_from_result(self, ocr_result, points_data: Dict[str, float] = None):
        """从OCR结果更新点位学习数据"""
        try:
            if not points_data and hasattr(ocr_result, 'points_data'):
                points_data = ocr_result.points_data

            if points_data:
                check_type = getattr(ocr_result, 'check_type', 'initial')
                self.point_learning_service.update_point_learning(
                    points_data=points_data,
                    check_type=check_type,
                    ocr_result=ocr_result
                )
                logger.info(f"已更新点位学习数据: {len(points_data)}个点位")
        except Exception as e:
            logger.error(f"更新点位学习数据失败: {str(e)}")


def get_point_learning_enhanced_ocr_service() -> PointLearningEnhancedOCRService:
    """
    获取集成点位学习的增强OCR服务实例

    Returns:
        PointLearningEnhancedOCRService: 集成点位学习的增强OCR服务实例
    """
    return PointLearningEnhancedOCRService()
