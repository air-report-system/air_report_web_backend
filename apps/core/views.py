from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import os
import sys
import platform
import datetime
import django

# Create your views here.

def get_version():
    """
    从.version文件读取版本信息
    每次调用都重新读取文件，避免缓存问题
    """
    try:
        import os
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.version')
        # 强制重新读取文件，避免任何可能的缓存
        with open(version_file, 'r', encoding='utf-8') as f:
            version_content = f.read().strip()
        # 添加时间戳确保每次读取都是最新的
        import time
        return version_content
    except Exception as e:
        return '1.0.0_unknown'

@api_view(['GET'])
@permission_classes([AllowAny])
def version_info(request):
    """
    返回应用版本和部署信息
    """
    try:
        # 从.version文件读取版本
        version = get_version()
        
        # 构建版本信息
        version_data = {
            'app_name': '室内空气检测数据处理系统 - 后端API',
            'version': version,
            'version_source': '.version文件',
            'deploy_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'django_version': django.get_version(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'platform': platform.system(),
            'platform_version': platform.release(),
            'debug_mode': settings.DEBUG,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'settings_module': os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.base'),
            'allowed_hosts': settings.ALLOWED_HOSTS,
            'cors_origins': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            'static_url': settings.STATIC_URL,
            'media_url': settings.MEDIA_URL,
            'timezone': settings.TIME_ZONE,
            'environment': {
                'PYTHONPATH': os.getenv('PYTHONPATH', ''),
                'DJANGO_SETTINGS_MODULE': os.getenv('DJANGO_SETTINGS_MODULE', ''),
                'REPL_DEPLOYMENT': os.getenv('REPL_DEPLOYMENT', 'false'),
                'NODE_ENV': os.getenv('NODE_ENV', 'development')
            }
        }
        
        return Response(version_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': '版本信息获取失败',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    健康检查端点
    """
    try:
        # 检查数据库连接
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        db_status = "connected"
        
        # 检查Redis连接（如果配置了）
        redis_status = "not configured"
        try:
            import redis
            redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)
            redis_client.ping()
            redis_status = "connected"
        except:
            redis_status = "disconnected"
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'database': db_status,
            'redis': redis_status,
            'services': {
                'api': 'running',
                'static_files': 'configured',
                'media_files': 'configured'
            }
        }
        
        return Response(health_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def root_view(request):
    """
    根路径视图 - 提供基本的服务信息
    """
    if request.method == 'GET':
        version = get_version()
        return JsonResponse({
            'message': '室内空气检测数据处理系统 - 后端API',
            'version': version,
            'status': 'running',
            'endpoints': {
                'api': '/api/v1/',
                'admin': '/admin/',
                'version': '/api/v1/version/',
                'health': '/api/v1/health/',
                'docs': {
                    'swagger': '/api/docs/',
                    'redoc': '/api/redoc/',
                    'schema': '/api/schema/'
                },
                'ai_config': {
                    'configs': '/api/v1/ai-config/configs/',
                    'status': '/api/v1/ai-config/configs/status/',
                    'health': '/api/v1/ai-config/configs/health/'
                },
                'ocr': '/api/v1/ocr/',
                'files': '/api/v1/files/',
                'reports': '/api/v1/reports/',
                'batch': '/api/v1/batch/',
                'monthly': '/api/v1/monthly/'
            },
            'version_source': '.version文件',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return JsonResponse({
            'error': 'Method not allowed',
            'allowed_methods': ['GET']
        }, status=405)
