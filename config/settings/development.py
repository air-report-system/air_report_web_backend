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
_static_candidate_dirs = [
    BASE_DIR / 'static',
]
STATICFILES_DIRS = [p for p in _static_candidate_dirs if p.exists()]

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

# 开发环境 Channels：不依赖 Redis，避免本机未启动 Redis 导致 WebSocket 订阅/广播失败
# 注意：InMemoryChannelLayer 仅适用于单进程开发调试，不支持多进程/多实例部署的跨进程消息。
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# 开发环境Celery设置
CELERY_TASK_ALWAYS_EAGER = True  # 同步执行任务，便于调试
CELERY_TASK_EAGER_PROPAGATES = True
