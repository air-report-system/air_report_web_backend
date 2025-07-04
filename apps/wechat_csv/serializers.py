"""
微信CSV处理序列化器
"""
import re
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import WechatCsvRecord, ProcessingHistory, ValidationResult, LoginAttempt


class WechatCsvRecordSerializer(serializers.ModelSerializer):
    """微信CSV记录序列化器"""
    
    class Meta:
        model = WechatCsvRecord
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_address',
            'product_type', 'transaction_amount', 'area', 'fulfillment_date',
            'cma_points', 'gift_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_customer_phone(self, value):
        """验证客户电话格式"""
        if value and not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError("电话号码格式不正确，应为11位手机号")
        return value
    
    def validate_product_type(self, value):
        """验证商品类型"""
        if value and value not in ['国标', '母婴']:
            raise serializers.ValidationError("商品类型只能是'国标'或'母婴'")
        return value
    
    def validate_gift_notes(self, value):
        """验证备注赠品格式"""
        if not value:
            return value
        
        import re
        # 检查基本格式：{品类:数量,品类:数量}
        pattern = r'^\{([^:]+:\d+(?:,[^:]+:\d+)*)\}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("备注赠品格式错误，应为{品类:数量}格式")
        
        # 检查品类是否在允许的范围内
        allowed_gifts = ["除醛宝", "炭包", "除醛机", "除醛喷雾"]
        content = value[1:-1]  # 去掉大括号
        items = content.split(',')
        
        for item in items:
            if ':' not in item:
                raise serializers.ValidationError("备注赠品格式错误")
            gift_type, quantity = item.split(':', 1)
            if gift_type.strip() not in allowed_gifts:
                raise serializers.ValidationError(f"不支持的赠品类型: {gift_type.strip()}")
            if not quantity.strip().isdigit():
                raise serializers.ValidationError("赠品数量必须是数字")
        
        return value


class ProcessingHistorySerializer(serializers.ModelSerializer):
    """处理历史序列化器"""
    
    records_count = serializers.ReadOnlyField()
    
    class Meta:
        model = ProcessingHistory
        fields = [
            'id', 'original_message', 'formatted_csv', 'status', 'error_message',
            'github_file_path', 'github_commit_sha', 'github_commit_url',
            'records_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'records_count']


class ValidationResultSerializer(serializers.ModelSerializer):
    """验证结果序列化器"""
    
    class Meta:
        model = ValidationResult
        fields = [
            'id', 'processing_history', 'is_valid', 'errors', 'warnings',
            'duplicate_indexes', 'match_details', 'format_fixes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WechatMessageProcessSerializer(serializers.Serializer):
    """微信消息处理请求序列化器"""
    
    wechat_text = serializers.CharField(
        help_text="微信消息内容",
        style={'base_template': 'textarea.html'}
    )
    
    def validate_wechat_text(self, value):
        """验证微信消息内容"""
        if not value.strip():
            raise serializers.ValidationError("微信消息内容不能为空")
        return value.strip()


class TableDataSerializer(serializers.Serializer):
    """表格数据序列化器"""
    
    index = serializers.IntegerField(read_only=True)
    客户姓名 = serializers.CharField(max_length=100)
    客户电话 = serializers.CharField(max_length=20, allow_blank=True)
    客户地址 = serializers.CharField()
    商品类型 = serializers.CharField(max_length=20, allow_blank=True)
    成交金额 = serializers.CharField(allow_blank=True)
    面积 = serializers.CharField(allow_blank=True)
    履约时间 = serializers.CharField(allow_blank=True)
    CMA点位数量 = serializers.CharField(max_length=50, allow_blank=True)
    备注赠品 = serializers.CharField(allow_blank=True)
    
    def validate_客户姓名(self, value):
        """验证客户姓名"""
        if not value.strip():
            raise serializers.ValidationError("客户姓名不能为空")
        return value.strip()
    
    def validate_客户电话(self, value):
        """验证客户电话"""
        if value:
            import re
            if not re.match(r'^1[3-9]\d{9}$', value):
                raise serializers.ValidationError("电话号码格式不正确")
        return value
    
    def validate_客户地址(self, value):
        """验证客户地址"""
        if not value.strip():
            raise serializers.ValidationError("客户地址不能为空")
        return value.strip()
    
    def validate_商品类型(self, value):
        """验证商品类型"""
        if value and value not in ['国标', '母婴']:
            raise serializers.ValidationError("商品类型只能是'国标'或'母婴'")
        return value
    
    def validate_成交金额(self, value):
        """验证成交金额"""
        if value:
            try:
                float(value)
            except ValueError:
                raise serializers.ValidationError("成交金额必须是数字")
        return value
    
    def validate_面积(self, value):
        """验证面积"""
        if value:
            try:
                float(value)
            except ValueError:
                raise serializers.ValidationError("面积必须是数字")
        return value
    
    def validate_履约时间(self, value):
        """验证履约时间"""
        if value:
            from datetime import datetime
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise serializers.ValidationError("履约时间格式不正确，应为YYYY-MM-DD")
        return value


class UpdateTableSerializer(serializers.Serializer):
    """更新表格数据请求序列化器"""
    
    table_data = TableDataSerializer(many=True)


class SubmitToGitHubSerializer(serializers.Serializer):
    """提交到GitHub请求序列化器"""
    
    table_data = TableDataSerializer(many=True, required=False)
    csv_content = serializers.CharField(required=False, allow_blank=True)
    csv_filename = serializers.CharField(max_length=255)
    
    def validate(self, data):
        """验证提交数据"""
        if not data.get('table_data') and not data.get('csv_content'):
            raise serializers.ValidationError("必须提供table_data或csv_content")
        return data


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    
    password = serializers.CharField(
        write_only=True,
        help_text="访问密码"
    )
    
    def validate_password(self, value):
        """验证密码"""
        from django.conf import settings
        if value != settings.WECHAT_CSV_PASSWORD:
            raise serializers.ValidationError("密码错误")
        return value


class ProcessResponseSerializer(serializers.Serializer):
    """处理响应序列化器"""
    
    formatted_csv = serializers.CharField()
    original_csv = serializers.CharField()
    table_data = TableDataSerializer(many=True)
    validation = ValidationResultSerializer()
    csv_filename = serializers.CharField()
    existing_content = serializers.CharField()
    potential_duplicates = serializers.ListField(child=serializers.IntegerField())
    match_details = serializers.ListField()
    format_fixes = serializers.ListField()


class SubmitResponseSerializer(serializers.Serializer):
    """提交响应序列化器"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    commit_info = serializers.DictField(required=False)
    file_path = serializers.CharField()
    error = serializers.CharField(required=False)
