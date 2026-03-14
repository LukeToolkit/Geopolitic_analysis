# 地缘政治分析AI工作流系统 - 完整项目文档

## 1. 项目概述

### 1.1 项目简介
地缘政治分析AI工作流系统是一个基于人工智能和大模型的智能分析平台，通过收集多源数据（新闻、金融、航空、船舶、社交媒体等），分析地缘政治热点地区现状，生成短期预测，并为金融投资提供决策支持。

### 1.2 核心功能
1. **多源数据收集**
   - 新闻数据（RSS、NewsAPI）
   - 金融数据（股票、货币、商品）
   - 航空数据（ADS-B实时飞行数据）
   - 船舶数据（AIS实时船舶数据）
   - 社交媒体数据（Twitter、Reddit OSINT）
   - 公开军事部署信息
   - 天气和卫星数据

2. **智能分析引擎**
   - 地缘政治事件检测与分类
   - 情感分析和影响评估
   - 实体识别和关系抽取
   - 时空数据分析

3. **预测与模拟**
   - 短期趋势预测（1-4周）
   - 风险评估和预警
   - 金融策略回测验证
   - 模拟投资组合管理

4. **决策支持**
   - 可视化仪表板
   - 实时告警和通知
   - 可执行投资建议
   - 报告自动生成

### 1.3 目标用户
- 金融机构和投资经理
- 地缘政治分析师
- 风险管理团队
- 政府和研究机构

## 2. 系统架构

### 2.1 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                       用户界面层                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  Web前端    │  │  移动端     │  │  API客户端  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       API网关层                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │              FastAPI REST API服务                  │     │
│  │  • 认证授权  • 请求路由  • 速率限制  • 监控指标    │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    业务逻辑层                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │数据收集  │ │数据处理  │ │AI分析    │ │预测引擎  │     │
│  │模块      │ │管道      │ │引擎      │ │          │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │工作流    │ │回测系统  │ │报告生成  │ │通知服务  │     │
│  │引擎      │ │          │ │器        │ │          │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     数据存储层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │PostgreSQL│ │Timescale │ │ Redis    │ │ MinIO    │     │
│  │关系数据库│ │DB时序数据│ │ 缓存/队列│ │ 对象存储 │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     基础设施层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ Docker  │ │K8s编排   │ │ 监控栈    │ │日志系统  │     │
│  │容器化    │ │          │ │(P+G+E+L+K)│ │(ELK)     │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块架构

#### 2.2.1 数据收集层 (`src/data_collection/`)
- **基础架构**: 插件化设计，所有收集器继承自 `DataCollector` 抽象基类
- **核心组件**:
  - `DataCollector`: 收集器抽象基类，定义统一接口
  - `CollectorRegistry`: 收集器注册表，管理所有收集器
  - `DataCollectionManager`: 数据收集管理器，协调收集任务
- **数据源类型**:
  - `NEWS`: 新闻数据
  - `FINANCIAL`: 金融数据
  - `SOCIAL_MEDIA`: 社交媒体
  - `ADS_B`: 航空数据
  - `AIS`: 船舶数据
  - `MILITARY`: 军事数据
  - `OSINT`: 公开情报
  - `WEATHER`: 天气数据
  - `SATELLITE`: 卫星数据

#### 2.2.2 数据处理层 (`src/data_processing/`)
- **处理管道**: `ProcessingPipeline` 管理多个处理器的执行顺序
- **处理器类型**:
  - `DataCleaner`: 数据清洗
  - `DataTransformer`: 数据转换
  - `FeatureExtractor`: 特征提取
  - `DataValidator`: 数据验证
- **处理流程**: 原始数据 → 清洗 → 转换 → 特征提取 → 验证 → 存储

#### 2.2.3 AI分析层 (`src/ai_analysis/`)
- **大模型集成**: Anthropic Claude, OpenAI GPT
- **分析类型**:
  - 文本分析和摘要
  - 情感分析和情绪检测
  - 实体识别和关系抽取
  - 事件检测和分类
- **向量数据库**: 用于语义搜索和相似性分析

#### 2.2.4 预测模块 (`src/prediction/`)
- **模型类型**:
  - 时间序列预测 (Prophet, ARIMA)
  - 机器学习模型 (LightGBM, XGBoost)
  - 深度学习模型 (LSTM, Transformer)
