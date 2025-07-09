#!/bin/bash

# Replit构建脚本 - 移植自setup_replit.sh的构建部分
# 包含所有耗时的配置工作，但不启动服务器

# 导入原始脚本的所有函数和变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 直接调用原始脚本，但修改其行为
log_info "🔨 开始Replit构建阶段..."
log_info "调用原始setup_replit.sh脚本进行构建..."

# 确保脚本有执行权限
chmod +x "$SCRIPT_DIR/setup_replit.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

# 设置环境变量标记这是构建阶段
export REPLIT_BUILD_PHASE=1

# 调用原始脚本
if [ -f "$SCRIPT_DIR/setup_replit.sh" ]; then
    "$SCRIPT_DIR/setup_replit.sh"
else
    log_error "setup_replit.sh 文件不存在"
    exit 1
fi

log_success "🎉 构建阶段完成！"
log_info "✅ 准备启动服务器..."

# 构建脚本执行完成
