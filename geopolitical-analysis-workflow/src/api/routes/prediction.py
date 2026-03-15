"""
预测API路由
提供预测模型的训练、预测和评估接口
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field

from src.prediction import (
    BasePredictor, PredictorConfig, PredictionType, ModelType,
    PredictionResult, ModelMetrics, ModelManager,
    TimeSeriesPredictor, MLPredictor
)
from src.api.models.response import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prediction", tags=["prediction"])

# 全局模型管理器实例
_model_manager = ModelManager()


class PredictorConfigSchema(BaseModel):
    """预测器配置模式"""
    name: str = Field(..., description="预测器名称")
    prediction_type: str = Field(..., description="预测类型", examples=["time_series", "classification", "regression"])
    model_type: str = Field(..., description="模型类型", examples=["statistical", "machine_learning", "deep_learning"])
    enabled: bool = Field(True, description="是否启用")
    retrain_interval_hours: int = Field(24, description="重新训练间隔（小时）")
    prediction_horizon: int = Field(7, description="预测步长")
    confidence_threshold: float = Field(0.7, description="置信度阈值")
    max_training_samples: int = Field(10000, description="最大训练样本数")
    params: Dict[str, Any] = Field(default_factory=dict, description="模型参数")


class TrainRequest(BaseModel):
    """训练请求"""
    predictor_name: str = Field(..., description="预测器名称")
    training_data: List[Dict[str, Any]] = Field(..., description="训练数据")
    labels: Optional[List[Any]] = Field(None, description="标签（监督学习）")
    params: Optional[Dict[str, Any]] = Field(None, description="训练参数")


class PredictRequest(BaseModel):
    """预测请求"""
    predictor_name: str = Field(..., description="预测器名称")
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    params: Optional[Dict[str, Any]] = Field(None, description="预测参数")


class EvaluateRequest(BaseModel):
    """评估请求"""
    predictor_name: str = Field(..., description="预测器名称")
    test_data: List[Dict[str, Any]] = Field(..., description="测试数据")
    test_labels: Optional[List[Any]] = Field(None, description="测试标签")
    params: Optional[Dict[str, Any]] = Field(None, description="评估参数")


class EnsemblePredictRequest(BaseModel):
    """集成预测请求"""
    prediction_type: str = Field(..., description="预测类型")
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    strategy: str = Field("weighted_average", description="集成策略")
    params: Optional[Dict[str, Any]] = Field(None, description="预测参数")


@router.get("/models", response_model=APIResponse)
async def list_models(
    enabled_only: bool = Query(True, description="仅返回启用的模型"),
    prediction_type: Optional[str] = Query(None, description="按预测类型过滤"),
    model_type: Optional[str] = Query(None, description="按模型类型过滤")
):
    """
    列出所有预测模型
    """
    try:
        if enabled_only:
            predictors = _model_manager.get_enabled_predictors()
        else:
            predictors = _model_manager.get_all_predictors()

        # 过滤
        filtered_predictors = []
        for predictor in predictors:
            if prediction_type and predictor.prediction_type.value != prediction_type:
                continue
            if model_type and predictor.model_type.value != model_type:
                continue
            filtered_predictors.append(predictor)

        model_list = []
        for predictor in filtered_predictors:
            model_info = predictor.get_model_info()
            model_list.append(model_info)

        return APIResponse.success(
            data={
                "models": model_list,
                "count": len(model_list),
                "filters": {
                    "enabled_only": enabled_only,
                    "prediction_type": prediction_type,
                    "model_type": model_type
                }
            }
        )

    except Exception as e:
        logger.error(f"列出模型失败: {str(e)}")
        return APIResponse.error(message=f"列出模型失败: {str(e)}")


@router.get("/models/{model_name}", response_model=APIResponse)
async def get_model_details(model_name: str):
    """
    获取模型详细信息
    """
    try:
        stats = _model_manager.get_predictor_stats(model_name)
        if not stats:
            raise HTTPException(status_code=404, detail=f"模型不存在: {model_name}")

        return APIResponse.success(data=stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型详情失败: {str(e)}")
        return APIResponse.error(message=f"获取模型详情失败: {str(e)}")


@router.post("/models/register", response_model=APIResponse)
async def register_model(config: PredictorConfigSchema):
    """
    注册新预测模型
    """
    try:
        # 转换预测类型和模型类型
        try:
            pred_type = PredictionType(config.prediction_type)
            model_type = ModelType(config.model_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的类型: {str(e)}")

        # 创建配置对象
        predictor_config = PredictorConfig(
            name=config.name,
            prediction_type=pred_type,
            model_type=model_type,
            enabled=config.enabled,
            retrain_interval_hours=config.retrain_interval_hours,
            prediction_horizon=config.prediction_horizon,
            confidence_threshold=config.confidence_threshold,
            max_training_samples=config.max_training_samples,
            params=config.params
        )

        # 根据类型创建预测器
        predictor = None
        if pred_type == PredictionType.TIME_SERIES:
            if TimeSeriesPredictor is not None:
                predictor = TimeSeriesPredictor(predictor_config)
            else:
                raise HTTPException(status_code=400, detail="时间序列预测器不可用")
        elif pred_type in [PredictionType.CLASSIFICATION, PredictionType.REGRESSION,
                          PredictionType.RISK_SCORE, PredictionType.EVENT_PROBABILITY]:
            if MLPredictor is not None:
                predictor = MLPredictor(predictor_config)
            else:
                raise HTTPException(status_code=400, detail="机器学习预测器不可用")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的预测类型: {pred_type.value}")

        if predictor:
            _model_manager.register_predictor(predictor)
            return APIResponse.success(
                message=f"模型注册成功: {config.name}",
                data={"model_name": config.name}
            )
        else:
            return APIResponse.error(message="创建预测器失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册模型失败: {str(e)}")
        return APIResponse.error(message=f"注册模型失败: {str(e)}")


@router.delete("/models/{model_name}", response_model=APIResponse)
async def unregister_model(model_name: str):
    """
    注销预测模型
    """
    try:
        _model_manager.unregister_predictor(model_name)
        return APIResponse.success(message=f"模型注销成功: {model_name}")

    except Exception as e:
        logger.error(f"注销模型失败: {str(e)}")
        return APIResponse.error(message=f"注销模型失败: {str(e)}")


@router.post("/train", response_model=APIResponse)
async def train_model(request: TrainRequest, background_tasks: BackgroundTasks):
    """
    训练预测模型
    """
    try:
        # 检查模型是否存在
        predictor = _model_manager.get_predictor(request.predictor_name)
        if not predictor:
            raise HTTPException(status_code=404, detail=f"模型不存在: {request.predictor_name}")

        # 在后台训练（避免阻塞API）
        async def train_task():
            try:
                success = await predictor.train(
                    request.training_data,
                    labels=request.labels,
                    **(request.params or {})
                )
                if success:
                    logger.info(f"模型训练成功: {request.predictor_name}")
                else:
                    logger.error(f"模型训练失败: {request.predictor_name}")
            except Exception as e:
                logger.error(f"训练任务异常: {request.predictor_name}, 错误: {str(e)}")

        background_tasks.add_task(train_task)

        return APIResponse.success(
            message="训练任务已启动",
            data={
                "model_name": request.predictor_name,
                "training_samples": len(request.training_data),
                "background_task": True
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动训练任务失败: {str(e)}")
        return APIResponse.error(message=f"启动训练任务失败: {str(e)}")


@router.post("/predict", response_model=APIResponse)
async def predict(request: PredictRequest):
    """
    使用模型进行预测
    """
    try:
        predictor = _model_manager.get_predictor(request.predictor_name)
        if not predictor:
            raise HTTPException(status_code=404, detail=f"模型不存在: {request.predictor_name}")

        if not predictor.is_trained:
            raise HTTPException(status_code=400, detail=f"模型未训练: {request.predictor_name}")

        result = await predictor.predict(
            request.input_data,
            **(request.params or {})
        )

        if result:
            return APIResponse.success(
                data={
                    "prediction": result.to_dict(),
                    "model_name": request.predictor_name
                }
            )
        else:
            return APIResponse.error(message="预测失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        return APIResponse.error(message=f"预测失败: {str(e)}")


@router.post("/predict/batch", response_model=APIResponse)
async def predict_batch(request: Dict[str, Any] = Body(...)):
    """
    批量预测
    """
    try:
        predictor_name = request.get("predictor_name")
        input_data = request.get("input_data", [])
        params = request.get("params", {})

        if not predictor_name:
            raise HTTPException(status_code=400, detail="缺少 predictor_name 参数")

        predictor = _model_manager.get_predictor(predictor_name)
        if not predictor:
            raise HTTPException(status_code=404, detail=f"模型不存在: {predictor_name}")

        if not predictor.is_trained:
            raise HTTPException(status_code=400, detail=f"模型未训练: {predictor_name}")

        results = await predictor.predict_batch(input_data, **params)

        return APIResponse.success(
            data={
                "predictions": [r.to_dict() for r in results],
                "count": len(results),
                "model_name": predictor_name
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量预测失败: {str(e)}")
        return APIResponse.error(message=f"批量预测失败: {str(e)}")


@router.post("/ensemble", response_model=APIResponse)
async def ensemble_predict(request: EnsemblePredictRequest):
    """
    集成预测：使用多个同类型模型进行预测并组合结果
    """
    try:
        try:
            pred_type = PredictionType(request.prediction_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的预测类型: {request.prediction_type}")

        result = await _model_manager.ensemble_predict(
            pred_type,
            request.input_data,
            strategy=request.strategy,
            **(request.params or {})
        )

        if result:
            return APIResponse.success(
                data={
                    "prediction": result.to_dict(),
                    "strategy": request.strategy,
                    "prediction_type": request.prediction_type
                }
            )
        else:
            return APIResponse.error(message="集成预测失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"集成预测失败: {str(e)}")
        return APIResponse.error(message=f"集成预测失败: {str(e)}")


@router.post("/evaluate", response_model=APIResponse)
async def evaluate_model(request: EvaluateRequest):
    """
    评估模型性能
    """
    try:
        predictor = _model_manager.get_predictor(request.predictor_name)
        if not predictor:
            raise HTTPException(status_code=404, detail=f"模型不存在: {request.predictor_name}")

        if not predictor.is_trained:
            raise HTTPException(status_code=400, detail=f"模型未训练: {request.predictor_name}")

        metrics = await predictor.evaluate(
            request.test_data,
            test_labels=request.test_labels,
            **(request.params or {})
        )

        if metrics:
            return APIResponse.success(
                data={
                    "metrics": metrics.to_dict(),
                    "model_name": request.predictor_name
                }
            )
        else:
            return APIResponse.error(message="评估失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"评估模型失败: {str(e)}")
        return APIResponse.error(message=f"评估模型失败: {str(e)}")


@router.get("/stats", response_model=APIResponse)
async def get_all_stats():
    """
    获取所有模型的统计信息
    """
    try:
        stats = _model_manager.get_all_stats()
        return APIResponse.success(data={"models": stats})

    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return APIResponse.error(message=f"获取统计信息失败: {str(e)}")


@router.post("/models/{model_name}/retrain", response_model=APIResponse)
async def retrain_model(
    model_name: str,
    training_data: List[Dict[str, Any]] = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    重新训练模型
    """
    try:
        predictor = _model_manager.get_predictor(model_name)
        if not predictor:
            raise HTTPException(status_code=404, detail=f"模型不存在: {model_name}")

        async def retrain_task():
            try:
                success = await predictor.train(training_data)
                if success:
                    logger.info(f"模型重新训练成功: {model_name}")
                else:
                    logger.error(f"模型重新训练失败: {model_name}")
            except Exception as e:
                logger.error(f"重新训练任务异常: {model_name}, 错误: {str(e)}")

        background_tasks.add_task(retrain_task)

        return APIResponse.success(
            message="重新训练任务已启动",
            data={
                "model_name": model_name,
                "training_samples": len(training_data),
                "background_task": True
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动重新训练任务失败: {str(e)}")
        return APIResponse.error(message=f"启动重新训练任务失败: {str(e)}")


@router.get("/health", response_model=APIResponse)
async def prediction_health():
    """
    预测模块健康检查
    """
    try:
        predictors = _model_manager.get_all_predictors()
        enabled_predictors = _model_manager.get_enabled_predictors()
        trained_predictors = [p for p in predictors if p.is_trained]

        health_data = {
            "total_models": len(predictors),
            "enabled_models": len(enabled_predictors),
            "trained_models": len(trained_predictors),
            "manager_initialized": True,
            "timestamp": datetime.utcnow().isoformat()
        }

        return APIResponse.success(data=health_data)

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return APIResponse.error(message=f"健康检查失败: {str(e)}")