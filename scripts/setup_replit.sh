#!/bin/bash

# Replit环境完整部署脚本
# 包含依赖安装、数据库迁移、超级用户创建等

set -e  # 遇到错误时退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 检查是否为首次运行
SETUP_MARKER="$PROJECT_ROOT/.replit_setup_complete"

# 检查环境
check_environment() {
    log_info "检查Replit环境..."
    
    # 检查Python版本
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_info "Python版本: $PYTHON_VERSION"
    
    # 检查uv是否可用
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version 2>&1 | cut -d' ' -f2)
        log_info "uv版本: $UV_VERSION"
    else
        log_error "uv包管理器未找到"
        exit 1
    fi
    
    # 设置工作目录
    cd "$PROJECT_ROOT"
    log_info "工作目录: $(pwd)"
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖..."
    
    cd "$PROJECT_ROOT"
    
    # 使用uv同步依赖
    if [[ -f "pyproject.toml" ]]; then
        log_info "使用uv同步依赖..."
        uv sync --all-extras
        log_success "Python依赖安装完成"
    else
        log_error "未找到pyproject.toml文件"
        exit 1
    fi
}

# 配置系统依赖
configure_system_dependencies() {
    log_info "配置系统依赖..."
    log_info "DEBUG: 当前工作目录: $(pwd)"
    log_info "DEBUG: 脚本目录: $SCRIPT_DIR"
    log_info "DEBUG: 项目根目录: $PROJECT_ROOT"

    # 检查是否需要配置系统依赖
    if [[ -f "$SETUP_MARKER" ]]; then
        log_info "系统依赖已配置，跳过..."
        log_info "DEBUG: 设置标记文件存在: $SETUP_MARKER"
        return 0
    fi

    # 验证Nix依赖
    log_info "验证Nix依赖安装状态..."
    local missing_deps=()
    local available_deps=()

    # 检查LibreOffice
    if command -v libreoffice &> /dev/null; then
        available_deps+=("libreoffice-fresh")
        log_info "DEBUG: LibreOffice路径: $(which libreoffice)"
        log_info "DEBUG: LibreOffice版本: $(libreoffice --version 2>/dev/null | head -n1 || echo '获取版本失败')"
    else
        missing_deps+=("libreoffice-fresh")
        log_error "DEBUG: LibreOffice命令未找到"
    fi

    # 检查图像处理工具
    if command -v convert &> /dev/null; then
        available_deps+=("imagemagick")
        log_info "DEBUG: ImageMagick路径: $(which convert)"
    else
        missing_deps+=("imagemagick")
        log_error "DEBUG: ImageMagick命令未找到"
    fi

    # 检查OCR工具
    if command -v tesseract &> /dev/null; then
        available_deps+=("tesseract")
        log_info "DEBUG: Tesseract路径: $(which tesseract)"
        log_info "DEBUG: Tesseract版本: $(tesseract --version 2>&1 | head -n1 || echo '获取版本失败')"
    else
        missing_deps+=("tesseract")
        log_error "DEBUG: Tesseract命令未找到"
    fi

    # 检查PDF工具
    if command -v pdfinfo &> /dev/null; then
        available_deps+=("poppler_utils")
        log_info "DEBUG: Poppler工具路径: $(which pdfinfo)"
    else
        missing_deps+=("poppler_utils")
        log_error "DEBUG: Poppler工具未找到"
    fi

    # 检查文件类型检测
    if command -v file &> /dev/null; then
        available_deps+=("file")
        log_info "DEBUG: file命令路径: $(which file)"
    else
        missing_deps+=("file")
        log_error "DEBUG: file命令未找到"
    fi

    # 检查字体配置
    if command -v fc-list &> /dev/null; then
        available_deps+=("fontconfig")
        log_info "DEBUG: fontconfig路径: $(which fc-list)"
        log_info "DEBUG: 系统字体数量: $(fc-list 2>/dev/null | wc -l || echo '0')"
    else
        missing_deps+=("fontconfig")
        log_error "DEBUG: fontconfig命令未找到"
    fi

    # 虚拟显示不再需要 - LibreOffice 7.6+ 支持真正headless模式
    available_deps+=("headless-mode")
    log_info "DEBUG: LibreOffice headless模式 - 无需虚拟显示"

    # 检查图像处理工具
    if command -v convert &> /dev/null; then
        available_deps+=("imagemagick")
        log_info "DEBUG: ImageMagick路径: $(which convert)"
        log_info "DEBUG: ImageMagick版本: $(convert --version 2>/dev/null | head -n1 || echo '获取版本失败')"
    else
        missing_deps+=("imagemagick")
        log_error "DEBUG: ImageMagick命令未找到"
    fi

    # 检查OCR工具
    if command -v tesseract &> /dev/null; then
        available_deps+=("tesseract4")
        log_info "DEBUG: Tesseract路径: $(which tesseract)"
        log_info "DEBUG: Tesseract版本: $(tesseract --version 2>&1 | head -n1 || echo '获取版本失败')"
    else
        missing_deps+=("tesseract4")
        log_error "DEBUG: Tesseract命令未找到"
    fi

    # 检查PDF工具
    if command -v pdfinfo &> /dev/null; then
        available_deps+=("poppler-utils")
        log_info "DEBUG: Poppler工具路径: $(which pdfinfo)"
        log_info "DEBUG: Poppler版本: $(pdfinfo -v 2>&1 | head -n1 || echo '获取版本失败')"
    else
        missing_deps+=("poppler-utils")
        log_error "DEBUG: Poppler工具未找到"
    fi

    # 检查文件类型检测
    if command -v file &> /dev/null; then
        available_deps+=("file")
        log_info "DEBUG: file命令路径: $(which file)"
        log_info "DEBUG: file版本: $(file --version 2>/dev/null | head -n1 || echo '获取版本失败')"
    else
        missing_deps+=("file")
        log_error "DEBUG: file命令未找到"
    fi

    log_info "DEBUG: 可用依赖 (${#available_deps[@]}): ${available_deps[*]}"

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "以下Nix依赖缺失 (${#missing_deps[@]}): ${missing_deps[*]}"
        log_error "请在replit.nix中添加这些依赖包，然后重新启动Repl"
        log_info "DEBUG: 当前replit.nix内容预览:"
        if [[ -f "$PROJECT_ROOT/replit.nix" ]]; then
            head -20 "$PROJECT_ROOT/replit.nix" | while read line; do
                log_info "DEBUG:   $line"
            done
        else
            log_error "DEBUG: replit.nix文件不存在"
        fi
        return 1
    fi

    log_success "所有Nix依赖验证通过"

    # 配置LibreOffice
    local libreoffice_script="$SCRIPT_DIR/install_libreoffice_replit.sh"
    log_info "DEBUG: 检查LibreOffice配置脚本: $libreoffice_script"
    if [[ -f "$libreoffice_script" ]]; then
        log_info "配置LibreOffice环境..."
        log_info "DEBUG: 执行LibreOffice配置脚本"
        chmod +x "$libreoffice_script" 2>/dev/null || true
        if "$libreoffice_script"; then
            log_success "DEBUG: LibreOffice配置脚本执行成功"
        else
            log_error "DEBUG: LibreOffice配置脚本执行失败，返回码: $?"
            return 1
        fi
    else
        log_warning "LibreOffice配置脚本未找到: $libreoffice_script"
    fi

    # 配置字体
    local fonts_script="$SCRIPT_DIR/install_fonts_replit.sh"
    log_info "DEBUG: 检查字体配置脚本: $fonts_script"
    if [[ -f "$fonts_script" ]]; then
        log_info "配置字体文件..."
        log_info "DEBUG: 执行字体配置脚本"
        chmod +x "$fonts_script" 2>/dev/null || true
        if "$fonts_script"; then
            log_success "DEBUG: 字体配置脚本执行成功"
        else
            log_error "DEBUG: 字体配置脚本执行失败，返回码: $?"
            return 1
        fi
    else
        log_warning "字体配置脚本未找到: $fonts_script"
    fi
}

