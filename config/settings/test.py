"""
测试环境配置

专门用于运行测试的Django设置
"""
from .base import *

# 数据库配置 - 使用内存SQLite数据库加速测试
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# 禁用缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# 禁用日志输出
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# 密码验证器 - 测试环境使用简单验证器
AUTH_PASSWORD_VALIDATORS = []

# 邮件后端 - 使用内存后端
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 文件存储 - 使用临时目录
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

# 静态文件 - 禁用收集
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Celery配置 - 使用同步执行
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# API配置 - 使用测试密钥
GEMINI_API_KEY = 'test_gemini_key'
OPENAI_API_KEY = 'test_openai_key'
GEMINI_BASE_URL = 'https://test-api.example.com'
OPENAI_BASE_URL = 'https://test-openai.example.com'

# 测试特定设置
USE_OPENAI_OCR = False  # 默认使用Gemini进行测试
API_TIMEOUT_SECONDS = 5  # 缩短超时时间
OCR_TIMEOUT_SECONDS = 5
IMAGE_PROCESSING_TIMEOUT_SECONDS = 5

# 禁用调试工具栏
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
}

# 安全设置 - 测试环境放宽限制
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True

# 测试数据库事务
DATABASES['default']['ATOMIC_REQUESTS'] = True

# 禁用迁移
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# 测试覆盖率排除
COVERAGE_EXCLUDE = [
    '*/migrations/*',
    '*/venv/*',
    '*/env/*',
    'manage.py',
    'config/wsgi.py',
    'config/asgi.py',
    '*/tests.py',
    '*/test_*.py',
    '*/*_test.py',
]
