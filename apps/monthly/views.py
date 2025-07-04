"""
月度报表视图
"""
import os
import logging
from django.http import HttpResponse
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.types import OpenApiTypes
from .models import MonthlyReport, MonthlyReportConfig
from .serializers import (
    MonthlyReportSerializer,
    MonthlyReportDetailSerializer,
    MonthlyReportCreateSerializer,
    MonthlyReportGenerateSerializer,
    MonthlyReportStatsSerializer,
    MonthlyReportConfigSerializer
)
from apps.files.models import UploadedFile


class MonthlyReportConfigViewSet(viewsets.ModelViewSet):
    """月度报表配置管理视图集"""
    queryset = MonthlyReportConfig.objects.all()
    serializer_class = MonthlyReportConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """返回配置列表"""
        queryset = MonthlyReportConfig.objects.all()

        # 管理员可以看到所有配置，普通用户只能看到公共配置和自己的配置
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                models.Q(created_by__isnull=True) | models.Q(created_by=self.request.user)
            )

        return queryset.order_by('-is_default', 'name')

    def perform_create(self, serializer):
        """创建配置时设置创建者"""
        serializer.save(created_by=self.request.user)


class MonthlyReportViewSet(viewsets.ModelViewSet):
    """月度报表管理视图集"""
    queryset = MonthlyReport.objects.all()
    serializer_class = MonthlyReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的月度报表"""
        queryset = MonthlyReport.objects.filter(created_by=self.request.user)

        # 支持按月份过滤
        month = self.request.query_params.get('month')
        if month:
            try:
                year, month_num = month.split('-')
                queryset = queryset.filter(
                    report_month__year=int(year),
                    report_month__month=int(month_num)
                )
            except (ValueError, TypeError):
                pass

        # 支持按生成状态过滤
        is_generated = self.request.query_params.get('is_generated')
        if is_generated is not None:
            queryset = queryset.filter(is_generated=is_generated.lower() == 'true')

        return queryset.select_related('csv_file', 'log_file').order_by('-report_month', '-created_at')

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'retrieve':
            return MonthlyReportDetailSerializer
        return MonthlyReportSerializer

    def perform_create(self, serializer):
        """创建报表时设置创建者"""
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="生成月度报表",
        description="生成指定月度报表的Excel和PDF文件",
        request=MonthlyReportGenerateSerializer,
        responses={202: {'description': '生成已开始'}}
    )
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """生成月度报表"""
        monthly_report = self.get_object()
        serializer = MonthlyReportGenerateSerializer(data=request.data)

        if serializer.is_valid():
            force_regenerate = serializer.validated_data.get('force_regenerate', False)
            generate_pdf = serializer.validated_data.get('generate_pdf', True)
            config_id = serializer.validated_data.get('config_id')

            # 检查是否已生成且不强制重新生成
            if monthly_report.is_generated and not force_regenerate:
                return Response({
                    'error': '报表已生成，如需重新生成请设置force_regenerate=true'
                }, status=status.HTTP_409_CONFLICT)

            # TODO: 调用异步月度报表生成任务
            # task = generate_monthly_report.delay(
            #     monthly_report.id,
            #     request.user.id,
            #     config_id,
            #     generate_pdf
            # )

            # 更新报表状态
            monthly_report.is_generated = False
            if config_id:
                monthly_report.config_data = {
                    **monthly_report.config_data,
                    'config_id': config_id,
                    'generate_pdf': generate_pdf
                }
            monthly_report.save()

            return Response({
                'message': '月度报表生成已开始',
                'report_id': monthly_report.id,
                # 'task_id': task.id,
                'status': 'generating'
            }, status=status.HTTP_202_ACCEPTED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="下载Excel文件",
        description="下载月度报表的Excel文件",
        responses={200: OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=['get'])
    def download_excel(self, request, pk=None):
        """下载Excel文件"""
        monthly_report = self.get_object()

        if not monthly_report.excel_file or not os.path.exists(monthly_report.excel_file.path):
            return Response({
                'error': 'Excel文件不存在，请先生成报表'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(monthly_report.excel_file.path, 'rb') as f:
                file_data = f.read()

            response = HttpResponse(
                file_data,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f"{monthly_report.title}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_data)

            return response

        except Exception as e:
            return Response({
                'error': f'下载失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="下载PDF文件",
        description="下载月度报表的PDF文件",
        responses={200: OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """下载PDF文件"""
        monthly_report = self.get_object()

        if not monthly_report.pdf_file or not os.path.exists(monthly_report.pdf_file.path):
            return Response({
                'error': 'PDF文件不存在，请先生成报表'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(monthly_report.pdf_file.path, 'rb') as f:
                file_data = f.read()

            response = HttpResponse(file_data, content_type='application/pdf')
            filename = f"{monthly_report.title}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_data)

            return response

        except Exception as e:
            return Response({
                'error': f'下载失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateMonthlyReportView(APIView):
    """创建月度报表视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="创建月度报表",
        description="基于CSV和日志文件创建月度报表",
        request=MonthlyReportCreateSerializer,
        responses={201: MonthlyReportSerializer}
    )
    def post(self, request):
        """创建月度报表"""
        serializer = MonthlyReportCreateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # 获取文件
                    csv_file = UploadedFile.objects.get(
                        id=serializer.validated_data['csv_file_id'],
                        created_by=request.user
                    )

                    log_file = None
                    if serializer.validated_data.get('log_file_id'):
                        log_file = UploadedFile.objects.get(
                            id=serializer.validated_data['log_file_id'],
                            created_by=request.user
                        )

                    # 准备配置数据
                    config_data = {
                        'uniform_profit_rate': serializer.validated_data.get('uniform_profit_rate', False),
                        'profit_rate_value': serializer.validated_data.get('profit_rate_value', 0.05),
                        'medicine_cost_per_order': serializer.validated_data.get('medicine_cost_per_order', 120.1),
                        'cma_cost_per_point': serializer.validated_data.get('cma_cost_per_point', 60.0),
                        'include_address_matching': serializer.validated_data.get('include_address_matching', True),
                        'exclude_recheck_records': serializer.validated_data.get('exclude_recheck_records', True),
                        'date_range_days': serializer.validated_data.get('date_range_days', 30),
                        'config_id': serializer.validated_data.get('config_id')
                    }

                    # 创建月度报表
                    monthly_report = MonthlyReport.objects.create(
                        title=serializer.validated_data['title'],
                        report_month=serializer.validated_data['report_month'],
                        csv_file=csv_file,
                        log_file=log_file,
                        config_data=config_data,
                        created_by=request.user
                    )

                # 返回创建的报表
                response_serializer = MonthlyReportSerializer(monthly_report)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except UploadedFile.DoesNotExist:
                return Response({
                    'error': '文件不存在或无权限访问'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({
                    'error': f'创建月度报表失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MonthlyReportStatsView(APIView):
    """月度报表统计视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取月度报表统计信息",
        description="获取当前用户的月度报表统计信息",
        responses={200: MonthlyReportStatsSerializer}
    )
    def get(self, request):
        """获取月度报表统计信息"""
        queryset = MonthlyReport.objects.filter(created_by=request.user)

        # 基本统计
        total_reports = queryset.count()
        generated_reports = queryset.filter(is_generated=True).count()
        pending_reports = total_reports - generated_reports

        # 按月份统计
        reports_by_month = {}
        for report in queryset:
            month_key = report.report_month.strftime('%Y-%m')
            if month_key not in reports_by_month:
                reports_by_month[month_key] = 0
            reports_by_month[month_key] += 1

        # 订单和收入统计
        total_orders_processed = 0
        total_revenue = 0.0

        for report in queryset.filter(is_generated=True):
            if report.summary_data:
                total_orders_processed += report.summary_data.get('total_orders', 0)
                total_revenue += report.summary_data.get('total_revenue', 0.0)

        # 平均生成时间
        generated_reports_with_time = queryset.filter(
            is_generated=True,
            created_at__isnull=False,
            generation_completed_at__isnull=False
        )

        if generated_reports_with_time.exists():
            total_generation_time = sum(
                (report.generation_completed_at - report.created_at).total_seconds()
                for report in generated_reports_with_time
            )
            average_generation_time = total_generation_time / generated_reports_with_time.count()
        else:
            average_generation_time = 0.0

        # 最近的报表
        recent_reports = queryset.select_related('csv_file', 'log_file').order_by('-created_at')[:5]

        stats_data = {
            'total_reports': total_reports,
            'generated_reports': generated_reports,
            'pending_reports': pending_reports,
            'reports_by_month': reports_by_month,
            'total_orders_processed': total_orders_processed,
            'total_revenue': total_revenue,
            'average_generation_time': average_generation_time,
            'recent_reports': recent_reports
        }

        serializer = MonthlyReportStatsSerializer(stats_data)
        return Response(serializer.data)


logger = logging.getLogger(__name__)


class LaborCostFileUploadView(APIView):
    """人工成本文件上传视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="上传人工成本文件",
        description="上传txt格式的人工成本文件，用于月度报表生成",
        request=inline_serializer(
            name='LaborCostFileUploadRequest',
            fields={
                'file': serializers.FileField(help_text='人工成本文件(txt格式)'),
                'month': serializers.IntegerField(help_text='月份'),
            }
        ),
        responses={200: {'description': '文件上传成功'}}
    )
    def post(self, request):
        """上传人工成本文件"""
        try:
            uploaded_file = request.FILES.get('file')
            month = request.data.get('month')

            if not uploaded_file:
                return Response(
                    {'error': '请选择要上传的文件'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not month:
                return Response(
                    {'error': '请指定月份'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 验证文件格式
            if not uploaded_file.name.endswith('.txt'):
                return Response(
                    {'error': '人工成本文件必须是txt格式'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 保存文件到人工成本目录
            from .services import MonthlyReportService
            report_service = MonthlyReportService()

            # 构造文件名
            filename = f"{month}月人工.txt"
            file_path = report_service.labor_cost_dir / filename

            # 保存文件
            with open(file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            logger.info(f"人工成本文件已保存: {file_path}")

            # 验证文件内容
            try:
                labor_costs = report_service.parse_labor_cost_file(str(file_path))
                total_cost = sum(labor_costs.values())

                return Response({
                    'success': True,
                    'message': '人工成本文件上传成功',
                    'file_path': str(file_path),
                    'parsed_data': {
                        'total_records': len(labor_costs),
                        'total_cost': total_cost,
                        'dates': list(labor_costs.keys())
                    }
                })
            except Exception as parse_error:
                # 如果解析失败，删除文件
                if file_path.exists():
                    file_path.unlink()
                return Response(
                    {'error': f'文件格式错误，解析失败: {str(parse_error)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"人工成本文件上传失败: {e}")
            return Response(
                {'error': f'上传失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateMonthlyReportFromDBView(APIView):
    """基于数据库订单记录生成月度报表"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="基于数据库生成月度报表",
        description="从数据库订单记录生成月度报表，不依赖CSV文件",
        request=inline_serializer(
            name='GenerateFromDBRequest',
            fields={
                'year': serializers.IntegerField(help_text='年份'),
                'month': serializers.IntegerField(help_text='月份'),
                'title': serializers.CharField(help_text='报表标题', required=False),
                'config_data': serializers.JSONField(help_text='配置数据', required=False),
                'labor_cost_file': serializers.FileField(help_text='人工成本文件(txt格式)', required=False),
            }
        ),
        responses={200: {'description': '报表生成成功'}}
    )
    def post(self, request):
        """生成基于数据库的月度报表"""
        try:
            year = request.data.get('year')
            month = request.data.get('month')

            # 确保年份和月份是整数类型
            try:
                year = int(year) if year else None
                month = int(month) if month else None
            except (ValueError, TypeError):
                return Response(
                    {'error': '年份和月份必须是有效的数字'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            title = request.data.get('title', f'{year}年{month}月订单报表')
            config_data = request.data.get('config_data', {})
            labor_cost_file = request.FILES.get('labor_cost_file')

            # 处理config_data，确保它是字典类型
            if isinstance(config_data, str):
                try:
                    import json
                    config_data = json.loads(config_data)
                except (json.JSONDecodeError, ValueError):
                    config_data = {}
            elif config_data is None:
                config_data = {}

            if not year or not month:
                return Response(
                    {'error': '年份和月份不能为空'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 处理人工成本文件
            labor_cost_file_path = None
            if labor_cost_file:
                # 验证文件格式
                if not labor_cost_file.name.endswith('.txt'):
                    return Response(
                        {'error': '人工成本文件必须是txt格式'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 保存上传的人工成本文件
                from pathlib import Path
                import tempfile

                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w+b', suffix='.txt', delete=False) as temp_file:
                    for chunk in labor_cost_file.chunks():
                        temp_file.write(chunk)
                    labor_cost_file_path = temp_file.name

                logger.info(f"人工成本文件已保存到: {labor_cost_file_path}")

            # 创建月度报表服务
            from .services import MonthlyReportService
            report_service = MonthlyReportService()

            # 生成报表
            excel_content, summary_data = report_service.generate_monthly_report_from_db(
                year, month, request.user.id, config_data, labor_cost_file_path
            )

            # 创建报表记录（不依赖CSV文件）
            from datetime import date
            report_month = date(year, month, 1)

            # 保存Excel文件
            from django.core.files.base import ContentFile
            import time

            excel_filename = f"monthly_report_db_{year}_{month}_{int(time.time())}.xlsx"
            excel_file = ContentFile(excel_content, name=excel_filename)

            # 调试：检查summary_data的结构
            import json
            try:
                json.dumps(summary_data)
                logger.info("summary_data JSON序列化成功")
            except Exception as json_error:
                logger.error(f"summary_data JSON序列化失败: {json_error}")
                logger.error(f"summary_data内容: {summary_data}")
                # 清理summary_data，移除不能序列化的内容
                summary_data = {
                    'total_orders': summary_data.get('total_orders', 0),
                    'total_revenue': summary_data.get('total_revenue', 0),
                    'total_profit_amount': summary_data.get('total_profit_amount', 0),
                    'product_type_stats': {}
                }

            # 创建月度报表记录
            monthly_report = MonthlyReport.objects.create(
                title=title,
                report_month=report_month,
                csv_file=None,  # 基于数据库，不需要CSV文件
                config_data=config_data,
                summary_data=summary_data,
                is_generated=True,
                generation_completed_at=timezone.now(),
                created_by=request.user
            )

            # 保存Excel文件
            monthly_report.excel_file.save(excel_filename, excel_file, save=True)

            # 序列化返回结果
            serializer = MonthlyReportSerializer(monthly_report)

            # 清理临时文件
            if labor_cost_file_path and os.path.exists(labor_cost_file_path):
                try:
                    os.unlink(labor_cost_file_path)
                    logger.info(f"临时人工成本文件已清理: {labor_cost_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"清理临时文件失败: {cleanup_error}")

            return Response({
                'success': True,
                'message': '月度报表生成成功',
                'report': serializer.data
            })

        except ValueError as e:
            # 清理临时文件
            if 'labor_cost_file_path' in locals() and labor_cost_file_path and os.path.exists(labor_cost_file_path):
                try:
                    os.unlink(labor_cost_file_path)
                except Exception:
                    pass
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 清理临时文件
            if 'labor_cost_file_path' in locals() and labor_cost_file_path and os.path.exists(labor_cost_file_path):
                try:
                    os.unlink(labor_cost_file_path)
                except Exception:
                    pass
            logger.error(f"生成月度报表失败: {e}")
            return Response(
                {'error': f'生成失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
