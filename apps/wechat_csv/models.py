from django.db import models
from django.conf import settings
import json


class WechatCsvRecord(models.Model):
    """微信CSV记录模型"""
    
    # 基本客户信息
    customer_name = models.CharField('客户姓名', max_length=100)
    customer_phone = models.CharField('客户电话', max_length=20, blank=True)
    customer_address = models.TextField('客户地址')
    
    # 产品和交易信息
    product_type = models.CharField('商品类型', max_length=20, choices=[
        ('国标', '国标'),
        ('母婴', '母婴'),
    ], blank=True)
    transaction_amount = models.DecimalField('成交金额', max_digits=10, decimal_places=2, null=True, blank=True)
    area = models.DecimalField('面积', max_digits=10, decimal_places=2, null=True, blank=True)
    fulfillment_date = models.DateField('履约时间', null=True, blank=True)
    
    # 扩展信息
    cma_points = models.CharField('CMA点位数量', max_length=50, blank=True)
    gift_notes = models.TextField('备注赠品', blank=True, help_text='格式：{品类:数量}')
    
    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建者')
    
    # 关联的处理历史
    processing_history = models.ForeignKey('ProcessingHistory', on_delete=models.CASCADE, 
                                         related_name='records', null=True, blank=True)
    
    class Meta:
        verbose_name = 'CSV记录'
        verbose_name_plural = 'CSV记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer_phone']),
            models.Index(fields=['customer_name', 'customer_address']),
            models.Index(fields=['fulfillment_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.customer_address[:50]}"
    
    def to_csv_row(self):
        """转换为CSV行格式"""
        return [
            self.customer_name,
            self.customer_phone,
            self.customer_address,
            self.product_type,
            str(self.transaction_amount) if self.transaction_amount else '',
            str(self.area) if self.area else '',
            self.fulfillment_date.strftime('%Y-%m-%d') if self.fulfillment_date else '',
            self.cma_points,
            self.gift_notes
        ]


class ProcessingHistory(models.Model):
    """处理历史模型"""
    
    STATUS_CHOICES = [
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('submitted', '已提交'),
    ]
    
    # 原始数据
    original_message = models.TextField('原始微信消息')
    formatted_csv = models.TextField('格式化后的CSV', blank=True)
    
    # 处理状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='processing')
    error_message = models.TextField('错误信息', blank=True)
    
    # GitHub相关
    github_file_path = models.CharField('GitHub文件路径', max_length=255, blank=True)
    github_commit_sha = models.CharField('提交SHA', max_length=40, blank=True)
    github_commit_url = models.URLField('提交URL', blank=True)
    
    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建者')
    
    class Meta:
        verbose_name = '处理历史'
        verbose_name_plural = '处理历史'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"处理历史 {self.id} - {self.status}"
    
    @property
    def records_count(self):
        """关联的记录数量"""
        return self.records.count()


class ValidationResult(models.Model):
    """验证结果模型"""
    
    processing_history = models.OneToOneField(ProcessingHistory, on_delete=models.CASCADE, 
                                            related_name='validation_result')
    
    # 验证结果
    is_valid = models.BooleanField('是否有效', default=False)
    errors = models.JSONField('错误信息', default=list, blank=True)
    warnings = models.JSONField('警告信息', default=list, blank=True)
    
    # 重复检测结果
    duplicate_indexes = models.JSONField('重复项索引', default=list, blank=True)
    match_details = models.JSONField('匹配详情', default=list, blank=True)
    
    # 格式修正信息
    format_fixes = models.JSONField('格式修正信息', default=list, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '验证结果'
        verbose_name_plural = '验证结果'
    
    def __str__(self):
        return f"验证结果 - {'有效' if self.is_valid else '无效'}"


class LoginAttempt(models.Model):
    """登录尝试记录模型"""
    
    ip_address = models.GenericIPAddressField('IP地址')
    attempts = models.PositiveIntegerField('尝试次数', default=0)
    is_locked = models.BooleanField('是否锁定', default=False)
    locked_until = models.DateTimeField('锁定到', null=True, blank=True)
    last_attempt = models.DateTimeField('最后尝试时间', auto_now=True)
    
    class Meta:
        verbose_name = '登录尝试'
        verbose_name_plural = '登录尝试'
        unique_together = ['ip_address']
    
    def __str__(self):
        return f"{self.ip_address} - {self.attempts}次尝试"
