# 确保Celery应用在Django启动时加载
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Skip celery import if not available
    __all__ = ()