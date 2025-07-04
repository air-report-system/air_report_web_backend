"""
批量处理模型
"""
from django.db import models
from apps.core.models import BaseModel
from apps.files.models import UploadedFile
from apps.ocr.models import OCRResult


class BatchJob(BaseModel):
    """批量处理任务"""
    STATUS_CHOICES = [
        ('created', '已创建'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='任务名称')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='状态')
    total_files = models.IntegerField(default=0, verbose_name='总文件数')
    processed_files = models.IntegerField(default=0, verbose_name='已处理文件数')
    failed_files = models.IntegerField(default=0, verbose_name='失败文件数')
    
    # 配置
    settings = models.JSONField(default=dict, verbose_name='处理设置')
    
    # 关联文件
    uploaded_files = models.ManyToManyField(UploadedFile, through='BatchFileItem', verbose_name='上传文件')
    
    # 时间追踪
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    estimated_completion = models.DateTimeField(null=True, blank=True, verbose_name='预计完成时间')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '批量任务'
        verbose_name_plural = '批量任务'
        
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def progress_percentage(self):
        """计算进度百分比"""
        if self.total_files == 0:
            return 0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def processing_duration(self):
        """计算处理耗时"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BatchFileItem(BaseModel):
    """批量处理文件项"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('skipped', '已跳过'),
    ]
    
    batch_job = models.ForeignKey(BatchJob, on_delete=models.CASCADE, verbose_name='批量任务')
    file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, verbose_name='文件')
    ocr_result = models.ForeignKey(
        OCRResult, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name='OCR结果'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    processing_order = models.IntegerField(default=0, verbose_name='处理顺序')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    processing_time_seconds = models.FloatField(null=True, blank=True, verbose_name='处理耗时(秒)')

    class Meta:
        ordering = ['processing_order']
        verbose_name = '批量文件项'
        verbose_name_plural = '批量文件项'
        
    def __str__(self):
        return f"{self.batch_job.name} - {self.file.original_name}"
