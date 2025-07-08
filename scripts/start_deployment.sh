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

echo "[INFO] 部署模式启动Django runserver..."
echo "[INFO] 绑定地址: 0.0.0.0:8000"
echo "[INFO] 使用runserver (Replit部署优化)"

# 等待一下确保端口释放
sleep 1

# 启动Django runserver - 在Replit部署中更稳定
exec python manage.py runserver 0.0.0.0:8000 --settings=config.settings.replit
