"""
预测模块使用示例
展示如何使用时间序列和机器学习预测器
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prediction import (
    PredictorConfig, PredictionType, ModelType, ModelManager,
    TimeSeriesPredictor, MLPredictor
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_time_series_data():
    """创建示例时间序列数据"""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(100)]
    # 正弦波 + 趋势 + 噪声
    values = np.sin(np.linspace(0, 4 * np.pi, 100)) * 10 + np.linspace(20, 40, 100) + np.random.normal(0, 2, 100)

    df = pd.DataFrame({
        'date': dates,
        'value': values,
        'temperature': np.random.uniform(15, 30, 100),
        'humidity': np.random.uniform(40, 80, 100)
    })

    return df


def create_classification_data():
    """创建示例分类数据"""
    n_samples = 200
    # 创建两个特征和二进制目标
    np.random.seed(42)
    X = np.random.randn(n_samples, 4)
    # 基于特征线性组合的目标
    y = (X[:, 0] * 1.5 + X[:, 1] * 2.0 - X[:, 2] * 0.5 > 0).astype(int)

    df = pd.DataFrame(X, columns=['feature1', 'feature2', 'feature3', 'feature4'])
    df['target'] = y

    return df, y


def create_regression_data():
    """创建示例回归数据"""
    n_samples = 200
    np.random.seed(42)
    X = np.random.randn(n_samples, 4)
    # 线性关系加噪声
    y = X[:, 0] * 3.0 + X[:, 1] * 1.5 - X[:, 2] * 2.0 + X[:, 3] * 0.5 + np.random.normal(0, 1, n_samples)

    df = pd.DataFrame(X, columns=['feature1', 'feature2', 'feature3', 'feature4'])
    df['target'] = y

    return df, y


async def time_series_example():
    """时间序列预测示例"""
    print("=" * 60)
    print("时间序列预测示例")
    print("=" * 60)

    # 创建模型管理器
    manager = ModelManager()

    # 创建时间序列预测器配置
    ts_config = PredictorConfig(
        name="stock_price_predictor",
        prediction_type=PredictionType.TIME_SERIES,
        model_type=ModelType.STATISTICAL,
        prediction_horizon=7,  # 预测未来7天
        retrain_interval_hours=24,
        params={
            "model": "prophet",  # 使用Prophet模型
            "target_column": "value",
            "date_column": "date",
            "model_params": {
                "seasonality_mode": "multiplicative",
                "seasonality_prior_scale": 10,
                "changepoint_prior_scale": 0.05
            }
        }
    )

    # 创建时间序列预测器
    try:
        ts_predictor = TimeSeriesPredictor(ts_config)
        manager.register_predictor(ts_predictor)
        print(f"✓ 时间序列预测器注册成功: {ts_predictor.name}")
    except ImportError as e:
        print(f"✗ 时间序列预测器不可用: {e}")
        print("请安装: pip install prophet statsmodels")
        return

    # 创建训练数据
    train_df = create_time_series_data()

    # 训练模型
    print("训练时间序列模型...")
    success = await ts_predictor.train(train_df)
    if success:
        print("✓ 时间序列模型训练成功")
    else:
        print("✗ 时间序列模型训练失败")
        return

    # 进行预测
    print("进行时间序列预测...")
    try:
        # 使用最后一条数据作为输入
        last_row = train_df.iloc[-1].to_dict()
        result = await ts_predictor.predict(last_row, horizon=14, freq='D')

        print(f"✓ 预测完成")
        print(f"   预测值: {result.predicted_value:.2f}")
        print(f"   置信度: {result.confidence_score:.2%}")
        print(f"   预测区间: {result.prediction_interval}")
        print(f"   特征: {result.features_used}")
    except Exception as e:
        print(f"✗ 预测失败: {e}")

    # 获取模型信息
    print("\n模型信息:")
    model_info = ts_predictor.get_model_info()
    print(f"   名称: {model_info['name']}")
    print(f"   类型: {model_info['prediction_type']}/{model_info['model_type']}")
    print(f"   已训练: {model_info['is_trained']}")
    print(f"   总预测次数: {model_info['total_predictions']}")

    return ts_predictor


async def ml_classification_example():
    """机器学习分类示例"""
    print("\n" + "=" * 60)
    print("机器学习分类示例")
    print("=" * 60)

    # 创建模型管理器
    manager = ModelManager()

    # 创建分类预测器配置
    clf_config = PredictorConfig(
        name="risk_classifier",
        prediction_type=PredictionType.CLASSIFICATION,
        model_type=ModelType.MACHINE_LEARNING,
        confidence_threshold=0.7,
        params={
            "model": "random_forest_classifier",
            "target_column": "target",
            "model_params": {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }
        }
    )

    # 创建分类预测器
    try:
        clf_predictor = MLPredictor(clf_config)
        manager.register_predictor(clf_predictor)
        print(f"✓ 分类预测器注册成功: {clf_predictor.name}")
    except ImportError as e:
        print(f"✗ 机器学习预测器不可用: {e}")
        print("请安装: pip install scikit-learn lightgbm xgboost")
        return

    # 创建训练数据
    train_df, train_labels = create_classification_data()

    # 训练模型
    print("训练分类模型...")
    success = await clf_predictor.train(train_df, labels=train_labels)
    if success:
        print("✓ 分类模型训练成功")
    else:
        print("✗ 分类模型训练失败")
        return

    # 进行预测
    print("进行分类预测...")
    try:
        # 创建测试数据
        test_features = {
            'feature1': 1.2,
            'feature2': -0.5,
            'feature3': 0.8,
            'feature4': -1.1
        }

        result = await clf_predictor.predict(test_features)

        print(f"✓ 预测完成")
        print(f"   预测类别: {result.predicted_value}")
        print(f"   置信度: {result.confidence_score:.2%}")
        print(f"   特征: {result.features_used}")
    except Exception as e:
        print(f"✗ 预测失败: {e}")

    # 评估模型
    print("评估模型性能...")
    try:
        test_df, test_labels = create_classification_data()
        metrics = await clf_predictor.evaluate(test_df, test_labels=test_labels)

        print(f"✓ 评估完成")
        print(f"   准确率: {metrics.accuracy:.2%}" if metrics.accuracy else "   准确率: N/A")
        print(f"   F1分数: {metrics.f1_score:.3f}" if metrics.f1_score else "   F1分数: N/A")
        print(f"   AUC: {metrics.auc:.3f}" if metrics.auc else "   AUC: N/A")
    except Exception as e:
        print(f"✗ 评估失败: {e}")

    return clf_predictor


async def ml_regression_example():
    """机器学习回归示例"""
    print("\n" + "=" * 60)
    print("机器学习回归示例")
    print("=" * 60)

    # 创建模型管理器
    manager = ModelManager()

    # 创建回归预测器配置
    reg_config = PredictorConfig(
        name="market_regressor",
        prediction_type=PredictionType.REGRESSION,
        model_type=ModelType.MACHINE_LEARNING,
        confidence_threshold=0.6,
        params={
            "model": "random_forest_regressor",
            "target_column": "target",
            "model_params": {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }
        }
    )

    # 创建回归预测器
    try:
        reg_predictor = MLPredictor(reg_config)
        manager.register_predictor(reg_predictor)
        print(f"✓ 回归预测器注册成功: {reg_predictor.name}")
    except ImportError as e:
        print(f"✗ 机器学习预测器不可用: {e}")
        return

    # 创建训练数据
    train_df, train_labels = create_regression_data()

    # 训练模型
    print("训练回归模型...")
    success = await reg_predictor.train(train_df, labels=train_labels)
    if success:
        print("✓ 回归模型训练成功")
    else:
        print("✗ 回归模型训练失败")
        return

    # 进行预测
    print("进行回归预测...")
    try:
        # 创建测试数据
        test_features = {
            'feature1': 0.5,
            'feature2': -0.8,
            'feature3': 1.2,
            'feature4': -0.3
        }

        result = await reg_predictor.predict(test_features)

        print(f"✓ 预测完成")
        print(f"   预测值: {result.predicted_value:.4f}")
        print(f"   置信度: {result.confidence_score:.2%}")
        print(f"   特征: {result.features_used}")
    except Exception as e:
        print(f"✗ 预测失败: {e}")

    # 评估模型
    print("评估模型性能...")
    try:
        test_df, test_labels = create_regression_data()
        metrics = await reg_predictor.evaluate(test_df, test_labels=test_labels)

        print(f"✓ 评估完成")
        print(f"   MAE: {metrics.mae:.4f}" if metrics.mae else "   MAE: N/A")
        print(f"   RMSE: {metrics.rmse:.4f}" if metrics.rmse else "   RMSE: N/A")
        print(f"   R²分数: {metrics.r2_score:.4f}" if metrics.r2_score else "   R²分数: N/A")
    except Exception as e:
        print(f"✗ 评估失败: {e}")

    return reg_predictor


async def model_manager_example():
    """模型管理器示例"""
    print("\n" + "=" * 60)
    print("模型管理器示例")
    print("=" * 60)

    # 创建模型管理器
    manager = ModelManager()

    # 创建多个预测器
    predictors = []

    # 时间序列预测器
    ts_config = PredictorConfig(
        name="ts_forecaster",
        prediction_type=PredictionType.TIME_SERIES,
        model_type=ModelType.STATISTICAL,
        params={"model": "prophet", "target_column": "value", "date_column": "date"}
    )

    # 分类预测器
    clf_config = PredictorConfig(
        name="risk_classifier",
        prediction_type=PredictionType.CLASSIFICATION,
        model_type=ModelType.MACHINE_LEARNING,
        params={"model": "random_forest_classifier", "target_column": "target"}
    )

    # 回归预测器
    reg_config = PredictorConfig(
        name="price_regressor",
        prediction_type=PredictionType.REGRESSION,
        model_type=ModelType.MACHINE_LEARNING,
        params={"model": "random_forest_regressor", "target_column": "target"}
    )

    try:
        # 注册预测器（跳过训练）
        from src.prediction import TimeSeriesPredictor, MLPredictor

        ts_predictor = TimeSeriesPredictor(ts_config)
        manager.register_predictor(ts_predictor)
        predictors.append(ts_predictor)

        clf_predictor = MLPredictor(clf_config)
        manager.register_predictor(clf_predictor)
        predictors.append(clf_predictor)

        reg_predictor = MLPredictor(reg_config)
        manager.register_predictor(reg_predictor)
        predictors.append(reg_predictor)

        print(f"✓ 注册了 {len(predictors)} 个预测器")

        # 获取所有预测器
        all_predictors = manager.get_all_predictors()
        print(f"✓ 模型管理器中有 {len(all_predictors)} 个预测器")

        # 按类型获取预测器
        ts_predictors = manager.get_predictors_by_type(PredictionType.TIME_SERIES)
        print(f"✓ 时间序列预测器: {len(ts_predictors)} 个")

        ml_predictors = manager.get_predictors_by_type(PredictionType.CLASSIFICATION)
        ml_predictors += manager.get_predictors_by_type(PredictionType.REGRESSION)
        print(f"✓ 机器学习预测器: {len(ml_predictors)} 个")

        # 获取统计信息
        stats = manager.get_all_stats()
        print(f"✓ 获取了 {len(stats)} 个预测器的统计信息")

        for name, stat in stats.items():
            print(f"  - {name}: 类型={stat['prediction_type']}, 已训练={stat['is_trained']}")

    except ImportError as e:
        print(f"✗ 示例需要完整的依赖: {e}")
        print("请安装: pip install prophet scikit-learn")


async def main():
    """主函数"""
    print("地缘政治分析AI工作流 - 预测模块示例")
    print("=" * 60)

    try:
        # 运行时间序列示例
        await time_series_example()

        # 运行分类示例
        await ml_classification_example()

        # 运行回归示例
        await ml_regression_example()

        # 运行模型管理器示例
        await model_manager_example()

    except Exception as e:
        print(f"\n✗ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())