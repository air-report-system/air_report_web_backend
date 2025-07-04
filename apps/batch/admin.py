"""
批量处理管理后台
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import BatchJob, BatchFileItem


class BatchFileItemInline(admin.TabularInline):
    """批量文件项内联编辑"""
    model = BatchFileItem
    extra = 0
    readonly_fields = [
        'file', 'status', 'processing_order', 'error_message',
        'processing_time_seconds', 'ocr_result', 'created_at'
    ]
    fields = [
        'file', 'status', 'processing_order', 'processing_time_seconds',
        'error_message', 'ocr_result'
    ]
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BatchJob)
class BatchJobAdmin(admin.ModelAdmin):
    """批量任务管理"""
    list_display = [
        'name', 'status_display', 'progress_display', 'total_files',
        'processed_files', 'failed_files', 'processing_duration_display',
        'created_by', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name']
    readonly_fields = [
        'total_files', 'processed_files', 'failed_files',
        'progress_percentage', 'processing_duration',
        'started_at', 'completed_at', 'estimated_completion',
        'created_at', 'updated_at'
    ]
    inlines = [BatchFileItemInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'status')
        }),
        ('进度统计', {
            'fields': (
                'total_files', 'processed_files', 'failed_files',
                'progress_percentage'
            )
        }),
        ('处理设置', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': (
                'started_at', 'completed_at', 'estimated_completion',
                'processing_duration', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """显示状态"""
        status_colors = {
            'created': 'blue',
            'running': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "状态"
    
    def progress_display(self, obj):
        """显示进度"""
        percentage = obj.progress_percentage
        if percentage > 0:
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: #007cba; height: 20px; border-radius: 3px; text-align: center; color: white; line-height: 20px;">'
                '{}%'
                '</div></div>',
                percentage,
                int(percentage)
            )
        return "0%"
    progress_display.short_description = "进度"
    
    def processing_duration_display(self, obj):
        """显示处理耗时"""
        duration = obj.processing_duration
        if duration:
            if duration < 60:
                return f"{duration:.1f}秒"
            elif duration < 3600:
                minutes = duration // 60
                seconds = duration % 60
                return f"{int(minutes)}分{seconds:.1f}秒"
            else:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                return f"{int(hours)}小时{int(minutes)}分"
        return "-"
    processing_duration_display.short_description = "处理耗时"
    
    def get_queryset(self, request):
        """管理员可以看到所有批量任务，其他用户只能看到自己的"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.prefetch_related('batchfileitem_set')
        return qs.filter(created_by=request.user).prefetch_related('batchfileitem_set')


@admin.register(BatchFileItem)
class BatchFileItemAdmin(admin.ModelAdmin):
    """批量文件项管理"""
    list_display = [
        'file_name', 'batch_job_name', 'status_display', 
        'processing_order', 'processing_time_display', 'created_at'
    ]
    list_filter = ['status', 'batch_job__status', 'created_at']
    search_fields = ['file__original_name', 'batch_job__name']
    readonly_fields = [
        'batch_job', 'file', 'processing_time_seconds',
        'ocr_result', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('batch_job', 'file', 'status', 'processing_order')
        }),
        ('处理结果', {
            'fields': ('ocr_result', 'processing_time_seconds', 'error_message')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_name(self, obj):
        """显示文件名"""
        return obj.file.original_name if obj.file else "-"
    file_name.short_description = "文件名"
    
    def batch_job_name(self, obj):
        """显示批量任务名"""
        return obj.batch_job.name
    batch_job_name.short_description = "批量任务"
    
    def status_display(self, obj):
        """显示状态"""
        status_colors = {
            'pending': 'blue',
            'processing': 'orange',
            'completed': 'green',
            'failed': 'red',
            'skipped': 'gray'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "状态"
    
    def processing_time_display(self, obj):
        """显示处理耗时"""
        if obj.processing_time_seconds:
            return f"{obj.processing_time_seconds:.1f}秒"
        return "-"
    processing_time_display.short_description = "处理耗时"
    
    def get_queryset(self, request):
        """管理员可以看到所有文件项，其他用户只能看到自己的"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related('batch_job', 'file', 'ocr_result')
        return qs.filter(batch_job__created_by=request.user).select_related('batch_job', 'file', 'ocr_result')
