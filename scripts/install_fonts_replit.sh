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
    log_info "DEBUG: 脚本目录: $SCRIPT_DIR"
    log_info "DEBUG: 字体目录: $FONTS_DIR"
    log_info "DEBUG: 项目根目录: $PROJECT_ROOT"

    if [[ ! -d "$FONTS_DIR" ]]; then
        log_error "字体目录不存在: $FONTS_DIR"
        log_info "DEBUG: 检查上级目录结构:"
        if [[ -d "$(dirname "$FONTS_DIR")" ]]; then
            ls -la "$(dirname "$FONTS_DIR")" | while read line; do
                log_info "DEBUG:   $line"
            done
        else
            log_error "DEBUG: 上级目录也不存在: $(dirname "$FONTS_DIR")"
        fi
        exit 1
    fi

    log_info "DEBUG: 字体目录存在，检查内容..."
    ls -la "$FONTS_DIR" | head -10 | while read line; do
        log_info "DEBUG:   $line"
    done

    # 检查字体文件数量
    FONT_COUNT=$(find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" | wc -l)
    log_info "发现 $FONT_COUNT 个字体文件"

    if [[ $FONT_COUNT -gt 0 ]]; then
        log_info "DEBUG: 字体文件列表:"
        find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" | head -5 | while read font; do
            log_info "DEBUG:   $(basename "$font")"
        done
        if [[ $FONT_COUNT -gt 5 ]]; then
            log_info "DEBUG:   ... 还有 $((FONT_COUNT - 5)) 个字体文件"
        fi
    else
        log_error "字体目录中没有找到字体文件"
        log_info "DEBUG: 搜索所有文件类型:"
        find "$FONTS_DIR" -type f | head -10 | while read file; do
            log_info "DEBUG:   $(basename "$file")"
        done
        exit 1
    fi
}

# 创建字体目录（支持系统级和用户级）
create_font_directories() {
    log_info "创建字体目录..."
    
    # 系统级字体目录（需要在Replit中创建）
    SYSTEM_FONTS_DIR="/usr/share/fonts/truetype/custom"
    if [[ -w "/usr/share/fonts" ]]; then
        log_info "创建系统级字体目录: $SYSTEM_FONTS_DIR"
        mkdir -p "$SYSTEM_FONTS_DIR"
    else
        log_warning "无法创建系统级字体目录，使用用户级目录"
    fi
    
    # 用户级字体目录
    USER_FONTS_DIR="$HOME/.local/share/fonts"
    mkdir -p "$USER_FONTS_DIR"
    
    # 创建fontconfig配置目录
    FONTCONFIG_DIR="$HOME/.config/fontconfig"
    mkdir -p "$FONTCONFIG_DIR"
    
    log_success "字体目录创建完成"
}

