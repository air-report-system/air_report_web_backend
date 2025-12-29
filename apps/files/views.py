"""
文件管理视图
"""
import os
import mimetypes
from django.db import transaction
from django.http import Http404, HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import UploadedFile
from .serializers import (
    UploadedFileSerializer,
    FileUploadSerializer,
    BulkFileUploadSerializer
)


def _infer_file_type_from_mime(mime_type: str) -> str:
    """根据MIME类型推断文件类型（与 UploadedFileSerializer.create 保持一致）"""
    if not mime_type:
        return 'other'
    if mime_type.startswith('image/'):
        return 'image'
    if mime_type in [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]:
        return 'document'
    if mime_type in [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
    ]:
        return 'spreadsheet'
    if mime_type == 'text/plain':
        return 'text'
    return 'other'


class UploadedFileViewSet(viewsets.ModelViewSet):
    """上传文件管理视图集"""
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户上传的文件"""
        queryset = UploadedFile.objects.filter(created_by=self.request.user)

        # 支持按文件类型过滤
        file_type = self.request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        # 支持按处理状态过滤
        is_processed = self.request.query_params.get('is_processed')
        if is_processed is not None:
            queryset = queryset.filter(is_processed=is_processed.lower() == 'true')

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """创建文件时设置创建者"""
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="下载文件",
        description="下载指定的文件",
        responses={200: OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """下载文件"""
        try:
            file_obj = self.get_object()

            if not file_obj.file or not os.path.exists(file_obj.file.path):
                return Response(
                    {'error': '文件不存在'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 读取文件内容
            with open(file_obj.file.path, 'rb') as f:
                file_data = f.read()

            # 设置响应头
            response = HttpResponse(
                file_data,
                content_type=file_obj.mime_type or 'application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{file_obj.original_name}"'
            response['Content-Length'] = len(file_data)

            return response

        except Exception as e:
            return Response(
                {'error': f'下载文件失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileUploadView(APIView):
    """文件上传视图"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="上传单个文件",
        description="上传单个文件到服务器",
        request=FileUploadSerializer,
        responses={201: UploadedFileSerializer}
    )
    def post(self, request):
        """上传单个文件"""
        serializer = FileUploadSerializer(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']
            description = serializer.validated_data.get('description', '')

            try:
                # 推断 MIME / file_type（前端上传的 CSV 在后续月度报表接口会校验 file_type=spreadsheet）
                mime_type = getattr(file, 'content_type', None) or mimetypes.guess_type(getattr(file, 'name', '') or '')[0] or 'application/octet-stream'
                file_type = _infer_file_type_from_mime(mime_type)

                # 创建文件记录
                uploaded_file = UploadedFile.objects.create(
                    file=file,
                    original_name=file.name,
                    mime_type=mime_type,
                    file_type=file_type,
                    created_by=request.user
                )

                # 返回创建的文件信息
                response_serializer = UploadedFileSerializer(uploaded_file)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {'error': f'文件上传失败: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkFileUploadView(APIView):
    """批量文件上传视图"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="批量上传文件",
        description="批量上传多个文件到服务器",
        request=BulkFileUploadSerializer,
        responses={201: UploadedFileSerializer(many=True)}
    )
    def post(self, request):
        """批量上传文件"""
        serializer = BulkFileUploadSerializer(data=request.data)

        if serializer.is_valid():
            files = serializer.validated_data['files']
            description = serializer.validated_data.get('description', '')

            uploaded_files = []
            failed_files = []

            # 使用事务确保数据一致性
            try:
                with transaction.atomic():
                    for file in files:
                        try:
                            mime_type = getattr(file, 'content_type', None) or mimetypes.guess_type(getattr(file, 'name', '') or '')[0] or 'application/octet-stream'
                            file_type = _infer_file_type_from_mime(mime_type)

                            # 创建文件记录
                            uploaded_file = UploadedFile.objects.create(
                                file=file,
                                original_name=file.name,
                                mime_type=mime_type,
                                file_type=file_type,
                                created_by=request.user
                            )
                            uploaded_files.append(uploaded_file)

                        except Exception as e:
                            failed_files.append({
                                'filename': file.name,
                                'error': str(e)
                            })

                # 返回结果
                response_data = {
                    'uploaded_files': UploadedFileSerializer(uploaded_files, many=True).data,
                    'success_count': len(uploaded_files),
                    'failed_count': len(failed_files),
                    'failed_files': failed_files
                }

                if failed_files:
                    return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
                else:
                    return Response(response_data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response(
                    {'error': f'批量上传失败: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileStatsView(APIView):
    """文件统计视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取文件统计信息",
        description="获取当前用户的文件统计信息",
        responses={200: {
            'type': 'object',
            'properties': {
                'total_files': {'type': 'integer'},
                'total_size': {'type': 'integer'},
                'file_types': {'type': 'object'},
                'processed_files': {'type': 'integer'},
                'unprocessed_files': {'type': 'integer'}
            }
        }}
    )
    def get(self, request):
        """获取文件统计信息"""
        queryset = UploadedFile.objects.filter(created_by=request.user)

        # 基本统计
        total_files = queryset.count()
        total_size = sum(f.file_size for f in queryset)
        processed_files = queryset.filter(is_processed=True).count()
        unprocessed_files = total_files - processed_files

        # 按文件类型统计
        file_types = {}
        for file_type in queryset.values_list('file_type', flat=True).distinct():
            count = queryset.filter(file_type=file_type).count()
            file_types[file_type] = count

        return Response({
            'total_files': total_files,
            'total_size': total_size,
            'file_types': file_types,
            'processed_files': processed_files,
            'unprocessed_files': unprocessed_files
        })
