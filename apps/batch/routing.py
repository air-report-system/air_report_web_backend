"""
批量处理WebSocket路由配置
"""
from django.urls import re_path
from .consumers import BatchProcessingConsumer

websocket_urlpatterns = [
    re_path(r'ws/batch/$', BatchProcessingConsumer.as_asgi()),
]