# 安装字体文件
install_fonts() {
    log_info "开始安装字体文件..."
    
    USER_FONTS_DIR="$HOME/.local/share/fonts"
    SYSTEM_FONTS_DIR="/usr/share/fonts/truetype/custom"
    
    # 优先尝试系统级安装
    if [[ -w "$SYSTEM_FONTS_DIR" ]]; then
        log_info "使用系统级字体安装..."
        TARGET_DIR="$SYSTEM_FONTS_DIR"
    else
        log_info "使用用户级字体安装..."
        TARGET_DIR="$USER_FONTS_DIR"
    fi
    
    # 复制所有字体文件
    log_info "复制字体文件到: $TARGET_DIR"
    local copied_count=0
    
    find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" | while read font_file; do
        font_name=$(basename "$font_file")
        if cp "$font_file" "$TARGET_DIR/" 2>/dev/null; then
            log_info "已复制: $font_name"
            ((copied_count++))
        else
            log_warning "复制失败: $font_name"
        fi
    done
    
    # 设置字体文件权限
    chmod 644 "$TARGET_DIR"/* 2>/dev/null || true
    
    log_success "字体文件复制完成 (已复制: $copied_count 个文件)"
}

# 安装系统字体（从Nix store）
install_system_fonts() {
    log_info "安装系统字体..."
    
    # 查找Nix store中的字体
    if [[ -d "/nix/store" ]]; then
        log_info "查找Nix store中的字体包..."
        
        # 创建系统字体链接目录
        SYSTEM_FONTS_LINK_DIR="/usr/share/fonts/nix"
        if [[ -w "/usr/share/fonts" ]]; then
            mkdir -p "$SYSTEM_FONTS_LINK_DIR"
            
            # 查找并链接字体
            find /nix/store -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | head -20 | while read font_file; do
                font_name=$(basename "$font_file")
                target_link="$SYSTEM_FONTS_LINK_DIR/$font_name"
                if [[ ! -e "$target_link" ]]; then
                    ln -sf "$font_file" "$target_link" 2>/dev/null || true
                    log_info "已链接系统字体: $font_name"
                fi
            done
        else
            log_warning "无法创建系统字体链接目录"
        fi
    else
        log_warning "Nix store不存在，跳过系统字体安装"
    fi
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
    <!-- 字体目录 -->
    <dir>~/.local/share/fonts</dir>
    <dir>/usr/share/fonts/truetype/custom</dir>
    <dir>/usr/share/fonts/nix</dir>
    
    <!-- 字体渲染设置 -->
    <match target="font">
        <edit name="antialias" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="hinting" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="rgba" mode="assign">
            <const>rgb</const>
        </edit>
        <edit name="hintstyle" mode="assign">
            <const>hintslight</const>
        </edit>
        <edit name="lcdfilter" mode="assign">
            <const>lcddefault</const>
        </edit>
    </match>
    
    <!-- 中文字体映射 -->
    <alias>
        <family>SimSun</family>
        <prefer>
            <family>SimSun</family>
            <family>Noto Sans CJK SC</family>
            <family>Source Han Sans CN</family>
            <family>WenQuanYi Zen Hei</family>
        </prefer>
    </alias>
    
    <alias>
        <family>宋体</family>
        <prefer>
            <family>SimSun</family>
            <family>Noto Sans CJK SC</family>
            <family>Source Han Sans CN</family>
        </prefer>
    </alias>
    
    <alias>
        <family>SimHei</family>
        <prefer>
            <family>SimHei</family>
            <family>Noto Sans CJK SC</family>
            <family>Source Han Sans CN</family>
            <family>WenQuanYi Zen Hei</family>
        </prefer>
    </alias>
    
    <alias>
        <family>黑体</family>
        <prefer>
            <family>SimHei</family>
            <family>Noto Sans CJK SC</family>
            <family>Source Han Sans CN</family>
        </prefer>
    </alias>
    
    <!-- 英文字体映射 -->
    <alias>
        <family>Arial</family>
        <prefer>
            <family>Arial</family>
            <family>Liberation Sans</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <alias>
        <family>Times New Roman</family>
        <prefer>
            <family>Times New Roman</family>
            <family>Liberation Serif</family>
            <family>DejaVu Serif</family>
        </prefer>
    </alias>
    
    <alias>
        <family>Calibri</family>
        <prefer>
            <family>Calibri</family>
            <family>Liberation Sans</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <!-- 默认字体设置 -->
    <alias>
        <family>serif</family>
        <prefer>
            <family>Times New Roman</family>
            <family>Liberation Serif</family>
            <family>Noto Serif CJK SC</family>
            <family>Source Han Serif CN</family>
            <family>SimSun</family>
        </prefer>
    </alias>
    
    <alias>
        <family>sans-serif</family>
        <prefer>
            <family>Arial</family>
            <family>Liberation Sans</family>
            <family>Noto Sans CJK SC</family>
            <family>Source Han Sans CN</family>
            <family>SimHei</family>
        </prefer>
    </alias>
    
    <alias>
        <family>monospace</family>
        <prefer>
            <family>Courier New</family>
            <family>Liberation Mono</family>
            <family>DejaVu Sans Mono</family>
            <family>Noto Sans Mono CJK SC</family>
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
    
    # 设置字体配置环境变量
    export FONTCONFIG_PATH="$HOME/.config/fontconfig"
    export FONTCONFIG_FILE="$HOME/.config/fontconfig/fonts.conf"
    
    # 检查并使用fc-cache
    if command -v fc-cache &> /dev/null; then
        log_info "使用fc-cache更新字体缓存..."
        
        # 更新用户字体缓存
        fc-cache -fv "$HOME/.local/share/fonts" 2>&1 | while read line; do
            log_info "fc-cache: $line"
        done
        
        # 更新系统字体缓存
        if [[ -d "/usr/share/fonts/truetype/custom" ]]; then
            fc-cache -fv "/usr/share/fonts/truetype/custom" 2>&1 | while read line; do
                log_info "fc-cache (system): $line"
            done
        fi
        
        # 更新全局字体缓存
        fc-cache -fv 2>&1 | while read line; do
            log_info "fc-cache (global): $line"
        done
        
        log_success "字体缓存更新完成"
    else
        log_warning "fc-cache不可用，尝试手动创建缓存..."
        
        # 创建缓存目录
        mkdir -p "$HOME/.cache/fontconfig"
        
        # 检查字体数量
        local font_count=$(find "$HOME/.local/share/fonts" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | wc -l)
        log_info "用户字体文件数量: $font_count"
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
        ["Liberation"]="Liberation字体"
        ["DejaVu"]="DejaVu字体"
        ["Noto"]="Noto字体"
    )
    
    local found_fonts=()
    local missing_fonts=()
    
    # 检查fc-list是否可用
    if command -v fc-list &> /dev/null; then
        log_info "使用fc-list检查字体..."
        
        for font_name in "${!REQUIRED_FONTS[@]}"; do
            if fc-list | grep -qi "$font_name"; then
                log_success "字体已安装: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                found_fonts+=("$font_name")
            else
                log_warning "字体未在系统中找到: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                missing_fonts+=("$font_name")
            fi
        done
    else
        log_warning "fc-list不可用，检查字体文件..."
        
        # 检查字体文件是否存在
        for font_name in "${!REQUIRED_FONTS[@]}"; do
            if find "$HOME/.local/share/fonts" -iname "*$font_name*" 2>/dev/null | grep -q .; then
                log_success "字体文件已复制: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                found_fonts+=("$font_name")
            else
                log_warning "字体文件未找到: ${REQUIRED_FONTS[$font_name]} ($font_name)"
                missing_fonts+=("$font_name")
            fi
        done
    fi
    
    # 显示安装总结
    log_info "=== 字体安装总结 ==="
    log_info "已安装字体数量: ${#found_fonts[@]}"
    log_info "缺失字体数量: ${#missing_fonts[@]}"
    
    if [[ ${#found_fonts[@]} -gt 0 ]]; then
        log_info "已安装的字体:"
        for font in "${found_fonts[@]}"; do
            log_info "  ✓ ${REQUIRED_FONTS[$font]} ($font)"
        done
    fi
    
    if [[ ${#missing_fonts[@]} -gt 0 ]]; then
        log_warning "缺失的字体:"
        for font in "${missing_fonts[@]}"; do
            log_warning "  ✗ ${REQUIRED_FONTS[$font]} ($font)"
        done
    fi
    
    # 检查字体总数
    local total_user_fonts=$(find "$HOME/.local/share/fonts" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | wc -l)
    log_info "用户字体文件总数: $total_user_fonts"
    
    if command -v fc-list &> /dev/null; then
        local total_system_fonts=$(fc-list 2>/dev/null | wc -l)
        log_info "系统字体总数: $total_system_fonts"
    fi
}

# 设置环境变量
setup_environment() {
    log_info "设置字体环境变量..."
    
    # 创建环境变量文件
    ENV_FILE="$PROJECT_ROOT/.env.fonts"
    cat > "$ENV_FILE" << EOF
# 字体相关环境变量
export FONTCONFIG_PATH=\$HOME/.config/fontconfig:\$FONTCONFIG_PATH
export FONTCONFIG_FILE=\$HOME/.config/fontconfig/fonts.conf
export FONTS_DIR=\$HOME/.local/share/fonts
export SYSTEM_FONTS_DIR=/usr/share/fonts/truetype/custom

# 确保字体配置生效
export FC_CACHE_FORCE=1
export FC_DEBUG=1
EOF
    
    log_success "字体环境变量文件创建完成: $ENV_FILE"
    log_info "请在启动脚本中source此文件: source $ENV_FILE"
}

# 主函数
main() {
    log_info "=== 开始Replit环境字体安装 ==="
    
    # 检查字体目录
    check_fonts_directory
    
    # 创建字体目录
    create_font_directories
    
    # 安装项目字体文件
    install_fonts
    
    # 安装系统字体
    install_system_fonts
    
    # 创建字体配置
    create_font_config
    
    # 更新字体缓存
    update_font_cache
    
    # 验证字体安装
    verify_fonts
    
    # 设置环境变量
    setup_environment
    
    log_success "=== Replit环境字体安装完成！ ==="
    log_info "字体文件位置: $HOME/.local/share/fonts"
    log_info "配置文件位置: $HOME/.config/fontconfig/fonts.conf"
    log_info "环境变量文件: $PROJECT_ROOT/.env.fonts"
    log_info ""
    log_info "请重新启动应用程序或重新加载环境变量以使字体生效。"
}

# 执行主函数
main "$@"
