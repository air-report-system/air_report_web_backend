"""
订单信息处理服务
复用GUI项目中的web csv功能逻辑
"""
import os
import csv
import io
import re
import threading
from datetime import datetime
from typing import Dict, Any, List
from django.conf import settings
import google.generativeai as genai


def timeout_handler(timeout_seconds):
    """超时处理装饰器 - 使用threading.Timer实现"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)

            if thread.is_alive():
                # 超时了，但无法强制终止线程
                raise TimeoutError(f"Gemini API调用超时 ({timeout_seconds}秒)")

            if exception[0] is not None:
                raise exception[0]

            return result[0]

        return wrapper
    return decorator


class OrderInfoProcessor:
    """订单信息处理器 - 复用GUI项目的format_wechat_message逻辑"""
    
    def __init__(self):
        """初始化Gemini API"""
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY未配置")

        try:
            # 设置代理（如果启用）
            self._setup_proxy()

            genai.configure(api_key=api_key)
            model_name = getattr(settings, 'GEMINI_MODEL_NAME')
            print(f"从settings读取到的模型名称: {model_name}")
            print(f"settings.GEMINI_MODEL_NAME = {settings.GEMINI_MODEL_NAME}")
            self.model = genai.GenerativeModel(model_name)
            print(f"Gemini API初始化成功，使用模型: {model_name}")
        except Exception as e:
            print(f"Gemini API初始化失败: {str(e)}")
            raise

    def _setup_proxy(self):
        """设置代理环境变量"""
        use_proxy = getattr(settings, 'USE_PROXY', False)
        if use_proxy:
            http_proxy = getattr(settings, 'HTTP_PROXY', 'http://127.0.0.1:10809')
            https_proxy = getattr(settings, 'HTTPS_PROXY', 'http://127.0.0.1:10809')

            os.environ["HTTP_PROXY"] = http_proxy
            os.environ["HTTPS_PROXY"] = https_proxy
            print(f"代理已启用: HTTP_PROXY={http_proxy}, HTTPS_PROXY={https_proxy}")
        else:
            # 清除代理环境变量
            if "HTTP_PROXY" in os.environ:
                del os.environ["HTTP_PROXY"]
            if "HTTPS_PROXY" in os.environ:
                del os.environ["HTTPS_PROXY"]
            print("代理已禁用，清除代理环境变量")
    
    @timeout_handler(getattr(settings, 'API_TIMEOUT_SECONDS', 30))
    def format_order_message(self, order_text: str) -> str:
        """
        使用Gemini API将订单信息格式化为CSV格式
        复用GUI项目的format_wechat_message函数逻辑
        """
        try:
            # 获取当前年份
            current_year = datetime.now().year

            prompt = f"""
            请分析以下订单信息中的业务数据，并提取关键信息整理成CSV格式。
            每行格式应为：客户姓名,客户电话,客户地址,商品类型(国标/母婴),成交金额,面积,履约时间,CMA点位数量,备注赠品

            注意事项：
            1. 如果某个字段没有信息，请留空
            2. 履约时间请使用YYYY-MM-DD格式，如果原文只有月日，请使用当前年份 {current_year} 作为年份
            3. 成交金额只保留数字，不要包含"元"等单位
            4. 面积只保留数字，不要包含"平方米"等单位
            5. 商品类型只能是"国标"或"母婴"
            6. CMA点位数量：如果是CMA检测订单，请提取具体的点位数量（数字），如果不是CMA订单或无法确定点位数量，请留空
            7. 备注赠品格式：{{品类:数量}}，多个赠品用逗号分隔，如：{{除醛宝:2,炭包:1}}
               - 支持的品类：除醛宝（也叫小绿罐）、炭包、除醛机（也叫除醛仪）、除醛喷雾
               - 数量识别：支持阿拉伯数字（如16个）和中文数字（如一台=1台）
               - 注意：一定要是双引号引住大括号，不然会被csv认为是多个字段
            8. 如果地址、姓名等字段包含逗号，请用双引号包围该字段
            9. 只输出CSV格式的一行数据，不要包含任何其他说明文字
            10. 不要包含CSV的标题行

            订单信息内容：
            {order_text}

            请只输出CSV格式的一行数据，不要包含任何其他说明文字。
            """

            print(f"正在调用Gemini API处理订单信息...")
            response = self.model.generate_content(prompt)
            formatted_csv = response.text.strip()
            print(f"Gemini API响应: {formatted_csv}")

            # 后处理：提取CMA点位数量和备注赠品
            formatted_csv = self._post_process_csv(formatted_csv, order_text)

            return formatted_csv
        except Exception as e:
            print(f"Gemini API调用失败，使用本地处理: {str(e)}")
            # 如果Gemini API失败，使用本地处理方式
            return self._local_format_order_message(order_text)
    
    def _post_process_csv(self, csv_line: str, original_text: str) -> str:
        """
        后处理CSV行，提取CMA点位数量和备注赠品
        复用GUI项目的相关逻辑
        """
        # 解析CSV行
        reader = csv.reader([csv_line])
        row = next(reader)
        
        if len(row) < 9:
            # 补齐列数
            row.extend([''] * (9 - len(row)))
        
        # 提取CMA点位数量
        cma_points = self._extract_cma_points(original_text)
        if cma_points:
            row[7] = cma_points
        
        # 提取备注赠品信息
        gift_notes = self._extract_gift_notes(original_text)
        if gift_notes:
            row[8] = gift_notes
        
        # 重新生成CSV行
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(row)
        return output.getvalue().strip()
    
    def _extract_cma_points(self, text: str) -> str:
        """提取CMA点位数量"""
        # CMA点位数量提取模式
        cma_patterns = [
            r'CMA.*?(\d+).*?点',
            r'(\d+).*?点.*?CMA',
            r'CMA.*?(\d+)',
            r'点位.*?(\d+)',
            r'(\d+).*?点位'
        ]
        
        for pattern in cma_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ''
    
    def _extract_gift_notes(self, text: str) -> str:
        """提取备注赠品信息"""
        gifts = {}
        
        # 赠品提取模式
        gift_patterns = {
            '除醛宝': [r'除醛宝.*?(\d+)', r'小绿罐.*?(\d+)', r'(\d+).*?除醛宝', r'(\d+).*?小绿罐'],
            '炭包': [r'炭包.*?(\d+)', r'(\d+).*?炭包'],
            '除醛机': [r'除醛机.*?(\d+)', r'除醛仪.*?(\d+)', r'(\d+).*?除醛机', r'(\d+).*?除醛仪'],
            '除醛喷雾': [r'除醛喷雾.*?(\d+)', r'喷雾.*?(\d+)', r'(\d+).*?除醛喷雾', r'(\d+).*?喷雾']
        }
        
        # 中文数字转换
        chinese_numbers = {
            '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
        }
        
        for gift_type, patterns in gift_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # 转换中文数字
                        if match in chinese_numbers:
                            match = chinese_numbers[match]
                        try:
                            count = int(match)
                            if gift_type in gifts:
                                gifts[gift_type] += count
                            else:
                                gifts[gift_type] = count
                        except ValueError:
                            continue
        
        # 格式化为{品类:数量}格式
        if gifts:
            gift_items = [f"{gift_type}:{count}" for gift_type, count in gifts.items()]
            return f'"{{{",".join(gift_items)}}}"'
        
        return ''
    
    def parse_csv_to_order_data(self, csv_content: str) -> Dict[str, Any]:
        """
        将CSV内容解析为订单数据格式
        """
        if not csv_content.strip():
            return {"order_data": {}, "validation_errors": []}
        
        # 定义列名
        columns = ["客户姓名", "客户电话", "客户地址", "商品类型", "成交金额", "面积", "履约时间", "CMA点位数量", "备注赠品"]
        
        try:
            # 解析CSV行
            reader = csv.reader([csv_content.strip()])
            row = next(reader)
            
            # 补齐列数
            if len(row) < len(columns):
                row.extend([''] * (len(columns) - len(row)))
            
            # 构建订单数据
            order_data = {}
            for i, column in enumerate(columns):
                value = row[i].strip() if i < len(row) else ''
                order_data[column] = value
            
            # 验证数据
            validation_errors = self._validate_order_data(order_data)
            
            return {
                "order_data": order_data,
                "validation_errors": validation_errors,
                "csv_content": csv_content
            }
            
        except Exception as e:
            return {
                "order_data": {},
                "validation_errors": [f"CSV解析失败: {str(e)}"],
                "csv_content": csv_content
            }
    
    def _validate_order_data(self, order_data: Dict[str, str]) -> List[str]:
        """验证订单数据"""
        errors = []
        
        # 必填字段检查（客户姓名不再是必填项）
        required_fields = []
        for field in required_fields:
            if not order_data.get(field, '').strip():
                errors.append(f"{field}不能为空")
        
        # 电话号码格式检查
        phone = order_data.get("客户电话", '').strip()
        if phone and not re.match(r'^1[3-9]\d{9}$', phone):
            errors.append("客户电话格式不正确")
        
        # 商品类型检查
        product_type = order_data.get("商品类型", '').strip()
        if product_type and product_type not in ['国标', '母婴']:
            errors.append("商品类型只能是'国标'或'母婴'")
        
        # 成交金额格式检查
        amount = order_data.get("成交金额", '').strip()
        if amount:
            try:
                float(amount)
            except ValueError:
                errors.append("成交金额格式不正确")
        
        # 履约时间格式检查
        fulfillment_date = order_data.get("履约时间", '').strip()
        if fulfillment_date:
            try:
                datetime.strptime(fulfillment_date, '%Y-%m-%d')
            except ValueError:
                errors.append("履约时间格式不正确，应为YYYY-MM-DD")
        
        return errors

    def _local_format_order_message(self, order_text: str) -> str:
        """
        本地处理订单信息，当Gemini API不可用时使用
        """
        # 简单的正则表达式提取
        import re

        # 提取客户姓名
        name_patterns = [
            r'姓名[：:]\s*([^\s,，]+)',
            r'客户[：:]\s*([^\s,，]+)',
            r'联系人[：:]\s*([^\s,，]+)'
        ]
        name = ''
        for pattern in name_patterns:
            match = re.search(pattern, order_text)
            if match:
                name = match.group(1)
                break

        # 提取电话
        phone_pattern = r'1[3-9]\d{9}'
        phone_match = re.search(phone_pattern, order_text)
        phone = phone_match.group(0) if phone_match else ''

        # 提取地址
        address_patterns = [
            r'地址[：:]\s*([^\n]+)',
            r'住址[：:]\s*([^\n]+)'
        ]
        address = ''
        for pattern in address_patterns:
            match = re.search(pattern, order_text)
            if match:
                address = match.group(1).strip()
                break

        # 提取商品类型
        product_type = ''
        if '国标' in order_text:
            product_type = '国标'
        elif '母婴' in order_text:
            product_type = '母婴'

        # 提取金额
        amount_patterns = [
            r'(\d+)元',
            r'金额[：:]\s*(\d+)',
            r'价格[：:]\s*(\d+)'
        ]
        amount = ''
        for pattern in amount_patterns:
            match = re.search(pattern, order_text)
            if match:
                amount = match.group(1)
                break

        # 提取面积
        area_patterns = [
            r'(\d+)平方米',
            r'(\d+)平米',
            r'面积[：:]\s*(\d+)'
        ]
        area = ''
        for pattern in area_patterns:
            match = re.search(pattern, order_text)
            if match:
                area = match.group(1)
                break

        # 提取履约时间
        date_patterns = [
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})',
            r'履约[：:]\s*(\d{4}-\d{1,2}-\d{1,2})'
        ]
        fulfillment_date = ''
        for pattern in date_patterns:
            match = re.search(pattern, order_text)
            if match:
                fulfillment_date = match.group(1)
                break

        # 提取CMA点位
        cma_patterns = [
            r'CMA[：:]?\s*(\d+)',
            r'(\d+)\s*个?点位',
            r'点位[：:]\s*(\d+)'
        ]
        cma_points = ''
        for pattern in cma_patterns:
            match = re.search(pattern, order_text)
            if match:
                cma_points = match.group(1)
                break

        # 提取赠品信息
        gift_notes = self._extract_gift_notes(order_text)

        # 构建CSV行
        csv_row = [name, phone, address, product_type, amount, area, fulfillment_date, cma_points, gift_notes]

        # 转换为CSV格式
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(csv_row)
        return output.getvalue().strip()

    def check_for_duplicates(self, order_data: Dict[str, str]) -> Dict[str, Any]:
        """
        检查订单是否与现有记录重复
        复用webcsv的查重逻辑

        判断重复的规则：
        1. 电话号码相同（前提是电话号码不为空）
        2. 姓名+地址的模糊匹配：
           - 姓名：忽略"先生"、"女士"等称谓
           - 地址：使用核心地址部分进行匹配（忽略门牌号等细节差异）
        """
        from apps.ocr.models import CSVRecord

        result = {
            "is_duplicate": False,
            "match_details": [],
            "duplicate_count": 0
        }

        customer_name = order_data.get('客户姓名', '').strip()
        customer_phone = order_data.get('客户电话', '').strip()
        customer_address = order_data.get('客户地址', '').strip()

        # 如果姓名、电话、地址都为空，则无法进行查重
        if not customer_name and not customer_phone and not customer_address:
            return result

        # 获取现有记录
        existing_records = CSVRecord.objects.filter(is_active=True)

        # 1. 电话号码检查（如果有电话号码）
        if customer_phone:
            phone_matches = existing_records.filter(客户电话=customer_phone)
            if phone_matches.exists():
                for record in phone_matches:
                    result["match_details"].append({
                        "existing_id": record.id,
                        "existing_name": record.客户姓名,
                        "existing_phone": record.客户电话,
                        "existing_address": record.客户地址,
                        "existing_date": record.履约时间.strftime('%Y-%m-%d') if record.履约时间 else '',
                        "match_type": "电话号码相同"
                    })
                result["is_duplicate"] = True
                result["duplicate_count"] = phone_matches.count()
                return result

        # 2. 姓名+地址的模糊匹配
        if customer_name and customer_address:
            cleaned_name = self._clean_name(customer_name)
            core_address = self._extract_core_address(customer_address)

            if cleaned_name and core_address:
                # 查找可能的匹配记录
                potential_matches = existing_records.filter(
                    客户姓名__isnull=False,
                    客户地址__isnull=False
                ).exclude(客户姓名='').exclude(客户地址='')

                for record in potential_matches:
                    existing_cleaned_name = self._clean_name(record.客户姓名)
                    existing_core_address = self._extract_core_address(record.客户地址)

                    # 姓名相似且地址核心部分相似
                    if (existing_cleaned_name and existing_core_address and
                        (cleaned_name in existing_cleaned_name or existing_cleaned_name in cleaned_name) and
                        (core_address in existing_core_address or existing_core_address in core_address)):

                        result["match_details"].append({
                            "existing_id": record.id,
                            "existing_name": record.客户姓名,
                            "existing_phone": record.客户电话 or '',
                            "existing_address": record.客户地址,
                            "existing_date": record.履约时间.strftime('%Y-%m-%d') if record.履约时间 else '',
                            "match_type": "姓名和地址相似"
                        })
                        result["is_duplicate"] = True
                        result["duplicate_count"] += 1

        return result

    def _clean_name(self, name: str) -> str:
        """清理姓名，移除称谓词"""
        if not name:
            return ''
        # 移除常见称谓词
        import re
        name = re.sub(r"(先生|女士|小姐|总|经理|老师|同学|大爷|阿姨)", "", name)
        return name.strip()

    def _extract_core_address(self, address: str) -> str:
        """提取地址的核心部分"""
        if not address:
            return ''

        import re
        # 移除详细门牌号、楼层、房间号等
        # 保留主要的区域信息
        core_patterns = [
            r'(.+?市.+?区.+?路)',  # 市区路
            r'(.+?市.+?区.+?街)',  # 市区街
            r'(.+?市.+?区.+?大道)', # 市区大道
            r'(.+?市.+?区.+?小区)', # 市区小区
            r'(.+?市.+?区)',       # 市区
            r'(.+?市.+?县)',       # 市县
            r'(.+?省.+?市)',       # 省市
        ]

        for pattern in core_patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(1)

        # 如果没有匹配到标准格式，返回前半部分
        if len(address) > 10:
            return address[:10]
        return address
