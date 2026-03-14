# 快速启动指南

## 系统要求
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (可选，仅前端开发需要)
- 至少 8GB RAM, 20GB 磁盘空间

## 第一步：环境设置

### 1. 克隆项目
```bash
git clone <repository-url>
cd geopolitical-analysis-workflow
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的API密钥
# 至少需要配置数据库密码和Redis密码
# 其他API密钥可以根据需要配置
```

### 3. 安装系统依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 或者使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 第二步：启动服务

### 使用Docker Compose（推荐）
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api  # 查看API日志
docker-compose logs -f postgres  # 查看数据库日志
```

### 验证服务运行
```bash
# 检查API健康状态
curl http://localhost:8000/health

# 检查数据库连接
docker-compose exec postgres pg_isready -U geopolitical_user -d geopolitical

# 检查Redis连接
docker-compose exec redis redis-cli ping
```

## 第三步：初始化数据库

### 自动初始化（通过Docker）
数据库容器启动时会自动执行 `scripts/init-db.sql` 脚本。

### 手动初始化（如果需要）
```bash
# 进入数据库容器
docker-compose exec postgres psql -U geopolitical_user -d geopolitical

# 在psql中运行
\i /docker-entrypoint-initdb.d/init.sql
```

## 第四步：使用系统

### API文档
访问 `http://localhost:8000/docs` 查看交互式API文档。

### 监控面板
- **Grafana**: `http://localhost:3000` (用户名: admin, 密码: admin)
- **Prometheus**: `http://localhost:9090`
- **MinIO控制台**: `http://localhost:9001` (用户名: minioadmin, 密码: minioadmin)
- **Kibana**: `http://localhost:5601`

### 前端应用
前端应用将在 `http://localhost:3001` 可用（开发模式）。

## 第五步：数据收集

### 启动数据收集
```bash
# 使用Makefile
make collect-data

# 或者直接运行
python -m src.data_collection.main
```

### 检查数据收集状态
```bash
# 查看收集器状态
curl http://localhost:8000/api/v1/data/collectors

# 立即触发数据收集
curl -X POST http://localhost:8000/api/v1/data/collect
```

## 第六步：运行分析

### 启动分析工作流
```bash
# 使用Makefile
make run-analysis

# 或者直接运行
python -m src.ai_analysis.main
```

### 查看分析结果
```bash
# 获取分析结果
curl http://localhost:8000/api/v1/analysis/results
```

## 常见问题

### 1. 端口冲突
如果端口被占用，可以在 `.env` 文件中修改端口配置：
```bash
PORT=8001  # 修改API端口
```

### 2. 内存不足
如果服务启动失败，可能需要增加Docker内存限制：
- Docker Desktop: Settings → Resources → Memory
- 或减少启动的服务数量

### 3. API密钥配置
某些数据源需要API密钥，在 `.env` 文件中配置：
```bash
NEWS_API_KEY=your_newsapi_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

### 4. 数据库连接问题
检查数据库服务是否正常运行：
```bash
docker-compose logs postgres
```

## 开发命令参考

### 项目管理
```bash
# 安装开发依赖
make install-dev

# 运行测试
make test
make test-unit
make test-integration

# 代码检查
make lint

# 代码格式化
make format
```

### 数据库管理
```bash
# 运行迁移
make db-migrate
make db-upgrade

# 重置数据库（谨慎使用）
make db-reset
```

### 服务管理
```bash
# 启动/停止服务
docker-compose up -d
docker-compose down

# 重建服务
docker-compose build
docker-compose up -d

# 查看所有日志
docker-compose logs -f
```

## 下一步

1. **配置数据源**：编辑 `src/data_collection/collectors/` 中的收集器配置
2. **自定义分析**：修改 `src/ai_analysis/` 中的分析逻辑
3. **添加预测模型**：在 `src/prediction/models/` 中添加新模型
4. **定制前端**：修改 `src/web/frontend/` 中的前端代码

## 获取帮助

- 查看完整文档：`docs/` 目录
- API参考：`http://localhost:8000/docs`
- 架构设计：`docs/architecture/` 目录
- 问题反馈：创建Issue或联系开发团队