#!/bin/bash

# Replit环境字体安装脚本 - 修复版本
# 专为解决并发执行和复制失败问题

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

# 锁文件防止并发执行
LOCK_FILE="/tmp/font_install.lock"

# 清理函数
cleanup() {
    if [[ -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE"
    fi
}

# 设置信号处理器
trap cleanup EXIT INT TERM

# 检查并获取锁
acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            log_warning "字体安装脚本已在运行 (PID: $lock_pid)，等待完成..."
            local wait_count=0
            while [[ -f "$LOCK_FILE" ]] && [[ $wait_count -lt 30 ]]; do
                sleep 2
                ((wait_count++))
            done
            
            if [[ -f "$LOCK_FILE" ]]; then
                log_error "等待超时，强制清理锁文件"
                rm -f "$LOCK_FILE"
            fi
        else
            log_info "清理过期的锁文件"
            rm -f "$LOCK_FILE"
        fi
    fi
    
    # 创建新锁
    echo $$ > "$LOCK_FILE"
    log_info "获取锁成功 (PID: $$)"
}

# 简化的字体复制函数
install_fonts_simple() {
    log_info "开始安装字体文件..."
    
    # 创建用户字体目录
    USER_FONTS_DIR="$HOME/.local/share/fonts"
    mkdir -p "$USER_FONTS_DIR"
    
    # 检查源字体目录
    if [[ ! -d "$FONTS_DIR" ]]; then
        log_error "字体源目录不存在: $FONTS_DIR"
        return 1
    fi
    
    log_info "源字体目录: $FONTS_DIR"
    log_info "目标字体目录: $USER_FONTS_DIR"
    
    # 计算字体文件数量
    local font_files=($(find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" 2>/dev/null))
    local total_fonts=${#font_files[@]}
    
    log_info "发现 $total_fonts 个字体文件"
    
    if [[ $total_fonts -eq 0 ]]; then
        log_error "源目录中没有找到字体文件"
        return 1
    fi
    
    # 复制字体文件
    local copied_count=0
    local failed_count=0
    
    for font_file in "${font_files[@]}"; do
        local font_name=$(basename "$font_file")
        local target_file="$USER_FONTS_DIR/$font_name"
        
        if cp "$font_file" "$target_file" 2>/dev/null; then
            chmod 644 "$target_file" 2>/dev/null || true
            log_info "✓ 已复制: $font_name"
            ((copied_count++))
        else
            log_warning "✗ 复制失败: $font_name"
            ((failed_count++))
        fi
    done
    
    log_info "=== 复制结果 ==="
    log_success "成功复制: $copied_count 个文件"
    if [[ $failed_count -gt 0 ]]; then
        log_warning "失败文件: $failed_count 个"
    fi
    
    # 验证复制结果
    local installed_count=$(find "$USER_FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" 2>/dev/null | wc -l)
    log_info "用户字体目录中的字体文件数量: $installed_count"
    
    return 0
}

# 创建简化的字体配置
create_simple_font_config() {
    log_info "创建字体配置文件..."
    
    FONTCONFIG_DIR="$HOME/.config/fontconfig"
    CONFIG_FILE="$FONTCONFIG_DIR/fonts.conf"
    
    mkdir -p "$FONTCONFIG_DIR"
    
    cat > "$CONFIG_FILE" << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- 字体目录 -->
    <dir>~/.local/share/fonts</dir>
    
    <!-- 字体渲染设置 -->
    <match target="font">
        <edit name="antialias" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="hinting" mode="assign">
            <bool>true</bool>
        </edit>
    </match>
    
    <!-- 中文字体映射 -->
    <alias>
        <family>SimSun</family>
        <prefer>
            <family>SimSun</family>
            <family>Noto Sans CJK SC</family>
        </prefer>
    </alias>
    
    <alias>
        <family>SimHei</family>
        <prefer>
            <family>SimHei</family>
            <family>Noto Sans CJK SC</family>
        </prefer>
    </alias>
    
    <!-- 英文字体映射 -->
    <alias>
        <family>Arial</family>
        <prefer>
            <family>Arial</family>
            <family>Liberation Sans</family>
        </prefer>
    </alias>
    
    <alias>
        <family>Times New Roman</family>
        <prefer>
            <family>Times New Roman</family>
            <family>Liberation Serif</family>
        </prefer>
    </alias>
    
    <alias>
        <family>Calibri</family>
        <prefer>
            <family>Calibri</family>
            <family>Liberation Sans</family>
        </prefer>
    </alias>
</fontconfig>
EOF
    
    log_success "字体配置文件创建完成: $CONFIG_FILE"
}

# 更新字体缓存
update_font_cache_simple() {
    log_info "更新字体缓存..."
    
    # 设置环境变量
    export FONTCONFIG_PATH="$HOME/.config/fontconfig"
    export FONTCONFIG_FILE="$HOME/.config/fontconfig/fonts.conf"
    
    if command -v fc-cache &> /dev/null; then
        log_info "使用fc-cache更新字体缓存..."
        fc-cache -fv "$HOME/.local/share/fonts" 2>/dev/null || log_warning "fc-cache执行失败"
        log_success "字体缓存更新完成"
    else
        log_warning "fc-cache不可用，跳过缓存更新"
    fi
    
    # 检查字体数量
    local font_count=$(find "$HOME/.local/share/fonts" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | wc -l)
    log_info "用户字体文件数量: $font_count"
}

# 快速验证函数
verify_fonts_simple() {
    log_info "验证字体安装..."
    
    local user_fonts_dir="$HOME/.local/share/fonts"
    local total_fonts=$(find "$user_fonts_dir" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | wc -l)
    
    log_info "用户字体目录中的字体数量: $total_fonts"
    
    # 检查关键字体文件
    local key_fonts=("arial.ttf" "simhei.ttf" "simsun.ttc" "calibri.ttf" "times.ttf")
    local found_key_fonts=0
    
    for font_file in "${key_fonts[@]}"; do
        if [[ -f "$user_fonts_dir/$font_file" ]]; then
            log_success "✓ 关键字体存在: $font_file"
            ((found_key_fonts++))
        else
            log_warning "✗ 关键字体缺失: $font_file"
        fi
    done
    
    log_info "关键字体检查: $found_key_fonts/${#key_fonts[@]} 个可用"
    
    # 检查配置文件
    if [[ -f "$HOME/.config/fontconfig/fonts.conf" ]]; then
        log_success "✓ 字体配置文件存在"
    else
        log_warning "✗ 字体配置文件缺失"
    fi
    
    return 0
}

# 主函数
main() {
    log_info "=== 开始字体安装 (修复版本) ==="
    
    # 获取锁
    acquire_lock
    
    # 执行安装步骤
    if install_fonts_simple; then
        create_simple_font_config
        update_font_cache_simple
        verify_fonts_simple
        log_success "=== 字体安装完成！ ==="
    else
        log_error "=== 字体安装失败！ ==="
        return 1
    fi
}

# 执行主函数
main "$@" 