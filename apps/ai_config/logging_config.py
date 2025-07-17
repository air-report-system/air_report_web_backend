"""
AI配置系统日志配置
"""
import logging
import os
from pathlib import Path
from django.conf import settings


def setup_ai_logging():
    """设置AI配置系统的日志配置"""
    
    # 创建日志目录
    log_dir = Path(settings.BASE_DIR) / 'logs' / 'ai_config'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # AI配置系统专用日志器
    ai_logger = logging.getLogger('apps.ai_config')
    ai_logger.setLevel(logging.INFO)
    
    # 如果已经有处理器，不重复添加
    if ai_logger.handlers:
        return ai_logger
    
    # 文件处理器 - 一般日志
    file_handler = logging.FileHandler(
        log_dir / 'ai_config.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 文件处理器 - 错误日志
    error_handler = logging.FileHandler(
        log_dir / 'ai_config_errors.log',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    
    # 文件处理器 - API调用日志
    api_handler = logging.FileHandler(
        log_dir / 'ai_api_calls.log',
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    
    # 控制台处理器（开发环境）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # 日志格式
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    api_formatter = logging.Formatter(
        '%(asctime)s - API - %(levelname)s - %(message)s'
    )
    
    # 设置格式
    file_handler.setFormatter(detailed_formatter)
    error_handler.setFormatter(detailed_formatter)
    api_handler.setFormatter(api_formatter)
    console_handler.setFormatter(simple_formatter)
    
    # 添加处理器
    ai_logger.addHandler(file_handler)
    ai_logger.addHandler(error_handler)
    ai_logger.addHandler(console_handler)
    
    # API调用专用日志器
    api_logger = logging.getLogger('apps.ai_config.api')
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(api_handler)
    api_logger.propagate = False  # 不传播到父日志器
    
    # 监控专用日志器
    monitor_logger = logging.getLogger('apps.ai_config.monitor')
    monitor_logger.setLevel(logging.INFO)
    
    monitor_handler = logging.FileHandler(
        log_dir / 'ai_monitor.log',
        encoding='utf-8'
    )
    monitor_handler.setLevel(logging.INFO)
    monitor_handler.setFormatter(detailed_formatter)
    monitor_logger.addHandler(monitor_handler)
    monitor_logger.propagate = False
    
    return ai_logger


def log_api_call(service_name: str, operation: str, success: bool, 
                response_time_ms: int = None, error_message: str = None):
    """记录API调用日志"""
    api_logger = logging.getLogger('apps.ai_config.api')
    
    log_data = {
        'service': service_name,
        'operation': operation,
        'success': success,
        'response_time_ms': response_time_ms
    }
    
    if success:
        message = f"API调用成功 - 服务: {service_name}, 操作: {operation}"
        if response_time_ms:
            message += f", 响应时间: {response_time_ms}ms"
        api_logger.info(message, extra=log_data)
    else:
        message = f"API调用失败 - 服务: {service_name}, 操作: {operation}"
        if error_message:
            message += f", 错误: {error_message}"
        api_logger.error(message, extra=log_data)


def log_service_switch(from_service: str, to_service: str, reason: str = None):
    """记录服务切换日志"""
    logger = logging.getLogger('apps.ai_config.monitor')
    
    message = f"服务切换 - 从 {from_service} 切换到 {to_service}"
    if reason:
        message += f", 原因: {reason}"
    
    logger.info(message, extra={
        'from_service': from_service,
        'to_service': to_service,
        'reason': reason
    })


def log_service_health(service_name: str, status: str, details: dict = None):
    """记录服务健康状态日志"""
    logger = logging.getLogger('apps.ai_config.monitor')
    
    message = f"服务健康检查 - {service_name}: {status}"
    
    log_data = {
        'service': service_name,
        'health_status': status,
        'details': details or {}
    }
    
    if status in ['critical', 'warning']:
        logger.warning(message, extra=log_data)
    else:
        logger.info(message, extra=log_data)


def log_config_change(config_name: str, action: str, user: str = None, details: dict = None):
    """记录配置变更日志"""
    logger = logging.getLogger('apps.ai_config')
    
    message = f"配置变更 - {config_name}: {action}"
    if user:
        message += f" (用户: {user})"
    
    log_data = {
        'config': config_name,
        'action': action,
        'user': user,
        'details': details or {}
    }
    
    logger.info(message, extra=log_data)


class AILoggerMixin:
    """AI日志记录混入类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f'apps.ai_config.{self.__class__.__name__}')
    
    def log_info(self, message: str, **kwargs):
        """记录信息日志"""
        self.logger.info(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, extra=kwargs)
    
    def log_error(self, message: str, exception: Exception = None, **kwargs):
        """记录错误日志"""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """记录调试日志"""
        self.logger.debug(message, extra=kwargs)


# 初始化日志配置
try:
    setup_ai_logging()
except Exception as e:
    # 如果日志配置失败，使用默认日志器记录错误
    logging.getLogger(__name__).error(f"AI日志配置失败: {e}")


# 导出常用的日志函数
__all__ = [
    'setup_ai_logging',
    'log_api_call',
    'log_service_switch',
    'log_service_health',
    'log_config_change',
    'AILoggerMixin'
]