- **预测目标**:
  - 地缘政治风险评分
  - 市场趋势预测
  - 事件概率预测

#### 2.2.5 工作流引擎 (`src/workflow/`)
- **编排框架**: Prefect 2.0
- **工作流类型**:
  - 数据收集工作流
  - 分析处理工作流
  - 预测生成工作流
  - 报告生成工作流
- **任务调度**: 基于时间或事件的触发机制

#### 2.2.6 API服务层 (`src/api/`)
- **框架**: FastAPI + Pydantic
- **API版本**: v1
- **认证方式**:
  - API密钥认证
  - JWT令牌认证
- **文档**: 自动生成 OpenAPI/Swagger 文档

#### 2.2.7 前端界面 (`src/web/frontend/`)
- **框架**: React 18 + TypeScript
- **UI库**: Tailwind CSS
- **状态管理**: React Context / Redux
- **图表库**: Recharts / Plotly

## 3. 技术栈

### 3.1 后端技术
- **Python 3.11+**: 主要编程语言
- **FastAPI 0.104+**: Web框架和API服务
- **Pydantic 2.5+**: 数据验证和序列化
- **SQLAlchemy 2.0+**: ORM框架
- **AsyncPG**: 异步PostgreSQL驱动
- **Redis 5.0+**: 缓存和消息队列
- **Polars 0.20+**: 高性能数据处理
- **Scikit-learn 1.3+**: 机器学习库
- **LightGBM/XGBoost**: 梯度提升模型
- **Prophet 1.1+**: 时间序列预测
- **Anthropic SDK 0.18+**: Claude API集成
- **OpenAI SDK 1.6+**: GPT API集成
- **Prefect 2.14+**: 工作流编排
- **Celery 5.3+**: 分布式任务队列

### 3.2 前端技术
- **React 18**: UI框架
- **TypeScript**: 类型安全
- **Tailwind CSS 3.3+**: 样式框架
- **React Router 6+**: 路由管理
- **Axios**: HTTP客户端
- **Recharts/Plotly**: 数据可视化
- **React Query/TanStack Query**: 数据获取和状态管理

### 3.3 数据库和存储
- **PostgreSQL 15+**: 关系型数据库
- **TimescaleDB 2.13+**: 时序数据扩展
- **Redis 7.0+**: 缓存和消息代理
- **MinIO**: S3兼容对象存储
- **pgvector**: 向量数据库扩展（可选）

### 3.4 基础设施和部署
- **Docker 24.0+**: 容器化
- **Docker Compose 2.20+**: 本地开发编排
- **Kubernetes 1.28+**: 生产环境编排
- **Helm**: Kubernetes包管理
- **Git**: 版本控制

### 3.5 监控和日志
- **Prometheus 2.47+**: 指标收集
- **Grafana 10.0+**: 指标可视化
- **Elasticsearch 8.11+**: 日志存储和搜索
- **Logstash 8.11+**: 日志处理
- **Kibana 8.11+**: 日志可视化
- **Sentry**: 错误追踪（可选）

### 3.6 开发和测试工具
- **Black**: 代码格式化
- **isort**: import排序
- **Flake8**: 代码风格检查
- **mypy**: 静态类型检查
- **pytest 7.4+**: 测试框架
- **pytest-asyncio**: 异步测试支持
- **pre-commit**: Git钩子管理

## 4. 安装与设置

### 4.1 环境要求
- **操作系统**: Linux/macOS/Windows (WSL2)
- **Docker**: 24.0+ 和 Docker Compose 2.20+
- **Python**: 3.11+
- **Node.js**: 18.0+
- **PostgreSQL**: 15.0+ (TimescaleDB扩展)
- **Redis**: 7.0+
- **Git**: 2.40+

### 4.2 快速开始

#### 4.2.1 克隆项目
```bash
git clone <repository-url>
cd geopolitical-analysis-workflow
```

#### 4.2.2 环境配置
```bash
# 1. 复制环境变量文件
cp .env.example .env

# 2. 编辑 .env 文件，配置必要的API密钥
# 最少需要配置以下密钥:
# - ANTHROPIC_API_KEY 或 OPENAI_API_KEY
# - DATABASE_URL (如果使用外部数据库)
# - REDIS_URL (如果使用外部Redis)
```

#### 4.2.3 启动开发环境
```bash
# 使用Docker Compose启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api
```

