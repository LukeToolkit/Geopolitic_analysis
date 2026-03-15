"""
预测模块基础测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.prediction import (
    BasePredictor, PredictorConfig, PredictionType, ModelType,
    PredictionResult, ModelMetrics, ModelManager
)

# 测试数据生成函数
def create_time_series_data(n_points: int = 100):
    """创建测试时间序列数据"""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_points)]
    values = np.sin(np.linspace(0, 4 * np.pi, n_points)) * 10 + 20 + np.random.normal(0, 1, n_points)

    df = pd.DataFrame({
        'date': dates,
        'value': values,
        'feature1': np.random.randn(n_points),
        'feature2': np.random.randn(n_points)
    })
    return df

def create_classification_data(n_samples: int = 100):
    """创建测试分类数据"""
    X = np.random.randn(n_samples, 5)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)  # 简单线性决策边界

    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(5)])
    df['target'] = y
    return df, y

def create_regression_data(n_samples: int = 100):
    """创建测试回归数据"""
    X = np.random.randn(n_samples, 5)
    y = X[:, 0] * 2 + X[:, 1] * 1.5 + np.random.normal(0, 0.5, n_samples)

    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(5)])
    df['target'] = y
    return df, y


class TestBasePredictor:
    """基础预测器测试"""

    def test_predictor_config(self):
        """测试预测器配置"""
        config = PredictorConfig(
            name="test_predictor",
            prediction_type=PredictionType.TIME_SERIES,
            model_type=ModelType.STATISTICAL,
            enabled=True,
            retrain_interval_hours=24,
            prediction_horizon=7,
            confidence_threshold=0.7,
            max_training_samples=10000,
            params={"param1": "value1"}
        )

        assert config.name == "test_predictor"
        assert config.prediction_type == PredictionType.TIME_SERIES
        assert config.model_type == ModelType.STATISTICAL
        assert config.enabled is True
        assert config.retrain_interval_hours == 24
        assert config.prediction_horizon == 7
        assert config.confidence_threshold == 0.7
        assert config.max_training_samples == 10000
        assert config.params == {"param1": "value1"}

    def test_prediction_result(self):
        """测试预测结果"""
        result = PredictionResult(
            prediction_id="test_123",
            model_id="test_model",
            target_type="value",
            predicted_value=42.5,
            confidence_score=0.85,
            prediction_type=PredictionType.TIME_SERIES,
            features_used=["feature1", "feature2"],
            forecast_horizon=7,
            prediction_interval=(40.0, 45.0)
        )

        assert result.prediction_id == "test_123"
        assert result.model_id == "test_model"
        assert result.predicted_value == 42.5
        assert result.confidence_score == 0.85
        assert result.prediction_type == PredictionType.TIME_SERIES
        assert result.forecast_horizon == 7
        assert result.prediction_interval == (40.0, 45.0)

        # 测试字典转换
        result_dict = result.to_dict()
        assert result_dict["prediction_id"] == "test_123"
        assert result_dict["predicted_value"] == 42.5
        assert result_dict["confidence_score"] == 0.85

    def test_model_metrics(self):
        """测试模型指标"""
        metrics = ModelMetrics(
            model_id="test_model",
            mae=0.5,
            mse=0.3,
            rmse=0.5477,
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            r2_score=0.92
        )

        assert metrics.model_id == "test_model"
        assert metrics.mae == 0.5
        assert metrics.accuracy == 0.85
        assert metrics.r2_score == 0.92

        metrics_dict = metrics.to_dict()
        assert metrics_dict["model_id"] == "test_model"
        assert metrics_dict["mae"] == 0.5
        assert metrics_dict["accuracy"] == 0.85


class TestModelManager:
    """模型管理器测试"""

    def setup_method(self):
        self.manager = ModelManager()

    def test_register_predictor(self):
        """测试注册预测器"""
        # 创建模拟预测器
        class MockPredictor(BasePredictor):
            async def train(self, training_data, labels=None, **kwargs):
                return True

            async def predict(self, input_data, **kwargs):
                return PredictionResult(
                    prediction_id="test",
                    model_id=self.name,
                    target_type="test",
                    predicted_value=1.0,
                    confidence_score=0.9,
                    prediction_type=self.prediction_type,
                    features_used=[]
                )

            async def evaluate(self, test_data, test_labels=None, **kwargs):
                return ModelMetrics(model_id=self.name)

            async def _save_model_impl(self, filepath):
                return True

            async def _load_model_impl(self, filepath):
                return True

        config = PredictorConfig(
            name="test_predictor",
            prediction_type=PredictionType.TIME_SERIES,
            model_type=ModelType.STATISTICAL
        )

        predictor = MockPredictor(config)
        self.manager.register_predictor(predictor)

        # 验证注册
        retrieved = self.manager.get_predictor("test_predictor")
        assert retrieved is not None
        assert retrieved.name == "test_predictor"

        # 验证获取所有预测器
        all_predictors = self.manager.get_all_predictors()
        assert len(all_predictors) == 1
        assert all_predictors[0].name == "test_predictor"

        # 验证注销
        self.manager.unregister_predictor("test_predictor")
        assert self.manager.get_predictor("test_predictor") is None
        assert len(self.manager.get_all_predictors()) == 0

    def test_predictor_stats(self):
        """测试预测器统计信息"""
        # 使用模拟预测器测试统计信息获取
        class MockPredictor(BasePredictor):
            async def train(self, training_data, labels=None, **kwargs):
                self._is_trained = True
                self._last_training_time = datetime.utcnow()
                return True

            async def predict(self, input_data, **kwargs):
                return PredictionResult(
                    prediction_id="test",
                    model_id=self.name,
                    target_type="test",
                    predicted_value=1.0,
                    confidence_score=0.9,
                    prediction_type=self.prediction_type,
                    features_used=[]
                )

            async def evaluate(self, test_data, test_labels=None, **kwargs):
                return ModelMetrics(model_id=self.name)

            async def _save_model_impl(self, filepath):
                return True

            async def _load_model_impl(self, filepath):
                return True

        config = PredictorConfig(
            name="test_predictor",
            prediction_type=PredictionType.TIME_SERIES,
            model_type=ModelType.STATISTICAL
        )

        predictor = MockPredictor(config)
        self.manager.register_predictor(predictor)

        # 训练后获取统计信息
        import asyncio
        asyncio.run(predictor.train([]))

        stats = self.manager.get_predictor_stats("test_predictor")
        assert stats is not None
        assert stats["name"] == "test_predictor"
        assert stats["is_trained"] is True
        assert "created_at" in stats


if __name__ == "__main__":
    # 运行基本测试
    import sys
    sys.path.insert(0, ".")

    test = TestBasePredictor()
    test.test_predictor_config()
    test.test_prediction_result()
    test.test_model_metrics()

    print("所有基础测试通过!")

    # 注意：实际模型测试需要相应的库安装
    print("\n注意：实际预测器测试需要安装相应的机器学习库")
    print("运行完整测试请使用: pytest src/prediction/tests/")