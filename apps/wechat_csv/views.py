"""
微信CSV处理视图
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login
from django.utils import timezone
from datetime import timedelta
import logging

from .models import WechatCsvRecord, ProcessingHistory, ValidationResult, LoginAttempt
from .serializers import (
    WechatMessageProcessSerializer, UpdateTableSerializer, SubmitToGitHubSerializer,
    LoginSerializer, ProcessResponseSerializer, SubmitResponseSerializer,
    WechatCsvRecordSerializer, ProcessingHistorySerializer
)
from .services import WechatMessageProcessor, CsvDataProcessor, DuplicateDetector, GitHubService

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """登录视图"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """处理登录请求"""
        # 先检查IP是否被锁定
        if self._is_ip_locked(request):
            return Response(
                {"error": "IP地址已被锁定，请稍后再试"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # 记录登录失败
            self._record_login_attempt(request, success=False)
            # 再次检查是否需要锁定
            if self._is_ip_locked(request):
                return Response(
                    {"error": "IP地址已被锁定，请稍后再试"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 登录成功
        self._record_login_attempt(request, success=True)
        request.session['wechat_csv_authenticated'] = True

        return Response({"success": True, "message": "登录成功"})
    
    def _record_login_attempt(self, request, success=True):
        """记录登录尝试"""
        ip_address = self._get_client_ip(request)
        
        try:
            attempt, created = LoginAttempt.objects.get_or_create(ip_address=ip_address)
            
            if success:
                # 登录成功，重置尝试次数
                attempt.attempts = 0
                attempt.is_locked = False
                attempt.locked_until = None
            else:
                # 登录失败，增加尝试次数
                attempt.attempts += 1
                
                # 检查是否需要锁定
                from django.conf import settings
                if attempt.attempts >= settings.WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT:
                    attempt.is_locked = True
                    attempt.locked_until = timezone.now() + timedelta(hours=settings.WECHAT_CSV_LOCKOUT_HOURS)
            
            attempt.save()
        except Exception as e:
            logger.error(f"记录登录尝试失败: {e}")
    
    def _is_ip_locked(self, request):
        """检查IP是否被锁定"""
        ip_address = self._get_client_ip(request)
        
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address)
            if attempt.is_locked and attempt.locked_until:
                return timezone.now() < attempt.locked_until
        except LoginAttempt.DoesNotExist:
            pass
        
        return False
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ProcessMessageView(APIView):
    """处理微信消息视图"""
    permission_classes = [permissions.AllowAny]  # 使用自定义认证
    
    def post(self, request):
        """处理微信消息"""
        # 检查认证
        if not request.session.get('wechat_csv_authenticated'):
            return Response(
                {"error": "未授权访问，请先登录"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = WechatMessageProcessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        wechat_text = serializer.validated_data['wechat_text']
        
        try:
            # 创建处理历史记录
            history = ProcessingHistory.objects.create(
                original_message=wechat_text,
                status='processing'
            )
            
            # 使用Gemini API格式化消息
            processor = WechatMessageProcessor()
            formatted_csv = processor.format_wechat_message(wechat_text)
            
            # 提取履约日期，确定使用哪个月份的文件
            fulfillment_dates = processor.extract_fulfillment_dates(formatted_csv)
            csv_filename = processor.get_current_month_file(fulfillment_dates)
            
            # 获取GitHub仓库中的现有文件内容
            github_service = GitHubService()
            existing_content, _ = github_service.get_file_content(csv_filename)
            
            # 检查是否有重复记录
            new_entries = formatted_csv.strip().split("\n")
            duplicate_detector = DuplicateDetector()
            duplicate_result = duplicate_detector.check_for_duplicates(new_entries, existing_content)
            
            # 解析CSV为表格数据
            csv_processor = CsvDataProcessor()
            parse_result = csv_processor.parse_csv_to_table_data(formatted_csv)
            table_data = parse_result["table_data"]
            fix_info = parse_result["fix_info"]
            fixed_csv_content = parse_result.get("fixed_csv_content", formatted_csv)
            
            # 验证表格数据
            validation_result = csv_processor.validate_table_data(table_data)
            
            # 更新处理历史
            history.formatted_csv = fixed_csv_content
            history.github_file_path = csv_filename
            history.status = 'completed'
            history.save()
            
            # 创建验证结果记录
            ValidationResult.objects.create(
                processing_history=history,
                is_valid=validation_result['valid'],
                errors=validation_result['errors'],
                warnings=validation_result['warnings'],
                duplicate_indexes=duplicate_result["duplicate_indexes"],
                match_details=duplicate_result["match_details"],
                format_fixes=fix_info
            )
            
            # 创建CSV记录
            for row_data in table_data:
                WechatCsvRecord.objects.create(
                    customer_name=row_data.get("客户姓名", ""),
                    customer_phone=row_data.get("客户电话", ""),
                    customer_address=row_data.get("客户地址", ""),
                    product_type=row_data.get("商品类型", ""),
                    transaction_amount=float(row_data.get("成交金额", 0)) if row_data.get("成交金额") else None,
                    area=float(row_data.get("面积", 0)) if row_data.get("面积") else None,
                    fulfillment_date=row_data.get("履约时间") if row_data.get("履约时间") else None,
                    cma_points=row_data.get("CMA点位数量", ""),
                    gift_notes=row_data.get("备注赠品", ""),
                    processing_history=history
                )
            
            response_data = {
                "formatted_csv": fixed_csv_content,
                "original_csv": formatted_csv,
                "table_data": table_data,
                "validation": validation_result,
                "csv_filename": csv_filename,
                "existing_content": existing_content,
                "potential_duplicates": duplicate_result["duplicate_indexes"],
                "match_details": duplicate_result["match_details"],
                "format_fixes": fix_info,
            }
            
            return Response(response_data)
            
        except Exception as e:
            # 更新处理历史为失败状态
            if 'history' in locals():
                history.status = 'failed'
                history.error_message = str(e)
                history.save()
            
            logger.error(f"处理微信消息失败: {e}")
            return Response(
                {"error": f"处理失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateTableView(APIView):
    """更新表格数据视图"""
    permission_classes = [permissions.AllowAny]  # 使用自定义认证
    
    def post(self, request):
        """更新表格数据并返回验证结果"""
        # 检查认证
        if not request.session.get('wechat_csv_authenticated'):
            return Response(
                {"error": "未授权访问，请先登录"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = UpdateTableSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        table_data = serializer.validated_data['table_data']
        
        try:
            # 验证表格数据
            csv_processor = CsvDataProcessor()
            validation_result = csv_processor.validate_table_data(table_data)
            
            # 转换为CSV格式
            csv_content = csv_processor.table_data_to_csv(table_data)
            
            return Response({
                "success": True,
                "validation": validation_result,
                "csv_content": csv_content
            })
            
        except Exception as e:
            logger.error(f"更新表格数据失败: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubmitToGitHubView(APIView):
    """提交到GitHub视图"""
    permission_classes = [permissions.AllowAny]  # 使用自定义认证

    def post(self, request):
        """提交CSV内容到GitHub"""
        # 检查认证
        if not request.session.get('wechat_csv_authenticated'):
            return Response(
                {"error": "未授权访问，请先登录"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = SubmitToGitHubSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        csv_filename = serializer.validated_data['csv_filename']
        table_data = serializer.validated_data.get('table_data')
        csv_content = serializer.validated_data.get('csv_content', '')

        # 如果提供了table_data，优先使用table_data转换为CSV
        if table_data:
            csv_processor = CsvDataProcessor()
            csv_content = csv_processor.table_data_to_csv(table_data)

        if not csv_content:
            return Response(
                {"error": "缺少CSV内容"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 提交到GitHub
            github_service = GitHubService()
            result = github_service.submit_to_github(csv_filename, csv_content)

            if result['success']:
                # 更新相关的处理历史记录
                try:
                    # 查找最近的处理历史记录
                    history = ProcessingHistory.objects.filter(
                        github_file_path=csv_filename,
                        status='completed'
                    ).order_by('-created_at').first()

                    if history and result.get('commit_info'):
                        history.status = 'submitted'
                        history.github_commit_sha = result['commit_info'].get('sha', '')
                        history.github_commit_url = result['commit_info'].get('url', '')
                        history.save()
                except Exception as e:
                    logger.warning(f"更新处理历史失败: {e}")

                return Response(result)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"提交到GitHub失败: {e}")
            return Response(
                {"error": f"提交失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """登出视图"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """处理登出请求"""
        request.session.pop('wechat_csv_authenticated', None)
        return Response({"success": True, "message": "登出成功"})


# 管理视图
class RecordsListView(APIView):
    """CSV记录列表视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取CSV记录列表"""
        records = WechatCsvRecord.objects.all().order_by('-created_at')
        serializer = WechatCsvRecordSerializer(records, many=True)
        return Response(serializer.data)


class ProcessingHistoryListView(APIView):
    """处理历史列表视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取处理历史列表"""
        histories = ProcessingHistory.objects.all().order_by('-created_at')
        serializer = ProcessingHistorySerializer(histories, many=True)
        return Response(serializer.data)
