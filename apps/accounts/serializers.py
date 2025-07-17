"""
用户认证序列化器
"""
import base64
import imghdr
from io import BytesIO
from rest_framework import serializers
from .models import User, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'company', 'role', 'is_active', 'date_joined',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """创建用户"""
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """用户配置序列化器"""
    
    class Meta:
        model = UserProfile
        fields = [
            'default_ocr_settings', 'ui_preferences', 'notification_settings',
            'background_image', 'background_opacity', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_background_image(self, value):
        """验证背景图片数据"""
        if not value:
            return value
            
        try:
            # 检查是否为有效的base64格式
            if not value.startswith('data:image/'):
                raise serializers.ValidationError("背景图片必须是有效的data URL格式")
            
            # 提取base64数据部分
            header, data = value.split(',', 1)
            
            # 检查MIME类型
            if not any(img_type in header for img_type in ['jpeg', 'jpg', 'png']):
                raise serializers.ValidationError("背景图片只支持JPEG和PNG格式")
            
            # 解码base64数据
            try:
                image_data = base64.b64decode(data)
            except Exception:
                raise serializers.ValidationError("背景图片base64数据无效")
            
            # 检查文件大小（5MB限制）
            if len(image_data) > 5 * 1024 * 1024:
                raise serializers.ValidationError("背景图片大小不能超过5MB")
            
            # 验证图片格式
            image_type = imghdr.what(BytesIO(image_data))
            if image_type not in ['jpeg', 'png']:
                raise serializers.ValidationError("背景图片格式不正确")
                
        except ValueError:
            raise serializers.ValidationError("背景图片数据格式错误")
        
        return value
    
    def validate_background_opacity(self, value):
        """验证背景图透明度"""
        if value is not None:
            if not 0 <= value <= 1:
                raise serializers.ValidationError("背景图透明度必须在0-1之间")
        return value


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(max_length=128, write_only=True)
    new_password = serializers.CharField(max_length=128, write_only=True)
    confirm_password = serializers.CharField(max_length=128, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("新密码和确认密码不匹配")
        return data
