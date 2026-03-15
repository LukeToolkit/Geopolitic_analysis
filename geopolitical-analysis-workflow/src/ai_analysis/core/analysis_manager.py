"""
AI分析管理器
负责协调和管理所有AI分析器，提供统一的分析接口
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import yaml
import os
import json
from enum import Enum

from .base_analyzer import BaseAnalyzer, AnalyzerConfig, AnalysisResult
from ..analyzers.ais_analyzer import AISAnalyzer
from ..analyzers.adsb_analyzer import ADS_BAnalyzer
from ..analyzers.military_analyzer import MilitaryAnalyzer
from ..analyzers.fusion_analyzer import FusionAnalyzer

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型枚举"""
    AIS_ANALYSIS = "ais_analysis"
    ADS_B_ANALYSIS = "adsb_analysis"
    MILITARY_ANALYSIS = "military_analysis"
    FUSION_ANALYSIS = "fusion_analysis"
    TEXT_ANALYSIS = "text_analysis"
    GEOSPATIAL_ANALYSIS = "geospatial_analysis"
    TEMPORAL_ANALYSIS = "temporal_analysis"


@dataclass
class AnalysisRequest:
    """分析请求"""
    analysis_type: AnalysisType
    data: Any
    context: Optional[Dict[str, Any]] = None
    priority: int = 1  # 1-10，越高优先级越高
    timeout_seconds: int = 300
    callback: Optional[Callable[[AnalysisResult], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisJob:
    """分析任务"""
    job_id: str
    request: AnalysisRequest
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[AnalysisResult] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None


class AnalysisManager:
    """AI分析管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.jobs: Dict[str, AnalysisJob] = {}
        self._config_path = config_path
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._worker_tasks: List[asyncio.Task] = []
        self._stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "average_processing_time": 0.0,
            "active_analyzers": 0
        }

    async def initialize(self) -> None:
        """初始化管理器"""
        logger.info("初始化AI分析管理器")

        # 加载配置
        if self._config_path and os.path.exists(self._config_path):
            await self._load_configs()
        else:
            logger.warning(f"配置文件不存在: {self._config_path}，使用默认配置")

        # 注册分析器
        await self._register_analyzers()

        logger.info(f"AI分析管理器初始化完成，注册了 {len(self.analyzers)} 个分析器")

    async def _load_configs(self) -> None:
        """加载配置文件"""
        try:
            with open(self._config_path, 'r') as f:
                configs = yaml.safe_load(f)

            if configs and 'analyzers' in configs:
                self._configs = configs['analyzers']
                logger.info(f"从配置文件加载了 {len(self._configs)} 个分析器配置")
            else:
                logger.warning("配置文件格式不正确，缺少 'analyzers' 部分")
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")

    async def _register_analyzers(self) -> None:
        """注册所有分析器"""
        # AIS分析器
        ais_config = AnalyzerConfig(
            name="ais_analyzer",
            processor_type="ais_analyzer",
            model_provider="anthropic",
            model_name="claude-3-sonnet-20240229",
            geographic_focus=["global"],
            analysis_depth="standard"
        )
        ais_analyzer = AISAnalyzer(ais_config)
        self.analyzers[AnalysisType.AIS_ANALYSIS.value] = ais_analyzer

        # ADS-B分析器
        adsb_config = AnalyzerConfig(
            name="adsb_analyzer",
            processor_type="adsb_analyzer",
            model_provider="anthropic",
            model_name="claude-3-sonnet-20240229",
            geographic_focus=["global"],
            analysis_depth="standard"
        )
        adsb_analyzer = ADS_BAnalyzer(adsb_config)
        self.analyzers[AnalysisType.ADS_B_ANALYSIS.value] = adsb_analyzer

        # 军事分析器
        military_config = AnalyzerConfig(
            name="military_analyzer",
            processor_type="military_analyzer",
            model_provider="anthropic",
            model_name="claude-3-sonnet-20240229",
            geographic_focus=["global"],
            analysis_depth="deep"
        )
        military_analyzer = MilitaryAnalyzer(military_config)
        self.analyzers[AnalysisType.MILITARY_ANALYSIS.value] = military_analyzer

        # 融合分析器
        fusion_config = AnalyzerConfig(
            name="fusion_analyzer",
            processor_type="fusion_analyzer",
            model_provider="anthropic",
            model_name="claude-3-sonnet-20240229",
            geographic_focus=["global"],
            analysis_depth="deep"
        )
        fusion_analyzer = FusionAnalyzer(fusion_config)
        self.analyzers[AnalysisType.FUSION_ANALYSIS.value] = fusion_analyzer

        # 从配置文件更新配置
        for analyzer_name, analyzer in self.analyzers.items():
            if analyzer_name in self._configs:
                self._update_analyzer_config(analyzer, self._configs[analyzer_name])

        logger.info(f"注册分析器: {list(self.analyzers.keys())}")

    def _update_analyzer_config(self, analyzer: BaseAnalyzer, config_dict: Dict[str, Any]) -> None:
        """从字典更新分析器配置"""
        for key, value in config_dict.items():
            if hasattr(analyzer.config, key):
                setattr(analyzer.config, key, value)
            elif key == "params" and isinstance(value, dict):
                analyzer.config.params.update(value)

    async def start(self) -> None:
        """启动分析管理器"""
        if self._running:
            logger.warning("分析管理器已经在运行")
            return

        logger.info("启动AI分析管理器")
        self._running = True

        # 启动工作线程
        worker_count = min(4, len(self.analyzers))  # 最多4个工作线程
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop(f"worker_{i+1}"))
            self._worker_tasks.append(task)
            logger.info(f"启动分析工作线程: worker_{i+1}")

        # 启动监控任务
        monitor_task = asyncio.create_task(self._monitor_analyzers())
        self._worker_tasks.append(monitor_task)

        logger.info(f"AI分析管理器已启动，{worker_count} 个工作线程运行中")

    async def stop(self) -> None:
        """停止分析管理器"""
        if not self._running:
            logger.warning("分析管理器未在运行")
            return

        logger.info("停止AI分析管理器")
        self._running = False

        # 取消所有工作线程
        for task in self._worker_tasks:
            task.cancel()

        # 等待任务完成
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

        # 清空任务队列
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("AI分析管理器已停止")

    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """执行分析（同步接口）"""
        job_id = f"job_{datetime.now().timestamp()}_{len(self.jobs)}"
        job = AnalysisJob(job_id=job_id, request=request)

        self.jobs[job_id] = job
        self._stats["total_jobs"] += 1

        try:
            # 获取分析器
            analyzer = self.analyzers.get(request.analysis_type.value)
            if not analyzer:
                raise ValueError(f"不支持的分析类型: {request.analysis_type}")

            # 执行分析
            job.status = "running"
            job.start_time = datetime.now()

            result = await analyzer.analyze(request.data, request.context)

            job.status = "completed"
            job.result = result
            job.end_time = datetime.now()

            # 更新统计信息
            self._stats["completed_jobs"] += 1
            processing_time = (job.end_time - job.start_time).total_seconds()
            self._update_processing_time_stats(processing_time)

            logger.info(f"分析完成: {job_id}, 耗时: {processing_time:.2f}s")

            # 执行回调
            if request.callback:
                try:
                    request.callback(result)
                except Exception as e:
                    logger.error(f"分析回调失败: {str(e)}")

            return result

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.end_time = datetime.now()
            self._stats["failed_jobs"] += 1

            logger.error(f"分析失败: {job_id}, 错误: {str(e)}")

            # 返回错误结果
            return AnalysisResult(
                data=request.data,
                confidence=0.0,
                errors=[f"分析失败: {str(e)}"],
                risk_level="unknown"
            )

    async def analyze_async(self, request: AnalysisRequest) -> str:
        """异步执行分析"""
        job_id = f"async_job_{datetime.now().timestamp()}_{len(self.jobs)}"
        job = AnalysisJob(job_id=job_id, request=request)

        self.jobs[job_id] = job
        self._stats["total_jobs"] += 1

        # 添加到任务队列（优先级队列）
        await self._task_queue.put((10 - request.priority, job_id))

        logger.info(f"异步分析任务已提交: {job_id}, 优先级: {request.priority}")
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        job = self.jobs.get(job_id)
        if not job:
            return None

        status = {
            "job_id": job.job_id,
            "status": job.status,
            "analysis_type": job.request.analysis_type.value,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "error": job.error
        }

        if job.result:
            status["result_summary"] = {
                "confidence": job.result.confidence,
                "risk_level": job.result.risk_level,
                "insights_count": len(job.result.insights),
                "impact_score": job.result.impact_score
            }

        return status

    async def get_job_result(self, job_id: str) -> Optional[AnalysisResult]:
        """获取任务结果"""
        job = self.jobs.get(job_id)
        return job.result if job else None

    async def analyze_multimodal(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """多模态分析：整合多个分析器"""
        try:
            logger.info("开始多模态分析")

            # 收集各个数据源的分析结果
            results = []

            # AIS数据分析
            if "ais_data" in data and data["ais_data"]:
                ais_request = AnalysisRequest(
                    analysis_type=AnalysisType.AIS_ANALYSIS,
                    data=data["ais_data"],
                    context=context
                )
                ais_result = await self.analyze(ais_request)
                results.append(("ais", ais_result))

            # ADS-B数据分析
            if "adsb_data" in data and data["adsb_data"]:
                adsb_request = AnalysisRequest(
                    analysis_type=AnalysisType.ADS_B_ANALYSIS,
                    data=data["adsb_data"],
                    context=context
                )
                adsb_result = await self.analyze(adsb_request)
                results.append(("adsb", adsb_result))

            # 军事数据分析
            if "military_data" in data and data["military_data"]:
                military_request = AnalysisRequest(
                    analysis_type=AnalysisType.MILITARY_ANALYSIS,
                    data=data["military_data"],
                    context=context
                )
                military_result = await self.analyze(military_request)
                results.append(("military", military_result))

            # 如果只有一个结果，直接返回
            if len(results) == 1:
                return results[0][1]

            # 如果有多个结果，进行融合分析
            fusion_data = {}
            for source_type, result in results:
                fusion_data[f"{source_type}_data"] = result.data

            fusion_request = AnalysisRequest(
                analysis_type=AnalysisType.FUSION_ANALYSIS,
                data=fusion_data,
                context=context
            )
            fusion_result = await self.analyze(fusion_request)

            return fusion_result

        except Exception as e:
            logger.error(f"多模态分析失败: {str(e)}", exc_info=True)
            return AnalysisResult(
                data=data,
                confidence=0.0,
                errors=[f"多模态分析失败: {str(e)}"],
                risk_level="unknown"
            )

    async def _worker_loop(self, worker_name: str) -> None:
        """工作线程循环"""
        logger.info(f"分析工作线程启动: {worker_name}")

        while self._running:
            try:
                # 从队列获取任务
                priority, job_id = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)

                job = self.jobs.get(job_id)
                if not job or job.status != "pending":
                    self._task_queue.task_done()
                    continue

                # 执行分析
                try:
                    analyzer = self.analyzers.get(job.request.analysis_type.value)
                    if not analyzer:
                        raise ValueError(f"不支持的分析类型: {job.request.analysis_type}")

                    job.status = "running"
                    job.start_time = datetime.now()

                    result = await analyzer.analyze(job.request.data, job.request.context)

                    job.status = "completed"
                    job.result = result
                    job.end_time = datetime.now()

                    # 更新统计信息
                    self._stats["completed_jobs"] += 1
                    processing_time = (job.end_time - job.start_time).total_seconds()
                    self._update_processing_time_stats(processing_time)

                    logger.info(f"{worker_name}: 分析完成 {job_id}, 耗时: {processing_time:.2f}s")

                    # 执行回调
                    if job.request.callback:
                        try:
                            job.request.callback(result)
                        except Exception as e:
                            logger.error(f"{worker_name}: 分析回调失败: {str(e)}")

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    job.status = "failed"
                    job.error = str(e)
                    job.end_time = datetime.now()
                    self._stats["failed_jobs"] += 1
                    logger.error(f"{worker_name}: 分析失败 {job_id}, 错误: {str(e)}")

                finally:
                    self._task_queue.task_done()

            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except asyncio.CancelledError:
                logger.info(f"{worker_name}: 工作线程被取消")
                break
            except Exception as e:
                logger.error(f"{worker_name}: 工作线程错误: {str(e)}")
                await asyncio.sleep(5)

        logger.info(f"{worker_name}: 分析工作线程停止")

    async def _monitor_analyzers(self) -> None:
        """监控分析器状态"""
        logger.info("启动分析器监控")

        while self._running:
            try:
                # 检查分析器状态
                for analyzer_name, analyzer in self.analyzers.items():
                    try:
                        # 获取分析器统计信息
                        stats = analyzer.get_analysis_stats()

                        # 检查处理错误率
                        total_processed = stats.get("total_processed", 0)
                        total_errors = stats.get("total_errors", 0)
                        if total_processed > 0:
                            error_rate = total_errors / total_processed
                            if error_rate > 0.2:  # 错误率超过20%
                                logger.warning(f"分析器 {analyzer_name} 错误率过高: {error_rate:.2%}")

                        # 检查长时间运行的分析器
                        # 这里可以添加更多监控逻辑

                    except Exception as e:
                        logger.error(f"监控分析器 {analyzer_name} 失败: {str(e)}")

                # 每5分钟检查一次
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                logger.info("监控任务被取消")
                break
            except Exception as e:
                logger.error(f"监控错误: {str(e)}")
                await asyncio.sleep(60)

        logger.info("分析器监控已停止")

    def _update_processing_time_stats(self, new_time: float) -> None:
        """更新处理时间统计"""
        total_completed = self._stats["completed_jobs"]
        current_avg = self._stats["average_processing_time"]

        # 指数加权移动平均
        alpha = 0.1
        new_avg = current_avg * (1 - alpha) + new_time * alpha
        self._stats["average_processing_time"] = new_avg

    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            "running": self._running,
            "analyzers_count": len(self.analyzers),
            "active_workers": len(self._worker_tasks),
            "queue_size": self._task_queue.qsize(),
            "jobs": self._stats.copy(),
            "analyzers": {name: analyzer.get_analysis_stats() for name, analyzer in self.analyzers.items()}
        }

    def get_analyzer(self, analysis_type: AnalysisType) -> Optional[BaseAnalyzer]:
        """获取分析器"""
        return self.analyzers.get(analysis_type.value)


# 单例实例
_analysis_manager: Optional[AnalysisManager] = None


async def get_analysis_manager(config_path: Optional[str] = None) -> AnalysisManager:
    """获取分析管理器实例（单例）"""
    global _analysis_manager

    if _analysis_manager is None:
        _analysis_manager = AnalysisManager(config_path)
        await _analysis_manager.initialize()

    return _analysis_manager


async def start_analysis(config_path: Optional[str] = None) -> None:
    """启动分析服务"""
    manager = await get_analysis_manager(config_path)
    await manager.start()


async def stop_analysis() -> None:
    """停止分析服务"""
    global _analysis_manager
    if _analysis_manager:
        await _analysis_manager.stop()


async def analyze_data(analysis_type: AnalysisType, data: Any,
                      context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
    """分析数据（简化接口）"""
    manager = await get_analysis_manager()
    request = AnalysisRequest(analysis_type=analysis_type, data=data, context=context)
    return await manager.analyze(request)


async def analyze_multimodal_data(data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
    """多模态数据分析（简化接口）"""
    manager = await get_analysis_manager()
    return await manager.analyze_multimodal(data, context)


def get_analysis_status() -> Dict[str, Any]:
    """获取分析服务状态"""
    if _analysis_manager:
        return _analysis_manager.get_stats()
    return {"running": False, "analyzers_count": 0, "active_workers": 0}