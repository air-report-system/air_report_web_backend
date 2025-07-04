"""
报告管理序列化器
"""
from rest_framework import serializers
from .models import Report, ReportTemplate
from apps.ocr.models import OCRResult


class ReportTemplateSerializer(serializers.ModelSerializer):
    """报告模板序列化器"""
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'template_file', 
            'is_active', 'template_config', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_template_file(self, value):
        """验证模板文件"""
        if not value:
            raise serializers.ValidationError("模板文件不能为空")
        
        # 检查文件类型
        allowed_types = [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError("只支持Word文档格式(.doc, .docx)")
        
        return value


class ReportSerializer(serializers.ModelSerializer):
    """报告序列化器"""
    ocr_result_info = serializers.SerializerMethodField()
    generation_duration = serializers.ReadOnlyField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'ocr_result', 'ocr_result_info', 'report_type', 'title',
            'form_data', 'template_data', 'docx_file', 'pdf_file',
            'delete_original_docx', 'generation_settings', 'is_generated',
            'generation_started_at', 'generation_completed_at', 
            'generation_duration', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ocr_result_info', 'docx_file', 'pdf_file', 'is_generated',
            'generation_started_at', 'generation_completed_at', 
            'generation_duration', 'error_message', 'created_at', 'updated_at'
        ]
    
    def get_ocr_result_info(self, obj):
        """获取OCR结果信息"""
        if obj.ocr_result:
            return {
                'id': obj.ocr_result.id,
                'file_name': obj.ocr_result.file.original_name,
                'status': obj.ocr_result.status,
                'phone': obj.ocr_result.phone,
                'date': obj.ocr_result.date,
                'check_type': obj.ocr_result.check_type
            }
        return None


class ReportCreateSerializer(serializers.Serializer):
    """报告创建序列化器"""
    ocr_result_id = serializers.IntegerField(help_text="OCR结果ID")
    report_type = serializers.ChoiceField(
        choices=Report.REPORT_TYPES,
        default='detection',
        help_text="报告类型"
    )
    title = serializers.CharField(max_length=200, help_text="报告标题")
    
    # 表单数据
    project_address = serializers.CharField(max_length=500, help_text="项目地址")
    contact_person = serializers.CharField(max_length=100, help_text="联系人")
    sampling_date = serializers.CharField(max_length=20, help_text="采样日期")
    temperature = serializers.CharField(max_length=10, required=False, help_text="现场温度")
    humidity = serializers.CharField(max_length=10, required=False, help_text="现场湿度")
    check_type = serializers.ChoiceField(
        choices=[('initial', '初检'), ('recheck', '复检')],
        help_text="检测类型"
    )
    points_data = serializers.JSONField(help_text="点位数据")
    
    # 生成选项
    delete_original_docx = serializers.BooleanField(
        default=True, 
        help_text="是否删除原始Word文件"
    )
    template_id = serializers.IntegerField(
        required=False, 
        help_text="使用的模板ID（可选）"
    )
    
    def validate_ocr_result_id(self, value):
        """验证OCR结果ID"""
        try:
            ocr_result = OCRResult.objects.get(id=value)
            if ocr_result.status != 'completed':
                raise serializers.ValidationError("OCR结果尚未完成处理")
            return value
        except OCRResult.DoesNotExist:
            raise serializers.ValidationError("OCR结果不存在")
    
    def validate_template_id(self, value):
        """验证模板ID"""
        if value:
            try:
                template = ReportTemplate.objects.get(id=value, is_active=True)
                return value
            except ReportTemplate.DoesNotExist:
                raise serializers.ValidationError("模板不存在或已禁用")
        return value
    
    def validate_points_data(self, value):
        """验证点位数据"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("点位数据必须是字典格式")
        
        if not value:
            raise serializers.ValidationError("点位数据不能为空")
        
        # 验证点位数据格式
        for point_name, point_value in value.items():
            if not isinstance(point_name, str) or not point_name.strip():
                raise serializers.ValidationError("点位名称必须是非空字符串")
            
            try:
                float(point_value)
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"点位 {point_name} 的值必须是数字")
        
        return value


class ReportUpdateSerializer(serializers.ModelSerializer):
    """报告更新序列化器"""
    
    class Meta:
        model = Report
        fields = [
            'title', 'form_data', 'template_data', 
            'delete_original_docx', 'generation_settings'
        ]
    
    def validate_form_data(self, value):
        """验证表单数据"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("表单数据必须是字典格式")
        return value
    
    def validate_template_data(self, value):
        """验证模板数据"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("模板数据必须是字典格式")
        return value


class ReportGenerateSerializer(serializers.Serializer):
    """报告生成序列化器"""
    force_regenerate = serializers.BooleanField(
        default=False,
        help_text="是否强制重新生成（即使已生成）"
    )
    template_id = serializers.IntegerField(
        required=False,
        help_text="使用的模板ID（可选）"
    )
    
    def validate_template_id(self, value):
        """验证模板ID"""
        if value:
            try:
                ReportTemplate.objects.get(id=value, is_active=True)
                return value
            except ReportTemplate.DoesNotExist:
                raise serializers.ValidationError("模板不存在或已禁用")
        return value


class ReportStatsSerializer(serializers.Serializer):
    """报告统计序列化器"""
    total_reports = serializers.IntegerField()
    generated_reports = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
    failed_reports = serializers.IntegerField()
    report_types = serializers.DictField()
    recent_reports = ReportSerializer(many=True)
