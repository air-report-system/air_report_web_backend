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

# 导入原始脚本的所有函数（除了main函数）
source "$SCRIPT_DIR/setup_replit.sh"

# 重新定义main函数，只包含构建步骤
main() {
    log_info "🔨 开始Replit构建阶段..."

    # 检查环境
    check_environment

    # 安装Python依赖
    install_python_dependencies

    # 配置系统依赖（仅首次运行）
    configure_system_dependencies

    # 安装字体
    install_fonts

    # 跳过LibreOffice服务启动（构建阶段不需要）
    log_info "跳过LibreOffice服务启动（将在运行阶段按需启动）"

    # 设置环境变量
    setup_environment_variables

    # 数据库迁移
    run_database_migrations

    # 创建超级用户
    create_superuser

    # 收集静态文件
    collect_static_files

    # 简化验证安装
    verify_installation_quick

    # 标记安装完成
    mark_setup_complete

    # 准备启动服务器（但不实际启动）
    prepare_server_startup

    # 显示构建完成信息
    log_success "🎉 构建阶段完成！"
    log_info "📋 构建信息:"
    log_info "• Django设置: config.settings.replit"
    log_info "• 超级用户: admin / admin123"
    log_info "• 管理后台: /admin/"
    log_info "• API文档: /api/docs/"
    log_info "• 字体支持: 中文/英文字体已安装"
    log_info "✅ 准备启动服务器..."
}

# 执行主函数
main "$@"
