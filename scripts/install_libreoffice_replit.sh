#!/bin/bash

# Replit环境LibreOffice配置脚本
# 专为Replit环境优化的LibreOffice配置和验证
# 注意：在Replit中，系统依赖应通过replit.nix文件管理，而不是apt-get

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

    if [[ -n "$REPL_ID" ]] || [[ -n "$REPLIT_DEV_DOMAIN" ]] || [[ -n "$REPL_SLUG" ]]; then
        log_success "检测到Replit环境"
        return 0
    else
        log_warning "未检测到Replit环境，继续配置..."
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

# 检查Nix依赖是否已安装
check_nix_dependencies() {
    log_info "检查Nix依赖安装状态..."
    log_info "DEBUG: 当前PATH: $PATH"
    log_info "DEBUG: 当前用户: $(whoami)"
    log_info "DEBUG: 系统信息: $(uname -a)"

    local missing_deps=()
    local available_deps=()

    # 检查LibreOffice
    log_info "DEBUG: 检查LibreOffice..."
    if command -v libreoffice &> /dev/null; then
        available_deps+=("libreoffice")
        local lo_path=$(which libreoffice)
        local lo_real_path=$(readlink -f "$lo_path" 2>/dev/null || echo "$lo_path")
        log_info "DEBUG: LibreOffice路径: $lo_path -> $lo_real_path"
        log_info "DEBUG: LibreOffice版本: $(libreoffice --version 2>/dev/null | head -n1 || echo '获取失败')"
    else
        missing_deps+=("libreoffice")
        log_error "DEBUG: LibreOffice命令未找到"
    fi

    # 检查字体配置
    log_info "DEBUG: 检查fontconfig..."
    if command -v fc-list &> /dev/null; then
        available_deps+=("fontconfig")
        local fc_path=$(which fc-list)
        log_info "DEBUG: fc-list路径: $fc_path"
        local font_count=$(fc-list 2>/dev/null | wc -l || echo "0")
        log_info "DEBUG: 系统字体数量: $font_count"
    else
        missing_deps+=("fontconfig")
        log_error "DEBUG: fontconfig命令未找到"
    fi

    # 虚拟显示不再需要 - 现代LibreOffice支持真正的headless模式
    log_info "DEBUG: 跳过虚拟显示检查 - LibreOffice 7.6+ 支持真正的headless模式"
    available_deps+=("headless-mode")

    log_info "DEBUG: 可用依赖 (${#available_deps[@]}): ${available_deps[*]}"
    log_info "DEBUG: 缺失依赖 (${#missing_deps[@]}): ${missing_deps[*]}"

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "以下依赖未通过Nix安装: ${missing_deps[*]}"
        log_error "请确保replit.nix文件包含所有必要的依赖包"
        log_info "建议的replit.nix配置:"
        log_info "  pkgs.libreoffice-fresh"
        log_info "  pkgs.fontconfig"
        log_info "  pkgs.dejavu_fonts"
        log_info "  pkgs.liberation_ttf"
        log_info "  pkgs.noto-fonts-cjk-sans"
        log_info "  # pkgs.xvfb-run  # 不再需要 - LibreOffice 7.6+ 支持真正headless"
        log_info "  pkgs.imagemagick"
        log_info "  pkgs.tesseract4"
        log_info "  pkgs.poppler-utils"

        # 检查Nix store
        log_info "DEBUG: 检查Nix store中的相关包..."
        if [[ -d "/nix/store" ]]; then
            local nix_packages=$(find /nix/store -maxdepth 1 -name "*libreoffice*" 2>/dev/null | wc -l)
            log_info "DEBUG: Nix store中LibreOffice相关包数量: $nix_packages"
            if [[ $nix_packages -gt 0 ]]; then
                log_info "DEBUG: LibreOffice包列表:"
                find /nix/store -maxdepth 1 -name "*libreoffice*" 2>/dev/null | head -5 | while read pkg; do
                    log_info "DEBUG:   $(basename "$pkg")"
                done
            fi
        else
            log_warning "DEBUG: /nix/store目录不存在"
        fi

        return 1
    else
        log_success "所有Nix依赖已正确安装"
        return 0
    fi
}

# 验证LibreOffice安装
verify_libreoffice_installation() {
    log_info "验证LibreOffice安装..."

    if command -v libreoffice &> /dev/null; then
        local version=$(libreoffice --version 2>/dev/null | head -n1 || echo "未知版本")
        log_success "LibreOffice已安装: $version"
        return 0
    else
        log_error "LibreOffice未安装或不可用"
        return 1
    fi
}

