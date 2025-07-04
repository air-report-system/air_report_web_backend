from django.apps import AppConfig


class BatchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.batch'
    label = 'batch'
    verbose_name = '批量处理'
