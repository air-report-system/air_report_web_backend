"""
报告管理视图
"""
import os
from django.http import HttpResponse, Http404
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import Report, ReportTemplate
from .serializers import (
    ReportSerializer,
    ReportTemplateSerializer,
    ReportCreateSerializer,
    ReportUpdateSerializer,
    ReportGenerateSerializer,
    ReportStatsSerializer
)
from apps.ocr.models import OCRResult


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """报告模板管理视图集"""
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """返回激活的模板"""
        queryset = ReportTemplate.objects.filter(is_active=True)

        # 管理员可以看到所有模板，普通用户只能看到公共模板
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by__isnull=True)

        return queryset.order_by('name')

    def perform_create(self, serializer):
        """创建模板时设置创建者"""
        serializer.save(created_by=self.request.user)


class ReportViewSet(viewsets.ModelViewSet):
    """报告管理视图集"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的报告"""
        queryset = Report.objects.filter(created_by=self.request.user)

        # 支持按报告类型过滤
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        # 支持按生成状态过滤
        is_generated = self.request.query_params.get('is_generated')
        if is_generated is not None:
            queryset = queryset.filter(is_generated=is_generated.lower() == 'true')

        # 支持搜索功能
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(form_data__contact_person__icontains=search) |
                Q(form_data__phone__icontains=search) |
                Q(form_data__project_address__icontains=search)
            )

        # 支持按创建时间筛选
        created_after = self.request.query_params.get('created_after')
        if created_after:
            from datetime import datetime
            try:
                date_obj = datetime.strptime(created_after, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_obj)
            except ValueError:
                pass  # 忽略无效日期格式

        created_before = self.request.query_params.get('created_before')
        if created_before:
            from datetime import datetime
            try:
                date_obj = datetime.strptime(created_before, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_obj)
            except ValueError:
                pass  # 忽略无效日期格式

        return queryset.select_related('ocr_result__file').order_by('-created_at')

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action in ['update', 'partial_update']:
            return ReportUpdateSerializer
        return ReportSerializer



    def perform_create(self, serializer):
        """创建报告时设置创建者"""
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="生成报告",
        description="生成指定报告的Word和PDF文件",
        request=ReportGenerateSerializer,
        responses={202: {'description': '生成已开始'}}
    )
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """生成报告"""
        report = self.get_object()
        serializer = ReportGenerateSerializer(data=request.data)

        if serializer.is_valid():
            force_regenerate = serializer.validated_data.get('force_regenerate', False)
            template_id = serializer.validated_data.get('template_id')

            # 检查是否已生成且不强制重新生成
            if report.is_generated and not force_regenerate:
                return Response({
                    'error': '报告已生成，如需重新生成请设置force_regenerate=true'
                }, status=status.HTTP_409_CONFLICT)

            # 更新报告状态
            report.is_generated = False
            report.error_message = ''
            if template_id:
                report.generation_settings = {
                    **report.generation_settings,
                    'template_id': template_id
                }
            report.save()

            # 尝试异步执行，如果失败则同步执行
            from .tasks import generate_report
            import logging

            logger = logging.getLogger(__name__)

            try:
                # 尝试异步执行
                task = generate_report.delay(
                    report.id,
                    request.user.id,
                    template_id
                )
                logger.info(f"异步任务已启动: {task.id}")

                return Response({
                    'message': '报告生成已开始（异步）',
                    'report_id': report.id,
                    'task_id': str(task.id),
                    'status': 'generating'
                }, status=status.HTTP_202_ACCEPTED)

            except Exception as e:
                # 异步执行失败，尝试同步执行
                logger.warning(f"异步执行失败，切换到同步执行: {e}")

                try:
                    # 同步执行任务
                    result = generate_report(
                        report.id,
                        request.user.id,
                        template_id
                    )
                    logger.info(f"同步执行成功: {result}")

                    return Response({
                        'message': '报告生成完成（同步）',
                        'report_id': report.id,
                        'status': 'completed',
                        'result': result
                    }, status=status.HTTP_200_OK)

                except Exception as sync_error:
                    # 同步执行也失败
                    logger.error(f"同步执行也失败: {sync_error}")
                    report.error_message = f"报告生成失败: {str(sync_error)}"
                    report.save()

                    return Response({
                        'error': f'报告生成失败: {str(sync_error)}',
                        'report_id': report.id,
                        'status': 'failed'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="下载Word文件",
        description="下载报告的Word文件",
        responses={200: OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=['get'])
    def download_docx(self, request, pk=None):
        """下载Word文件"""
        report = self.get_object()

        if not report.docx_file or not os.path.exists(report.docx_file.path):
            return Response({
                'error': 'Word文件不存在，请先生成报告'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(report.docx_file.path, 'rb') as f:
                file_data = f.read()

            response = HttpResponse(
                file_data,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            filename = f"{report.title}.docx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_data)

            return response

        except Exception as e:
            return Response({
                'error': f'下载失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="下载PDF文件",
        description="下载报告的PDF文件",
        responses={200: OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """下载PDF文件"""
        report = self.get_object()

        if not report.pdf_file or not os.path.exists(report.pdf_file.path):
            return Response({
                'error': 'PDF文件不存在，请先生成报告'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(report.pdf_file.path, 'rb') as f:
                file_data = f.read()

            response = HttpResponse(file_data, content_type='application/pdf')
            filename = f"{report.title}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_data)

            return response

        except Exception as e:
            return Response({
                'error': f'下载失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="生成微信模板",
        description="生成微信通知模板内容",
        responses={200: {'description': '微信模板内容'}}
    )
    @action(detail=True, methods=['post'])
    def generate_wechat_template(self, request, pk=None):
        """生成微信模板 - 移植自GUI项目的微信模板功能"""
        report = self.get_object()

        # 获取模板类型
        template_type = request.data.get('template_type', 'standard')

        try:
            from .services import WeChatTemplateService

            # 准备报告数据
            report_data = {
                'contact_person': report.form_data.get('contact_person', ''),
                'project_address': report.form_data.get('project_address', ''),
                'phone': report.ocr_result.phone if report.ocr_result else '',
                'sampling_date': report.form_data.get('sampling_date', ''),
                'temperature': report.form_data.get('temperature', ''),
                'humidity': report.form_data.get('humidity', ''),
                'check_type_display': '初检' if report.form_data.get('check_type') == 'initial' else '复检',
                'points_data': []
            }

            # 转换点位数据格式
            if report.ocr_result and report.ocr_result.points_data:
                points_data = []
                for point_name, point_value in report.ocr_result.points_data.items():
                    points_data.append((point_name, str(point_value)))
                report_data['points_data'] = points_data

            # 创建微信模板服务
            wechat_service = WeChatTemplateService()

            # 生成模板内容
            template_content = wechat_service.generate_wechat_template(report_data, template_type)

            return Response({
                'status': 'success',
                'template_type': template_type,
                'template_content': template_content,
                'report_id': report.id,
                'character_count': len(template_content)
            })

        except Exception as e:
            return Response({
                'error': f'微信模板生成失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateReportView(APIView):
    """创建报告视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="创建新报告",
        description="基于OCR结果创建新报告",
        request=ReportCreateSerializer,
        responses={201: ReportSerializer}
    )
    def post(self, request):
        """创建新报告"""
        serializer = ReportCreateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # 获取OCR结果
                    ocr_result = OCRResult.objects.get(
                        id=serializer.validated_data['ocr_result_id'],
                        created_by=request.user
                    )

                    # 准备表单数据
                    form_data = {
                        'project_address': serializer.validated_data['project_address'],
                        'contact_person': serializer.validated_data['contact_person'],
                        'sampling_date': serializer.validated_data['sampling_date'],
                        'temperature': serializer.validated_data.get('temperature', ''),
                        'humidity': serializer.validated_data.get('humidity', ''),
                        'check_type': serializer.validated_data['check_type'],
                        'points_data': serializer.validated_data['points_data']
                    }

                    # 准备模板数据
                    template_data = {
                        'project_address': form_data['project_address'],
                        'contact_person': form_data['contact_person'],
                        'sampling_date': form_data['sampling_date'],
                        'temperature': form_data['temperature'],
                        'humidity': form_data['humidity'],
                        'check_type_display': '初检' if form_data['check_type'] == 'initial' else '复检',
                        'points': [
                            {'name': name, 'value': value}
                            for name, value in form_data['points_data'].items()
                        ]
                    }

                    # 创建报告
                    report = Report.objects.create(
                        ocr_result=ocr_result,
                        report_type=serializer.validated_data['report_type'],
                        title=serializer.validated_data['title'],
                        form_data=form_data,
                        template_data=template_data,
                        delete_original_docx=serializer.validated_data.get('delete_original_docx', True),
                        generation_settings={
                            'template_id': serializer.validated_data.get('template_id')
                        },
                        created_by=request.user
                    )

                # 返回创建的报告
                response_serializer = ReportSerializer(report)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except OCRResult.DoesNotExist:
                return Response({
                    'error': 'OCR结果不存在或无权限访问'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({
                    'error': f'创建报告失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportStatsView(APIView):
    """报告统计视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取报告统计信息",
        description="获取当前用户的报告统计信息",
        responses={200: ReportStatsSerializer}
    )
    def get(self, request):
        """获取报告统计信息"""
        queryset = Report.objects.filter(created_by=request.user)

        # 基本统计
        total_reports = queryset.count()
        generated_reports = queryset.filter(is_generated=True).count()
        pending_reports = queryset.filter(is_generated=False, error_message='').count()
        failed_reports = queryset.exclude(error_message='').count()

        # 按报告类型统计
        report_types = {}
        for report_type, display_name in Report.REPORT_TYPES:
            count = queryset.filter(report_type=report_type).count()
            report_types[display_name] = count

        # 最近的报告
        recent_reports = queryset.select_related('ocr_result__file').order_by('-created_at')[:5]

        stats_data = {
            'total_reports': total_reports,
            'generated_reports': generated_reports,
            'pending_reports': pending_reports,
            'failed_reports': failed_reports,
            'report_types': report_types,
            'recent_reports': recent_reports
        }

        serializer = ReportStatsSerializer(stats_data)
        return Response(serializer.data)
