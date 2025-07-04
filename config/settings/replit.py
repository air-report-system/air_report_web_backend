"""
Replit环境设置
"""
import os
import urllib.parse as urlparse
from pathlib import Path

# 基础设置
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 从base导入设置
from .base import *

# Replit环境特定设置
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Replit主机配置
ALLOWED_HOSTS = ['*']  # Replit需要允许所有主机

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

# CORS配置 - 允许Replit域名
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# 安全设置
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-replit-dev-key-change-me')

# CSRF配置（仅用于开发测试）
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.replit.co',
        'https://*.repl.co',
        'https://*.lovableproject.com',  # Lovable平台域名
        'http://localhost:8000',
        'http://127.0.0.1:8000'
    ]

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

# Celery配置 - 禁用异步任务
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

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

# 创建必要的目录
os.makedirs(BASE_DIR / 'staticfiles', exist_ok=True)
os.makedirs(BASE_DIR / 'media', exist_ok=True)
os.makedirs(BASE_DIR / 'static', exist_ok=True)

# 数据持久化警告
if not DATABASE_URL or 'sqlite' in str(DATABASES['default']['ENGINE']):
    import warnings
    warnings.warn(
        "⚠️  使用SQLite数据库：数据可能在Replit重启时丢失！\n"
        "🔧 推荐配置PostgreSQL数据库URL以确保数据持久化。",
        UserWarning
    )