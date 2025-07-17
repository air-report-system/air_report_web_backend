"""
AI配置系统监控和错误处理
"""
import logging
import time
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import AIServiceConfig, AIServiceUsageLog
from .logging_config import log_api_call, log_service_health, AILoggerMixin

logger = logging.getLogger(__name__)


class AIServiceMonitor(AILoggerMixin):
    """AI服务监控器"""

    def __init__(self):
        super().__init__()
        self.cache_timeout = getattr(settings, 'AI_MONITOR_CACHE_TIMEOUT', 300)  # 5分钟
        self.error_threshold = getattr(settings, 'AI_ERROR_THRESHOLD', 5)  # 错误阈值
        self.monitor_window = getattr(settings, 'AI_MONITOR_WINDOW', 3600)  # 监控窗口1小时
    
    def record_service_call(self, service_config: Dict[str, Any], 
                          service_type: str, success: bool, 
                          response_time_ms: Optional[int] = None,
                          error_message: str = '', user=None):
        """记录服务调用"""
        try:
            # 如果是数据库配置，记录到数据库
            if 'id' in service_config:
                config_obj = AIServiceConfig.objects.get(id=service_config['id'])
                
                AIServiceUsageLog.objects.create(
                    config=config_obj,
                    service_type=service_type,
                    request_data={'service_type': service_type},
                    response_data={'success': success} if success else None,
                    is_success=success,
                    error_message=error_message,
                    response_time_ms=response_time_ms,
                    user=user
                )
                
                # 更新配置统计
                if success:
                    config_obj.increment_success()
                else:
                    config_obj.increment_failure()
            
            # 记录到缓存用于实时监控
            cache_key = f"ai_service_stats_{service_config.get('name', 'unknown')}"
            stats = cache.get(cache_key, {
                'total_calls': 0,
                'success_calls': 0,
                'error_calls': 0,
                'avg_response_time': 0,
                'last_error': None,
                'error_count_in_window': 0
            })
            
            stats['total_calls'] += 1
            if success:
                stats['success_calls'] += 1
                if response_time_ms:
                    # 计算平均响应时间
                    total_time = stats['avg_response_time'] * (stats['total_calls'] - 1) + response_time_ms
                    stats['avg_response_time'] = total_time / stats['total_calls']
            else:
                stats['error_calls'] += 1
                stats['last_error'] = {
                    'message': error_message,
                    'timestamp': timezone.now().isoformat()
                }
                
                # 检查错误窗口
                error_window_key = f"ai_errors_{service_config.get('name', 'unknown')}"
                error_count = cache.get(error_window_key, 0) + 1
                cache.set(error_window_key, error_count, self.monitor_window)
                stats['error_count_in_window'] = error_count
                
                # 如果错误超过阈值，记录警告
                if error_count >= self.error_threshold:
                    self.log_warning(
                        f"AI服务 {service_config.get('name')} 在 {self.monitor_window} 秒内"
                        f"出现 {error_count} 次错误，超过阈值 {self.error_threshold}",
                        service_name=service_config.get('name'),
                        error_count=error_count,
                        threshold=self.error_threshold,
                        window_seconds=self.monitor_window
                    )

                    # 记录服务健康状态
                    log_service_health(
                        service_config.get('name', 'unknown'),
                        'critical',
                        {'error_count': error_count, 'threshold': self.error_threshold}
                    )
            
            cache.set(cache_key, stats, self.cache_timeout)
            
        except Exception as e:
            logger.error(f"记录服务调用失败: {e}")
    
    def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """获取服务统计信息"""
        cache_key = f"ai_service_stats_{service_name}"
        return cache.get(cache_key, {})
    
    def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """检查服务健康状态"""
        stats = self.get_service_stats(service_name)
        
        if not stats:
            return {
                'status': 'unknown',
                'message': '没有统计数据'
            }
        
        total_calls = stats.get('total_calls', 0)
        error_calls = stats.get('error_calls', 0)
        error_count_in_window = stats.get('error_count_in_window', 0)
        
        if total_calls == 0:
            return {
                'status': 'unknown',
                'message': '没有调用记录'
            }
        
        error_rate = error_calls / total_calls
        
        # 判断健康状态
        if error_count_in_window >= self.error_threshold:
            status = 'critical'
            message = f'近期错误过多: {error_count_in_window} 次'
        elif error_rate > 0.5:
            status = 'warning'
            message = f'错误率较高: {error_rate:.1%}'
        elif error_rate > 0.1:
            status = 'degraded'
            message = f'错误率: {error_rate:.1%}'
        else:
            status = 'healthy'
            message = f'运行正常，错误率: {error_rate:.1%}'
        
        return {
            'status': status,
            'message': message,
            'stats': stats
        }


