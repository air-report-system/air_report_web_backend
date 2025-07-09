"""
主要的WebSocket路由配置
"""
from django.urls import path
from apps.batch.routing import websocket_urlpatterns as batch_websocket_urlpatterns

# 汇总所有WebSocket路由
websocket_urlpatterns = [
    # 批量处理WebSocket路由
    *batch_websocket_urlpatterns,
    # 未来可以添加其他模块的WebSocket路由
]