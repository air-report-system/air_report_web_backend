"""
报告管理后台
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Report, ReportTemplate


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    """报告模板管理"""
    list_display = ['name', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('模板文件', {
            'fields': ('template_file',)
        }),
        ('配置信息', {
            'fields': ('template_config',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """管理员可以看到所有模板，其他用户只能看到自己的模板"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """报告管理"""
    list_display = [
        'title', 'report_type', 'is_generated', 'generation_status',
        'generation_duration_display', 'created_by', 'created_at'
    ]
    list_filter = [
        'report_type', 'is_generated', 'delete_original_docx', 'created_at'
    ]
    search_fields = ['title', 'ocr_result__file__original_name']
    readonly_fields = [
        'ocr_result', 'docx_file', 'pdf_file', 'is_generated',
        'generation_started_at', 'generation_completed_at',
        'generation_duration', 'error_message', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'report_type', 'ocr_result')
        }),
        ('表单数据', {
            'fields': ('form_data',),
            'classes': ('collapse',)
        }),
        ('模板数据', {
            'fields': ('template_data',),
            'classes': ('collapse',)
        }),
        ('生成设置', {
            'fields': ('delete_original_docx', 'generation_settings')
        }),
        ('生成结果', {
            'fields': (
                'is_generated', 'docx_file', 'pdf_file',
                'generation_started_at', 'generation_completed_at',
                'generation_duration', 'error_message'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def generation_status(self, obj):
        """显示生成状态"""
        if obj.is_generated:
            return format_html(
                '<span style="color: green;">✓ 已生成</span>'
            )
        elif obj.error_message:
            return format_html(
                '<span style="color: red;">✗ 生成失败</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">⏳ 待生成</span>'
            )
    generation_status.short_description = "生成状态"
    
    def generation_duration_display(self, obj):
        """显示生成耗时"""
        duration = obj.generation_duration
        if duration:
            if duration < 60:
                return f"{duration:.1f}秒"
            else:
                minutes = duration // 60
                seconds = duration % 60
                return f"{int(minutes)}分{seconds:.1f}秒"
        return "-"
    generation_duration_display.short_description = "生成耗时"
    
    def get_queryset(self, request):
        """管理员可以看到所有报告，其他用户只能看到自己的报告"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related('ocr_result__file')
        return qs.filter(created_by=request.user).select_related('ocr_result__file')
