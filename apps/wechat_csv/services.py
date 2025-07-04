"""
微信CSV处理服务
移植自GUI项目的web_csv_submitter模块
"""
import re
import csv
import io
from datetime import datetime
from typing import Dict, List, Tuple, Any
import google.generativeai as genai
from django.conf import settings


class WechatMessageProcessor:
    """微信消息处理服务"""
    
    def __init__(self):
        # 配置Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def format_wechat_message(self, wechat_text: str) -> str:
        """
        使用Gemini API将微信消息格式化为CSV格式
        移植自GUI项目的format_wechat_message函数
        """
        prompt = f"""
        请将以下微信消息内容转换为CSV格式的一行数据。

        输出格式要求：
        客户姓名,客户电话,客户地址,商品类型(国标/母婴),成交金额,面积,履约时间,CMA点位数量,备注赠品

        注意事项：
        1. 如果某个字段没有信息，请留空
        2. 履约时间请使用YYYY-MM-DD格式
        3. 成交金额只保留数字，不要包含"元"等单位
        4. 面积只保留数字，不要包含"平方米"等单位
        5. 商品类型只能是"国标"或"母婴"
        6. 备注赠品格式：{{品类:数量}}，多个赠品用逗号分隔，如：{{除醛宝:2,炭包:1}}
        7. 如果地址、姓名等字段包含逗号，请用双引号包围该字段

        微信消息内容：
        {wechat_text}

        请只输出CSV格式的一行数据，不要包含任何其他说明文字。
        """
        
        try:
            response = self.model.generate_content(prompt)
            formatted_csv = response.text.strip()
            
            # 后处理：提取CMA点位数量和备注赠品
            formatted_csv = self._post_process_csv(formatted_csv, wechat_text)
            
            return formatted_csv
        except Exception as e:
            raise Exception(f"Gemini API调用失败: {str(e)}")
    
    def _post_process_csv(self, csv_line: str, original_text: str) -> str:
        """
        后处理CSV行，提取CMA点位数量和备注赠品
        移植自GUI项目的相关逻辑
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
    
    def _extract_cma_points(self, wechat_text: str) -> str:
        """提取CMA点位数量"""
        # CMA点位相关的正则表达式
        cma_patterns = [
            r"CMA.*?(\d+).*?个",
            r"(\d+).*?个.*?CMA",
            r"CMA.*?(\d+)",
            r"(\d+).*?CMA",
            r"检测.*?(\d+).*?个.*?点",
            r"(\d+).*?个.*?检测.*?点",
            r"点位.*?(\d+).*?个",
            r"(\d+).*?个.*?点位"
        ]
        
        for pattern in cma_patterns:
            match = re.search(pattern, wechat_text, re.IGNORECASE)
            if match:
                for group in match.groups():
                    if group and group.isdigit():
                        return group
        
        return ""
    
    def _extract_gift_notes(self, wechat_text: str) -> str:
        """
        从微信消息中提取备注赠品信息
        返回格式：{品类:数量}，多个赠品用逗号分隔
        移植自GUI项目的extract_gift_notes函数
        """
        # 备注赠品相关的正则表达式
        gift_patterns = {
            "除醛宝": [
                r"除醛宝.*?(\d+).*?个",
                r"(\d+).*?个.*?除醛宝",
                r"小绿罐.*?(\d+).*?个",
                r"(\d+).*?个.*?小绿罐",
                r"总共.*?(\d+).*?个.*?小绿罐",
                r"总共.*?(\d+).*?小绿罐",
                r"除醛宝.*?(\d+)",
                r"(\d+).*?除醛宝"
            ],
            "炭包": [
                r"炭包.*?(\d+).*?包",
                r"(\d+).*?包.*?炭包",
                r"炭包.*?(\d+)",
                r"(\d+).*?炭包",
                r"1000g.*?炭包.*?(\d+)",
                r"(\d+).*?1000g.*?炭包"
            ],
            "除醛机": [
                r"除醛机一台",
                r"除醛仪一台",
                r"一台.*?除醛机",
                r"一台.*?除醛仪",
                r"除醛机.*?(\d+).*?台",
                r"(\d+)台.*?除醛机",
                r"除醛仪.*?(\d+).*?台",
                r"(\d+)台.*?除醛仪",
                r"除醛机.*?(\d+)",
                r"(\d+).*?除醛机",
                r"除醛仪.*?(\d+)",
                r"(\d+).*?除醛仪"
            ],
            "除醛喷雾": [
                r"除醛喷雾.*?(\d+).*?瓶",
                r"(\d+).*?瓶.*?除醛喷雾",
                r"除醛喷雾.*?(\d+).*?个",
                r"(\d+).*?个.*?除醛喷雾",
                r"除醛喷雾.*?(\d+)",
                r"(\d+).*?除醛喷雾"
            ]
        }
        
        extracted_gifts = {}
        
        # 遍历每种赠品类型
        for gift_type, patterns in gift_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, wechat_text, re.IGNORECASE)
                if match:
                    # 检查是否匹配到数字
                    found_quantity = None
                    for group in match.groups():
                        if group and group.isdigit():
                            found_quantity = int(group)
                            break

                    # 如果没有找到数字，检查是否是特殊的中文数字模式（如"一台"）
                    if found_quantity is None:
                        # 检查"一台除醛机/除醛仪"这种模式
                        if "一台" in match.group(0):
                            found_quantity = 1

                    if found_quantity and found_quantity > 0:
                        extracted_gifts[gift_type] = found_quantity
                        break

            # 如果已经找到该类型的赠品，跳到下一个类型
            if gift_type in extracted_gifts:
                continue
        
        # 格式化输出
        if extracted_gifts:
            gift_strings = []
            for gift_type, quantity in extracted_gifts.items():
                gift_strings.append(f"{gift_type}:{quantity}")
            return "{" + ",".join(gift_strings) + "}"
        else:
            return ""
    
    def extract_fulfillment_dates(self, csv_content: str) -> List[str]:
        """从CSV内容中提取所有履约日期"""
        dates = []
        for line in csv_content.strip().split("\n"):
            parts = line.split(",")
            if len(parts) >= 7:  # 确保有足够的列
                dates.append(parts[6])  # 履约时间是第7列
        return dates
    
    def get_current_month_file(self, fulfillment_dates: List[str]) -> str:
        """
        根据履约日期确定应该使用哪个月份的CSV文件
        返回完整的文件路径，包含目录前缀
        """
        months = []
        for date_str in fulfillment_dates:
            try:
                # 尝试解析日期字符串
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                months.append(date_obj.month)
            except:
                # 如果解析失败，使用当前月份
                months.append(datetime.now().month)
        
        # 使用最常见的月份
        if months:
            most_common_month = max(set(months), key=months.count)
            filename = f"{most_common_month}月.csv"
        else:
            # 默认使用当前月份
            filename = f"{datetime.now().month}月.csv"
        
        # 返回包含目录前缀的完整路径
        return f"to csv/{filename}"


class CsvDataProcessor:
    """CSV数据处理服务"""

    def parse_csv_to_table_data(self, csv_content: str) -> Dict[str, Any]:
        """
        将CSV内容解析为表格数据格式，并进行大括号字段格式修正
        返回包含表格数据和修正信息的字典
        移植自GUI项目的parse_csv_to_table_data函数
        """
        if not csv_content.strip():
            return {"table_data": [], "fix_info": []}

        # 定义列名
        columns = ["客户姓名", "客户电话", "客户地址", "商品类型", "成交金额", "面积", "履约时间", "CMA点位数量", "备注赠品"]

        table_data = []
        all_fix_info = []

        # 先对整个CSV内容进行行级格式修正
        lines = csv_content.strip().split('\n')
        fixed_lines = []

        for line_index, line in enumerate(lines):
            if line.strip():  # 跳过空行
                fixed_line, line_fix_info = self._validate_and_fix_csv_line(line)
                fixed_lines.append(fixed_line)

                # 记录修正信息
                for fix in line_fix_info:
                    fix['line'] = line_index
                    all_fix_info.append(fix)
            else:
                fixed_lines.append(line)

        # 使用修正后的内容进行解析
        fixed_csv_content = '\n'.join(fixed_lines)
        reader = csv.reader(io.StringIO(fixed_csv_content))

        for row_index, row in enumerate(reader):
            if len(row) >= 7:  # 确保有足够的列（至少7列，第8、9列可选）
                # 调试备注赠品列
                gift_notes_raw = row[8] if len(row) > 8 else ""

                row_data = {
                    "index": row_index,
                    "客户姓名": row[0].strip(),
                    "客户电话": row[1].strip(),
                    "客户地址": row[2].strip(),
                    "商品类型": row[3].strip(),
                    "成交金额": row[4].strip(),
                    "面积": row[5].strip(),
                    "履约时间": row[6].strip(),
                    "CMA点位数量": row[7].strip() if len(row) > 7 else "",
                    "备注赠品": gift_notes_raw.strip()
                }
                table_data.append(row_data)

        return {
            "table_data": table_data,
            "fix_info": all_fix_info,
            "fixed_csv_content": fixed_csv_content if all_fix_info else csv_content
        }

    def validate_table_data(self, table_data: List[Dict]) -> Dict[str, Any]:
        """
        验证表格数据的有效性
        返回验证结果和错误信息
        移植自GUI项目的validate_table_data函数
        """
        errors = []
        warnings = []

        for i, row in enumerate(table_data):
            row_errors = []
            row_warnings = []

            # 验证客户姓名
            if not row["客户姓名"].strip():
                row_errors.append("客户姓名不能为空")

            # 验证客户电话
            phone = row["客户电话"].strip()
            if phone:
                if not re.match(r"^1[3-9]\d{9}$", phone):
                    row_errors.append("电话号码格式不正确")
            else:
                row_warnings.append("电话号码为空")

            # 验证客户地址
            if not row["客户地址"].strip():
                row_errors.append("客户地址不能为空")

            # 验证商品类型
            product_type = row["商品类型"].strip()
            if product_type and product_type not in ["国标", "母婴"]:
                row_warnings.append(f"商品类型'{product_type}'可能不正确，建议使用'国标'或'母婴'")

            # 验证成交金额
            amount = row["成交金额"].strip()
            if amount:
                try:
                    float(amount)
                except ValueError:
                    row_errors.append("成交金额必须是数字")
            else:
                row_errors.append("成交金额不能为空")

            # 验证面积
            area = row["面积"].strip()
            if area:
                try:
                    float(area)
                except ValueError:
                    row_errors.append("面积必须是数字")

            # 验证履约时间
            date_str = row["履约时间"].strip()
            if date_str:
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    row_errors.append("履约时间格式不正确，应为YYYY-MM-DD")
            else:
                row_warnings.append("履约时间为空")

            # 验证备注赠品格式
            gift_notes = row.get("备注赠品", "").strip()
            if gift_notes:
                if not self._validate_gift_notes_format(gift_notes):
                    row_errors.append("备注赠品格式错误，应为{品类:数量}格式")

            if row_errors:
                errors.append({"row": i, "errors": row_errors})
            if row_warnings:
                warnings.append({"row": i, "warnings": row_warnings})

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def table_data_to_csv(self, table_data: List[Dict]) -> str:
        """
        将表格数据转换回CSV格式，确保大括号字段被正确处理
        移植自GUI项目的table_data_to_csv函数
        """
        if not table_data:
            return ""

        output = io.StringIO()
        writer = csv.writer(output)

        for row in table_data:
            # 获取备注赠品字段并确保格式正确
            gift_notes = row.get("备注赠品", "")
            if gift_notes:
                # 确保大括号字段被正确引用
                gift_notes, _ = self._fix_brace_field_format(gift_notes)

            csv_row = [
                row["客户姓名"],
                row["客户电话"],
                row["客户地址"],
                row["商品类型"],
                row["成交金额"],
                row["面积"],
                row["履约时间"],
                row.get("CMA点位数量", ""),  # 使用get方法以兼容旧数据
                gift_notes  # 使用处理后的备注赠品字段
            ]
            writer.writerow(csv_row)

        return output.getvalue()

    def _validate_and_fix_csv_line(self, csv_line: str) -> Tuple[str, List[Dict]]:
        """
        验证并修正CSV行中的大括号字段格式
        在CSV解析之前先修正大括号字段，避免逗号分割问题
        移植自GUI项目的validate_and_fix_csv_line函数
        """
        if not csv_line.strip():
            return csv_line, []

        fix_info = []
        fixed_line = csv_line

        # 使用正则表达式查找未被引号包围的大括号内容
        # 匹配模式：{...} 但不在双引号内
        brace_pattern = r'(?<!")(\{[^{}]*\})(?!")'

        def replace_brace(match):
            brace_content = match.group(1)
            fixed_content = f'"{brace_content}"'

            fix_info.append({
                'original': brace_content,
                'fixed': fixed_content,
                'message': f'大括号字段已添加双引号包围: {brace_content} -> {fixed_content}'
            })

            return fixed_content

        # 执行替换
        fixed_line = re.sub(brace_pattern, replace_brace, fixed_line)

        return fixed_line, fix_info

    def _validate_gift_notes_format(self, gift_notes: str) -> bool:
        """验证备注赠品格式是否正确"""
        if not gift_notes:
            return True  # 空值是允许的

        # 检查基本格式：{品类:数量,品类:数量}
        pattern = r'^\{([^:]+:\d+(?:,[^:]+:\d+)*)\}$'
        if not re.match(pattern, gift_notes):
            return False

        # 检查品类是否在允许的范围内
        allowed_gifts = ["除醛宝", "炭包", "除醛机", "除醛喷雾"]
        content = gift_notes[1:-1]  # 去掉大括号
        items = content.split(',')

        for item in items:
            if ':' not in item:
                return False
            gift_type, quantity = item.split(':', 1)
            if gift_type.strip() not in allowed_gifts:
                return False
            if not quantity.strip().isdigit():
                return False

        return True

    def _fix_brace_field_format(self, field_value: str) -> Tuple[str, bool]:
        """
        检测并修正包含大括号的字段格式
        移植自GUI项目的fix_brace_field_format函数
        """
        if not field_value or not field_value.strip():
            return field_value, False

        field_value = field_value.strip()

        # 检查是否包含大括号
        if '{' not in field_value or '}' not in field_value:
            return field_value, False

        # 检查是否已经被双引号包围
        if field_value.startswith('"') and field_value.endswith('"'):
            return field_value, False

        # 检查是否是有效的大括号格式（基本验证）
        brace_pattern = r'\{[^{}]*\}'
        if re.search(brace_pattern, field_value):
            # 添加双引号包围
            fixed_value = f'"{field_value}"'
            return fixed_value, True

        return field_value, False


class DuplicateDetector:
    """重复检测服务"""

    def check_for_duplicates(self, new_entries: List[str], existing_content: str) -> Dict[str, Any]:
        """
        检查新条目是否与现有内容有重复
        返回包含重复项索引和匹配详情的字典
        移植自GUI项目的check_for_duplicates函数

        判断重复的规则：
        1. 电话号码相同（前提是电话号码不为空）
        2. 姓名+地址的模糊匹配：
           - 姓名：忽略"先生"、"女士"等称谓
           - 地址：使用核心地址部分进行匹配（忽略门牌号等细节差异）
        """
        # 存储结果的字典
        result = {
            "duplicate_indexes": [],  # 重复项的索引
            "match_details": [],  # 匹配详情，包含匹配到的行号和内容
        }

        # 解析现有内容
        existing_rows = []
        if existing_content:
            f = io.StringIO(existing_content)
            reader = csv.reader(f)
            existing_rows = list(reader)

        # 检查每个新条目
        for i, new_entry in enumerate(new_entries):
            # 使用csv.reader解析单行，以正确处理引号内的逗号
            new_row = list(csv.reader([new_entry]))[0]
            is_duplicate = False
            match_detail = {"new_index": i, "new_content": new_entry, "matched_rows": []}

            # 1. 电话号码检查（如果有电话号码）
            if len(new_row) >= 2 and new_row[1].strip():
                phone = new_row[1].strip()

                for row_idx, existing_row in enumerate(existing_rows):
                    if len(existing_row) >= 2 and existing_row[1].strip() == phone:
                        # 找到匹配项，记录详情
                        result["duplicate_indexes"].append(i)
                        match_detail["matched_rows"].append(
                            {
                                "existing_index": row_idx + 1,  # +1转为1-索引行号
                                "existing_content": ",".join(existing_row),
                                "match_type": "电话号码相同",
                            }
                        )
                        is_duplicate = True
                        break

                # 如果已经确认是重复项，添加匹配详情并继续下一个条目
                if is_duplicate:
                    result["match_details"].append(match_detail)
                    continue

            # 2. 姓名+地址的模糊匹配
            if len(new_row) >= 3:
                # 提取姓名和地址
                name = new_row[0].strip() if len(new_row) > 0 else ""
                address = new_row[2].strip() if len(new_row) > 2 else ""

                # 只有当姓名和地址都不为空时才进行比较
                if name and address:
                    cleaned_name = self._clean_name(name)
                    core_address = self._extract_core_address(address)

                    # 跳过处理过短或无意义的地址核心
                    if len(core_address) < 3:
                        continue

                    for row_idx, existing_row in enumerate(existing_rows):
                        if len(existing_row) < 3:
                            continue

                        existing_name = (
                            existing_row[0].strip() if len(existing_row) > 0 else ""
                        )
                        existing_address = (
                            existing_row[2].strip() if len(existing_row) > 2 else ""
                        )

                        # 清理并提取核心信息
                        existing_cleaned_name = self._clean_name(existing_name)
                        existing_core_address = self._extract_core_address(existing_address)

                        # 姓名相似且地址核心部分相似
                        if (
                            cleaned_name
                            and existing_cleaned_name
                            and (
                                cleaned_name in existing_cleaned_name
                                or existing_cleaned_name in cleaned_name
                            )
                            and core_address
                            and existing_core_address
                            and (
                                core_address in existing_core_address
                                or existing_core_address in core_address
                            )
                        ):
                            # 找到匹配项，记录详情
                            result["duplicate_indexes"].append(i)
                            match_detail["matched_rows"].append(
                                {
                                    "existing_index": row_idx + 1,  # +1转为1-索引行号
                                    "existing_content": ",".join(existing_row),
                                    "match_type": "姓名和地址相似",
                                }
                            )
                            is_duplicate = True
                            break

                    # 如果找到了模糊匹配项，添加匹配详情
                    if is_duplicate:
                        result["match_details"].append(match_detail)

        # 去重，确保每个索引只出现一次
        result["duplicate_indexes"] = list(set(result["duplicate_indexes"]))
        return result

    def _clean_name(self, name: str) -> str:
        """清理姓名的函数（移除称谓词）"""
        # 移除常见称谓词
        name = re.sub(r"(先生|女士|小姐|总|经理|老师|同学|大爷|阿姨)", "", name)
        return name.strip()

    def _extract_core_address(self, address: str) -> str:
        """提取地址核心部分的函数"""
        # 移除详细门牌号
        # 匹配类似"XX单元XX号"、"XX栋XX单元XX楼XX号"等门牌号
        address = re.sub(r"\d+[栋幢座号楼]-?\d*-?\d*\s*$", "", address)
        address = re.sub(r"\d+[单元门]-?\d*\s*$", "", address)
        address = re.sub(r"\d+[层楼][-]?\d*\s*$", "", address)
        address = re.sub(r"[0-9-]+号\s*$", "", address)

        # 提取主要地址信息（城市、区域、小区/街道名称）
        matches = re.findall(
            r"([省市区县]|[\u4e00-\u9fa5]{2,}(?:小区|公寓|花园|广场|大厦|社区|天地|世家|苑|台|湾|岛|城|府|园|里))",
            address,
        )
        core_parts = "".join(matches) if matches else address

        return core_parts.strip()


class GitHubService:
    """GitHub集成服务"""

    def __init__(self):
        from github import Github
        import base64

        self.github_token = settings.GITHUB_TOKEN
        self.github_repo = settings.GITHUB_REPO
        self.github = Github(self.github_token)
        self.base64 = base64

    def get_file_content(self, file_path: str) -> Tuple[str, str]:
        """
        获取GitHub文件内容
        返回 (文件内容, 文件SHA)
        支持多路径尝试，移植自GUI项目的逻辑
        """
        try:
            repo = self.github.get_repo(self.github_repo)

            # 尝试多种路径组合
            paths_to_try = [
                file_path,  # 原始路径 (如 "to csv/5月.csv")
                file_path.split("/")[-1],  # 只使用文件名 (如 "5月.csv")
                "to csv/" + file_path.split("/")[-1],  # 添加to csv目录 (如果不存在)
            ]

            for path in paths_to_try:
                try:
                    file_obj = repo.get_contents(path)
                    # 处理可能返回列表的情况
                    if isinstance(file_obj, list):
                        file_obj = file_obj[0]
                    file_content = self.base64.b64decode(file_obj.content).decode("utf-8")
                    return file_content, file_obj.sha
                except Exception:
                    continue

            # 如果所有路径都失败，返回空内容
            return "", ""

        except Exception as e:
            raise Exception(f"GitHub文件获取失败: {str(e)}")

    def submit_to_github(self, file_path: str, csv_content: str) -> Dict[str, Any]:
        """
        提交CSV内容到GitHub
        移植自GUI项目的submit逻辑
        """
        try:
            repo = self.github.get_repo(self.github_repo)

            # 检查文件是否存在
            file_content, file_sha = self.get_file_content(file_path)

            # 尝试多种路径组合
            paths_to_try = [
                file_path,  # 原始路径 (如 "to csv/5月.csv")
                file_path.split("/")[-1],  # 只使用文件名 (如 "5月.csv")
                "to csv/" + file_path.split("/")[-1],  # 添加to csv目录 (如果不存在)
            ]

            file_path_used = file_path  # 默认使用原始路径

            for path in paths_to_try:
                try:
                    file_obj = repo.get_contents(path)
                    # 处理可能返回列表的情况
                    if isinstance(file_obj, list):
                        file_obj = file_obj[0]
                    file_content = self.base64.b64decode(file_obj.content).decode("utf-8")
                    file_sha = file_obj.sha
                    file_path_used = path  # 记录实际使用的路径
                    break  # 找到文件后跳出循环
                except Exception:
                    continue

            # 准备新内容
            if file_content:
                # 确保文件最后有换行符
                if not file_content.endswith("\n"):
                    file_content += "\n"

                # 添加新内容
                new_content = file_content + csv_content
            else:
                # 创建新文件，添加标题行
                header = "客户姓名,客户电话,客户地址,商品类型(国标/母婴),成交金额,面积,履约时间,CMA点位数量,备注赠品\n"
                new_content = header + csv_content

            # 提交到GitHub
            commit_message = f"添加新记录到 {file_path_used}"
            commit_result = None

            if file_sha:
                # 更新现有文件
                commit_result = repo.update_file(file_path_used, commit_message, new_content, file_sha)
            else:
                # 创建新文件
                commit_result = repo.create_file(file_path_used, commit_message, new_content)

            # 获取提交信息
            commit_info = None
            if commit_result:
                if isinstance(commit_result, dict) and 'commit' in commit_result:
                    commit_obj = commit_result['commit']
                    commit_sha = commit_obj.sha

                    # 获取完整的commit对象来获取详细信息
                    full_commit = repo.get_commit(commit_sha)

                    commit_info = {
                        "sha": commit_sha,
                        "message": commit_message,
                        "date": full_commit.commit.author.date.isoformat(),
                        "author": full_commit.commit.author.name,
                        "url": full_commit.html_url
                    }

            return {
                "success": True,
                "message": f"成功添加记录到 {file_path_used}",
                "commit_info": commit_info,
                "file_path": file_path_used
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"提交到GitHub失败: {str(e)}"
            }