# 配置LibreOffice环境
configure_libreoffice() {
    log_info "配置LibreOffice环境..."
    log_info "DEBUG: 开始LibreOffice环境配置"

    # 创建LibreOffice配置目录
    LIBREOFFICE_CONFIG_DIR="$HOME/.config/libreoffice"
    log_info "DEBUG: 创建配置目录: $LIBREOFFICE_CONFIG_DIR"
    mkdir -p "$LIBREOFFICE_CONFIG_DIR"

    # 检测LibreOffice安装路径（Nix环境）
    local libreoffice_path=""
    if command -v libreoffice &> /dev/null; then
        local libreoffice_cmd=$(which libreoffice)
        log_info "DEBUG: LibreOffice命令路径: $libreoffice_cmd"

        local libreoffice_real=$(readlink -f "$libreoffice_cmd" 2>/dev/null || echo "$libreoffice_cmd")
        log_info "DEBUG: LibreOffice真实路径: $libreoffice_real"

        libreoffice_path=$(dirname $(dirname "$libreoffice_real"))
        log_info "DEBUG: 检测到LibreOffice安装路径: $libreoffice_path"

        # 列出LibreOffice目录内容
        if [[ -d "$libreoffice_path" ]]; then
            log_info "DEBUG: LibreOffice目录内容:"
            ls -la "$libreoffice_path" 2>/dev/null | head -10 | while read line; do
                log_info "DEBUG:   $line"
            done
        fi
    else
        log_error "DEBUG: 无法检测LibreOffice安装路径，命令不存在"
        return 1
    fi

    # 查找UNO路径
    local uno_path=""
    local search_paths=(
        "$libreoffice_path/program"
        "$libreoffice_path/lib/libreoffice/program"
        "$libreoffice_path/lib/program"
    )

    log_info "DEBUG: 搜索UNO路径..."
    for path in "${search_paths[@]}"; do
        log_info "DEBUG: 检查路径: $path"
        if [[ -d "$path" ]]; then
            uno_path="$path"
            log_info "DEBUG: 找到UNO路径: $uno_path"
            break
        fi
    done

    # 如果还没找到，在Nix store中搜索
    if [[ -z "$uno_path" ]]; then
        log_info "DEBUG: 在Nix store中搜索UNO路径..."
        if [[ -d "/nix/store" ]]; then
            uno_path=$(find /nix/store -name "program" -path "*/libreoffice*/program" 2>/dev/null | head -n1)
            if [[ -n "$uno_path" ]]; then
                log_info "DEBUG: 在Nix store中找到UNO路径: $uno_path"
            else
                log_warning "DEBUG: 在Nix store中未找到UNO路径"
            fi
        fi
    fi

    if [[ -z "$uno_path" ]]; then
        log_warning "无法自动检测UNO路径，使用默认配置"
        uno_path="/usr/lib/libreoffice/program"
        log_info "DEBUG: 使用默认UNO路径: $uno_path"
    fi

    # 验证UNO路径
    if [[ -d "$uno_path" ]]; then
        log_success "UNO路径验证通过: $uno_path"
        log_info "DEBUG: UNO目录内容:"
        ls -la "$uno_path" 2>/dev/null | head -5 | while read line; do
            log_info "DEBUG:   $line"
        done
    else
        log_warning "UNO路径不存在，但继续配置: $uno_path"
    fi

    # 设置LibreOffice环境变量
    export UNO_PATH="$uno_path"
    export PYTHONPATH="$uno_path:$PYTHONPATH"
    export OFFICE_HOME="$(dirname "$uno_path")"

    log_info "DEBUG: 设置环境变量:"
    log_info "DEBUG:   UNO_PATH=$UNO_PATH"
    log_info "DEBUG:   OFFICE_HOME=$OFFICE_HOME"
    log_info "DEBUG:   PYTHONPATH前缀: $uno_path"

    # 创建环境变量文件
    ENV_FILE="$(dirname "$0")/../.env.libreoffice"
    log_info "DEBUG: 创建环境变量文件: $ENV_FILE"

    cat > "$ENV_FILE" << EOF
# LibreOffice环境变量 (Replit/Nix环境)
# 生成时间: $(date)
export UNO_PATH="$uno_path"
export PYTHONPATH="$uno_path:\$PYTHONPATH"
export OFFICE_HOME="$(dirname "$uno_path")"
# export DISPLAY=:99  # 不再需要 - LibreOffice支持真正headless模式

# 字体配置
export FONTCONFIG_PATH=/etc/fonts
export FONTCONFIG_FILE=/etc/fonts/fonts.conf

# 调试信息
# LibreOffice命令: $(which libreoffice 2>/dev/null || echo '未找到')
# LibreOffice版本: $(libreoffice --version 2>/dev/null | head -n1 || echo '未知')
# 配置时间: $(date)
EOF

    if [[ -f "$ENV_FILE" ]]; then
        log_success "LibreOffice环境配置完成"
        log_info "环境变量文件: $ENV_FILE"
        log_info "DEBUG: 环境变量文件内容:"
        cat "$ENV_FILE" | while read line; do
            log_info "DEBUG:   $line"
        done
    else
        log_error "DEBUG: 环境变量文件创建失败"
        return 1
    fi
}

# 启动虚拟显示
setup_virtual_display() {
    log_info "设置虚拟显示..."

    # LibreOffice 7.6+ 支持真正的headless模式，不需要Xvfb
    log_info "DEBUG: LibreOffice headless模式 - 无需虚拟显示"
    log_info "DEBUG: 跳过虚拟显示检查 - LibreOffice 7.6+ 支持真正的headless模式"

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

# 启动虚拟显示 - LibreOffice 7.6+ 支持真正headless模式，跳过Xvfb
echo "LibreOffice headless模式 - 无需虚拟显示"

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
    log_info "开始配置LibreOffice环境..."

    # 检查环境
    check_replit_environment
    check_system_architecture

    # 检查Nix依赖
    if ! check_nix_dependencies; then
        log_error "Nix依赖检查失败，请检查replit.nix配置"
        exit 1
    fi

    # 验证LibreOffice安装
    if ! verify_libreoffice_installation; then
        log_error "LibreOffice验证失败"
        exit 1
    fi

    # 配置环境
    configure_libreoffice

    # 设置虚拟显示
    setup_virtual_display

    # 测试安装
    test_libreoffice

    # 创建启动脚本
    create_startup_script

    log_success "LibreOffice环境配置完成！"
    log_info "LibreOffice版本: $(libreoffice --version 2>/dev/null || echo '未知')"
    log_info "环境变量文件: $(dirname "$0")/../.env.libreoffice"
    log_info "启动脚本: $(dirname "$0")/start_libreoffice.sh"
    log_info ""
    log_info "注意: 在Replit环境中，系统依赖通过replit.nix管理"
    log_info "如果遇到依赖问题，请检查replit.nix文件配置"
}

# 执行主函数
main "$@"
