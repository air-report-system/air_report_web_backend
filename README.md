# 室内空气检测平台后端

基于 Django + Django REST Framework 的室内空气检测数据处理和报告生成平台后端 API。

## 项目结构

```
backend/
├── config/                 # Django配置
│   ├── settings/
│   │   ├── base.py        # 基础设置
│   │   ├── development.py # 开发环境设置
│   │   └── production.py  # 生产环境设置
│   ├── urls.py            # URL配置
│   ├── wsgi.py            # WSGI配置
│   └── celery.py          # Celery配置
├── apps/                   # 应用模块
│   ├── accounts/          # 用户认证和权限
│   ├── core/              # 核心工具和基类
│   ├── files/             # 文件管理
│   ├── ocr/               # OCR处理服务
│   ├── reports/           # 报告生成管理
│   ├── batch/             # 批量处理
│   └── monthly/           # 月度报表
├── services/              # 业务逻辑服务
├── utils/                 # 工具函数
├── tasks/                 # Celery任务
└── manage.py              # Django管理脚本
```

## 核心功能

### 1. 用户认证和权限管理

- 自定义用户模型，支持角色管理
- 用户配置和偏好设置
- JWT 认证支持

### 2. 文件管理

- 文件上传和存储
- 文件类型检测和验证
- MD5 哈希去重

### 3. OCR 处理

- 集成 Gemini API 进行图像识别
- 多重 OCR 验证机制
- 联系人信息匹配

### 4. 报告生成

- Word 模板处理
- PDF 转换
- 动态表格生成

### 5. 批量处理

- 批量图片处理队列
- 进度跟踪和状态管理
- 错误处理和重试机制

### 6. 月度报表

- Excel 数据处理
- 地址匹配算法
- 成本分析和统计

## 快速开始

### 1. 安装 uv 包管理器

```bash
# Windows (使用pip)
pip install uv

# macOS/Linux (使用curl)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用pip
pip install uv
```

### 2. 环境准备

```bash
# 克隆项目后进入后端目录
cd django/backend

# 创建虚拟环境并安装所有依赖
uv sync

# 安装开发和测试依赖
uv sync --extra dev --extra test

# 复制环境变量文件
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

### 2. 数据库设置

```bash
# 创建数据库迁移
uv run python manage.py makemigrations

# 执行数据库迁移
uv run python manage.py migrate

# 创建超级用户
uv run python manage.py createsuperuser
```

### 3. 启动开发服务器

```bash
# 使用启动脚本
python start_dev.py

# 或者直接启动
uv run python manage.py runserver
```

### 4. 启动 Celery 工作进程

```bash
# 启动Celery worker
uv run celery -A config worker -l info

# 启动Celery beat (定时任务)
uv run celery -A config beat -l info
```

## Replit 部署

### 字体安装

本项目包含完整的字体安装解决方案，解决在 Replit 环境中 PDF 生成字体显示为方块的问题。

#### 完整部署流程

```bash
# 运行完整的Replit部署脚本（包含字体安装）
bash scripts/setup_replit.sh
```

该脚本将自动执行以下步骤：

1. ✅ 检查环境和依赖
2. ✅ 安装 Python 依赖包
3. ✅ 配置系统依赖
4. ✅ **安装字体文件**（新增）
5. ✅ 设置环境变量
6. ✅ 启动 LibreOffice 服务
7. ✅ 数据库迁移
8. ✅ 创建超级用户
9. ✅ 收集静态文件
10. ✅ 验证安装

#### 手动字体安装

如果需要单独安装字体：

```bash
# 完整字体安装（包含Nix字体包链接）
bash scripts/install_fonts_replit.sh
```

> **注意**：字体安装已集成到主部署脚本中，通常不需要手动执行。

#### 字体支持

本项目支持以下字体：

**中文字体：**

- 宋体 (SimSun)
- 黑体 (SimHei)
- Noto Sans CJK SC
- Source Han Sans CN
- WenQuanYi Zen Hei

**英文字体：**

- Arial
- Times New Roman
- Calibri
- Liberation Sans/Serif
- DejaVu Sans/Serif

#### 字体配置文件

字体配置文件位置：

- 配置文件：`~/.config/fontconfig/fonts.conf`
- 字体目录：`~/.local/share/fonts`
- 环境变量：`.env.fonts`

### Replit 环境特性

- 自动安装 Nix 包管理的字体包
- 系统级字体链接支持
- 字体渲染优化配置
- PDF 生成中文字体支持
- 字体缓存自动管理

## API 文档

启动服务器后，可以访问以下地址查看 API 文档：

- Swagger UI: <http://localhost:8000/api/docs/>
- ReDoc: <http://localhost:8000/api/redoc/>
- OpenAPI Schema: <http://localhost:8000/api/schema/>

## 环境变量配置

主要的环境变量配置项：

```bash
# Django配置
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库配置
DATABASE_URL=sqlite:///db.sqlite3

# Redis配置
REDIS_URL=redis://localhost:6379/0

# Gemini API配置
GEMINI_API_KEY=your-gemini-api-key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_MODEL_NAME=gemini-2.0-flash-exp

# API超时配置
API_TIMEOUT_SECONDS=30
OCR_TIMEOUT_SECONDS=60
```

## 开发指南

### 添加新的应用

1. 在 `apps/` 目录下创建新应用
2. 在 `config/settings/base.py` 的 `LOCAL_APPS` 中添加应用
3. 创建模型、视图、序列化器等
4. 在主 URL 配置中添加应用的 URL

### 添加新的 Celery 任务

1. 在对应应用的 `tasks.py` 文件中定义任务
2. 在 `config/celery.py` 中配置任务路由
3. 在视图中调用异步任务

### 数据库迁移

```bash
# 创建迁移文件
uv run python manage.py makemigrations

# 查看迁移SQL
uv run python manage.py sqlmigrate app_name migration_name

# 执行迁移
uv run python manage.py migrate
```

## UV 包管理器使用

本项目使用 uv 作为包管理器，提供更快的依赖安装和更好的依赖解析。

### 依赖管理

```bash
# 安装所有依赖
uv sync

# 安装特定依赖组
uv sync --extra dev          # 开发工具
uv sync --extra test         # 测试工具
uv sync --extra production   # 生产环境
uv sync --extra docs         # 文档工具
uv sync --extra all          # 所有依赖

# 添加新依赖
uv add "package-name>=1.0.0"

# 添加开发依赖
uv add --group dev "package-name>=1.0.0"

# 移除依赖
uv remove package-name

# 更新依赖
uv sync --upgrade
```

### 运行命令

```bash
# 运行Django命令
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 运行测试
uv run pytest
uv run python run_tests.py --all

# 代码质量检查
uv run black .              # 代码格式化
uv run isort .              # 导入排序
uv run flake8               # 代码检查
uv run mypy apps/           # 类型检查

# 启动Celery
uv run celery -A config worker -l info
uv run celery -A config beat -l info
```

### 环境管理

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (macOS/Linux)
source .venv/bin/activate

# 从锁定文件安装 (生产环境)
uv sync --frozen
```

详细的 uv 使用指南请参考 [UV_USAGE.md](UV_USAGE.md)。

## 测试

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定应用测试
uv run pytest apps/ocr/

# 运行覆盖率测试
uv run pytest --cov=apps --cov-report=html

# 使用自定义测试脚本
uv run python run_tests.py --all
uv run python run_tests.py --app ocr
uv run python run_tests.py --coverage
```

### 测试覆盖率

项目目标测试覆盖率为 80%以上。运行覆盖率测试后，可以在 `htmlcov/index.html` 查看详细的覆盖率报告。
