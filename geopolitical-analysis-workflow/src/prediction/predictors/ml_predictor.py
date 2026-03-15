"""
机器学习预测器
基于Scikit-learn、LightGBM、XGBoost等库的机器学习预测器
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
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
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
    from sklearn.svm import SVC, SVR
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
        mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn库未安装，机器学习预测功能将受限")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM库未安装")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost库未安装")


class MLPredictor(BasePredictor):
    """机器学习预测器"""

    def __init__(self, config: PredictorConfig):
        if config.prediction_type not in [PredictionType.CLASSIFICATION, PredictionType.REGRESSION,
                                         PredictionType.RISK_SCORE, PredictionType.EVENT_PROBABILITY]:
            raise ValueError(f"MLPredictor不支持 {config.prediction_type.value} 预测类型")

        super().__init__(config)
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.feature_columns = []
        self.target_column = self.config.params.get("target_column", "target")
        self.model_type_name = self.config.params.get("model", "random_forest")
        self._model_params = self.config.params.get("model_params", {})
        self.classes_ = None  # 分类任务的类别

    async def train(self, training_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                   labels: Optional[Union[np.ndarray, List]] = None,
                   **kwargs) -> bool:
        """
        训练机器学习模型

        Args:
            training_data: 训练数据
            labels: 标签（监督学习）
            **kwargs: 其他参数

        Returns:
            bool: 训练是否成功
        """
        try:
            # 准备数据
            X, y = self._prepare_training_data(training_data, labels)

            if X is None or len(X) == 0:
                self.logger.error("训练数据为空或格式错误")
                return False

            # 数据预处理
            X_processed = await self._preprocess_data(X, training=True)

            # 根据模型类型训练
            model_func = self._get_model_factory()
            if model_func is None:
                self.logger.error(f"不支持的模型类型或库未安装: {self.model_type_name}")
                return False

            self.model = model_func()
            self.model.fit(X_processed, y)

            # 保存类别信息（分类任务）
            if self.prediction_type in [PredictionType.CLASSIFICATION, PredictionType.EVENT_PROBABILITY]:
                if hasattr(self.model, 'classes_'):
                    self.classes_ = self.model.classes_.tolist()
                else:
                    # 从y中提取唯一类别
                    self.classes_ = list(np.unique(y))

            self._is_trained = True
            self._last_training_time = datetime.utcnow()
            self.logger.info(f"机器学习模型训练成功: {self.model_type_name}")
            return True

        except Exception as e:
            self.logger.error(f"机器学习模型训练失败: {str(e)}")
            self._total_errors += 1
            return False

    async def predict(self, input_data: Union[pd.DataFrame, np.ndarray, List[Dict], Dict],
                     **kwargs) -> PredictionResult:
        """
        进行机器学习预测

        Args:
            input_data: 输入数据
            **kwargs: 其他参数

        Returns:
            PredictionResult: 预测结果
        """
        if not self._is_trained or self.model is None:
            raise ValueError("模型未训练，请先训练模型")

        try:
            # 准备预测数据
            X = self._prepare_prediction_data(input_data)

            if X is None:
                raise ValueError("输入数据格式错误")

            # 数据预处理
            X_processed = await self._preprocess_data(X, training=False)

            # 进行预测
            if self.prediction_type in [PredictionType.CLASSIFICATION, PredictionType.EVENT_PROBABILITY]:
                # 分类预测
                if hasattr(self.model, 'predict_proba'):
                    probabilities = self.model.predict_proba(X_processed)
                    if len(probabilities.shape) == 2 and probabilities.shape[1] > 1:
                        predicted_class_idx = np.argmax(probabilities[0])
                        predicted_value = self.classes_[predicted_class_idx] if self.classes_ else predicted_class_idx
                        confidence_score = float(probabilities[0][predicted_class_idx])
                    else:
                        predicted_value = self.model.predict(X_processed)[0]
                        confidence_score = 0.5  # 默认置信度
                else:
                    predicted_value = self.model.predict(X_processed)[0]
                    confidence_score = 0.5
            else:
                # 回归预测
                predicted_value = float(self.model.predict(X_processed)[0])
                # 计算置信度（基于模型类型）
                confidence_score = self._calculate_regression_confidence(X_processed)

            # 获取特征重要性（如果可用）
            feature_importance = await self.get_feature_importance()
            if feature_importance:
                used_features = list(feature_importance.keys())
            else:
                used_features = self.feature_columns

            # 创建预测结果
            result = PredictionResult(
                prediction_id=f"ml_{datetime.utcnow().timestamp()}",
                model_id=self.name,
                target_type=self.target_column,
                predicted_value=predicted_value,
                confidence_score=confidence_score,
                prediction_type=self.prediction_type,
                features_used=used_features,
                metadata={
                    "model_type": self.model_type_name,
                    "model_params": self._model_params,
                    "prediction_timestamp": datetime.utcnow().isoformat()
                }
            )

            self._last_prediction_time = datetime.utcnow()
            self._total_predictions += 1
            return result

        except Exception as e:
            self.logger.error(f"机器学习预测失败: {str(e)}")
            self._total_errors += 1
            raise

    async def evaluate(self, test_data: Union[pd.DataFrame, np.ndarray, List[Dict]],
                      test_labels: Optional[Union[np.ndarray, List]] = None,
                      **kwargs) -> ModelMetrics:
        """
        评估机器学习模型性能

        Args:
            test_data: 测试数据
            test_labels: 测试标签
            **kwargs: 其他参数

        Returns:
            ModelMetrics: 模型评估指标
        """
        if not self._is_trained or self.model is None:
            raise ValueError("模型未训练，请先训练模型")

        try:
            # 准备测试数据
            X_test, y_test = self._prepare_training_data(test_data, test_labels)

            if X_test is None or len(X_test) == 0:
                raise ValueError("测试数据为空或格式错误")

            # 数据预处理
            X_test_processed = await self._preprocess_data(X_test, training=False)

            # 进行预测
            y_pred = self.model.predict(X_test_processed)

            # 计算评估指标
            metrics = ModelMetrics(model_id=self.name)

            if self.prediction_type in [PredictionType.CLASSIFICATION, PredictionType.EVENT_PROBABILITY]:
                # 分类指标
                metrics.accuracy = float(accuracy_score(y_test, y_pred))
                metrics.precision = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
                metrics.recall = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
                metrics.f1_score = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))

                # 尝试计算AUC（需要概率预测）
                if hasattr(self.model, 'predict_proba'):
                    try:
                        y_proba = self.model.predict_proba(X_test_processed)
                        if len(np.unique(y_test)) == 2:  # 二分类
                            metrics.auc = float(roc_auc_score(y_test, y_proba[:, 1]))
                        else:  # 多分类
                            metrics.auc = float(roc_auc_score(y_test, y_proba, multi_class='ovr'))
                    except:
                        pass

            else:
                # 回归指标
                y_test_numeric = np.array(y_test, dtype=float)
                y_pred_numeric = np.array(y_pred, dtype=float)

                metrics.mae = float(mean_absolute_error(y_test_numeric, y_pred_numeric))
                metrics.mse = float(mean_squared_error(y_test_numeric, y_pred_numeric))
                metrics.rmse = float(np.sqrt(metrics.mse))

                # 计算MAPE（避免除以0）
                try:
                    metrics.mape = float(mean_absolute_percentage_error(y_test_numeric, y_pred_numeric))
                except:
                    pass

                metrics.r2_score = float(r2_score(y_test_numeric, y_pred_numeric))

            return metrics

        except Exception as e:
            self.logger.error(f"机器学习模型评估失败: {str(e)}")
            # 返回默认指标
            return ModelMetrics(model_id=self.name)

    def _prepare_training_data(self, data: Any, labels: Optional[Any] = None) -> Tuple[Optional[pd.DataFrame], Optional[np.ndarray]]:
        """准备训练数据"""
        try:
            if isinstance(data, pd.DataFrame):
                df = data.copy()
                # 提取特征和目标
                if self.target_column in df.columns and labels is None:
                    X = df.drop(columns=[self.target_column])
                    y = df[self.target_column].values
                else:
                    X = df
                    y = np.array(labels) if labels is not None else None
            elif isinstance(data, list):
                df = pd.DataFrame(data)
                if self.target_column in df.columns and labels is None:
                    X = df.drop(columns=[self.target_column])
                    y = df[self.target_column].values
                else:
                    X = df
                    y = np.array(labels) if labels is not None else None
            elif isinstance(data, np.ndarray):
                X = pd.DataFrame(data)
                y = labels
            elif isinstance(data, dict):
                X = pd.DataFrame([data])
                if self.target_column in X.columns and labels is None:
                    y = X[self.target_column].values
                    X = X.drop(columns=[self.target_column])
                else:
                    y = labels
            else:
                raise ValueError(f"不支持的数据类型: {type(data)}")

            # 记录特征列
            self.feature_columns = list(X.columns)

            # 处理目标变量（分类任务需要编码）
            if y is not None and self.prediction_type in [PredictionType.CLASSIFICATION, PredictionType.EVENT_PROBABILITY]:
                if self.label_encoder is None:
                    self.label_encoder = LabelEncoder()
                    y = self.label_encoder.fit_transform(y)
                else:
                    # 使用已有的编码器
                    try:
                        y = self.label_encoder.transform(y)
                    except:
                        # 遇到新类别，重新拟合
                        self.label_encoder = LabelEncoder()
                        y = self.label_encoder.fit_transform(y)

            return X, y

        except Exception as e:
            self.logger.error(f"准备训练数据失败: {str(e)}")
            return None, None

    def _prepare_prediction_data(self, data: Any) -> Optional[pd.DataFrame]:
        """准备预测数据"""
        try:
            if isinstance(data, pd.DataFrame):
                X = data.copy()
            elif isinstance(data, list):
                X = pd.DataFrame(data)
            elif isinstance(data, dict):
                X = pd.DataFrame([data])
            elif isinstance(data, np.ndarray):
                X = pd.DataFrame(data)
                if len(X.columns) == len(self.feature_columns):
                    X.columns = self.feature_columns
            else:
                raise ValueError(f"不支持的数据类型: {type(data)}")

            # 确保特征顺序一致
            if self.feature_columns:
                missing_cols = set(self.feature_columns) - set(X.columns)
                if missing_cols:
                    for col in missing_cols:
                        X[col] = 0  # 用0填充缺失特征
                X = X[self.feature_columns]

            return X

        except Exception as e:
            self.logger.error(f"准备预测数据失败: {str(e)}")
            return None

    async def _preprocess_data(self, X: pd.DataFrame, training: bool = True) -> np.ndarray:
        """数据预处理"""
        try:
            # 处理缺失值
            X_filled = X.fillna(0)

            # 特征缩放
            if training:
                self.scaler = StandardScaler()
                X_scaled = self.scaler.fit_transform(X_filled)
            else:
                if self.scaler is not None:
                    X_scaled = self.scaler.transform(X_filled)
                else:
                    X_scaled = X_filled.values

            return X_scaled

        except Exception as e:
            self.logger.error(f"数据预处理失败: {str(e)}")
            return X.values if hasattr(X, 'values') else np.array(X)

    def _get_model_factory(self) -> Optional[callable]:
        """获取模型工厂函数"""
        model_map = {}

        if SKLEARN_AVAILABLE:
            model_map.update({
                'random_forest_classifier': lambda: RandomForestClassifier(**self._model_params),
                'random_forest_regressor': lambda: RandomForestRegressor(**self._model_params),
                'gradient_boosting_classifier': lambda: GradientBoostingClassifier(**self._model_params),
                'gradient_boosting_regressor': lambda: GradientBoostingRegressor(**self._model_params),
                'logistic_regression': lambda: LogisticRegression(**self._model_params),
                'linear_regression': lambda: LinearRegression(**self._model_params),
                'ridge': lambda: Ridge(**self._model_params),
                'lasso': lambda: Lasso(**self._model_params),
                'svc': lambda: SVC(**self._model_params, probability=True),
                'svr': lambda: SVR(**self._model_params),
                'mlp_classifier': lambda: MLPClassifier(**self._model_params),
                'mlp_regressor': lambda: MLPRegressor(**self._model_params)
            })

        if LIGHTGBM_AVAILABLE:
            model_map.update({
                'lightgbm_classifier': lambda: lgb.LGBMClassifier(**self._model_params),
                'lightgbm_regressor': lambda: lgb.LGBMRegressor(**self._model_params)
            })

        if XGBOOST_AVAILABLE:
            model_map.update({
                'xgboost_classifier': lambda: xgb.XGBClassifier(**self._model_params),
                'xgboost_regressor': lambda: xgb.XGBRegressor(**self._model_params)
            })

        # 根据预测类型选择默认模型
        if self.model_type_name in model_map:
            return model_map[self.model_type_name]
        else:
            # 尝试根据预测类型推断
            if self.prediction_type in [PredictionType.CLASSIFICATION, PredictionType.EVENT_PROBABILITY]:
                if 'random_forest_classifier' in model_map:
                    self.model_type_name = 'random_forest_classifier'
                    return model_map['random_forest_classifier']
            else:
                if 'random_forest_regressor' in model_map:
                    self.model_type_name = 'random_forest_regressor'
                    return model_map['random_forest_regressor']

        return None

    def _calculate_regression_confidence(self, X: np.ndarray) -> float:
        """计算回归预测的置信度"""
        # 简单的置信度估计
        # 可以基于训练集误差、特征相似度等计算
        # 这里返回一个默认值，子类可以重写此方法

        if hasattr(self.model, 'oob_score_'):
            # 随机森林的袋外分数
            return float(self.model.oob_score_)
        elif hasattr(self.model, 'score'):
            try:
                # 使用模型在训练集上的分数
                return float(max(0.0, min(1.0, (self.model.score + 1) / 2)))  # 将[-1,1]映射到[0,1]
            except:
                pass

        # 默认置信度
        return 0.7

    async def _save_model_impl(self, filepath: str) -> bool:
        """保存模型到文件"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'label_encoder': self.label_encoder,
                'feature_columns': self.feature_columns,
                'target_column': self.target_column,
                'model_type_name': self.model_type_name,
                'model_params': self._model_params,
                'prediction_type': self.prediction_type.value,
                'classes_': self.classes_,
                'config': self.config
            }

            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)

            return True

        except Exception as e:
            self.logger.error(f"保存模型失败: {str(e)}")
            return False

    async def _load_model_impl(self, filepath: str) -> bool:
        """从文件加载模型"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.label_encoder = model_data['label_encoder']
            self.feature_columns = model_data['feature_columns']
            self.target_column = model_data['target_column']
            self.model_type_name = model_data['model_type_name']
            self._model_params = model_data['model_params']
            self.classes_ = model_data['classes_']
            # 注意：不覆盖config，只恢复模型状态

            self._is_trained = True
            return True

        except Exception as e:
            self.logger.error(f"加载模型失败: {str(e)}")
            return False

    async def _get_feature_importance_impl(self) -> Optional[Dict[str, float]]:
        """获取特征重要性"""
        try:
            if self.model is None or not self._is_trained:
                return None

            # 检查模型是否支持特征重要性
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif hasattr(self.model, 'coef_'):
                # 线性模型系数
                if len(self.model.coef_.shape) == 1:
                    importances = np.abs(self.model.coef_)
                else:
                    # 多分类情况，取平均绝对值
                    importances = np.mean(np.abs(self.model.coef_), axis=0)
            else:
                return None

            # 归一化到[0,1]
            if importances.sum() > 0:
                importances = importances / importances.sum()

            # 创建特征名称到重要性的映射
            feature_importance = {}
            for idx, col in enumerate(self.feature_columns):
                if idx < len(importances):
                    feature_importance[col] = float(importances[idx])

            return feature_importance

        except Exception as e:
            self.logger.warning(f"获取特征重要性失败: {str(e)}")
            return None