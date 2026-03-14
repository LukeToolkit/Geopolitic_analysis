# 地缘政治分析AI工作流系统

## 项目概述
基于AI和大模型的地缘政治分析系统，通过多源数据收集、智能分析和预测，为金融投资提供决策支持。

## 核心功能
1. **多源数据收集**：新闻、民航(ADS-B)、船运(AIS)、金融数据、公开军事部署、社交媒体OSINT博主帖子
2. **地缘政治分析**：分析特定热点地区的现状和发展趋势
3. **短期预测**：基于数据和AI分析生成未来趋势预测（1-4周）
4. **金融指导**：基于预测结果提供投资建议和模拟回测验证

## 技术架构
- **后端**：Python 3.11+ (FastAPI, Polars, Scikit-learn, Prefect)
- **前端**：React 18 + TypeScript + Tailwind CSS
- **数据库**：PostgreSQL + TimescaleDB + Redis
- **部署**：Docker + Kubernetes
- **监控**：Prometheus + Grafana + ELK Stack

## 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### 开发环境设置
```bash
# 1. 克隆项目
git clone <repository-url>
cd geopolitical-analysis-workflow

# 2. 复制环境变量文件
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等

# 3. 启动开发环境
docker-compose up -d

# 4. 安装Python依赖
pip install -r requirements.txt

# 5. 安装前端依赖
cd src/web/frontend
npm install
```

### 项目结构
```
geopolitical-analysis-workflow/
├── src/                    # 源代码
│   ├── data_collection/   # 数据收集层
│   ├── data_processing/   # 数据处理层
│   ├── ai_analysis/       # AI分析层
│   ├── prediction/        # 预测模块
│   ├── workflow/          # 工作流引擎
│   ├── api/              # API服务
│   ├── storage/          # 存储抽象
│   └── web/              # Web界面
├── tests/                 # 测试代码
├── docs/                  # 文档
├── scripts/               # 运维脚本
└── docker-compose.yml     # 开发环境配置
```

## 开发指南

### 数据收集器开发
数据收集器遵循插件化架构，实现统一的`DataCollector`接口：
```python
from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime

class DataCollector(ABC):
    @abstractmethod
    async def collect(self, config: Dict) -> List[Dict]:
        """收集数据"""
        pass

    @abstractmethod
    def validate(self, data: List[Dict]) -> bool:
        """验证数据质量"""
        pass
```

### API开发规范
- 使用FastAPI创建REST API
- 所有API端点必须有OpenAPI文档
- 错误处理使用统一格式
- 认证使用JWT Token

### 测试规范
- 单元测试：测试独立函数和类
- 集成测试：测试模块间集成
- E2E测试：测试完整工作流

## 部署指南

### 开发环境
```bash
docker-compose up -d
```

### 生产环境
```bash
# 使用Kubernetes部署
kubectl apply -f k8s/
```

## 监控与日志
- **指标监控**：Prometheus + Grafana
- **日志收集**：ELK Stack (Elasticsearch, Logstash, Kibana)
- **应用性能监控**：自定义业务指标

## 安全与合规
- 数据加密传输和存储
- RBAC权限控制
- 审计日志记录
- GDPR合规性考虑

## 贡献指南
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证
[待定]

## 联系方式
[待定]