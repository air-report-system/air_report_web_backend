"""
OCR处理序列化器
"""
from rest_framework import serializers
from .models import OCRResult, ContactInfo, PointLearning, PointValue, CSVRecord
from apps.files.models import UploadedFile


class CSVRecordSerializer(serializers.ModelSerializer):
    """CSV记录序列化器"""

    class Meta:
        model = CSVRecord
        fields = [
            'id', '客户姓名', '客户电话', '客户地址', '商品类型', '成交金额',
            '面积', '履约时间', 'CMA点位数量', '备注赠品', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContactInfoSerializer(serializers.ModelSerializer):
    """联系人信息序列化器"""
    csv_record = CSVRecordSerializer(read_only=True)

    class Meta:
        model = ContactInfo
        fields = [
            'id', 'contact_name', 'full_phone', 'address',
            'match_type', 'similarity_score', 'match_source',
            'csv_record',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OCRResultSerializer(serializers.ModelSerializer):
    """OCR结果序列化器"""
    contact_info = ContactInfoSerializer(source='contactinfo', read_only=True)
    file_name = serializers.CharField(source='file.original_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    processing_duration = serializers.ReadOnlyField()

    class Meta:
        model = OCRResult
        fields = [
            'id', 'file', 'file_name', 'file_url', 'status', 'phone', 'date',
            'temperature', 'humidity', 'check_type', 'points_data',
            'raw_response', 'confidence_score', 'ocr_attempts',
            'has_conflicts', 'conflict_details', 'processing_duration',
            'processing_started_at', 'processing_completed_at',
            'error_message', 'contact_info', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_name', 'file_url', 'status', 'raw_response', 'confidence_score',
            'ocr_attempts', 'has_conflicts', 'conflict_details',
            'processing_duration', 'processing_started_at',
            'processing_completed_at', 'error_message', 'contact_info',
            'created_at', 'updated_at'
        ]

    def get_file_url(self, obj):
        """获取文件URL路径"""
        if obj.file and obj.file.file:
            file_url = obj.file.file.url

            request = self.context.get('request')
            if request and hasattr(request, 'build_absolute_uri'):
                # 检查是否为开发环境（localhost）
                host = request.get_host()
                if 'localhost' in host or '127.0.0.1' in host:
                    # 开发环境：返回相对路径，让前端代理处理
                    return file_url
                else:
                    # 生产环境：返回完整URL
                    return request.build_absolute_uri(file_url)
            return file_url
        return None


class OCRProcessSerializer(serializers.Serializer):
    """OCR处理请求序列化器"""
    file_id = serializers.IntegerField(help_text="要处理的文件ID")
    use_multi_ocr = serializers.BooleanField(
        default=False, 
        help_text="是否使用多重OCR验证"
    )
    ocr_count = serializers.IntegerField(
        default=3, 
        min_value=2, 
        max_value=5,
        help_text="多重OCR次数（2-5次）"
    )
    
    def validate_file_id(self, value):
        """验证文件ID"""
        try:
            file_obj = UploadedFile.objects.get(id=value)
            
            # 检查文件是否为图片
            if not file_obj.is_image:
                raise serializers.ValidationError("只能处理图片文件")
            
            # 检查文件是否存在
            if not file_obj.file or not file_obj.file.name:
                raise serializers.ValidationError("文件不存在")
            
            return value
            
        except UploadedFile.DoesNotExist:
            raise serializers.ValidationError("文件不存在")
    
    def validate(self, attrs):
        """验证整体数据"""
        use_multi_ocr = attrs.get('use_multi_ocr', False)
        ocr_count = attrs.get('ocr_count', 3)
        
        # 如果不使用多重OCR，忽略ocr_count参数
        if not use_multi_ocr:
            attrs['ocr_count'] = 1
        
        return attrs


class ImageUploadAndProcessSerializer(serializers.Serializer):
    """图片上传并处理序列化器"""
    image = serializers.ImageField(help_text="要处理的图片文件")
    use_multi_ocr = serializers.BooleanField(
        default=False, 
        help_text="是否使用多重OCR验证"
    )
    ocr_count = serializers.IntegerField(
        default=3, 
        min_value=2, 
        max_value=5,
        help_text="多重OCR次数（2-5次）"
    )
    
    def validate_image(self, value):
        """验证图片文件"""
        if not value:
            raise serializers.ValidationError("图片文件不能为空")
        
        # 检查文件大小 (最大20MB)
        max_size = 20 * 1024 * 1024  # 20MB
        if value.size > max_size:
            raise serializers.ValidationError(f"图片大小不能超过{max_size // (1024*1024)}MB")
        
        # 检查文件类型
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(f"不支持的图片类型: {value.content_type}")
        
        return value


class OCRResultUpdateSerializer(serializers.ModelSerializer):
    """OCR结果更新序列化器"""
    
    class Meta:
        model = OCRResult
        fields = [
            'phone', 'date', 'temperature', 'humidity', 
            'check_type', 'points_data'
        ]
    
    def validate_phone(self, value):
        """验证电话号码"""
        if value and len(value) != 11:
            raise serializers.ValidationError("电话号码必须是11位数字")
        return value
    
    def validate_date(self, value):
        """验证日期格式"""
        if value:
            import re
            if not re.match(r'^\d{2}-\d{2}$', value):
                raise serializers.ValidationError("日期格式必须是MM-DD")
        return value
    
    def validate_points_data(self, value):
        """验证点位数据"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("点位数据必须是字典格式")
        return value


class ContactInfoUpdateSerializer(serializers.ModelSerializer):
    """联系人信息更新序列化器"""
    
    class Meta:
        model = ContactInfo
        fields = [
            'contact_name', 'full_phone', 'address',
            'match_type', 'match_source'
        ]
    
    def validate_full_phone(self, value):
        """验证完整电话号码"""
        if value and len(value) != 11:
            raise serializers.ValidationError("电话号码必须是11位数字")
        return value


class PointLearningSerializer(serializers.ModelSerializer):
    """点位学习序列化器"""

    class Meta:
        model = PointLearning
        fields = [
            'id', 'point_name', 'usage_count', 'avg_value',
            'initial_count', 'recheck_count', 'last_used_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usage_count', 'avg_value', 'initial_count',
            'recheck_count', 'last_used_at', 'created_at', 'updated_at'
        ]


class PointValueSerializer(serializers.ModelSerializer):
    """点位值序列化器"""

    class Meta:
        model = PointValue
        fields = [
            'id', 'ocr_result', 'point_name', 'value', 'check_type',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PointLearningUpdateSerializer(serializers.Serializer):
    """点位学习更新序列化器"""
    points_data = serializers.DictField(
        child=serializers.FloatField(),
        help_text="点位数据字典，格式：{'点位名称': 检测值}"
    )
    check_type = serializers.ChoiceField(
        choices=OCRResult.CHECK_TYPE_CHOICES,
        default='initial',
        help_text="检测类型"
    )

    def validate_points_data(self, value):
        """验证点位数据"""
        if not value:
            raise serializers.ValidationError("点位数据不能为空")

        for point_name, point_value in value.items():
            if not isinstance(point_name, str) or not point_name.strip():
                raise serializers.ValidationError("点位名称必须是非空字符串")

            if not isinstance(point_value, (int, float)) or point_value < 0:
                raise serializers.ValidationError(f"点位值必须是非负数字: {point_name}")

        return value


class PointSuggestionSerializer(serializers.Serializer):
    """点位建议序列化器"""
    existing_points = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="已存在的点位名称列表"
    )
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        help_text="返回建议数量"
    )


class CheckTypeInferenceSerializer(serializers.Serializer):
    """检测类型推断序列化器"""
    points_data = serializers.DictField(
        child=serializers.FloatField(),
        help_text="点位数据字典，格式：{'点位名称': 检测值}"
    )
    threshold = serializers.FloatField(
        default=0.080,
        help_text="判断阈值，默认0.080"
    )

    def validate_points_data(self, value):
        """验证点位数据"""
        if not value:
            raise serializers.ValidationError("点位数据不能为空")

        for point_name, point_value in value.items():
            if not isinstance(point_value, (int, float)):
                raise serializers.ValidationError(f"点位值必须是数字: {point_name}")

        return value
