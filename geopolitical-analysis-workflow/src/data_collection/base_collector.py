"""
数据收集器基础类
实现插件化数据收集器架构，所有具体收集器必须继承此类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型枚举"""
    NEWS = "news"
    FINANCIAL = "financial"
    SOCIAL_MEDIA = "social_media"
    ADS_B = "ads_b"  # 航空数据
    AIS = "ais"  # 船舶数据
    MILITARY = "military"
    OSINT = "osint"
    WEATHER = "weather"
    SATELLITE = "satellite"
    OTHER = "other"


class DataFormat(Enum):
    """数据格式枚举"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    TEXT = "text"
    BINARY = "binary"
    HTML = "html"


@dataclass
class DataRecord:
    """数据记录基类"""
    id: str
    source_type: DataSourceType
    raw_data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processed: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "raw_data": self.raw_data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "errors": self.errors
        }


@dataclass
class CollectorConfig:
    """收集器配置"""
    name: str
    source_type: DataSourceType
    enabled: bool = True
    interval_seconds: int = 3600  # 默认1小时
    batch_size: int = 100
    timeout_seconds: int = 300
    retry_attempts: int = 3
    retry_delay_seconds: int = 60
    priority: int = 1  # 1-10，越高优先级越高
    params: Dict[str, Any] = field(default_factory=dict)


class DataCollector(ABC):
    """数据收集器抽象基类"""

    def __init__(self, config: CollectorConfig):
        self.config = config
        self._is_running = False
        self._last_collection_time: Optional[datetime] = None
        self._total_collected = 0
        self._total_errors = 0
        self.logger = logging.getLogger(f"{__name__}.{self.config.name}")

    @property
    def name(self) -> str:
        """收集器名称"""
        return self.config.name

    @property
    def source_type(self) -> DataSourceType:
        """数据源类型"""
        return self.config.source_type

    @property
    def is_due(self) -> bool:
        """是否到了收集时间"""
        if not self._last_collection_time:
            return True
        next_time = self._last_collection_time + timedelta(seconds=self.config.interval_seconds)
        return datetime.utcnow() >= next_time

    @abstractmethod
    async def collect(self) -> List[DataRecord]:
        """
        收集数据
        返回: 数据记录列表
        """
        pass

    @abstractmethod
    def validate(self, record: DataRecord) -> bool:
        """
        验证数据记录的有效性
        返回: 是否有效
        """
        pass

    async def collect_with_retry(self) -> List[DataRecord]:
        """带重试的数据收集"""
        attempts = 0
        last_error = None

        while attempts < self.config.retry_attempts:
            try:
                self.logger.info(f"开始收集数据 (尝试 {attempts + 1}/{self.config.retry_attempts})")
                records = await self.collect()
                self._last_collection_time = datetime.utcnow()
                self._total_collected += len(records)

                # 验证数据
                valid_records = []
                for record in records:
                    if self.validate(record):
                        valid_records.append(record)
                    else:
                        self.logger.warning(f"数据验证失败: {record.id}")
                        self._total_errors += 1

                self.logger.info(f"数据收集完成: {len(valid_records)} 条有效记录")
                return valid_records

            except Exception as e:
                attempts += 1
                last_error = e
                self.logger.error(f"数据收集失败 (尝试 {attempts}/{self.config.retry_attempts}): {str(e)}")

                if attempts < self.config.retry_attempts:
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    self.logger.error(f"数据收集最终失败: {str(e)}")
                    self._total_errors += 1

        # 所有重试都失败
        error_record = DataRecord(
            id=f"error_{datetime.utcnow().timestamp()}",
            source_type=self.source_type,
            raw_data={"error": str(last_error)},
            metadata={"collector": self.name, "attempts": attempts},
            errors=[str(last_error)]
        )
        return [error_record]

    async def collect_stream(self) -> AsyncGenerator[DataRecord, None]:
        """流式收集数据（适用于大量数据）"""
        try:
            self.logger.info("开始流式数据收集")
            batch = []

            # 具体收集器需要实现_iter_collect方法
            async for record in self._iter_collect():
                if self.validate(record):
                    batch.append(record)

                    if len(batch) >= self.config.batch_size:
                        for record in batch:
                            yield record
                        batch = []
                else:
                    self.logger.warning(f"数据验证失败: {record.id}")
                    self._total_errors += 1

            # 返回剩余的记录
            if batch:
                for record in batch:
                    yield record

            self._last_collection_time = datetime.utcnow()
            self._total_collected += sum(1 for _ in batch)
            self.logger.info("流式数据收集完成")

        except Exception as e:
            self.logger.error(f"流式数据收集失败: {str(e)}")
            self._total_errors += 1

    async def _iter_collect(self) -> AsyncGenerator[DataRecord, None]:
        """迭代收集数据（需要子类实现）"""
        # 默认实现：调用collect方法并迭代返回的列表
        records = await self.collect()
        for record in records:
            yield record

    def get_stats(self) -> Dict[str, Any]:
        """获取收集器统计信息"""
        return {
            "name": self.name,
            "source_type": self.source_type.value,
            "enabled": self.config.enabled,
            "last_collection_time": self._last_collection_time.isoformat() if self._last_collection_time else None,
            "total_collected": self._total_collected,
            "total_errors": self._total_errors,
            "interval_seconds": self.config.interval_seconds,
            "is_due": self.is_due,
            "next_collection_in": self._get_next_collection_in()
        }

    def _get_next_collection_in(self) -> Optional[int]:
        """距离下一次收集还有多少秒"""
        if not self._last_collection_time:
            return 0
        next_time = self._last_collection_time + timedelta(seconds=self.config.interval_seconds)
        now = datetime.utcnow()
        if now >= next_time:
            return 0
        return int((next_time - now).total_seconds())

    async def test_connection(self) -> bool:
        """测试数据源连接"""
        try:
            self.logger.info(f"测试 {self.name} 连接...")
            # 具体收集器需要实现_test_connection方法
            result = await self._test_connection()
            self.logger.info(f"连接测试 {'成功' if result else '失败'}")
            return result
        except Exception as e:
            self.logger.error(f"连接测试失败: {str(e)}")
            return False

    async def _test_connection(self) -> bool:
        """测试连接的具体实现（需要子类实现）"""
        # 默认实现：尝试收集一条数据
        try:
            records = await self.collect()
            return len(records) > 0
        except:
            return False


class CollectorRegistry:
    """收集器注册表"""

    def __init__(self):
        self._collectors: Dict[str, DataCollector] = {}
        self._by_type: Dict[DataSourceType, List[DataCollector]] = {}
        self.logger = logging.getLogger(__name__)

    def register(self, collector: DataCollector) -> None:
        """注册收集器"""
        name = collector.name
        source_type = collector.source_type

        if name in self._collectors:
            self.logger.warning(f"收集器 '{name}' 已存在，将被替换")

        self._collectors[name] = collector

        if source_type not in self._by_type:
            self._by_type[source_type] = []

        if collector not in self._by_type[source_type]:
            self._by_type[source_type].append(collector)

        self.logger.info(f"注册收集器: {name} ({source_type.value})")

    def unregister(self, name: str) -> None:
        """注销收集器"""
        if name in self._collectors:
            collector = self._collectors.pop(name)
            source_type = collector.source_type

            if source_type in self._by_type:
                self._by_type[source_type] = [c for c in self._by_type[source_type] if c.name != name]
                if not self._by_type[source_type]:
                    del self._by_type[source_type]

            self.logger.info(f"注销收集器: {name}")

    def get_collector(self, name: str) -> Optional[DataCollector]:
        """获取收集器"""
        return self._collectors.get(name)

    def get_collectors_by_type(self, source_type: DataSourceType) -> List[DataCollector]:
        """按类型获取收集器"""
        return self._by_type.get(source_type, [])

    def get_all_collectors(self) -> List[DataCollector]:
        """获取所有收集器"""
        return list(self._collectors.values())

    def get_enabled_collectors(self) -> List[DataCollector]:
        """获取启用的收集器"""
        return [c for c in self._collectors.values() if c.config.enabled]

    async def collect_all(self) -> Dict[str, List[DataRecord]]:
        """收集所有启用的收集器的数据"""
        results = {}

        for collector in self.get_enabled_collectors():
            try:
                if collector.is_due:
                    self.logger.info(f"开始收集: {collector.name}")
                    records = await collector.collect_with_retry()
                    results[collector.name] = records
                else:
                    self.logger.debug(f"跳过收集: {collector.name} (未到时间)")
            except Exception as e:
                self.logger.error(f"收集器 {collector.name} 失败: {str(e)}")
                results[collector.name] = []

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取所有收集器的统计信息"""
        stats = {}
        for name, collector in self._collectors.items():
            stats[name] = collector.get_stats()
        return stats