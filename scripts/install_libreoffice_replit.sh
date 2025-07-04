#!/bin/bash

# Replit环境LibreOffice安装脚本
# 专为Replit环境优化的LibreOffice和PDF依赖安装

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

# 检查Replit环境
check_replit_environment() {
    log_info "检查Replit环境..."
    
    if [[ -n "$REPL_ID" ]] || [[ -n "$REPLIT_DEV_DOMAIN" ]]; then
        log_success "检测到Replit环境"
        return 0
    else
        log_warning "未检测到Replit环境，继续安装..."
        return 1
    fi
}

# 检查系统架构
check_system_architecture() {
    log_info "检查系统架构..."
    
    ARCH=$(uname -m)
    OS=$(uname -s)
    
    log_info "系统: $OS"
    log_info "架构: $ARCH"
    
    if [[ "$OS" != "Linux" ]]; then
        log_error "不支持的操作系统: $OS"
        exit 1
    fi
}

# 安装系统依赖
install_system_dependencies() {
    log_info "安装系统依赖..."
    
    # 更新包管理器
    if command -v apt-get &> /dev/null; then
        log_info "使用apt-get安装依赖..."
        
        # 更新包列表
        apt-get update -qq
        
        # 安装基础依赖
        apt-get install -y \
            wget \
            curl \
            gnupg \
            software-properties-common \
            fontconfig \
            libfontconfig1 \
            fonts-liberation \
            fonts-dejavu-core \
            fonts-freefont-ttf \
            xvfb \
            dbus-x11
            
        log_success "基础依赖安装完成"
    else
        log_error "未找到apt-get包管理器"
        exit 1
    fi
}

# 安装LibreOffice
install_libreoffice() {
    log_info "安装LibreOffice..."
    
    # 检查是否已安装
    if command -v libreoffice &> /dev/null; then
        log_warning "LibreOffice已安装，跳过安装步骤"
        return 0
    fi
    
    # 安装LibreOffice
    apt-get install -y \
        libreoffice \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress \
        libreoffice-draw \
        python3-uno
    
    log_success "LibreOffice安装完成"
}

# 安装unoconv
install_unoconv() {
    log_info "安装unoconv..."
    
    # 检查是否已安装
    if command -v unoconv &> /dev/null; then
        log_warning "unoconv已安装，跳过安装步骤"
        return 0
    fi
    
    # 安装unoconv
    apt-get install -y unoconv
    
    log_success "unoconv安装完成"
}

# 配置LibreOffice环境
configure_libreoffice() {
    log_info "配置LibreOffice环境..."
    
    # 创建LibreOffice配置目录
    LIBREOFFICE_CONFIG_DIR="$HOME/.config/libreoffice"
    mkdir -p "$LIBREOFFICE_CONFIG_DIR"
    
    # 设置LibreOffice环境变量
    export UNO_PATH=/usr/lib/libreoffice/program
    export PYTHONPATH=/usr/lib/python3/dist-packages:/usr/lib/libreoffice/program:$PYTHONPATH
    export OFFICE_HOME=/usr/lib/libreoffice
    
    # 创建环境变量文件
    ENV_FILE="$(dirname "$0")/../.env.libreoffice"
    cat > "$ENV_FILE" << EOF
# LibreOffice环境变量
export UNO_PATH=/usr/lib/libreoffice/program
export PYTHONPATH=/usr/lib/python3/dist-packages:/usr/lib/libreoffice/program:\$PYTHONPATH
export OFFICE_HOME=/usr/lib/libreoffice
export DISPLAY=:99
EOF
    
    log_success "LibreOffice环境配置完成"
    log_info "环境变量文件: $ENV_FILE"
}

# 启动虚拟显示
setup_virtual_display() {
    log_info "设置虚拟显示..."
    
    # 检查Xvfb是否运行
    if pgrep -x "Xvfb" > /dev/null; then
        log_warning "Xvfb已在运行"
        return 0
    fi
    
    # 启动虚拟显示
    Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &
    export DISPLAY=:99
    
    # 等待显示启动
    sleep 2
    
    log_success "虚拟显示设置完成"
}

