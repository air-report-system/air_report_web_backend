"""
批量处理视图
"""
from django.db import transaction
from django.utils import timezone
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from .models import BatchJob, BatchFileItem
from .serializers import (
    BatchJobSerializer,
    BatchJobCreateSerializer,
    BatchJobUpdateSerializer,
    BatchJobStartSerializer,
    BatchJobStatsSerializer,
    BulkFileUploadAndBatchSerializer,
    BatchFileItemSerializer
)
from apps.files.models import UploadedFile


class BatchJobViewSet(viewsets.ModelViewSet):
    """批量任务管理视图集"""
    queryset = BatchJob.objects.all()
    serializer_class = BatchJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的批量任务"""
        queryset = BatchJob.objects.filter(created_by=self.request.user)

        # 支持按状态过滤
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.prefetch_related('batchfileitem_set__file').order_by('-created_at')

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action in ['update', 'partial_update']:
            return BatchJobUpdateSerializer
        return BatchJobSerializer

    def perform_create(self, serializer):
        """创建批量任务时设置创建者"""
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="启动批量任务",
        description="启动指定的批量处理任务",
        request=BatchJobStartSerializer,
        responses={202: {'description': '任务已启动'}}
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动批量任务"""
        batch_job = self.get_object()
        serializer = BatchJobStartSerializer(data=request.data)

        if serializer.is_valid():
            force_restart = serializer.validated_data.get('force_restart', False)

            # 检查任务状态
            if batch_job.status == 'running':
                return Response({
                    'error': '任务正在运行中'
                }, status=status.HTTP_409_CONFLICT)

            if batch_job.status == 'completed' and not force_restart:
                return Response({
                    'error': '任务已完成，如需重新运行请设置force_restart=true'
                }, status=status.HTTP_409_CONFLICT)

            # 如果强制重启，重置任务状态
            if force_restart:
                batch_job.status = 'created'
                batch_job.processed_files = 0
                batch_job.failed_files = 0
                batch_job.started_at = None
                batch_job.completed_at = None
                batch_job.estimated_completion = None

                # 重置文件项状态
                BatchFileItem.objects.filter(batch_job=batch_job).update(
                    status='pending',
                    error_message='',
                    processing_time_seconds=None,
                    ocr_result=None
                )

            # TODO: 调用异步批量处理任务
            # task = start_batch_processing.delay(batch_job.id)

            # 更新任务状态
            batch_job.status = 'running'
            batch_job.save()

            return Response({
                'message': '批量任务已启动',
                'batch_job_id': batch_job.id,
                # 'task_id': task.id,
                'status': 'running'
            }, status=status.HTTP_202_ACCEPTED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="取消批量任务",
        description="取消正在运行的批量处理任务",
        responses={200: {'description': '任务已取消'}}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消批量任务"""
        batch_job = self.get_object()

        if batch_job.status != 'running':
            return Response({
                'error': '只能取消正在运行的任务'
            }, status=status.HTTP_409_CONFLICT)

        # TODO: 发送取消信号到Celery任务
        # cancel_batch_processing.delay(batch_job.id)

        # 更新任务状态
        batch_job.status = 'cancelled'
        batch_job.completed_at = timezone.now()
        batch_job.save()

        return Response({
            'message': '批量任务已取消',
            'batch_job_id': batch_job.id,
            'status': 'cancelled'
        })

    @extend_schema(
        summary="获取任务进度",
        description="获取批量任务的详细进度信息",
        responses={200: BatchJobSerializer}
    )
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """获取任务进度"""
        batch_job = self.get_object()
        serializer = BatchJobSerializer(batch_job)
        return Response(serializer.data)

    @extend_schema(
        summary="重试失败的文件",
        description="重新处理批量任务中失败的文件",
        responses={202: {'description': '重试已开始'}}
    )
    @action(detail=True, methods=['post'])
    def retry_failed(self, request, pk=None):
        """重试失败的文件"""
        batch_job = self.get_object()

        # 获取失败的文件项
        failed_items = BatchFileItem.objects.filter(
            batch_job=batch_job,
            status='failed'
        )

        if not failed_items.exists():
            return Response({
                'error': '没有失败的文件需要重试'
            }, status=status.HTTP_404_NOT_FOUND)

        # 重置失败文件的状态
        failed_items.update(
            status='pending',
            error_message='',
            processing_time_seconds=None
        )

        # 更新批量任务状态
        batch_job.failed_files = 0
        batch_job.status = 'running'
        batch_job.save()

        # TODO: 调用异步重试任务
        # task = retry_failed_items.delay(batch_job.id)

        return Response({
            'message': f'开始重试 {failed_items.count()} 个失败的文件',
            'batch_job_id': batch_job.id,
            'retry_count': failed_items.count(),
            # 'task_id': task.id,
            'status': 'running'
        }, status=status.HTTP_202_ACCEPTED)


class CreateBatchJobView(APIView):
    """创建批量任务视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="创建批量任务",
        description="基于文件ID列表创建批量处理任务",
        request=BatchJobCreateSerializer,
        responses={201: BatchJobSerializer}
    )
    def post(self, request):
        """创建批量任务"""
        serializer = BatchJobCreateSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # 获取文件列表
                    file_ids = serializer.validated_data['file_ids']
                    files = UploadedFile.objects.filter(
                        id__in=file_ids,
                        created_by=request.user
                    ).order_by('id')

                    # 创建批量任务
                    batch_job = BatchJob.objects.create(
                        name=serializer.validated_data['name'],
                        total_files=len(file_ids),
                        settings={
                            'use_multi_ocr': serializer.validated_data.get('use_multi_ocr', False),
                            'ocr_count': serializer.validated_data.get('ocr_count', 3)
                        },
                        created_by=request.user
                    )

                    # 创建文件项
                    file_items = []
                    for order, file_obj in enumerate(files):
                        file_items.append(BatchFileItem(
                            batch_job=batch_job,
                            file=file_obj,
                            processing_order=order,
                            created_by=request.user
                        ))

                    BatchFileItem.objects.bulk_create(file_items)

                    # 如果设置了自动开始，启动任务
                    auto_start = serializer.validated_data.get('auto_start', False)
                    if auto_start:
                        # TODO: 调用异步批量处理任务
                        # task = start_batch_processing.delay(batch_job.id)
                        batch_job.status = 'running'
                        batch_job.save()

                # 返回创建的批量任务
                response_serializer = BatchJobSerializer(batch_job)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response({
                    'error': f'创建批量任务失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkFileUploadAndBatchView(APIView):
    """批量文件上传并创建批量任务视图"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def dispatch(self, request, *args, **kwargs):
        """重写dispatch方法来确保我们能看到所有请求"""
        print(f"=== BulkFileUploadAndBatchView 收到 {request.method} 请求 ===")
        print(f"用户: {request.user}")
        print(f"路径: {request.path}")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """测试GET请求"""
        print("收到GET请求")
        return Response({"message": "批量上传视图正常工作"})

    @extend_schema(
        summary="批量上传文件并创建批量任务",
        description="批量上传图片文件并自动创建批量处理任务",
        request=BulkFileUploadAndBatchSerializer,
        responses={201: BatchJobSerializer}
    )
    def post(self, request):
        """批量上传文件并创建批量任务"""
        print("=== 批量上传POST请求开始 ===")
        print(f"收到批量上传请求，用户: {request.user}")
        print(f"请求数据键: {list(request.data.keys())}")
        print(f"Content-Type: {request.content_type}")
        serializer = BulkFileUploadAndBatchSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # 获取上传的文件
                files = serializer.validated_data['files']
                batch_name = serializer.validated_data['batch_name']
                use_multi_ocr = serializer.validated_data.get('use_multi_ocr', False)
                ocr_count = serializer.validated_data.get('ocr_count', 3)
                auto_start = serializer.validated_data.get('auto_start', True)

                # 先上传文件，处理重复文件（在事务外处理）
                uploaded_files = []
                print(f"开始处理 {len(files)} 个文件")

                for file in files:
                    print(f"处理文件: {file.name}, 大小: {file.size}")

                    # 计算文件哈希值
                    import hashlib
                    import time
                    file.seek(0)
                    hash_md5 = hashlib.md5()
                    for chunk in file.chunks():
                        hash_md5.update(chunk)
                    file_hash = hash_md5.hexdigest()
                    file.seek(0)

                    print(f"文件哈希值: {file_hash}")

                    # 查找当前用户的现有文件
                    existing_file = UploadedFile.objects.filter(
                        hash_md5=file_hash,
                        created_by=request.user
                    ).first()

                    # 检查文件是否有效
                    if (existing_file and existing_file.file and
                        default_storage.exists(existing_file.file.name)):
                        # 如果找到当前用户的有效文件，直接复用
                        print(f"复用现有文件: {existing_file.id}")
                        uploaded_files.append(existing_file)
                    else:
                        # 如果当前用户存在记录但物理文件不存在，删除旧记录
                        if existing_file:
                            print(f"现有文件 {existing_file.id} 的物理文件不存在，删除旧记录")
                            try:
                                existing_file.delete()
                            except Exception as delete_error:
                                print(f"删除无效记录失败: {delete_error}")

                        # 检查是否有其他用户的相同哈希文件存在
                        other_existing_file = UploadedFile.objects.filter(
                            hash_md5=file_hash
                        ).exclude(created_by=request.user).first()

                        if other_existing_file:
                            # 如果其他用户有相同文件，为避免哈希冲突，我们重新计算哈希（加上用户ID和时间戳）
                            unique_hash = hashlib.md5(
                                f"{file_hash}_{request.user.id}_{int(time.time())}".encode()
                            ).hexdigest()
                            print(f"检测到哈希冲突，使用唯一哈希: {unique_hash}")

                            # 手动创建文件记录，避免自动哈希计算
                            try:
                                uploaded_file = UploadedFile(
                                    file=file,
                                    original_name=file.name,
                                    created_by=request.user,
                                    hash_md5=unique_hash,
                                    file_size=file.size,
                                    file_type=(file.content_type.split('/')[0]
                                              if file.content_type else 'unknown'),
                                    mime_type=file.content_type or 'application/octet-stream'
                                )
                                uploaded_file.save()
                                print(f"创建新文件(唯一哈希): {uploaded_file.id}")
                                uploaded_files.append(uploaded_file)
                            except Exception as e:
                                print(f"创建文件记录失败 {file.name}: {e}")
                                continue
                        else:
                            # 创建新文件记录
                            try:
                                uploaded_file = UploadedFile.objects.create(
                                    file=file,
                                    original_name=file.name,
                                    created_by=request.user
                                )
                                print(f"创建新文件: {uploaded_file.id}")
                                uploaded_files.append(uploaded_file)
                            except Exception as e:
                                # 如果仍然创建失败，记录错误并跳过该文件
                                print(f"创建文件记录失败 {file.name}: {e}")
                                continue

                print(f"成功处理 {len(uploaded_files)} 个文件")

                # 检查是否有文件成功上传
                if not uploaded_files:
                    return Response({
                        'error': '没有文件成功上传'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 在事务中创建批量任务
                with transaction.atomic():
                    # 创建批量任务
                    batch_job = BatchJob.objects.create(
                        name=batch_name,
                        total_files=len(uploaded_files),
                        settings={
                            'use_multi_ocr': use_multi_ocr,
                            'ocr_count': ocr_count
                        },
                        created_by=request.user
                    )

                    # 创建文件项
                    file_items = []
                    for order, uploaded_file in enumerate(uploaded_files):
                        file_items.append(BatchFileItem(
                            batch_job=batch_job,
                            file=uploaded_file,
                            processing_order=order,
                            created_by=request.user
                        ))

                    BatchFileItem.objects.bulk_create(file_items)

                    # 如果设置了自动开始，启动任务
                    if auto_start:
                        print(f"准备启动批量OCR处理，任务ID: {batch_job.id}")
                        # 启动批量OCR处理
                        from apps.batch.tasks import start_batch_ocr_processing
                        batch_job.status = 'running'
                        batch_job.save()

                        # 异步启动OCR处理
                        try:
                            print(f"调用start_batch_ocr_processing...")
                            start_batch_ocr_processing(batch_job.id)
                            print(f"批量OCR处理启动成功")
                        except Exception as e:
                            print(f"启动批量OCR处理失败: {e}")
                            import traceback
                            traceback.print_exc()
                            batch_job.status = 'failed'
                            batch_job.save()
                    else:
                        print(f"auto_start=False，不自动启动OCR处理")

                # 返回创建的批量任务
                response_serializer = BatchJobSerializer(batch_job)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response({
                    'error': f'批量上传和创建任务失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BatchStatsView(APIView):
    """批量任务统计视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取批量任务统计信息",
        description="获取当前用户的批量任务统计信息",
        responses={200: BatchJobStatsSerializer}
    )
    def get(self, request):
        """获取批量任务统计信息"""
        queryset = BatchJob.objects.filter(created_by=request.user)

        # 基本统计
        total_jobs = queryset.count()
        running_jobs = queryset.filter(status='running').count()
        completed_jobs = queryset.filter(status='completed').count()
        failed_jobs = queryset.filter(status='failed').count()

        # 文件处理统计
        total_files_processed = sum(job.processed_files for job in queryset)

        # 平均处理时间
        completed_jobs_with_duration = queryset.filter(
            status='completed',
            started_at__isnull=False,
            completed_at__isnull=False
        )

        if completed_jobs_with_duration.exists():
            total_duration = sum(
                (job.completed_at - job.started_at).total_seconds()
                for job in completed_jobs_with_duration
            )
            average_processing_time = total_duration / completed_jobs_with_duration.count()
        else:
            average_processing_time = 0.0

        # 最近的任务
        recent_jobs = queryset.order_by('-created_at')[:5]

        stats_data = {
            'total_jobs': total_jobs,
            'running_jobs': running_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'total_files_processed': total_files_processed,
            'average_processing_time': average_processing_time,
            'recent_jobs': recent_jobs
        }

        serializer = BatchJobStatsSerializer(stats_data)
        return Response(serializer.data)
