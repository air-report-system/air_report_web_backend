"""
用户认证模型
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """自定义用户模型"""
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    phone = models.CharField(max_length=20, blank=True, verbose_name='电话号码')
    company = models.CharField(max_length=100, blank=True, verbose_name='公司')
    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', '管理员'),
            ('operator', '操作员'),
            ('viewer', '查看员'),
        ],
        default='operator',
        verbose_name='角色'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """用户配置信息"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    default_ocr_settings = models.JSONField(default=dict, verbose_name='默认OCR设置')
    ui_preferences = models.JSONField(default=dict, verbose_name='界面偏好')
    notification_settings = models.JSONField(default=dict, verbose_name='通知设置')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '用户配置'
        verbose_name_plural = '用户配置'

    def __str__(self):
        return f"{self.user.username}的配置"