class AIServiceErrorHandler:
    """AI服务错误处理器"""
    
    def __init__(self):
        self.monitor = AIServiceMonitor()
    
    def handle_api_error(self, error: Exception, service_config: Dict[str, Any], 
                        service_type: str, user=None) -> Dict[str, Any]:
        """处理API错误"""
        error_message = str(error)
        error_type = type(error).__name__
        
        # 记录错误
        logger.error(
            f"AI服务API错误 - 服务: {service_config.get('name', 'unknown')}, "
            f"类型: {error_type}, 消息: {error_message}",
            exc_info=True
        )
        
        # 记录到监控系统
        self.monitor.record_service_call(
            service_config=service_config,
            service_type=service_type,
            success=False,
            error_message=error_message,
            user=user
        )
        
        # 分析错误类型并提供建议
        suggestions = self._analyze_error(error, service_config)
        
        return {
            'error_type': error_type,
            'error_message': error_message,
            'service_name': service_config.get('name', 'unknown'),
            'suggestions': suggestions,
            'timestamp': timezone.now().isoformat()
        }
    
    def _analyze_error(self, error: Exception, service_config: Dict[str, Any]) -> list:
        """分析错误并提供建议"""
        suggestions = []
        error_message = str(error).lower()
        
        # API密钥相关错误
        if 'api key' in error_message or 'unauthorized' in error_message:
            suggestions.extend([
                '检查API密钥是否正确',
                '确认API密钥是否已过期',
                '验证API密钥权限是否足够'
            ])
        
        # 网络连接错误
        elif 'connection' in error_message or 'timeout' in error_message:
            suggestions.extend([
                '检查网络连接',
                '确认API服务器是否可访问',
                '考虑增加超时时间',
                '检查防火墙设置'
            ])
        
        # 配额限制错误
        elif 'quota' in error_message or 'rate limit' in error_message:
            suggestions.extend([
                '检查API配额使用情况',
                '考虑升级API计划',
                '实施请求频率限制',
                '切换到备用服务'
            ])
        
        # 模型相关错误
        elif 'model' in error_message:
            suggestions.extend([
                '检查模型名称是否正确',
                '确认模型是否可用',
                '尝试使用其他模型'
            ])
        
        # 请求格式错误
        elif 'format' in error_message or 'invalid' in error_message:
            suggestions.extend([
                '检查请求格式是否正确',
                '验证API参数',
                '确认API版本兼容性'
            ])
        
        # 通用建议
        if not suggestions:
            suggestions.extend([
                '检查服务配置',
                '查看详细错误日志',
                '尝试重新测试服务',
                '联系技术支持'
            ])
        
        return suggestions


def monitor_ai_service(service_type: str = 'unknown'):
    """AI服务监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            monitor = AIServiceMonitor()
            error_handler = AIServiceErrorHandler()
            
            # 尝试从参数中获取服务配置和用户
            service_config = kwargs.get('service_config') or (args[0] if args else {})
            user = kwargs.get('user')
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功调用
                response_time_ms = int((time.time() - start_time) * 1000)
                monitor.record_service_call(
                    service_config=service_config,
                    service_type=service_type,
                    success=True,
                    response_time_ms=response_time_ms,
                    user=user
                )
                
                return result
                
            except Exception as e:
                # 记录失败调用
                response_time_ms = int((time.time() - start_time) * 1000)
                error_info = error_handler.handle_api_error(
                    error=e,
                    service_config=service_config,
                    service_type=service_type,
                    user=user
                )
                
                # 重新抛出异常，但附加错误信息
                if hasattr(e, '__dict__'):
                    e.__dict__['error_info'] = error_info
                raise e
        
        return wrapper
    return decorator


def log_ai_operation(operation: str, details: Optional[Dict[str, Any]] = None):
    """记录AI操作日志"""
    log_data = {
        'operation': operation,
        'timestamp': timezone.now().isoformat(),
        'details': details or {}
    }
    
    logger.info(f"AI操作: {operation}", extra=log_data)


def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    monitor = AIServiceMonitor()
    
    # 获取所有活跃的AI配置
    active_configs = AIServiceConfig.objects.filter(is_active=True)
    
    health_status = {
        'overall_status': 'healthy',
        'services': {},
        'summary': {
            'total_services': active_configs.count(),
            'healthy_services': 0,
            'warning_services': 0,
            'critical_services': 0
        },
        'timestamp': timezone.now().isoformat()
    }
    
    for config in active_configs:
        service_health = monitor.check_service_health(config.name)
        health_status['services'][config.name] = service_health
        
        # 统计服务状态
        status = service_health.get('status', 'unknown')
        if status == 'healthy':
            health_status['summary']['healthy_services'] += 1
        elif status in ['warning', 'degraded']:
            health_status['summary']['warning_services'] += 1
        elif status == 'critical':
            health_status['summary']['critical_services'] += 1
    
    # 确定整体状态
    if health_status['summary']['critical_services'] > 0:
        health_status['overall_status'] = 'critical'
    elif health_status['summary']['warning_services'] > 0:
        health_status['overall_status'] = 'warning'
    
    return health_status


# 全局监控实例
ai_monitor = AIServiceMonitor()
ai_error_handler = AIServiceErrorHandler()
