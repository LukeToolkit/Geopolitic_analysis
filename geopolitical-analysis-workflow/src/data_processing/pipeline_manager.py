"""
数据处理管道管理器
负责管理和协调数据处理管道
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import yaml
import os

from .base_processor import ProcessingPipeline, BaseProcessor, ProcessorConfig

logger = logging.getLogger(__name__)


class PipelineManager:
    """管道管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.pipelines: Dict[str, ProcessingPipeline] = {}
        self.processors: Dict[str, BaseProcessor] = {}
        self._config_path = config_path
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._running = False

    async def initialize(self) -> None:
        """初始化管理器"""
        logger.info("初始化数据处理管道管理器")

        # 加载配置
        if self._config_path and os.path.exists(self._config_path):
            await self._load_configs()
        else:
            logger.warning(f"配置文件不存在: {self._config_path}，使用默认配置")

        # 注册处理器和管道
        await self._register_processors()
        await self._create_pipelines()

        logger.info(f"数据处理管道管理器初始化完成，注册了 {len(self.processors)} 个处理器，"
                   f"创建了 {len(self.pipelines)} 个管道")

    async def _load_configs(self) -> None:
        """加载配置文件"""
        try:
            with open(self._config_path, 'r') as f:
                configs = yaml.safe_load(f)

            if configs:
                self._configs = configs
                logger.info(f"从配置文件加载了配置")
            else:
                logger.warning("配置文件为空或格式不正确")
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")

    async def _register_processors(self) -> None:
        """注册处理器"""
        # 这里应该动态导入和注册所有处理器
        # 暂时只创建示例处理器

        # 示例：文本清洗器
        text_cleaner_config = ProcessorConfig(
            name="text_cleaner",
            processor_type="cleaner",
            enabled=True,
            priority=1,
            params={
                "remove_html": True,
                "remove_urls": True,
                "remove_special_chars": True,
                "lowercase": True
            }
        )

        # 示例：时间序列特征提取器
        ts_feature_config = ProcessorConfig(
            name="time_series_feature_extractor",
            processor_type="feature_extractor",
            enabled=True,
            priority=3,
            params={
                "window_sizes": [7, 14, 30],
                "features": ["mean", "std", "min", "max", "trend"]
            }
        )

        # 示例：数据验证器
        validator_config = ProcessorConfig(
            name="data_validator",
            processor_type="validator",
            enabled=True,
            priority=4,
            params={
                "required_fields": ["timestamp", "value", "source"],
                "value_range": {"min": 0, "max": 1000000}
            }
        )

        # 从配置文件更新配置
        if "text_cleaner" in self._configs.get("processors", {}):
            text_cleaner_config = self._update_config_from_dict(
                text_cleaner_config, self._configs["processors"]["text_cleaner"]
            )

        if "time_series_feature_extractor" in self._configs.get("processors", {}):
            ts_feature_config = self._update_config_from_dict(
                ts_feature_config, self._configs["processors"]["time_series_feature_extractor"]
            )

        # 创建处理器（需要具体实现）
        # text_cleaner = TextCleaner(text_cleaner_config)
        # ts_feature_extractor = TimeSeriesFeatureExtractor(ts_feature_config)
        # data_validator = DataValidator(validator_config)

        # self.register_processor(text_cleaner)
        # self.register_processor(ts_feature_extractor)
        # self.register_processor(data_validator)

    def _update_config_from_dict(self, config: ProcessorConfig, config_dict: Dict[str, Any]) -> ProcessorConfig:
        """从字典更新配置"""
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
            elif key == "params" and isinstance(value, dict):
                config.params.update(value)
        return config

    async def _create_pipelines(self) -> None:
        """创建处理管道"""
        # 创建新闻数据处理管道
        news_pipeline = ProcessingPipeline(
            name="news_processing",
            description="新闻数据处理管道"
        )

        # 添加处理器到管道
        # if "text_cleaner" in self.processors:
        #     news_pipeline.add_processor(self.processors["text_cleaner"])
        # if "data_validator" in self.processors:
        #     news_pipeline.add_processor(self.processors["data_validator"])

        self.register_pipeline(news_pipeline)

        # 创建金融数据处理管道
        financial_pipeline = ProcessingPipeline(
            name="financial_processing",
            description="金融数据处理管道"
        )

        # if "time_series_feature_extractor" in self.processors:
        #     financial_pipeline.add_processor(self.processors["time_series_feature_extractor"])
        # if "data_validator" in self.processors:
        #     financial_pipeline.add_processor(self.processors["data_validator"])

        self.register_pipeline(financial_pipeline)

    def register_processor(self, processor: BaseProcessor) -> None:
        """注册处理器"""
        name = processor.name

        if name in self.processors:
            logger.warning(f"处理器 '{name}' 已存在，将被替换")

        self.processors[name] = processor
        logger.info(f"注册处理器: {name} ({processor.processor_type})")

    def unregister_processor(self, name: str) -> None:
        """注销处理器"""
        if name in self.processors:
            del self.processors[name]
            logger.info(f"注销处理器: {name}")

    def register_pipeline(self, pipeline: ProcessingPipeline) -> None:
        """注册管道"""
        name = pipeline.name

        if name in self.pipelines:
            logger.warning(f"管道 '{name}' 已存在，将被替换")

        self.pipelines[name] = pipeline
        logger.info(f"注册管道: {name}")

    def unregister_pipeline(self, name: str) -> None:
        """注销管道"""
        if name in self.pipelines:
            del self.pipelines[name]
            logger.info(f"注销管道: {name}")

    def get_pipeline(self, name: str) -> Optional[ProcessingPipeline]:
        """获取管道"""
        return self.pipelines.get(name)

    def get_processor(self, name: str) -> Optional[BaseProcessor]:
        """获取处理器"""
        return self.processors.get(name)

    async def process_with_pipeline(self, pipeline_name: str, data: Any,
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用指定管道处理数据"""
        pipeline = self.get_pipeline(pipeline_name)

        if not pipeline:
            raise ValueError(f"管道 '{pipeline_name}' 不存在")

        try:
            logger.info(f"开始使用管道处理数据: {pipeline_name}")
            result = await pipeline.execute(data, context)

            return {
                "pipeline": pipeline_name,
                "success": len(result.errors) == 0,
                "data": result.data,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata,
                "processing_time": result.processing_time
            }

        except Exception as e:
            logger.error(f"管道处理失败: {pipeline_name}, 错误: {str(e)}")
            raise

    async def process_batch(self, pipeline_name: str, data_list: List[Any],
                           context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """批量处理数据"""
        results = []

        for i, data in enumerate(data_list):
            try:
                logger.debug(f"批量处理 [{i+1}/{len(data_list)}]")
                result = await self.process_with_pipeline(pipeline_name, data, context)
                results.append(result)
            except Exception as e:
                logger.error(f"批量处理失败 [{i+1}/{len(data_list)}]: {str(e)}")
                results.append({
                    "pipeline": pipeline_name,
                    "success": False,
                    "data": data,
                    "errors": [f"处理失败: {str(e)}"],
                    "warnings": [],
                    "metadata": {},
                    "processing_time": 0
                })

        return results

    def get_pipeline_stats(self, pipeline_name: Optional[str] = None) -> Dict[str, Any]:
        """获取管道统计信息"""
        if pipeline_name:
            pipeline = self.get_pipeline(pipeline_name)
            if not pipeline:
                return {"error": f"管道 '{pipeline_name}' 不存在"}
            return pipeline.get_stats()
        else:
            stats = {}
            for name, pipeline in self.pipelines.items():
                stats[name] = pipeline.get_stats()
            return stats

    def get_processor_stats(self, processor_name: Optional[str] = None) -> Dict[str, Any]:
        """获取处理器统计信息"""
        if processor_name:
            processor = self.get_processor(processor_name)
            if not processor:
                return {"error": f"处理器 '{processor_name}' 不存在"}
            return processor.get_stats()
        else:
            stats = {}
            for name, processor in self.processors.items():
                stats[name] = processor.get_stats()
            return stats

    async def test_all_processors(self) -> Dict[str, bool]:
        """测试所有处理器"""
        results = {}

        for name, processor in self.processors.items():
            try:
                # 创建测试数据
                test_data = {"test": "data", "timestamp": "2024-01-01T00:00:00Z"}

                # 测试处理器
                result = await processor.process_with_metrics(test_data)
                success = len(result.errors) == 0

                results[name] = success
                logger.info(f"处理器测试 {name}: {'成功' if success else '失败'}")

            except Exception as e:
                logger.error(f"处理器测试失败 {name}: {str(e)}")
                results[name] = False

        return results


# 单例实例
_manager: Optional[PipelineManager] = None


async def get_manager(config_path: Optional[str] = None) -> PipelineManager:
    """获取管道管理器实例（单例）"""
    global _manager

    if _manager is None:
        _manager = PipelineManager(config_path)
        await _manager.initialize()

    return _manager


async def process_data(pipeline_name: str, data: Any,
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """处理数据（便捷函数）"""
    manager = await get_manager()
    return await manager.process_with_pipeline(pipeline_name, data, context)


async def process_batch_data(pipeline_name: str, data_list: List[Any],
                            context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """批量处理数据（便捷函数）"""
    manager = await get_manager()
    return await manager.process_batch(pipeline_name, data_list, context)