# 设置环境变量
setup_environment_variables() {
    log_info "设置环境变量..."
    
    # 加载字体环境变量
    if [[ -f "$PROJECT_ROOT/.env.fonts" ]]; then
        source "$PROJECT_ROOT/.env.fonts"
        log_info "已加载字体环境变量"
    fi
    
    # 加载LibreOffice环境变量
    if [[ -f "$PROJECT_ROOT/.env.libreoffice" ]]; then
        source "$PROJECT_ROOT/.env.libreoffice"
        log_info "已加载LibreOffice环境变量"
    fi
    
    # 设置Django环境变量
    export DJANGO_SETTINGS_MODULE="config.settings.replit"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    
    log_success "环境变量设置完成"
}

# 启动LibreOffice服务
start_libreoffice_service() {
    log_info "启动LibreOffice服务..."
    
    # 启动虚拟显示
    if ! pgrep -x "Xvfb" > /dev/null; then
        log_info "启动虚拟显示..."
        Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &
        export DISPLAY=:99
        sleep 2
    fi
    
    # 启动LibreOffice服务
    if ! pgrep -f "soffice.*headless" > /dev/null; then
        log_info "启动LibreOffice后台服务..."
        libreoffice --headless --accept="socket,host=127.0.0.1,port=2002;urp;" --nofirststartwizard &
        sleep 3
    fi
    
    log_success "LibreOffice服务已启动"
}

