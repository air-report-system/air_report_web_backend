"""
测试数据工厂

使用factory-boy创建测试数据，基于GUI项目的真实数据格式
"""
import factory
import factory.fuzzy
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
import json
from datetime import date, datetime

from apps.files.models import UploadedFile
from apps.ocr.models import OCRResult, ContactInfo
from apps.reports.models import Report, ReportTemplate
from apps.monthly.models import MonthlyReport, MonthlyReportConfig
from apps.batch.models import BatchJob, BatchFileItem

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """用户工厂"""
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'testuser{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name', locale='zh_CN')
    last_name = factory.Faker('last_name', locale='zh_CN')
    is_active = True


class UploadedFileFactory(factory.django.DjangoModelFactory):
    """上传文件工厂"""
    class Meta:
        model = UploadedFile
    
    original_name = factory.Faker('file_name', extension='jpg')
    file_size = factory.fuzzy.FuzzyInteger(1024, 10240)  # 1KB-10KB
    file_type = 'image'
    mime_type = 'image/jpeg'
    hash_md5 = factory.Faker('md5')
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def file(self):
        """创建测试图片文件"""
        image = Image.new('RGB', (800, 600), color='white')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            name=self.original_name,
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )


class OCRResultFactory(factory.django.DjangoModelFactory):
    """OCR结果工厂"""
    class Meta:
        model = OCRResult
    
    file = factory.SubFactory(UploadedFileFactory)
    phone = factory.Faker('phone_number', locale='zh_CN')
    date = factory.fuzzy.FuzzyDate(date(2024, 1, 1), date(2024, 12, 31)).fuzz().strftime('%m-%d')
    temperature = factory.fuzzy.FuzzyDecimal(20.0, 30.0, 1)
    humidity = factory.fuzzy.FuzzyDecimal(30.0, 70.0, 1)
    check_type = factory.fuzzy.FuzzyChoice(['initial', 'recheck'])
    confidence_score = factory.fuzzy.FuzzyDecimal(0.8, 1.0, 2)
    status = 'completed'
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def points_data(self):
        """生成点位数据"""
        rooms = ['客厅', '主卧', '次卧', '厨房', '书房', '卫生间']
        points = {}
        
        # 根据检测类型生成不同的点位值
        if self.check_type == 'initial':
            # 初检：大多数点位值>0.080
            for room in factory.Faker('random_elements', elements=rooms, length=factory.fuzzy.FuzzyInteger(3, 6).fuzz(), unique=True).generate():
                if factory.Faker('boolean', chance_of_getting_true=70).generate():
                    points[room] = round(factory.fuzzy.FuzzyDecimal(0.081, 0.120).fuzz(), 3)
                else:
                    points[room] = round(factory.fuzzy.FuzzyDecimal(0.050, 0.080).fuzz(), 3)
        else:
            # 复检：大多数点位值≤0.080
            for room in factory.Faker('random_elements', elements=rooms, length=factory.fuzzy.FuzzyInteger(3, 6).fuzz(), unique=True).generate():
                if factory.Faker('boolean', chance_of_getting_true=80).generate():
                    points[room] = round(factory.fuzzy.FuzzyDecimal(0.040, 0.080).fuzz(), 3)
                else:
                    points[room] = round(factory.fuzzy.FuzzyDecimal(0.081, 0.100).fuzz(), 3)
        
        return points


class ContactInfoFactory(factory.django.DjangoModelFactory):
    """联系人信息工厂"""
    class Meta:
        model = ContactInfo
    
    ocr_result = factory.SubFactory(OCRResultFactory)
    contact_name = factory.Faker('name', locale='zh_CN')
    full_phone = factory.LazyAttribute(lambda obj: obj.ocr_result.phone)
    address = factory.Faker('address', locale='zh_CN')
    match_type = factory.fuzzy.FuzzyChoice(['exact', 'partial', 'fuzzy'])
    similarity_score = factory.fuzzy.FuzzyDecimal(0.7, 1.0, 2)
    match_source = factory.fuzzy.FuzzyChoice(['csv', 'log', 'manual'])


