from django.contrib import admin
from .models import WechatCsvRecord, ProcessingHistory, ValidationResult


@admin.register(WechatCsvRecord)
class WechatCsvRecordAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'customer_phone', 'customer_address', 'product_type', 
                   'transaction_amount', 'area', 'fulfillment_date', 'created_at']
    list_filter = ['product_type', 'fulfillment_date', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_address']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProcessingHistory)
class ProcessingHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_message_preview', 'records_count', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at']
    
    def original_message_preview(self, obj):
        return obj.original_message[:100] + '...' if len(obj.original_message) > 100 else obj.original_message
    original_message_preview.short_description = '原始消息预览'


@admin.register(ValidationResult)
class ValidationResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'processing_history', 'is_valid', 'errors_count', 'warnings_count', 'created_at']
    list_filter = ['is_valid', 'created_at']
    readonly_fields = ['created_at']
    
    def errors_count(self, obj):
        return len(obj.errors) if obj.errors else 0
    errors_count.short_description = '错误数量'
    
    def warnings_count(self, obj):
        return len(obj.warnings) if obj.warnings else 0
    warnings_count.short_description = '警告数量'
