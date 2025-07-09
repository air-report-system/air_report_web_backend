"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.core.views import HealthCheckView, detailed_health_check


def api_root(request):
    """API根路径，快速健康检查响应"""
    return JsonResponse({
        'status': 'ok',
        'message': 'API is running'
    })

def simple_health_check(request):
    """超简单的健康检查，立即返回200状态码"""
    try:
        return HttpResponse("OK", status=200, content_type="text/plain")
    except Exception as e:
        # 如果有任何错误，仍然返回200但记录错误
        return HttpResponse(f"OK-{str(e)[:50]}", status=200, content_type="text/plain")

urlpatterns = [
    # 根路径 - 快速健康检查
    path('', simple_health_check, name='api-root'),

    # 专门的健康检查端点
    path('health', simple_health_check, name='health-simple'),  # 不带斜杠
    path('health/', simple_health_check, name='health-check'),
    path('health/detailed/', detailed_health_check, name='health-check-detailed'),

    # API状态端点
    path('api/', api_root, name='api-status'),

    # 管理后台
    path('admin/', admin.site.urls),

    # API文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API路由 - 同时支持带斜杠和不带斜杠
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/files/', include('apps.files.urls')),
    path('api/v1/ocr/', include('apps.ocr.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/reports', include('apps.reports.urls')),  # 不带斜杠的版本
    path('api/v1/batch/', include('apps.batch.urls')),
    path('api/v1/monthly/', include('apps.monthly.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/orders', include('apps.orders.urls')),  # 不带斜杠的版本
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
