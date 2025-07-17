"""
AI配置管理应用配置
"""
from django.apps import AppConfig


class AiConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_config'
    verbose_name = 'AI配置管理'
    
    def ready(self):
        """应用就绪时的初始化操作"""
        # 导入信号处理器
        try:
            from . import signals
        except ImportError:
            pass
