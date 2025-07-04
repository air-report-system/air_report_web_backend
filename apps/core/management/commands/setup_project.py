"""
项目初始化管理命令
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.reports.models import ReportTemplate
from apps.monthly.models import MonthlyReportConfig

User = get_user_model()


class Command(BaseCommand):
    help = '初始化项目数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='创建超级用户',
        )
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='超级用户用户名',
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@example.com',
            help='超级用户邮箱',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='超级用户密码',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化项目...'))

        with transaction.atomic():
            # 创建超级用户
            if options['create_superuser']:
                self.create_superuser(
                    options['username'],
                    options['email'],
                    options['password']
                )

            # 创建默认报告模板配置
            self.create_default_templates()

            # 创建默认月度报表配置
            self.create_default_monthly_configs()

        self.stdout.write(self.style.SUCCESS('项目初始化完成！'))

    def create_superuser(self, username, email, password):
        """创建超级用户"""
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'用户 {username} 已存在，跳过创建')
            )
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        self.stdout.write(
            self.style.SUCCESS(f'创建超级用户: {username}')
        )

    def create_default_templates(self):
        """创建默认报告模板"""
        templates = [
            {
                'name': '标准检测报告模板',
                'description': '标准的室内空气质量检测报告模板',
                'is_active': True,
                'template_config': {
                    'include_charts': True,
                    'include_summary': True,
                    'include_recommendations': True
                }
            },
            {
                'name': '简化检测报告模板',
                'description': '简化版的检测报告模板，适用于快速出报告',
                'is_active': True,
                'template_config': {
                    'include_charts': False,
                    'include_summary': True,
                    'include_recommendations': False
                }
            }
        ]

        for template_data in templates:
            template, created = ReportTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'创建报告模板: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'报告模板 {template.name} 已存在')
                )

    def create_default_monthly_configs(self):
        """创建默认月度报表配置"""
        configs = [
            {
                'name': '标准配置',
                'description': '标准的月度报表配置',
                'uniform_profit_rate': False,
                'profit_rate_value': 0.05,
                'medicine_cost_per_order': 120.1,
                'cma_cost_per_point': 60.0,
                'is_default': True,
                'config_options': {
                    'include_address_matching': True,
                    'exclude_recheck_records': True,
                    'date_range_days': 30
                }
            },
            {
                'name': '统一分润配置',
                'description': '所有订单使用统一分润比的配置',
                'uniform_profit_rate': True,
                'profit_rate_value': 0.05,
                'medicine_cost_per_order': 120.1,
                'cma_cost_per_point': 60.0,
                'is_default': False,
                'config_options': {
                    'include_address_matching': True,
                    'exclude_recheck_records': True,
                    'date_range_days': 30
                }
            }
        ]

        for config_data in configs:
            config, created = MonthlyReportConfig.objects.get_or_create(
                name=config_data['name'],
                defaults=config_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'创建月度报表配置: {config.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'月度报表配置 {config.name} 已存在')
                )
