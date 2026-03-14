# 地缘政治分析AI工作流系统 Makefile

.PHONY: help install install-dev setup-db start stop clean test lint format docker-up docker-down docker-build docker-logs

.DEFAULT_GOAL := help

# 定义变量
PROJECT_NAME := geopolitical-analysis-workflow
PYTHON := python3.11
PIP := pip3
DOCKER_COMPOSE := docker-compose

# 帮助信息
help:
	@echo "地缘政治分析AI工作流系统 - 开发命令"
	@echo ""
	@echo "环境设置:"
	@echo "  make install         安装生产依赖"
	@echo "  make install-dev     安装开发依赖"
	@echo "  make setup-db        初始化数据库"
	@echo "  make setup-env       设置环境变量"
	@echo ""
	@echo "开发命令:"
	@echo "  make start           启动开发服务器"
	@echo "  make stop            停止开发服务器"
	@echo "  make test            运行测试"
	@echo "  make test-unit       运行单元测试"
	@echo "  make test-integration 运行集成测试"
	@echo "  make test-e2e        运行端到端测试"
	@echo "  make lint            代码检查"
	@echo "  make format          代码格式化"
	@echo ""
	@echo "Docker命令:"
	@echo "  make docker-up       启动Docker服务"
	@echo "  make docker-down     停止Docker服务"
	@echo "  make docker-build    构建Docker镜像"
	@echo "  make docker-logs     查看Docker日志"
	@echo ""
	@echo "数据库命令:"
	@echo "  make db-migrate      运行数据库迁移"
	@echo "  make db-rollback     回滚数据库迁移"
	@echo "  make db-reset        重置数据库"
	@echo ""
	@echo "部署命令:"
	@echo "  make build           构建生产版本"
	@echo "  make clean           清理临时文件"

# 环境设置
install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install pre-commit
	pre-commit install

setup-env:
	@if [ ! -f .env ]; then \
		echo "复制 .env.example 到 .env"; \
		cp .env.example .env; \
		echo "请编辑 .env 文件并设置必要的环境变量"; \
	else \
		echo ".env 文件已存在"; \
	fi

setup-db:
	@echo "初始化数据库..."
	$(DOCKER_COMPOSE) up -d postgres redis minio
	@echo "等待数据库启动..."
	sleep 10
	@echo "运行数据库迁移..."
	$(PYTHON) -m alembic upgrade head
	@echo "数据库初始化完成"

# 开发命令
start:
	$(PYTHON) -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

stop:
	@pkill -f "uvicorn src.api.main:app" || true

test:
	$(PYTHON) -m pytest tests/ -v

test-unit:
	$(PYTHON) -m pytest tests/unit/ -v

test-integration:
	$(PYTHON) -m pytest tests/integration/ -v

test-e2e:
	$(PYTHON) -m pytest tests/e2e/ -v

lint:
	$(PYTHON) -m flake8 src/
	$(PYTHON) -m mypy src/
	$(PYTHON) -m black --check src/ tests/
	$(PYTHON) -m isort --check-only src/ tests/

format:
	$(PYTHON) -m black src/ tests/
	$(PYTHON) -m isort src/ tests/

# Docker命令
docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-build:
	$(DOCKER_COMPOSE) build

docker-logs:
	$(DOCKER_COMPOSE) logs -f

# 数据库命令
db-migrate:
	@echo "创建新的数据库迁移..."
	read -p "请输入迁移描述: " message; \
	$(PYTHON) -m alembic revision --autogenerate -m "$$message"

db-upgrade:
	$(PYTHON) -m alembic upgrade head

db-rollback:
	@read -p "请输入要回滚到的版本 (或 'head-1' 表示上一个版本): " version; \
	$(PYTHON) -m alembic downgrade $$version

db-reset:
	@read -p "这将删除所有数据。确定要继续吗? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(DOCKER_COMPOSE) down -v; \
		echo "数据库已重置"; \
	else \
		echo "操作已取消"; \
	fi

# 部署命令
build:
	@echo "构建生产版本..."
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml build

clean:
	@echo "清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "清理完成"

# 监控命令
monitor:
	@echo "启动监控面板..."
	open http://localhost:3000  # Grafana
	open http://localhost:9090  # Prometheus
	open http://localhost:5601  # Kibana
	open http://localhost:9001  # MinIO Console

# 数据收集命令
collect-data:
	$(PYTHON) -m src.data_collection.main

process-data:
	$(PYTHON) -m src.data_processing.main

run-analysis:
	$(PYTHON) -m src.ai_analysis.main

# 工作流命令
run-workflow:
	$(PYTHON) -m src.workflow.orchestrator.main

# 检查系统状态
status:
	@echo "检查系统状态..."
	$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "API健康检查:"
	curl -f http://localhost:8000/health || echo "API未运行"
	@echo ""
	@echo "数据库连接:"
	$(PYTHON) -c "import asyncpg; import asyncio; import os; async def check(): \
		try: \
			conn = await asyncpg.connect(os.getenv('DATABASE_URL')); \
			print('数据库连接正常'); \
			await conn.close(); \
		except Exception as e: \
			print(f'数据库连接失败: {e}') \
		asyncio.run(check())" 2>/dev/null || echo "Python脚本执行失败"