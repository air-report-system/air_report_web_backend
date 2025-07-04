"""
月度报表模型
"""
from django.db import models
from apps.core.models import BaseModel
from apps.files.models import UploadedFile


class MonthlyReport(BaseModel):
    """月度报表"""
    title = models.CharField(max_length=200, verbose_name='报表标题')
    report_month = models.DateField(verbose_name='报表月份')  # 报表月份
    
    # 数据源
    csv_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='monthly_reports_csv',
        verbose_name='CSV文件'
    )
    log_file = models.ForeignKey(
        UploadedFile, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='monthly_reports_log',
        verbose_name='日志文件'
    )
    
    # 生成配置
    config_data = models.JSONField(default=dict, verbose_name='配置数据')
    
    # 分析结果
    summary_data = models.JSONField(default=dict, verbose_name='汇总统计')  # 汇总统计
    address_matches = models.JSONField(default=dict, verbose_name='地址匹配结果')  # 地址匹配结果
    cost_analysis = models.JSONField(default=dict, verbose_name='成本分析')  # 成本分析
    
    # 输出文件
    excel_file = models.FileField(
        upload_to='monthly/excel/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name='Excel文件'
    )
    pdf_file = models.FileField(
        upload_to='monthly/pdf/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name='PDF文件'
    )
    
    is_generated = models.BooleanField(default=False, verbose_name='是否已生成')
    generation_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='生成完成时间')

    class Meta:
        ordering = ['-report_month', '-created_at']
        verbose_name = '月度报表'
        verbose_name_plural = '月度报表'
        
    def __str__(self):
        return f"{self.title} - {self.report_month.strftime('%Y年%m月')}"


class MonthlyReportConfig(BaseModel):
    """月度报表配置"""
    name = models.CharField(max_length=100, verbose_name='配置名称')
    description = models.TextField(blank=True, verbose_name='配置描述')
    
    # 配置选项
    uniform_profit_rate = models.BooleanField(default=False, verbose_name='统一分润比')
    profit_rate_value = models.FloatField(default=0.05, verbose_name='分润比值')
    
    # 成本配置
    medicine_cost_per_order = models.FloatField(default=120.1, verbose_name='每单药水成本')
    cma_cost_per_point = models.FloatField(default=60.0, verbose_name='每个CMA点位成本')
    
    # 其他配置
    config_options = models.JSONField(default=dict, verbose_name='其他配置选项')
    
    is_default = models.BooleanField(default=False, verbose_name='是否为默认配置')

    class Meta:
        ordering = ['name']
        verbose_name = '月度报表配置'
        verbose_name_plural = '月度报表配置'
        
    def __str__(self):
        return self.name
