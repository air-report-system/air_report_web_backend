"""
月度报表异步任务 - 移植自GUI项目的月度报表生成逻辑
"""
import os
import time
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from .models import MonthlyReport
from .services import MonthlyReportService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_monthly_report(self, report_id, user_id, config_id=None, generate_pdf=True):
    """
    生成月度报表任务 - 移植自GUI项目的月度报表生成逻辑
    
    Args:
        report_id: 月度报表ID
        user_id: 用户ID
        config_id: 配置ID（可选）
        generate_pdf: 是否生成PDF
    """
    try:
        # 获取月度报表对象
        monthly_report = MonthlyReport.objects.get(id=report_id)
        
        # 更新生成状态
        monthly_report.is_generated = False
        monthly_report.save()
        
        # 检查CSV文件是否存在
        if not monthly_report.csv_file or not os.path.exists(monthly_report.csv_file.path):
            raise Exception("CSV文件不存在")
        
        # 创建月度报表服务
        report_service = MonthlyReportService()
        
        # 生成报表
        excel_content, summary_data = report_service.generate_monthly_report(
            monthly_report.csv_file.path,
            monthly_report.config_data
        )
        
        # 保存Excel文件
        excel_filename = f"monthly_report_{report_id}_{int(time.time())}.xlsx"
        monthly_report.excel_file.save(
            excel_filename,
            ContentFile(excel_content),
            save=False
        )
        
        # 更新统计数据
        monthly_report.summary_data = summary_data
        
        # 生成PDF（如果需要）
        if generate_pdf:
            try:
                pdf_content = convert_excel_to_pdf(excel_content)
                pdf_filename = f"monthly_report_{report_id}_{int(time.time())}.pdf"
                monthly_report.pdf_file.save(
                    pdf_filename,
                    ContentFile(pdf_content),
                    save=False
                )
            except Exception as e:
                logger.warning(f"PDF生成失败: {e}")
        
        # 更新完成状态
        monthly_report.is_generated = True
        monthly_report.generation_completed_at = timezone.now()
        monthly_report.save()
        
        return {
            'status': 'success',
            'report_id': report_id,
            'excel_file': monthly_report.excel_file.name if monthly_report.excel_file else None,
            'pdf_file': monthly_report.pdf_file.name if monthly_report.pdf_file else None,
            'summary_data': summary_data
        }
        
    except Exception as e:
        # 更新错误状态
        if 'monthly_report' in locals():
            monthly_report.generation_completed_at = timezone.now()
            monthly_report.save()
        
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {
            'status': 'error',
            'error': str(e),
            'report_id': report_id
        }


