#!/bin/bash

# 后端缓存清理脚本
# 清理所有可能的缓存文件并更新版本号

set -e

echo "🧹 开始清理后端缓存..."

# 0. 更新版本号时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 读取当前版本号，提取基础版本部分（去掉时间戳）
if [ -f ".version" ]; then
    CURRENT_VERSION=$(cat .version)
    # 提取基础版本号(去掉_后面的时间戳部分)
    BASE_VERSION=$(echo $CURRENT_VERSION | sed 's/_[0-9]*_[0-9]*$//')
else
    BASE_VERSION="1.0.0"
fi

NEW_VERSION="${BASE_VERSION}_${TIMESTAMP}"
echo $NEW_VERSION > .version
echo "✅ 版本号已更新为: $NEW_VERSION (基础版本: $BASE_VERSION)"

# 1. 清理Python字节码缓存
echo "清理Python字节码缓存..."
cd ..
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -type f -delete 2>/dev/null || true
find . -name "*.pyo" -type f -delete 2>/dev/null || true
echo "✅ Python字节码缓存已清理"

# 2. 清理Django静态文件缓存
echo "清理Django静态文件缓存..."
rm -rf staticfiles/*
rm -rf static/*
echo "✅ Django静态文件缓存已清理"

# 3. 清理会话和临时文件
echo "清理会话和临时文件..."
rm -rf .sessions
rm -rf .tmp
rm -rf .cache
rm -f celerybeat-schedule*
echo "✅ 会话和临时文件已清理"

# 4. 清理日志文件
echo "清理日志文件..."
rm -rf logs/*
mkdir -p logs
echo "✅ 日志文件已清理"

# 5. 清理pip缓存
echo "清理pip缓存..."
pip cache purge 2>/dev/null || true
echo "✅ pip缓存已清理"

# 6. 清理uv缓存
echo "清理uv缓存..."
if command -v uv >/dev/null 2>&1; then
    uv cache clean 2>/dev/null || true
    echo "✅ uv缓存已清理"
else
    echo "⚠️ uv命令未找到，跳过uv缓存清理"
fi


# 8. 清理Django缓存文件
echo "清理Django缓存文件..."
rm -rf .django_cache 2>/dev/null || true
rm -rf django_cache 2>/dev/null || true
echo "✅ Django缓存文件已清理"

# 9. 清理Replit相关缓存
echo "清理Replit相关缓存..."
rm -f .replit_setup_complete
rm -f .env.fonts
rm -f .env.libreoffice
echo "✅ Replit缓存已清理"

echo "🎉 后端缓存清理完成！"
echo "📋 版本信息: $NEW_VERSION"
echo "� 建议现在重新部署到Replit"
echo "🔍 部署后访问 /api/v1/version/ 验证版本更新"