"""
文件管理序列化器
"""
from rest_framework import serializers
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from .models import UploadedFile


class UploadedFileSerializer(serializers.ModelSerializer):
    """上传文件序列化器"""
    file_extension = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_document = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = [
            'id', 'file', 'file_url', 'original_name', 'file_size', 'file_type',
            'mime_type', 'hash_md5', 'is_processed', 'file_extension',
            'is_image', 'is_document', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'file_type', 'mime_type', 'hash_md5',
            'is_processed', 'created_at', 'updated_at'
        ]

    def get_file_url(self, obj):
        """获取文件URL路径"""
        if obj.file:
            file_url = obj.file.url

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
    
    def validate_file(self, value):
        """验证上传文件"""
        if not value:
            raise serializers.ValidationError("文件不能为空")
        
        # 检查文件大小 (最大50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(f"文件大小不能超过{max_size // (1024*1024)}MB")
        
        # 检查文件类型
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv', 'text/plain'
        ]
        
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(f"不支持的文件类型: {value.content_type}")
        
        return value
    
    def create(self, validated_data):
        """创建文件记录"""
        file = validated_data['file']
        
        # 自动设置文件信息
        validated_data['file_size'] = file.size
        validated_data['mime_type'] = getattr(file, 'content_type', 'application/octet-stream')
        
        # 根据MIME类型确定文件类型
        mime_type = validated_data['mime_type']
        if mime_type.startswith('image/'):
            validated_data['file_type'] = 'image'
        elif mime_type in ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            validated_data['file_type'] = 'document'
        elif mime_type in ['application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'text/csv']:
            validated_data['file_type'] = 'spreadsheet'
        elif mime_type == 'text/plain':
            validated_data['file_type'] = 'text'
        else:
            validated_data['file_type'] = 'other'
        
        return super().create(validated_data)


class FileUploadSerializer(serializers.Serializer):
    """文件上传序列化器"""
    file = serializers.FileField()
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_file(self, value):
        """验证上传文件"""
        if not value:
            raise serializers.ValidationError("文件不能为空")
        
        # 检查文件大小 (最大50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(f"文件大小不能超过{max_size // (1024*1024)}MB")
        
        return value


class BulkFileUploadSerializer(serializers.Serializer):
    """批量文件上传序列化器"""
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=20,  # 最多20个文件
        help_text="批量上传的文件列表，最多20个文件"
    )
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_files(self, value):
        """验证批量上传文件"""
        if not value:
            raise serializers.ValidationError("文件列表不能为空")
        
        total_size = 0
        max_total_size = 200 * 1024 * 1024  # 总大小不超过200MB
        max_single_size = 50 * 1024 * 1024  # 单个文件不超过50MB
        
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
