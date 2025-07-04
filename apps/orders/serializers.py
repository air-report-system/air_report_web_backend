"""
订单信息序列化器
"""
from rest_framework import serializers
from apps.ocr.models import CSVRecord


class OrderInfoInputSerializer(serializers.Serializer):
    """订单信息输入序列化器"""
    order_text = serializers.CharField(
        help_text="原始订单信息文本",
        style={'base_template': 'textarea.html', 'rows': 10}
    )


class OrderInfoOutputSerializer(serializers.Serializer):
    """订单信息输出序列化器"""
    formatted_csv = serializers.CharField(help_text="格式化后的CSV数据")
    order_data = serializers.DictField(help_text="解析后的订单数据")
    validation_errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="验证错误列表"
    )
    csv_content = serializers.CharField(help_text="CSV内容")


class OrderRecordSerializer(serializers.ModelSerializer):
    """订单记录序列化器 - 复用CSVRecord模型"""
    
    class Meta:
        model = CSVRecord
        fields = [
            'id', '客户姓名', '客户电话', '客户地址', '商品类型', '成交金额',
            '面积', '履约时间', 'CMA点位数量', '备注赠品', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_客户电话(self, value):
        """验证客户电话格式"""
        if value and not value.isdigit():
            raise serializers.ValidationError("电话号码只能包含数字")
        if value and len(value) != 11:
            raise serializers.ValidationError("电话号码必须是11位")
        return value
    
    def validate_商品类型(self, value):
        """验证商品类型"""
        if value and value not in ['国标', '母婴']:
            raise serializers.ValidationError("商品类型只能是'国标'或'母婴'")
        return value


class OrderUpdateSerializer(serializers.Serializer):
    """订单更新序列化器"""
    order_data = serializers.DictField(help_text="订单数据")
    
    def validate_order_data(self, value):
        """验证订单数据格式"""
        required_fields = ["客户姓名", "客户地址"]
        for field in required_fields:
            if not value.get(field, '').strip():
                raise serializers.ValidationError(f"{field}不能为空")
        return value


class OrderSubmitSerializer(serializers.Serializer):
    """订单提交序列化器"""
    order_data = serializers.DictField(help_text="订单数据")
    
    def validate_order_data(self, value):
        """验证订单数据"""
        # 验证必填字段
        required_fields = ["客户姓名", "客户地址"]
        for field in required_fields:
            if not value.get(field, '').strip():
                raise serializers.ValidationError(f"{field}不能为空")
        
        # 验证电话格式
        phone = value.get("客户电话", '').strip()
        if phone and (not phone.isdigit() or len(phone) != 11):
            raise serializers.ValidationError("客户电话格式不正确")
        
        # 验证商品类型
        product_type = value.get("商品类型", '').strip()
        if product_type and product_type not in ['国标', '母婴']:
            raise serializers.ValidationError("商品类型只能是'国标'或'母婴'")
        
        return value
