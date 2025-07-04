"""
开发环境设置
"""
from .base import *

# 开发环境特定设置
DEBUG = True

# 允许所有主机（仅开发环境）
ALLOWED_HOSTS = ['*']

# 开发环境数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 开发环境CORS设置
CORS_ALLOW_ALL_ORIGINS = True

# 开发环境静态文件设置
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# 开发环境日志设置
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['root']['level'] = 'DEBUG'

# Django Debug Toolbar（如果需要）
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
    except ImportError:
        pass

# 开发环境邮件后端
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 开发环境缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# 开发环境Celery设置
CELERY_TASK_ALWAYS_EAGER = True  # 同步执行任务，便于调试
CELERY_TASK_EAGER_PROPAGATES = True
