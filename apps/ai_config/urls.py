"""
AI配置管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIServiceConfigViewSet,
    AIConfigHistoryViewSet,
    AIServiceUsageLogViewSet
)

# 创建路由器
router = DefaultRouter(trailing_slash=False)
router.register(r'configs', AIServiceConfigViewSet, basename='ai-config')
router.register(r'history', AIConfigHistoryViewSet, basename='ai-config-history')
router.register(r'logs', AIServiceUsageLogViewSet, basename='ai-usage-log')

app_name = 'ai_config'

urlpatterns = [
    path('', include(router.urls)),
]
