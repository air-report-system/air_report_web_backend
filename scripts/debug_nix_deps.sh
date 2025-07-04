#!/bin/bash

# Nix依赖调试脚本
# 用于逐步测试和添加依赖

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

# 检查当前可用的命令
check_available_commands() {
    log_info "检查当前环境中可用的命令..."

    local commands=(
        "python3:Python解释器"
        "libreoffice:LibreOffice"
        "soffice:LibreOffice(备用)"
        "fc-list:字体配置"
        "Xvfb:虚拟显示"
        "convert:ImageMagick"
        "tesseract:OCR引擎"
        "pdfinfo:PDF工具"
        "file:文件类型检测"
        "psql:PostgreSQL客户端"
    )

    local available=0
    local total=${#commands[@]}

    for cmd_info in "${commands[@]}"; do
        local cmd=$(echo "$cmd_info" | cut -d':' -f1)
        local desc=$(echo "$cmd_info" | cut -d':' -f2)

        if command -v "$cmd" &> /dev/null; then
            local cmd_path=$(which "$cmd" 2>/dev/null || echo "路径获取失败")
            log_success "$desc: $cmd_path"
            available=$((available + 1))
        else
            log_warning "$desc: 未找到"
        fi
    done

    log_info "可用命令: $available/$total"
    echo ""
}

# 显示当前replit.nix内容
show_current_config() {
    log_info "当前replit.nix配置:"
    if [[ -f "replit.nix" ]]; then
        cat replit.nix | while read line; do
            echo "  $line"
        done
    else
        log_error "replit.nix文件不存在"
    fi
    echo ""
}

# 建议的依赖添加顺序
suggest_dependency_order() {
    log_info "建议的依赖添加顺序:"
    echo ""
    
    log_info "第1步 - 基础环境 (当前配置):"
    echo "  pkgs.python3"
    echo "  pkgs.curl"
    echo "  pkgs.wget"
    echo "  pkgs.git"
    echo ""
    
    log_info "第2步 - 添加LibreOffice:"
    echo "  pkgs.libreoffice  # 或 pkgs.libreoffice-fresh"
    echo ""
    
    log_info "第3步 - 添加字体支持:"
    echo "  pkgs.fontconfig"
    echo "  pkgs.dejavu_fonts"
    echo ""
    
    log_info "第4步 - 添加虚拟显示:"
    echo "  pkgs.xvfb-run"
    echo ""
    
    log_info "第5步 - 添加图像处理:"
    echo "  pkgs.imagemagick"
    echo ""
    
    log_info "第6步 - 添加OCR支持:"
    echo "  pkgs.tesseract  # 或 pkgs.tesseract4"
    echo ""
    
    log_info "第7步 - 添加PDF工具:"
    echo "  pkgs.poppler-utils"
    echo ""
    
    log_info "第8步 - 添加数据库:"
    echo "  pkgs.postgresql"
    echo ""
    
    log_info "每次添加后重启Repl测试是否能成功构建"
}

# 生成下一步配置建议
generate_next_config() {
    local step=${1:-2}
    
    log_info "生成第${step}步配置建议:"
    echo ""
    
    case $step in
        2)
            cat << 'EOF'
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.curl
    pkgs.wget
    pkgs.git
    pkgs.libreoffice
  ];
}
EOF
            ;;
        3)
            cat << 'EOF'
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.curl
    pkgs.wget
    pkgs.git
    pkgs.libreoffice
    pkgs.fontconfig
    pkgs.dejavu_fonts
  ];
}
EOF
            ;;
        4)
            cat << 'EOF'
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.curl
    pkgs.wget
    pkgs.git
    pkgs.libreoffice
    pkgs.fontconfig
    pkgs.dejavu_fonts
    pkgs.xvfb-run
  ];
}
EOF
            ;;
        *)
            log_warning "步骤 $step 的配置请参考建议顺序"
            ;;
    esac
    echo ""
}

# 主函数
main() {
    log_info "Nix依赖调试工具"
    log_info "DEBUG: 脚本开始执行"
    echo ""

    # 检查可用命令
    log_info "DEBUG: 开始检查可用命令"
    check_available_commands
    log_info "DEBUG: 命令检查完成"

    # 显示当前配置
    log_info "DEBUG: 开始显示当前配置"
    show_current_config
    log_info "DEBUG: 配置显示完成"

    # 显示建议
    log_info "DEBUG: 开始显示建议"
    suggest_dependency_order
    log_info "DEBUG: 建议显示完成"

    # 生成下一步配置
    if [[ $# -gt 0 ]]; then
        log_info "DEBUG: 生成第$1步配置"
        generate_next_config "$1"
    else
        log_info "使用方法: $0 [步骤号]"
        log_info "例如: $0 2  # 生成第2步配置"
    fi

    log_info "DEBUG: 脚本执行完成"
}

main "$@"