class ReportTemplateFactory(factory.django.DjangoModelFactory):
    """报告模板工厂"""
    class Meta:
        model = ReportTemplate
    
    name = factory.Faker('sentence', nb_words=3, locale='zh_CN')
    description = factory.Faker('text', max_nb_chars=200, locale='zh_CN')
    is_active = True
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def template_config(self):
        """生成模板配置"""
        return {
            'page_size': 'A4',
            'font_family': '宋体',
            'font_size': 12,
            'line_spacing': 1.5,
            'margins': {
                'top': 2.5,
                'bottom': 2.5,
                'left': 2.0,
                'right': 2.0
            }
        }


class ReportFactory(factory.django.DjangoModelFactory):
    """报告工厂"""
    class Meta:
        model = Report
    
    ocr_result = factory.SubFactory(OCRResultFactory)
    report_type = 'detection'
    title = factory.Faker('sentence', nb_words=4, locale='zh_CN')
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def form_data(self):
        """生成表单数据"""
        return {
            'customer_name': factory.Faker('name', locale='zh_CN').generate(),
            'customer_phone': self.ocr_result.phone,
            'detection_address': factory.Faker('address', locale='zh_CN').generate(),
            'detection_date': factory.Faker('date', pattern='%Y-%m-%d').generate(),
            'detection_area': str(factory.fuzzy.FuzzyInteger(50, 200).fuzz()),
            'company_name': '北京某某检测有限公司',
            'report_number': f'BJ{factory.Faker("date", pattern="%Y%m%d").generate()}{factory.fuzzy.FuzzyInteger(1, 999):03d}',
            'detection_standard': 'GB/T 18883-2022',
            'detection_method': '酚试剂分光光度法'
        }
    
    @factory.lazy_attribute
    def template_data(self):
        """生成模板数据"""
        points_table = []
        for room, value in self.ocr_result.points_data.items():
            points_table.append({
                'room_name': room,
                'value': value,
                'standard_limit': '≤0.08',
                'result': '超标' if value > 0.08 else '合格'
            })
        
        exceeded_count = sum(1 for point in points_table if point['result'] == '超标')
        total_count = len(points_table)
        
        if exceeded_count == 0:
            detection_results = '全部合格'
            conclusion = '检测结果符合GB/T 18883-2022标准要求'
        elif exceeded_count == total_count:
            detection_results = '全部超标'
            conclusion = '检测结果超出标准限值，建议进行治理后复检'
        else:
            detection_results = '部分超标'
            conclusion = f'{exceeded_count}个点位超标，建议针对超标区域进行治理'
        
        return {
            'customer_name': self.form_data['customer_name'],
            'customer_phone': self.form_data['customer_phone'],
            'detection_address': self.form_data['detection_address'],
            'detection_date': self.form_data['detection_date'],
            'report_number': self.form_data['report_number'],
            'points_table': points_table,
            'detection_results': detection_results,
            'conclusion': conclusion
        }


class MonthlyReportConfigFactory(factory.django.DjangoModelFactory):
    """月度报表配置工厂"""
    class Meta:
        model = MonthlyReportConfig
    
    name = factory.Faker('sentence', nb_words=3, locale='zh_CN')
    description = factory.Faker('text', max_nb_chars=200, locale='zh_CN')
    uniform_profit_rate = factory.Faker('boolean')
    profit_rate_value = factory.fuzzy.FuzzyDecimal(0.03, 0.12, 2)
    medicine_cost_per_order = factory.fuzzy.FuzzyDecimal(100.0, 150.0, 1)
    cma_cost_per_point = factory.fuzzy.FuzzyDecimal(50.0, 80.0, 1)
    is_default = False
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def config_options(self):
        """生成配置选项"""
        return {
            'exclude_recheck_from_profit': factory.Faker('boolean').generate(),
            'include_gift_cost_analysis': factory.Faker('boolean').generate(),
            'detailed_address_matching': True,
            'auto_generate_report_number': True
        }


