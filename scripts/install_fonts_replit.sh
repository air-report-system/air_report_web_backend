#!/bin/bash

# Replit环境字体安装脚本
# 专为Replit环境优化的字体安装方案

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

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONTS_DIR="$SCRIPT_DIR/../templates/fonts"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 检查字体目录是否存在
check_fonts_directory() {
    log_info "检查字体目录..."
    if [[ ! -d "$FONTS_DIR" ]]; then
        log_error "字体目录不存在: $FONTS_DIR"
        exit 1
    fi
    
    # 检查字体文件数量
    FONT_COUNT=$(find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" | wc -l)
    log_info "发现 $FONT_COUNT 个字体文件"
    
    if [[ $FONT_COUNT -eq 0 ]]; then
        log_error "字体目录中没有找到字体文件"
        exit 1
    fi
}

# 创建用户字体目录（Replit环境）
create_user_fonts_directory() {
    log_info "创建用户字体目录..."
    
    # Replit环境使用用户目录
    USER_FONTS_DIR="$HOME/.local/share/fonts"
    mkdir -p "$USER_FONTS_DIR"
    
    # 创建fontconfig配置目录
    FONTCONFIG_DIR="$HOME/.config/fontconfig"
    mkdir -p "$FONTCONFIG_DIR"
    
    log_success "字体目录创建完成: $USER_FONTS_DIR"
}

# 安装字体文件
install_fonts() {
    log_info "开始安装字体文件..."
    
    USER_FONTS_DIR="$HOME/.local/share/fonts"
    
    # 复制所有字体文件
    log_info "复制字体文件..."
    find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" | while read font_file; do
        font_name=$(basename "$font_file")
        cp "$font_file" "$USER_FONTS_DIR/"
        log_info "已复制: $font_name"
    done
    
    # 设置字体文件权限
    chmod 644 "$USER_FONTS_DIR"/*
    
    log_success "字体文件复制完成"
}

# 创建字体配置文件
create_font_config() {
    log_info "创建字体配置文件..."
    
    FONTCONFIG_DIR="$HOME/.config/fontconfig"
    CONFIG_FILE="$FONTCONFIG_DIR/fonts.conf"
    
    cat > "$CONFIG_FILE" << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- 用户字体目录 -->
    <dir>~/.local/share/fonts</dir>
    
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
    
    <!-- 默认字体回退 -->
    <alias>
        <family>serif</family>
        <prefer>
            <family>Times New Roman</family>
            <family>SimSun</family>
        </prefer>
    </alias>
    
    <alias>
        <family>sans-serif</family>
        <prefer>
            <family>Arial</family>
            <family>SimHei</family>
        </prefer>
    </alias>
    
    <alias>
        <family>monospace</family>
        <prefer>
            <family>Courier New</family>
            <family>SimSun</family>
        </prefer>
    </alias>
</fontconfig>
EOF
    
    log_success "字体配置文件创建完成: $CONFIG_FILE"
}

# 更新字体缓存
update_font_cache() {
    log_info "更新字体缓存..."
    
    # 检查fc-cache是否可用
    if command -v fc-cache &> /dev/null; then
        fc-cache -fv "$HOME/.local/share/fonts"
        log_success "字体缓存更新完成"
    else
        log_warning "fc-cache命令不可用，跳过缓存更新"
    fi
}

# 验证字体安装
verify_fonts() {
    log_info "验证字体安装..."
    
    # 需要验证的字体列表
    declare -A REQUIRED_FONTS=(
        ["SimSun"]="宋体"
        ["SimHei"]="黑体" 
        ["Arial"]="Arial"
        ["Times"]="Times New Roman"
        ["Calibri"]="Calibri"
    )
    
    local missing_fonts=()
    local found_fonts=()
    
    for font_name in "${!REQUIRED_FONTS[@]}"; do
        if command -v fc-list &> /dev/null; then
            if fc-list | grep -qi "$font_name"; then
                log_success "字体已安装: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                found_fonts+=("$font_name")
            else
                log_warning "字体未在系统中找到: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                missing_fonts+=("$font_name")
            fi
        else
            # 如果fc-list不可用，检查文件是否存在
            if find "$HOME/.local/share/fonts" -iname "*$font_name*" | grep -q .; then
                log_success "字体文件已复制: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                found_fonts+=("$font_name")
            else
                log_warning "字体文件未找到: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                missing_fonts+=("$font_name")
            fi
        fi
    done
    
    log_info "字体安装总结:"
    log_info "已安装字体数量: ${#found_fonts[@]}"
    log_info "缺失字体数量: ${#missing_fonts[@]}"
    
    if [[ ${#missing_fonts[@]} -eq 0 ]]; then
        log_success "所有必需字体已正确安装"
    else
        log_warning "部分字体可能未正确安装，但PDF生成仍可能正常工作"
    fi
}

# 设置环境变量
setup_environment() {
    log_info "设置字体环境变量..."
    
    # 创建环境变量文件
    ENV_FILE="$PROJECT_ROOT/.env.fonts"
    cat > "$ENV_FILE" << EOF
# 字体相关环境变量
export FONTCONFIG_PATH=\$HOME/.config/fontconfig
export FONTCONFIG_FILE=\$HOME/.config/fontconfig/fonts.conf
export FONTS_DIR=\$HOME/.local/share/fonts
EOF
    
    log_success "字体环境变量文件创建完成: $ENV_FILE"
    log_info "请在启动脚本中source此文件: source $ENV_FILE"
}

# 主函数
main() {
    log_info "开始Replit环境字体安装..."
    
    # 检查字体目录
    check_fonts_directory
    
    # 创建用户字体目录
    create_user_fonts_directory
    
    # 安装字体文件
    install_fonts
    
    # 创建字体配置
    create_font_config
    
    # 更新字体缓存
    update_font_cache
    
    # 验证字体安装
    verify_fonts
    
    # 设置环境变量
    setup_environment
    
    log_success "Replit环境字体安装完成！"
    log_info "字体文件位置: $HOME/.local/share/fonts"
    log_info "配置文件位置: $HOME/.config/fontconfig/fonts.conf"
    log_info "环境变量文件: $PROJECT_ROOT/.env.fonts"
}

# 执行主函数
main "$@"
