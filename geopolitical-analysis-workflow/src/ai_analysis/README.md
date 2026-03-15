# AI分析模块

地缘政治分析AI工作流系统的核心分析模块，提供多源数据智能分析功能。

## 功能概述

1. **航运数据(AIS)分析** - 分析船舶自动识别系统数据，检测异常航运活动
2. **民航数据(ADS-B)分析** - 分析广播式自动相关监视数据，检测异常航空活动
3. **军事部署分析** - 分析军事部署、演习和装备移动，评估冲突风险
4. **多源融合分析** - 整合多维度数据，提供综合地缘政治风险评估
5. **大模型集成** - 集成Anthropic Claude和OpenAI GPT系列模型
6. **分析管理** - 协调多个分析器，管理分析任务队列

## 架构设计

### 核心组件

```
src/ai_analysis/
├── core/                    # 核心基础类
│   ├── base_analyzer.py    # 分析器抽象基类
│   └── analysis_manager.py # 分析管理器
├── analyzers/              # 具体分析器
│   ├── ais_analyzer.py     # AIS数据分析器
│   ├── adsb_analyzer.py    # ADS-B数据分析器
│   ├── military_analyzer.py # 军事部署分析器
│   └── fusion_analyzer.py  # 多源融合分析器
├── integrations/           # 外部集成
│   └── llm_integration.py  # 大语言模型集成
├── models/                 # 数据模型
├── utils/                  # 工具函数
└── __init__.py            # 模块导出
```

### 设计模式

1. **插件化架构** - 所有分析器继承自`BaseAnalyzer`，支持动态注册
2. **工厂模式** - `AnalysisManager`负责创建和管理分析器实例
3. **策略模式** - 不同的分析算法可以通过配置选择
4. **观察者模式** - 支持分析结果回调通知
5. **单例模式** - 关键服务管理器使用单例确保全局唯一

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 环境配置

在`.env`文件中配置API密钥：

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 基本使用

```python
import asyncio
from src.ai_analysis import (
    get_analysis_manager,
    analyze_data,
    analyze_multimodal_data,
    AnalysisType
)

async def main():
    # 获取分析管理器
    manager = await get_analysis_manager()

    # 分析AIS数据
    ais_data = [...]  # AIS数据列表
    ais_result = await analyze_data(AnalysisType.AIS_ANALYSIS, ais_data)

    print(f"风险等级: {ais_result.risk_level}")
    print(f"关键洞察: {ais_result.insights}")

    # 多模态融合分析
    multimodal_data = {
        "ais_data": ais_data,
        "adsb_data": [...],  # ADS-B数据
        "military_data": {...}  # 军事数据
    }

    fusion_result = await analyze_multimodal_data(multimodal_data)
    print(f"综合风险评估: {fusion_result.risk_level}")

asyncio.run(main())
```

### 运行示例

```bash
cd /path/to/project
python scripts/ai_analysis_example.py
```

## 分析器详解

### 1. AIS分析器 (`AISAnalyzer`)

**功能**:
- 检测异常航运活动（限制区域、异常速度、AIS信号异常）
- 识别高风险船舶（身份不明、敏感货物、受制裁船旗国）
- 分析航运模式变化
- 使用LLM进行综合风险评估

