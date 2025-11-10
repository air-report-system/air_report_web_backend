"""
AI配置管理视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import AIServiceConfig, AIConfigHistory, AIServiceUsageLog
from .serializers import (
    AIServiceConfigSerializer, AIServiceConfigCreateSerializer,
    AIServiceConfigUpdateSerializer, AIServiceTestSerializer,
    AIConfigHistorySerializer, AIServiceUsageLogSerializer,
    AIServiceSwitchSerializer, AIServiceStatusSerializer,
    AIServiceStatsSerializer
)
from .services import AIServiceManager, ai_service_manager
from .monitoring import get_system_health, ai_monitor
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="获取AI配置列表",
        description="获取所有AI服务配置的列表，支持按状态和提供商过滤",
        parameters=[
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='过滤激活状态的配置'
            ),
            OpenApiParameter(
                name='provider',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='过滤指定提供商的配置（gemini/openai/anthropic）'
            ),
        ],
        tags=['AI配置管理']
    ),
    create=extend_schema(
        summary="创建AI配置",
        description="创建新的AI服务配置",
        tags=['AI配置管理']
    ),
    retrieve=extend_schema(
        summary="获取AI配置详情",
        description="获取指定AI配置的详细信息",
        tags=['AI配置管理']
    ),
    update=extend_schema(
        summary="更新AI配置",
        description="完整更新AI配置信息",
        tags=['AI配置管理']
    ),
    partial_update=extend_schema(
        summary="部分更新AI配置",
        description="部分更新AI配置信息",
        tags=['AI配置管理']
    ),
    destroy=extend_schema(
        summary="删除AI配置",
        description="删除指定的AI配置",
        tags=['AI配置管理']
    ),
)
class AIServiceConfigViewSet(viewsets.ModelViewSet):
    """AI服务配置管理视图集"""

    queryset = AIServiceConfig.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIServiceConfigCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AIServiceConfigUpdateSerializer
        return AIServiceConfigSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 过滤参数
        is_active = self.request.query_params.get('is_active')
        provider = self.request.query_params.get('provider')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if provider:
            queryset = queryset.filter(provider=provider)
        
        return queryset.order_by('priority', '-created_at')
    
    def perform_create(self, serializer):
        """创建配置时记录历史"""
        with transaction.atomic():
            config = serializer.save()
            
            # 记录创建历史
            AIConfigHistory.objects.create(
                config=config,
                action='create',
                new_data=serializer.data,
                user=self.request.user,
                notes=f"创建AI服务配置: {config.name}"
            )
            
            logger.info(f"用户 {self.request.user.username} 创建了AI配置: {config.name}")
    
    def perform_update(self, serializer):
        """更新配置时记录历史"""
        with transaction.atomic():
            old_data = AIServiceConfigSerializer(serializer.instance).data
            config = serializer.save()
            
            # 记录更新历史
            AIConfigHistory.objects.create(
                config=config,
                action='update',
                old_data=old_data,
                new_data=serializer.data,
                user=self.request.user,
                notes=f"更新AI服务配置: {config.name}"
            )
            
            logger.info(f"用户 {self.request.user.username} 更新了AI配置: {config.name}")
    
    def perform_destroy(self, instance):
        """删除配置时记录历史"""
        with transaction.atomic():
            old_data = AIServiceConfigSerializer(instance).data
            
            # 记录删除历史
            AIConfigHistory.objects.create(
                config=instance,
                action='delete',
                old_data=old_data,
                user=self.request.user,
                notes=f"删除AI服务配置: {instance.name}"
            )
            
            logger.info(f"用户 {self.request.user.username} 删除了AI配置: {instance.name}")
            super().perform_destroy(instance)
    
    @extend_schema(
        summary="测试AI配置",
        description="测试指定AI配置的连接性和可用性",
        tags=['AI配置管理'],
        responses={
            200: {'description': '测试成功'},
            400: {'description': '测试失败'}
        }
    )
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """测试AI服务配置"""
        config = self.get_object()
        
        try:
            config_dict = ai_service_manager._db_config_to_dict(config)
            
            # 执行测试
            test_result = ai_service_manager.test_service(config_dict)
            
            # 更新测试结果
            config.update_test_result(test_result)
            
            # 记录测试历史
            AIConfigHistory.objects.create(
                config=config,
                action='test',
                new_data=test_result,
                user=request.user,
                notes=f"测试AI服务配置: {config.name}"
            )
            
            logger.info(f"用户 {request.user.username} 测试了AI配置: {config.name}")
            
            return Response({
                'success': True,
                'message': '测试完成',
                'result': test_result
            })
            
        except Exception as e:
            logger.error(f"测试AI配置失败: {e}")
            return Response({
                'success': False,
                'message': f'测试失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活AI服务配置"""
        config = self.get_object()
        
        try:
            with transaction.atomic():
                config.is_active = True
                config.save()
                ai_service_manager.clear_cache()
                
                # 记录激活历史
                AIConfigHistory.objects.create(
                    config=config,
                    action='activate',
                    user=request.user,
                    notes=f"激活AI服务配置: {config.name}"
                )
                
                logger.info(f"用户 {request.user.username} 激活了AI配置: {config.name}")
                
                return Response({
                    'success': True,
                    'message': f'已激活配置: {config.name}'
                })
                
        except Exception as e:
            logger.error(f"激活AI配置失败: {e}")
            return Response({
                'success': False,
                'message': f'激活失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """停用AI服务配置"""
        config = self.get_object()
        
        # 检查是否为默认配置
        if config.is_default:
            return Response({
                'success': False,
                'message': '不能停用默认配置'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                config.is_active = False
                config.save()
                ai_service_manager.clear_cache()
                
                # 记录停用历史
                AIConfigHistory.objects.create(
                    config=config,
                    action='deactivate',
                    user=request.user,
                    notes=f"停用AI服务配置: {config.name}"
                )
                
                logger.info(f"用户 {request.user.username} 停用了AI配置: {config.name}")
                
                return Response({
                    'success': True,
                    'message': f'已停用配置: {config.name}'
                })
                
        except Exception as e:
            logger.error(f"停用AI配置失败: {e}")
            return Response({
                'success': False,
                'message': f'停用失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        
        if not config.is_active:
            return Response({
                'success': False,
                'message': '只能将激活的配置设为默认'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # 取消其他默认配置
                AIServiceConfig.objects.filter(is_default=True).update(is_default=False)
                
                # 设置当前配置为默认
                config.is_default = True
                config.save()
                ai_service_manager.switch_service(config.name, request.user)
                
                # 记录历史
                AIConfigHistory.objects.create(
                    config=config,
                    action='update',
                    user=request.user,
                    notes=f"设置为默认AI服务配置: {config.name}"
                )
                
                logger.info(f"用户 {request.user.username} 将AI配置设为默认: {config.name}")
                
                return Response({
                    'success': True,
                    'message': f'已将 {config.name} 设为默认配置'
                })
                
        except Exception as e:
            logger.error(f"设置默认AI配置失败: {e}")
            return Response({
                'success': False,
                'message': f'设置失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def test_config(self, request):
        """测试配置（不保存到数据库）"""
        serializer = AIServiceTestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                test_result = serializer.test_service()
                
                return Response({
                    'success': True,
                    'message': '测试完成',
                    'result': test_result
                })
                
            except Exception as e:
                logger.error(f"测试配置失败: {e}")
                return Response({
                    'success': False,
                    'message': f'测试失败: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'message': '配置数据无效',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def switch_service(self, request):
        """切换当前使用的AI服务"""
        serializer = AIServiceSwitchSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                success = serializer.switch_service(request.user)
                
                if success:
                    return Response({
                        'success': True,
                        'message': f'已切换到服务: {serializer.validated_data["service_name"]}'
                    })
                else:
                    return Response({
                        'success': False,
                        'message': '切换服务失败'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"切换服务失败: {e}")
                return Response({
                    'success': False,
                    'message': f'切换失败: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'message': '请求数据无效',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="获取AI服务状态",
        description="获取当前AI服务的运行状态和可用服务列表",
        tags=['AI监控'],
        responses={
            200: {'description': '状态获取成功'}
        }
    )
    @action(detail=False, methods=['get'])
    def status(self, request):
        """获取AI服务状态"""
        try:
            serializer = AIServiceStatusSerializer()
            status_data = serializer.get_status()
            
            return Response({
                'success': True,
                'data': status_data
            })
            
        except Exception as e:
            logger.error(f"获取服务状态失败: {e}")
            return Response({
                'success': False,
                'message': f'获取状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取AI服务使用统计"""
        serializer = AIServiceStatsSerializer(data=request.query_params)

        if serializer.is_valid():
            try:
                stats_data = serializer.get_stats()

                return Response({
                    'success': True,
                    'data': stats_data
                })

            except Exception as e:
                logger.error(f"获取使用统计失败: {e}")
                return Response({
                    'success': False,
                    'message': f'获取统计失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': False,
            'message': '查询参数无效',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def health(self, request):
        """获取系统健康状态"""
        try:
            health_data = get_system_health()

            return Response({
                'success': True,
                'data': health_data
            })

        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return Response({
                'success': False,
                'message': f'获取健康状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def monitor(self, request, pk=None):
        """获取特定服务的监控数据"""
        config = self.get_object()

        try:
            # 获取服务统计
            stats = ai_monitor.get_service_stats(config.name)

            # 获取健康状态
            health = ai_monitor.check_service_health(config.name)

            return Response({
                'success': True,
                'data': {
                    'service_name': config.name,
                    'stats': stats,
                    'health': health,
                    'config_stats': {
                        'success_count': config.success_count,
                        'failure_count': config.failure_count,
                        'success_rate': config.success_rate,
                        'last_used_at': config.last_used_at,
                        'last_test_at': config.last_test_at
                    }
                }
            })

        except Exception as e:
            logger.error(f"获取服务监控数据失败: {e}")
            return Response({
                'success': False,
                'message': f'获取监控数据失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIConfigHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """AI配置历史视图集"""

    queryset = AIConfigHistory.objects.all()
    serializer_class = AIConfigHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 过滤参数
        config_id = self.request.query_params.get('config_id')
        action = self.request.query_params.get('action')
        user_id = self.request.query_params.get('user_id')

        if config_id:
            queryset = queryset.filter(config_id=config_id)

        if action:
            queryset = queryset.filter(action=action)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-created_at')


class AIServiceUsageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """AI服务使用日志视图集"""

    queryset = AIServiceUsageLog.objects.all()
    serializer_class = AIServiceUsageLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 过滤参数
        config_id = self.request.query_params.get('config_id')
        service_type = self.request.query_params.get('service_type')
        is_success = self.request.query_params.get('is_success')
        user_id = self.request.query_params.get('user_id')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if config_id:
            queryset = queryset.filter(config_id=config_id)

        if service_type:
            queryset = queryset.filter(service_type=service_type)

        if is_success is not None:
            queryset = queryset.filter(is_success=is_success.lower() == 'true')

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if date_from:
            try:
                date_from_parsed = parse_datetime(date_from)
                if date_from_parsed:
                    queryset = queryset.filter(created_at__gte=date_from_parsed)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_parsed = parse_datetime(date_to)
                if date_to_parsed:
                    queryset = queryset.filter(created_at__lte=date_to_parsed)
            except ValueError:
                pass

        return queryset.order_by('-created_at')