#### 4.2.4 手动安装（开发环境）
```bash
# 1. 创建Python虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 安装前端依赖
cd src/web/frontend
npm install

# 4. 启动数据库服务（使用Docker）
docker-compose up -d postgres redis minio

# 5. 初始化数据库
psql -h localhost -U geopolitical_user -d geopolitical -f scripts/init-db.sql

# 6. 启动后端服务
cd ../..
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 7. 启动前端服务（新终端）
cd src/web/frontend
npm start
```

### 4.3 服务访问
启动后可通过以下地址访问服务：

| 服务 | URL | 说明 |
|------|-----|------|
| API文档 | http://localhost:8000/docs | Swagger UI界面 |
| API服务 | http://localhost:8000 | REST API端点 |
| 前端应用 | http://localhost:3001 | React开发服务器 |
| Grafana | http://localhost:3000 | 监控仪表板 |
| Kibana | http://localhost:5601 | 日志分析 |
| MinIO控制台 | http://localhost:9001 | 对象存储管理 |
| PostgreSQL | localhost:5432 | 数据库 |

### 4.4 配置说明

#### 4.4.1 主要配置项
- **数据库配置**: `DATABASE_URL`, `POSTGRES_*`
- **Redis配置**: `REDIS_URL`, `REDIS_PASSWORD`
- **MinIO配置**: `MINIO_*`
- **大模型API**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- **外部数据源**: `NEWS_API_KEY`, `FINANCIAL_API_KEY`, `ADS_B_API_KEY`, `AIS_API_KEY`
- **安全配置**: `SECRET_KEY`, `JWT_SECRET_KEY`
- **监控配置**: `PROMETHEUS_ENABLED`, `SENTRY_DSN`

#### 4.4.2 环境变量示例
```bash
# 开发环境
APP_ENVIRONMENT=development
DEBUG=True

# 生产环境
APP_ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your_secure_secret_key_here
```

## 5. 开发指南

### 5.1 项目结构
```
geopolitical-analysis-workflow/
├── src/                           # 源代码目录
│   ├── api/                       # API服务层
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI应用入口
│   │   ├── config.py             # 应用配置
│   │   ├── middleware/           # 中间件
│   │   │   ├── __init__.py
│   │   │   └── auth.py           # 认证中间件
│   │   ├── models/               # 数据模型
│   │   │   ├── __init__.py
│   │   │   └── response.py       # API响应模型
│   │   ├── routes/               # API路由
│   │   │   ├── __init__.py
│   │   │   ├── data.py           # 数据相关路由
│   │   │   ├── analysis.py       # 分析相关路由
│   │   │   ├── prediction.py     # 预测相关路由
│   │   │   ├── workflow.py       # 工作流相关路由
│   │   │   └── system.py         # 系统管理路由
│   │   └── utils/                # 工具函数
│   ├── data_collection/          # 数据收集层
│   │   ├── __init__.py
│   │   ├── base_collector.py     # 收集器基类
│   │   ├── manager.py            # 收集管理器
│   │   └── collectors/           # 具体收集器实现
│   │       ├── __init__.py
│   │       ├── news_collector.py
│   │       ├── financial_collector.py
│   │       ├── adsb_collector.py
│   │       └── social_media_collector.py
│   ├── data_processing/          # 数据处理层
│   │   ├── __init__.py
│   │   ├── base_processor.py     # 处理器基类
│   │   ├── pipeline_manager.py   # 管道管理器
│   │   └── processors/           # 具体处理器
│   │       ├── __init__.py
│   │       ├── cleaner.py
│   │       ├── transformer.py
│   │       └── validator.py
│   ├── ai_analysis/              # AI分析层
│   │   ├── __init__.py
│   │   ├── base_analyzer.py      # 分析器基类
│   │   ├── llm_integration.py    # 大模型集成
│   │   └── analyzers/            # 具体分析器
│   │       ├── __init__.py
│   │       ├── sentiment_analyzer.py
│   │       └── entity_extractor.py
│   ├── prediction/               # 预测模块
│   │   ├── __init__.py
│   │   ├── base_predictor.py     # 预测器基类
│   │   ├── model_manager.py      # 模型管理器
│   │   └── predictors/           # 具体预测器
│   │       ├── __init__.py
│   │       ├── time_series.py
│   │       └── risk_predictor.py
│   ├── workflow/                 # 工作流引擎
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # 工作流编排器
│   │   ├── tasks/                # 任务定义
│   │   │   ├── __init__.py
│   │   │   ├── data_collection.py
│   │   │   └── analysis_pipeline.py
│   │   └── schedules/            # 调度配置
│   │       ├── __init__.py
│   │       └── hourly_tasks.py
│   ├── storage/                  # 存储抽象层
│   │   ├── __init__.py
│   │   ├── base_repository.py    # 存储库基类
│   │   ├── database.py           # 数据库操作
│   │   ├── cache.py              # 缓存操作
│   │   └── object_storage.py     # 对象存储操作
│   └── web/                      # Web界面
│       └── frontend/             # React前端
│           ├── public/
│           ├── src/
│           │   ├── components/   # React组件
│           │   ├── pages/        # 页面组件
│           │   ├── hooks/        # 自定义Hooks
│           │   ├── utils/        # 工具函数
│           │   ├── App.js        # 主应用组件
│           │   └── index.js      # 入口文件
│           ├── package.json
│           ├── Dockerfile.frontend
│           └── nginx.conf
├── tests/                        # 测试代码
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   ├── e2e/                      # 端到端测试
│   └── fixtures/                 # 测试数据
├── docs/                         # 文档
│   ├── api/                      # API文档
│   ├── architecture/             # 架构文档
│   └── deployment/               # 部署文档
├── scripts/                      # 运维脚本
│   ├── init-db.sql               # 数据库初始化
│   ├── backup.sh                 # 备份脚本
│   └── migrate.py                # 数据迁移
├── config/                       # 配置文件
│   ├── prometheus.yml            # Prometheus配置
│   ├── logstash.conf             # Logstash配置
│   └── grafana-datasources/      # Grafana数据源
├── docker-compose.yml            # 开发环境编排
├── Dockerfile.api                # API服务镜像
├── Dockerfile.workflow           # 工作流镜像
├── requirements.txt              # Python依赖
├── package.json                  # Node.js依赖
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── README.md                     # 项目简介
├── QUICKSTART.md                 # 快速开始指南
└── Makefile                      # 常用命令
```

