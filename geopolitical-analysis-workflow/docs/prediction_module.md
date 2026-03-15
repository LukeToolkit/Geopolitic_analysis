# 预测模块文档

## 概述

预测模块是地缘政治分析AI工作流系统的核心组件之一，负责时间序列预测和机器学习预测任务。模块采用插件化架构，支持多种预测模型和算法。

## 主要特性

1. **多模型支持**: 支持时间序列模型（Prophet, ARIMA, SARIMA, ETS）和机器学习模型（Scikit-learn, LightGBM, XGBoost）
2. **插件化架构**: 所有预测器继承自统一的基类，易于扩展
3. **统一接口**: 提供一致的训练、预测、评估接口
4. **模型管理**: 集中管理多个预测器，支持模型注册、注销、状态跟踪
5. **集成预测**: 支持多个模型的集成预测（加权平均、多数投票等）
6. **性能监控**: 跟踪模型性能指标和使用统计

## 架构设计

### 核心类

1. **BasePredictor**: 预测器抽象基类，定义统一接口
2. **PredictorConfig**: 预测器配置类
3. **PredictionResult**: 预测结果类
4. **ModelMetrics**: 模型评估指标类
5. **ModelManager**: 模型管理器，集中管理所有预测器

### 预测器类型

1. **时间序列预测器** (`TimeSeriesPredictor`):
   - 基于Prophet、ARIMA、SARIMA、ETS等模型
   - 适用于时间序列数据预测

2. **机器学习预测器** (`MLPredictor`):
   - 基于Scikit-learn、LightGBM、XGBoost等库
   - 支持分类、回归、风险评分等任务

## 快速开始

### 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 时间序列预测（可选）
pip install prophet statsmodels

# 机器学习（可选）
pip install scikit-learn lightgbm xgboost
```

### 基本使用示例

```python
import asyncio
from src.prediction import (
    PredictorConfig, PredictionType, ModelType,
    TimeSeriesPredictor, MLPredictor, ModelManager
)

# 创建时间序列预测器
ts_config = PredictorConfig(
    name="stock_forecaster",
    prediction_type=PredictionType.TIME_SERIES,
    model_type=ModelType.STATISTICAL,
    prediction_horizon=7,
    params={
        "model": "prophet",
        "target_column": "price",
        "date_column": "date"
    }
)

ts_predictor = TimeSeriesPredictor(ts_config)

# 创建机器学习分类器
ml_config = PredictorConfig(
    name="risk_classifier",
    prediction_type=PredictionType.CLASSIFICATION,
    model_type=ModelType.MACHINE_LEARNING,
    params={
        "model": "random_forest_classifier",
        "target_column": "risk_level"
    }
)

ml_predictor = MLPredictor(ml_config)

# 使用模型管理器
manager = ModelManager()
manager.register_predictor(ts_predictor)
manager.register_predictor(ml_predictor)

# 训练和预测
async def main():
    # 训练模型
    await ts_predictor.train(training_data)
    await ml_predictor.train(training_data, labels)

    # 进行预测
    prediction = await ts_predictor.predict(input_data)
    print(f"预测结果: {prediction.predicted_value}, 置信度: {prediction.confidence_score}")

asyncio.run(main())
```

## API使用

### REST API端点

预测模块提供以下REST API端点：

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/v1/prediction/models` | GET | 列出所有预测模型 | API密钥 |
| `/api/v1/prediction/models/{name}` | GET | 获取模型详细信息 | API密钥 |
| `/api/v1/prediction/models/register` | POST | 注册新模型 | API密钥 |
| `/api/v1/prediction/models/{name}` | DELETE | 注销模型 | API密钥 |
| `/api/v1/prediction/train` | POST | 训练模型 | API密钥 |
| `/api/v1/prediction/predict` | POST | 进行预测 | API密钥 |
| `/api/v1/prediction/predict/batch` | POST | 批量预测 | API密钥 |
| `/api/v1/prediction/ensemble` | POST | 集成预测 | API密钥 |
| `/api/v1/prediction/evaluate` | POST | 评估模型 | API密钥 |
| `/api/v1/prediction/stats` | GET | 获取所有模型统计 | API密钥 |
| `/api/v1/prediction/health` | GET | 预测模块健康检查 | 公开 |

### API示例

#### 注册时间序列预测器

```bash
curl -X POST "http://localhost:8000/api/v1/prediction/models/register" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "geopolitical_risk_forecaster",
    "prediction_type": "time_series",
    "model_type": "statistical",
    "prediction_horizon": 14,
    "params": {
      "model": "prophet",
      "target_column": "risk_score",
      "date_column": "timestamp",
      "model_params": {
        "seasonality_mode": "multiplicative"
      }
    }
  }'
```

#### 进行预测

```bash
curl -X POST "http://localhost:8000/api/v1/prediction/predict" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "predictor_name": "geopolitical_risk_forecaster",
    "input_data": {
      "timestamp": "2024-01-15T00:00:00Z",
      "risk_score": 65.2,
      "event_count": 12,
      "news_sentiment": -0.3
    }
  }'
```

## 预测器配置

### PredictorConfig参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `name` | str | 必需 | 预测器名称 |
| `prediction_type` | PredictionType | 必需 | 预测类型 |
| `model_type` | ModelType | 必需 | 模型类型 |
| `enabled` | bool | True | 是否启用 |
| `retrain_interval_hours` | int | 24 | 重新训练间隔（小时） |
| `prediction_horizon` | int | 7 | 预测步长 |
| `confidence_threshold` | float | 0.7 | 置信度阈值 |
| `max_training_samples` | int | 10000 | 最大训练样本数 |
| `params` | Dict[str, Any] | {} | 模型特定参数 |

