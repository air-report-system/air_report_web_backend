"""
订单信息记录视图
"""
import csv
import io
import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .services import OrderInfoProcessor
from .serializers import (
    OrderInfoInputSerializer, OrderInfoOutputSerializer,
    OrderRecordSerializer, OrderUpdateSerializer, OrderSubmitSerializer
)
from apps.ocr.models import CSVRecord

logger = logging.getLogger(__name__)


class ProcessOrderInfoView(APIView):
    """处理订单信息视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """处理订单信息并返回格式化结果"""
        serializer = OrderInfoInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_text = serializer.validated_data['order_text']
        
        try:
            # 使用订单信息处理器格式化文本
            processor = OrderInfoProcessor()
            formatted_csv = processor.format_order_message(order_text)
            
            # 解析CSV为订单数据
            parse_result = processor.parse_csv_to_order_data(formatted_csv)

            # 检查重复记录
            duplicate_result = processor.check_for_duplicates(parse_result["order_data"])

            response_data = {
                "formatted_csv": formatted_csv,
                "order_data": parse_result["order_data"],
                "validation_errors": parse_result["validation_errors"],
                "csv_content": parse_result.get("csv_content", formatted_csv),
                "duplicate_check": duplicate_result
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"处理订单信息失败: {e}")
            return Response(
                {"error": f"处理失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProcessMultipleOrdersView(APIView):
    """处理多个订单信息视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """处理多个订单信息并返回格式化结果"""
        serializer = OrderInfoInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_text = serializer.validated_data['order_text']
        
        try:
            # 使用订单信息处理器格式化多个订单
            processor = OrderInfoProcessor()
            
            # 增加超时处理和重试机制
            try:
                formatted_csv_lines = processor.format_multiple_orders(order_text)
            except TimeoutError as timeout_error:
                logger.warning(f"AI处理超时，尝试本地处理: {timeout_error}")
                # 超时情况下，尝试本地处理
                formatted_csv_lines = [processor._local_format_order_message(order_text)]
            
            # 解析多个CSV为订单数据
            parse_result = processor.parse_multiple_csv_to_order_data(formatted_csv_lines)

            # 为每个订单检查重复记录
            for order_item in parse_result["order_data_list"]:
                try:
                    duplicate_result = processor.check_for_duplicates(order_item["order_data"])
                    order_item["duplicate_check"] = duplicate_result
                except Exception as dup_error:
                    logger.warning(f"重复检查失败: {dup_error}")
                    order_item["duplicate_check"] = {"is_duplicate": False, "match_details": [], "duplicate_count": 0}

            response_data = {
                "formatted_csv_lines": formatted_csv_lines,
                "order_data_list": parse_result["order_data_list"],
                "validation_errors": parse_result["validation_errors"],
                "total_orders": parse_result["total_orders"]
            }
            
            logger.info(f"批量处理完成，共处理 {parse_result['total_orders']} 个订单")
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"处理多个订单信息失败: {e}")
            return Response(
                {"error": f"处理失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateOrderDataView(APIView):
    """更新订单数据视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """更新订单数据并返回验证结果"""
        serializer = OrderUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_data = serializer.validated_data['order_data']
        
        try:
            # 验证订单数据
            processor = OrderInfoProcessor()
            validation_errors = processor._validate_order_data(order_data)
            
            return Response({
                "success": True,
                "validation_errors": validation_errors,
                "order_data": order_data
            })
            
        except Exception as e:
            logger.error(f"更新订单数据失败: {e}")
            return Response(
                {"error": f"更新失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubmitOrderView(APIView):
    """提交订单到数据库视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """提交订单数据到数据库"""
        serializer = OrderSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_data = serializer.validated_data['order_data']
        
        try:
            with transaction.atomic():
                # 转换数据格式以适配CSVRecord模型
                csv_data = self._convert_order_data_to_csv_record(order_data)
                csv_data['created_by'] = request.user
                
                # 创建CSV记录
                csv_record = CSVRecord.objects.create(**csv_data)
                
                # 序列化返回结果
                record_serializer = OrderRecordSerializer(csv_record)
                
                return Response({
                    "success": True,
                    "message": "订单信息保存成功",
                    "record": record_serializer.data
                })
                
        except Exception as e:
            logger.error(f"提交订单失败: {e}")
            return Response(
                {"error": f"提交失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _convert_order_data_to_csv_record(self, order_data):
        """将订单数据转换为CSVRecord模型格式"""
        csv_data = {}
        
        # 直接映射字段
        field_mapping = {
            '客户姓名': '客户姓名',
            '客户电话': '客户电话',
            '客户地址': '客户地址',
            '商品类型': '商品类型',
            '面积': '面积',
            'CMA点位数量': 'CMA点位数量',
            '备注赠品': '备注赠品'
        }
        
        for order_field, csv_field in field_mapping.items():
            value = order_data.get(order_field, '').strip()
            csv_data[csv_field] = value if value else ''
        
        # 处理成交金额 - 转换为Decimal
        amount_str = order_data.get('成交金额', '').strip()
        if amount_str:
            try:
                csv_data['成交金额'] = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                csv_data['成交金额'] = None
        else:
            csv_data['成交金额'] = None
        
        # 处理履约时间 - 转换为日期
        date_str = order_data.get('履约时间', '').strip()
        if date_str:
            try:
                csv_data['履约时间'] = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                csv_data['履约时间'] = None
        else:
            csv_data['履约时间'] = None
        
        return csv_data


class SubmitMultipleOrdersView(APIView):
    """批量提交订单到数据库视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """批量提交订单数据到数据库"""
        order_data_list = request.data.get('order_data_list', [])
        
        if not order_data_list:
            return Response(
                {"error": "order_data_list字段不能为空"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success_records = []
        failed_records = []
        
        try:
            with transaction.atomic():
                for i, order_data in enumerate(order_data_list):
                    try:
                        # 验证订单数据
                        if not isinstance(order_data, dict):
                            failed_records.append({
                                'index': i + 1,
                                'error': '订单数据格式不正确'
                            })
                            continue
                        
                        # 转换数据格式以适配CSVRecord模型
                        csv_data = self._convert_order_data_to_csv_record(order_data)
                        csv_data['created_by'] = request.user
                        
                        # 创建CSV记录
                        csv_record = CSVRecord.objects.create(**csv_data)
                        
                        # 序列化返回结果
                        record_serializer = OrderRecordSerializer(csv_record)
                        success_records.append({
                            'index': i + 1,
                            'record': record_serializer.data
                        })
                        
                    except Exception as e:
                        logger.error(f"保存订单{i+1}失败: {e}")
                        failed_records.append({
                            'index': i + 1,
                            'error': str(e)
                        })
                
                # 如果有失败记录，回滚事务
                if failed_records:
                    raise Exception("部分订单保存失败")
                
                return Response({
                    "success": True,
                    "message": f"成功保存 {len(success_records)} 个订单信息",
                    "success_count": len(success_records),
                    "failed_count": len(failed_records),
                    "records": success_records
                })
                
        except Exception as e:
            logger.error(f"批量提交订单失败: {e}")
            return Response(
                {
                    "error": f"批量提交失败: {str(e)}",
                    "success_count": len(success_records),
                    "failed_count": len(failed_records),
                    "failed_records": failed_records
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _convert_order_data_to_csv_record(self, order_data):
        """将订单数据转换为CSVRecord模型格式"""
        csv_data = {}
        
        # 直接映射字段
        field_mapping = {
            '客户姓名': '客户姓名',
            '客户电话': '客户电话',
            '客户地址': '客户地址',
            '商品类型': '商品类型',
            '面积': '面积',
            'CMA点位数量': 'CMA点位数量',
            '备注赠品': '备注赠品'
        }
        
        for order_field, csv_field in field_mapping.items():
            value = order_data.get(order_field, '').strip()
            csv_data[csv_field] = value if value else ''
        
        # 处理成交金额 - 转换为Decimal
        amount_str = order_data.get('成交金额', '').strip()
        if amount_str:
            try:
                csv_data['成交金额'] = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                csv_data['成交金额'] = None
        else:
            csv_data['成交金额'] = None
        
        # 处理履约时间 - 转换为日期
        date_str = order_data.get('履约时间', '').strip()
        if date_str:
            try:
                csv_data['履约时间'] = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                csv_data['履约时间'] = None
        else:
            csv_data['履约时间'] = None
        
        return csv_data


class OrderRecordListView(ListCreateAPIView):
    """订单记录列表视图"""
    queryset = CSVRecord.objects.filter(is_active=True)
    serializer_class = OrderRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取当前用户的订单记录"""
        queryset = super().get_queryset()

        # 客户姓名筛选
        customer_name = self.request.query_params.get('customer_name')
        if customer_name:
            queryset = queryset.filter(客户姓名__icontains=customer_name)

        # 客户电话筛选
        customer_phone = self.request.query_params.get('customer_phone')
        if customer_phone:
            queryset = queryset.filter(客户电话__icontains=customer_phone)

        # 履约月份筛选
        fulfillment_month = self.request.query_params.get('fulfillment_month')
        if fulfillment_month:
            try:
                # fulfillment_month格式: YYYY-MM
                year, month = fulfillment_month.split('-')
                queryset = queryset.filter(
                    履约时间__year=int(year),
                    履约时间__month=int(month)
                )
            except (ValueError, AttributeError):
                # 如果格式不正确，忽略筛选
                pass

        return queryset.order_by('-履约时间', '-created_at')
    
    def perform_create(self, serializer):
        """创建时设置创建者"""
        serializer.save(created_by=self.request.user)


class OrderRecordDetailView(RetrieveUpdateDestroyAPIView):
    """订单记录详情视图"""
    queryset = CSVRecord.objects.filter(is_active=True)
    serializer_class = OrderRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_destroy(self, instance):
        """软删除"""
        instance.is_active = False
        instance.save()


class OrderExportView(APIView):
    """订单CSV导出视图"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        operation_id='export_orders',
        summary='导出月度订单CSV',
        description='''
        导出指定月份的订单数据为CSV格式文件。
        
        ## 功能说明
        - 支持按年月筛选订单数据
        - 导出标准CSV格式，UTF-8编码，支持中文
        - 包含订单核心字段信息
        - 自动生成文件名包含导出时间
        
        ## 使用示例
        ```
        GET /api/v1/orders/export/?month=2024-01
        ```
        
        ## 响应说明
        - 成功：返回CSV文件下载
        - 无数据：返回404错误
        - 参数错误：返回400错误
        ''',
        parameters=[
            OpenApiParameter(
                name='month',
                description='指定月份，格式：YYYY-MM',
                required=True,
                type=str,
                examples=['2024-01', '2024-12']
            )
        ],
        responses={
            200: {
                'description': 'CSV文件下载',
                'content': {
                    'text/csv': {
                        'example': '订单ID,客户姓名,客户电话,客户地址,商品类型,成交金额,面积,履约时间,CMA点位数量,备注赠品,创建时间\n1,张三,13800138001,北京市朝阳区...'
                    }
                }
            },
            400: {
                'description': '参数错误',
                'content': {
                    'application/json': {
                        'example': {'error': 'month参数格式错误，应为YYYY-MM格式'}
                    }
                }
            },
            404: {
                'description': '无数据',
                'content': {
                    'application/json': {
                        'example': {'error': '2024年1月没有订单数据'}
                    }
                }
            }
        },
        tags=['订单管理']
    )
    def get(self, request):
        """导出指定月份的订单为CSV格式"""
        # 获取月份参数
        month_param = request.query_params.get('month')
        if not month_param:
            return Response(
                {"error": "缺少month参数，格式应为YYYY-MM"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证月份格式
        try:
            year, month = month_param.split('-')
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError("月份必须在1-12之间")
        except (ValueError, AttributeError) as e:
            return Response(
                {"error": f"month参数格式错误，应为YYYY-MM格式: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 查询指定月份的订单数据
            queryset = CSVRecord.objects.filter(
                is_active=True,
                履约时间__year=year,
                履约时间__month=month
            ).order_by('履约时间', 'created_at')
            
            # 检查是否有数据
            if not queryset.exists():
                return Response(
                    {"error": f"{year}年{month}月没有订单数据"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 性能优化：对于大数据量，可以考虑使用 iterator() 或分批处理
            # 当前实现适用于中小规模数据（< 10万条记录）
            record_count = queryset.count()
            if record_count > 50000:
                logger.warning(f"大数据量导出警告：{record_count} 条记录，可能需要较长时间")
            
            # 创建CSV内容
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入CSV头部
            headers = [
                '订单ID',
                '客户姓名', 
                '客户电话',
                '客户地址',
                '商品类型',
                '成交金额',
                '面积',
                '履约时间',
                'CMA点位数量',
                '备注赠品',
                '创建时间'
            ]
            writer.writerow(headers)
            
            # 写入订单数据
            for record in queryset:
                row = [
                    record.id,
                    record.客户姓名 or '',
                    record.客户电话 or '',
                    record.客户地址 or '',
                    record.商品类型 or '',
                    float(record.成交金额) if record.成交金额 else '',
                    record.面积 or '',
                    record.履约时间.strftime('%Y-%m-%d') if record.履约时间 else '',
                    record.CMA点位数量 or '',
                    record.备注赠品 or '',
                    record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else ''
                ]
                writer.writerow(row)
            
            # 准备HTTP响应
            csv_content = output.getvalue()
            output.close()
            
            # 创建HTTP响应，设置为CSV文件下载
            response = HttpResponse(
                csv_content.encode('utf-8-sig'),  # 使用UTF-8 BOM，确保Excel能正确识别中文
                content_type='text/csv; charset=utf-8'
            )
            
            # 设置文件下载头部
            filename = f"订单导出_{year}年{month:02d}月_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"用户 {request.user} 成功导出 {year}年{month}月 订单数据，共 {queryset.count()} 条记录")
            
            return response
            
        except Exception as e:
            logger.error(f"导出订单CSV失败: {e}")
            return Response(
                {"error": f"导出失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