class MonthlyReportFactory(factory.django.DjangoModelFactory):
    """月度报表工厂"""
    class Meta:
        model = MonthlyReport
    
    title = factory.LazyAttribute(lambda obj: f'{obj.report_month.year}年{obj.report_month.month}月月度报表')
    report_month = factory.fuzzy.FuzzyDate(date(2024, 1, 1), date(2024, 12, 1))
    csv_file = factory.SubFactory(UploadedFileFactory, original_name='orders.csv', file_type='document', mime_type='text/csv')
    log_file = factory.SubFactory(UploadedFileFactory, original_name='log.txt', file_type='document', mime_type='text/plain')
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def config_data(self):
        """生成配置数据"""
        return {
            'uniform_profit_rate': factory.Faker('boolean').generate(),
            'profit_rate_value': factory.fuzzy.FuzzyDecimal(0.05, 0.10, 2).fuzz(),
            'medicine_cost_per_order': 120.1,
            'cma_cost_per_point': 60.0
        }
    
    @factory.lazy_attribute
    def summary_data(self):
        """生成汇总数据"""
        total_orders = factory.fuzzy.FuzzyInteger(10, 50).fuzz()
        total_amount = factory.fuzzy.FuzzyDecimal(10000, 100000, 2).fuzz()
        
        return {
            'total_orders': total_orders,
            'total_amount': float(total_amount),
            'total_profit': float(total_amount * factory.fuzzy.FuzzyDecimal(0.05, 0.10).fuzz()),
            'average_order_value': float(total_amount / total_orders)
        }
    
    @factory.lazy_attribute
    def cost_analysis(self):
        """生成成本分析"""
        total_orders = self.summary_data['total_orders']
        
        return {
            '药水成本': total_orders * 120.1,
            'CMA成本': factory.fuzzy.FuzzyInteger(1000, 5000).fuzz(),
            '人工成本': factory.fuzzy.FuzzyInteger(3000, 8000).fuzz(),
            '其他成本': factory.fuzzy.FuzzyInteger(500, 2000).fuzz()
        }


class BatchJobFactory(factory.django.DjangoModelFactory):
    """批量任务工厂"""
    class Meta:
        model = BatchJob
    
    name = factory.Faker('sentence', nb_words=4, locale='zh_CN')
    total_files = factory.fuzzy.FuzzyInteger(5, 20)
    processed_files = 0
    failed_files = 0
    status = 'created'
    created_by = factory.SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def settings(self):
        """生成批量任务设置"""
        return {
            'ocr_provider': factory.fuzzy.FuzzyChoice(['gemini', 'openai']).fuzz(),
            'enable_multi_ocr': factory.Faker('boolean').generate(),
            'ocr_attempts': factory.fuzzy.FuzzyInteger(1, 5).fuzz(),
            'auto_retry_failed': factory.Faker('boolean').generate(),
            'parallel_processing': factory.Faker('boolean').generate(),
            'batch_size': factory.fuzzy.FuzzyInteger(5, 20).fuzz()
        }


class BatchFileItemFactory(factory.django.DjangoModelFactory):
    """批量文件项工厂"""
    class Meta:
        model = BatchFileItem
    
    batch_job = factory.SubFactory(BatchJobFactory)
    file = factory.SubFactory(UploadedFileFactory)
    processing_order = factory.Sequence(lambda n: n + 1)
    status = 'pending'
    
    @factory.maybe_lazy_attribute
    def ocr_result(self):
        """根据状态决定是否创建OCR结果"""
        if self.status == 'completed':
            return factory.SubFactory(OCRResultFactory, file=self.file)
        return None
    
    @factory.maybe_lazy_attribute
    def processing_time_seconds(self):
        """根据状态决定是否设置处理时间"""
        if self.status in ['completed', 'failed']:
            return factory.fuzzy.FuzzyDecimal(5.0, 30.0, 1).fuzz()
        return None
