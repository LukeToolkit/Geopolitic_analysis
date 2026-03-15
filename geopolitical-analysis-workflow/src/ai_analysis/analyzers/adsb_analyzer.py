"""
民航数据(ADS-B)分析器
分析广播式自动相关监视(ADS-B)数据，检测异常航空活动
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
class ADS_BData:
    """ADS-B数据结构"""
    icao24: str  # ICAO 24位地址
    callsign: Optional[str] = None
    origin_country: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    altitude: Optional[float] = None  # 米
    velocity: Optional[float] = None  # 米/秒
    heading: Optional[float] = None  # 度
    vertical_rate: Optional[float] = None  # 米/秒
    squawk: Optional[str] = None  # 应答机代码
    on_ground: Optional[bool] = None
    aircraft_type: Optional[str] = None
    registration: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None  # 数据源


@dataclass
class FlightPattern:
    """飞行模式"""
    route: List[Dict[str, float]]  # 航线坐标
    typical_altitude: float  # 典型高度（米）
    typical_speed: float  # 典型速度（米/秒）
    frequency: int  # 频率（次/天）
    risk_level: str  # 风险等级


class ADS_BAnalyzer(BaseAnalyzer):
    """ADS-B数据分析器"""

    def __init__(self, config: AnalyzerConfig):
        super().__init__(config)
        self.config.processor_type = "adsb_analyzer"
        self._known_patterns: Dict[str, FlightPattern] = {}
        self._restricted_airspace: List[Dict[str, Any]] = []  # 限制空域
        self._high_risk_aircraft_types: List[str] = ["military", "government", "unknown"]
        self._sensitive_countries: List[str] = []  # 敏感国家
        self._no_fly_zones: List[Dict[str, Any]] = []  # 禁飞区

    async def analyze(self, data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析ADS-B数据"""
        try:
            self.logger.info(f"开始分析ADS-B数据: {self.name}")

            # 解析数据
            adsb_data_list = self._parse_adsb_data(data)
            if not adsb_data_list:
                return AnalysisResult(
                    data={},
                    confidence=0.0,
                    insights=["无有效的ADS-B数据可供分析"],
                    risk_level="low"
                )

            # 检测异常活动
            anomalies = await self._detect_anomalies(adsb_data_list, context)

            # 检测高风险航空器
            high_risk_aircraft = await self._detect_high_risk_aircraft(adsb_data_list)

            # 分析飞行模式变化
            pattern_changes = await self._analyze_pattern_changes(adsb_data_list)

            # 检测空域侵犯
            airspace_violations = await self._detect_airspace_violations(adsb_data_list)

            # 使用LLM进行综合分析
            llm_analysis = await self._analyze_with_llm(adsb_data_list, anomalies, high_risk_aircraft,
                                                       airspace_violations, context)

            # 合并结果
            insights = []
            recommendations = []
            risk_level = "low"

            if anomalies:
                insights.append(f"检测到 {len(anomalies)} 个异常航空活动")
                risk_level = self._escalate_risk(risk_level, "medium")

            if high_risk_aircraft:
                insights.append(f"发现 {len(high_risk_aircraft)} 架高风险航空器")
                risk_level = self._escalate_risk(risk_level, "high")

            if airspace_violations:
                insights.append(f"检测到 {len(airspace_violations)} 次空域侵犯")
                risk_level = self._escalate_risk(risk_level, "high")

            if pattern_changes:
                insights.append(f"检测到飞行模式变化: {len(pattern_changes)} 处")
                risk_level = self._escalate_risk(risk_level, "medium")

            if llm_analysis.get("insights"):
                insights.extend(llm_analysis["insights"])
                risk_level = self._escalate_risk(risk_level, llm_analysis.get("risk_level", "low"))

            if llm_analysis.get("recommendations"):
                recommendations.extend(llm_analysis["recommendations"])

            # 确定地理范围
            geographic_scope = self._determine_geographic_scope(adsb_data_list)

            # 计算置信度
            confidence = self._calculate_confidence(adsb_data_list, len(anomalies), len(airspace_violations))

            # 计算影响评分
            impact_score = self._calculate_impact_score(anomalies, high_risk_aircraft, airspace_violations)

            return AnalysisResult(
                data={
                    "aircraft_analyzed": len(adsb_data_list),
                    "anomalies": anomalies,
                    "high_risk_aircraft": high_risk_aircraft,
                    "airspace_violations": airspace_violations,
                    "pattern_changes": pattern_changes,
                    "geographic_scope": geographic_scope
                },
                confidence=confidence,
                insights=insights,
                recommendations=recommendations,
                risk_level=risk_level,
                impact_score=impact_score,
                geographic_scope=geographic_scope,
                timeline=self._generate_timeline(adsb_data_list, anomalies, airspace_violations),
                metadata={
                    "analyzer": self.name,
                    "data_source": "ADS-B",
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"ADS-B分析失败: {str(e)}", exc_info=True)
            return AnalysisResult(
                data=data,
                confidence=0.0,
                errors=[f"ADS-B分析失败: {str(e)}"],
                risk_level="unknown"
            )

    def _parse_adsb_data(self, data: Any) -> List[ADS_BData]:
        """解析ADS-B数据"""
        adsb_data_list = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    try:
                        # 处理时间戳
                        timestamp = item.get("timestamp")
                        if timestamp and isinstance(timestamp, str):
                            try:
                                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            except:
                                timestamp = None

                        adsb_data = ADS_BData(
                            icao24=str(item.get("icao24", "")),
                            callsign=item.get("callsign"),
                            origin_country=item.get("origin_country"),
                            longitude=item.get("longitude"),
                            latitude=item.get("latitude"),
                            altitude=item.get("altitude"),
                            velocity=item.get("velocity"),
                            heading=item.get("heading"),
                            vertical_rate=item.get("vertical_rate"),
                            squawk=item.get("squawk"),
                            on_ground=item.get("on_ground"),
                            aircraft_type=item.get("aircraft_type"),
                            registration=item.get("registration"),
                            timestamp=timestamp,
                            source=item.get("source")
                        )
                        adsb_data_list.append(adsb_data)
                    except Exception as e:
                        logger.warning(f"解析ADS-B数据项失败: {e}")
        elif isinstance(data, dict):
            # 单个航空器数据
            try:
                timestamp = data.get("timestamp")
                if timestamp and isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        timestamp = None

                adsb_data = ADS_BData(
                    icao24=str(data.get("icao24", "")),
                    callsign=data.get("callsign"),
                    origin_country=data.get("origin_country"),
                    longitude=data.get("longitude"),
                    latitude=data.get("latitude"),
                    altitude=data.get("altitude"),
                    velocity=data.get("velocity"),
                    heading=data.get("heading"),
                    vertical_rate=data.get("vertical_rate"),
                    squawk=data.get("squawk"),
                    on_ground=data.get("on_ground"),
                    aircraft_type=data.get("aircraft_type"),
                    registration=data.get("registration"),
                    timestamp=timestamp,
                    source=data.get("source")
                )
                adsb_data_list.append(adsb_data)
            except Exception as e:
                logger.warning(f"解析ADS-B数据失败: {e}")

        logger.info(f"解析了 {len(adsb_data_list)} 条ADS-B数据记录")
        return adsb_data_list

    async def _detect_anomalies(self, adsb_data_list: List[ADS_BData], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测异常活动"""
        anomalies = []

        for adsb_data in adsb_data_list:
            # 检查应答机代码异常
            if adsb_data.squawk:
                if adsb_data.squawk in ["7500", "7600", "7700"]:  # 紧急代码
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "emergency_squawk",
                        "description": f"航空器使用紧急应答机代码: {adsb_data.squawk}",
                        "severity": "critical"
                    })
                elif adsb_data.squawk == "0000":  # 军事行动
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "military_squawk",
                        "description": "航空器使用军事应答机代码: 0000",
                        "severity": "high"
                    })

            # 检查高度异常
            if adsb_data.altitude is not None:
                if adsb_data.altitude < 100:  # 异常低空飞行
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "low_altitude",
                        "description": f"异常低空飞行 (高度: {adsb_data.altitude}米)",
                        "severity": "medium"
                    })
                elif adsb_data.altitude > 13000 and adsb_data.aircraft_type == "general_aviation":  # 通用航空异常高空
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "high_altitude",
                        "description": f"通用航空器异常高空飞行 (高度: {adsb_data.altitude}米)",
                        "severity": "medium"
                    })

            # 检查速度异常
            if adsb_data.velocity is not None:
                if adsb_data.velocity == 0 and not adsb_data.on_ground:  # 空中停滞
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "airborne_stagnation",
                        "description": "航空器在空中停滞",
                        "severity": "high"
                    })

            # 检查呼号异常
            if adsb_data.callsign:
                if adsb_data.callsign.startswith("SPAR"):  # 美国军事训练
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "military_training",
                        "description": f"军事训练呼号: {adsb_data.callsign}",
                        "severity": "medium"
                    })
                elif adsb_data.callsign.startswith("REACH"):  # 美国空军运输
                    anomalies.append({
                        "icao24": adsb_data.icao24,
                        "callsign": adsb_data.callsign,
                        "type": "military_transport",
                        "description": f"军事运输呼号: {adsb_data.callsign}",
                        "severity": "medium"
                    })

            # 检查来源国异常
            if adsb_data.origin_country and adsb_data.origin_country in self._sensitive_countries:
                anomalies.append({
                    "icao24": adsb_data.icao24,
                    "callsign": adsb_data.callsign,
                    "type": "sensitive_country",
                    "description": f"航空器来自敏感国家: {adsb_data.origin_country}",
                    "severity": "high"
                })

        return anomalies

    async def _detect_high_risk_aircraft(self, adsb_data_list: List[ADS_BData]) -> List[Dict[str, Any]]:
        """检测高风险航空器"""
        high_risk_aircraft = []

        for adsb_data in adsb_data_list:
            risk_factors = []

            # 未知/模糊身份
            if not adsb_data.callsign or adsb_data.callsign.strip() in ["", "UNKNOWN", "N/A"]:
                risk_factors.append("身份不明")

            # 军事或政府航空器
            if adsb_data.aircraft_type in self._high_risk_aircraft_types:
                risk_factors.append(f"高风险航空器类型: {adsb_data.aircraft_type}")

            # 敏感国家
            if adsb_data.origin_country in self._sensitive_countries:
                risk_factors.append(f"敏感国家: {adsb_data.origin_country}")

            # 应答机代码异常
            if adsb_data.squawk in ["0000", "7500", "7600", "7700"]:
                risk_factors.append(f"异常应答机代码: {adsb_data.squawk}")

            if risk_factors:
                high_risk_aircraft.append({
                    "icao24": adsb_data.icao24,
                    "callsign": adsb_data.callsign,
                    "aircraft_type": adsb_data.aircraft_type,
                    "risk_factors": risk_factors,
                    "risk_score": len(risk_factors) * 25,  # 简单评分
                    "current_position": {
                        "latitude": adsb_data.latitude,
                        "longitude": adsb_data.longitude,
                        "altitude": adsb_data.altitude
                    } if adsb_data.latitude and adsb_data.longitude else None
                })

        return high_risk_aircraft

    async def _detect_airspace_violations(self, adsb_data_list: List[ADS_BData]) -> List[Dict[str, Any]]:
        """检测空域侵犯"""
        violations = []

        for adsb_data in adsb_data_list:
            if adsb_data.latitude and adsb_data.longitude:
                for no_fly_zone in self._no_fly_zones:
                    if self._is_in_no_fly_zone(adsb_data.latitude, adsb_data.longitude, no_fly_zone):
                        violations.append({
                            "icao24": adsb_data.icao24,
                            "callsign": adsb_data.callsign,
                            "type": "no_fly_zone_violation",
                            "description": f"侵犯禁飞区: {no_fly_zone.get('name', '未知')}",
                            "severity": "critical",
                            "zone": no_fly_zone.get("name"),
                            "position": {
                                "latitude": adsb_data.latitude,
                                "longitude": adsb_data.longitude,
                                "altitude": adsb_data.altitude
                            }
                        })

        return violations

    async def _analyze_pattern_changes(self, adsb_data_list: List[ADS_BData]) -> List[Dict[str, Any]]:
        """分析飞行模式变化"""
        # 简化实现：基于当前位置和历史模式对比
        pattern_changes = []
        return pattern_changes

    async def _analyze_with_llm(self, adsb_data_list: List[ADS_BData], anomalies: List[Dict[str, Any]],
                               high_risk_aircraft: List[Dict[str, Any]], airspace_violations: List[Dict[str, Any]],
                               context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM进行综合分析"""
        try:
            # 准备分析数据
            analysis_data = {
                "aircraft_count": len(adsb_data_list),
                "anomalies_count": len(anomalies),
                "high_risk_aircraft_count": len(high_risk_aircraft),
                "airspace_violations_count": len(airspace_violations),
                "sample_aircraft": adsb_data_list[:5],  # 采样前5架
                "sample_anomalies": anomalies[:3],  # 采样前3个异常
                "sample_violations": airspace_violations[:3],  # 采样前3个侵犯
                "geographic_focus": context.get("region") if context else "全球",
                "analysis_timeframe": context.get("timeframe") if context else "实时"
            }

            prompt = f"""
作为航空安全和地缘政治分析专家，请分析以下ADS-B数据：

数据摘要:
- 航空器总数: {analysis_data['aircraft_count']}
- 异常活动数: {analysis_data['anomalies_count']}
- 高风险航空器数: {analysis_data['high_risk_aircraft_count']}
- 空域侵犯数: {analysis_data['airspace_violations_count']}
- 分析区域: {analysis_data['geographic_focus']}
- 时间范围: {analysis_data['analysis_timeframe']}

详细数据:
{json.dumps(analysis_data, indent=2, default=str)}

请提供:
1. 关键洞察（3-5条）
2. 风险评估（low/medium/high/critical）
3. 建议措施（3-5条）
4. 潜在的地缘政治影响
5. 需要关注的特定航空器或空域

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
                system_prompt="你是航空安全和地缘政治分析专家，擅长从ADS-B数据中识别潜在威胁和异常模式。",
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

    def _is_in_no_fly_zone(self, latitude: float, longitude: float, no_fly_zone: Dict[str, Any]) -> bool:
        """检查是否在禁飞区"""
        zone_type = no_fly_zone.get("type", "circle")

        if zone_type == "circle":
            center_lat = no_fly_zone.get("center_lat", 0)
            center_lon = no_fly_zone.get("center_lon", 0)
            radius_km = no_fly_zone.get("radius_km", 0)

            # 简化距离计算（Haversine公式的近似）
            distance = self._calculate_distance(latitude, longitude, center_lat, center_lon)
            return distance <= radius_km

        elif zone_type == "polygon":
            polygon = no_fly_zone.get("coordinates", [])
            return self._is_point_in_polygon(latitude, longitude, polygon)

        return False

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间距离（公里）"""
        # 简化实现，实际应使用Haversine公式
        return abs(lat1 - lat2) * 111 + abs(lon1 - lon2) * 111 * abs(lat1 / 90)

    def _is_point_in_polygon(self, lat: float, lon: float, polygon: List[List[float]]) -> bool:
        """判断点是否在多边形内（射线法）"""
        # 简化实现，返回False
        return False

    def _escalate_risk(self, current_risk: str, new_risk: str) -> str:
        """升级风险等级"""
        risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 0}
        current_level = risk_levels.get(current_risk, 0)
        new_level = risk_levels.get(new_risk, 0)
        return new_risk if new_level > current_level else current_risk

    def _determine_geographic_scope(self, adsb_data_list: List[ADS_BData]) -> List[str]:
        """确定地理范围"""
        regions = set()

        for adsb_data in adsb_data_list:
            if adsb_data.latitude and adsb_data.longitude:
                # 简单区域判断
                if 20 <= adsb_data.latitude <= 50 and 100 <= adsb_data.longitude <= 140:
                    regions.add("东亚")
                elif 30 <= adsb_data.latitude <= 50 and -10 <= adsb_data.longitude <= 40:
                    regions.add("欧洲")
                elif 10 <= adsb_data.latitude <= 40 and 30 <= adsb_data.longitude <= 60:
                    regions.add("中东")
                elif 25 <= adsb_data.latitude <= 50 and -130 <= adsb_data.longitude <= -60:
                    regions.add("北美")
                # 添加更多区域判断...

        return list(regions) if regions else ["全球"]

    def _calculate_confidence(self, adsb_data_list: List[ADS_BData], anomaly_count: int, violation_count: int) -> float:
        """计算分析置信度"""
        if not adsb_data_list:
            return 0.0

        # 基于数据量和异常数量计算置信度
        data_confidence = min(len(adsb_data_list) / 100, 1.0)  # 最多100条数据达到最大置信度
        anomaly_confidence = min(anomaly_count / 10, 1.0) if anomaly_count > 0 else 0.5
        violation_confidence = min(violation_count / 5, 1.0) if violation_count > 0 else 0.3

        # 加权平均
        return 0.5 * data_confidence + 0.3 * anomaly_confidence + 0.2 * violation_confidence

    def _calculate_impact_score(self, anomalies: List[Dict[str, Any]],
                               high_risk_aircraft: List[Dict[str, Any]],
                               airspace_violations: List[Dict[str, Any]]) -> float:
        """计算影响评分（0-10）"""
        score = 0.0

        # 异常活动贡献
        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            if severity == "critical":
                score += 3.0
            elif severity == "high":
                score += 2.0
            elif severity == "medium":
                score += 1.0
            else:
                score += 0.5

        # 高风险航空器贡献
        score += len(high_risk_aircraft) * 2.0

        # 空域侵犯贡献（非常严重）
        score += len(airspace_violations) * 4.0

        return min(score, 10.0)

    def _generate_timeline(self, adsb_data_list: List[ADS_BData], anomalies: List[Dict[str, Any]],
                          airspace_violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成时间线预测"""
        timeline = {
            "events": [],
            "trends": [],
            "milestones": []
        }

        # 基于异常预测未来事件
        for anomaly in anomalies[:3]:  # 前3个异常
            timeline["events"].append({
                "id": f"event_{anomaly.get('icao24', 'unknown')}_{datetime.now().timestamp()}",
                "type": anomaly.get("type", "unknown"),
                "description": anomaly.get("description", ""),
                "predicted_time": (datetime.now() + timedelta(hours=3)).isoformat(),
                "confidence": 0.6
            })

        # 基于空域侵犯预测
        for violation in airspace_violations[:2]:  # 前2个侵犯
            timeline["events"].append({
                "id": f"violation_{violation.get('icao24', 'unknown')}_{datetime.now().timestamp()}",
                "type": "airspace_violation",
                "description": violation.get("description", ""),
                "predicted_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "confidence": 0.8
            })

        # 添加趋势预测
        if len(anomalies) > 5 or len(airspace_violations) > 0:
            timeline["trends"].append({
                "id": "trend_increased_aviation_risk",
                "description": "航空风险呈上升趋势",
                "timeframe": "未来12小时",
                "direction": "increasing"
            })

        return timeline

    async def analyze_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析文本数据（航空相关报告）"""
        return AnalysisResult(
            data={"text": text},
            confidence=0.8,
            insights=["文本分析功能待实现"],
            risk_level="low"
        )

    async def analyze_geospatial(self, geospatial_data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析地理空间数据"""
        return AnalysisResult(
            data={"geospatial": geospatial_data},
            confidence=0.8,
            insights=["地理空间分析功能待实现"],
            risk_level="low"
        )

    async def analyze_temporal(self, temporal_data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析时间序列数据"""
        return AnalysisResult(
            data={"temporal": temporal_data},
            confidence=0.8,
            insights=["时间序列分析功能待实现"],
            risk_level="low"
        )