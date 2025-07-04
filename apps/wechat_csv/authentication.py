"""
微信CSV工具认证和权限控制
"""
from rest_framework import permissions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import timedelta
import logging

from .models import LoginAttempt

logger = logging.getLogger(__name__)


class WechatCsvSessionAuthentication(BaseAuthentication):
    """微信CSV工具会话认证"""
    
    def authenticate(self, request):
        """
        认证用户
        返回 (user, auth) 元组，如果认证失败返回 None
        """
        # 检查会话中的认证状态
        if request.session.get('wechat_csv_authenticated'):
            # 返回匿名用户，但表示已认证
            return (AnonymousUser(), 'wechat_csv_session')
        
        return None
    
    def authenticate_header(self, request):
        """返回认证头"""
        return 'Session'


class WechatCsvPermission(permissions.BasePermission):
    """微信CSV工具权限控制"""
    
    def has_permission(self, request, view):
        """检查用户是否有权限访问"""
        # 检查会话认证
        if request.session.get('wechat_csv_authenticated'):
            return True
        
        # 检查IP是否被锁定
        if self._is_ip_locked(request):
            return False
        
        return False
    
    def _is_ip_locked(self, request):
        """检查IP是否被锁定"""
        ip_address = self._get_client_ip(request)
        
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address)
            if attempt.is_locked and attempt.locked_until:
                return timezone.now() < attempt.locked_until
        except LoginAttempt.DoesNotExist:
            pass
        
        return False
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class IPLockoutMiddleware:
    """IP锁定中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 检查IP是否被锁定（仅对微信CSV相关路径）
        if request.path.startswith('/api/v1/wechat-csv/'):
            if self._is_ip_locked(request):
                from django.http import JsonResponse
                return JsonResponse(
                    {"error": "IP地址已被锁定，请稍后再试"},
                    status=429
                )
        
        response = self.get_response(request)
        return response
    
    def _is_ip_locked(self, request):
        """检查IP是否被锁定"""
        ip_address = self._get_client_ip(request)
        
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address)
            if attempt.is_locked and attempt.locked_until:
                return timezone.now() < attempt.locked_until
        except LoginAttempt.DoesNotExist:
            pass
        
        return False
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LoginAttemptManager:
    """登录尝试管理器"""
    
    @staticmethod
    def record_attempt(request, success=True):
        """记录登录尝试"""
        ip_address = LoginAttemptManager._get_client_ip(request)
        
        try:
            attempt, created = LoginAttempt.objects.get_or_create(ip_address=ip_address)
            
            if success:
                # 登录成功，重置尝试次数
                attempt.attempts = 0
                attempt.is_locked = False
                attempt.locked_until = None
            else:
                # 登录失败，增加尝试次数
                attempt.attempts += 1
                
                # 检查是否需要锁定
                from django.conf import settings
                if attempt.attempts >= settings.WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT:
                    attempt.is_locked = True
                    attempt.locked_until = timezone.now() + timedelta(hours=settings.WECHAT_CSV_LOCKOUT_HOURS)
            
            attempt.save()
        except Exception as e:
            logger.error(f"记录登录尝试失败: {e}")
    
    @staticmethod
    def is_locked(request):
        """检查IP是否被锁定"""
        ip_address = LoginAttemptManager._get_client_ip(request)
        
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address)
            if attempt.is_locked and attempt.locked_until:
                return timezone.now() < attempt.locked_until
        except LoginAttempt.DoesNotExist:
            pass
        
        return False
    
    @staticmethod
    def get_remaining_attempts(request):
        """获取剩余尝试次数"""
        ip_address = LoginAttemptManager._get_client_ip(request)
        
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address)
            from django.conf import settings
            return max(0, settings.WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT - attempt.attempts)
        except LoginAttempt.DoesNotExist:
            from django.conf import settings
            return settings.WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT
    
    @staticmethod
    def get_lockout_time(request):
        """获取锁定剩余时间"""
        ip_address = LoginAttemptManager._get_client_ip(request)
        
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address)
            if attempt.is_locked and attempt.locked_until:
                remaining = attempt.locked_until - timezone.now()
                if remaining.total_seconds() > 0:
                    return remaining
        except LoginAttempt.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def _get_client_ip(request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def cleanup_expired_attempts():
    """清理过期的登录尝试记录"""
    try:
        expired_time = timezone.now() - timedelta(hours=24)
        LoginAttempt.objects.filter(
            last_attempt__lt=expired_time,
            is_locked=False
        ).delete()
        
        # 清理已过期的锁定记录
        LoginAttempt.objects.filter(
            is_locked=True,
            locked_until__lt=timezone.now()
        ).update(
            is_locked=False,
            locked_until=None,
            attempts=0
        )
        
    except Exception as e:
        logger.error(f"清理过期登录尝试记录失败: {e}")
