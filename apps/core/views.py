"""
核心视图
"""
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
