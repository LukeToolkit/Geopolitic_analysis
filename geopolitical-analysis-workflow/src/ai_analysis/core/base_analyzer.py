"""
AI分析器基础类
定义AI分析组件的抽象接口和基础实现
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
import asyncio

from src.data_processing.base_processor import BaseProcessor, ProcessorConfig, ProcessingResult

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """分析错误"""
    pass


@dataclass
class AnalysisResult(ProcessingResult):
    """分析结果，继承自ProcessingResult"""
    confidence: float = 0.0  # 分析置信度 (0.0-1.0)
    insights: List[str] = field(default_factory=list)  # 关键洞察
    recommendations: List[str] = field(default_factory=list)  # 建议
    risk_level: str = "low"  # 风险等级: low, medium, high, critical
    impact_score: float = 0.0  # 影响评分 (0.0-10.0)
    geographic_scope: List[str] = field(default_factory=list)  # 影响地理范围
    timeline: Dict[str, Any] = field(default_factory=dict)  # 时间线预测

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "confidence": self.confidence,
            "insights": self.insights,
            "recommendations": self.recommendations,
            "risk_level": self.risk_level,
            "impact_score": self.impact_score,
            "geographic_scope": self.geographic_scope,
            "timeline": self.timeline
        })
        return base_dict


@dataclass
class AnalyzerConfig(ProcessorConfig):
    """分析器配置"""
    model_provider: str = "anthropic"  # 模型提供商: anthropic, openai, local
    model_name: str = "claude-3-opus-20240229"  # 模型名称
    max_tokens: int = 4000  # 最大token数
    temperature: float = 0.1  # 温度参数
    use_cached_results: bool = True  # 是否使用缓存结果
    cache_ttl_seconds: int = 3600  # 缓存过期时间
    geographic_focus: List[str] = field(default_factory=list)  # 地理关注区域
    analysis_depth: str = "standard"  # 分析深度: quick, standard, deep


class BaseAnalyzer(BaseProcessor, ABC):
    """分析器抽象基类，继承自BaseProcessor"""

    def __init__(self, config: AnalyzerConfig):
        super().__init__(config)
        self.analyzer_config = config  # 类型提示用

    @abstractmethod
    async def analyze(self, data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        分析数据
        Args:
            data: 输入数据
            context: 分析上下文信息（区域、时间范围等）
        Returns:
            AnalysisResult: 分析结果
        """
        pass

    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        处理数据（实现BaseProcessor的抽象方法）
        默认调用analyze方法
        """
        return await self.analyze(data, context)

    async def analyze_multimodal(self,
                                 text_data: Optional[str] = None,
                                 geospatial_data: Optional[Any] = None,
                                 temporal_data: Optional[Any] = None,
                                 context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        多模态分析：结合文本、地理空间、时间序列数据
        Args:
            text_data: 文本数据
            geospatial_data: 地理空间数据
            temporal_data: 时间序列数据
            context: 分析上下文
        Returns:
            AnalysisResult: 分析结果
        """
        # 默认实现：分别分析然后融合
        results = []

        if text_data:
            text_result = await self.analyze_text(text_data, context)
            results.append(text_result)

        if geospatial_data:
            geo_result = await self.analyze_geospatial(geospatial_data, context)
            results.append(geo_result)

        if temporal_data:
            temp_result = await self.analyze_temporal(temporal_data, context)
            results.append(temp_result)

        # 融合多个分析结果
        return await self.fuse_analysis_results(results, context)

    @abstractmethod
    async def analyze_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析文本数据"""
        pass

    @abstractmethod
    async def analyze_geospatial(self, geospatial_data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析地理空间数据"""
        pass

    @abstractmethod
    async def analyze_temporal(self, temporal_data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析时间序列数据"""
        pass

    async def fuse_analysis_results(self, results: List[AnalysisResult], context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        融合多个分析结果
        Args:
            results: 多个分析结果
            context: 融合上下文
        Returns:
            AnalysisResult: 融合后的结果
        """
        if not results:
            return AnalysisResult(
                data={},
                confidence=0.0,
                insights=["没有可用数据进行分析"],
                risk_level="unknown"
            )

        # 简单融合策略：取平均置信度，合并insights
        total_confidence = sum(r.confidence for r in results)
        avg_confidence = total_confidence / len(results)

        all_insights = []
        all_recommendations = []
        all_geographic_scopes = []

        for result in results:
            all_insights.extend(result.insights)
            all_recommendations.extend(result.recommendations)
            all_geographic_scopes.extend(result.geographic_scope)

        # 确定最高风险等级
        risk_levels = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        max_risk = max(results, key=lambda r: risk_levels.get(r.risk_level, 0))

        # 计算平均影响评分
        avg_impact = sum(r.impact_score for r in results) / len(results)

        return AnalysisResult(
            data={"fused_results": [r.to_dict() for r in results]},
            confidence=avg_confidence,
            insights=list(set(all_insights)),  # 去重
            recommendations=list(set(all_recommendations)),
            risk_level=max_risk.risk_level,
            impact_score=avg_impact,
            geographic_scope=list(set(all_geographic_scopes)),
            timeline=self._merge_timelines([r.timeline for r in results]),
            metadata={"fusion_method": "simple_average", "source_results": len(results)}
        )

    def _merge_timelines(self, timelines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个时间线预测"""
        merged = {
            "events": [],
            "trends": [],
            "milestones": []
        }

        for timeline in timelines:
            if isinstance(timeline, dict):
                merged["events"].extend(timeline.get("events", []))
                merged["trends"].extend(timeline.get("trends", []))
                merged["milestones"].extend(timeline.get("milestones", []))

        # 去重
        merged["events"] = self._deduplicate_items(merged["events"], "id")
        merged["trends"] = self._deduplicate_items(merged["trends"], "id")
        merged["milestones"] = self._deduplicate_items(merged["milestones"], "id")

        return merged

    def _deduplicate_items(self, items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        """根据指定键去重"""
        seen = set()
        unique_items = []

        for item in items:
            if key in item and item[key] not in seen:
                seen.add(item[key])
                unique_items.append(item)

        return unique_items

    def get_analysis_stats(self) -> Dict[str, Any]:
        """获取分析器统计信息"""
        return {
            "name": self.name,
            "processor_type": self.processor_type,
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "total_warnings": self._total_warnings,
            "model_provider": self.analyzer_config.model_provider,
            "model_name": self.analyzer_config.model_name
        }