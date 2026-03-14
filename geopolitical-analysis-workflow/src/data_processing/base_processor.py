"""
数据处理基础类
定义数据处理组件的抽象接口和基础实现
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """数据处理错误"""
    pass


@dataclass
class ProcessingResult:
    """处理结果"""
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "metadata": self.metadata,
            "errors": self.errors,
            "warnings": self.warnings,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ProcessorConfig:
    """处理器配置"""
    name: str
    processor_type: str
    enabled: bool = True
    priority: int = 1  # 处理优先级，越小越先执行
    params: Dict[str, Any] = field(default_factory=dict)


class BaseProcessor(ABC):
    """处理器抽象基类"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self._total_processed = 0
        self._total_errors = 0
        self._total_warnings = 0
        self.logger = logging.getLogger(f"{__name__}.{self.config.name}")

    @property
    def name(self) -> str:
        """处理器名称"""
        return self.config.name

    @property
    def processor_type(self) -> str:
        """处理器类型"""
        return self.config.processor_type

    @abstractmethod
    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        处理数据
        Args:
            data: 输入数据
            context: 处理上下文信息
        Returns:
            ProcessingResult: 处理结果
        """
        pass

    async def process_with_metrics(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """带指标统计的处理"""
        import time
        start_time = time.time()

        try:
            self.logger.debug(f"开始处理数据: {self.name}")
            result = await self.process(data, context)

            # 更新指标
            processing_time = time.time() - start_time
            result.processing_time = processing_time

            self._total_processed += 1

            if result.errors:
                self._total_errors += len(result.errors)
                self.logger.warning(f"处理完成但有错误: {self.name}, 错误数: {len(result.errors)}")

            if result.warnings:
                self._total_warnings += len(result.warnings)
                self.logger.info(f"处理完成但有警告: {self.name}, 警告数: {len(result.warnings)}")

            self.logger.debug(f"处理完成: {self.name}, 耗时: {processing_time:.3f}s")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self._total_errors += 1
            self.logger.error(f"处理失败: {self.name}, 错误: {str(e)}", exc_info=True)

            return ProcessingResult(
                data=data,
                errors=[f"{self.name} 处理失败: {str(e)}"],
                processing_time=processing_time
            )

    def validate_input(self, data: Any) -> bool:
        """验证输入数据"""
        if data is None:
            return False
        return True

    def validate_output(self, result: Any) -> bool:
        """验证输出数据"""
        if result is None:
            return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取处理器统计信息"""
        return {
            "name": self.name,
            "type": self.processor_type,
            "enabled": self.config.enabled,
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "total_warnings": self._total_warnings,
            "error_rate": self._total_errors / max(self._total_processed, 1)
        }


class DataCleaner(BaseProcessor):
    """数据清洗器基类"""

    def __init__(self, config: ProcessorConfig):
        super().__init__(config)
        self.config.processor_type = "cleaner"

    @abstractmethod
    async def clean(self, data: Any) -> Any:
        """清洗数据"""
        pass

    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """处理数据（清洗）"""
        try:
            if not self.validate_input(data):
                return ProcessingResult(
                    data=data,
                    errors=["输入数据无效"],
                    warnings=["跳过清洗"]
                )

            cleaned_data = await self.clean(data)

            if not self.validate_output(cleaned_data):
                return ProcessingResult(
                    data=data,
                    errors=["清洗后数据无效"],
                    warnings=["清洗失败"]
                )

            return ProcessingResult(
                data=cleaned_data,
                metadata={"cleaning_method": self.name}
            )

        except Exception as e:
            raise ProcessingError(f"数据清洗失败: {str(e)}")


class DataTransformer(BaseProcessor):
    """数据转换器基类"""

    def __init__(self, config: ProcessorConfig):
        super().__init__(config)
        self.config.processor_type = "transformer"

    @abstractmethod
    async def transform(self, data: Any) -> Any:
        """转换数据"""
        pass

    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """处理数据（转换）"""
        try:
            if not self.validate_input(data):
                return ProcessingResult(
                    data=data,
                    errors=["输入数据无效"],
                    warnings=["跳过转换"]
                )

            transformed_data = await self.transform(data)

            if not self.validate_output(transformed_data):
                return ProcessingResult(
                    data=data,
                    errors=["转换后数据无效"],
                    warnings=["转换失败"]
                )

            return ProcessingResult(
                data=transformed_data,
                metadata={"transformation_method": self.name}
            )

        except Exception as e:
            raise ProcessingError(f"数据转换失败: {str(e)}")