# 测试LibreOffice安装
test_libreoffice() {
    log_info "测试LibreOffice安装..."
    
    # 创建临时测试文件
    TEST_DIR=$(mktemp -d)
    TEST_DOC="$TEST_DIR/test.odt"
    TEST_PDF="$TEST_DIR/test.pdf"
    
    # 创建简单的测试文档
    cat > "$TEST_DOC" << 'EOF'
测试文档

这是一个LibreOffice测试文档。
This is a LibreOffice test document.

测试中文字体显示效果。
Testing Chinese font display.
EOF
    
    # 测试LibreOffice转换
    log_info "测试LibreOffice PDF转换..."
    
    # 设置环境变量
    source "$(dirname "$0")/../.env.libreoffice" 2>/dev/null || true
    
    # 使用LibreOffice转换
    if libreoffice --headless --convert-to pdf --outdir "$TEST_DIR" "$TEST_DOC" 2>/dev/null; then
        if [[ -f "$TEST_PDF" ]]; then
            log_success "LibreOffice PDF转换测试成功"
        else
            log_warning "LibreOffice转换完成但PDF文件未生成"
        fi
    else
        log_warning "LibreOffice转换测试失败"
    fi
    
    # 测试unoconv转换
    if command -v unoconv &> /dev/null; then
        log_info "测试unoconv转换..."
        
        TEST_PDF_UNOCONV="$TEST_DIR/test_unoconv.pdf"
        
        if unoconv -f pdf -o "$TEST_PDF_UNOCONV" "$TEST_DOC" 2>/dev/null; then
            if [[ -f "$TEST_PDF_UNOCONV" ]]; then
                log_success "unoconv转换测试成功"
            else
                log_warning "unoconv转换完成但PDF文件未生成"
            fi
        else
            log_warning "unoconv转换测试失败"
        fi
    fi
    
    # 清理临时文件
    rm -rf "$TEST_DIR"
}

# 创建启动脚本
create_startup_script() {
    log_info "创建LibreOffice启动脚本..."
    
    STARTUP_SCRIPT="$(dirname "$0")/start_libreoffice.sh"
    
    cat > "$STARTUP_SCRIPT" << 'EOF'
#!/bin/bash

# LibreOffice启动脚本

# 设置环境变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env.libreoffice" 2>/dev/null || true

# 启动虚拟显示
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "启动虚拟显示..."
    Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &
    export DISPLAY=:99
    sleep 2
fi

# 启动LibreOffice服务
if ! pgrep -f "soffice.*headless" > /dev/null; then
    echo "启动LibreOffice服务..."
    libreoffice --headless --accept="socket,host=127.0.0.1,port=2002;urp;" --nofirststartwizard &
    sleep 3
fi

echo "LibreOffice服务已启动"
EOF
    
    chmod +x "$STARTUP_SCRIPT"
    
    log_success "LibreOffice启动脚本创建完成: $STARTUP_SCRIPT"
}

# 主函数
main() {
    log_info "开始安装LibreOffice和PDF依赖..."
    
    # 检查环境
    check_replit_environment
    check_system_architecture
    
    # 安装系统依赖
    install_system_dependencies
    
    # 安装LibreOffice
    install_libreoffice
    
    # 安装unoconv
    install_unoconv
    
    # 配置环境
    configure_libreoffice
    
    # 设置虚拟显示
    setup_virtual_display
    
    # 测试安装
    test_libreoffice
    
    # 创建启动脚本
    create_startup_script
    
    log_success "LibreOffice和PDF依赖安装完成！"
    log_info "LibreOffice版本: $(libreoffice --version 2>/dev/null || echo '未知')"
    log_info "unoconv版本: $(unoconv --version 2>/dev/null || echo '未知')"
    log_info "环境变量文件: $(dirname "$0")/../.env.libreoffice"
    log_info "启动脚本: $(dirname "$0")/start_libreoffice.sh"
}

# 执行主函数
main "$@"
