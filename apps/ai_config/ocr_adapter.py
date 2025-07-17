"""
OCR服务适配器 - 使用AI服务工厂
"""
import base64
import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from .factory import ai_service_factory
from apps.ocr.services import OCRService

logger = logging.getLogger(__name__)


class AIConfigOCRService(OCRService):
    """使用AI配置系统的OCR服务"""
    
    def __init__(self):
        super().__init__()
        self.factory = ai_service_factory
    
    def process_image(self, image_path: str, user=None) -> Dict[str, Any]:
        """
        使用AI配置系统处理图片OCR
        
        Args:
            image_path: 图片路径
            user: 用户对象
            
        Returns:
            dict: OCR结果
        """
        try:
            logger.info(f"开始AI配置OCR处理: {image_path}")
            
            # 编码图片
            image_base64 = self.encode_image_to_base64(image_path)
            logger.info(f"图片编码完成，大小: {len(image_base64)} 字符")
            
            # 构建OCR提示词
            prompt = self.build_ocr_prompt()
            
            # 准备请求数据
            request_data = {
                'type': 'ocr',
                'service_type': 'ocr_processing',
                'prompt': prompt,
                'image_base64': image_base64,
                'image_path': image_path,
                'user': user
            }
            
            # 获取AI服务并处理请求
            ai_service = self.factory.get_service()
            response = ai_service.process_request(request_data)
            
            # 解析OCR结果
            if response.get('success'):
                generated_text = response.get('generated_text', '')
                result = self.parse_ocr_response(generated_text)
                result['provider'] = response.get('provider', 'unknown')
                result['model'] = response.get('model', 'unknown')
                result['confidence_score'] = 0.9  # 默认置信度
                
                logger.info(f"AI配置OCR处理成功: {image_path}")
                return result
            else:
                raise Exception("AI服务处理失败")
                
        except Exception as e:
            logger.error(f"AI配置OCR处理失败: {e}")
            
            # 尝试切换到备用服务
            fallback_service = self.factory.handle_service_failure(str(e), user)
            if fallback_service:
                try:
                    logger.info("尝试使用备用服务重新处理")
                    response = fallback_service.process_request(request_data)
                    
                    if response.get('success'):
                        generated_text = response.get('generated_text', '')
                        result = self.parse_ocr_response(generated_text)
                        result['provider'] = response.get('provider', 'unknown')
                        result['model'] = response.get('model', 'unknown')
                        result['confidence_score'] = 0.85  # 备用服务稍低置信度
                        
                        logger.info(f"备用服务OCR处理成功: {image_path}")
                        return result
                except Exception as fallback_error:
                    logger.error(f"备用服务也失败: {fallback_error}")
            
            # 所有服务都失败，抛出异常
            raise e
    
    def build_ocr_prompt(self) -> str:
        """构建OCR提示词"""
        return """请仔细分析这张室内空气检测报告图片，提取以下信息并以JSON格式返回：

{
    "customer_info": {
        "name": "客户姓名",
        "phone": "联系电话",
        "address": "检测地址"
    },
    "detection_info": {
        "detection_date": "检测日期(YYYY-MM-DD格式)",
        "detection_time": "检测时间",
        "weather": "天气情况",
        "temperature": "温度",
        "humidity": "湿度"
    },
    "points_data": {
        "房间名称1": {
            "formaldehyde": "甲醛数值",
            "benzene": "苯数值", 
            "toluene": "甲苯数值",
            "xylene": "二甲苯数值",
            "tvoc": "TVOC数值"
        }
    },
    "company_info": {
        "detection_company": "检测机构名称",
        "report_number": "报告编号"
    }
}

注意事项：
1. 如果某个字段无法识别，请设置为空字符串""
2. 数值请保留原始格式，包括单位
3. 房间名称请使用实际识别到的名称
4. 日期格式必须是YYYY-MM-DD
5. 请确保返回的是有效的JSON格式"""


class AIConfigMultiOCRService:
    """使用AI配置系统的多重OCR服务"""
    
    def __init__(self):
        self.factory = ai_service_factory
        self.base_service = AIConfigOCRService()
    
    def process_image_multiple(self, image_path: str, ocr_count: int = 3, user=None) -> Dict[str, Any]:
        """
        多次OCR处理并分析结果
        
        Args:
            image_path: 图片路径
            ocr_count: OCR次数
            user: 用户对象
            
        Returns:
            dict: 最佳OCR结果
        """
        logger.info(f"开始多重OCR处理: {image_path}, 次数: {ocr_count}")
        
        results = []
        errors = []
        
        for i in range(ocr_count):
            try:
                logger.info(f"执行第 {i+1} 次OCR")
                result = self.base_service.process_image(image_path, user)
                results.append(result)
                logger.info(f"第 {i+1} 次OCR成功")
            except Exception as e:
                error_msg = f"第 {i+1} 次OCR失败: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        if not results:
            raise Exception(f"所有OCR尝试都失败: {'; '.join(errors)}")
        
        # 分析多次结果，选择最佳结果
        best_result = self._analyze_multiple_results(results)
        best_result['ocr_attempts'] = len(results)
        best_result['total_attempts'] = ocr_count
        best_result['errors'] = errors
        
        logger.info(f"多重OCR处理完成，成功 {len(results)}/{ocr_count} 次")
        return best_result
    
    def _analyze_multiple_results(self, results: list) -> Dict[str, Any]:
        """
        分析多次OCR结果，选择最佳结果
        
        Args:
            results: OCR结果列表
            
        Returns:
            dict: 最佳结果
        """
        if len(results) == 1:
            return results[0]
        
        # 简单策略：选择点位数据最多的结果
        best_result = results[0]
        max_points = len(best_result.get('points_data', {}))
        
        for result in results[1:]:
            points_count = len(result.get('points_data', {}))
            if points_count > max_points:
                max_points = points_count
                best_result = result
        
        # 添加分析信息
        best_result['analysis'] = {
            'total_results': len(results),
            'selected_reason': f'选择了包含 {max_points} 个检测点位的结果',
            'all_points_counts': [len(r.get('points_data', {})) for r in results]
        }
        
        return best_result


def get_ai_config_ocr_service() -> AIConfigOCRService:
    """
    获取AI配置OCR服务实例
    
    Returns:
        AIConfigOCRService: AI配置OCR服务实例
    """
    return AIConfigOCRService()


def get_ai_config_multi_ocr_service() -> AIConfigMultiOCRService:
    """
    获取AI配置多重OCR服务实例
    
    Returns:
        AIConfigMultiOCRService: AI配置多重OCR服务实例
    """
    return AIConfigMultiOCRService()
