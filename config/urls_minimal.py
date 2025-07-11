"""
Minimal URL configuration for testing CSV export feature
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    """API root path"""
    return JsonResponse({
        'status': 'ok',
        'message': 'API is running'
    })

urlpatterns = [
    # Basic paths
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-status'),
    
    # Orders API only
    path('api/v1/orders/', include('apps.orders.urls')),
]