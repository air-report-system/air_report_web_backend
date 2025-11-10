"""
AI配置序列化器
"""
from rest_framework import serializers
from django.core.validators import URLValidator
from .models import AIServiceConfig, AIConfigHistory, AIServiceUsageLog
from .services import AIServiceManager, ai_service_manager


class AIServiceConfigSerializer(serializers.ModelSerializer):
    """AI服务配置序列化器"""
    
    success_rate = serializers.ReadOnlyField()
    extra_config = serializers.JSONField(default=dict, required=False)
    
    class Meta:
        model = AIServiceConfig
        fields = [
            'id', 'name', 'description', 'provider', 'api_format',
            'api_base_url', 'api_key', 'model_name', 'timeout_seconds',
            'max_retries', 'extra_config', 'is_active', 'is_default',
            'priority', 'success_count', 'failure_count', 'success_rate',
            'last_used_at', 'last_test_at', 'last_test_result',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'success_count', 'failure_count', 'success_rate',
            'last_used_at', 'last_test_at', 'last_test_result',
            'created_at', 'updated_at'
        ]
    
    def validate_api_base_url(self, value):
        """验证API基础URL"""
        validator = URLValidator()
        try:
            validator(value)
        except serializers.ValidationError:
            raise serializers.ValidationError("请输入有效的URL")
        return value
    
    def validate_api_key(self, value):
        """验证API密钥"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("API密钥长度不能少于10个字符")
        return value.strip()
    
    def validate_timeout_seconds(self, value):
        """验证超时时间"""
        if value < 5 or value > 300:
            raise serializers.ValidationError("超时时间必须在5-300秒之间")
        return value
    
    def validate_max_retries(self, value):
        """验证最大重试次数"""
        if value < 0 or value > 10:
            raise serializers.ValidationError("最大重试次数必须在0-10之间")
        return value
    
    def validate_priority(self, value):
        """验证优先级"""
        if value < 1 or value > 1000:
            raise serializers.ValidationError("优先级必须在1-1000之间")
        return value


class AIServiceConfigCreateSerializer(AIServiceConfigSerializer):
    """AI服务配置创建序列化器"""
    
    def create(self, validated_data):
        # 设置创建者
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AIServiceConfigUpdateSerializer(AIServiceConfigSerializer):
    """AI服务配置更新序列化器"""
    
    class Meta(AIServiceConfigSerializer.Meta):
        # 更新时不允许修改某些字段
        read_only_fields = AIServiceConfigSerializer.Meta.read_only_fields + [
            'created_by'
        ]


class AIServiceTestSerializer(serializers.Serializer):
    """AI服务测试序列化器"""
    
    name = serializers.CharField(max_length=100, required=False)
    provider = serializers.ChoiceField(
        choices=['gemini', 'openai', 'anthropic', 'custom'],
        required=True
    )
    api_format = serializers.ChoiceField(
        choices=['gemini', 'openai'],
        required=True
    )
    api_base_url = serializers.URLField(required=True)
    api_key = serializers.CharField(max_length=500, required=True)
    model_name = serializers.CharField(max_length=100, required=True)
    timeout_seconds = serializers.IntegerField(min_value=5, max_value=300, default=30)
    max_retries = serializers.IntegerField(min_value=0, max_value=10, default=3)
    extra_config = serializers.JSONField(required=False, default=dict)
    
    def validate(self, data):
        """验证测试数据"""
        # 根据提供商验证API格式
        provider = data.get('provider')
        api_format = data.get('api_format')
        
        if provider == 'gemini' and api_format != 'gemini':
            raise serializers.ValidationError("Gemini提供商必须使用Gemini格式")
        elif provider == 'openai' and api_format != 'openai':
            raise serializers.ValidationError("OpenAI提供商必须使用OpenAI格式")
        
        return data
    
    def test_service(self):
        """执行服务测试"""
        return ai_service_manager.test_service(self.validated_data)


class AIConfigHistorySerializer(serializers.ModelSerializer):
    """AI配置历史序列化器"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AIConfigHistory
        fields = [
            'id', 'config', 'config_name', 'action', 'action_display',
            'old_data', 'new_data', 'user', 'user_name', 'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AIServiceUsageLogSerializer(serializers.ModelSerializer):
    """AI服务使用日志序列化器"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AIServiceUsageLog
        fields = [
            'id', 'config', 'config_name', 'service_type',
            'request_data', 'response_data', 'is_success',
            'error_message', 'response_time_ms', 'user', 'user_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AIServiceSwitchSerializer(serializers.Serializer):
    """AI服务切换序列化器"""
    
    service_name = serializers.CharField(max_length=100, required=True)
    
    def validate_service_name(self, value):
        """验证服务名称"""
        available_services = ai_service_manager.get_available_services()
        
        service_names = [
            service.get('service_name') or service.get('name') 
            for service in available_services
        ]
        
        if value not in service_names:
            raise serializers.ValidationError(f"服务 {value} 不存在或未激活")
        
        return value
    
    def switch_service(self, user=None):
        """执行服务切换"""
        service_name = self.validated_data['service_name']
        return ai_service_manager.switch_service(service_name, user)


class AIServiceStatusSerializer(serializers.Serializer):
    """AI服务状态序列化器"""
    
    current_service = serializers.DictField(read_only=True)
    available_services = serializers.ListField(read_only=True)
    total_services = serializers.IntegerField(read_only=True)
    active_services = serializers.IntegerField(read_only=True)
    
    def get_status(self):
        """获取服务状态"""
        current_service = ai_service_manager.get_current_service_config()
        available_services = ai_service_manager.get_available_services()
        
        return {
            'current_service': current_service,
            'available_services': available_services,
            'total_services': len(available_services),
            'active_services': len([s for s in available_services if s.get('is_active', True)])
        }


class AIServiceStatsSerializer(serializers.Serializer):
    """AI服务统计序列化器"""
    
    service_id = serializers.IntegerField(required=False)
    service_name = serializers.CharField(max_length=100, required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    service_type = serializers.CharField(max_length=50, required=False)
    
    def get_stats(self):
        """获取使用统计"""
        filters = {}
        
        if self.validated_data.get('service_id'):
            filters['config_id'] = self.validated_data['service_id']
        
        if self.validated_data.get('date_from'):
            filters['created_at__gte'] = self.validated_data['date_from']
        
        if self.validated_data.get('date_to'):
            filters['created_at__lte'] = self.validated_data['date_to']
        
        if self.validated_data.get('service_type'):
            filters['service_type'] = self.validated_data['service_type']
        
        logs = AIServiceUsageLog.objects.filter(**filters)
        
        total_requests = logs.count()
        success_requests = logs.filter(is_success=True).count()
        failure_requests = total_requests - success_requests
        
        avg_response_time = logs.filter(
            response_time_ms__isnull=False
        ).aggregate(
            avg_time=models.Avg('response_time_ms')
        )['avg_time'] or 0
        
        from django.db import models

        return {
            'total_requests': total_requests,
            'success_requests': success_requests,
            'failure_requests': failure_requests,
            'success_rate': round((success_requests / total_requests * 100), 2) if total_requests > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 2)
        }
