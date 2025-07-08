#!/bin/bash

# Replit部署专用启动脚本
set -e

echo "[INFO] 开始Replit部署启动..."

# 设置环境变量
export DJANGO_SETTINGS_MODULE=config.settings.replit
export PYTHONPATH="."
export PYTHONUNBUFFERED=1
export REPL_DEPLOYMENT=1

# 检查端口是否被占用
if lsof -i :8000 >/dev/null 2>&1; then
    echo "[WARNING] 端口8000已被占用，尝试终止..."
    pkill -f "gunicorn\|runserver" || true
    sleep 1
fi

echo "[INFO] 部署模式启动gunicorn..."
echo "[INFO] 绑定地址: 0.0.0.0:8000"
echo "[INFO] Workers: 1 (部署优化)"
echo "[INFO] 超时: 120秒 (快速响应)"

# 等待一下确保端口释放
sleep 1

# 启动gunicorn - 部署优化配置
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --worker-class sync \
    --timeout 120 \
    --graceful-timeout 15 \
    --keep-alive 2 \
    --max-requests 200 \
    --max-requests-jitter 20 \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output
