#!/bin/bash

# PDF依赖安装脚本
# 包含字体安装和配置功能

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到root用户，将直接安装系统依赖"
        return 0
    else
        log_info "非root用户，某些操作可能需要sudo权限"
        return 1
    fi
}

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi

    log_info "检测到操作系统: $OS $VERSION"
}

# 安装基础PDF依赖
install_pdf_dependencies() {
    log_info "开始安装PDF生成依赖..."

    case $OS in
        ubuntu|debian)
            log_info "更新包管理器..."
            sudo apt-get update

            log_info "安装unoconv和LibreOffice..."
            sudo apt-get install -y \
                unoconv \
                libreoffice \
                libreoffice-writer \
                fontconfig \
                fonts-liberation \
                fonts-dejavu-core \
                fonts-freefont-ttf \
                python3-uno
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi

            log_info "安装unoconv和LibreOffice..."
            sudo $PKG_MANAGER install -y \
                unoconv \
                libreoffice \
                libreoffice-writer \
                fontconfig \
                liberation-fonts \
                dejavu-fonts-common \
                gnu-free-fonts-common \
                python3-uno
            ;;
        *)
            log_warning "未识别的操作系统，请手动安装: unoconv, libreoffice, fontconfig"
            ;;
    esac

    log_success "PDF依赖安装完成"
}