@shared_task(bind=True, max_retries=3)
def process_csv_data(self, csv_file_path, config_data):
    """
    处理CSV数据任务 - 移植自GUI项目的CSV处理逻辑
    
    Args:
        csv_file_path: CSV文件路径
        config_data: 配置数据
        
    Returns:
        dict: 处理结果
    """
    try:
        from .services import MonthlyReportService
        
        report_service = MonthlyReportService()
        
        # 读取和预处理数据
        df = report_service._read_csv_data(csv_file_path)
        df = report_service._preprocess_data(df, config_data)
        
        # 计算分润比和成本
        df = report_service._calculate_profit_rates(df, config_data)
        df = report_service._calculate_costs(df, config_data)
        
        # 生成统计数据
        summary_data = report_service._generate_summary_data(df)
        
        return {
            'status': 'success',
            'summary_data': summary_data,
            'total_rows': len(df)
        }
        
    except Exception as e:
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (self.request.retries + 1))
        
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task
def match_addresses(csv_addresses, log_addresses, threshold=80.0):
    """
    地址匹配任务 - 移植自GUI项目的地址匹配逻辑
    
    Args:
        csv_addresses: CSV地址列表
        log_addresses: 日志地址列表
        threshold: 相似度阈值
        
    Returns:
        dict: 匹配结果
    """
    try:
        from apps.core.services import AddressMatchingService
        
        # 执行地址匹配
        matches = AddressMatchingService.match_addresses(
            csv_addresses, 
            log_addresses, 
            threshold
        )
        
        # 统计匹配结果
        total_addresses = len(csv_addresses)
        matched_addresses = sum(1 for match in matches if match['is_matched'])
        match_rate = (matched_addresses / total_addresses * 100) if total_addresses > 0 else 0
        
        return {
            'status': 'success',
            'matches': matches,
            'total_addresses': total_addresses,
            'matched_addresses': matched_addresses,
            'match_rate': match_rate
        }
        
    except Exception as e:
        logger.error(f"地址匹配失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def convert_excel_to_pdf(excel_content):
    """
    将Excel转换为PDF - 移植自GUI项目的PDF转换逻辑
    
    Args:
        excel_content: Excel文件内容
        
    Returns:
        bytes: PDF文件内容
    """
    try:
        # TODO: 实现真实的Excel到PDF转换
        # 可以使用 openpyxl + reportlab 或其他库
        
        # 临时实现：返回模拟的PDF内容
        pdf_content = f"月度报表PDF版本\n生成时间: {datetime.now()}\n"
        return pdf_content.encode('utf-8')
        
    except Exception as e:
        logger.error(f"Excel转PDF失败: {e}")
        raise e


@shared_task
def cleanup_old_monthly_reports():
    """清理旧的月度报表文件"""
    from datetime import timedelta
    
    # 删除90天前的报表文件
    cutoff_date = timezone.now() - timedelta(days=90)
    old_reports = MonthlyReport.objects.filter(
        created_at__lt=cutoff_date,
        is_generated=True
    )
    
    cleaned_count = 0
    for report in old_reports:
        try:
            # 删除文件
            if report.excel_file and os.path.exists(report.excel_file.path):
                os.remove(report.excel_file.path)
            if report.pdf_file and os.path.exists(report.pdf_file.path):
                os.remove(report.pdf_file.path)
            
            # 重置文件字段
            report.excel_file = None
            report.pdf_file = None
            report.is_generated = False
            report.save()
            
            cleaned_count += 1
            
        except Exception as e:
            logger.warning(f"清理月度报表 {report.id} 失败: {e}")
    
    return f"清理了 {cleaned_count} 个旧的月度报表文件"


@shared_task
def analyze_monthly_trends(report_ids):
    """
    分析月度趋势 - 移植自GUI项目的趋势分析功能
    
    Args:
        report_ids: 报表ID列表
        
    Returns:
        dict: 趋势分析结果
    """
    try:
        reports = MonthlyReport.objects.filter(
            id__in=report_ids,
            is_generated=True
        ).order_by('report_month')
        
        if not reports:
            return {'status': 'error', 'error': '没有可分析的报表'}
        
        # 提取趋势数据
        trend_data = []
        for report in reports:
            if report.summary_data:
                trend_data.append({
                    'month': report.report_month.strftime('%Y-%m'),
                    'total_revenue': report.summary_data.get('total_revenue', 0),
                    'total_profit': report.summary_data.get('total_profit', 0),
                    'total_orders': report.summary_data.get('total_orders', 0),
                    'profit_margin': report.summary_data.get('profit_margin', 0)
                })
        
        # 计算趋势指标
        if len(trend_data) >= 2:
            latest = trend_data[-1]
            previous = trend_data[-2]
            
            revenue_growth = ((latest['total_revenue'] - previous['total_revenue']) / 
                            previous['total_revenue'] * 100) if previous['total_revenue'] > 0 else 0
            
            profit_growth = ((latest['total_profit'] - previous['total_profit']) / 
                           previous['total_profit'] * 100) if previous['total_profit'] > 0 else 0
            
            order_growth = ((latest['total_orders'] - previous['total_orders']) / 
                          previous['total_orders'] * 100) if previous['total_orders'] > 0 else 0
        else:
            revenue_growth = profit_growth = order_growth = 0
        
        return {
            'status': 'success',
            'trend_data': trend_data,
            'growth_metrics': {
                'revenue_growth': revenue_growth,
                'profit_growth': profit_growth,
                'order_growth': order_growth
            }
        }
        
    except Exception as e:
        logger.error(f"月度趋势分析失败: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
