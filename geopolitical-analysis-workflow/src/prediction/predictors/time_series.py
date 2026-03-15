"""
时间序列预测器
基于Prophet、ARIMA等模型的时间序列预测
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import json
import pickle
import numpy as np
import pandas as pd
from dataclasses import field

from ..base_predictor import (
    BasePredictor, PredictorConfig, PredictionType, ModelType,
    PredictionResult, ModelMetrics
)

logger = logging.getLogger(__name__)


try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet库未安装，时间序列预测功能将受限")

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels库未安装，ARIMA/SARIMA预测功能将受限")


class TimeSeriesPredictor(BasePredictor):
    """时间序列预测器"""

    def __init__(self, config: PredictorConfig):
        if config.prediction_type != PredictionType.TIME_SERIES:
            raise ValueError("TimeSeriesPredictor仅支持TIME_SERIES预测类型")

        super().__init__(config)
        self.model = None
        self.model_type_name = self.config.params.get("model", "prophet")  # prophet, arima, sarima, ets
        self.feature_columns = []
        self.target_column = self.config.params.get("target_column", "value")
        self.date_column = self.config.params.get("date_column", "date")
        self._model_params = self.config.params.get("model_params", {})

    async def train(self, training_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                   labels: Optional[Union[np.ndarray, List]] = None,
                   **kwargs) -> bool:
        """
        训练时间序列模型

        Args:
            training_data: 训练数据，应为DataFrame且包含日期列和目标列
            labels: 不用于时间序列，可忽略
            **kwargs: 其他参数

        Returns:
            bool: 训练是否成功
        """
        try:
            # 转换数据为DataFrame
            df = self._prepare_data(training_data)

            if df is None or len(df) < 10:
                self.logger.error(f"训练数据不足或格式错误: {len(df) if df is not None else 0} 条记录")
                return False

            # 根据模型类型训练
            if self.model_type_name == "prophet" and PROPHET_AVAILABLE:
                success = await self._train_prophet(df)
            elif self.model_type_name == "arima" and STATSMODELS_AVAILABLE:
                success = await self._train_arima(df)
            elif self.model_type_name == "sarima" and STATSMODELS_AVAILABLE:
                success = await self._train_sarima(df)
            elif self.model_type_name == "ets" and STATSMODELS_AVAILABLE:
                success = await self._train_ets(df)
            else:
                self.logger.error(f"不支持的模型类型或库未安装: {self.model_type_name}")
                return False

            if success:
                self._is_trained = True
                self._last_training_time = datetime.utcnow()
                self.logger.info(f"时间序列模型训练成功: {self.model_type_name}")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"时间序列训练失败: {str(e)}")
            self._total_errors += 1
            return False

    async def predict(self, input_data: Union[pd.DataFrame, np.ndarray, List[Dict], Dict],
                     **kwargs) -> PredictionResult:
        """
        进行时间序列预测

        Args:
            input_data: 输入数据，可以是DataFrame、字典或历史数据
            **kwargs:
                - horizon: 预测步长（默认使用config.prediction_horizon）
                - freq: 频率字符串（如'D'表示天，'H'表示小时）

        Returns:
            PredictionResult: 预测结果
        """
        if not self._is_trained or self.model is None:
            raise ValueError("模型未训练，请先训练模型")

        try:
            # 获取预测参数
            horizon = kwargs.get('horizon', self.config.prediction_horizon)
            freq = kwargs.get('freq', 'D')  # 默认天频率

            # 执行预测
            if self.model_type_name == "prophet" and PROPHET_AVAILABLE:
                forecast, confidence_interval = await self._predict_prophet(horizon, freq)
            elif self.model_type_name in ["arima", "sarima"] and STATSMODELS_AVAILABLE:
                forecast, confidence_interval = await self._predict_statsmodels(horizon, freq)
            elif self.model_type_name == "ets" and STATSMODELS_AVAILABLE:
                forecast, confidence_interval = await self._predict_ets(horizon, freq)
            else:
                raise ValueError(f"不支持的模型类型: {self.model_type_name}")

            # 计算置信度（基于预测区间宽度）
            confidence_score = self._calculate_confidence(forecast, confidence_interval)

            # 创建预测结果
            result = PredictionResult(
                prediction_id=f"ts_{datetime.utcnow().timestamp()}",
                model_id=self.name,
                target_type=self.target_column,
                predicted_value=forecast,
                confidence_score=confidence_score,
                prediction_type=PredictionType.TIME_SERIES,
                features_used=self.feature_columns,
                forecast_horizon=horizon,
                prediction_interval=confidence_interval,
                metadata={
                    "model_type": self.model_type_name,
                    "frequency": freq,
                    "horizon": horizon,
                    "model_params": self._model_params
                }
            )

            self._last_prediction_time = datetime.utcnow()
            self._total_predictions += 1
            return result

        except Exception as e:
            self.logger.error(f"时间序列预测失败: {str(e)}")
            self._total_errors += 1
            raise

    async def evaluate(self, test_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                      test_labels: Optional[Union[np.ndarray, List]] = None,
                      **kwargs) -> ModelMetrics:
        """
        评估时间序列模型性能

        Args:
            test_data: 测试数据
            test_labels: 不用于时间序列，可忽略
            **kwargs: 其他参数

        Returns:
            ModelMetrics: 模型评估指标
        """
        if not self._is_trained or self.model is None:
            raise ValueError("模型未训练，请先训练模型")

        try:
            # 准备测试数据
            test_df = self._prepare_data(test_data)
            if test_df is None or len(test_df) == 0:
                raise ValueError("测试数据格式错误或为空")

            # 将测试数据分为历史和未来
            split_ratio = kwargs.get('split_ratio', 0.8)
            split_idx = int(len(test_df) * split_ratio)
            history_df = test_df.iloc[:split_idx]
            actual_future = test_df.iloc[split_idx:][self.target_column].values

            # 重新训练模型（仅用于评估）
            if self.model_type_name == "prophet" and PROPHET_AVAILABLE:
                temp_model = Prophet(**self._model_params)
                history_df_prophet = history_df.rename(columns={self.date_column: 'ds', self.target_column: 'y'})
                temp_model.fit(history_df_prophet)
                forecast_horizon = len(actual_future)
                future = temp_model.make_future_dataframe(periods=forecast_horizon, freq='D')
                forecast = temp_model.predict(future)
                predicted = forecast['yhat'].values[-forecast_horizon:]
            elif self.model_type_name in ["arima", "sarima"] and STATSMODELS_AVAILABLE:
                # 简化的评估：使用历史数据预测
                predicted = []
                for i in range(len(actual_future)):
                    # 这里简化处理，实际应重新训练模型
                    predicted.append(np.mean(history_df[self.target_column].values))
                predicted = np.array(predicted)
            else:
                # 简化评估：使用均值预测
                predicted = np.full_like(actual_future, np.mean(history_df[self.target_column].values))

            # 计算评估指标
            metrics = self._calculate_metrics(actual_future, predicted)

            model_metrics = ModelMetrics(
                model_id=self.name,
                mae=metrics.get('mae'),
                mse=metrics.get('mse'),
                rmse=metrics.get('rmse'),
                mape=metrics.get('mape'),
                r2_score=metrics.get('r2_score')
            )

            return model_metrics

        except Exception as e:
            self.logger.error(f"时间序列模型评估失败: {str(e)}")
            # 返回默认指标
            return ModelMetrics(model_id=self.name)

    async def _train_prophet(self, df: pd.DataFrame) -> bool:
        """训练Prophet模型"""
        try:
            # 准备Prophet格式数据
            df_prophet = df.rename(columns={self.date_column: 'ds', self.target_column: 'y'})

            # 添加额外回归量
            extra_regressors = {}
            for col in self.feature_columns:
                if col != self.target_column and col != self.date_column:
                    df_prophet[col] = df[col]
                    extra_regressors[col] = {}

            # 创建并训练模型
            self.model = Prophet(**self._model_params)

            # 添加回归量
            for regressor in extra_regressors:
                self.model.add_regressor(regressor)

            self.model.fit(df_prophet)
            return True

        except Exception as e:
            self.logger.error(f"Prophet模型训练失败: {str(e)}")
            return False

    async def _train_arima(self, df: pd.DataFrame) -> bool:
        """训练ARIMA模型"""
        try:
            # 提取时间序列
            ts = df[self.target_column].values

            # 获取ARIMA参数
            order = self._model_params.get('order', (1, 1, 1))

            # 训练ARIMA模型
            self.model = ARIMA(ts, order=order)
            self.model = self.model.fit()
            return True

        except Exception as e:
            self.logger.error(f"ARIMA模型训练失败: {str(e)}")
            return False

    async def _train_sarima(self, df: pd.DataFrame) -> bool:
        """训练SARIMA模型"""
        try:
            # 提取时间序列
            ts = df[self.target_column].values

            # 获取SARIMA参数
            order = self._model_params.get('order', (1, 1, 1))
            seasonal_order = self._model_params.get('seasonal_order', (1, 1, 1, 7))  # 7天季节性

            # 训练SARIMA模型
            self.model = SARIMAX(ts, order=order, seasonal_order=seasonal_order)
            self.model = self.model.fit()
            return True

        except Exception as e:
            self.logger.error(f"SARIMA模型训练失败: {str(e)}")
            return False

    async def _train_ets(self, df: pd.DataFrame) -> bool:
        """训练指数平滑模型"""
        try:
            # 提取时间序列
            ts = df[self.target_column].values

            # 训练ETS模型
            self.model = ExponentialSmoothing(ts, **self._model_params)
            self.model = self.model.fit()
            return True

        except Exception as e:
            self.logger.error(f"ETS模型训练失败: {str(e)}")
            return False

    async def _predict_prophet(self, horizon: int, freq: str) -> Tuple[float, Tuple[float, float]]:
        """使用Prophet进行预测"""
        # 创建未来数据框
        future = self.model.make_future_dataframe(periods=horizon, freq=freq)

        # 添加回归量（如果存在）
        for col in self.feature_columns:
            if col != self.target_column and col != self.date_column:
                # 这里简化处理：使用最后的值填充未来回归量
                future[col] = self.model.history[col].iloc[-1] if col in self.model.history.columns else 0

        # 进行预测
        forecast = self.model.predict(future)

        # 获取预测结果
        last_prediction = forecast.iloc[-1]
        yhat = float(last_prediction['yhat'])
        yhat_lower = float(last_prediction['yhat_lower'])
        yhat_upper = float(last_prediction['yhat_upper'])

        return yhat, (yhat_lower, yhat_upper)

    async def _predict_statsmodels(self, horizon: int, freq: str) -> Tuple[float, Tuple[float, float]]:
        """使用statsmodels模型进行预测"""
        # 进行预测
        forecast_result = self.model.forecast(steps=horizon)

        # 获取置信区间
        if hasattr(self.model, 'get_forecast'):
            forecast_obj = self.model.get_forecast(steps=horizon)
            conf_int = forecast_obj.conf_int()
            if len(conf_int) > 0:
                lower, upper = conf_int.iloc[-1].values
            else:
                lower, upper = forecast_result[-1] * 0.9, forecast_result[-1] * 1.1
        else:
            # 简单置信区间
            std = np.std(self.model.resid) if hasattr(self.model, 'resid') else forecast_result[-1] * 0.1
            lower = forecast_result[-1] - 1.96 * std
            upper = forecast_result[-1] + 1.96 * std

        return float(forecast_result[-1]), (float(lower), float(upper))

    async def _predict_ets(self, horizon: int, freq: str) -> Tuple[float, Tuple[float, float]]:
        """使用ETS模型进行预测"""
        # 进行预测
        forecast_result = self.model.forecast(horizon)

        # 简化的置信区间
        if hasattr(self.model, 'sse'):
            std_error = np.sqrt(self.model.sse / len(self.model.fittedvalues))
            lower = forecast_result[-1] - 1.96 * std_error
            upper = forecast_result[-1] + 1.96 * std_error
        else:
            lower = forecast_result[-1] * 0.9
            upper = forecast_result[-1] * 1.1

        return float(forecast_result[-1]), (float(lower), float(upper))

    def _prepare_data(self, data: Any) -> Optional[pd.DataFrame]:
        """准备时间序列数据"""
        try:
            if isinstance(data, pd.DataFrame):
                df = data.copy()
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, np.ndarray):
                # 假设为二维数组 [date, value, ...]
                df = pd.DataFrame(data)
                if df.shape[1] >= 2:
                    df.columns = [self.date_column, self.target_column] + [f'feature_{i}' for i in range(2, df.shape[1])]
            else:
                raise ValueError(f"不支持的数据类型: {type(data)}")

            # 确保日期列是datetime类型
            if self.date_column in df.columns:
                df[self.date_column] = pd.to_datetime(df[self.date_column])
                df = df.sort_values(self.date_column)

            # 记录特征列
            self.feature_columns = list(df.columns)

            return df

        except Exception as e:
            self.logger.error(f"数据准备失败: {str(e)}")
            return None

    def _calculate_confidence(self, forecast: float, interval: Tuple[float, float]) -> float:
        """计算置信度评分"""
        if interval is None:
            return 0.5

        lower, upper = interval
        width = upper - lower

        if width <= 0:
            return 0.5

        # 宽度越小，置信度越高
        # 假设基准宽度为预测值的20%
        baseline_width = abs(forecast) * 0.2
        if baseline_width <= 0:
            baseline_width = 1.0

        confidence = max(0.1, min(0.9, baseline_width / width))
        return confidence

    def _calculate_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """计算时间序列评估指标"""
        metrics = {}

        try:
            # 确保长度一致
            min_len = min(len(actual), len(predicted))
            actual = actual[:min_len]
            predicted = predicted[:min_len]

            if min_len == 0:
                return metrics

            # 计算绝对误差
            errors = actual - predicted
            abs_errors = np.abs(errors)

            # MAE (平均绝对误差)
            metrics['mae'] = float(np.mean(abs_errors))

            # MSE (均方误差)
            metrics['mse'] = float(np.mean(errors ** 2))

            # RMSE (均方根误差)
            metrics['rmse'] = float(np.sqrt(metrics['mse']))

            # MAPE (平均绝对百分比误差)
            # 避免除以0
            non_zero_mask = actual != 0
            if np.any(non_zero_mask):
                mape = np.mean(np.abs(errors[non_zero_mask] / actual[non_zero_mask])) * 100
                metrics['mape'] = float(mape)

            # R²分数
            ss_res = np.sum(errors ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            if ss_tot > 0:
                metrics['r2_score'] = float(1 - (ss_res / ss_tot))
            else:
                metrics['r2_score'] = 0.0

        except Exception as e:
            self.logger.error(f"计算评估指标失败: {str(e)}")

        return metrics

    async def _save_model_impl(self, filepath: str) -> bool:
        """保存模型到文件"""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'model_type': self.model_type_name,
                    'feature_columns': self.feature_columns,
                    'target_column': self.target_column,
                    'date_column': self.date_column,
                    'model_params': self._model_params,
                    'config': self.config
                }, f)
            return True
        except Exception as e:
            self.logger.error(f"保存模型失败: {str(e)}")
            return False

    async def _load_model_impl(self, filepath: str) -> bool:
        """从文件加载模型"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)

            self.model = data['model']
            self.model_type_name = data['model_type']
            self.feature_columns = data['feature_columns']
            self.target_column = data['target_column']
            self.date_column = data['date_column']
            self._model_params = data['model_params']
            # 注意：不覆盖config，只恢复模型状态

            return True
        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            return False

    async def _get_feature_importance_impl(self) -> Optional[Dict[str, float]]:
        """获取特征重要性（如果适用）"""
        if self.model_type_name == "prophet" and hasattr(self.model, 'params'):
            # Prophet的特征重要性可以通过回归量系数估计
            importance = {}
            if hasattr(self.model, 'extra_regressors'):
                for name, regressor in self.model.extra_regressors.items():
                    if hasattr(regressor, 'prior_scale'):
                        # 使用先验尺度的倒数作为重要性指标（越小表示越重要）
                        importance[name] = 1.0 / regressor.prior_scale if regressor.prior_scale > 0 else 0.0
            return importance if importance else None
        return None