### 5.2 开发工作流

#### 5.2.1 设置开发环境
```bash
# 1. 克隆并进入项目
git clone <repo-url>
cd geopolitical-analysis-workflow

# 2. 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS

# 3. 安装开发依赖
pip install -r requirements.txt

# 4. 安装前端依赖
cd src/web/frontend
npm install
cd ../..

# 5. 启动基础设施服务
docker-compose up -d postgres redis minio prometheus grafana

# 6. 初始化数据库
psql -h localhost -U geopolitical_user -d geopolitical -f scripts/init-db.sql

# 7. 启动开发服务器
# 终端1: 启动后端
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 终端2: 启动前端
cd src/web/frontend
npm start
```

#### 5.2.2 代码规范
- **Python代码**: 遵循PEP 8，使用Black格式化
- **TypeScript代码**: 使用ESLint和Prettier
- **提交消息**: 遵循Conventional Commits规范
- **文档**: 所有公共API必须有文档字符串

#### 5.2.3 测试流程
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_data_collection.py

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html

# 运行前端测试
cd src/web/frontend
npm test
```

### 5.3 添加新功能

#### 5.3.1 添加新数据收集器
1. 在 `src/data_collection/collectors/` 创建新文件
2. 继承 `DataCollector` 基类
3. 实现 `collect()` 和 `validate()` 方法
4. 在 `__init__.py` 中导出类
5. 在收集器配置中注册

示例:
```python
# src/data_collection/collectors/news_collector.py
from ..base_collector import DataCollector, DataSourceType, CollectorConfig

class NewsCollector(DataCollector):
    def __init__(self, config: CollectorConfig):
        super().__init__(config)

    async def collect(self):
        # 实现数据收集逻辑
        pass

    def validate(self, record):
        # 实现数据验证逻辑
        return True
```

#### 5.3.2 添加新API端点
1. 在 `src/api/routes/` 创建新路由文件或扩展现有文件
2. 定义路由函数
3. 在 `src/api/main.py` 中注册路由
4. 添加API文档字符串

#### 5.3.3 添加新处理器
1. 在 `src/data_processing/processors/` 创建新文件
2. 继承适当的处理器基类
3. 实现处理方法
4. 在管道配置中注册

## 6. API文档

### 6.1 API概览
- **基础URL**: `http://localhost:8000/api/v1`
- **认证方式**: API密钥或JWT令牌
- **响应格式**: 统一JSON格式
- **错误处理**: 标准HTTP状态码和错误消息

