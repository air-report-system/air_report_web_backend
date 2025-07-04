"""
文件管理后台
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import UploadedFile


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """上传文件管理"""
    list_display = [
        'original_name', 'file_type', 'file_size_display', 
        'is_processed', 'created_by', 'created_at'
    ]
    list_filter = ['file_type', 'is_processed', 'created_at']
    search_fields = ['original_name', 'hash_md5']
    readonly_fields = [
        'file_size', 'file_type', 'mime_type', 'hash_md5', 
        'file_extension', 'is_image', 'is_document',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('file', 'original_name', 'is_processed')
        }),
        ('文件属性', {
            'fields': (
                'file_size', 'file_type', 'mime_type', 'hash_md5',
                'file_extension', 'is_image', 'is_document'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """显示文件大小"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = "文件大小"
    
    def get_queryset(self, request):
        """管理员可以看到所有文件，其他用户只能看到自己的文件"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)
