"""
AI服务工厂模式实现
"""
import logging
from typing import Dict, Any, Optional, Type
from abc import ABC, abstractmethod
from .services import AIServiceManager
from .models import AIServiceUsageLog
from .monitoring import ai_monitor, ai_error_handler, monitor_ai_service, log_ai_operation
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseAIService(ABC):
    """AI服务基类"""
    
    def __init__(self, config: Dict[str, Any], service_manager: AIServiceManager):
        self.config = config
        self.service_manager = service_manager
        self.service_name = config.get('name', 'Unknown')
        self.provider = config.get('provider', 'unknown')
        self.api_format = config.get('api_format', 'unknown')
    
    @abstractmethod
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理AI请求"""
        pass
    
    def log_usage(self, service_type: str, request_data: Dict[str, Any],
                  response_data: Optional[Dict[str, Any]] = None,
                  is_success: bool = True, error_message: str = '',
                  response_time_ms: Optional[int] = None, user=None):
        """记录使用日志"""
        try:
            # 使用监控系统记录
            ai_monitor.record_service_call(
                service_config=self.config,
                service_type=service_type,
                success=is_success,
                response_time_ms=response_time_ms,
                error_message=error_message,
                user=user
            )

            # 记录操作日志
            log_ai_operation(
                operation=f"ai_service_call_{service_type}",
                details={
                    'service_name': self.service_name,
                    'provider': self.provider,
                    'success': is_success,
                    'response_time_ms': response_time_ms
                }
            )

        except Exception as e:
            logger.error(f"记录使用日志失败: {e}")


class GeminiAIService(BaseAIService):
    """Gemini AI服务实现"""
    
    def __init__(self, config: Dict[str, Any], service_manager: AIServiceManager):
        super().__init__(config, service_manager)
        self.api_key = config['api_key']
        self.base_url = config['api_base_url']
        self.model_name = config['model_name']
        self.timeout = config.get('timeout_seconds', 30)
        self.max_retries = config.get('max_retries', 3)
    
    @monitor_ai_service('gemini_api')
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Gemini API请求"""
        import requests
        import time

        start_time = time.time()
        
        try:
            url = f"{self.base_url}/v1beta/models/{self.model_name}:generateContent"
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.api_key
            }
            
            # 构建请求负载
            payload = self._build_gemini_payload(request_data)
            
            # 发送请求
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                response_data = response.json()
                result = self._parse_gemini_response(response_data)
                
                # 记录成功日志
                self.log_usage(
                    service_type=request_data.get('service_type', 'unknown'),
                    request_data=request_data,
                    response_data=result,
                    is_success=True,
                    response_time_ms=response_time_ms,
                    user=request_data.get('user')
                )
                
                return result
            else:
                error_msg = f"Gemini API错误: {response.status_code} - {response.text}"
                
                # 记录失败日志
                self.log_usage(
                    service_type=request_data.get('service_type', 'unknown'),
                    request_data=request_data,
                    is_success=False,
                    error_message=error_msg,
                    response_time_ms=response_time_ms,
                    user=request_data.get('user')
                )
                
                raise Exception(error_msg)
                
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 记录异常日志
            self.log_usage(
                service_type=request_data.get('service_type', 'unknown'),
                request_data=request_data,
                is_success=False,
                error_message=str(e),
                response_time_ms=response_time_ms,
                user=request_data.get('user')
            )
            
            raise e
    
    def _build_gemini_payload(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建Gemini API请求负载"""
        if request_data.get('type') == 'ocr':
            return {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": request_data.get('prompt', '')
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": request_data.get('image_base64', '')
                                }
                            }
                        ]
                    }
                ]
            }
        elif request_data.get('type') == 'text':
            return {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": request_data.get('prompt', '')
                            }
                        ]
                    }
                ]
            }
        else:
            raise ValueError(f"不支持的请求类型: {request_data.get('type')}")
    
    def _parse_gemini_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析Gemini API响应"""
        if 'candidates' in response_data and response_data['candidates']:
            candidate = response_data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                generated_text = candidate['content']['parts'][0]['text']
                return {
                    'success': True,
                    'generated_text': generated_text,
                    'provider': 'gemini',
                    'model': self.model_name
                }
        
        raise Exception("Gemini响应格式异常")


class OpenAIAIService(BaseAIService):
    """OpenAI AI服务实现"""
    
    def __init__(self, config: Dict[str, Any], service_manager: AIServiceManager):
        super().__init__(config, service_manager)
        self.api_key = config['api_key']
        self.base_url = config['api_base_url']
        self.model_name = config['model_name']
        self.timeout = config.get('timeout_seconds', 30)
        self.max_retries = config.get('max_retries', 3)
    
    @monitor_ai_service('openai_api')
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理OpenAI API请求"""
        import requests
        import time

        start_time = time.time()
        
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # 构建请求负载
            payload = self._build_openai_payload(request_data)
            
            # 发送请求
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                response_data = response.json()
                result = self._parse_openai_response(response_data)
                
                # 记录成功日志
                self.log_usage(
                    service_type=request_data.get('service_type', 'unknown'),
                    request_data=request_data,
                    response_data=result,
                    is_success=True,
                    response_time_ms=response_time_ms,
                    user=request_data.get('user')
                )
                
                return result
            else:
                error_msg = f"OpenAI API错误: {response.status_code} - {response.text}"
                
                # 记录失败日志
                self.log_usage(
                    service_type=request_data.get('service_type', 'unknown'),
                    request_data=request_data,
                    is_success=False,
                    error_message=error_msg,
                    response_time_ms=response_time_ms,
                    user=request_data.get('user')
                )
                
                raise Exception(error_msg)
                
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 记录异常日志
            self.log_usage(
                service_type=request_data.get('service_type', 'unknown'),
                request_data=request_data,
                is_success=False,
                error_message=str(e),
                response_time_ms=response_time_ms,
                user=request_data.get('user')
            )
            
            raise e
    
    def _build_openai_payload(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建OpenAI API请求负载"""
        if request_data.get('type') == 'ocr':
            return {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": request_data.get('prompt', '')
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{request_data.get('image_base64', '')}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
        elif request_data.get('type') == 'text':
            return {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": request_data.get('prompt', '')
                    }
                ],
                "max_tokens": 1000
            }
        else:
            raise ValueError(f"不支持的请求类型: {request_data.get('type')}")
    
    def _parse_openai_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析OpenAI API响应"""
        if 'choices' in response_data and response_data['choices']:
            generated_text = response_data['choices'][0]['message']['content']
            return {
                'success': True,
                'generated_text': generated_text,
                'provider': 'openai',
                'model': self.model_name
            }
        
        raise Exception("OpenAI响应格式异常")


class AIServiceFactory:
    """AI服务工厂"""
    
    # 服务类映射
    SERVICE_CLASSES = {
        'gemini': GeminiAIService,
        'openai': OpenAIAIService,
    }
    
    def __init__(self):
        self.service_manager = AIServiceManager()
        self._current_service = None
    
    def get_service(self, service_name: Optional[str] = None) -> BaseAIService:
        """获取AI服务实例"""
        if service_name:
            # 切换到指定服务
            if self.service_manager.switch_service(service_name):
                self._current_service = None  # 清除缓存
        
        # 如果没有缓存的服务，创建新的
        if not self._current_service:
            config = self.service_manager.get_current_service_config()
            if not config:
                raise Exception("没有可用的AI服务配置")
            
            self._current_service = self._create_service(config)
        
        return self._current_service
    
    def _create_service(self, config: Dict[str, Any]) -> BaseAIService:
        """根据配置创建服务实例"""
        api_format = config.get('api_format')

        if not api_format or api_format not in self.SERVICE_CLASSES:
            raise ValueError(f"不支持的API格式: {api_format}")

        service_class = self.SERVICE_CLASSES[api_format]
        return service_class(config, self.service_manager)
    
    def handle_service_failure(self, error: str, user=None) -> Optional[BaseAIService]:
        """处理服务故障，尝试切换到备用服务"""
        current_service_name = self._current_service.service_name if self._current_service else 'unknown'
        
        logger.warning(f"AI服务故障，尝试切换备用服务: {error}")
        
        # 尝试切换到备用服务
        fallback_config = self.service_manager.handle_service_failure(
            current_service_name, error, user
        )
        
        if fallback_config:
            self._current_service = self._create_service(fallback_config)
            logger.info(f"成功切换到备用服务: {fallback_config.get('name')}")
            return self._current_service
        
        logger.error("所有AI服务都不可用")
        return None
    
    def test_current_service(self) -> Dict[str, Any]:
        """测试当前服务"""
        config = self.service_manager.get_current_service_config()
        if not config:
            return {'success': False, 'error': '没有可用的服务配置'}
        
        return self.service_manager.test_service(config)
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        current_config = self.service_manager.get_current_service_config()
        available_services = self.service_manager.get_available_services()
        
        return {
            'current_service': current_config,
            'available_services': available_services,
            'total_services': len(available_services),
            'active_services': len([s for s in available_services if s.get('is_active', True)])
        }


# 全局AI服务工厂实例
ai_service_factory = AIServiceFactory()
