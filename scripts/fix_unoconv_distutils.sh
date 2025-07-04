#!/bin/bash

# 修复unoconv的distutils兼容性问题
# 在Python 3.12中，distutils被移除，需要使用packaging.version替代

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
if [[ $EUID -ne 0 ]]; then
   log_error "此脚本需要root权限运行"
   log_info "请使用: sudo $0"
   exit 1
fi

log_info "开始修复unoconv的distutils兼容性问题..."

# 检查unoconv是否存在
if [[ ! -f /usr/bin/unoconv ]]; then
    log_error "unoconv未安装，请先安装: sudo apt-get install unoconv"
    exit 1
fi

# 安装packaging模块（如果未安装）
log_info "确保packaging模块已安装..."
apt-get update
apt-get install -y python3-packaging

# 备份原始文件
log_info "备份原始unoconv文件..."
cp /usr/bin/unoconv /usr/bin/unoconv.backup

# 创建修复后的unoconv文件
log_info "创建修复后的unoconv文件..."
cat > /usr/bin/unoconv << 'EOF'
#!/usr/bin/env python3

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 only
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
### Copyright 2007-2010 Dag Wieers <dag@wieers.com>

from __future__ import print_function

# 修复distutils兼容性问题
try:
    from distutils.version import LooseVersion
except ImportError:
    # Python 3.12+ 使用packaging.version替代
    from packaging.version import Version as LooseVersion

import getopt
import glob
import os
import subprocess
import sys
import time
EOF

# 将原文件的其余部分追加到新文件
tail -n +26 /usr/bin/unoconv.backup >> /usr/bin/unoconv

# 设置执行权限
chmod +x /usr/bin/unoconv

# 测试修复后的unoconv
log_info "测试修复后的unoconv..."
if /usr/bin/unoconv --version >/dev/null 2>&1; then
    log_success "unoconv修复成功！"
    
    # 显示版本信息
    VERSION_INFO=$(/usr/bin/unoconv --version 2>&1 | head -n1)
    log_success "unoconv版本: $VERSION_INFO"
    
    # 清理备份文件
    rm -f /usr/bin/unoconv.backup
    
    log_success "distutils兼容性问题已修复"
else
    log_error "unoconv修复失败，恢复原始文件..."
    mv /usr/bin/unoconv.backup /usr/bin/unoconv
    exit 1
fi

log_info "修复完成！现在可以正常使用unoconv进行PDF转换"