# 数据库迁移
run_database_migrations() {
    log_info "运行数据库迁移..."
    
    cd "$PROJECT_ROOT"
    
    # 检查数据库连接
    if python manage.py check --database default; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        exit 1
    fi
    
    # 运行迁移
    python manage.py makemigrations
    python manage.py migrate
    
    log_success "数据库迁移完成"
}

# 创建超级用户
create_superuser() {
    log_info "创建超级用户..."
    
    cd "$PROJECT_ROOT"
    
    # 检查是否已存在admin用户
    if python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(username='admin').exists())" | grep -q "True"; then
        log_warning "超级用户admin已存在，跳过创建"
        return 0
    fi
    
    # 创建超级用户
    python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('超级用户admin创建成功')
else:
    print('超级用户admin已存在')
"
    
    log_success "超级用户创建完成"
    log_info "用户名: admin"
    log_info "密码: admin123"
}

# 收集静态文件
collect_static_files() {
    log_info "收集静态文件..."
    
    cd "$PROJECT_ROOT"
    
    # 收集静态文件
    python manage.py collectstatic --noinput
    
    log_success "静态文件收集完成"
}

# 验证安装
verify_installation() {
    log_info "验证安装..."
    
    cd "$PROJECT_ROOT"
    
    # 检查Django配置
    if python manage.py check; then
        log_success "Django配置检查通过"
    else
        log_error "Django配置检查失败"
        exit 1
    fi
    
    # 检查字体安装
    if fc-list | grep -qi "SimSun\|Arial\|Calibri"; then
        log_success "字体安装验证通过"
    else
        log_warning "字体安装可能有问题"
    fi
    
    # 检查LibreOffice
    if command -v libreoffice &> /dev/null; then
        log_success "LibreOffice安装验证通过"
    else
        log_warning "LibreOffice未正确安装"
    fi
    
    log_success "安装验证完成"
}

# 标记安装完成
mark_setup_complete() {
    echo "$(date): Replit setup completed successfully" > "$SETUP_MARKER"
    log_success "安装标记已创建"
}

# 显示启动信息
show_startup_info() {
    log_success "🎉 Replit环境部署完成！"
    echo ""
    log_info "📋 部署信息:"
    log_info "  • Django设置: config.settings.replit"
    log_info "  • 超级用户: admin / admin123"
    log_info "  • 管理后台: /admin/"
    log_info "  • API文档: /api/docs/"
    echo ""
    log_info "🔧 环境变量配置:"
    log_info "  • DATABASE_URL: PostgreSQL连接字符串"
    log_info "  • SECRET_KEY: Django密钥"
    log_info "  • DEBUG: 调试模式 (True/False)"
    echo ""
    log_info "🚀 服务器即将启动..."
}

# 主函数
main() {
    log_info "开始Replit环境部署..."
    
    # 检查环境
    check_environment
    
    # 安装Python依赖
    install_python_dependencies

    # 配置系统依赖（仅首次运行）
    configure_system_dependencies
    
    # 设置环境变量
    setup_environment_variables
    
    # 启动LibreOffice服务
    start_libreoffice_service
    
    # 数据库迁移
    run_database_migrations
    
    # 创建超级用户
    create_superuser
    
    # 收集静态文件
    collect_static_files
    
    # 验证安装
    verify_installation
    
    # 标记安装完成
    mark_setup_complete
    
    # 显示启动信息
    show_startup_info
}

# 执行主函数
main "$@"