### 6.2 认证和授权

#### 6.2.1 API密钥认证
```http
GET /api/v1/data/sources
X-API-Key: your_api_key_here
```

#### 6.2.2 JWT认证
```http
GET /api/v1/workflow/status
Authorization: Bearer <jwt_token>
```

### 6.3 主要API端点

#### 6.3.1 系统管理
| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 公开 |
| `/status` | GET | 系统状态 | 公开 |
| `/metrics` | GET | Prometheus指标 | 公开 |
| `/api/v1/system/info` | GET | 详细系统信息 | API密钥 |
| `/api/v1/system/metrics` | GET | 系统实时指标 | API密钥 |
| `/api/v1/system/logs` | GET | 系统日志 | API密钥 |
| `/api/v1/system/config` | GET | 配置信息 | API密钥 |
| `/api/v1/system/version` | GET | 版本信息 | 公开 |

#### 6.3.2 数据管理
| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/v1/data/sources` | GET | 数据源列表 | API密钥 |
| `/api/v1/data/collectors` | GET | 收集器状态 | API密钥 |
| `/api/v1/data/collect` | POST | 立即收集数据 | API密钥 |
| `/api/v1/data/status` | GET | 收集状态 | API密钥 |
| `/api/v1/data/collectors/{name}/enable` | POST | 启用收集器 | API密钥 |
| `/api/v1/data/collectors/{name}/disable` | POST | 禁用收集器 | API密钥 |
| `/api/v1/data/test-connections` | GET | 测试连接 | API密钥 |
| `/api/v1/data/recent` | GET | 最近数据 | API密钥 |
| `/api/v1/data/stats/daily` | GET | 每日统计 | API密钥 |

#### 6.3.3 分析管理
| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/v1/analysis/run` | POST | 运行分析 | API密钥 |
| `/api/v1/analysis/results` | GET | 分析结果 | API密钥 |
| `/api/v1/analysis/status` | GET | 分析状态 | API密钥 |
| `/api/v1/analysis/history` | GET | 分析历史 | API密钥 |

#### 6.3.4 预测管理
| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/v1/prediction/generate` | POST | 生成预测 | API密钥 |
| `/api/v1/prediction/results` | GET | 预测结果 | API密钥 |
| `/api/v1/prediction/models` | GET | 模型列表 | API密钥 |
| `/api/v1/prediction/evaluate` | POST | 评估模型 | API密钥 |

#### 6.3.5 工作流管理
| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/v1/workflow/start` | POST | 启动作业流 | JWT |
| `/api/v1/workflow/stop` | POST | 停止工作流 | JWT |
| `/api/v1/workflow/status` | GET | 工作流状态 | JWT |
| `/api/v1/workflow/executions` | GET | 执行历史 | JWT |
| `/api/v1/workflow/schedule` | POST | 调度工作流 | JWT |

### 6.4 响应格式

