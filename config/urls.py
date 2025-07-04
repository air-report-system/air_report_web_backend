"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def api_root(request):
    """API根路径，返回可用的API端点"""
    return JsonResponse({
        'message': '欢迎使用检测报告管理系统API',
        'version': '1.0.0',
        'endpoints': {
            'admin': '/admin/',
            'api_docs': '/api/docs/',
            'api_redoc': '/api/redoc/',
            'api_schema': '/api/schema/',
            'auth': '/api/v1/auth/',
            'files': '/api/v1/files/',
            'ocr': '/api/v1/ocr/',
            'reports': '/api/v1/reports/',
            'batch': '/api/v1/batch/',
            'monthly': '/api/v1/monthly/',
            'wechat_csv': '/api/v1/wechat-csv/',
            'orders': '/api/v1/orders/',
        }
    })

urlpatterns = [
    # 根路径
    path('', api_root, name='api-root'),

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
    path('api/v1/wechat-csv/', include('apps.wechat_csv.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
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