**输入数据格式**:
```python
{
    "mmsi": "123456789",           # 海事移动服务标识
    "ship_name": "OCEAN_TRADER",   # 船名
    "ship_type": "cargo",          # 船舶类型
    "latitude": 35.6895,           # 纬度
    "longitude": 139.6917,         # 经度
    "speed": 15.5,                 # 速度（节）
    "course": 120.5,               # 航向（度）
    "destination": "Shanghai",     # 目的地
    "cargo": "electronics",        # 货物类型
    "flag": "Panama",              # 船旗国
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. ADS-B分析器 (`ADS_BAnalyzer`)

**功能**:
- 检测异常航空活动（紧急代码、异常高度、空中停滞）
- 识别高风险航空器（军事、政府、未知身份）
- 检测空域侵犯
- 分析飞行模式变化

**输入数据格式**:
```python
{
    "icao24": "abc123",            # ICAO 24位地址
    "callsign": "UAL123",          # 呼号
    "origin_country": "United States",  # 来源国
    "latitude": 40.7128,           # 纬度
    "longitude": -74.0060,         # 经度
    "altitude": 10000,             # 高度（米）
    "velocity": 250.0,             # 速度（米/秒）
    "squawk": "1234",              # 应答机代码
    "on_ground": False,            # 是否在地面
    "aircraft_type": "commercial", # 航空器类型
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 3. 军事部署分析器 (`MilitaryAnalyzer`)

**功能**:
- 检测异常军事活动（隐蔽部署、短时间通知演习、战备等级提升）
- 评估冲突风险（热点区域、部队对峙、历史模式）
- 分析军事态势变化
- 评估军事力量平衡

**输入数据格式**:
```python
{
    "units": [  # 军事单位列表
        {
            "unit_id": "unit_001",
            "unit_type": "navy",
            "country": "United States",
            "location": {"latitude": 35.6895, "longitude": 139.6917},
            "strength": 1500,
            "equipment": ["destroyer", "helicopter"],
            "readiness_level": "elevated",
            "movement_status": "stationary"
        }
    ],
    "exercises": [  # 军事演习列表
        {
            "exercise_id": "ex_001",
            "name": "Joint Pacific Exercise",
            "participating_countries": ["United States", "Japan", "South Korea"],
            "location": {"region": "east_asia"},
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-03T00:00:00Z",
            "exercise_type": "joint",
            "scale": "large",
            "objectives": ["interoperability", "deterrence"]
        }
    ],
    "deployments": []  # 军事部署列表
}
```

### 4. 融合分析器 (`FusionAnalyzer`)

**功能**:
- 检测跨数据源关联（空间、时间、主题）
- 分析协同信号（多个数据源指向同一事件）
- 检测矛盾信息（数据源间不一致）
- 进行综合风险评估
- 使用LLM进行高级融合分析

**输入数据格式**:
```python
{
    "ais_data": [...],        # AIS数据列表
    "adsb_data": [...],       # ADS-B数据列表
    "military_data": {...},   # 军事数据
    "news_data": [...],       # 新闻数据（可选）
    "financial_data": [...],  # 金融数据（可选）
    "social_media_data": [...],  # 社交媒体数据（可选）
    "geographic_scope": ["east_asia"],  # 地理范围
    "timeframe": "recent"     # 时间范围
}
```

## 配置说明

配置文件：`config/ai_analysis_config.yaml`

### 主要配置项

```yaml
# 分析器配置
analyzers:
  ais_analyzer:
    enabled: true
    model_provider: "anthropic"  # 模型提供商
    model_name: "claude-3-sonnet-20240229"  # 模型名称
    max_tokens: 4000  # 最大token数
    temperature: 0.1  # 温度参数
    geographic_focus: ["global"]  # 地理关注区域
    analysis_depth: "standard"  # 分析深度

# LLM配置
llm:
  default_provider: "anthropic"
  fallback_provider: "openai"
  max_retries: 3
  timeout: 30

# 分析管理器配置
analysis_manager:
  worker_count: 4  # 工作线程数
  max_queue_size: 100  # 最大队列大小
  default_timeout: 300  # 默认超时时间（秒）
```

## API参考

### 主要类

#### `BaseAnalyzer`
所有分析器的基类，定义统一接口。

**主要方法**:
- `analyze(data, context)` - 分析数据
- `analyze_text(text, context)` - 分析文本数据
- `analyze_geospatial(geospatial_data, context)` - 分析地理空间数据
- `analyze_temporal(temporal_data, context)` - 分析时间序列数据

#### `AnalysisManager`
分析管理器，协调多个分析器的运行。

**主要方法**:
- `analyze(request)` - 执行分析（同步）
- `analyze_async(request)` - 异步执行分析
- `analyze_multimodal(data, context)` - 多模态分析
- `get_job_status(job_id)` - 获取任务状态
- `start()` / `stop()` - 启动/停止管理器

#### `LLMManager`
LLM管理器，提供统一的语言模型接口。

**主要方法**:
- `generate_text(prompt, **kwargs)` - 生成文本
- `generate_structured(prompt, output_schema, **kwargs)` - 生成结构化输出
- `get_client(provider)` - 获取LLM客户端

### 数据模型

#### `AnalysisResult`
分析结果数据类。

**属性**:
- `data` - 原始分析数据
- `confidence` - 分析置信度 (0.0-1.0)
- `insights` - 关键洞察列表
- `recommendations` - 建议列表
- `risk_level` - 风险等级 (low/medium/high/critical)
- `impact_score` - 影响评分 (0.0-10.0)
- `geographic_scope` - 地理范围列表
- `timeline` - 时间线预测

#### `AnalysisRequest`
分析请求数据类。

**属性**:
- `analysis_type` - 分析类型
- `data` - 输入数据
- `context` - 分析上下文
- `priority` - 优先级 (1-10)
- `timeout_seconds` - 超时时间

## 性能优化

### 缓存策略
- LLM响应缓存：1小时TTL，最大1000条
- 分析结果缓存：根据配置可调整
- 地理空间索引：加速空间查询

### 并发处理
- 异步IO：所有网络请求使用async/await
- 工作线程池：可配置数量的分析工作线程
- 优先级队列：高优先级任务优先处理

### 资源管理
- 连接池：数据库、Redis连接复用
- 内存限制：大结果集分页处理
- 超时控制：防止长时间阻塞

## 监控和日志

### 指标监控
- 分析成功率/失败率
- 平均处理时间
- 队列积压情况
- LLM调用统计
- 内存和CPU使用率

### 日志记录
- 结构化JSON日志
- 不同级别日志分离
- 日志轮转和归档
- 敏感信息脱敏

## 扩展开发

### 添加新分析器

1. 创建新的分析器类，继承`BaseAnalyzer`:

```python
from .core.base_analyzer import BaseAnalyzer, AnalyzerConfig, AnalysisResult

class MyAnalyzer(BaseAnalyzer):
    def __init__(self, config: AnalyzerConfig):
        super().__init__(config)

    async def analyze(self, data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        # 实现分析逻辑
        pass
```

2. 在`AnalysisManager._register_analyzers()`中注册新分析器
3. 添加对应的`AnalysisType`枚举值
4. 更新配置文件支持新分析器

### 自定义LLM提示

可以通过修改各个分析器的`_analyze_with_llm()`方法来自定义提示词，或通过配置传递自定义提示模板。

## 故障排除

### 常见问题

1. **LLM API调用失败**
   - 检查API密钥配置
   - 检查网络连接
   - 确认API配额和限制

2. **分析结果置信度过低**
   - 检查输入数据质量
   - 调整分析器参数
   - 增加数据量

3. **处理时间过长**
   - 检查数据量是否过大
   - 调整工作线程数量
   - 优化LLM提示减少token使用

4. **内存使用过高**
   - 启用结果缓存清理
   - 限制同时处理的任务数
   - 优化数据结构

### 调试模式

启用调试日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

或在配置中设置：
```yaml
logging:
  level: "DEBUG"
```

## 安全考虑

### 数据安全
- 敏感数据加密存储
- API密钥安全管理
- 访问控制和认证

### 模型安全
- 提示注入防护
- 输出内容过滤
- 使用率限制和监控

### 合规性
- 数据隐私保护
- 使用条款遵守
- 审计日志记录

## 贡献指南

1. Fork项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

[待定]

## 联系方式

[待定]

---

## 更新日志

### v0.1.0 (2026-03-15)
- 初始版本发布
- 实现AIS、ADS-B、军事部署、多源融合分析器
- 集成Anthropic Claude和OpenAI GPT模型
- 提供分析管理器和统一API接口
- 包含完整配置文件和示例代码