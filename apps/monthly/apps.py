from django.apps import AppConfig


class MonthlyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.monthly'
    label = 'monthly'
    verbose_name = '月度报表'