### 预测类型（PredictionType）

- `TIME_SERIES`: 时间序列预测
- `CLASSIFICATION`: 分类预测
- `REGRESSION`: 回归预测
- `RISK_SCORE`: 风险评分
- `EVENT_PROBABILITY`: 事件概率预测
- `MARKET_TREND`: 市场趋势预测
- `GEOPOLITICAL_RISK`: 地缘政治风险预测

### 模型类型（ModelType）

- `STATISTICAL`: 统计模型
- `MACHINE_LEARNING`: 机器学习模型
- `DEEP_LEARNING`: 深度学习模型
- `HYBRID`: 混合模型
- `CUSTOM`: 自定义模型

## 扩展预测器

### 创建自定义预测器

```python
from src.prediction import BasePredictor, PredictorConfig, PredictionResult, ModelMetrics

class CustomPredictor(BasePredictor):
    """自定义预测器示例"""

    async def train(self, training_data, labels=None, **kwargs):
        """训练模型"""
        # 实现训练逻辑
        self._is_trained = True
        return True

    async def predict(self, input_data, **kwargs):
        """进行预测"""
        # 实现预测逻辑
        result = PredictionResult(
            prediction_id="custom_123",
            model_id=self.name,
            target_type="custom_target",
            predicted_value=42.0,
            confidence_score=0.85,
            prediction_type=self.prediction_type,
            features_used=["feature1", "feature2"]
        )
        return result

    async def evaluate(self, test_data, test_labels=None, **kwargs):
        """评估模型"""
        # 实现评估逻辑
        return ModelMetrics(model_id=self.name, accuracy=0.92)

    async def _save_model_impl(self, filepath):
        """保存模型"""
        # 实现保存逻辑
        return True

    async def _load_model_impl(self, filepath):
        """加载模型"""
        # 实现加载逻辑
        return True
```

### 注册自定义预测器

```python
from src.prediction import ModelManager

config = PredictorConfig(
    name="custom_predictor",
    prediction_type=PredictionType.CUSTOM,
    model_type=ModelType.CUSTOM
)

custom_predictor = CustomPredictor(config)

manager = ModelManager()
manager.register_predictor(custom_predictor)
```

## 模型持久化

### 保存和加载模型

```python
# 保存单个模型
await predictor.save_model("/path/to/model.pkl")

# 加载单个模型
await predictor.load_model("/path/to/model.pkl")

# 保存整个注册表
manager.save_registry("/path/to/registry.json")

# 加载整个注册表
def predictor_factory(config):
    # 根据配置创建预测器
    if config.prediction_type == PredictionType.TIME_SERIES:
        return TimeSeriesPredictor(config)
    elif config.prediction_type == PredictionType.CLASSIFICATION:
        return MLPredictor(config)
    return None

await manager.load_registry("/path/to/registry.json", predictor_factory)
```

## 性能监控

### 模型统计信息

每个预测器提供以下统计信息：

- 模型名称和类型
- 训练状态和时间
- 预测次数和错误次数
- 性能指标历史
- 使用统计（创建时间、最后使用时间、使用次数）

### 性能指标

根据预测类型，模型提供不同的性能指标：

- **时间序列**: MAE, MSE, RMSE, MAPE, R²
- **分类**: 准确率、精确率、召回率、F1分数、AUC
- **回归**: MAE, MSE, RMSE, MAPE, R²

## 集成预测

### 集成策略

1. **加权平均** (`weighted_average`): 根据置信度加权平均预测值
2. **多数投票** (`majority_vote`): 分类任务中使用多数投票
3. **最佳模型** (`best_model`): 选择置信度最高的模型

### 使用示例

```python
# 使用集成预测
result = await manager.ensemble_predict(
    prediction_type=PredictionType.TIME_SERIES,
    input_data=input_data,
    strategy="weighted_average"
)
```

## 故障排除

### 常见问题

1. **导入错误**: 确保已安装所需依赖
2. **训练失败**: 检查数据格式和质量
3. **预测失败**: 确认模型已训练，输入数据格式正确
4. **性能差**: 调整模型参数，增加训练数据

### 依赖检查

```python
from src.prediction import TIME_SERIES_AVAILABLE, ML_PREDICTOR_AVAILABLE

print(f"时间序列预测器可用: {TIME_SERIES_AVAILABLE}")
print(f"机器学习预测器可用: {ML_PREDICTOR_AVAILABLE}")
```

## 最佳实践

1. **数据预处理**: 确保训练数据经过适当的清洗和标准化
2. **模型选择**: 根据问题类型选择合适的预测器
3. **参数调优**: 使用交叉验证调整模型参数
4. **监控和评估**: 定期评估模型性能，及时重新训练
5. **错误处理**: 实现适当的错误处理和日志记录

## 相关模块

- **数据收集模块**: 提供训练和预测数据
- **数据处理模块**: 数据清洗和特征工程
- **AI分析模块**: 高级分析和特征提取
- **工作流引擎**: 自动化预测任务调度

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 基础预测器框架
- 时间序列和机器学习预测器
- REST API支持
- 模型管理功能

## 支持

如有问题或建议，请联系项目维护团队。