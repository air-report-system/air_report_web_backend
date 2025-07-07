"""
OCR处理视图
"""
import logging
import os
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from .models import OCRResult, ContactInfo, PointLearning, PointValue
from .serializers import (
    OCRResultSerializer,
    OCRProcessSerializer,
    ImageUploadAndProcessSerializer,
    OCRResultUpdateSerializer,
    ContactInfoSerializer,
    ContactInfoUpdateSerializer,
    PointLearningSerializer,
    PointValueSerializer,
    PointLearningUpdateSerializer,
    PointSuggestionSerializer,
    CheckTypeInferenceSerializer
)
from apps.files.models import UploadedFile
from apps.files.serializers import UploadedFileSerializer

logger = logging.getLogger(__name__)


class OCRResultViewSet(viewsets.ModelViewSet):
    """OCR结果管理视图集"""
    queryset = OCRResult.objects.all()
    serializer_class = OCRResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的OCR结果"""
        queryset = OCRResult.objects.filter(created_by=self.request.user)

        # 支持按状态过滤
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 支持按检测类型过滤
        check_type = self.request.query_params.get('check_type')
        if check_type:
            queryset = queryset.filter(check_type=check_type)

        # 支持按冲突状态过滤
        has_conflicts = self.request.query_params.get('has_conflicts')
        if has_conflicts is not None:
            queryset = queryset.filter(has_conflicts=has_conflicts.lower() == 'true')

        return queryset.select_related('file', 'contactinfo').order_by('-created_at')

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action in ['update', 'partial_update']:
            return OCRResultUpdateSerializer
        return OCRResultSerializer

    @extend_schema(
        summary="重新处理OCR",
        description="重新处理指定的OCR结果",
        request=OCRProcessSerializer,
        responses={202: {'description': '处理已开始'}}
    )
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """重新处理OCR"""
        ocr_result = self.get_object()

        serializer = OCRProcessSerializer(data={
            'file_id': ocr_result.file.id,
            **request.data
        })

        if serializer.is_valid():
            # 调用异步OCR处理任务
            from .tasks import process_image_ocr

            task = process_image_ocr.delay(
                ocr_result.file.id,
                request.user.id,
                serializer.validated_data.get('use_multi_ocr', False),
                serializer.validated_data.get('ocr_count', 3)
            )

            # 更新状态为处理中
            ocr_result.status = 'processing'
            ocr_result.error_message = ''
            ocr_result.save()

            return Response({
                'message': '重新处理已开始',
                'ocr_result_id': ocr_result.id,
                'task_id': str(task.id),
                'status': 'processing'
            }, status=status.HTTP_202_ACCEPTED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="更新联系人信息",
        description="更新OCR结果关联的联系人信息",
        request=ContactInfoUpdateSerializer,
        responses={200: ContactInfoSerializer}
    )
    @action(detail=True, methods=['post', 'put'])
    def update_contact(self, request, pk=None):
        """更新联系人信息"""
        ocr_result = self.get_object()

        try:
            contact_info = ocr_result.contactinfo
        except ContactInfo.DoesNotExist:
            contact_info = ContactInfo(ocr_result=ocr_result)

        serializer = ContactInfoUpdateSerializer(contact_info, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                ContactInfoSerializer(serializer.instance).data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProcessImageView(APIView):
    """图片OCR处理视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="处理已上传的图片",
        description="对已上传的图片进行OCR处理",
        request=OCRProcessSerializer,
        responses={202: {'description': '处理已开始'}}
    )
    def post(self, request):
        """处理已上传的图片"""
        serializer = OCRProcessSerializer(data=request.data)

        if serializer.is_valid():
            file_id = serializer.validated_data['file_id']
            use_multi_ocr = serializer.validated_data.get('use_multi_ocr', False)
            ocr_count = serializer.validated_data.get('ocr_count', 3)

            try:
                file_obj = UploadedFile.objects.get(
                    id=file_id,
                    created_by=request.user
                )

                # 检查是否已有处理中的OCR任务
                existing_ocr = OCRResult.objects.filter(
                    file=file_obj,
                    status__in=['pending', 'processing']
                ).first()

                if existing_ocr:
                    return Response({
                        'error': '该文件已有处理中的OCR任务',
                        'ocr_result_id': existing_ocr.id
                    }, status=status.HTTP_409_CONFLICT)

                # 创建OCR结果记录
                ocr_result = OCRResult.objects.create(
                    file=file_obj,
                    status='pending',
                    ocr_attempts=ocr_count if use_multi_ocr else 1,
                    created_by=request.user
                )

                # 调用异步OCR处理任务
                from .tasks import process_image_ocr

                task = process_image_ocr.delay(
                    file_id,
                    request.user.id,
                    use_multi_ocr,
                    ocr_count
                )

                return Response({
                    'message': 'OCR处理已开始',
                    'ocr_result_id': ocr_result.id,
                    'file_id': file_id,
                    'task_id': str(task.id),
                    'status': 'pending'
                }, status=status.HTTP_202_ACCEPTED)

            except UploadedFile.DoesNotExist:
                return Response({
                    'error': '文件不存在或无权限访问'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({
                    'error': f'处理失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadAndProcessView(APIView):
    """上传图片并处理视图"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="上传图片并进行OCR处理",
        description="上传图片文件并立即进行OCR处理",
        request=ImageUploadAndProcessSerializer,
        responses={202: {'description': '上传和处理已开始'}}
    )
    def post(self, request):
        """上传图片并处理"""
        logger.info(f"开始上传和处理图片，用户: {request.user.id}")
        
        serializer = ImageUploadAndProcessSerializer(data=request.data)

        if serializer.is_valid():
            image = serializer.validated_data['image']
            use_multi_ocr = serializer.validated_data.get('use_multi_ocr', False)
            ocr_count = serializer.validated_data.get('ocr_count', 3)

            try:
                with transaction.atomic():
                    # 计算文件哈希
                    import hashlib
                    image.seek(0)
                    file_content = image.read()
                    file_hash = hashlib.md5(file_content).hexdigest()
                    image.seek(0)  # 重置文件指针

                    # 检查是否已存在相同文件
                    existing_file = UploadedFile.objects.filter(
                        hash_md5=file_hash,
                        created_by=request.user
                    ).first()

                    if existing_file and existing_file.file and os.path.exists(existing_file.file.path):
                        # 使用现有文件（仅当物理文件存在时）
                        uploaded_file = existing_file
                        logger.info(f"使用现有文件: {uploaded_file.id}")
                    else:
                        # 创建新文件记录（如果没有文件或物理文件不存在）
                        if existing_file:
                            logger.warning(f"现有文件 {existing_file.id} 的物理文件不存在，创建新文件")
                        uploaded_file = UploadedFile.objects.create(
                            file=image,
                            original_name=image.name,
                            created_by=request.user
                        )
                        logger.info(f"创建新文件: {uploaded_file.id}")

                    # 检查是否已有处理中的OCR任务
                    existing_ocr = OCRResult.objects.filter(
                        file=uploaded_file,
                        status__in=['pending', 'processing']
                    ).first()

                    if existing_ocr:
                        logger.info(f"文件已有处理中的OCR任务: {existing_ocr.id}")
                        return Response({
                            'message': '该文件已有处理中的OCR任务',
                            'file_id': uploaded_file.id,
                            'ocr_result_id': existing_ocr.id,
                            'status': existing_ocr.status
                        }, status=status.HTTP_200_OK)

                    # 创建OCR结果记录
                    ocr_result = OCRResult.objects.create(
                        file=uploaded_file,
                        status='pending',
                        ocr_attempts=ocr_count if use_multi_ocr else 1,
                        created_by=request.user
                    )
                    logger.info(f"创建OCR结果记录: {ocr_result.id}")

                # 检查是否在同步模式下运行（如Replit）
                from django.conf import settings
                if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                    # 同步模式：直接处理
                    logger.info("使用同步模式处理OCR")
                    try:
                        from .tasks import process_image_ocr_sync
                        result = process_image_ocr_sync(
                            uploaded_file.id,
                            request.user.id,
                            use_multi_ocr,
                            ocr_count
                        )
                        
                        # 获取更新后的OCR结果
                        ocr_result.refresh_from_db()
                        
                        return Response({
                            'message': '文件上传成功，OCR处理完成',
                            'file_id': uploaded_file.id,
                            'ocr_result_id': ocr_result.id,
                            'status': ocr_result.status,
                            'phone': ocr_result.phone,
                            'processing_result': result
                        }, status=status.HTTP_200_OK)
                        
                    except Exception as sync_error:
                        logger.error(f"同步OCR处理失败: {sync_error}", exc_info=True)
                        # 更新OCR结果状态
                        ocr_result.status = 'failed'
                        ocr_result.error_message = str(sync_error)
                        ocr_result.save()
                        
                        # 尝试降级到 Gemini API
                        logger.info("尝试降级到 Gemini API")
                        try:
                            from .services import GeminiOCRService
                            import tempfile
                            
                            gemini_service = GeminiOCRService()
                            
                            # 创建临时文件用于处理
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                                image.seek(0)  # 重置文件指针
                                for chunk in image.chunks():
                                    temp_file.write(chunk)
                                temp_image_path = temp_file.name
                            
                            try:
                                fallback_result = gemini_service.process_image(temp_image_path)
                                logger.info("Gemini API 处理成功")
                            finally:
                                # 清理临时文件
                                if os.path.exists(temp_image_path):
                                    os.unlink(temp_image_path)
                            
                            # 更新OCR结果
                            ocr_result.status = 'completed'
                            ocr_result.phone = fallback_result.get('phone', '')
                            ocr_result.date = fallback_result.get('date', '')
                            ocr_result.temperature = fallback_result.get('temperature', '')
                            ocr_result.humidity = fallback_result.get('humidity', '')
                            ocr_result.check_type = fallback_result.get('check_type', 'initial')
                            ocr_result.points_data = fallback_result.get('points_data', {})
                            ocr_result.raw_response = fallback_result.get('raw_response', '')
                            ocr_result.confidence_score = fallback_result.get('confidence_score', 0.0)
                            ocr_result.error_message = ''
                            ocr_result.save()
                            
                            return Response({
                                'message': '文件上传成功，OCR处理完成（使用备用服务）',
                                'file_id': uploaded_file.id,
                                'ocr_result_id': ocr_result.id,
                                'status': ocr_result.status,
                                'phone': ocr_result.phone,
                                'fallback_used': True
                            }, status=status.HTTP_200_OK)
                            
                        except Exception as fallback_error:
                            logger.error(f"降级处理也失败: {fallback_error}", exc_info=True)
                            return Response({
                                'error': f'OCR处理失败: {str(sync_error)}',
                                'fallback_error': str(fallback_error),
                                'file_id': uploaded_file.id,
                                'ocr_result_id': ocr_result.id,
                                'status': 'failed'
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    # 异步模式：使用Celery
                    logger.info("使用异步模式处理OCR")
                    from .tasks import process_image_ocr

                    task = process_image_ocr.delay(
                        uploaded_file.id,
                        request.user.id,
                        use_multi_ocr,
                        ocr_count
                    )

                    return Response({
                        'message': '文件上传成功，OCR处理已开始',
                        'file_id': uploaded_file.id,
                        'ocr_result_id': ocr_result.id,
                        'task_id': str(task.id),
                        'status': 'pending'
                    }, status=status.HTTP_202_ACCEPTED)

            except Exception as e:
                logger.error(f"上传和处理失败: {str(e)}", exc_info=True)
                return Response({
                    'error': f'上传和处理失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.error(f"序列化器验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestOCRView(APIView):
    """OCR测试视图"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="测试OCR处理",
        description="直接测试OCR处理功能，不保存到数据库",
        request=ImageUploadAndProcessSerializer,
        responses={200: {'description': 'OCR测试结果'}}
    )
    def post(self, request):
        """测试OCR处理"""
        serializer = ImageUploadAndProcessSerializer(data=request.data)

        if serializer.is_valid():
            image = serializer.validated_data['image']

            try:
                # 临时保存图片
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    for chunk in image.chunks():
                        temp_file.write(chunk)
                    temp_image_path = temp_file.name

                try:
                    # 检查是否使用多重OCR
                    use_multi_ocr = serializer.validated_data.get('use_multi_ocr', False)
                    ocr_count = serializer.validated_data.get('ocr_count', 3)

                    if use_multi_ocr:
                        # 调用增强OCR服务
                        from .services import get_enhanced_ocr_service
                        enhanced_ocr_service = get_enhanced_ocr_service()

                        result = enhanced_ocr_service.process_image_multi_ocr(temp_image_path, ocr_count)

                        return Response({
                            'status': 'success',
                            'message': '多重OCR测试完成',
                            'service_type': 'EnhancedOCRService',
                            'ocr_attempts': result.get('ocr_attempts', ocr_count),
                            'has_conflicts': result.get('has_conflicts', False),
                            'best_result': result.get('best_result', {}),
                            'analysis': result.get('analysis', {})
                        })
                    else:
                        # 调用单次OCR服务
                        from .services import get_ocr_service
                        ocr_service = get_ocr_service()

                        result = ocr_service.process_image(temp_image_path)

                        return Response({
                            'status': 'success',
                            'message': 'OCR测试完成',
                            'service_type': ocr_service.__class__.__name__,
                            'result': result
                        })

                finally:
                    # 清理临时文件
                    if os.path.exists(temp_image_path):
                        os.unlink(temp_image_path)

            except Exception as e:
                return Response({
                    'status': 'error',
                    'error': str(e),
                    'message': 'OCR测试失败'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PointLearningViewSet(viewsets.ModelViewSet):
    """点位学习管理视图集"""
    queryset = PointLearning.objects.all()
    serializer_class = PointLearningSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """获取点位学习数据"""
        queryset = PointLearning.objects.all()

        # 支持按使用次数过滤
        min_usage = self.request.query_params.get('min_usage')
        if min_usage:
            try:
                queryset = queryset.filter(usage_count__gte=int(min_usage))
            except ValueError:
                pass

        # 支持搜索点位名称
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(point_name__icontains=search)

        return queryset

    @extend_schema(
        summary="获取热门点位",
        description="获取使用频率最高的点位列表",
        parameters=[
            {
                'name': 'limit',
                'in': 'query',
                'description': '返回数量限制',
                'required': False,
                'schema': {'type': 'integer', 'default': 20}
            }
        ]
    )
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """获取热门点位"""
        limit = int(request.query_params.get('limit', 20))
        popular_points = PointLearning.get_popular_points(limit)
        serializer = self.get_serializer(popular_points, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="获取点位建议",
        description="根据已有点位获取智能建议",
        request=PointSuggestionSerializer,
        responses={200: PointLearningSerializer(many=True)}
    )
    @action(detail=False, methods=['post'])
    def suggestions(self, request):
        """获取点位建议"""
        serializer = PointSuggestionSerializer(data=request.data)
        if serializer.is_valid():
            existing_points = serializer.validated_data.get('existing_points', [])
            limit = serializer.validated_data.get('limit', 10)

            suggested_points = PointLearning.get_suggested_points(existing_points, limit)
            response_serializer = PointLearningSerializer(suggested_points, many=True)
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="更新点位学习数据",
        description="批量更新点位使用统计",
        request=PointLearningUpdateSerializer,
        responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
    )
    @action(detail=False, methods=['post'])
    def update_learning(self, request):
        """更新点位学习数据"""
        serializer = PointLearningUpdateSerializer(data=request.data)
        if serializer.is_valid():
            points_data = serializer.validated_data['points_data']
            check_type = serializer.validated_data['check_type']

            updated_count = 0
            with transaction.atomic():
                for point_name, value in points_data.items():
                    point_learning, created = PointLearning.objects.get_or_create(
                        point_name=point_name,
                        defaults={
                            'usage_count': 0,
                            'total_value': 0.0,
                            'avg_value': 0.0,
                        }
                    )
                    point_learning.update_statistics(value, check_type)
                    updated_count += 1

            return Response({
                'message': f'成功更新{updated_count}个点位的学习数据',
                'updated_count': updated_count
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckTypeInferenceAPIView(APIView):
    """检测类型推断API"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="推断检测类型",
        description="根据点位数据推断是初检还是复检",
        request=CheckTypeInferenceSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'inferred_type': {'type': 'string', 'enum': ['initial', 'recheck']},
                    'confidence': {'type': 'number'},
                    'statistics': {
                        'type': 'object',
                        'properties': {
                            'high_count': {'type': 'integer'},
                            'low_count': {'type': 'integer'},
                            'threshold': {'type': 'number'},
                            'total_points': {'type': 'integer'}
                        }
                    }
                }
            }
        }
    )
    def post(self, request):
        """推断检测类型"""
        serializer = CheckTypeInferenceSerializer(data=request.data)
        if serializer.is_valid():
            points_data = serializer.validated_data['points_data']
            threshold = serializer.validated_data['threshold']

            # 统计高于和低于阈值的点位数量
            high_count = 0
            low_count = 0
            valid_values = []

            for point_name, value in points_data.items():
                try:
                    float_value = float(value)
                    valid_values.append(float_value)
                    if float_value > threshold:
                        high_count += 1
                    else:
                        low_count += 1
                except (ValueError, TypeError):
                    continue

            # 推断检测类型
            if high_count > low_count:
                inferred_type = 'initial'
                confidence = high_count / (high_count + low_count) if (high_count + low_count) > 0 else 0
            elif low_count > high_count:
                inferred_type = 'recheck'
                confidence = low_count / (high_count + low_count) if (high_count + low_count) > 0 else 0
            else:
                inferred_type = 'initial'  # 默认初检
                confidence = 0.5

            return Response({
                'inferred_type': inferred_type,
                'confidence': round(confidence, 3),
                'statistics': {
                    'high_count': high_count,
                    'low_count': low_count,
                    'threshold': threshold,
                    'total_points': len(valid_values)
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PointValueViewSet(viewsets.ModelViewSet):
    """点位值记录管理视图集"""
    queryset = PointValue.objects.all()
    serializer_class = PointValueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """获取点位值记录"""
        queryset = PointValue.objects.all()

        # 支持按OCR结果过滤
        ocr_result_id = self.request.query_params.get('ocr_result_id')
        if ocr_result_id:
            try:
                queryset = queryset.filter(ocr_result_id=int(ocr_result_id))
            except ValueError:
                pass

        # 支持按点位名称过滤
        point_name = self.request.query_params.get('point_name')
        if point_name:
            queryset = queryset.filter(point_name__icontains=point_name)

        # 支持按检测类型过滤
        check_type = self.request.query_params.get('check_type')
        if check_type:
            queryset = queryset.filter(check_type=check_type)

        return queryset.select_related('ocr_result').order_by('-created_at')


class DataSyncAPIView(APIView):
    """数据同步API"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="从GUI数据同步",
        description="从GUI版本的数据文件同步点位学习数据",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'synced_from_json': {'type': 'integer'},
                    'synced_from_txt': {'type': 'integer'},
                    'total_synced': {'type': 'integer'},
                    'errors': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        }
    )
    def post(self, request):
        """同步GUI数据"""
        from .data_sync_service import get_data_sync_service

        sync_service = get_data_sync_service()
        result = sync_service.sync_from_gui_data()

        return Response(result)

    @extend_schema(
        summary="导出为GUI格式",
        description="导出数据为GUI版本兼容的格式",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'exported_json': {'type': 'boolean'},
                    'exported_txt': {'type': 'boolean'},
                    'point_count': {'type': 'integer'},
                    'errors': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        }
    )
    def put(self, request):
        """导出为GUI格式"""
        from .data_sync_service import get_data_sync_service

        sync_service = get_data_sync_service()
        result = sync_service.export_to_gui_format()

        return Response(result)

    @extend_schema(
        summary="获取同步状态",
        description="获取数据同步状态信息",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'database_points': {'type': 'integer'},
                    'database_values': {'type': 'integer'},
                    'json_file_exists': {'type': 'boolean'},
                    'txt_file_exists': {'type': 'boolean'},
                    'last_sync_time': {'type': 'string'}
                }
            }
        }
    )
    def get(self, request):
        """获取同步状态"""
        from .data_sync_service import get_data_sync_service

        sync_service = get_data_sync_service()
        status = sync_service.get_sync_status()

        return Response(status)
