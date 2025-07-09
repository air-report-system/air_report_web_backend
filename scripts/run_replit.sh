#!/bin/bash

# Replit运行脚本 - 仅启动服务器
# 假设构建阶段已经完成所有配置

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[RUN]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[RUN]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[RUN]${NC} $1"
}

log_error() {
    echo -e "${RED}[RUN]${NC} $1"
}

log_info "🚀 开始Replit运行阶段..."

# 设置基本环境变量
export DJANGO_SETTINGS_MODULE=config.settings.replit
export PYTHONPATH="."
export PYTHONUNBUFFERED=1

# 检查构建是否完成
if [ ! -f ".replit_setup_complete" ]; then
    log_warning "构建标记文件不存在，可能构建未完成"
fi

# 加载环境变量（从原始脚本的逻辑）
log_info "加载环境变量..."
if [ -f ".env.fonts" ]; then
    source .env.fonts
    log_info "已加载字体环境变量"
fi

if [ -f ".env.libreoffice" ]; then
    source .env.libreoffice
    log_info "已加载LibreOffice环境变量"
fi

# 清理可能占用的端口
if command -v lsof >/dev/null 2>&1 && lsof -i :8000 >/dev/null 2>&1; then
    log_info "清理端口8000..."
    pkill -f "gunicorn\|runserver" || true
    sleep 1
fi

log_info "启动Gunicorn服务器..."
log_info "• 绑定地址: 0.0.0.0:8000"
log_info "• Workers: 2"
log_info "• 超时: 60秒"
log_info "• 模式: 快速启动优化"

# 启动Gunicorn - 2个worker，快速启动配置
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --worker-class sync \
    --timeout 60 \
    --graceful-timeout 10 \
    --keep-alive 2 \
    --max-requests 200 \
    --max-requests-jitter 20 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
