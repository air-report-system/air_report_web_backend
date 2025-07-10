"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.core.views import version_info, health_check, root_view


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
    # 根路径 - 基本API信息
    path('', root_view, name='api-root'),

    # 专门的健康检查端点
    path('health', simple_health_check, name='health-simple'),  # 不带斜杠
    path('health/', simple_health_check, name='health-check'),
    path('api/v1/health/', health_check, name='health-check-detailed'),

    # API状态端点
    path('api/', api_root, name='api-status'),
    path('api/v1/', api_root, name='api-v1-status'),
    
    # 版本信息端点
    path('api/v1/version/', version_info, name='version-info'),

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

# 静态文件和媒体文件服务
if settings.DEBUG:
    # 开发环境：Django自动提供静态文件和媒体文件服务
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
else:
    # 生产环境：手动添加媒体文件服务（适用于Replit等小型部署）
    # 注意：大型生产环境应使用Nginx等Web服务器来提供媒体文件
    from django.views.static import serve
    from django.urls import re_path

    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
