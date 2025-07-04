"""
OCR处理管理后台
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import OCRResult, ContactInfo


class ContactInfoInline(admin.StackedInline):
    """联系人信息内联编辑"""
    model = ContactInfo
    extra = 0
    fields = [
        'contact_name', 'full_phone', 'address',
        'match_type', 'similarity_score', 'match_source'
    ]


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    """OCR结果管理"""
    list_display = [
        'file_name', 'status', 'check_type', 'phone', 'date',
        'has_conflicts', 'processing_duration_display', 'created_at'
    ]
    list_filter = [
        'status', 'check_type', 'has_conflicts', 'ocr_attempts', 'created_at'
    ]
    search_fields = ['phone', 'file__original_name']
    readonly_fields = [
        'file', 'raw_response', 'confidence_score', 'ocr_attempts',
        'has_conflicts', 'conflict_details', 'processing_started_at',
        'processing_completed_at', 'processing_duration', 'error_message',
        'created_at', 'updated_at'
    ]
    inlines = [ContactInfoInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('file', 'status')
        }),
        ('OCR识别结果', {
            'fields': (
                'phone', 'date', 'temperature', 'humidity', 
                'check_type', 'points_data'
            )
        }),
        ('处理信息', {
            'fields': (
                'ocr_attempts', 'has_conflicts', 'conflict_details',
                'confidence_score', 'raw_response'
            ),
            'classes': ('collapse',)
        }),
        ('时间统计', {
            'fields': (
                'processing_started_at', 'processing_completed_at',
                'processing_duration', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        ('错误信息', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def file_name(self, obj):
        """显示文件名"""
        return obj.file.original_name if obj.file else "-"
    file_name.short_description = "文件名"
    
    def processing_duration_display(self, obj):
        """显示处理耗时"""
        duration = obj.processing_duration
        if duration:
            if duration < 60:
                return f"{duration:.1f}秒"
            else:
                minutes = duration // 60
                seconds = duration % 60
                return f"{int(minutes)}分{seconds:.1f}秒"
        return "-"
    processing_duration_display.short_description = "处理耗时"
    
    def get_queryset(self, request):
        """管理员可以看到所有OCR结果，其他用户只能看到自己的"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related('file', 'contactinfo')
        return qs.filter(created_by=request.user).select_related('file', 'contactinfo')


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    """联系人信息管理"""
    list_display = [
        'contact_name', 'full_phone', 'match_type', 
        'similarity_score', 'match_source', 'created_at'
    ]
    list_filter = ['match_type', 'match_source', 'created_at']
    search_fields = ['contact_name', 'full_phone', 'address']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('联系人信息', {
            'fields': ('contact_name', 'full_phone', 'address')
        }),
        ('匹配信息', {
            'fields': ('match_type', 'similarity_score', 'match_source')
        }),
        ('关联信息', {
            'fields': ('ocr_result',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """管理员可以看到所有联系人信息，其他用户只能看到自己的"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related('ocr_result__file')
        return qs.filter(ocr_result__created_by=request.user).select_related('ocr_result__file')
