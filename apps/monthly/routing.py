"""
月度报表AI WebSocket路由配置
"""
from django.urls import re_path
from .consumers import MonthlyReportAIConsumer

websocket_urlpatterns = [
    re_path(r'ws/monthly/$', MonthlyReportAIConsumer.as_asgi()),
]


