# 室内空气检测平台后端 API

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14+-orange.svg)](https://www.django-rest-framework.org/)
[![uv](https://img.shields.io/badge/uv-package%20manager-purple.svg)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于 Django + Django REST Framework 的室内空气检测数据处理和报告生成平台后端 API。

## 🚀 项目简介

这是一个专业的室内空气质量检测系统后端，提供完整的数据处理、OCR 识别、报告生成和业务管理功能。系统支持从图像识别检测数据到自动生成专业检测报告的全流程处理，并提供月度统计分析和批量处理能力。

### ✨ 核心特性

- 🔍 **智能 OCR 识别**: 集成 Gemini 和 OpenAI API，支持多重验证
- 📊 **自动报告生成**: Word 模板处理，PDF 转换，动态表格生成
- 📈 **月度统计分析**: Excel 数据处理，成本分析，利润率计算
- ⚡ **批量处理**: 异步任务队列，进度跟踪，错误重试
- 👥 **用户权限管理**: 角色分级，配置管理，Token 认证
- 📁 **文件管理**: MD5 去重，类型检测，安全存储
- 🔄 **实时通信**: WebSocket 支持，状态同步
- 🌐 **部署友好**: Replit 优化，Docker 支持，环境自适应

## 📁 项目结构

```text
air_report_web_backend/
├── config/                 # Django配置
│   ├── settings/          # 环境配置
│   │   ├── base.py       # 基础设置
│   │   ├── development.py # 开发环境
│   │   ├── production.py  # 生产环境
│   │   ├── replit.py     # Replit环境
│   │   └── test.py       # 测试环境
│   ├── urls.py           # URL路由配置
│   ├── wsgi.py           # WSGI应用
│   ├── asgi.py           # ASGI应用(WebSocket)
│   └── celery.py         # Celery配置
├── apps/                  # 应用模块
│   ├── accounts/         # 用户认证和权限管理
│   ├── core/             # 核心工具和基类
│   ├── files/            # 文件管理和存储
│   ├── ocr/              # OCR处理和识别
│   ├── reports/          # 报告生成和模板
│   ├── batch/            # 批量处理任务
│   ├── monthly/          # 月度报表统计
│   └── orders/           # 订单信息管理
├── scripts/              # 部署和工具脚本
│   ├── setup_replit.sh   # Replit环境配置
│   ├── build_replit.sh   # 构建脚本
│   ├── run_replit.sh     # 运行脚本
│   └── install_*.sh      # 依赖安装脚本
├── templates/            # 模板文件
├── static/               # 静态文件
├── media/                # 媒体文件存储
├── tests/                # 测试文件
├── pyproject.toml        # 项目配置和依赖
└── manage.py             # Django管理脚本
```

## 🔧 技术栈

### 后端框架

- **Django 4.2+**: 现代 Web 框架，提供 ORM、认证、管理后台等完整功能
- **Django REST Framework 3.14+**: 强大的 API 框架，支持序列化、权限、分页等
- **Python 3.12+**: 最新 Python 版本，性能优化和类型提示支持

### 数据库和缓存

- **SQLite**: 开发环境默认数据库
- **PostgreSQL**: 生产环境推荐数据库
- **Redis**: 缓存、会话存储、Celery 消息队列

### 异步任务和实时通信

- **Celery**: 分布式任务队列，支持异步处理
- **Django Channels**: WebSocket 支持，实时状态更新
- **Redis**: 消息代理和结果后端

### AI 和文档处理

- **Google Gemini API**: 主要 OCR 识别服务
- **OpenAI API**: 备用 OCR 识别服务
- **LibreOffice**: 文档转换和处理
- **python-docx**: Word 文档操作
- **ReportLab**: PDF 生成和处理

### 开发工具

- **uv**: 现代 Python 包管理器，快速依赖解析
- **pytest**: 测试框架，支持覆盖率和并行测试
- **Black + isort**: 代码格式化和导入排序
- **MyPy**: 静态类型检查
- **pre-commit**: Git 钩子，代码质量保证

### 部署和监控

- **Gunicorn**: WSGI 服务器，生产环境部署
- **WhiteNoise**: 静态文件服务
- **Sentry**: 错误跟踪和性能监控
- **drf-spectacular**: OpenAPI 文档生成

## 🏗️ 核心功能模块

### 1. 用户认证和权限管理 (`apps.accounts`)

- **自定义用户模型**: 扩展 Django 用户模型，支持头像、电话、公司等字段
- **角色管理**: 三级权限体系 (admin/operator/viewer)
- **Token 认证**: REST API Token 认证，支持会话和 Token 双重认证
- **用户配置**: 个性化 OCR 设置、界面偏好、通知设置
- **API 端点**: `/api/v1/auth/` - 登录、登出、用户管理、配置管理

### 2. 文件管理 (`apps.files`)

- **安全上传**: 文件类型检测、大小限制、恶意文件过滤
- **智能去重**: MD5 哈希去重，避免重复存储
- **批量上传**: 支持多文件同时上传，进度跟踪
- **文件统计**: 上传统计、存储分析、类型分布
- **API 端点**: `/api/v1/files/` - 文件上传、管理、统计

### 3. OCR 处理 (`apps.ocr`)

- **多引擎支持**: Gemini API (主要) + OpenAI API (备用)
- **多重验证**: 可配置多次 OCR 识别，提高准确率
- **智能学习**: 点位名称学习和记忆，提高识别效果
- **联系人匹配**: 电话号码匹配，客户信息关联
- **结果缓存**: OCR 结果缓存，避免重复处理
- **API 端点**: `/api/v1/ocr/` - 图像处理、结果管理、学习数据

### 4. 报告生成 (`apps.reports`)

- **模板引擎**: Word 模板处理，支持动态内容替换
- **PDF 转换**: LibreOffice headless 模式，高质量 PDF 生成
- **动态表格**: 根据检测数据自动生成表格和图表
- **批量生成**: 支持批量报告生成，异步处理
- **模板管理**: 可配置报告模板，支持多种格式
- **API 端点**: `/api/v1/reports/` - 报告生成、模板管理、下载

### 5. 批量处理 (`apps.batch`)

- **任务队列**: Celery 异步任务，支持大批量处理
- **进度跟踪**: 实时进度更新，WebSocket 状态同步
- **错误处理**: 失败重试机制，错误日志记录
- **并发控制**: 可配置并发数，资源使用优化
- **结果统计**: 处理统计、成功率分析、性能监控
- **API 端点**: `/api/v1/batch/` - 批量任务管理、进度查询

### 6. 月度报表 (`apps.monthly`)

- **数据处理**: Excel 文件解析，CSV 数据处理
- **地址匹配**: 智能地址匹配算法，重复订单识别
- **成本分析**: 药水成本、CMA 成本、人工成本计算
- **利润分析**: 分润比计算，利润率统计
- **报表生成**: Excel 报表生成，PDF 摘要报告
- **API 端点**: `/api/v1/monthly/` - 月度报表生成、统计分析

### 7. 订单管理 (`apps.orders`)

- **订单解析**: 文本订单信息结构化处理
- **数据验证**: 订单数据完整性检查
- **重复检测**: 基于客户信息的重复订单检测
- **格式转换**: 多种数据格式支持和转换
- **API 端点**: `/api/v1/orders/` - 订单处理、数据管理

## 🚀 快速开始

### 系统要求

- **Python**: 3.12+ (推荐使用最新版本)
- **操作系统**: Windows 10+, macOS 10.15+, Ubuntu 20.04+
- **内存**: 最少 2GB，推荐 4GB+
- **存储**: 最少 1GB 可用空间

### 1. 安装 uv 包管理器

uv 是现代 Python 包管理器，提供更快的依赖安装和更好的依赖解析。

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux (使用curl)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用pip安装
pip install uv

# 验证安装
uv --version
```

### 2. 项目设置

```bash
# 克隆项目
git clone <repository-url>
cd air_report_web_backend

# 创建虚拟环境并安装所有依赖
uv sync

# 安装开发和测试依赖（可选）
uv sync --extra dev --extra test

# 验证安装
uv run python --version
```

### 3. 环境配置

```bash
# 创建环境变量文件（如果不存在）
touch .env

# 编辑环境变量文件，添加必要配置
# 参考下面的环境变量配置部分
```

### 4. 数据库初始化

```bash
# 创建数据库迁移文件
uv run python manage.py makemigrations

# 执行数据库迁移
uv run python manage.py migrate

# 创建超级用户（可选）
uv run python manage.py createsuperuser

# 收集静态文件（生产环境）
uv run python manage.py collectstatic --noinput
```

### 5. 启动开发服务器

```bash
# 启动Django开发服务器
uv run python manage.py runserver

# 或指定端口
uv run python manage.py runserver 0.0.0.0:8000
```

服务器启动后，访问以下地址：

- **API 根地址**: <http://localhost:8000/api/v1/>
- **管理后台**: <http://localhost:8000/admin/>
- **API 文档**: <http://localhost:8000/api/docs/>

### 6. 启动异步服务（可选）

如果需要使用异步功能（OCR 处理、报告生成等），需要启动 Redis 和 Celery：

```bash
# 启动Redis服务器（需要单独安装Redis）
redis-server

# 新终端：启动Celery worker
uv run celery -A config worker -l info

# 新终端：启动Celery beat（定时任务）
uv run celery -A config beat -l info
```

## 🌐 Replit 部署

本项目专门针对 Replit 平台进行了优化，提供完整的部署解决方案，包括字体安装、LibreOffice 配置和环境自适应。

### 一键部署

在 Replit 上导入项目后，系统会自动执行`.replit`文件中定义的部署流程：

```bash
# 自动执行的部署命令
chmod +x scripts/setup_replit.sh && ./scripts/setup_replit.sh && \
uv run python manage.py runserver 0.0.0.0:8000
```

### 部署架构

项目在 Replit 上采用分离的构建和运行阶段：

1. **构建阶段**：执行`scripts/build_replit.sh`，安装依赖和配置环境
2. **运行阶段**：执行`scripts/run_replit.sh`，启动应用服务

### 完整部署流程

完整部署脚本`scripts/setup_replit.sh`自动执行以下步骤：

1. ✅ **环境检测**：检查 Replit 环境和系统依赖
2. ✅ **依赖安装**：使用 uv 安装 Python 依赖
3. ✅ **系统配置**：配置系统依赖和环境变量
4. ✅ **字体安装**：安装中英文字体，解决 PDF 生成问题
5. ✅ **Redis 服务**：启动 Redis 服务，支持 WebSocket 和 Celery
6. ✅ **LibreOffice 配置**：配置 LibreOffice headless 模式
7. ✅ **数据库迁移**：执行数据库迁移和初始化
8. ✅ **超级用户创建**：自动创建管理员账户
9. ✅ **静态文件收集**：收集静态文件
10. ✅ **验证安装**：验证环境配置完整性

### 字体支持

本项目解决了 Replit 环境中 PDF 生成中文字体显示为方块的问题，支持以下字体：

**中文字体**

- 宋体 (SimSun)
- 黑体 (SimHei)
- Noto Sans CJK SC
- Source Han Sans CN
- WenQuanYi Zen Hei

**英文字体**

- Arial
- Times New Roman
- Calibri
- Liberation Sans/Serif
- DejaVu Sans/Serif

### LibreOffice 集成

项目集成了 LibreOffice headless 模式，用于高质量文档转换：

```bash
# LibreOffice服务自动启动
libreoffice --headless --accept="socket,host=127.0.0.1,port=2002;urp;" --nofirststartwizard
```

### 环境变量配置

Replit 环境使用以下环境变量文件：

- **主配置**：`.env`
- **字体配置**：`.env.fonts`
- **LibreOffice 配置**：`.env.libreoffice`

### 性能优化

针对 Replit 环境的性能优化：

- **同步任务执行**：`CELERY_TASK_ALWAYS_EAGER = True`
- **内存缓存**：使用`LocMemCache`减少 Redis 依赖
- **超时增加**：增加 API 超时时间适应 Replit 环境
- **静态文件优化**：使用 WhiteNoise 处理静态文件
- **开发服务器**：使用 Django 开发服务器替代 Gunicorn

## 📚 API 文档

本项目使用 drf-spectacular 自动生成 OpenAPI 3.0 规范的 API 文档，提供完整的接口说明和交互式测试。

### 文档访问地址

启动服务器后，可以访问以下地址查看 API 文档：

- **Swagger UI**: <http://localhost:8000/api/docs/> - 交互式 API 文档
- **ReDoc**: <http://localhost:8000/api/redoc/> - 美观的 API 文档展示
- **OpenAPI Schema**: <http://localhost:8000/api/schema/> - JSON 格式的 API 规范

### API 端点概览

| 模块 | 端点               | 功能描述                       |
| ---- | ------------------ | ------------------------------ |
| 认证 | `/api/v1/auth/`    | 用户登录、登出、注册、配置管理 |
| 文件 | `/api/v1/files/`   | 文件上传、管理、统计           |
| OCR  | `/api/v1/ocr/`     | 图像处理、OCR 识别、结果管理   |
| 报告 | `/api/v1/reports/` | 报告生成、模板管理、下载       |
| 批量 | `/api/v1/batch/`   | 批量任务管理、进度查询         |
| 月报 | `/api/v1/monthly/` | 月度报表生成、统计分析         |
| 订单 | `/api/v1/orders/`  | 订单处理、数据管理             |

### 认证方式

API 支持以下认证方式：

- **Token 认证**: 在请求头中添加`Authorization: Token <your-token>`
- **会话认证**: 通过 Django 会话系统认证（主要用于管理后台）

### 请求格式

- **Content-Type**: `application/json`
- **字符编码**: UTF-8
- **分页**: 使用`page`和`page_size`参数

## ⚙️ 环境变量配置

### 基础配置

```bash
# Django核心配置
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*.replit.app

# 数据库配置
DATABASE_URL=sqlite:///db.sqlite3
# 或使用PostgreSQL: postgresql://user:password@host:port/dbname

# 时区和语言
TIME_ZONE=Asia/Shanghai
LANGUAGE_CODE=zh-hans
```

### Redis 和 Celery 配置

```bash
# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_ALWAYS_EAGER=False  # 生产环境设为False
```

### AI 服务配置

```bash
# Gemini API配置（主要OCR服务）
GEMINI_API_KEY=your-gemini-api-key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_MODEL_NAME=gemini-2.0-flash-exp

# OpenAI API配置（备用OCR服务）
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4-vision-preview

# 使用OpenAI作为主要OCR服务（可选）
USE_OPENAI_OCR=False
```

### 超时和性能配置

```bash
# API超时配置
API_TIMEOUT_SECONDS=30
OCR_TIMEOUT_SECONDS=60
IMAGE_PROCESSING_TIMEOUT_SECONDS=120

# 日志级别
LOG_LEVEL=INFO
```

### 生产环境配置

```bash
# 安全配置
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,*.yourdomain.com

# 数据库（生产环境推荐PostgreSQL）
DATABASE_URL=postgresql://user:password@host:port/dbname

# 邮件配置
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# 错误跟踪
SENTRY_DSN=your-sentry-dsn

# 云存储（可选）
USE_S3_STORAGE=True
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

## 🛠️ 开发指南

### 项目架构

本项目采用 Django 应用模块化架构，每个应用负责特定的业务功能：

```text
apps/
├── accounts/     # 用户认证和权限管理
├── core/         # 核心工具和基类
├── files/        # 文件管理和存储
├── ocr/          # OCR处理和识别
├── reports/      # 报告生成和模板
├── batch/        # 批量处理任务
├── monthly/      # 月度报表统计
└── orders/       # 订单信息管理
```

### 添加新应用

1. **创建应用**

   ```bash
   cd apps/
   uv run python ../manage.py startapp your_app_name
   ```

2. **注册应用**
   在`config/settings/base.py`的`LOCAL_APPS`中添加：

   ```python
   LOCAL_APPS = [
       # ... 其他应用
       'apps.your_app_name',
   ]
   ```

3. **创建 URL 配置**
   在应用目录下创建`urls.py`：

   ```python
   from django.urls import path, include
   from rest_framework.routers import DefaultRouter
   from . import views

   router = DefaultRouter(trailing_slash=False)
   router.register(r'items', views.YourViewSet, basename='your-items')

   urlpatterns = [
       path('', include(router.urls)),
   ]
   ```

4. **添加到主 URL 配置**
   在`config/urls.py`中添加：

   ```python
   path('api/v1/your-app/', include('apps.your_app_name.urls')),
   ```

### 添加 Celery 异步任务

1. **定义任务**
   在应用的`tasks.py`文件中：

   ```python
   from celery import shared_task

   @shared_task(bind=True, max_retries=3)
   def your_async_task(self, param1, param2):
       try:
           # 任务逻辑
           return {'status': 'success', 'result': 'data'}
       except Exception as e:
           # 重试机制
           if self.request.retries < self.max_retries:
               raise self.retry(countdown=60)
           raise e
   ```

2. **配置任务路由**
   在`config/celery.py`中添加：

   ```python
   app.conf.task_routes.update({
       'apps.your_app_name.tasks.your_async_task': {'queue': 'your_queue'},
   })
   ```

3. **在视图中调用**

   ```python
   from .tasks import your_async_task

   # 异步调用
   task = your_async_task.delay(param1, param2)
   return Response({'task_id': task.id})
   ```

### 数据库操作

```bash
# 创建迁移文件
uv run python manage.py makemigrations

# 查看迁移SQL（可选）
uv run python manage.py sqlmigrate app_name migration_name

# 执行迁移
uv run python manage.py migrate

# 回滚迁移（谨慎使用）
uv run python manage.py migrate app_name migration_number
```

### 代码规范

项目使用以下工具确保代码质量：

```bash
# 代码格式化
uv run black .

# 导入排序
uv run isort .

# 代码检查
uv run flake8

# 类型检查
uv run mypy apps/

# 运行所有检查
uv run pre-commit run --all-files
```

## 📦 UV 包管理器使用

本项目使用 uv 作为包管理器，提供更快的依赖安装和更好的依赖解析。uv 比传统的 pip 快 10-100 倍，并提供更好的依赖冲突解决。

### 依赖管理

```bash
# 安装所有依赖
uv sync

# 安装特定依赖组
uv sync --extra dev          # 开发工具 (black, isort, flake8, mypy等)
uv sync --extra test         # 测试工具 (pytest, factory-boy等)
uv sync --extra production   # 生产环境 (gunicorn, whitenoise等)
uv sync --extra docs         # 文档工具 (sphinx等)
uv sync --extra all          # 所有依赖

# 添加新依赖
uv add "django>=4.2.0"
uv add "requests>=2.31.0"

# 添加开发依赖
uv add --group dev "pytest>=7.4.0"
uv add --group test "factory-boy>=3.3.0"

# 移除依赖
uv remove package-name

# 更新依赖
uv sync --upgrade            # 更新所有依赖
uv sync --upgrade-package django  # 更新特定包
```

### 运行命令

```bash
# Django管理命令
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py createsuperuser
uv run python manage.py collectstatic
uv run python manage.py shell

# 测试命令
uv run pytest                    # 运行所有测试
uv run pytest apps/ocr/         # 运行特定应用测试
uv run pytest --cov=apps        # 运行覆盖率测试
uv run pytest -v --tb=short     # 详细输出

# 代码质量检查
uv run black .                   # 代码格式化
uv run black --check .          # 检查格式（不修改）
uv run isort .                   # 导入排序
uv run flake8                    # 代码风格检查
uv run mypy apps/                # 类型检查

# Celery任务
uv run celery -A config worker -l info
uv run celery -A config beat -l info
uv run celery -A config flower   # 监控界面
```

### 环境管理

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 查看环境信息
uv pip list                      # 查看已安装包
uv pip show package-name         # 查看包信息

# 生产环境部署
uv sync --frozen                 # 使用锁定版本
uv sync --no-dev                 # 不安装开发依赖
```

### 项目配置

项目的依赖配置在 `pyproject.toml` 中定义：

```toml
[project]
dependencies = [
    "django>=4.2.0",
    "djangorestframework>=3.14.0",
    # ... 其他核心依赖
]

[project.optional-dependencies]
dev = ["black>=23.0.0", "isort>=5.12.0", ...]
test = ["pytest>=7.4.0", "pytest-django>=4.5.0", ...]
production = ["gunicorn>=21.0.0", "whitenoise>=6.5.0", ...]
```

### 性能优势

- **速度**: 比 pip 快 10-100 倍
- **并行安装**: 支持并行下载和安装
- **缓存**: 智能缓存机制，避免重复下载
- **依赖解析**: 更好的依赖冲突解决
- **锁定文件**: 自动生成 `uv.lock` 确保环境一致性

## 🧪 测试

本项目使用 pytest 作为测试框架，配合 factory-boy 生成测试数据，目标测试覆盖率为 80% 以上。

### 测试架构

```text
tests/
├── factories.py          # 测试数据工厂
└── conftest.py          # pytest配置（如果存在）

apps/
├── accounts/tests.py    # 用户认证测试
├── ocr/tests.py        # OCR处理测试
├── reports/tests.py    # 报告生成测试
├── batch/tests.py      # 批量处理测试
├── monthly/tests.py    # 月度报表测试
└── ...
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定应用测试
uv run pytest apps/ocr/
uv run pytest apps/reports/

# 运行特定测试文件
uv run pytest apps/ocr/tests.py

# 运行特定测试方法
uv run pytest apps/ocr/tests.py::TestOCRProcessing::test_image_processing

# 并行测试（加速）
uv run pytest -n auto

# 详细输出
uv run pytest -v --tb=short
```

### 测试覆盖率

```bash
# 运行覆盖率测试
uv run pytest --cov=apps --cov-report=html

# 生成终端覆盖率报告
uv run pytest --cov=apps --cov-report=term-missing

# 设置覆盖率阈值
uv run pytest --cov=apps --cov-fail-under=80

# 查看HTML覆盖率报告
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
```

### 测试标记

项目使用 pytest 标记来分类测试：

```bash
# 运行单元测试
uv run pytest -m unit

# 运行集成测试
uv run pytest -m integration

# 运行API测试
uv run pytest -m api

# 跳过慢速测试
uv run pytest -m "not slow"

# 运行特定功能测试
uv run pytest -m ocr
uv run pytest -m reports
```

### 测试数据工厂

使用 factory-boy 创建测试数据：

```python
# 使用示例
from tests.factories import UserFactory, OCRResultFactory

def test_user_creation():
    user = UserFactory()
    assert user.username
    assert user.email

def test_ocr_result():
    ocr_result = OCRResultFactory(
        phone='13812345678',
        check_type='initial'
    )
    assert ocr_result.phone == '13812345678'
    assert ocr_result.points_data
```

### 测试配置

测试环境配置在 `config/settings/test.py` 中：

- 使用内存 SQLite 数据库
- 禁用缓存和日志
- 使用同步 Celery 执行
- 模拟 API 调用

### 持续集成

项目支持 GitHub Actions 等 CI/CD 平台：

```yaml
# .github/workflows/test.yml 示例
- name: Run tests
  run: |
    uv sync --extra test
    uv run pytest --cov=apps --cov-report=xml
```

## 🚀 生产环境部署

### Docker 部署（推荐）

```dockerfile
# Dockerfile 示例
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libpq-dev \
    libreoffice \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 安装uv
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN uv sync --extra production

# 收集静态文件
RUN uv run python manage.py collectstatic --noinput

# 启动命令
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### 传统服务器部署

```bash
# 1. 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv postgresql redis-server libreoffice

# 2. 创建项目目录
sudo mkdir -p /var/www/air-report-backend
sudo chown $USER:$USER /var/www/air-report-backend
cd /var/www/air-report-backend

# 3. 克隆项目
git clone <repository-url> .

# 4. 安装uv和依赖
pip install uv
uv sync --extra production

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 6. 数据库迁移
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput

# 7. 配置Nginx和Gunicorn
# 参考下面的配置文件
```

### Nginx 配置

```nginx
# /etc/nginx/sites-available/air-report-backend
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /var/www/air-report-backend/staticfiles/;
    }

    location /media/ {
        alias /var/www/air-report-backend/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd 服务配置

```ini
# /etc/systemd/system/air-report-backend.service
[Unit]
Description=Air Report Backend
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/air-report-backend
Environment=PATH=/var/www/air-report-backend/.venv/bin
ExecStart=/var/www/air-report-backend/.venv/bin/uv run gunicorn config.wsgi:application --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请遵循以下步骤：

### 开发流程

1. **Fork 项目**

   ```bash
   git clone https://github.com/your-username/air-report-system.git
   cd air-report-system/air_report_web_backend
   ```

2. **创建功能分支**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **安装开发依赖**

   ```bash
   uv sync --extra dev --extra test
   ```

4. **进行开发**

   - 遵循代码规范
   - 添加必要的测试
   - 更新文档

5. **运行测试和检查**

   ```bash
   uv run pytest
   uv run black .
   uv run isort .
   uv run flake8
   uv run mypy apps/
   ```

6. **提交更改**

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

7. **推送并创建 Pull Request**

   ```bash
   git push origin feature/your-feature-name
   ```

### 编码规范

- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 遵循 PEP 8 代码风格
- 添加类型提示
- 编写清晰的文档字符串
- 保持测试覆盖率 80% 以上

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` 错误修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢以下开源项目和服务：

- [Django](https://www.djangoproject.com/) - Web 框架
- [Django REST Framework](https://www.django-rest-framework.org/) - API 框架
- [uv](https://github.com/astral-sh/uv) - Python 包管理器
- [Celery](https://celeryproject.org/) - 分布式任务队列
- [Redis](https://redis.io/) - 内存数据库
- [LibreOffice](https://www.libreoffice.org/) - 文档处理
- [Google Gemini](https://ai.google.dev/) - AI 服务
- [Replit](https://replit.com/) - 在线开发平台

## 📞 支持

如果您遇到问题或有疑问，请通过以下方式联系我们：

- 📧 邮箱: [team@airquality.com](mailto:team@airquality.com)
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-org/air-quality-backend/issues)
- 📖 文档: [项目文档](https://air-quality-backend.readthedocs.io/)

---

**室内空气检测平台后端 API** - 让空气质量检测更智能、更高效！
