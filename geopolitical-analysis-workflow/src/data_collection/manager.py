"""
数据收集管理器
负责协调和管理所有数据收集器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import yaml
import os

from .base_collector import DataCollector, CollectorConfig, DataSourceType, CollectorRegistry

logger = logging.getLogger(__name__)


class DataCollectionManager:
    """数据收集管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.registry = CollectorRegistry()
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._config_path = config_path
        self._configs: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """初始化管理器"""
        logger.info("初始化数据收集管理器")

        # 加载配置
        if self._config_path and os.path.exists(self._config_path):
            await self._load_configs()
        else:
            logger.warning(f"配置文件不存在: {self._config_path}，使用默认配置")

        # 注册收集器
        await self._register_collectors()

        logger.info(f"数据收集管理器初始化完成，注册了 {len(self.registry.get_all_collectors())} 个收集器")

    async def _load_configs(self) -> None:
        """加载配置文件"""
        try:
            with open(self._config_path, 'r') as f:
                configs = yaml.safe_load(f)

            if configs and 'collectors' in configs:
                self._configs = configs['collectors']
                logger.info(f"从配置文件加载了 {len(self._configs)} 个收集器配置")
            else:
                logger.warning("配置文件格式不正确，缺少 'collectors' 部分")
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")

    async def _register_collectors(self) -> None:
        """注册所有收集器"""
        # 这里应该动态导入和注册所有收集器
        # 暂时只创建一些示例收集器

        # 示例：新闻收集器
        news_config = CollectorConfig(
            name="news_collector",
            source_type=DataSourceType.NEWS,
            interval_seconds=3600,  # 1小时
            batch_size=100,
            params={
                "sources": ["newsapi", "rss"],
                "topics": ["geopolitics", "conflict", "economics"]
            }
        )

        # 示例：金融数据收集器
        financial_config = CollectorConfig(
            name="financial_collector",
            source_type=DataSourceType.FINANCIAL,
            interval_seconds=1800,  # 30分钟
            batch_size=50,
            params={
                "indicators": ["stocks", "currencies", "commodities"],
                "exchanges": ["NYSE", "NASDAQ", "HKEX"]
            }
        )

        # 从配置文件更新配置
        if "news_collector" in self._configs:
            news_config = self._update_config_from_dict(news_config, self._configs["news_collector"])

        if "financial_collector" in self._configs:
            financial_config = self._update_config_from_dict(financial_config, self._configs["financial_collector"])

        # 创建并注册收集器（这里需要具体实现）
        # 暂时只创建占位符
        # news_collector = NewsCollector(news_config)
        # financial_collector = FinancialDataCollector(financial_config)

        # self.registry.register(news_collector)
        # self.registry.register(financial_collector)

    def _update_config_from_dict(self, config: CollectorConfig, config_dict: Dict[str, Any]) -> CollectorConfig:
        """从字典更新配置"""
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
            elif key == "params" and isinstance(value, dict):
                config.params.update(value)
        return config

    async def start(self) -> None:
        """启动数据收集"""
        if self._running:
            logger.warning("数据收集已经在运行")
            return

        logger.info("启动数据收集")
        self._running = True

        # 启动定期收集任务
        for collector in self.registry.get_enabled_collectors():
            task = asyncio.create_task(self._run_collector(collector))
            self._tasks[collector.name] = task
            logger.info(f"启动收集器: {collector.name}")

        # 启动监控任务
        monitor_task = asyncio.create_task(self._monitor_collectors())
        self._tasks["monitor"] = monitor_task

        logger.info("数据收集已启动")

    async def stop(self) -> None:
        """停止数据收集"""
        if not self._running:
            logger.warning("数据收集未在运行")
            return

        logger.info("停止数据收集")
        self._running = False

        # 取消所有任务
        for name, task in self._tasks.items():
            task.cancel()
            logger.info(f"取消任务: {name}")

        # 等待任务完成
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

        logger.info("数据收集已停止")

    async def _run_collector(self, collector: DataCollector) -> None:
        """运行单个收集器"""
        logger.info(f"开始运行收集器: {collector.name}")

        while self._running:
            try:
                if collector.is_due:
                    logger.info(f"收集器 {collector.name} 开始收集数据")
                    records = await collector.collect_with_retry()

                    if records:
                        # 处理收集到的数据
                        await self._process_records(collector, records)
                        logger.info(f"收集器 {collector.name} 收集到 {len(records)} 条数据")
                    else:
                        logger.warning(f"收集器 {collector.name} 未收集到数据")

                # 等待下一次检查
                await asyncio.sleep(60)  # 每分钟检查一次

            except asyncio.CancelledError:
                logger.info(f"收集器 {collector.name} 任务被取消")
                break
            except Exception as e:
                logger.error(f"收集器 {collector.name} 运行错误: {str(e)}")
                await asyncio.sleep(300)  # 错误后等待5分钟

        logger.info(f"收集器 {collector.name} 停止运行")

    async def _process_records(self, collector: DataCollector, records: List) -> None:
        """处理收集到的数据记录"""
        # 这里应该将数据存储到数据库或发送到消息队列
        # 暂时只记录日志
        logger.info(f"处理 {collector.name} 收集的 {len(records)} 条记录")

        # 示例：将数据存储到文件（临时方案）
        output_dir = "data/raw"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/{collector.name}_{timestamp}.json"

        # 这里需要实现具体的存储逻辑
        # with open(filename, 'w') as f:
        #     json.dump([record.to_dict() for record in records], f, indent=2)

        logger.info(f"数据已保存到: {filename}")

    async def _monitor_collectors(self) -> None:
        """监控收集器状态"""
        logger.info("启动收集器监控")

        while self._running:
            try:
                stats = self.registry.get_stats()

                # 检查收集器状态
                for name, stat in stats.items():
                    if not stat['enabled']:
                        continue

                    # 检查是否长时间未收集
                    last_time = stat.get('last_collection_time')
                    if last_time:
                        last_dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                        if datetime.utcnow() - last_dt > timedelta(hours=2):
                            logger.warning(f"收集器 {name} 已超过2小时未收集数据")

                    # 检查错误率
                    total = stat['total_collected']
                    errors = stat['total_errors']
                    if total > 0 and errors / total > 0.1:  # 错误率超过10%
                        logger.warning(f"收集器 {name} 错误率过高: {errors}/{total}")

                # 每5分钟检查一次
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                logger.info("监控任务被取消")
                break
            except Exception as e:
                logger.error(f"监控错误: {str(e)}")
                await asyncio.sleep(60)

        logger.info("收集器监控已停止")

    async def collect_now(self, collector_names: Optional[List[str]] = None) -> Dict[str, List]:
        """立即收集数据"""
        results = {}

        if collector_names:
            collectors = [self.registry.get_collector(name) for name in collector_names]
            collectors = [c for c in collectors if c is not None]
        else:
            collectors = self.registry.get_enabled_collectors()

        for collector in collectors:
            try:
                logger.info(f"立即收集: {collector.name}")
                records = await collector.collect_with_retry()
                results[collector.name] = records
                logger.info(f"收集完成: {collector.name} - {len(records)} 条记录")
            except Exception as e:
                logger.error(f"立即收集失败 {collector.name}: {str(e)}")
                results[collector.name] = []

        return results

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        return {
            "running": self._running,
            "collectors": self.registry.get_stats(),
            "tasks": len(self._tasks),
            "configs_loaded": len(self._configs) > 0
        }

    async def test_all_connections(self) -> Dict[str, bool]:
        """测试所有收集器的连接"""
        results = {}

        for collector in self.registry.get_all_collectors():
            try:
                result = await collector.test_connection()
                results[collector.name] = result
                logger.info(f"连接测试 {collector.name}: {'成功' if result else '失败'}")
            except Exception as e:
                logger.error(f"连接测试失败 {collector.name}: {str(e)}")
                results[collector.name] = False

        return results


# 单例实例
_manager: Optional[DataCollectionManager] = None


async def get_manager(config_path: Optional[str] = None) -> DataCollectionManager:
    """获取数据收集管理器实例（单例）"""
    global _manager

    if _manager is None:
        _manager = DataCollectionManager(config_path)
        await _manager.initialize()

    return _manager


async def start_collection(config_path: Optional[str] = None) -> None:
    """启动数据收集"""
    manager = await get_manager(config_path)
    await manager.start()


async def stop_collection() -> None:
    """停止数据收集"""
    if _manager:
        await _manager.stop()


async def get_status() -> Dict[str, Any]:
    """获取收集状态"""
    if _manager:
        return _manager.get_status()
    return {"running": False, "collectors": {}, "tasks": 0}