#!/bin/bash

# Replit启动脚本 - 确保端口正确绑定
set -e

echo "[INFO] 开始Replit应用启动..."

# 设置环境变量
export DJANGO_SETTINGS_MODULE=config.settings.replit
export PYTHONPATH="."
export PYTHONUNBUFFERED=1

# 检查端口是否被占用
if lsof -i :8000 >/dev/null 2>&1; then
    echo "[WARNING] 端口8000已被占用，尝试终止..."
    pkill -f "gunicorn\|runserver" || true
    sleep 2
fi

echo "[INFO] 启动gunicorn服务器..."
echo "[INFO] 绑定地址: 0.0.0.0:8000"

# 检测是否为部署模式
if [ "$REPL_DEPLOYMENT" = "1" ]; then
    echo "[INFO] 部署模式: 使用单worker配置"
    echo "[INFO] Workers: 1"
    echo "[INFO] 超时: 300秒"

    # 部署模式：单worker，更快启动
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 1 \
        --worker-class sync \
        --timeout 300 \
        --graceful-timeout 30 \
        --keep-alive 2 \
        --max-requests 500 \
        --max-requests-jitter 50 \
        --preload \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    echo "[INFO] 开发模式: 使用多worker配置"
    echo "[INFO] Workers: 2"
    echo "[INFO] 超时: 600秒"

    # 开发模式：多worker
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 2 \
        --worker-class sync \
        --timeout 600 \
        --keep-alive 2 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
        --access-logfile - \
        --error-logfile - \
        --log-level info
fi
