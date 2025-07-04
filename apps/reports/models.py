"""
报告管理模型
"""
from django.db import models
from apps.core.models import BaseModel
from apps.ocr.models import OCRResult


class Report(BaseModel):
    """生成的报告"""
    REPORT_TYPES = [
        ('detection', '检测报告'),
        ('monthly', '月度报表'),
    ]
    
    ocr_result = models.ForeignKey(
        OCRResult, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name='OCR结果'
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='报告类型')
    title = models.CharField(max_length=200, verbose_name='报告标题')
    
    # 报告数据
    form_data = models.JSONField(default=dict, verbose_name='表单填写数据')  # 表单填写数据
    template_data = models.JSONField(default=dict, verbose_name='模板渲染数据')  # 模板渲染数据
    
    # 生成的文件
    docx_file = models.FileField(
        upload_to='reports/docx/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name='Word文件'
    )
    pdf_file = models.FileField(
        upload_to='reports/pdf/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name='PDF文件'
    )
    
    # 配置选项
    delete_original_docx = models.BooleanField(default=False, verbose_name='删除原始Word文件')
    generation_settings = models.JSONField(default=dict, verbose_name='生成设置')
    
    # 状态追踪
    is_generated = models.BooleanField(default=False, verbose_name='是否已生成')
    generation_started_at = models.DateTimeField(null=True, blank=True, verbose_name='生成开始时间')
    generation_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='生成完成时间')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '报告'
        verbose_name_plural = '报告'
        
    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"
    
    @property
    def generation_duration(self):
        """计算生成耗时"""
        if self.generation_started_at and self.generation_completed_at:
            return (self.generation_completed_at - self.generation_started_at).total_seconds()
        return None


class ReportTemplate(BaseModel):
    """报告模板"""
    name = models.CharField(max_length=100, verbose_name='模板名称')
    description = models.TextField(blank=True, verbose_name='模板描述')
    template_file = models.FileField(upload_to='templates/', verbose_name='模板文件')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    # 模板配置
    template_config = models.JSONField(default=dict, verbose_name='模板配置')
    
    class Meta:
        ordering = ['name']
        verbose_name = '报告模板'
        verbose_name_plural = '报告模板'
        
    def __str__(self):
        return self.name
