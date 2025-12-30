"""
AI配置管理服务
"""
import json
import os
import shutil
import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import AIServiceConfig, AIConfigHistory, AIServiceUsageLog
import logging
import threading

logger = logging.getLogger(__name__)

class AIConfigFileManager:
    """AI配置文件管理器"""
    
    def __init__(self):
        self.config_dir = Path(settings.BASE_DIR) / 'config' / 'ai_configs'
        self.config_file = self.config_dir / 'ai_services.json'
        self.backup_dir = self.config_dir / 'backups'
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"成功加载AI配置文件: {self.config_file}")
                return config
            else:
                logger.info("AI配置文件不存在，返回默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载AI配置文件失败: {e}")
            return self._get_default_config()
    
    def save_config(self, config: Dict[str, Any], backup: bool = True) -> bool:
        """保存配置文件"""
        try:
            # 创建备份
            if backup and self.config_file.exists():
                self._create_backup()
            
            # 验证配置格式
            self._validate_config(config)
            
            # 保存配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存AI配置文件: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存AI配置文件失败: {e}")
            return False
    
    def _create_backup(self):
        """创建配置文件备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'ai_services_{timestamp}.json'
        shutil.copy2(self.config_file, backup_file)
        logger.info(f"创建配置备份: {backup_file}")
        
        # 清理旧备份（保留最近10个）
        self._cleanup_old_backups()
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份文件"""
        backup_files = sorted(
            self.backup_dir.glob('ai_services_*.json'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for backup_file in backup_files[keep_count:]:
            backup_file.unlink()
            logger.info(f"删除旧备份: {backup_file}")
    
    def _validate_config(self, config: Dict[str, Any]):
        """验证配置格式"""
        required_fields = ['version', 'default_service', 'services']
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"配置文件缺少必需字段: {field}")
        
        # 验证服务配置
        for service_name, service_config in config['services'].items():
            self._validate_service_config(service_name, service_config)
    
    def _validate_service_config(self, name: str, config: Dict[str, Any]):
        """验证单个服务配置"""
        required_fields = ['provider', 'api_format', 'api_base_url', 'api_key', 'model_name']
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"服务 {name} 缺少必需字段: {field}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "1.0",
            "default_service": "gemini_default",
            "fallback_enabled": True,
            "services": {
                "gemini_default": {
                    "name": "Gemini默认配置",
                    "provider": "gemini",
                    "api_format": "gemini",
                    "api_base_url": "https://generativelanguage.googleapis.com",
                    "api_key": os.getenv('GEMINI_API_KEY', ''),
                    "model_name": "gemini-2.0-flash-exp-image-generation",
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "is_active": True,
                    "priority": 1
                },
                "openai_fallback": {
                    "name": "OpenAI备用配置",
                    "provider": "openai",
                    "api_format": "openai",
                    "api_base_url": "https://api.openai.com/v1",
                    "api_key": os.getenv('OPENAI_API_KEY', ''),
                    "model_name": "gpt-4o-mini",
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "is_active": True,
                    "priority": 2
                }
            }
        }
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取指定服务配置"""
        config = self.load_config()
        return config.get('services', {}).get(service_name)
    
    def get_default_service_config(self) -> Optional[Dict[str, Any]]:
        """获取默认服务配置"""
        config = self.load_config()
        default_service = config.get('default_service')
        if default_service:
            return self.get_service_config(default_service)
        return None
    
    def get_active_services(self) -> List[Dict[str, Any]]:
        """获取所有活跃的服务配置"""
        config = self.load_config()
        services = []
        for name, service_config in config.get('services', {}).items():
            if service_config.get('is_active', True):
                service_config['service_name'] = name
                services.append(service_config)
        
        # 按优先级排序
        return sorted(services, key=lambda x: x.get('priority', 100))
    
    def add_service(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """添加新服务配置"""
        try:
            config = self.load_config()
            
            # 验证服务配置
            self._validate_service_config(service_name, service_config)
            
            # 添加服务
            config['services'][service_name] = service_config
            
            # 保存配置
            return self.save_config(config)
        except Exception as e:
            logger.error(f"添加服务配置失败: {e}")
            return False
    
    def update_service(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """更新服务配置"""
        try:
            config = self.load_config()
            
            if service_name not in config['services']:
                raise ValidationError(f"服务 {service_name} 不存在")
            
            # 验证服务配置
            self._validate_service_config(service_name, service_config)
            
            # 更新服务
            config['services'][service_name] = service_config
            
            # 保存配置
            return self.save_config(config)
        except Exception as e:
            logger.error(f"更新服务配置失败: {e}")
            return False
    
    def remove_service(self, service_name: str) -> bool:
        """删除服务配置"""
        try:
            config = self.load_config()
            
            if service_name not in config['services']:
                raise ValidationError(f"服务 {service_name} 不存在")
            
            # 检查是否为默认服务
            if config.get('default_service') == service_name:
                raise ValidationError(f"不能删除默认服务 {service_name}")
            
            # 删除服务
            del config['services'][service_name]
            
            # 保存配置
            return self.save_config(config)
        except Exception as e:
            logger.error(f"删除服务配置失败: {e}")
            return False
    
    def set_default_service(self, service_name: str) -> bool:
        """设置默认服务"""
        try:
            config = self.load_config()
            
            if service_name not in config['services']:
                raise ValidationError(f"服务 {service_name} 不存在")
            
            config['default_service'] = service_name
            return self.save_config(config)
        except Exception as e:
            logger.error(f"设置默认服务失败: {e}")
            return False


class AIServiceManager:
    """AI服务管理器 - 负责服务的动态切换和故障处理"""

    def __init__(self):
        self.config_manager = AIConfigFileManager()
        # 注意：不同用户可能配置不同的默认服务，必须隔离缓存
        self._current_service = None  # 全局/无用户场景
        self._current_service_by_user: Dict[str, Dict[str, Any]] = {}
        self._service_cache = {}
        self._lock = threading.RLock()

    def clear_cache(self, user=None):
        with self._lock:
            try:
                self._service_cache.clear()
            except Exception as e:
                logger.warning(f"清理服务缓存时发生异常，重建缓存: {e}")
                self._service_cache = {}
            if user is None:
                self._current_service = None
                self._current_service_by_user.clear()
            else:
                user_key = str(getattr(user, 'pk', 'global') or 'global')
                self._current_service_by_user.pop(user_key, None)
        
        try:
            from .factory import ai_service_factory
            # 工厂侧也需要同步清缓存（支持按用户缓存）
            if hasattr(ai_service_factory, 'clear_cache'):
                ai_service_factory.clear_cache(user=user)
        except Exception as e:
            logger.warning(f"同步清理工厂缓存失败: {e}", exc_info=True)

    def get_current_service_config(self, user=None) -> Optional[Dict[str, Any]]:
        """获取当前使用的服务配置"""
        with self._lock:
            if user is None and self._current_service:
                return copy.deepcopy(self._current_service)
            if user is not None:
                user_key = str(getattr(user, 'pk', 'global') or 'global')
                cached = self._current_service_by_user.get(user_key)
                if cached:
                    return copy.deepcopy(cached)

        # 尝试从数据库获取默认配置
        logger.debug("AIServiceManager: 开始从数据库获取默认AI配置...")
        try:
            # 1) 优先：用户自己的默认配置
            if user:
                user_default = AIServiceConfig.objects.filter(
                    is_active=True,
                    is_default=True,
                    created_by=user
                ).order_by('priority').first()
                if user_default:
                    logger.debug(
                        f"AIServiceManager: 命中用户默认配置: ID={user_default.id}, 名称='{user_default.name}'"
                    )
                    with self._lock:
                        cfg = self._db_config_to_dict(user_default)
                        user_key = str(getattr(user, 'pk', 'global') or 'global')
                        self._current_service_by_user[user_key] = cfg
                        return copy.deepcopy(cfg)

                # 2) 其次：用户任意可用配置（按优先级）
                user_any = AIServiceConfig.objects.filter(
                    is_active=True,
                    created_by=user
                ).order_by('priority').first()
                if user_any:
                    logger.debug(
                        f"AIServiceManager: 用户无默认配置，使用用户优先级最高配置: "
                        f"ID={user_any.id}, 名称='{user_any.name}'"
                    )
                    with self._lock:
                        cfg = self._db_config_to_dict(user_any)
                        user_key = str(getattr(user, 'pk', 'global') or 'global')
                        self._current_service_by_user[user_key] = cfg
                        return copy.deepcopy(cfg)

            # 3) 全局默认配置（任意用户创建的默认）
            db_config = AIServiceConfig.objects.filter(
                is_active=True,
                is_default=True
            ).order_by('priority').first()

            if db_config:
                logger.debug(f"AIServiceManager: 成功从数据库找到默认配置: ID={db_config.id}, 名称='{db_config.name}'")
                with self._lock:
                    cfg = self._db_config_to_dict(db_config)
                    if user is None:
                        self._current_service = cfg
                    else:
                        user_key = str(getattr(user, 'pk', 'global') or 'global')
                        self._current_service_by_user[user_key] = cfg
                    return copy.deepcopy(cfg)
            else:
                logger.debug("AIServiceManager: 数据库中没有找到激活的默认配置。")
        except Exception as e:
            logger.warning(f"AIServiceManager: 从数据库获取配置时发生错误: {e}")

        # 从配置文件获取默认配置
        logger.debug("AIServiceManager: 尝试从JSON配置文件获取默认配置...")
        file_config = self.config_manager.get_default_service_config()
        if file_config:
            logger.debug(f"AIServiceManager: 成功从JSON文件找到默认配置: 名称='{file_config.get('name')}'")
            with self._lock:
                if user is None:
                    self._current_service = file_config
                else:
                    user_key = str(getattr(user, 'pk', 'global') or 'global')
                    self._current_service_by_user[user_key] = file_config
                return copy.deepcopy(file_config)
        else:
            logger.debug("AIServiceManager: JSON配置文件中也没有找到默认配置。")

        # 最后回退到环境变量配置
        logger.debug("AIServiceManager: 回退到环境变量配置。")
        return self._get_env_fallback_config()

    def get_available_services(self, user=None) -> List[Dict[str, Any]]:
        """获取所有可用的服务配置"""
        services = []

        # 从数据库获取配置
        try:
            queryset = AIServiceConfig.objects.filter(is_active=True)
            # 用户隔离：如果提供了用户，只查询该用户的配置
            if user:
                queryset = queryset.filter(created_by=user)
            
            db_configs = queryset.order_by('priority')
            for config in db_configs:
                services.append(self._db_config_to_dict(config))
        except Exception as e:
            logger.warning(f"从数据库获取服务列表失败: {e}")

        # 如果数据库没有配置，从文件获取
        if not services:
            services = self.config_manager.get_active_services()

        return services

    def switch_service(self, service_name: str, user=None) -> bool:
        """切换到指定服务"""
        try:
            # 从数据库查找服务
            queryset = AIServiceConfig.objects.filter(
                name=service_name,
                is_active=True
            )
            # 用户隔离：如果提供了用户，只查询该用户的配置
            if user:
                queryset = queryset.filter(created_by=user)
            
            db_config = queryset.first()

            if db_config:
                with self._lock:
                    cfg = self._db_config_to_dict(db_config)
                    if user is None:
                        self._current_service = cfg
                    else:
                        user_key = str(getattr(user, 'pk', 'global') or 'global')
                        self._current_service_by_user[user_key] = cfg
                self._log_service_switch(service_name, user, 'database')
                try:
                    from .factory import ai_service_factory
                    # 工厂已改为按用户缓存，切换成功后必须清理对应用户缓存
                    if hasattr(ai_service_factory, 'clear_cache'):
                        ai_service_factory.clear_cache(user=user)
                except Exception as e:
                    logger.warning(f"切换服务时同步清理工厂缓存失败: {e}", exc_info=True)
                return True

            # 从配置文件查找服务
            file_config = self.config_manager.get_service_config(service_name)
            if file_config and file_config.get('is_active', True):
                with self._lock:
                    if user is None:
                        self._current_service = file_config
                    else:
                        user_key = str(getattr(user, 'pk', 'global') or 'global')
                        self._current_service_by_user[user_key] = file_config
                self._log_service_switch(service_name, user, 'file')
                # 失效工厂缓存，确保下次获取到新实例
                try:
                    from .factory import ai_service_factory
                    if hasattr(ai_service_factory, 'clear_cache'):
                        ai_service_factory.clear_cache(user=user)
                except Exception as e:
                    logger.warning(f"切换服务时同步清理工厂缓存失败: {e}", exc_info=True)
                return True

            logger.error(f"服务 {service_name} 不存在或未激活")
            return False

        except Exception as e:
            logger.error(f"切换服务失败: {e}")
            return False

    def test_service(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试服务配置"""
        test_result = {
            'success': False,
            'response_time_ms': None,
            'error_message': '',
            'test_time': timezone.now().isoformat()
        }

        try:
            start_time = timezone.now()

            # 根据API格式选择测试方法
            if service_config.get('api_format') == 'gemini':
                result = self._test_gemini_service(service_config)
            elif service_config.get('api_format') == 'openai':
                result = self._test_openai_service(service_config)
            else:
                raise ValueError(f"不支持的API格式: {service_config.get('api_format')}")

            end_time = timezone.now()
            test_result['response_time_ms'] = int((end_time - start_time).total_seconds() * 1000)
            test_result['success'] = True
            test_result.update(result)

        except Exception as e:
            try:
                end_time = timezone.now()
                # 失败也记录耗时，便于前端展示“超时/快速失败”
                test_result['response_time_ms'] = int((end_time - start_time).total_seconds() * 1000)
            except Exception:
                pass
            test_result['error_message'] = str(e)
            logger.error(f"服务测试失败: {e}")

        return test_result

    def handle_service_failure(self, failed_service: str, error: str, user=None) -> Optional[Dict[str, Any]]:
        """处理服务故障，尝试切换到备用服务"""
        logger.warning(f"服务 {failed_service} 故障: {error}")

        # 记录故障
        self._log_service_failure(failed_service, error, user)

        # 获取备用服务列表（按用户隔离）
        available_services = self.get_available_services(user=user)

        for service in available_services:
            service_name = service.get('service_name') or service.get('name')
            if service_name and service_name != failed_service:
                logger.info(f"尝试切换到备用服务: {service_name}")

                # 测试备用服务
                test_result = self.test_service(service)
                if test_result['success']:
                    self.switch_service(service_name, user)
                    logger.info(f"成功切换到备用服务: {service_name}")
                    return service
                else:
                    logger.warning(f"备用服务 {service_name} 也不可用: {test_result['error_message']}")

        # 所有服务都不可用，回退到环境变量配置
        logger.error("所有配置的服务都不可用，回退到环境变量配置")
        env_config = self._get_env_fallback_config()
        if env_config:
            with self._lock:
                self._current_service = env_config
            return env_config

        return None

    def _db_config_to_dict(self, db_config: AIServiceConfig) -> Dict[str, Any]:
        """将数据库配置转换为字典格式"""
        return {
            'id': db_config.pk,
            'name': db_config.name,
            'provider': db_config.provider,
            'api_format': db_config.api_format,
            'api_base_url': db_config.api_base_url,
            'api_key': db_config.api_key,
            'model_name': db_config.model_name,
            'timeout_seconds': db_config.timeout_seconds,
            'max_retries': db_config.max_retries,
            'extra_config': db_config.extra_config,
            'is_active': db_config.is_active,
            'priority': db_config.priority,
        }

    def _get_env_fallback_config(self) -> Optional[Dict[str, Any]]:
        """获取环境变量回退配置"""
        use_openai = getattr(settings, 'USE_OPENAI_OCR', False)

        if use_openai and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            return {
                'name': 'OpenAI环境变量配置',
                'provider': 'openai',
                'api_format': 'openai',
                'api_base_url': getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'api_key': settings.OPENAI_API_KEY,
                'model_name': getattr(settings, 'OPENAI_MODEL_NAME', 'gpt-4o-mini'),
                'timeout_seconds': getattr(settings, 'API_TIMEOUT_SECONDS', 30),
                'max_retries': 3,
                'is_active': True,
                'priority': 999,  # 最低优先级
            }
        elif hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            return {
                'name': 'Gemini环境变量配置',
                'provider': 'gemini',
                'api_format': 'gemini',
                'api_base_url': getattr(settings, 'GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com'),
                'api_key': settings.GEMINI_API_KEY,
                'model_name': getattr(settings, 'GEMINI_MODEL_NAME', 'gemini-2.0-flash-exp-image-generation'),
                'timeout_seconds': getattr(settings, 'API_TIMEOUT_SECONDS', 30),
                'max_retries': 3,
                'is_active': True,
                'priority': 999,  # 最低优先级
            }

        return None

    def _test_gemini_service(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试Gemini服务"""
        import requests

        url = f"{config['api_base_url']}/v1beta/models/{config['model_name']}:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': config['api_key']
        }

        # 简单的测试请求
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "测试连接，请回复'连接成功'"
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=config.get('timeout_seconds', 30)
        )

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                raise Exception("Gemini API返回200但不是合法JSON")

            # 尝试解析出模型文本，确保“确实可用”而不仅是 HTTP 200
            text = None
            try:
                if data.get('candidates'):
                    cand0 = data['candidates'][0]
                    parts = cand0.get('content', {}).get('parts') or []
                    if parts and isinstance(parts[0], dict):
                        text = parts[0].get('text')
            except Exception:
                text = None

            if not text or not str(text).strip():
                raise Exception("Gemini API返回200但未解析到模型输出文本")

            return {
                'message': 'Gemini服务连接成功',
                'sample_output': str(text).strip()[:200],
            }
        else:
            raise Exception(f"Gemini API错误: {response.status_code} - {response.text}")

    def _test_openai_service(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """测试OpenAI服务"""
        """
        重要：测试必须与“真实调用”使用同一套代码路径，否则会出现：
        - 真实调用可用
        - 但测试因解析/参数差异误判失败
        """
        from .factory import OpenAIAIService

        service = OpenAIAIService(config, self)
        resp = service.process_request({
            'type': 'text',
            'prompt': 'hi',
            'service_type': 'test_openai',
            'user': None,
        })

        text = (resp or {}).get('generated_text')
        if not text or not str(text).strip():
            raise Exception("OpenAI接口返回但未解析到模型输出文本")

        return {
            'message': 'OpenAI服务连接成功',
            'sample_output': str(text).strip()[:200],
        }

    def _log_service_switch(self, service_name: str, user, source: str):
        """记录服务切换日志"""
        logger.info(f"服务切换: {service_name} (来源: {source}, 用户: {user})")

    def _log_service_failure(self, service_name: str, error: str, user):
        """记录服务故障日志"""
        logger.error(f"服务故障: {service_name}, 错误: {error}, 用户: {user}")


# 全局服务管理器实例
ai_service_manager = AIServiceManager()