#### 6.4.1 成功响应
```json
{
  "status": "success",
  "message": "操作成功",
  "data": {...},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 6.4.2 错误响应
```json
{
  "status": "error",
  "message": "操作失败",
  "errors": ["错误详情1", "错误详情2"],
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 6.4.3 分页响应
```json
{
  "status": "success",
  "message": "数据获取成功",
  "data": [...],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 100,
    "pages": 10
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 7. 数据模型

### 7.1 数据库架构

#### 7.1.1 核心表结构
```sql
-- 用户和认证
users (id, username, email, password_hash, is_active, is_admin, created_at)
api_keys (id, user_id, client_id, api_key, is_active, created_at, expires_at)

-- 数据源配置
data_sources (id, name, type, config, is_enabled, priority, collection_interval)

-- 原始数据（TimescaleDB超级表）
raw_data (id, source_id, source_type, raw_data, collected_at, processing_status)

-- 处理后的数据
processed_data (id, raw_data_id, source_type, processed_data, features, quality_score)

-- 地理事件
geo_events (id, event_type, title, location, region, severity, start_time, confidence)

-- 金融数据（TimescaleDB超级表）
financial_data (id, symbol, data_type, open_price, close_price, volume, timestamp)

-- 预测模型
prediction_models (id, name, model_type, version, parameters, performance_metrics)

-- 预测结果（TimescaleDB超级表）
predictions (id, model_id, target_type, predicted_value, confidence_score, generated_at)

-- 回测结果
backtest_results (id, strategy_name, model_id, start_date, end_date, metrics)

-- 工作流执行
workflow_executions (id, workflow_name, execution_id, status, input_data, output_data)

-- 系统指标（TimescaleDB超级表）
system_metrics (id, metric_name, metric_value, labels, timestamp)
```

#### 7.1.2 数据关系
```
users 1───∞ api_keys
data_sources 1───∞ raw_data
raw_data 1──1 processed_data
prediction_models 1───∞ predictions
prediction_models 1───∞ backtest_results
raw_data ∞───∞ geo_events (通过sources数组)
```

#### 7.1.3 索引和优化
- TimescaleDB超级表用于时序数据（raw_data, financial_data, predictions, system_metrics）
- GIN索引用于JSONB字段
- GiST索引用于地理空间数据
- 分区策略：按时间自动分区

### 7.2 数据流

#### 7.2.1 数据收集流程
```
外部数据源 → 数据收集器 → 原始数据存储 → 数据处理管道 → 处理后的数据存储
```

#### 7.2.2 分析流程
```
处理后的数据 → AI分析引擎 → 分析结果 → 预测模型 → 预测结果 → 回测验证
```

#### 7.2.3 工作流程
```
触发事件 → 工作流编排器 → 任务调度 → 并行执行 → 结果汇总 → 报告生成
```

## 8. 部署指南

### 8.1 开发环境部署

#### 8.1.1 使用Docker Compose
```bash
# 启动所有服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重建并启动
docker-compose up -d --build
```

#### 8.1.2 服务配置
- **PostgreSQL**: TimescaleDB扩展已启用，数据保留90天
- **Redis**: 启用AOF持久化，密码保护
- **MinIO**: S3兼容对象存储，用于文件存储
- **监控栈**: Prometheus, Grafana, ELK Stack

### 8.2 生产环境部署

#### 8.2.1 Kubernetes部署
```bash
# 1. 创建命名空间
kubectl create namespace geopolitical

# 2. 应用配置
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/

# 3. 部署数据库
kubectl apply -f k8s/database/

# 4. 部署应用
kubectl apply -f k8s/api/
kubectl apply -f k8s/workflow/
kubectl apply -f k8s/frontend/

# 5. 部署监控
kubectl apply -f k8s/monitoring/
```

#### 8.2.2 Helm Chart部署
```bash
# 1. 添加Helm仓库
helm repo add geopolitical https://charts.geopolitical.ai

# 2. 安装Chart
helm install geopolitical-analytics geopolitical/geopolitical-analytics \
  --namespace geopolitical \
  --values production-values.yaml
```

#### 8.2.3 生产配置建议
- **数据库**: 使用云托管的PostgreSQL（如RDS, Cloud SQL）
- **缓存**: 使用云托管的Redis（如ElastiCache, Memorystore）
- **存储**: 使用云对象存储（如S3, GCS）
- **监控**: 使用云监控服务（如CloudWatch, Stackdriver）
- **安全**: 启用SSL/TLS，配置防火墙规则，使用密钥管理服务

### 8.3 高可用配置

#### 8.3.1 数据库高可用
- PostgreSQL主从复制
- TimescaleDB多节点集群
- 自动故障转移

#### 8.3.2 应用高可用
- Kubernetes Deployment多副本
- 负载均衡器（如Ingress Controller）
- 健康检查和就绪检查
- 自动扩缩容（HPA）

#### 8.3.3 数据备份
```bash
# 数据库备份
pg_dump -h localhost -U geopolitical_user geopolitical > backup.sql

# 对象存储备份
mc mirror local/geopolitical-data s3/backup-bucket/
```

## 9. 测试策略

### 9.1 测试金字塔

```
        ┌─────────────────┐
        │  端到端测试     │ (10%)
        └─────────────────┘
        ┌─────────────────┐
        │  集成测试       │ (20%)
        └─────────────────┘
        ┌─────────────────┐
        │  单元测试       │ (70%)
        └─────────────────┘
```

### 9.2 测试类型

#### 9.2.1 单元测试
- **测试范围**: 单个函数、类、方法
- **框架**: pytest
- **位置**: `tests/unit/`
- **覆盖率目标**: >80%

```python
# 示例单元测试
def test_data_collector_initialization():
    config = CollectorConfig(name="test", source_type=DataSourceType.NEWS)
    collector = DataCollector(config)
    assert collector.name == "test"
    assert collector.source_type == DataSourceType.NEWS
```

#### 9.2.2 集成测试
- **测试范围**: 模块间集成、数据库操作、API调用
- **框架**: pytest + pytest-asyncio
- **位置**: `tests/integration/`
- **使用测试数据库**: 是的

#### 9.2.3 端到端测试
- **测试范围**: 完整业务流程
- **框架**: pytest + 测试客户端
- **位置**: `tests/e2e/`
- **模拟外部API**: 使用responses或httpretty

#### 9.2.4 性能测试
- **工具**: locust, k6
- **测试场景**: 并发数据收集、高负载分析
- **指标**: 响应时间、吞吐量、资源使用率

#### 9.2.5 安全测试
- **工具**: bandit (SAST), trivy (容器扫描)
- **检查项**: SQL注入、XSS、敏感信息泄露

### 9.3 测试自动化

#### 9.3.1 CI/CD流水线
```yaml
# GitHub Actions示例
name: Test and Deploy
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

#### 9.3.2 测试数据管理
- 使用工厂模式生成测试数据
- 测试前后清理数据
- 使用fixture共享测试数据

## 10. 监控与日志

### 10.1 监控体系

#### 10.1.1 系统监控
- **CPU使用率**: 每个容器的CPU使用情况
- **内存使用率**: 每个进程的内存消耗
- **磁盘IO**: 读写性能监控
- **网络流量**: 入站和出站流量

#### 10.1.2 应用监控
- **API响应时间**: 每个端点的P95/P99延迟
- **错误率**: HTTP错误码统计
- **业务指标**: 数据收集量、分析完成率
- **队列深度**: 任务队列长度

#### 10.1.3 数据库监控
- **连接数**: 活跃和空闲连接
- **查询性能**: 慢查询日志
- **复制延迟**: 主从同步状态
- **磁盘空间**: 表空间使用情况

### 10.2 日志管理

#### 10.2.1 日志级别
- **DEBUG**: 详细的调试信息
- **INFO**: 一般操作日志
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

#### 10.2.2 日志格式
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "data_collection.manager",
  "message": "数据收集启动成功",
  "collector": "news_collector",
  "duration_ms": 1234,
  "request_id": "req_123456"
}
```

#### 10.2.3 日志收集
- **Filebeat**: 收集容器日志
- **Logstash**: 日志处理和转换
- **Elasticsearch**: 日志存储和索引
- **Kibana**: 日志查询和可视化

### 10.3 告警配置

#### 10.3.1 告警规则
```yaml
# Prometheus告警规则示例
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API错误率过高"
          description: "5分钟内API错误率超过10%"
