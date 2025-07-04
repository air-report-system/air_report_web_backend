from django.apps import AppConfig


class WechatCsvConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.wechat_csv'
    verbose_name = '微信CSV提交工具'
