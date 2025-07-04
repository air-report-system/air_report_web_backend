"""
批量处理序列化器
"""
from rest_framework import serializers
from .models import BatchJob, BatchFileItem
from apps.files.models import UploadedFile
from apps.ocr.serializers import OCRResultSerializer


class BatchFileItemSerializer(serializers.ModelSerializer):
    """批量文件项序列化器"""
    filename = serializers.CharField(source='file.original_name', read_only=True)
    file_path = serializers.SerializerMethodField()
    file_size = serializers.IntegerField(source='file.file_size', read_only=True)
    ocr_result = OCRResultSerializer(read_only=True)

    class Meta:
        model = BatchFileItem
        fields = [
            'id', 'file', 'filename', 'file_path', 'file_size', 'status',
            'processing_order', 'error_message', 'processing_time_seconds',
            'ocr_result', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'filename', 'file_path', 'file_size', 'status', 'error_message',
            'processing_time_seconds', 'ocr_result', 'created_at', 'updated_at'
        ]

    def get_file_path(self, obj):
        """获取文件URL路径"""
        if obj.file and obj.file.file:
            # 在开发环境下，返回相对路径以便前端代理
            # 在生产环境下，返回完整URL
            request = self.context.get('request')
            if request and hasattr(request, 'build_absolute_uri'):
                # 检查是否为开发环境（localhost）
                host = request.get_host()
                if 'localhost' in host or '127.0.0.1' in host:
                    # 开发环境：返回相对路径，让前端代理处理
                    return obj.file.file.url
                else:
                    # 生产环境：返回完整URL
                    return request.build_absolute_uri(obj.file.file.url)
            return obj.file.file.url
        return None


class BatchJobSerializer(serializers.ModelSerializer):
    """批量任务序列化器"""
    progress_percentage = serializers.ReadOnlyField()
    processing_duration = serializers.ReadOnlyField()
    file_items = BatchFileItemSerializer(
        source='batchfileitem_set', 
        many=True, 
        read_only=True
    )
    
    class Meta:
        model = BatchJob
        fields = [
            'id', 'name', 'status', 'total_files', 'processed_files',
            'failed_files', 'settings', 'progress_percentage',
            'processing_duration', 'started_at', 'completed_at',
            'estimated_completion', 'file_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'total_files', 'processed_files', 'failed_files',
            'progress_percentage', 'processing_duration', 'started_at',
            'completed_at', 'estimated_completion', 'file_items',
            'created_at', 'updated_at'
        ]


class BatchJobCreateSerializer(serializers.Serializer):
    """批量任务创建序列化器"""
    name = serializers.CharField(max_length=200, help_text="任务名称")
    file_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100,
        help_text="要处理的文件ID列表"
    )
    
    # 处理设置
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
    auto_start = serializers.BooleanField(
        default=False,
        help_text="是否自动开始处理"
    )
    
    def validate_file_ids(self, value):
        """验证文件ID列表"""
        if not value:
            raise serializers.ValidationError("文件ID列表不能为空")
        
        # 检查文件是否存在且为图片
        user = self.context['request'].user
        files = UploadedFile.objects.filter(
            id__in=value,
            created_by=user
        )
        
        if files.count() != len(value):
            raise serializers.ValidationError("部分文件不存在或无权限访问")
        
        # 检查是否都是图片文件
        non_image_files = files.filter(file_type__ne='image')
        if non_image_files.exists():
            non_image_names = list(non_image_files.values_list('original_name', flat=True))
            raise serializers.ValidationError(
                f"以下文件不是图片格式: {', '.join(non_image_names)}"
            )
        
        return value
    
    def validate(self, attrs):
        """验证整体数据"""
        use_multi_ocr = attrs.get('use_multi_ocr', False)
        ocr_count = attrs.get('ocr_count', 3)
        
        # 如果不使用多重OCR，忽略ocr_count参数
        if not use_multi_ocr:
            attrs['ocr_count'] = 1
        
        return attrs


class BatchJobUpdateSerializer(serializers.ModelSerializer):
    """批量任务更新序列化器"""
    
    class Meta:
        model = BatchJob
        fields = ['name', 'settings']


class BatchJobStartSerializer(serializers.Serializer):
    """批量任务启动序列化器"""
    force_restart = serializers.BooleanField(
        default=False,
        help_text="是否强制重新开始（清除之前的进度）"
    )


class BatchJobStatsSerializer(serializers.Serializer):
    """批量任务统计序列化器"""
    total_jobs = serializers.IntegerField()
    running_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    total_files_processed = serializers.IntegerField()
    average_processing_time = serializers.FloatField()
    recent_jobs = BatchJobSerializer(many=True)


class BulkFileUploadAndBatchSerializer(serializers.Serializer):
    """批量文件上传并创建批量任务序列化器"""
    files = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,
        max_length=50,
        help_text="批量上传的图片文件列表"
    )
    batch_name = serializers.CharField(
        max_length=200,
        help_text="批量任务名称"
    )
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
    auto_start = serializers.BooleanField(
        default=True,
        help_text="是否自动开始处理"
    )
    
    def validate_files(self, value):
        """验证批量上传文件"""
        if not value:
            raise serializers.ValidationError("文件列表不能为空")
        
        total_size = 0
        max_total_size = 500 * 1024 * 1024  # 总大小不超过500MB
        max_single_size = 20 * 1024 * 1024  # 单个文件不超过20MB
        
        for file in value:
            if file.size > max_single_size:
                raise serializers.ValidationError(
                    f"文件 {file.name} 大小超过限制 ({max_single_size // (1024*1024)}MB)"
                )
            total_size += file.size
        
        if total_size > max_total_size:
            raise serializers.ValidationError(
                f"批量上传文件总大小超过限制 ({max_total_size // (1024*1024)}MB)"
            )
        
        return value
