"""
预测器基础类
实现插件化预测器架构，所有具体预测器必须继承此类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PredictionType(Enum):
    """预测类型枚举"""
    TIME_SERIES = "time_series"  # 时间序列预测
    CLASSIFICATION = "classification"  # 分类预测
    REGRESSION = "regression"  # 回归预测
    RISK_SCORE = "risk_score"  # 风险评分
    EVENT_PROBABILITY = "event_probability"  # 事件概率
    MARKET_TREND = "market_trend"  # 市场趋势
    GEOPOLITICAL_RISK = "geopolitical_risk"  # 地缘政治风险


class ModelType(Enum):
    """模型类型枚举"""
    STATISTICAL = "statistical"  # 统计模型
    MACHINE_LEARNING = "machine_learning"  # 机器学习
    DEEP_LEARNING = "deep_learning"  # 深度学习
    HYBRID = "hybrid"  # 混合模型
    CUSTOM = "custom"  # 自定义模型


@dataclass
class PredictionResult:
    """预测结果"""
    prediction_id: str
    model_id: str
    target_type: str
    predicted_value: Union[float, int, str, Dict[str, Any]]
    confidence_score: float  # 置信度评分 (0-1)
    prediction_type: PredictionType
    features_used: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    forecast_horizon: Optional[int] = None  # 预测步长（适用于时间序列）
    prediction_interval: Optional[Tuple[float, float]] = None  # 预测区间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "prediction_id": self.prediction_id,
            "model_id": self.model_id,
            "target_type": self.target_type,
            "predicted_value": self.predicted_value,
            "confidence_score": self.confidence_score,
            "prediction_type": self.prediction_type.value,
            "features_used": self.features_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "forecast_horizon": self.forecast_horizon,
            "prediction_interval": self.prediction_interval
        }


@dataclass
class ModelMetrics:
    """模型评估指标"""
    model_id: str
    mae: Optional[float] = None  # 平均绝对误差
    mse: Optional[float] = None  # 均方误差
    rmse: Optional[float] = None  # 均方根误差
    mape: Optional[float] = None  # 平均绝对百分比误差
    accuracy: Optional[float] = None  # 准确率
    precision: Optional[float] = None  # 精确率
    recall: Optional[float] = None  # 召回率
    f1_score: Optional[float] = None  # F1分数
    auc: Optional[float] = None  # AUC分数
    r2_score: Optional[float] = None  # R²分数
    log_loss: Optional[float] = None  # 对数损失
    evaluation_date: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "model_id": self.model_id,
            "mae": self.mae,
            "mse": self.mse,
            "rmse": self.rmse,
            "mape": self.mape,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "auc": self.auc,
            "r2_score": self.r2_score,
            "log_loss": self.log_loss,
            "evaluation_date": self.evaluation_date.isoformat()
        }


@dataclass
class PredictorConfig:
    """预测器配置"""
    name: str
    prediction_type: PredictionType
    model_type: ModelType
    enabled: bool = True
    retrain_interval_hours: int = 24  # 重新训练间隔（小时）
    prediction_horizon: int = 7  # 预测步长（天）
    confidence_threshold: float = 0.7  # 置信度阈值
    max_training_samples: int = 10000  # 最大训练样本数
    params: Dict[str, Any] = field(default_factory=dict)


class BasePredictor(ABC):
    """预测器抽象基类"""

    def __init__(self, config: PredictorConfig):
        self.config = config
        self._is_trained = False
        self._last_training_time: Optional[datetime] = None
        self._last_prediction_time: Optional[datetime] = None
        self._total_predictions = 0
        self._total_errors = 0
        self._model_metrics: Optional[ModelMetrics] = None
        self.logger = logging.getLogger(f"{__name__}.{self.config.name}")

    @property
    def name(self) -> str:
        """预测器名称"""
        return self.config.name

    @property
    def prediction_type(self) -> PredictionType:
        """预测类型"""
        return self.config.prediction_type

    @property
    def model_type(self) -> ModelType:
        """模型类型"""
        return self.config.model_type

    @property
    def is_trained(self) -> bool:
        """模型是否已训练"""
        return self._is_trained

    @property
    def needs_retraining(self) -> bool:
        """是否需要重新训练"""
        if not self._last_training_time:
            return True
        next_time = self._last_training_time + timedelta(hours=self.config.retrain_interval_hours)
        return datetime.utcnow() >= next_time

    @abstractmethod
    async def train(self, training_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                   labels: Optional[Union[np.ndarray, List]] = None,
                   **kwargs) -> bool:
        """
        训练模型

        Args:
            training_data: 训练数据
            labels: 标签（监督学习）
            **kwargs: 其他参数

        Returns:
            bool: 训练是否成功
        """
        pass

    @abstractmethod
    async def predict(self, input_data: Union[pd.DataFrame, np.ndarray, List[Dict], Dict],
                     **kwargs) -> PredictionResult:
        """
        进行预测

        Args:
            input_data: 输入数据
            **kwargs: 其他参数

        Returns:
            PredictionResult: 预测结果
        """
        pass

    @abstractmethod
    async def evaluate(self, test_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                      test_labels: Optional[Union[np.ndarray, List]] = None,
                      **kwargs) -> ModelMetrics:
        """
        评估模型性能

        Args:
            test_data: 测试数据
            test_labels: 测试标签
            **kwargs: 其他参数

        Returns:
            ModelMetrics: 模型评估指标
        """
        pass

    async def train_with_validation(self,
                                  training_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                                  validation_data: Optional[Union[pd.DataFrame, np.ndarray, List[Dict]]] = None,
                                  validation_labels: Optional[Union[np.ndarray, List]] = None,
                                  **kwargs) -> bool:
        """带验证的训练"""
        try:
            self.logger.info(f"开始训练 {self.name}")

            # 训练模型
            labels = kwargs.pop('labels', None)
            success = await self.train(training_data, labels=labels, **kwargs)

            if not success:
                self.logger.error(f"训练失败: {self.name}")
                return False

            # 如果有验证数据，进行评估
            if validation_data is not None:
                self.logger.info(f"验证模型 {self.name}")
                metrics = await self.evaluate(validation_data, validation_labels, **kwargs)
                self._model_metrics = metrics
                self.logger.info(f"验证完成: {metrics}")

            self._is_trained = True
            self._last_training_time = datetime.utcnow()
            self.logger.info(f"训练完成: {self.name}")
            return True

        except Exception as e:
            self.logger.error(f"训练过程中出错: {str(e)}")
            self._total_errors += 1
            return False

    async def predict_batch(self, input_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                          **kwargs) -> List[PredictionResult]:
        """批量预测"""
        results = []

        if isinstance(input_data, pd.DataFrame):
            # DataFrame逐行预测
            for idx, row in input_data.iterrows():
                try:
                    result = await self.predict(row.to_dict(), **kwargs)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"第 {idx} 行预测失败: {str(e)}")
                    self._total_errors += 1
        elif isinstance(input_data, list):
            # 列表逐项预测
            for idx, item in enumerate(input_data):
                try:
                    result = await self.predict(item, **kwargs)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"第 {idx} 项预测失败: {str(e)}")
                    self._total_errors += 1
        else:
            # 单次预测
            result = await self.predict(input_data, **kwargs)
            results.append(result)

        self._last_prediction_time = datetime.utcnow()
        self._total_predictions += len(results)
        return results

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "name": self.name,
            "prediction_type": self.prediction_type.value,
            "model_type": self.model_type.value,
            "is_trained": self._is_trained,
            "last_training_time": self._last_training_time.isoformat() if self._last_training_time else None,
            "last_prediction_time": self._last_prediction_time.isoformat() if self._last_prediction_time else None,
            "total_predictions": self._total_predictions,
            "total_errors": self._total_errors,
            "needs_retraining": self.needs_retraining,
            "model_metrics": self._model_metrics.to_dict() if self._model_metrics else None,
            "config": {
                "enabled": self.config.enabled,
                "retrain_interval_hours": self.config.retrain_interval_hours,
                "prediction_horizon": self.config.prediction_horizon,
                "confidence_threshold": self.config.confidence_threshold,
                "max_training_samples": self.config.max_training_samples
            }
        }

    async def save_model(self, filepath: str) -> bool:
        """保存模型到文件"""
        try:
            self.logger.info(f"保存模型到: {filepath}")
            success = await self._save_model_impl(filepath)
            if success:
                self.logger.info("模型保存成功")
            return success
        except Exception as e:
            self.logger.error(f"模型保存失败: {str(e)}")
            return False

    async def load_model(self, filepath: str) -> bool:
        """从文件加载模型"""
        try:
            self.logger.info(f"从文件加载模型: {filepath}")
            success = await self._load_model_impl(filepath)
            if success:
                self._is_trained = True
                self.logger.info("模型加载成功")
            return success
        except Exception as e:
            self.logger.error(f"模型加载失败: {str(e)}")
            return False

    @abstractmethod
    async def _save_model_impl(self, filepath: str) -> bool:
        """保存模型的具体实现"""
        pass

    @abstractmethod
    async def _load_model_impl(self, filepath: str) -> bool:
        """加载模型的具体实现"""
        pass

    async def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """获取特征重要性（如果适用）"""
        try:
            return await self._get_feature_importance_impl()
        except Exception as e:
            self.logger.warning(f"获取特征重要性失败: {str(e)}")
            return None

    async def _get_feature_importance_impl(self) -> Optional[Dict[str, float]]:
        """获取特征重要性的具体实现"""
        # 默认实现，子类可重写
        return None