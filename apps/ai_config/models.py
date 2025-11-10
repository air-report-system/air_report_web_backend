"""
AI配置管理模型
"""
from django.db import models
from django.db.models import F
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator
from django.utils import timezone
from apps.core.models import BaseModel

User = get_user_model()


class AIServiceProvider(models.TextChoices):
    """AI服务提供商选择"""
    GEMINI = 'gemini', 'Google Gemini'
    OPENAI = 'openai', 'OpenAI'
    ANTHROPIC = 'anthropic', 'Anthropic Claude'
    CUSTOM = 'custom', '自定义服务'


class AIServiceFormat(models.TextChoices):
    """AI服务API格式"""
    GEMINI = 'gemini', 'Gemini格式'
    OPENAI = 'openai', 'OpenAI格式'


class AIServiceConfig(BaseModel):
    """AI服务配置模型"""
    
    # 基本信息
    name = models.CharField(max_length=100, verbose_name='配置名称', help_text='用于识别的配置名称')
    description = models.TextField(blank=True, verbose_name='配置描述')
    provider = models.CharField(
        max_length=20, 
        choices=AIServiceProvider.choices, 
        verbose_name='服务提供商'
    )
    
    # API配置
    api_format = models.CharField(
        max_length=20,
        choices=AIServiceFormat.choices,
        verbose_name='API格式',
        help_text='API调用格式（Gemini格式或OpenAI格式）'
    )
    api_base_url = models.URLField(
        verbose_name='API基础URL',
        validators=[URLValidator()],
        help_text='API服务的基础URL'
    )
    api_key = models.CharField(
        max_length=500,
        verbose_name='API密钥',
        help_text='API访问密钥，将被加密存储'
    )
    model_name = models.CharField(
        max_length=100, 
        verbose_name='模型名称',
        help_text='使用的AI模型名称'
    )
    
    # 高级配置
    timeout_seconds = models.PositiveIntegerField(
        default=30, 
        verbose_name='超时时间（秒）'
    )
    max_retries = models.PositiveIntegerField(
        default=3, 
        verbose_name='最大重试次数'
    )
    
    # 额外配置（JSON格式）
    extra_config = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='额外配置',
        help_text='其他配置参数，JSON格式'
    )
    
    # 状态管理
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    is_default = models.BooleanField(default=False, verbose_name='是否为默认配置')
    priority = models.PositiveIntegerField(
        default=100, 
        verbose_name='优先级',
        help_text='数值越小优先级越高，用于故障切换'
    )
    
    # 使用统计
    success_count = models.PositiveIntegerField(default=0, verbose_name='成功调用次数')
    failure_count = models.PositiveIntegerField(default=0, verbose_name='失败调用次数')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')
    last_test_at = models.DateTimeField(null=True, blank=True, verbose_name='最后测试时间')
    last_test_result = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='最后测试结果'
    )
    


    class Meta:
        ordering = ['priority', '-created_at']
        verbose_name = 'AI服务配置'
        verbose_name_plural = 'AI服务配置'
        constraints = [
            models.UniqueConstraint(
                fields=['is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_config'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            from django.db import transaction
            
            with transaction.atomic():
                # 取消其他所有默认配置
                AIServiceConfig.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
    
    @property
    def success_rate(self):
        """成功率计算"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0
        return round((self.success_count / total) * 100, 2)
    
    def increment_success(self):
        """增加成功计数"""
        self.__class__.objects.filter(pk=self.pk).update(
            success_count=F('success_count') + 1,
            last_used_at=timezone.now()
        )
        self.refresh_from_db(fields=['success_count', 'last_used_at'])
    
    def increment_failure(self):
        """增加失败计数"""
        self.__class__.objects.filter(pk=self.pk).update(
            failure_count=F('failure_count') + 1
        )
        self.refresh_from_db(fields=['failure_count'])
    
    def update_test_result(self, result):
        """更新测试结果"""
        self.last_test_at = timezone.now()
        self.last_test_result = result
        self.save(update_fields=['last_test_at', 'last_test_result'])


class AIConfigHistory(BaseModel):
    """AI配置变更历史"""
    
    config = models.ForeignKey(
        AIServiceConfig, 
        on_delete=models.CASCADE, 
        related_name='history',
        verbose_name='配置'
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('create', '创建'),
            ('update', '更新'),
            ('delete', '删除'),
            ('test', '测试'),
            ('activate', '激活'),
            ('deactivate', '停用'),
        ],
        verbose_name='操作类型'
    )
    old_data = models.JSONField(null=True, blank=True, verbose_name='变更前数据')
    new_data = models.JSONField(null=True, blank=True, verbose_name='变更后数据')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_config_history',
        verbose_name='操作用户'
    )
    notes = models.TextField(blank=True, verbose_name='备注')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI配置变更历史'
        verbose_name_plural = 'AI配置变更历史'

    def __str__(self):
        return f"{self.config.name} - {self.get_action_display()} ({self.created_at})"


class AIServiceUsageLog(BaseModel):
    """AI服务使用日志"""
    
    config = models.ForeignKey(
        AIServiceConfig, 
        on_delete=models.CASCADE, 
        related_name='usage_logs',
        verbose_name='使用的配置'
    )
    service_type = models.CharField(
        max_length=50,
        verbose_name='服务类型',
        help_text='OCR、订单处理等'
    )
    request_data = models.JSONField(verbose_name='请求数据')
    response_data = models.JSONField(null=True, blank=True, verbose_name='响应数据')
    is_success = models.BooleanField(verbose_name='是否成功')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    response_time_ms = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name='响应时间（毫秒）'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_usage_logs',
        verbose_name='用户'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI服务使用日志'
        verbose_name_plural = 'AI服务使用日志'
        indexes = [
            models.Index(fields=['config', '-created_at']),
            models.Index(fields=['service_type', '-created_at']),
            models.Index(fields=['is_success', '-created_at']),
        ]

    def __str__(self):
        status = "成功" if self.is_success else "失败"
        return f"{self.config.name} - {self.service_type} - {status}"
