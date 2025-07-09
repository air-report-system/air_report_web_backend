"""
Replit环境设置
专为Replit部署优化的Django配置
"""
import os
import urllib.parse as urlparse
from pathlib import Path

# 基础设置
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 从base导入设置
from .base import *

# Replit环境特定设置
# 默认启用DEBUG模式以便调试，生产环境通过环境变量关闭
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# 生产环境媒体文件服务说明
# 注意：在生产环境中(DEBUG=False)，媒体文件通过urls.py中的自定义路由提供服务
# 这适用于Replit等小型部署，大型生产环境应使用Nginx等Web服务器

# Replit主机配置 - 允许Replit域名
ALLOWED_HOSTS = [
    '*',  # Replit需要允许所有主机
    '.replit.co',
    '.repl.co',
    '.replit.dev',
    '.lovableproject.com',
    'localhost',
    '127.0.0.1',
]

# 数据库配置
# 重要：Replit的免费计划可能会清除SQLite文件
# 推荐使用外部数据库服务如PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and 'postgresql' in DATABASE_URL:
    # PostgreSQL配置（推荐用于生产）
    url = urlparse.urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port,
        }
    }
else:
    # SQLite配置（仅用于开发测试）
    # 注意：在Replit中SQLite数据可能会在重启时丢失
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS配置 - 允许前后端跨域通信
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://*.alicee.me",
    "https://*.replit.app",
    "https://*.replit.co",
    "https://*.repl.co",
    "https://*.replit.dev",
    "https://*.lovableproject.com",
    "http://localhost:3000",  # 前端开发服务器
    "http://localhost:8000",  # 后端开发服务器
]

# CORS头部配置
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# 安全设置
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-replit-dev-key-change-me-in-production')

# CSRF配置
CSRF_TRUSTED_ORIGINS = [
    'https://*.alicee.me',
    'https://*.replit.app',
    'https://*.replit.co',
    'https://*.repl.co',
    'https://*.replit.dev',
    'https://*.lovableproject.com',
    'http://localhost:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
]

# 如果是生产环境，禁用CSRF（API模式）
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# 简化的日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Celery配置 - 部署环境优化
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 增加API超时时间以适应部署环境
API_TIMEOUT_SECONDS = int(os.getenv('API_TIMEOUT_SECONDS', '120'))
OCR_TIMEOUT_SECONDS = int(os.getenv('OCR_TIMEOUT_SECONDS', '180'))
IMAGE_PROCESSING_TIMEOUT_SECONDS = int(os.getenv('IMAGE_PROCESSING_TIMEOUT_SECONDS', '240'))

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# 邮件后端
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 时区
USE_TZ = True
TIME_ZONE = 'Asia/Shanghai'

# 静态文件和媒体文件配置（生产环境）
if not DEBUG:
    # 尝试使用WhiteNoise处理静态文件（如果可用）
    try:
        import whitenoise
        MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
        STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    except ImportError:
        # WhiteNoise不可用时的回退方案
        pass

# 创建必要的目录
os.makedirs(BASE_DIR / 'staticfiles', exist_ok=True)
os.makedirs(BASE_DIR / 'media', exist_ok=True)
os.makedirs(BASE_DIR / 'static', exist_ok=True)

# 字体和LibreOffice环境配置
FONTS_DIR = BASE_DIR / 'templates' / 'fonts'
os.environ.setdefault('FONTCONFIG_PATH', os.path.expanduser('~/.config/fontconfig'))
os.environ.setdefault('UNO_PATH', '/usr/lib/libreoffice/program')
os.environ.setdefault('DISPLAY', ':99')

# 文件上传配置
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# API配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# 数据持久化警告
if not DATABASE_URL or 'sqlite' in str(DATABASES['default']['ENGINE']):
    import warnings
    warnings.warn(
        "⚠️  使用SQLite数据库：数据可能在Replit重启时丢失！\n"
        "🔧 推荐配置PostgreSQL数据库URL以确保数据持久化。",
        UserWarning
    )