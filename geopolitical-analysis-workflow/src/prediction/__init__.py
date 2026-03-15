"""
预测模块
提供时间序列和机器学习预测功能
"""

from .base_predictor import (
    BasePredictor,
    PredictorConfig,
    PredictionType,
    ModelType,
    PredictionResult,
    ModelMetrics
)

from .model_manager import ModelManager

# 导入预测器实现
try:
    from .predictors.time_series import TimeSeriesPredictor
    TIME_SERIES_AVAILABLE = True
except ImportError as e:
    TIME_SERIES_AVAILABLE = False
    logger = __import__('logging').getLogger(__name__)
    logger.warning(f"时间序列预测器导入失败: {e}")

try:
    from .predictors.ml_predictor import MLPredictor
    ML_PREDICTOR_AVAILABLE = True
except ImportError as e:
    ML_PREDICTOR_AVAILABLE = False
    logger = __import__('logging').getLogger(__name__)
    logger.warning(f"机器学习预测器导入失败: {e}")

__all__ = [
    'BasePredictor',
    'PredictorConfig',
    'PredictionType',
    'ModelType',
    'PredictionResult',
    'ModelMetrics',
    'ModelManager',
    'TimeSeriesPredictor',
    'MLPredictor',
    'TIME_SERIES_AVAILABLE',
    'ML_PREDICTOR_AVAILABLE'
]