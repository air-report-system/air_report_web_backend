#!/bin/bash

# Replit环境字体安装脚本 - 调试增强版本
# 专为解决并发执行和复制失败问题，添加详细调试信息

set -e  # 遇到错误时退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_debug() {
    echo -e "${CYAN}[DEBUG]${NC} $1"
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

log_debug "=== 环境信息 ==="
log_debug "脚本路径: ${BASH_SOURCE[0]}"
log_debug "脚本目录: $SCRIPT_DIR"
log_debug "字体目录: $FONTS_DIR"
log_debug "项目根目录: $PROJECT_ROOT"
log_debug "当前用户: $(whoami)"
log_debug "当前工作目录: $(pwd)"
log_debug "HOME目录: $HOME"
log_debug "Shell: $SHELL"
log_debug "操作系统: $(uname -a)"

# 清理函数
cleanup() {
    if [[ -f "$LOCK_FILE" ]]; then
        log_debug "清理锁文件: $LOCK_FILE"
        rm -f "$LOCK_FILE"
    fi
}

# 设置信号处理器
trap cleanup EXIT INT TERM

# 检查并获取锁
acquire_lock() {
    log_debug "检查锁文件: $LOCK_FILE"
    
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        log_debug "发现现有锁文件，PID: $lock_pid"
        
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            log_warning "字体安装脚本已在运行 (PID: $lock_pid)，等待完成..."
            local wait_count=0
            while [[ -f "$LOCK_FILE" ]] && [[ $wait_count -lt 30 ]]; do
                sleep 2
                ((wait_count++))
                log_debug "等待中... ($wait_count/30)"
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

# 详细的环境检查
check_environment() {
    log_debug "=== 详细环境检查 ==="
    
    # 检查命令可用性
    local commands=("cp" "chmod" "mkdir" "find" "fc-cache" "fc-list")
    for cmd in "${commands[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            log_debug "✓ 命令可用: $cmd ($(which "$cmd"))"
        else
            log_warning "✗ 命令不可用: $cmd"
        fi
    done
    
    # 检查目录权限
    log_debug "检查关键目录权限:"
    
    # 检查HOME目录
    if [[ -d "$HOME" ]]; then
        log_debug "✓ HOME目录: $HOME ($(ls -ld "$HOME" | awk '{print $1, $3, $4}'))"
    else
        log_error "✗ HOME目录不存在: $HOME"
    fi
    
    # 检查.local目录
    if [[ -d "$HOME/.local" ]]; then
        log_debug "✓ .local目录存在: $(ls -ld "$HOME/.local" | awk '{print $1, $3, $4}')"
    else
        log_debug "✗ .local目录不存在，将创建"
    fi
    
    # 检查.config目录
    if [[ -d "$HOME/.config" ]]; then
        log_debug "✓ .config目录存在: $(ls -ld "$HOME/.config" | awk '{print $1, $3, $4}')"
    else
        log_debug "✗ .config目录不存在，将创建"
    fi
    
    # 检查磁盘空间
    log_debug "磁盘空间信息:"
    df -h "$HOME" | tail -1 | while read line; do
        log_debug "  $line"
    done
}

# 简化的字体复制函数
install_fonts_simple() {
    log_info "开始安装字体文件..."
    
    # 详细检查源字体目录
    log_debug "=== 源字体目录检查 ==="
    log_debug "字体目录路径: $FONTS_DIR"
    
    if [[ ! -d "$FONTS_DIR" ]]; then
        log_error "字体源目录不存在: $FONTS_DIR"
        log_debug "尝试查找相对路径..."
        
        # 尝试不同的相对路径
        local alt_paths=(
            "templates/fonts"
            "../templates/fonts"
            "./templates/fonts"
            "$(pwd)/templates/fonts"
        )
        
        for alt_path in "${alt_paths[@]}"; do
            log_debug "检查路径: $alt_path"
            if [[ -d "$alt_path" ]]; then
                FONTS_DIR="$alt_path"
                log_info "找到字体目录: $FONTS_DIR"
                break
            fi
        done
        
        if [[ ! -d "$FONTS_DIR" ]]; then
            log_error "无法找到字体目录"
            return 1
        fi
    fi
    
    log_debug "字体目录权限: $(ls -ld "$FONTS_DIR" | awk '{print $1, $3, $4}')"
    log_debug "字体目录内容概览:"
    ls -la "$FONTS_DIR" | head -5 | while read line; do
        log_debug "  $line"
    done
    
    # 创建用户字体目录
    # 关键修复：根据部署环境的fc-cache扫描路径，将字体安装到项目工作区内
    USER_FONTS_DIR="$PROJECT_ROOT/.local/share/fonts"
    log_info "修正后的目标字体目录: $USER_FONTS_DIR"
    
    log_debug "=== 目标字体目录设置 ==="
    log_debug "目标目录: $USER_FONTS_DIR"
    
    # 逐级创建目录
    log_debug "逐级创建目录结构..."
    
    if [[ ! -d "$HOME/.local" ]]; then
        log_debug "创建 .local 目录..."
        if mkdir -p "$HOME/.local"; then
            log_debug "✓ .local 目录创建成功"
            log_debug "  权限: $(ls -ld "$HOME/.local" | awk '{print $1, $3, $4}')"
        else
            log_error "✗ .local 目录创建失败"
            return 1
        fi
    fi
    
    if [[ ! -d "$HOME/.local/share" ]]; then
        log_debug "创建 .local/share 目录..."
        if mkdir -p "$HOME/.local/share"; then
            log_debug "✓ .local/share 目录创建成功"
            log_debug "  权限: $(ls -ld "$HOME/.local/share" | awk '{print $1, $3, $4}')"
        else
            log_error "✗ .local/share 目录创建失败"
            return 1
        fi
    fi
    
    if [[ ! -d "$USER_FONTS_DIR" ]]; then
        log_debug "创建字体目录..."
        if mkdir -p "$USER_FONTS_DIR"; then
            log_debug "✓ 字体目录创建成功"
            log_debug "  权限: $(ls -ld "$USER_FONTS_DIR" | awk '{print $1, $3, $4}')"
        else
            log_error "✗ 字体目录创建失败"
            return 1
        fi
    else
        log_debug "字体目录已存在"
        log_debug "  权限: $(ls -ld "$USER_FONTS_DIR" | awk '{print $1, $3, $4}')"
        log_debug "  现有文件数: $(find "$USER_FONTS_DIR" -type f | wc -l)"
    fi
    
    log_info "源字体目录: $FONTS_DIR"
    log_info "目标字体目录: $USER_FONTS_DIR"
    
    # 计算字体文件数量
    log_debug "=== 字体文件扫描 ==="
    local font_files=($(find "$FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" 2>/dev/null))
    local total_fonts=${#font_files[@]}
    
    log_info "发现 $total_fonts 个字体文件"
    
    if [[ $total_fonts -eq 0 ]]; then
        log_error "源目录中没有找到字体文件"
        log_debug "目录内容详情:"
        find "$FONTS_DIR" -type f | head -10 | while read file; do
            log_debug "  文件: $(basename "$file") ($(file "$file" 2>/dev/null || echo "未知类型"))"
        done
        return 1
    fi
    
    # 显示将要复制的字体文件
    log_debug "字体文件列表:"
    for font_file in "${font_files[@]}"; do
        local font_name=$(basename "$font_file")
        local file_size=$(stat -c%s "$font_file" 2>/dev/null || echo "未知")
        log_debug "  $font_name ($file_size 字节)"
    done
    
    # 复制字体文件
    log_debug "=== 开始字体文件复制 ==="
    local copied_count=0
    local failed_count=0
    local skipped_count=0
    
    for font_file in "${font_files[@]}"; do
        local font_name=$(basename "$font_file")
        local target_file="$USER_FONTS_DIR/$font_name"
        
        log_debug "处理字体: $font_name"
        log_debug "  源文件: $font_file"
        log_debug "  目标文件: $target_file"
        
        # 检查源文件
        if [[ ! -f "$font_file" ]]; then
            log_warning "  ✗ 源文件不存在"
            ((failed_count++))
            continue
        fi
        
        # 检查是否已存在且相同
        if [[ -f "$target_file" ]]; then
            local src_size=$(stat -c%s "$font_file" 2>/dev/null || echo "0")
            local dst_size=$(stat -c%s "$target_file" 2>/dev/null || echo "0")
            if [[ "$src_size" == "$dst_size" ]] && [[ "$src_size" != "0" ]]; then
                log_debug "  ✓ 文件已存在且大小相同，跳过"
                ((skipped_count++))
                continue
            fi
        fi
        
        # 尝试复制
        log_debug "  复制中..."
        if cp "$font_file" "$target_file" 2>/dev/null; then
            # 验证复制结果
            if [[ -f "$target_file" ]]; then
                local src_size=$(stat -c%s "$font_file" 2>/dev/null || echo "0")
                local dst_size=$(stat -c%s "$target_file" 2>/dev/null || echo "0")
                
                if [[ "$src_size" == "$dst_size" ]] && [[ "$src_size" != "0" ]]; then
                    # 设置权限
                    if chmod 644 "$target_file" 2>/dev/null; then
                        log_info "  ✓ 已复制: $font_name ($dst_size 字节)"
                        ((copied_count++))
                    else
                        log_warning "  ✓ 已复制但权限设置失败: $font_name"
                        ((copied_count++))
                    fi
                else
                    log_error "  ✗ 复制验证失败: $font_name (源:$src_size, 目标:$dst_size)"
                    rm -f "$target_file" 2>/dev/null || true
                    ((failed_count++))
                fi
            else
                log_error "  ✗ 复制后文件不存在: $font_name"
                ((failed_count++))
            fi
        else
            log_warning "  ✗ 复制失败: $font_name ($(cp "$font_file" "$target_file" 2>&1 || echo "权限或空间不足"))"
            ((failed_count++))
        fi
    done
    
    log_info "=== 复制结果 ==="
    log_success "成功复制: $copied_count 个文件"
    if [[ $skipped_count -gt 0 ]]; then
        log_info "跳过文件: $skipped_count 个 (已存在)"
    fi
    if [[ $failed_count -gt 0 ]]; then
        log_warning "失败文件: $failed_count 个"
    fi
    
    # 验证复制结果
    local installed_count=$(find "$USER_FONTS_DIR" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" -o -name "*.TTF" -o -name "*.TTC" -o -name "*.OTF" 2>/dev/null | wc -l)
    log_info "用户字体目录中的字体文件数量: $installed_count"
    
    # 显示目录内容
    log_debug "字体目录最终状态:"
    ls -la "$USER_FONTS_DIR" | while read line; do
        log_debug "  $line"
    done
    
    if [[ $copied_count -gt 0 ]] || [[ $installed_count -gt 10 ]]; then
        return 0
    else
        log_error "字体复制失败或文件数量不足"
        return 1
    fi
}

# 创建简化的字体配置
create_simple_font_config() {
    log_info "创建字体配置文件..."
    
    FONTCONFIG_DIR="$HOME/.config/fontconfig"
    CONFIG_FILE="$FONTCONFIG_DIR/fonts.conf"
    USER_FONTS_DIR="$HOME/.local/share/fonts"
    
    log_debug "=== 字体配置文件创建 ==="
    log_debug "配置目录: $FONTCONFIG_DIR"
    log_debug "配置文件: $CONFIG_FILE"
    
    # 创建配置目录
    if mkdir -p "$FONTCONFIG_DIR"; then
        log_debug "✓ 配置目录创建成功"
        log_debug "  权限: $(ls -ld "$FONTCONFIG_DIR" | awk '{print $1, $3, $4}')"
    else
        log_error "✗ 配置目录创建失败"
        return 1
    fi
    
    # 创建配置文件
    log_debug "写入字体配置..."
    cat > "$CONFIG_FILE" << EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- 用户字体目录 -->
    <dir>$USER_FONTS_DIR</dir>
    <!-- 根据 XDG 规范的字体目录 -->
    <dir prefix="xdg">fonts</dir>
    
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
    
    if [[ -f "$CONFIG_FILE" ]]; then
        log_success "字体配置文件创建完成: $CONFIG_FILE"
        log_debug "配置文件大小: $(stat -c%s "$CONFIG_FILE" 2>/dev/null || echo "未知") 字节"
        log_debug "配置文件权限: $(ls -l "$CONFIG_FILE" | awk '{print $1, $3, $4}')"
    else
        log_error "字体配置文件创建失败"
        return 1
    fi
}

# 更新字体缓存
update_font_cache_simple() {
    log_info "更新字体缓存..."
    
    # 在执行 fc-cache 之前先清理可能损坏的旧缓存，避免出现 “invalid cache file”
    log_info "清理旧的 fontconfig 缓存目录..."
    if [[ -d "$HOME/.cache/fontconfig" ]]; then
        rm -rf "$HOME/.cache/fontconfig" 2>/dev/null || true
        log_debug "已删除旧缓存目录: $HOME/.cache/fontconfig"
    fi

    # 设置环境变量
    export FONTCONFIG_PATH="$HOME/.config/fontconfig"
    export FONTCONFIG_FILE="$HOME/.config/fontconfig/fonts.conf"
    export FC_CACHEDIR="$HOME/.cache/fontconfig"
    
    log_debug "=== 字体缓存更新 ==="
    log_debug "FONTCONFIG_PATH: $FONTCONFIG_PATH"
    log_debug "FONTCONFIG_FILE: $FONTCONFIG_FILE"
    
    if command -v fc-cache &> /dev/null; then
        log_info "使用fc-cache更新字体缓存..."
        log_debug "fc-cache版本: $(fc-cache --version 2>/dev/null || echo "未知")"
        
        # 更新字体缓存，显示详细输出
        if fc-cache -fv "$HOME/.local/share/fonts" 2>&1 | while read line; do
            log_debug "fc-cache: $line"
        done; then
            log_success "字体缓存更新完成"
        else
            log_warning "fc-cache执行可能有问题，但继续"
        fi
    else
        log_warning "fc-cache不可用，跳过缓存更新"
    fi
    
    # 检查字体数量
    local font_count=$(find "$HOME/.local/share/fonts" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | wc -l)
    log_info "用户字体文件数量: $font_count"
    
    # 检查fontconfig是否能识别字体
    if command -v fc-list &> /dev/null; then
        log_debug "检查fontconfig识别的字体..."
        local fc_count=$(fc-list 2>/dev/null | wc -l)
        log_debug "fontconfig识别的字体总数: $fc_count"
        
        # 检查用户字体目录中的字体
        local user_fc_count=$(fc-list "$HOME/.local/share/fonts" 2>/dev/null | wc -l)
        log_debug "用户字体目录中被识别的字体: $user_fc_count"
    fi
}

# 快速验证函数
verify_fonts_simple() {
    log_info "验证字体安装..."
    
    log_debug "=== 字体安装验证 ==="
    
    local user_fonts_dir="$HOME/.local/share/fonts"
    local total_fonts=$(find "$user_fonts_dir" -name "*.ttf" -o -name "*.ttc" -o -name "*.otf" 2>/dev/null | wc -l)
    
    log_info "用户字体目录中的字体数量: $total_fonts"
    
    # 检查关键字体文件
    local key_fonts=("arial.ttf" "simhei.ttf" "simsun.ttc" "calibri.ttf" "times.ttf")
    local found_key_fonts=0
    
    log_debug "检查关键字体文件:"
    for font_file in "${key_fonts[@]}"; do
        if [[ -f "$user_fonts_dir/$font_file" ]]; then
            local file_size=$(stat -c%s "$user_fonts_dir/$font_file" 2>/dev/null || echo "未知")
            log_success "✓ 关键字体存在: $font_file ($file_size 字节)"
            ((found_key_fonts++))
        else
            log_warning "✗ 关键字体缺失: $font_file"
        fi
    done
    
    log_info "关键字体检查: $found_key_fonts/${#key_fonts[@]} 个可用"
    
    # 检查配置文件
    if [[ -f "$HOME/.config/fontconfig/fonts.conf" ]]; then
        log_success "✓ 字体配置文件存在"
        log_debug "  文件大小: $(stat -c%s "$HOME/.config/fontconfig/fonts.conf" 2>/dev/null || echo "未知") 字节"
    else
        log_warning "✗ 字体配置文件缺失"
    fi
    
    # 最终检查
    if [[ $total_fonts -gt 0 ]] && [[ $found_key_fonts -gt 0 ]]; then
        log_success "字体安装验证通过"
        return 0
    else
        log_error "字体安装验证失败"
        return 1
    fi
}

# 主函数
main() {
    log_info "=== 开始字体安装 (调试增强版本) ==="
    
    # 清除可能遗留的调试环境变量，避免干扰 fc-list/ fc-cache 输出
    unset FC_DEBUG

    # 环境检查
    check_environment
    
    # 获取锁
    acquire_lock
    
    # 执行安装步骤
    if install_fonts_simple; then
        create_simple_font_config
        update_font_cache_simple
        verify_fonts_simple
        
        # 生成/覆盖字体相关环境变量文件，避免遗留的 FC_DEBUG 干扰
        ENV_FILE="$PROJECT_ROOT/.env.fonts"
        cat > "$ENV_FILE" << EOF
# 字体相关环境变量（由 install_fonts_replit_fixed.sh 自动生成）
export FONTCONFIG_PATH=\$HOME/.config/fontconfig:\$FONTCONFIG_PATH
export FONTCONFIG_FILE=$HOME/.config/fontconfig/fonts.conf
export FC_CACHEDIR=$HOME/.cache/fontconfig

# 关闭 fontconfig 调试输出
unset FC_DEBUG
EOF
        log_success "已刷新字体环境变量文件: $ENV_FILE"
        
        log_success "=== 字体安装完成！ ==="
    else
        log_error "=== 字体安装失败！ ==="
        return 1
    fi
}

# 执行主函数
main "$@" 