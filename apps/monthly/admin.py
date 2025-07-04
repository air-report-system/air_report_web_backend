"""
月度报表管理后台
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import MonthlyReport, MonthlyReportConfig


@admin.register(MonthlyReportConfig)
class MonthlyReportConfigAdmin(admin.ModelAdmin):
    """月度报表配置管理"""
    list_display = [
        'name', 'is_default', 'uniform_profit_rate', 
        'profit_rate_value', 'created_by', 'created_at'
    ]
    list_filter = ['is_default', 'uniform_profit_rate', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'is_default')
        }),
        ('分润配置', {
            'fields': ('uniform_profit_rate', 'profit_rate_value')
        }),
        ('成本配置', {
            'fields': ('medicine_cost_per_order', 'cma_cost_per_point')
        }),
        ('其他配置', {
            'fields': ('config_options',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """管理员可以看到所有配置，其他用户只能看到自己的配置"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    """月度报表管理"""
    list_display = [
        'title', 'report_month_display', 'generation_status',
        'total_orders_display', 'total_revenue_display', 
        'created_by', 'created_at'
    ]
    list_filter = ['is_generated', 'report_month', 'created_at']
    search_fields = ['title', 'csv_file__original_name']
    readonly_fields = [
        'csv_file', 'log_file', 'summary_data', 'address_matches',
        'cost_analysis', 'excel_file', 'pdf_file', 'is_generated',
        'generation_completed_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'report_month')
        }),
        ('数据文件', {
            'fields': ('csv_file', 'log_file')
        }),
        ('配置信息', {
            'fields': ('config_data',),
            'classes': ('collapse',)
        }),
        ('处理结果', {
            'fields': (
                'summary_data', 'address_matches', 'cost_analysis'
            ),
            'classes': ('collapse',)
        }),
        ('生成文件', {
            'fields': ('excel_file', 'pdf_file', 'is_generated', 'generation_completed_at')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def report_month_display(self, obj):
        """显示报表月份"""
        return obj.report_month.strftime('%Y年%m月')
    report_month_display.short_description = "报表月份"
    
    def generation_status(self, obj):
        """显示生成状态"""
        if obj.is_generated:
            return format_html(
                '<span style="color: green;">✓ 已生成</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">⏳ 待生成</span>'
            )
    generation_status.short_description = "生成状态"
    
    def total_orders_display(self, obj):
        """显示订单总数"""
        if obj.summary_data and 'total_orders' in obj.summary_data:
            return obj.summary_data['total_orders']
        return "-"
    total_orders_display.short_description = "订单总数"
    
    def total_revenue_display(self, obj):
        """显示总收入"""
        if obj.summary_data and 'total_revenue' in obj.summary_data:
            revenue = obj.summary_data['total_revenue']
            return f"¥{revenue:,.2f}"
        return "-"
    total_revenue_display.short_description = "总收入"
    
    def get_queryset(self, request):
        """管理员可以看到所有报表，其他用户只能看到自己的报表"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related('csv_file', 'log_file')
        return qs.filter(created_by=request.user).select_related('csv_file', 'log_file')
