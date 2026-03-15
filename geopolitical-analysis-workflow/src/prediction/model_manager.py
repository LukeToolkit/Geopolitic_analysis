"""
预测模型管理器
管理所有预测器实例，提供统一的训练、预测和评估接口
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, field
import json

from .base_predictor import BasePredictor, PredictorConfig, PredictionType, ModelType, PredictionResult, ModelMetrics

logger = logging.getLogger(__name__)


@dataclass
class ModelRegistryEntry:
    """模型注册表条目"""
    predictor: BasePredictor
    config: PredictorConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    performance_history: List[ModelMetrics] = field(default_factory=list)


class ModelManager:
    """预测模型管理器"""

    def __init__(self):
        self._predictors: Dict[str, ModelRegistryEntry] = {}
        self._by_type: Dict[PredictionType, List[str]] = {}
        self._by_model_type: Dict[ModelType, List[str]] = {}
        self.logger = logging.getLogger(__name__)

    def register_predictor(self, predictor: BasePredictor) -> None:
        """注册预测器"""
        name = predictor.name

        if name in self._predictors:
            self.logger.warning(f"预测器 '{name}' 已存在，将被替换")

        # 创建注册表条目
        entry = ModelRegistryEntry(
            predictor=predictor,
            config=predictor.config
        )

        self._predictors[name] = entry

        # 按预测类型索引
        pred_type = predictor.prediction_type
        if pred_type not in self._by_type:
            self._by_type[pred_type] = []
        if name not in self._by_type[pred_type]:
            self._by_type[pred_type].append(name)

        # 按模型类型索引
        model_type = predictor.model_type
        if model_type not in self._by_model_type:
            self._by_model_type[model_type] = []
        if name not in self._by_model_type[model_type]:
            self._by_model_type[model_type].append(name)

        self.logger.info(f"注册预测器: {name} ({pred_type.value}/{model_type.value})")

    def unregister_predictor(self, name: str) -> None:
        """注销预测器"""
        if name in self._predictors:
            entry = self._predictors.pop(name)
            predictor = entry.predictor

            # 从类型索引中移除
            pred_type = predictor.prediction_type
            if pred_type in self._by_type and name in self._by_type[pred_type]:
                self._by_type[pred_type].remove(name)
                if not self._by_type[pred_type]:
                    del self._by_type[pred_type]

            model_type = predictor.model_type
            if model_type in self._by_model_type and name in self._by_model_type[model_type]:
                self._by_model_type[model_type].remove(name)
                if not self._by_model_type[model_type]:
                    del self._by_model_type[model_type]

            self.logger.info(f"注销预测器: {name}")

    def get_predictor(self, name: str) -> Optional[BasePredictor]:
        """获取预测器"""
        entry = self._predictors.get(name)
        return entry.predictor if entry else None

    def get_predictors_by_type(self, prediction_type: PredictionType) -> List[BasePredictor]:
        """按预测类型获取预测器"""
        predictor_names = self._by_type.get(prediction_type, [])
        predictors = []
        for name in predictor_names:
            entry = self._predictors.get(name)
            if entry:
                predictors.append(entry.predictor)
        return predictors

    def get_predictors_by_model_type(self, model_type: ModelType) -> List[BasePredictor]:
        """按模型类型获取预测器"""
        predictor_names = self._by_model_type.get(model_type, [])
        predictors = []
        for name in predictor_names:
            entry = self._predictors.get(name)
            if entry:
                predictors.append(entry.predictor)
        return predictors

    def get_all_predictors(self) -> List[BasePredictor]:
        """获取所有预测器"""
        return [entry.predictor for entry in self._predictors.values()]

    def get_enabled_predictors(self) -> List[BasePredictor]:
        """获取启用的预测器"""
        return [entry.predictor for entry in self._predictors.values() if entry.config.enabled]

    def _update_usage_stats(self, name: str) -> None:
        """更新使用统计"""
        if name in self._predictors:
            entry = self._predictors[name]
            entry.last_used = datetime.utcnow()
            entry.usage_count += 1

    async def train_predictor(self, name: str, training_data: Any, **kwargs) -> bool:
        """训练指定预测器"""
        predictor = self.get_predictor(name)
        if not predictor:
            self.logger.error(f"预测器不存在: {name}")
            return False

        try:
            labels = kwargs.pop('labels', None)
            success = await predictor.train(training_data, labels=labels, **kwargs)

            if success:
                self._update_usage_stats(name)
                self.logger.info(f"预测器训练成功: {name}")
            else:
                self.logger.error(f"预测器训练失败: {name}")

            return success

        except Exception as e:
            self.logger.error(f"预测器训练过程中出错: {name}, 错误: {str(e)}")
            return False

    async def train_all(self, training_data_dict: Dict[str, Any], **kwargs) -> Dict[str, bool]:
        """训练所有启用的预测器"""
        results = {}
        predictors = self.get_enabled_predictors()

        # 并行训练
        tasks = []
        for predictor in predictors:
            data = training_data_dict.get(predictor.name)
            if data is not None:
                task = self.train_predictor(predictor.name, data, **kwargs)
                tasks.append(task)
            else:
                self.logger.warning(f"找不到预测器 {predictor.name} 的训练数据")

        # 等待所有任务完成
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            for predictor, result in zip(predictors, task_results):
                if isinstance(result, Exception):
                    self.logger.error(f"预测器 {predictor.name} 训练异常: {str(result)}")
                    results[predictor.name] = False
                else:
                    results[predictor.name] = result

        return results

    async def predict(self, name: str, input_data: Any, **kwargs) -> Optional[PredictionResult]:
        """使用指定预测器进行预测"""
        predictor = self.get_predictor(name)
        if not predictor:
            self.logger.error(f"预测器不存在: {name}")
            return None

        if not predictor.is_trained:
            self.logger.warning(f"预测器未训练: {name}")
            return None

        try:
            result = await predictor.predict(input_data, **kwargs)
            self._update_usage_stats(name)
            return result

        except Exception as e:
            self.logger.error(f"预测过程中出错: {name}, 错误: {str(e)}")
            return None

    async def predict_batch(self, name: str, input_data: Any, **kwargs) -> List[PredictionResult]:
        """使用指定预测器进行批量预测"""
        predictor = self.get_predictor(name)
        if not predictor:
            self.logger.error(f"预测器不存在: {name}")
            return []

        if not predictor.is_trained:
            self.logger.warning(f"预测器未训练: {name}")
            return []

        try:
            results = await predictor.predict_batch(input_data, **kwargs)
            self._update_usage_stats(name)
            return results

        except Exception as e:
            self.logger.error(f"批量预测过程中出错: {name}, 错误: {str(e)}")
            return []

    async def ensemble_predict(self, prediction_type: PredictionType, input_data: Any,
                             strategy: str = "weighted_average", **kwargs) -> Optional[PredictionResult]:
        """
        集成预测：使用多个同类型预测器进行预测并组合结果

        Args:
            prediction_type: 预测类型
            input_data: 输入数据
            strategy: 组合策略 (weighted_average, majority_vote, best_model)
            **kwargs: 其他参数

        Returns:
            Optional[PredictionResult]: 集成预测结果
        """
        predictors = self.get_predictors_by_type(prediction_type)
        if not predictors:
            self.logger.error(f"没有找到 {prediction_type.value} 类型的预测器")
            return None

        # 过滤已训练的预测器
        trained_predictors = [p for p in predictors if p.is_trained]
        if not trained_predictors:
            self.logger.error(f"没有已训练的 {prediction_type.value} 类型预测器")
            return None

        try:
            # 并行获取所有预测结果
            tasks = [p.predict(input_data, **kwargs) for p in trained_predictors]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤异常结果
            valid_results = []
            valid_predictors = []
            for predictor, result in zip(trained_predictors, results):
                if isinstance(result, Exception):
                    self.logger.warning(f"预测器 {predictor.name} 预测异常: {str(result)}")
                else:
                    valid_results.append(result)
                    valid_predictors.append(predictor)

            if not valid_results:
                self.logger.error("所有预测器都预测失败")
                return None

            # 根据策略组合结果
            if strategy == "weighted_average" and prediction_type in [PredictionType.REGRESSION, PredictionType.RISK_SCORE]:
                # 加权平均（根据置信度加权）
                weights = [r.confidence_score for r in valid_results]
                total_weight = sum(weights)
                if total_weight > 0:
                    weighted_values = [r.predicted_value * w for r, w in zip(valid_results, weights)]
                    avg_value = sum(weighted_values) / total_weight
                    avg_confidence = sum(weights) / len(weights)

                    # 创建集成预测结果
                    ensemble_result = PredictionResult(
                        prediction_id=f"ensemble_{datetime.utcnow().timestamp()}",
                        model_id="ensemble",
                        target_type=valid_results[0].target_type,
                        predicted_value=avg_value,
                        confidence_score=avg_confidence,
                        prediction_type=prediction_type,
                        features_used=list(set([f for r in valid_results for f in r.features_used])),
                        metadata={
                            "strategy": strategy,
                            "component_models": [p.name for p in valid_predictors],
                            "component_weights": weights,
                            "component_results": [r.to_dict() for r in valid_results]
                        }
                    )
                    return ensemble_result

            elif strategy == "majority_vote" and prediction_type in [PredictionType.CLASSIFICATION]:
                # 多数投票
                from collections import Counter
                votes = [r.predicted_value for r in valid_results]
                vote_counts = Counter(votes)
                majority_value = vote_counts.most_common(1)[0][0]
                confidence = vote_counts[majority_value] / len(votes)

                ensemble_result = PredictionResult(
                    prediction_id=f"ensemble_{datetime.utcnow().timestamp()}",
                    model_id="ensemble",
                    target_type=valid_results[0].target_type,
                    predicted_value=majority_value,
                    confidence_score=confidence,
                    prediction_type=prediction_type,
                    features_used=list(set([f for r in valid_results for f in r.features_used])),
                    metadata={
                        "strategy": strategy,
                        "component_models": [p.name for p in valid_predictors],
                        "vote_counts": dict(vote_counts),
                        "component_results": [r.to_dict() for r in valid_results]
                    }
                )
                return ensemble_result

            elif strategy == "best_model":
                # 选择置信度最高的模型
                best_result = max(valid_results, key=lambda r: r.confidence_score)
                best_result.metadata["ensemble_strategy"] = strategy
                best_result.metadata["component_models"] = [p.name for p in valid_predictors]
                return best_result

            else:
                self.logger.warning(f"不支持的策略或预测类型组合: {strategy}/{prediction_type.value}")
                # 默认返回第一个结果
                valid_results[0].metadata["ensemble_strategy"] = "first_valid"
                valid_results[0].metadata["component_models"] = [p.name for p in valid_predictors]
                return valid_results[0]

        except Exception as e:
            self.logger.error(f"集成预测过程中出错: {str(e)}")
            return None

    async def evaluate_predictor(self, name: str, test_data: Any, **kwargs) -> Optional[ModelMetrics]:
        """评估指定预测器"""
        predictor = self.get_predictor(name)
        if not predictor:
            self.logger.error(f"预测器不存在: {name}")
            return None

        if not predictor.is_trained:
            self.logger.warning(f"预测器未训练: {name}")
            return None

        try:
            test_labels = kwargs.pop('test_labels', None)
            metrics = await predictor.evaluate(test_data, test_labels=test_labels, **kwargs)

            # 保存评估结果到历史记录
            if name in self._predictors:
                self._predictors[name].performance_history.append(metrics)
                # 保留最近10次评估结果
                if len(self._predictors[name].performance_history) > 10:
                    self._predictors[name].performance_history = self._predictors[name].performance_history[-10:]

            self._update_usage_stats(name)
            return metrics

        except Exception as e:
            self.logger.error(f"评估过程中出错: {name}, 错误: {str(e)}")
            return None

    def get_predictor_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """获取预测器统计信息"""
        entry = self._predictors.get(name)
        if not entry:
            return None

        predictor = entry.predictor
        stats = predictor.get_model_info()

        # 添加管理器统计信息
        stats.update({
            "created_at": entry.created_at.isoformat(),
            "last_used": entry.last_used.isoformat() if entry.last_used else None,
            "usage_count": entry.usage_count,
            "performance_history_count": len(entry.performance_history),
            "performance_trend": self._calculate_performance_trend(entry.performance_history)
        })

        return stats

    def _calculate_performance_trend(self, history: List[ModelMetrics]) -> Dict[str, Any]:
        """计算性能趋势"""
        if len(history) < 2:
            return {"trend": "insufficient_data", "change": 0.0}

        # 使用主要指标计算趋势
        recent = history[-1]
        previous = history[-2]

        # 根据指标类型选择主要指标
        if recent.accuracy is not None:
            current = recent.accuracy
            previous_val = previous.accuracy if previous.accuracy is not None else 0.0
            metric = "accuracy"
        elif recent.rmse is not None:
            current = recent.rmse
            previous_val = previous.rmse if previous.rmse is not None else 0.0
            metric = "rmse"
            # 对于误差指标，下降表示改进
            change = (previous_val - current) / previous_val if previous_val > 0 else 0.0
            return {
                "trend": "improving" if change > 0.01 else "stable" if abs(change) <= 0.01 else "declining",
                "change": change,
                "metric": metric
            }
        elif recent.r2_score is not None:
            current = recent.r2_score
            previous_val = previous.r2_score if previous.r2_score is not None else 0.0
            metric = "r2_score"
        else:
            return {"trend": "unknown", "change": 0.0}

        if previous_val == 0:
            change = 0.0
        else:
            change = (current - previous_val) / previous_val

        if change > 0.01:
            trend = "improving"
        elif change < -0.01:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change": change,
            "metric": metric
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有预测器的统计信息"""
        stats = {}
        for name in self._predictors:
            stats[name] = self.get_predictor_stats(name)
        return stats

    def save_registry(self, filepath: str) -> bool:
        """保存注册表到文件"""
        try:
            registry_data = {
                "predictors": {}
            }

            for name, entry in self._predictors.items():
                registry_data["predictors"][name] = {
                    "config": {
                        "name": entry.config.name,
                        "prediction_type": entry.config.prediction_type.value,
                        "model_type": entry.config.model_type.value,
                        "enabled": entry.config.enabled,
                        "retrain_interval_hours": entry.config.retrain_interval_hours,
                        "prediction_horizon": entry.config.prediction_horizon,
                        "confidence_threshold": entry.config.confidence_threshold,
                        "max_training_samples": entry.config.max_training_samples,
                        "params": entry.config.params
                    },
                    "created_at": entry.created_at.isoformat(),
                    "last_used": entry.last_used.isoformat() if entry.last_used else None,
                    "usage_count": entry.usage_count,
                    "performance_history": [m.to_dict() for m in entry.performance_history]
                }

            with open(filepath, 'w') as f:
                json.dump(registry_data, f, indent=2)

            self.logger.info(f"注册表保存到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"保存注册表失败: {str(e)}")
            return False

    async def load_registry(self, filepath: str, predictor_factory: callable) -> bool:
        """从文件加载注册表"""
        try:
            with open(filepath, 'r') as f:
                registry_data = json.load(f)

            # 清空当前注册表
            self._predictors.clear()
            self._by_type.clear()
            self._by_model_type.clear()

            # 重新注册预测器
            for name, data in registry_data["predictors"].items():
                config_dict = data["config"]
                config = PredictorConfig(
                    name=config_dict["name"],
                    prediction_type=PredictionType(config_dict["prediction_type"]),
                    model_type=ModelType(config_dict["model_type"]),
                    enabled=config_dict["enabled"],
                    retrain_interval_hours=config_dict["retrain_interval_hours"],
                    prediction_horizon=config_dict["prediction_horizon"],
                    confidence_threshold=config_dict["confidence_threshold"],
                    max_training_samples=config_dict["max_training_samples"],
                    params=config_dict["params"]
                )

                # 使用工厂函数创建预测器
                predictor = predictor_factory(config)
                if predictor:
                    self.register_predictor(predictor)

                    # 恢复历史数据
                    if name in self._predictors:
                        entry = self._predictors[name]
                        entry.created_at = datetime.fromisoformat(data["created_at"])
                        if data["last_used"]:
                            entry.last_used = datetime.fromisoformat(data["last_used"])
                        entry.usage_count = data["usage_count"]

                        # 恢复性能历史记录
                        for metric_data in data["performance_history"]:
                            metric = ModelMetrics(
                                model_id=metric_data["model_id"],
                                mae=metric_data.get("mae"),
                                mse=metric_data.get("mse"),
                                rmse=metric_data.get("rmse"),
                                mape=metric_data.get("mape"),
                                accuracy=metric_data.get("accuracy"),
                                precision=metric_data.get("precision"),
                                recall=metric_data.get("recall"),
                                f1_score=metric_data.get("f1_score"),
                                auc=metric_data.get("auc"),
                                r2_score=metric_data.get("r2_score"),
                                log_loss=metric_data.get("log_loss"),
                                evaluation_date=datetime.fromisoformat(metric_data["evaluation_date"])
                            )
                            entry.performance_history.append(metric)

            self.logger.info(f"注册表从 {filepath} 加载成功")
            return True

        except Exception as e:
            self.logger.error(f"加载注册表失败: {str(e)}")
            return False