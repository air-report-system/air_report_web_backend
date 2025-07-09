#!/bin/bash

# Redis启动脚本 - 适用于Replit环境
# 支持WebSocket通信和Celery任务队列

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[REDIS]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[REDIS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[REDIS]${NC} $1"
}

log_error() {
    echo -e "${RED}[REDIS]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Redis配置
REDIS_PORT=6379
REDIS_HOST=127.0.0.1
REDIS_DATA_DIR="$PROJECT_ROOT/data/redis"
REDIS_LOG_FILE="$PROJECT_ROOT/logs/redis.log"
REDIS_PID_FILE="$PROJECT_ROOT/tmp/redis.pid"

# 创建必要目录
setup_redis_directories() {
    log_info "创建Redis目录..."
    
    mkdir -p "$REDIS_DATA_DIR"
    mkdir -p "$(dirname "$REDIS_LOG_FILE")"
    mkdir -p "$(dirname "$REDIS_PID_FILE")"
    
    log_success "Redis目录创建完成"
}

# 检查Redis是否已运行
check_redis_running() {
    if [[ -f "$REDIS_PID_FILE" ]]; then
        local pid=$(cat "$REDIS_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "Redis已在运行 (PID: $pid)"
            return 0
        else
            log_warning "Redis PID文件存在但进程未运行，清理PID文件"
            rm -f "$REDIS_PID_FILE"
        fi
    fi
    
    # 检查端口是否被占用
    if command -v lsof >/dev/null 2>&1 && lsof -i :$REDIS_PORT >/dev/null 2>&1; then
        log_warning "端口$REDIS_PORT被占用，尝试清理..."
        pkill -f redis-server || true
        sleep 1
    fi
    
    return 1
}

# 生成Redis配置文件
generate_redis_config() {
    log_info "生成Redis配置文件..."
    
    local config_file="$PROJECT_ROOT/config/redis.conf"
    mkdir -p "$(dirname "$config_file")"
    
    cat > "$config_file" << EOF
# Redis配置文件 - Replit环境
# 用于Django Channels和Celery

# 基本配置
port $REDIS_PORT
bind $REDIS_HOST
protected-mode no
timeout 0
tcp-keepalive 300

# 内存配置
maxmemory 64mb
maxmemory-policy allkeys-lru

# 持久化配置
save 60 1000
save 300 10
save 900 1
dir $REDIS_DATA_DIR
dbfilename dump.rdb
rdbcompression yes
rdbchecksum yes

# 日志配置
loglevel notice
logfile $REDIS_LOG_FILE
syslog-enabled no

# 进程配置
daemonize yes
pidfile $REDIS_PID_FILE

# 网络配置
tcp-backlog 511
unixsocket /tmp/redis.sock
unixsocketperm 700

# 客户端配置
maxclients 100

# 安全配置
# requirepass yourpassword  # 在生产环境中启用

# 性能优化
hz 10
dynamic-hz yes
aof-rewrite-incremental-fsync yes
rdb-save-incremental-fsync yes

# 模块配置
loadmodule-bulk-size 1
EOF
    
    log_success "Redis配置文件生成完成: $config_file"
}

# 启动Redis服务
start_redis_service() {
    log_info "启动Redis服务..."
    
    # 检查redis-server是否可用
    if ! command -v redis-server >/dev/null 2>&1; then
        log_error "redis-server命令未找到，请检查Redis是否已安装"
        return 1
    fi
    
    local config_file="$PROJECT_ROOT/config/redis.conf"
    
    # 启动Redis服务
    if redis-server "$config_file"; then
        log_success "Redis服务启动成功"
        
        # 等待Redis完全启动
        local max_attempts=10
        local attempt=0
        
        while [[ $attempt -lt $max_attempts ]]; do
            if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
                log_success "Redis服务可用 (尝试 $((attempt + 1))/$max_attempts)"
                return 0
            fi
            
            log_info "等待Redis启动... ($((attempt + 1))/$max_attempts)"
            sleep 1
            ((attempt++))
        done
        
        log_error "Redis服务启动超时"
        return 1
    else
        log_error "Redis服务启动失败"
        return 1
    fi
}

# 测试Redis连接
test_redis_connection() {
    log_info "测试Redis连接..."
    
    # 基本连接测试
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
        log_success "Redis连接测试通过"
    else
        log_error "Redis连接测试失败"
        return 1
    fi
    
    # 写入测试
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" set test_key "test_value" >/dev/null 2>&1; then
        log_success "Redis写入测试通过"
    else
        log_error "Redis写入测试失败"
        return 1
    fi
    
    # 读取测试
    if [[ "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" get test_key)" == "test_value" ]]; then
        log_success "Redis读取测试通过"
    else
        log_error "Redis读取测试失败"
        return 1
    fi
    
    # 清理测试数据
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" del test_key >/dev/null 2>&1
    
    log_success "Redis功能测试全部通过"
}

# 显示Redis状态
show_redis_status() {
    log_info "Redis服务状态:"
    log_info "  • 主机: $REDIS_HOST"
    log_info "  • 端口: $REDIS_PORT"
    log_info "  • 数据目录: $REDIS_DATA_DIR"
    log_info "  • 日志文件: $REDIS_LOG_FILE"
    log_info "  • PID文件: $REDIS_PID_FILE"
    
    if [[ -f "$REDIS_PID_FILE" ]]; then
        local pid=$(cat "$REDIS_PID_FILE")
        log_info "  • 进程ID: $pid"
    fi
    
    # 显示Redis信息
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server 2>/dev/null | grep -E "redis_version|uptime_in_seconds" | while read line; do
        log_info "  • $line"
    done; then
        :
    else
        log_warning "无法获取Redis服务信息"
    fi
}

# 主函数
main() {
    log_info "开始Redis服务启动..."
    
    # 设置目录
    setup_redis_directories
    
    # 检查是否已运行
    if check_redis_running; then
        log_success "Redis服务已在运行，无需重复启动"
        show_redis_status
        return 0
    fi
    
    # 生成配置文件
    generate_redis_config
    
    # 启动Redis服务
    if start_redis_service; then
        # 测试连接
        test_redis_connection
        
        # 显示状态
        show_redis_status
        
        log_success "Redis服务启动完成！"
    else
        log_error "Redis服务启动失败"
        exit 1
    fi
}

# 脚本参数处理
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        log_info "停止Redis服务..."
        if [[ -f "$REDIS_PID_FILE" ]]; then
            local pid=$(cat "$REDIS_PID_FILE")
            if kill "$pid" 2>/dev/null; then
                log_success "Redis服务已停止"
                rm -f "$REDIS_PID_FILE"
            else
                log_error "无法停止Redis服务"
            fi
        else
            log_warning "Redis PID文件不存在"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if check_redis_running; then
            show_redis_status
        else
            log_warning "Redis服务未运行"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac