"""
Django基础设置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,alicee.me,*.alicee.me').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    'channels',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.core',
    'apps.files',
    'apps.ocr',
    'apps.reports',
    'apps.batch',
    'apps.monthly',
    'apps.orders',
    'apps.ai_config',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 如果设置了DATABASE_URL，使用PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and 'postgresql' in DATABASE_URL:
    # 简单的PostgreSQL配置解析
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname,
        'PORT': url.port,
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# URL配置
APPEND_SLASH = False  # 禁用自动添加斜杠，避免API请求重定向问题

# 自定义用户模型
AUTH_USER_MODEL = 'accounts.User'

# REST Framework配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# API文档配置
SPECTACULAR_SETTINGS = {
    'TITLE': '室内空气检测平台 API',
    'DESCRIPTION': '室内空气检测数据处理和报告生成平台的REST API，包含AI配置管理系统',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'TAGS': [
        {'name': 'AI配置管理', 'description': 'AI服务配置的增删改查和管理操作'},
        {'name': 'AI监控', 'description': 'AI服务的监控、健康检查和统计'},
        {'name': 'OCR处理', 'description': '图片OCR识别和数据提取'},
        {'name': '用户管理', 'description': '用户认证和权限管理'},
        {'name': '文件管理', 'description': '文件上传和管理'},
        {'name': '报告管理', 'description': '检测报告的生成和管理'},
    ],
}

# CORS配置
CORS_ALLOWED_ORIGINS = [
    "https://alicee.me",
    "https://*.alicee.me",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# CSRF设置 - 对API路径豁免CSRF检查
CSRF_TRUSTED_ORIGINS = [
    "https://alicee.me",
    "https://*.alicee.me",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Celery配置
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Channels配置
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv('REDIS_URL', 'redis://localhost:6379/2')],
        },
    },
}

# API配置
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_BASE_URL = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com')
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash-exp-image-generation')

# 代理配置已移除

USE_OPENAI_OCR = os.getenv('USE_OPENAI_OCR', 'False').lower() == 'true'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
OPENAI_MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4-vision-preview')

# 超时配置
API_TIMEOUT_SECONDS = int(os.getenv('API_TIMEOUT_SECONDS', '30'))
OCR_TIMEOUT_SECONDS = int(os.getenv('OCR_TIMEOUT_SECONDS', '60'))
IMAGE_PROCESSING_TIMEOUT_SECONDS = int(os.getenv('IMAGE_PROCESSING_TIMEOUT_SECONDS', '120'))

# GitHub集成配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')

# 微信CSV工具配置
WECHAT_CSV_PASSWORD = os.getenv('WECHAT_CSV_PASSWORD', '123456')
WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT = int(os.getenv('WECHAT_CSV_LOGIN_ATTEMPTS_LIMIT', '3'))
WECHAT_CSV_LOCKOUT_HOURS = int(os.getenv('WECHAT_CSV_LOCKOUT_HOURS', '24'))

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
}

# 创建日志目录
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
