"""
航运数据(AIS)分析器
分析船舶自动识别系统(AIS)数据，检测异常航运活动
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, field

from ..core.base_analyzer import BaseAnalyzer, AnalyzerConfig, AnalysisResult
from ..integrations.llm_integration import LLMManager, LLMModel, LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class AISData:
    """AIS数据结构"""
    mmsi: str  # 海事移动服务标识
    ship_name: Optional[str] = None
    ship_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None  # 节
    course: Optional[float] = None  # 度
    heading: Optional[float] = None  # 度
    destination: Optional[str] = None
    eta: Optional[str] = None  # 预计到达时间
    timestamp: Optional[datetime] = None
    draught: Optional[float] = None  # 吃水深度
    cargo: Optional[str] = None  # 货物类型
    flag: Optional[str] = None  # 船旗国


@dataclass
class ShippingPattern:
    """航运模式"""
    route: List[Dict[str, float]]  # 航线坐标
    frequency: int  # 频率（次/天）
    typical_speed: float  # 典型速度（节）
    typical_cargo: List[str]  # 典型货物
    risk_level: str  # 风险等级


class AISAnalyzer(BaseAnalyzer):
    """AIS数据分析器"""

    def __init__(self, config: AnalyzerConfig):
        super().__init__(config)
        self.config.processor_type = "ais_analyzer"
        self._known_patterns: Dict[str, ShippingPattern] = {}
        self._high_risk_areas: List[Dict[str, Any]] = []  # 高风险区域
        self._embargoed_countries: List[str] = []  # 受制裁国家
        self._sensitive_cargo_types: List[str] = ["weapons", "oil", "chemicals", "nuclear"]

    async def analyze(self, data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析AIS数据"""
        try:
            self.logger.info(f"开始分析AIS数据: {self.name}")

            # 解析数据
            ais_data_list = self._parse_ais_data(data)
            if not ais_data_list:
                return AnalysisResult(
                    data={},
                    confidence=0.0,
                    insights=["无有效的AIS数据可供分析"],
                    risk_level="low"
                )

            # 分析异常活动
            anomalies = await self._detect_anomalies(ais_data_list, context)

            # 检测高风险船舶
            high_risk_vessels = await self._detect_high_risk_vessels(ais_data_list)

            # 分析航运模式变化
            pattern_changes = await self._analyze_pattern_changes(ais_data_list)

            # 使用LLM进行综合分析
            llm_analysis = await self._analyze_with_llm(ais_data_list, anomalies, high_risk_vessels, context)

            # 合并结果
            insights = []
            recommendations = []
            risk_level = "low"

            if anomalies:
                insights.append(f"检测到 {len(anomalies)} 个异常航运活动")
                risk_level = self._escalate_risk(risk_level, "medium")

            if high_risk_vessels:
                insights.append(f"发现 {len(high_risk_vessels)} 艘高风险船舶")
                risk_level = self._escalate_risk(risk_level, "high")

            if pattern_changes:
                insights.append(f"检测到航运模式变化: {len(pattern_changes)} 处")
                risk_level = self._escalate_risk(risk_level, "medium")

            if llm_analysis.get("insights"):
                insights.extend(llm_analysis["insights"])
                risk_level = self._escalate_risk(risk_level, llm_analysis.get("risk_level", "low"))

            if llm_analysis.get("recommendations"):
                recommendations.extend(llm_analysis["recommendations"])

            # 确定地理范围
            geographic_scope = self._determine_geographic_scope(ais_data_list)

            # 计算置信度
            confidence = self._calculate_confidence(ais_data_list, len(anomalies))

            # 计算影响评分
            impact_score = self._calculate_impact_score(anomalies, high_risk_vessels, pattern_changes)

            return AnalysisResult(
                data={
                    "vessels_analyzed": len(ais_data_list),
                    "anomalies": anomalies,
                    "high_risk_vessels": high_risk_vessels,
                    "pattern_changes": pattern_changes,
                    "geographic_scope": geographic_scope
                },
                confidence=confidence,
                insights=insights,
                recommendations=recommendations,
                risk_level=risk_level,
                impact_score=impact_score,
                geographic_scope=geographic_scope,
                timeline=self._generate_timeline(ais_data_list, anomalies),
                metadata={
                    "analyzer": self.name,
                    "data_source": "AIS",
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"AIS分析失败: {str(e)}", exc_info=True)
            return AnalysisResult(
                data=data,
                confidence=0.0,
                errors=[f"AIS分析失败: {str(e)}"],
                risk_level="unknown"
            )

    def _parse_ais_data(self, data: Any) -> List[AISData]:
        """解析AIS数据"""
        ais_data_list = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    try:
                        ais_data = AISData(
                            mmsi=str(item.get("mmsi", "")),
                            ship_name=item.get("ship_name"),
                            ship_type=item.get("ship_type"),
                            latitude=item.get("latitude"),
                            longitude=item.get("longitude"),
                            speed=item.get("speed"),
                            course=item.get("course"),
                            heading=item.get("heading"),
                            destination=item.get("destination"),
                            eta=item.get("eta"),
                            timestamp=item.get("timestamp"),
                            draught=item.get("draught"),
                            cargo=item.get("cargo"),
                            flag=item.get("flag")
                        )
                        ais_data_list.append(ais_data)
                    except Exception as e:
                        logger.warning(f"解析AIS数据项失败: {e}")
        elif isinstance(data, dict):
            # 单个船舶数据
            try:
                ais_data = AISData(
                    mmsi=str(data.get("mmsi", "")),
                    ship_name=data.get("ship_name"),
                    ship_type=data.get("ship_type"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    speed=data.get("speed"),
                    course=data.get("course"),
                    heading=data.get("heading"),
                    destination=data.get("destination"),
                    eta=data.get("eta"),
                    timestamp=data.get("timestamp"),
                    draught=data.get("draught"),
                    cargo=data.get("cargo"),
                    flag=data.get("flag")
                )
                ais_data_list.append(ais_data)
            except Exception as e:
                logger.warning(f"解析AIS数据失败: {e}")

        logger.info(f"解析了 {len(ais_data_list)} 条AIS数据记录")
        return ais_data_list

    async def _detect_anomalies(self, ais_data_list: List[AISData], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测异常活动"""
        anomalies = []

        for ais_data in ais_data_list:
            # 检查位置异常
            if ais_data.latitude and ais_data.longitude:
                if self._is_in_restricted_area(ais_data.latitude, ais_data.longitude):
                    anomalies.append({
                        "mmsi": ais_data.mmsi,
                        "ship_name": ais_data.ship_name,
                        "type": "restricted_area",
                        "description": f"船舶进入限制区域 ({ais_data.latitude}, {ais_data.longitude})",
                        "severity": "high"
                    })

            # 检查速度异常
            if ais_data.speed is not None:
                if ais_data.speed == 0:
                    # 长时间停滞
                    anomalies.append({
                        "mmsi": ais_data.mmsi,
                        "ship_name": ais_data.ship_name,
                        "type": "stagnation",
                        "description": f"船舶停滞 (速度: {ais_data.speed}节)",
                        "severity": "medium"
                    })
                elif ais_data.speed > 30:  # 异常高速
                    anomalies.append({
                        "mmsi": ais_data.mmsi,
                        "ship_name": ais_data.ship_name,
                        "type": "high_speed",
                        "description": f"异常高速航行 (速度: {ais_data.speed}节)",
                        "severity": "medium"
                    })

            # 检查船旗国异常
            if ais_data.flag and ais_data.flag in self._embargoed_countries:
                anomalies.append({
                    "mmsi": ais_data.mmsi,
                    "ship_name": ais_data.ship_name,
                    "type": "embargoed_flag",
                    "description": f"船舶注册在受制裁国家: {ais_data.flag}",
                    "severity": "high"
                })

            # 检查货物类型
            if ais_data.cargo and any(sensitive in ais_data.cargo.lower() for sensitive in self._sensitive_cargo_types):
                anomalies.append({
                    "mmsi": ais_data.mmsi,
                    "ship_name": ais_data.ship_name,
                    "type": "sensitive_cargo",
                    "description": f"运载敏感货物: {ais_data.cargo}",
                    "severity": "high"
                })

            # 检查AIS信号异常（突然消失/出现）
            # 这里需要历史数据对比，简化实现

        return anomalies

    async def _detect_high_risk_vessels(self, ais_data_list: List[AISData]) -> List[Dict[str, Any]]:
        """检测高风险船舶"""
        high_risk_vessels = []

        # 高风险船舶特征
        for ais_data in ais_data_list:
            risk_factors = []

            # 未知/模糊身份
            if not ais_data.ship_name or ais_data.ship_name.strip() in ["", "UNKNOWN", "N/A"]:
                risk_factors.append("身份不明")

            # 频繁更改目的地
            # 这里需要历史数据，简化实现

            # 异常航线
            if self._is_unusual_route(ais_data):
                risk_factors.append("异常航线")

            # 高风险货物
            if ais_data.cargo and any(sensitive in ais_data.cargo.lower() for sensitive in self._sensitive_cargo_types):
                risk_factors.append("敏感货物")

            # 受制裁船旗国
            if ais_data.flag in self._embargoed_countries:
                risk_factors.append("受制裁船旗国")

            if risk_factors:
                high_risk_vessels.append({
                    "mmsi": ais_data.mmsi,
                    "ship_name": ais_data.ship_name,
                    "risk_factors": risk_factors,
                    "risk_score": len(risk_factors) * 25,  # 简单评分
                    "current_position": {
                        "latitude": ais_data.latitude,
                        "longitude": ais_data.longitude
                    } if ais_data.latitude and ais_data.longitude else None
                })

        return high_risk_vessels

    async def _analyze_pattern_changes(self, ais_data_list: List[AISData]) -> List[Dict[str, Any]]:
        """分析航运模式变化"""
        # 简化实现：基于当前位置和历史模式对比
        pattern_changes = []

        # 这里需要历史数据来检测模式变化
        # 临时返回空列表
        return pattern_changes

    async def _analyze_with_llm(self, ais_data_list: List[AISData], anomalies: List[Dict[str, Any]],
                               high_risk_vessels: List[Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM进行综合分析"""
        try:
            # 准备分析数据
            analysis_data = {
                "vessels_count": len(ais_data_list),
                "anomalies_count": len(anomalies),
                "high_risk_vessels_count": len(high_risk_vessels),
                "sample_vessels": ais_data_list[:5],  # 采样前5艘
                "sample_anomalies": anomalies[:3],  # 采样前3个异常
                "geographic_focus": context.get("region") if context else "全球",
                "analysis_timeframe": context.get("timeframe") if context else "实时"
            }

            prompt = f"""
作为地缘政治和航运安全分析专家，请分析以下AIS数据：

数据摘要:
- 船舶总数: {analysis_data['vessels_count']}
- 异常活动数: {analysis_data['anomalies_count']}
- 高风险船舶数: {analysis_data['high_risk_vessels_count']}
- 分析区域: {analysis_data['geographic_focus']}
- 时间范围: {analysis_data['analysis_timeframe']}

详细数据:
{json.dumps(analysis_data, indent=2, default=str)}

请提供:
1. 关键洞察（3-5条）
2. 风险评估（low/medium/high/critical）
3. 建议措施（3-5条）
4. 潜在的地缘政治影响
5. 需要关注的特定船舶或区域

请用JSON格式回复，包含以下字段:
- insights: 字符串列表
- risk_level: 字符串
- recommendations: 字符串列表
- geopolitical_impact: 字符串
- areas_to_watch: 字符串列表
"""

            result = await LLMManager.generate_structured(
                prompt=prompt,
                output_schema={
                    "insights": ["string"],
                    "risk_level": "string",
                    "recommendations": ["string"],
                    "geopolitical_impact": "string",
                    "areas_to_watch": ["string"]
                },
                system_prompt="你是地缘政治和航运安全分析专家，擅长从AIS数据中识别潜在威胁和异常模式。",
                model=LLMModel.CLAUDE_3_SONNET,
                provider=LLMProvider.ANTHROPIC,
                temperature=0.1,
                max_tokens=2000
            )

            return result

        except Exception as e:
            logger.error(f"LLM分析失败: {str(e)}")
            return {
                "insights": ["LLM分析暂时不可用"],
                "risk_level": "unknown",
                "recommendations": ["检查LLM配置"],
                "geopolitical_impact": "无法评估",
                "areas_to_watch": []
            }

    def _is_in_restricted_area(self, latitude: float, longitude: float) -> bool:
        """检查是否在限制区域"""
        # 简化实现：检查是否在预定义的高风险区域
        for area in self._high_risk_areas:
            lat_min = area.get("lat_min", -90)
            lat_max = area.get("lat_max", 90)
            lon_min = area.get("lon_min", -180)
            lon_max = area.get("lon_max", 180)

            if lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max:
                return True
        return False

    def _is_unusual_route(self, ais_data: AISData) -> bool:
        """检查是否异常航线"""
        # 简化实现：基于船舶类型和位置判断
        # 这里需要历史航线数据，返回False
        return False

    def _escalate_risk(self, current_risk: str, new_risk: str) -> str:
        """升级风险等级"""
        risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 0}
        current_level = risk_levels.get(current_risk, 0)
        new_level = risk_levels.get(new_risk, 0)
        return new_risk if new_level > current_level else current_risk

    def _determine_geographic_scope(self, ais_data_list: List[AISData]) -> List[str]:
        """确定地理范围"""
        regions = set()

        for ais_data in ais_data_list:
            if ais_data.latitude and ais_data.longitude:
                # 简单区域判断
                if 20 <= ais_data.latitude <= 50 and 100 <= ais_data.longitude <= 140:
                    regions.add("东亚")
                elif 30 <= ais_data.latitude <= 50 and -10 <= ais_data.longitude <= 40:
                    regions.add("欧洲")
                elif 10 <= ais_data.latitude <= 40 and 30 <= ais_data.longitude <= 60:
                    regions.add("中东")
                # 添加更多区域判断...

        return list(regions) if regions else ["全球"]

    def _calculate_confidence(self, ais_data_list: List[AISData], anomaly_count: int) -> float:
        """计算分析置信度"""
        if not ais_data_list:
            return 0.0

        # 基于数据量和异常数量计算置信度
        data_confidence = min(len(ais_data_list) / 100, 1.0)  # 最多100条数据达到最大置信度
        anomaly_confidence = min(anomaly_count / 10, 1.0) if anomaly_count > 0 else 0.5

        # 加权平均
        return 0.7 * data_confidence + 0.3 * anomaly_confidence

    def _calculate_impact_score(self, anomalies: List[Dict[str, Any]],
                               high_risk_vessels: List[Dict[str, Any]],
                               pattern_changes: List[Dict[str, Any]]) -> float:
        """计算影响评分（0-10）"""
        score = 0.0

        # 异常活动贡献
        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            if severity == "high":
                score += 2.0
            elif severity == "medium":
                score += 1.0
            else:
                score += 0.5

        # 高风险船舶贡献
        score += len(high_risk_vessels) * 1.5

        # 模式变化贡献
        score += len(pattern_changes) * 1.0

        return min(score, 10.0)

    def _generate_timeline(self, ais_data_list: List[AISData], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成时间线预测"""
        timeline = {
            "events": [],
            "trends": [],
            "milestones": []
        }

        # 基于异常预测未来事件
        for anomaly in anomalies[:3]:  # 前3个异常
            timeline["events"].append({
                "id": f"event_{anomaly.get('mmsi', 'unknown')}_{datetime.now().timestamp()}",
                "type": anomaly.get("type", "unknown"),
                "description": anomaly.get("description", ""),
                "predicted_time": (datetime.now() + timedelta(hours=6)).isoformat(),
                "confidence": 0.7
            })

        # 添加趋势预测
        if len(anomalies) > 5:
            timeline["trends"].append({
                "id": "trend_increased_risk",
                "description": "航运风险呈上升趋势",
                "timeframe": "未来24小时",
                "direction": "increasing"
            })

        return timeline

    async def analyze_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析文本数据（AIS相关报告）"""
        # 实现文本分析逻辑
        return AnalysisResult(
            data={"text": text},
            confidence=0.8,
            insights=["文本分析功能待实现"],
            risk_level="low"
        )

    async def analyze_geospatial(self, geospatial_data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析地理空间数据"""
        # 实现地理空间分析逻辑
        return AnalysisResult(
            data={"geospatial": geospatial_data},
            confidence=0.8,
            insights=["地理空间分析功能待实现"],
            risk_level="low"
        )

    async def analyze_temporal(self, temporal_data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析时间序列数据"""
        # 实现时间序列分析逻辑
        return AnalysisResult(
            data={"temporal": temporal_data},
            confidence=0.8,
            insights=["时间序列分析功能待实现"],
            risk_level="low"
        )


# 辅助函数
import json  # 导入json模块用于序列化