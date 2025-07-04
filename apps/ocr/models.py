"""
OCR处理模型
"""
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone
from apps.core.models import BaseModel
from apps.files.models import UploadedFile
import logging

logger = logging.getLogger(__name__)


class OCRResult(BaseModel):
    """OCR识别结果"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    CHECK_TYPE_CHOICES = [
        ('initial', '初检'),
        ('recheck', '复检'),
    ]
    
    file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, verbose_name='文件')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    
    # OCR识别字段
    phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
    date = models.CharField(max_length=10, blank=True, verbose_name='采样日期')  # MM-DD格式
    temperature = models.CharField(max_length=10, blank=True, verbose_name='现场温度')
    humidity = models.CharField(max_length=10, blank=True, verbose_name='现场湿度')
    check_type = models.CharField(
        max_length=20, 
        choices=CHECK_TYPE_CHOICES, 
        blank=True,
        verbose_name='检测类型'
    )
    
    # JSON字段存储复杂数据
    points_data = models.JSONField(default=dict, verbose_name='点位数据')  # 点位数据
    raw_response = models.TextField(blank=True, verbose_name='原始API响应')   # 原始API响应
    confidence_score = models.FloatField(null=True, blank=True, verbose_name='置信度分数')
    
    # 多重OCR相关
    ocr_attempts = models.IntegerField(default=1, verbose_name='OCR尝试次数')
    has_conflicts = models.BooleanField(default=False, verbose_name='是否有冲突')
    conflict_details = models.JSONField(default=dict, verbose_name='冲突详情')
    
    # 处理时间统计
    processing_started_at = models.DateTimeField(null=True, blank=True, verbose_name='处理开始时间')
    processing_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理完成时间')
    
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'OCR结果'
        verbose_name_plural = 'OCR结果'
        
    def __str__(self):
        return f"OCR结果 - {self.file.original_name} ({self.status})"
    
    @property
    def processing_duration(self):
        """计算处理耗时"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None


class CSVRecord(BaseModel):
    """CSV记录表 - 与原CSV字段完全一致"""
    # 基本信息 - 与CSV字段名完全一致
    客户姓名 = models.CharField(max_length=100, verbose_name='客户姓名')
    客户电话 = models.CharField(max_length=20, blank=True, verbose_name='客户电话')
    客户地址 = models.TextField(verbose_name='客户地址')

    # 业务信息
    商品类型 = models.CharField(max_length=20, choices=[
        ('国标', '国标'),
        ('母婴', '母婴'),
    ], verbose_name='商品类型(国标/母婴)')
    成交金额 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='成交金额')
    面积 = models.CharField(max_length=20, blank=True, verbose_name='面积')
    履约时间 = models.DateField(null=True, blank=True, verbose_name='履约时间')
    CMA点位数量 = models.CharField(max_length=10, blank=True, verbose_name='CMA点位数量')
    备注赠品 = models.TextField(blank=True, verbose_name='备注赠品')

    # 系统字段
    is_active = models.BooleanField(default=True, verbose_name='是否有效')

    class Meta:
        verbose_name = 'CSV记录'
        verbose_name_plural = 'CSV记录'
        indexes = [
            models.Index(fields=['客户电话']),
            models.Index(fields=['客户姓名']),
        ]

    def __str__(self):
        return f"{self.客户姓名} - {self.客户电话}"


