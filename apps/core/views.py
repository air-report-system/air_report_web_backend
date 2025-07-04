"""
核心视图
"""
import os
import subprocess
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class HealthCheckView(APIView):
    """健康检查视图"""
    permission_classes = []

    def get(self, request):
        """健康检查端点"""
        return Response({
            'status': 'healthy',
            'message': '室内空气检测平台API运行正常'
        }, status=status.HTTP_200_OK)


@csrf_exempt
@require_http_methods(["GET"])
def detailed_health_check(request):
    """
    详细健康检查端点
    检查数据库连接、字体安装、LibreOffice等关键组件
    """
    health_status = {
        "status": "healthy",
        "timestamp": None,
        "checks": {
            "database": False,
            "fonts": False,
            "libreoffice": False,
            "environment": False
        },
        "details": {}
    }

    # 检查数据库连接
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["checks"]["database"] = True
        health_status["details"]["database"] = "Connected"
    except Exception as e:
        health_status["checks"]["database"] = False
        health_status["details"]["database"] = f"Error: {str(e)}"

    # 检查字体安装
    try:
        result = subprocess.run(
            ["fc-list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            fonts_output = result.stdout.lower()
            required_fonts = ["simsun", "arial", "calibri"]
            found_fonts = [font for font in required_fonts if font in fonts_output]

            health_status["checks"]["fonts"] = len(found_fonts) > 0
            health_status["details"]["fonts"] = {
                "found": found_fonts,
                "total_fonts": len(fonts_output.split('\n')) - 1
            }
        else:
            health_status["checks"]["fonts"] = False
            health_status["details"]["fonts"] = "fc-list command failed"
    except Exception as e:
        health_status["checks"]["fonts"] = False
        health_status["details"]["fonts"] = f"Error: {str(e)}"

    # 检查LibreOffice
    try:
        result = subprocess.run(
            ["libreoffice", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            health_status["checks"]["libreoffice"] = True
            health_status["details"]["libreoffice"] = result.stdout.strip()
        else:
            health_status["checks"]["libreoffice"] = False
            health_status["details"]["libreoffice"] = "LibreOffice not found"
    except Exception as e:
        health_status["checks"]["libreoffice"] = False
        health_status["details"]["libreoffice"] = f"Error: {str(e)}"

    # 检查环境变量
    required_env_vars = ["DJANGO_SETTINGS_MODULE"]
    env_status = {}

    for var in required_env_vars:
        env_status[var] = os.getenv(var) is not None

    health_status["checks"]["environment"] = all(env_status.values())
    health_status["details"]["environment"] = {
        "variables": env_status,
        "replit_detected": bool(os.getenv('REPL_ID') or os.getenv('REPLIT_DEV_DOMAIN')),
        "debug_mode": settings.DEBUG
    }

    # 设置时间戳
    from datetime import datetime
    health_status["timestamp"] = datetime.now().isoformat()

    # 确定整体状态
    all_healthy = all(health_status["checks"].values())
    health_status["status"] = "healthy" if all_healthy else "unhealthy"

    # 返回适当的HTTP状态码
    status_code = 200 if all_healthy else 503

    return JsonResponse(health_status, status=status_code)