```

#### 10.3.2 通知渠道
- **电子邮件**: 重要告警通知
- **Slack**: 团队即时通知
- **PagerDuty**: 值班人员告警
- **Webhook**: 自定义集成

## 11. 贡献指南

### 11.1 开发流程

#### 11.1.1 分支策略
- **main**: 生产环境代码
- **develop**: 开发主干分支
- **feature/***: 新功能开发
- **bugfix/***: 缺陷修复
- **release/***: 发布准备

#### 11.1.2 代码审查
- 所有更改必须通过Pull Request
- 至少需要一名评审人员批准
- 必须通过所有测试和检查
- 必须更新相关文档

#### 11.1.3 提交规范
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型:
- **feat**: 新功能
- **fix**: 缺陷修复
- **docs**: 文档更新
- **style**: 代码格式
- **refactor**: 代码重构
- **test**: 测试相关
- **chore**: 构建或工具更新

### 11.2 代码质量

#### 11.2.1 静态分析
```bash
# Python代码检查
black . --check
isort . --check-only
flake8 .
mypy .

# TypeScript代码检查
cd src/web/frontend
npm run lint
```

#### 11.2.2 预提交钩子
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

### 11.3 文档要求

#### 11.3.1 代码文档
- 所有公共API必须有docstring
- 使用Google风格或NumPy风格的docstring
- 包含参数、返回值和示例

#### 11.3.2 API文档
- OpenAPI/Swagger规范
- 使用FastAPI自动生成
- 提供请求和响应示例

#### 11.3.3 架构文档
- 系统架构图
- 数据流图
- 部署架构图

## 12. 故障排除

### 12.1 常见问题

#### 12.1.1 数据库连接问题
```bash
# 检查PostgreSQL状态
docker-compose ps postgres