class ContactInfo(BaseModel):
    """联系人信息匹配结果"""
    MATCH_TYPE_CHOICES = [
        ('exact', '完全匹配'),
        ('partial', '部分匹配'),
        ('similarity', '相似度匹配'),
        ('manual', '手动输入'),
    ]

    MATCH_SOURCE_CHOICES = [
        ('csv', 'CSV记录'),
        ('manual', '手动输入'),
    ]
    
    ocr_result = models.OneToOneField(OCRResult, on_delete=models.CASCADE, verbose_name='OCR结果')
    contact_name = models.CharField(max_length=100, blank=True, verbose_name='联系人姓名')
    full_phone = models.CharField(max_length=20, blank=True, verbose_name='完整电话')
    address = models.TextField(blank=True, verbose_name='地址')

    # 匹配信息
    match_type = models.CharField(
        max_length=20,
        choices=MATCH_TYPE_CHOICES,
        blank=True,
        verbose_name='匹配类型'
    )
    similarity_score = models.FloatField(null=True, blank=True, verbose_name='相似度分数')
    match_source = models.CharField(
        max_length=20,
        choices=MATCH_SOURCE_CHOICES,
        blank=True,
        verbose_name='匹配来源'
    )

    # 关联的记录
    csv_record = models.ForeignKey(CSVRecord, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联CSV记录')

    class Meta:
        verbose_name = '联系人信息'
        verbose_name_plural = '联系人信息'
        
    def __str__(self):
        return f"{self.contact_name} - {self.full_phone}"


class PointLearning(BaseModel):
    """点位学习记录"""
    point_name = models.CharField(max_length=100, verbose_name='点位名称')
    usage_count = models.IntegerField(default=1, verbose_name='使用次数')
    total_value = models.FloatField(default=0.0, verbose_name='总值')
    avg_value = models.FloatField(default=0.0, verbose_name='平均值')
    last_used_at = models.DateTimeField(auto_now=True, verbose_name='最后使用时间')

    # 统计信息
    initial_count = models.IntegerField(default=0, verbose_name='初检次数')
    recheck_count = models.IntegerField(default=0, verbose_name='复检次数')

    class Meta:
        ordering = ['-usage_count', '-last_used_at']
        verbose_name = '点位学习'
        verbose_name_plural = '点位学习'
        unique_together = ['point_name']

    def __str__(self):
        return f"{self.point_name} (使用{self.usage_count}次)"

    def update_statistics(self, value: float, check_type: str = 'initial'):
        """更新统计信息 - 使用数据库级别的原子操作"""
        from django.db import transaction
        from django.db.models import F

        try:
            # 使用数据库级别的原子更新，避免锁定问题
            with transaction.atomic():
                # 使用F表达式进行原子更新
                update_fields = {
                    'usage_count': F('usage_count') + 1,
                    'total_value': F('total_value') + value,
                    'last_used_at': timezone.now(),
                }

                if check_type == 'initial':
                    update_fields['initial_count'] = F('initial_count') + 1
                else:
                    update_fields['recheck_count'] = F('recheck_count') + 1

                # 执行原子更新
                PointLearning.objects.filter(pk=self.pk).update(**update_fields)

                # 重新计算平均值（需要单独处理）
                self.refresh_from_db()
                if self.usage_count > 0:
                    self.avg_value = self.total_value / self.usage_count
                    PointLearning.objects.filter(pk=self.pk).update(avg_value=self.avg_value)

        except Exception as e:
            logger.warning(f"更新点位统计失败: {e}")
            # 降级到简单更新
            self.usage_count += 1
            self.total_value += value
            self.avg_value = self.total_value / self.usage_count if self.usage_count > 0 else 0

            if check_type == 'initial':
                self.initial_count += 1
            else:
                self.recheck_count += 1

            self.save()

    @classmethod
    def get_popular_points(cls, limit: int = 20):
        """获取热门点位"""
        return cls.objects.all()[:limit]

    @classmethod
    def get_suggested_points(cls, existing_points: list = None, limit: int = 10):
        """获取建议点位（排除已存在的）"""
        queryset = cls.objects.all()
        if existing_points:
            queryset = queryset.exclude(point_name__in=existing_points)
        return queryset[:limit]


class PointValue(BaseModel):
    """点位值记录"""
    ocr_result = models.ForeignKey(OCRResult, on_delete=models.CASCADE, verbose_name='OCR结果')
    point_name = models.CharField(max_length=100, verbose_name='点位名称')
    value = models.FloatField(verbose_name='检测值')
    check_type = models.CharField(
        max_length=20,
        choices=OCRResult.CHECK_TYPE_CHOICES,
        verbose_name='检测类型'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = '点位值记录'
        verbose_name_plural = '点位值记录'

    def __str__(self):
        return f"{self.point_name}: {self.value} ({self.check_type})"

    def save(self, *args, **kwargs):
        """保存时自动更新点位学习统计"""
        # 添加标志位避免重复更新
        update_learning = kwargs.pop('update_learning', True)

        super().save(*args, **kwargs)

        # 只有在明确要求更新时才更新学习统计
        if update_learning:
            # 更新或创建点位学习记录
            point_learning, created = PointLearning.objects.get_or_create(
                point_name=self.point_name,
                defaults={
                    'usage_count': 0,
                    'total_value': 0.0,
                    'avg_value': 0.0,
                    'initial_count': 0,
                    'recheck_count': 0,
                }
            )
            point_learning.update_statistics(self.value, self.check_type)
