"""
订单管理后台
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.ocr.models import CSVRecord


@admin.register(CSVRecord)
class CSVRecordAdmin(admin.ModelAdmin):
    """CSVRecord 订单信息管理"""
    list_display = (
        'id', '客户姓名', '客户电话', 'short_address',
        '商品类型', '成交金额', '履约时间', 'is_active', 'created_at',
    )
    list_filter = ('商品类型', 'is_active', ('履约时间', admin.DateFieldListFilter))
    search_fields = ('客户姓名', '客户电话', '客户地址')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('soft_delete_records', 'restore_records')

    fieldsets = (
        (_('基本信息'), {
            'fields': (
                '客户姓名', '客户电话', '客户地址',
                '商品类型', '成交金额', '面积', 'CMA点位数量', '备注赠品',
            )
        }),
        (_('履约信息'), {
            'fields': ('履约时间', ),
        }),
        (_('系统信息'), {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )

    def short_address(self, obj):
        """截断显示地址"""
        if obj.客户地址:
            return (obj.客户地址[:15] + '...') if len(obj.客户地址) > 15 else obj.客户地址
        return "-"
    short_address.short_description = '客户地址'

    def soft_delete_records(self, request, queryset):
        """批量软删除"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"已软删除 {updated} 条记录")
    soft_delete_records.short_description = '软删除选中记录'

    def restore_records(self, request, queryset):
        """批量恢复"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"已恢复 {updated} 条记录")
    restore_records.short_description = '恢复选中记录'