class FeatureExtractor(BaseProcessor):
    """特征提取器基类"""

    def __init__(self, config: ProcessorConfig):
        super().__init__(config)
        self.config.processor_type = "feature_extractor"

    @abstractmethod
    async def extract(self, data: Any) -> Dict[str, Any]:
        """提取特征"""
        pass

    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """处理数据（特征提取）"""
        try:
            if not self.validate_input(data):
                return ProcessingResult(
                    data=data,
                    errors=["输入数据无效"],
                    warnings=["跳过特征提取"]
                )

            features = await self.extract(data)

            if not features or not isinstance(features, dict):
                return ProcessingResult(
                    data=data,
                    errors=["特征提取结果无效"],
                    warnings=["特征提取失败"]
                )

            return ProcessingResult(
                data=features,
                metadata={
                    "feature_extractor": self.name,
                    "feature_count": len(features),
                    "feature_names": list(features.keys())
                }
            )

        except Exception as e:
            raise ProcessingError(f"特征提取失败: {str(e)}")


class DataValidator(BaseProcessor):
    """数据验证器基类"""

    def __init__(self, config: ProcessorConfig):
        super().__init__(config)
        self.config.processor_type = "validator"

    @abstractmethod
    async def validate(self, data: Any) -> Dict[str, Any]:
        """验证数据"""
        pass

    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """处理数据（验证）"""
        try:
            validation_result = await self.validate(data)

            errors = validation_result.get("errors", [])
            warnings = validation_result.get("warnings", [])
            metadata = validation_result.get("metadata", {})

            if errors:
                self.logger.warning(f"数据验证失败: {len(errors)} 个错误")

            return ProcessingResult(
                data=data,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )

        except Exception as e:
            raise ProcessingError(f"数据验证失败: {str(e)}")


class ProcessingPipeline:
    """处理管道"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.processors: List[BaseProcessor] = []
        self.logger = logging.getLogger(f"{__name__}.pipeline.{name}")

    def add_processor(self, processor: BaseProcessor) -> None:
        """添加处理器到管道"""
        self.processors.append(processor)
        self.logger.info(f"添加处理器: {processor.name} 到管道 {self.name}")

    def remove_processor(self, processor_name: str) -> None:
        """从管道移除处理器"""
        self.processors = [p for p in self.processors if p.name != processor_name]
        self.logger.info(f"从管道 {self.name} 移除处理器: {processor_name}")

    def get_processor(self, processor_name: str) -> Optional[BaseProcessor]:
        """获取处理器"""
        for processor in self.processors:
            if processor.name == processor_name:
                return processor
        return None

    async def execute(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """执行管道"""
        self.logger.info(f"开始执行管道: {self.name}")

        current_data = data
        pipeline_errors = []
        pipeline_warnings = []
        pipeline_metadata = {
            "pipeline_name": self.name,
            "processor_count": len(self.processors),
            "processors": []
        }

        total_processing_time = 0.0

        # 按优先级排序处理器
        sorted_processors = sorted(self.processors, key=lambda p: p.config.priority)

        for i, processor in enumerate(sorted_processors):
            if not processor.config.enabled:
                self.logger.debug(f"跳过禁用的处理器: {processor.name}")
                continue

            try:
                self.logger.debug(f"执行处理器 [{i+1}/{len(sorted_processors)}]: {processor.name}")

                # 执行处理器
                result = await processor.process_with_metrics(current_data, context)

                # 更新当前数据
                current_data = result.data

                # 收集结果
                pipeline_errors.extend(result.errors)
                pipeline_warnings.extend(result.warnings)

                # 更新元数据
                processor_metadata = {
                    "name": processor.name,
                    "type": processor.processor_type,
                    "processing_time": result.processing_time,
                    "metadata": result.metadata
                }
                pipeline_metadata["processors"].append(processor_metadata)

                total_processing_time += result.processing_time

                # 如果有严重错误，停止管道执行
                if result.errors and self._should_stop_on_errors(result.errors):
                    self.logger.error(f"管道因错误停止: {processor.name}")
                    break

            except Exception as e:
                error_msg = f"处理器 {processor.name} 执行失败: {str(e)}"
                pipeline_errors.append(error_msg)
                self.logger.error(error_msg, exc_info=True)
                break

        pipeline_metadata["total_processing_time"] = total_processing_time
        pipeline_metadata["success"] = len(pipeline_errors) == 0

        self.logger.info(f"管道执行完成: {self.name}, 耗时: {total_processing_time:.3f}s, "
                        f"错误: {len(pipeline_errors)}, 警告: {len(pipeline_warnings)}")

        return ProcessingResult(
            data=current_data,
            errors=pipeline_errors,
            warnings=pipeline_warnings,
            metadata=pipeline_metadata,
            processing_time=total_processing_time
        )

    def _should_stop_on_errors(self, errors: List[str]) -> bool:
        """判断是否因错误停止管道"""
        # 这里可以根据错误类型决定是否停止
        # 例如，致命错误停止，警告继续
        return True  # 默认任何错误都停止

    def get_stats(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        stats = {
            "name": self.name,
            "description": self.description,
            "processor_count": len(self.processors),
            "enabled_processors": [p.name for p in self.processors if p.config.enabled],
            "disabled_processors": [p.name for p in self.processors if not p.config.enabled],
            "processors": []
        }

        for processor in self.processors:
            stats["processors"].append(processor.get_stats())

        return stats