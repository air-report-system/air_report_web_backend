"""
Celery配置
"""
import os
from celery import Celery
from django.conf import settings

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 创建Celery应用
app = Celery('backend')

# 使用Django设置配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# Celery配置
app.conf.update(
    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务路由
    task_routes={
        'apps.ocr.tasks.*': {'queue': 'ocr'},
        'apps.reports.tasks.*': {'queue': 'reports'},
        'apps.batch.tasks.*': {'queue': 'batch'},
        'apps.monthly.tasks.*': {'queue': 'monthly'},
    },

    # 任务优先级
    task_default_priority=5,
    worker_prefetch_multiplier=1,

    # 结果后端
    result_backend='redis://localhost:6379/1',
    result_expires=3600,  # 1小时

    # 任务超时
    task_soft_time_limit=300,  # 5分钟软超时
    task_time_limit=600,       # 10分钟硬超时

    # 重试配置
    task_acks_late=True,

    # 监控
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# 队列配置
app.conf.task_routes = {
    # OCR处理任务
    'apps.ocr.tasks.process_image_ocr': {'queue': 'ocr'},
    'apps.ocr.tasks.multi_ocr_process': {'queue': 'ocr'},

    # 报告生成任务
    'apps.reports.tasks.generate_report': {'queue': 'reports'},
    'apps.reports.tasks.convert_to_pdf': {'queue': 'reports'},

    # 批量处理任务
    'apps.batch.tasks.start_batch_processing': {'queue': 'batch'},
    'apps.batch.tasks.process_batch_item': {'queue': 'batch'},
    'apps.batch.tasks.retry_failed_items': {'queue': 'batch'},

    # 月度报表任务
    'apps.monthly.tasks.generate_monthly_report': {'queue': 'monthly'},
    'apps.monthly.tasks.process_csv_data': {'queue': 'monthly'},
    'apps.monthly.tasks.match_addresses': {'queue': 'monthly'},
}

@app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'
