"""
月度报表序列化器
"""
from rest_framework import serializers
from .models import MonthlyReport, MonthlyReportConfig
from apps.files.models import UploadedFile


class MonthlyReportConfigSerializer(serializers.ModelSerializer):
    """月度报表配置序列化器"""
    
    class Meta:
        model = MonthlyReportConfig
        fields = [
            'id', 'name', 'description', 'uniform_profit_rate',
            'profit_rate_value', 'medicine_cost_per_order', 'cma_cost_per_point',
            'config_options', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MonthlyReportSerializer(serializers.ModelSerializer):
    """月度报表序列化器"""
    csv_file_name = serializers.CharField(source='csv_file.original_name', read_only=True)
    log_file_name = serializers.CharField(source='log_file.original_name', read_only=True)
    report_month_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MonthlyReport
        fields = [
            'id', 'title', 'report_month', 'report_month_display',
            'csv_file', 'csv_file_name', 'log_file', 'log_file_name',
            'config_data', 'summary_data', 'address_matches', 'cost_analysis',
            'excel_file', 'pdf_file', 'is_generated', 'generation_completed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'csv_file_name', 'log_file_name', 'report_month_display',
            'summary_data', 'address_matches', 'cost_analysis',
            'excel_file', 'pdf_file', 'is_generated', 'generation_completed_at',
            'created_at', 'updated_at'
        ]
    
    def get_report_month_display(self, obj):
        """获取报表月份显示"""
        return obj.report_month.strftime('%Y年%m月')


class MonthlyReportCreateSerializer(serializers.Serializer):
    """月度报表创建序列化器"""
    title = serializers.CharField(max_length=200, help_text="报表标题")
    report_month = serializers.DateField(help_text="报表月份")
    csv_file_id = serializers.IntegerField(help_text="CSV文件ID")
    log_file_id = serializers.IntegerField(required=False, help_text="日志文件ID（可选）")
    config_id = serializers.IntegerField(required=False, help_text="配置ID（可选）")
    
    # 配置选项
    uniform_profit_rate = serializers.BooleanField(
        default=False,
        help_text="是否统一分润比"
    )
    profit_rate_value = serializers.FloatField(
        default=0.05,
        min_value=0.0,
        max_value=1.0,
        help_text="分润比值（0-1之间）"
    )
    medicine_cost_per_order = serializers.FloatField(
        default=120.1,
        min_value=0.0,
        help_text="每单药水成本"
    )
    cma_cost_per_point = serializers.FloatField(
        default=60.0,
        min_value=0.0,
        help_text="每个CMA点位成本"
    )
    
    # 其他配置
    include_address_matching = serializers.BooleanField(
        default=True,
        help_text="是否包含地址匹配"
    )
    exclude_recheck_records = serializers.BooleanField(
        default=True,
        help_text="是否排除复检记录"
    )
    date_range_days = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        help_text="日期范围限制（天）"
    )
    
    def validate_csv_file_id(self, value):
        """验证CSV文件ID"""
        try:
            file_obj = UploadedFile.objects.get(id=value)
            
            # 检查文件类型
            if file_obj.file_type != 'spreadsheet':
                raise serializers.ValidationError("必须是Excel或CSV文件")
            
            return value
        except UploadedFile.DoesNotExist:
            raise serializers.ValidationError("CSV文件不存在")
    
    def validate_log_file_id(self, value):
        """验证日志文件ID"""
        if value:
            try:
                file_obj = UploadedFile.objects.get(id=value)
                
                # 检查文件类型
                if file_obj.file_type != 'text':
                    raise serializers.ValidationError("日志文件必须是文本文件")
                
                return value
            except UploadedFile.DoesNotExist:
                raise serializers.ValidationError("日志文件不存在")
        return value
    
    def validate_config_id(self, value):
        """验证配置ID"""
        if value:
            try:
                MonthlyReportConfig.objects.get(id=value)
                return value
            except MonthlyReportConfig.DoesNotExist:
                raise serializers.ValidationError("配置不存在")
        return value


class MonthlyReportGenerateSerializer(serializers.Serializer):
    """月度报表生成序列化器"""
    force_regenerate = serializers.BooleanField(
        default=False,
        help_text="是否强制重新生成"
    )
    generate_pdf = serializers.BooleanField(
        default=True,
        help_text="是否生成PDF文件"
    )
    config_id = serializers.IntegerField(
        required=False,
        help_text="使用的配置ID（可选）"
    )
    
    def validate_config_id(self, value):
        """验证配置ID"""
        if value:
            try:
                MonthlyReportConfig.objects.get(id=value)
                return value
            except MonthlyReportConfig.DoesNotExist:
                raise serializers.ValidationError("配置不存在")
        return value


class MonthlyReportStatsSerializer(serializers.Serializer):
    """月度报表统计序列化器"""
    total_reports = serializers.IntegerField()
    generated_reports = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
    reports_by_month = serializers.DictField()
    total_orders_processed = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    average_generation_time = serializers.FloatField()
    recent_reports = MonthlyReportSerializer(many=True)


class AddressMatchingSerializer(serializers.Serializer):
    """地址匹配序列化器"""
    csv_address = serializers.CharField()
    log_address = serializers.CharField()
    similarity_score = serializers.FloatField()
    match_type = serializers.CharField()
    phone_match = serializers.BooleanField()


class CostAnalysisSerializer(serializers.Serializer):
    """成本分析序列化器"""
    total_orders = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_medicine_cost = serializers.FloatField()
    total_cma_cost = serializers.FloatField()
    total_labor_cost = serializers.FloatField()
    total_profit = serializers.FloatField()
    profit_margin = serializers.FloatField()
    average_order_value = serializers.FloatField()
    cost_breakdown = serializers.DictField()


class MonthlyReportDetailSerializer(serializers.ModelSerializer):
    """月度报表详情序列化器"""
    csv_file_name = serializers.CharField(source='csv_file.original_name', read_only=True)
    log_file_name = serializers.CharField(source='log_file.original_name', read_only=True)
    report_month_display = serializers.SerializerMethodField()
    address_matches_detail = AddressMatchingSerializer(many=True, read_only=True)
    cost_analysis_detail = CostAnalysisSerializer(read_only=True)
    
    class Meta:
        model = MonthlyReport
        fields = [
            'id', 'title', 'report_month', 'report_month_display',
            'csv_file', 'csv_file_name', 'log_file', 'log_file_name',
            'config_data', 'summary_data', 'address_matches', 'address_matches_detail',
            'cost_analysis', 'cost_analysis_detail', 'excel_file', 'pdf_file',
            'is_generated', 'generation_completed_at', 'created_at', 'updated_at'
        ]
    
    def get_report_month_display(self, obj):
        """获取报表月份显示"""
        return obj.report_month.strftime('%Y年%m月')