# 安装字体文件
install_fonts() {
    log_info "开始安装字体文件..."

    # 获取脚本所在目录的绝对路径
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    FONTS_DIR="$SCRIPT_DIR/../templates/fonts"

    # 检查字体目录是否存在
    if [[ ! -d "$FONTS_DIR" ]]; then
        log_error "字体目录不存在: $FONTS_DIR"
        exit 1
    fi

    # 创建系统字体目录
    SYSTEM_FONTS_DIR="/usr/share/fonts/truetype/custom"
    sudo mkdir -p "$SYSTEM_FONTS_DIR"

    # 复制字体文件
    log_info "复制字体文件到系统目录..."
    sudo cp "$FONTS_DIR"/*.{ttf,ttc,otf,TTF,TTC,OTF} "$SYSTEM_FONTS_DIR/" 2>/dev/null || true

    # 设置字体文件权限
    sudo chmod 644 "$SYSTEM_FONTS_DIR"/*

    # 更新字体缓存
    log_info "更新字体缓存..."
    sudo fc-cache -fv

    log_success "字体安装完成"
}

# 验证字体安装
verify_fonts() {
    log_info "验证字体安装..."

    # 需要验证的字体列表
    declare -A REQUIRED_FONTS=(
        ["SimSun"]="宋体"
        ["SimHei"]="黑体"
        ["FangSong"]="仿宋"
        ["Arial"]="Arial"
        ["Times New Roman"]="Times New Roman"
        ["Calibri"]="Calibri"
    )

    local missing_fonts=()

    for font_name in "${!REQUIRED_FONTS[@]}"; do
        if fc-list | grep -qi "$font_name"; then
            log_success "字体已安装: ${REQUIRED_FONTS[$font_name]} ($font_name)"
        else
            log_warning "字体未找到: ${REQUIRED_FONTS[$font_name]} ($font_name)"
            missing_fonts+=("$font_name")
        fi
    done

    if [[ ${#missing_fonts[@]} -eq 0 ]]; then
        log_success "所有必需字体已正确安装"
    else
        log_warning "部分字体可能未正确安装，但PDF生成仍可能正常工作"
    fi
}

# 配置字体映射
configure_font_mapping() {
    log_info "配置字体映射..."

    # 创建fontconfig配置目录
    FONTCONFIG_DIR="/etc/fonts/conf.d"
    sudo mkdir -p "$FONTCONFIG_DIR"

    # 创建字体映射配置文件
    cat << 'EOF' | sudo tee "$FONTCONFIG_DIR/99-custom-fonts.conf" > /dev/null
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- 中文字体映射 -->
    <alias>
        <family>SimSun</family>
        <prefer>
            <family>SimSun</family>
        </prefer>
    </alias>

    <alias>
        <family>宋体</family>
        <prefer>
            <family>SimSun</family>
        </prefer>
    </alias>

    <alias>
        <family>SimHei</family>
        <prefer>
            <family>SimHei</family>
        </prefer>
    </alias>

    <alias>
        <family>黑体</family>
        <prefer>
            <family>SimHei</family>
        </prefer>
    </alias>

    <alias>
        <family>FangSong</family>
        <prefer>
            <family>FangSong</family>
        </prefer>
    </alias>

    <alias>
        <family>仿宋</family>
        <prefer>
            <family>FangSong</family>
        </prefer>
    </alias>

    <!-- 英文字体映射 -->
    <alias>
        <family>Arial</family>
        <prefer>
            <family>Arial</family>
        </prefer>
    </alias>

    <alias>
        <family>Times New Roman</family>
        <prefer>
            <family>Times New Roman</family>
        </prefer>
    </alias>

    <alias>
        <family>Calibri</family>
        <prefer>
            <family>Calibri</family>
        </prefer>
    </alias>
</fontconfig>
EOF

    # 重新加载fontconfig配置
    sudo fc-cache -fv

    log_success "字体映射配置完成"
}

# 测试PDF生成
test_pdf_generation() {
    log_info "测试unoconv PDF转换功能..."

    # 创建临时测试文件
    TEST_DOCX=$(mktemp --suffix=.docx)
    TEST_PDF=$(mktemp --suffix=.pdf)

    # 创建简单的测试文本文件
    TEST_TXT="${TEST_DOCX%.docx}.txt"
    cat << 'EOF' > "$TEST_TXT"
字体测试报告

这是宋体中文测试内容。
This is Arial English test content.
测试unoconv转换是否正确工作。
EOF

    # 使用unoconv测试转换
    if command -v unoconv &> /dev/null; then
        log_info "测试unoconv转换..."

        # 先创建一个简单的docx文件用于测试
        if command -v libreoffice &> /dev/null; then
            # 使用LibreOffice创建测试docx
            libreoffice --headless --convert-to docx --outdir "$(dirname "$TEST_DOCX")" "$TEST_TXT" 2>/dev/null || true

            if [[ -f "$TEST_DOCX" ]]; then
                # 设置环境变量并使用系统python3调用unoconv
                export UNO_PATH=/usr/lib/libreoffice/program
                export PYTHONPATH=/usr/lib/python3/dist-packages:/usr/lib/libreoffice/program

                if /usr/bin/python3 /usr/bin/unoconv -f pdf -o "$TEST_PDF" "$TEST_DOCX" 2>/dev/null; then
                    log_success "unoconv PDF生成测试成功: $TEST_PDF"
                    log_info "可以查看生成的PDF文件验证转换效果"
                else
                    log_warning "unoconv转换测试失败，将使用LibreOffice作为备选方案"
                fi
            else
                log_warning "无法创建测试docx文件，跳过转换测试"
            fi
        else
            log_warning "LibreOffice未安装，无法进行完整测试"
        fi
    else
        log_error "unoconv未正确安装"
    fi

    # 清理临时文件
    rm -f "$TEST_DOCX" "$TEST_PDF" "$TEST_TXT"
}

# 主函数
main() {
    log_info "开始安装PDF依赖和字体..."

    # 检查权限
    check_root

    # 检测操作系统
    detect_os

    # 安装PDF依赖
    install_pdf_dependencies

    # 安装字体
    install_fonts

    # 配置字体映射
    configure_font_mapping

    # 验证字体安装
    verify_fonts

    # 测试PDF生成
    test_pdf_generation

    log_success "所有安装和配置完成！"
    log_info "现在可以使用unoconv生成PDF，字体将严格按照模板映射"
    log_info "注意：如果unoconv出现UNO库问题，请设置环境变量: export UNO_PATH=/usr/lib/libreoffice/program"
    log_info "如果遇到distutils兼容性问题，请运行修复脚本: sudo ./scripts/fix_unoconv_distutils.sh"
}

# 执行主函数
main "$@"