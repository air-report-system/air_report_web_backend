"""
AI配置管理后台
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import AIServiceConfig, AIConfigHistory, AIServiceUsageLog


@admin.register(AIServiceConfig)
class AIServiceConfigAdmin(admin.ModelAdmin):
    """AI服务配置管理"""
    
    list_display = [
        'name', 'provider', 'api_format', 'model_name',
        'is_active', 'is_default', 'priority', 'success_rate_display',
        'last_used_at', 'created_at'
    ]
    list_filter = [
        'provider', 'api_format', 'is_active', 'is_default',
        'created_at', 'last_used_at'
    ]
    search_fields = ['name', 'description', 'model_name', 'api_base_url']
    ordering = ['priority', '-created_at']
    readonly_fields = [
        'success_count', 'failure_count', 'success_rate',
        'last_used_at', 'last_test_at', 'last_test_result',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'provider', 'created_by')
        }),
        ('API配置', {
            'fields': (
                'api_format', 'api_base_url', 'api_key',
                'model_name', 'timeout_seconds', 'max_retries'
            )
        }),
        ('高级配置', {
            'fields': ('extra_config', 'priority'),
            'classes': ('collapse',)
        }),
        ('状态管理', {
            'fields': ('is_active', 'is_default')
        }),
        ('使用统计', {
            'fields': (
                'success_count', 'failure_count', 'success_rate',
                'last_used_at', 'last_test_at', 'last_test_result'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def success_rate_display(self, obj):
        """成功率显示"""
        rate = obj.success_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = '成功率'
    success_rate_display.admin_order_field = 'success_count'
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related('created_by')
    
    def save_model(self, request, obj, form, change):
        """保存时设置创建者"""
        if not change:  # 新建时
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AIConfigHistory)
class AIConfigHistoryAdmin(admin.ModelAdmin):
    """AI配置历史管理"""
    
    list_display = [
        'config', 'action', 'user', 'created_at', 'notes_short'
    ]
    list_filter = ['action', 'created_at', 'user']
    search_fields = ['config__name', 'notes', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('config', 'action', 'user', 'notes')
        }),
        ('变更数据', {
            'fields': ('old_data', 'new_data'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def notes_short(self, obj):
        """备注简短显示"""
        if obj.notes:
            return obj.notes[:50] + '...' if len(obj.notes) > 50 else obj.notes
        return '-'
    notes_short.short_description = '备注'
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related('config', 'user')
    
    def has_add_permission(self, request):
        """禁止手动添加历史记录"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改历史记录"""
        return False


@admin.register(AIServiceUsageLog)
class AIServiceUsageLogAdmin(admin.ModelAdmin):
    """AI服务使用日志管理"""
    
    list_display = [
        'config', 'service_type', 'is_success', 'response_time_ms',
        'user', 'created_at'
    ]
    list_filter = [
        'service_type', 'is_success', 'created_at',
        'config__provider', 'config__name'
    ]
    search_fields = [
        'config__name', 'service_type', 'error_message',
        'user__username'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('config', 'service_type', 'user', 'is_success')
        }),
        ('请求响应', {
            'fields': ('request_data', 'response_data', 'response_time_ms'),
            'classes': ('collapse',)
        }),
        ('错误信息', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related('config', 'user')
    
    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日志"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """禁止删除日志"""
        return False


# 自定义管理后台标题
admin.site.site_header = '室内空气检测系统管理后台'
admin.site.site_title = 'AI配置管理'
admin.site.index_title = 'AI配置管理'