# 测试数据库连接
psql -h localhost -U geopolitical_user -d geopolitical -c "SELECT 1"

# 查看数据库日志
docker-compose logs postgres
```

#### 12.1.2 API服务问题
```bash
# 检查API服务状态
curl http://localhost:8000/health

# 查看API日志
docker-compose logs api

# 检查端口占用
netstat -tulpn | grep 8000
```

#### 12.1.3 数据收集问题
```bash
# 检查收集器状态
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/data/collectors

# 测试数据源连接
curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/data/test-connections

# 手动触发收集
curl -X POST -H "X-API-Key: your_key" http://localhost:8000/api/v1/data/collect
```

### 12.2 调试技巧

#### 12.2.1 Python调试
```python
# 使用调试器
import pdb; pdb.set_trace()

# 使用日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 12.2.2 容器调试
```bash
# 进入运行中的容器
docker-compose exec api bash

# 检查容器环境
docker-compose exec api env

# 查看容器文件系统
docker-compose exec api ls -la /app
```

#### 12.2.3 网络调试
```bash
# 测试服务连通性
curl -v http://localhost:8000/health

# 检查DNS解析
nslookup postgres

# 测试端口连通性
nc -zv localhost 5432
```

### 12.3 性能优化

#### 12.3.1 数据库优化
```sql
-- 查看慢查询
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- 重建索引
REINDEX TABLE raw_data;

-- 分析表统计信息
ANALYZE raw_data;
```

#### 12.3.2 应用优化
- 启用数据库连接池
- 使用Redis缓存频繁访问的数据
- 异步处理耗时操作
- 批量处理数据减少IO

#### 12.3.3 监控指标
- API响应时间P95 < 500ms
- 数据库连接池使用率 < 80%
- 系统内存使用率 < 70%
- 磁盘IO等待时间 < 20ms

### 12.4 安全审计

#### 12.4.1 定期检查
```bash
# 检查依赖漏洞
pip-audit
npm audit

# 容器镜像扫描
docker scan geopolitical-analysis-api:latest

# 代码安全扫描
bandit -r src/
```

#### 12.4.2 密钥管理
- 定期轮换API密钥和令牌
- 使用密钥管理服务（如Vault）
- 避免硬编码敏感信息
- 审计密钥使用记录

---

## 附录

### A. 环境变量参考
完整的环境变量列表见 `.env.example` 文件。

### B. API密钥申请
项目需要以下外部API密钥：
1. **新闻数据**: NewsAPI (https://newsapi.org)
2. **金融数据**: Alpha Vantage (https://www.alphavantage.co)
3. **航空数据**: OpenSky Network (https://opensky-network.org)
4. **船舶数据**: MarineTraffic (https://www.marinetraffic.com)
5. **大模型**: Anthropic Claude (https://console.anthropic.com) 或 OpenAI (https://platform.openai.com)
6. **地图数据**: Mapbox (https://www.mapbox.com)

### C. 开发路线图

#### 短期目标 (1-3个月)
- [ ] 实现核心数据收集器（新闻、金融、ADS-B）
- [ ] 完善数据处理管道
- [ ] 搭建基础AI分析框架
- [ ] 开发基本预测模型
- [ ] 创建管理仪表板

#### 中期目标 (3-6个月)
- [ ] 集成社交媒体OSINT数据
- [ ] 实现高级分析功能（情感分析、实体识别）
- [ ] 开发回测系统
- [ ] 优化系统性能
- [ ] 完善监控和告警

#### 长期目标 (6-12个月)
- [ ] 实现实时数据处理
- [ ] 开发移动应用
- [ ] 集成更多数据源
- [ ] 实现多语言支持
- [ ] 商业化部署

### D. 联系方式
- **项目仓库**: [GitHub Repository URL]
- **问题反馈**: [Issue Tracker URL]
- **文档网站**: [Documentation URL]
- **支持邮箱**: support@geopolitical.ai

### E. 许可证
本项目采用 [MIT License](LICENSE)。

---

*文档最后更新: 2024-01-01*
*文档版本: 1.0.0*