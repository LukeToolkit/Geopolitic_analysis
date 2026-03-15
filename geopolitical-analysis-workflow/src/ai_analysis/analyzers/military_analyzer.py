"""
军事部署分析器
分析军事部署、演习和装备移动数据，评估地缘政治风险
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
class MilitaryUnit:
    """军事单位"""
    unit_id: str
    unit_type: str  # army, navy, air_force, missile, special_forces
    country: str
    location: Optional[Dict[str, float]] = None  # {latitude, longitude}
    strength: Optional[int] = None  # 人员数量
    equipment: Optional[List[str]] = None  # 装备列表
    readiness_level: str = "normal"  # normal, elevated, high, maximum
    movement_status: str = "stationary"  # stationary, moving, deployed
    last_update: Optional[datetime] = None


@dataclass
class MilitaryExercise:
    """军事演习"""
    exercise_id: str
    name: str
    participating_countries: List[str]
    location: Dict[str, Any]
    start_date: datetime
    end_date: datetime
    exercise_type: str  # joint, naval, air, ground, nuclear
    scale: str  # small, medium, large, massive
    objectives: List[str]


@dataclass
class MilitaryDeployment:
    """军事部署"""
    deployment_id: str
    unit_id: str
    from_location: Dict[str, float]
    to_location: Dict[str, float]
    start_time: datetime
    estimated_arrival: datetime
    purpose: str  # routine, reinforcement, deterrent, offensive
    visibility: str  # public, discreet, covert


class MilitaryAnalyzer(BaseAnalyzer):
    """军事部署分析器"""

    def __init__(self, config: AnalyzerConfig):
        super().__init__(config)
        self.config.processor_type = "military_analyzer"
        self._historical_deployments: List[MilitaryDeployment] = []
        self._current_exercises: List[MilitaryExercise] = []
        self._flashpoints: List[Dict[str, Any]] = []  # 潜在冲突点
        self._alliances: Dict[str, List[str]] = {}  # 军事联盟
        self._capability_assessments: Dict[str, Dict[str, Any]] = {}  # 国家军事能力评估

    async def analyze(self, data: Any, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析军事部署数据"""
        try:
            self.logger.info(f"开始分析军事部署数据: {self.name}")

            # 解析数据
            military_data = self._parse_military_data(data)
            if not military_data.get("units") and not military_data.get("exercises") and not military_data.get("deployments"):
                return AnalysisResult(
                    data={},
                    confidence=0.0,
                    insights=["无有效的军事部署数据可供分析"],
                    risk_level="low"
                )

            # 检测异常军事活动
            anomalies = await self._detect_anomalies(military_data, context)

            # 评估冲突风险
            conflict_risks = await self._assess_conflict_risks(military_data, context)

            # 分析军事态势变化
            posture_changes = await self._analyze_posture_changes(military_data)

            # 评估军事平衡
            balance_assessment = await self._assess_military_balance(military_data, context)

            # 使用LLM进行综合分析
            llm_analysis = await self._analyze_with_llm(military_data, anomalies, conflict_risks, posture_changes, context)

            # 合并结果
            insights = []
            recommendations = []
            risk_level = "low"

            if anomalies:
                insights.append(f"检测到 {len(anomalies)} 个异常军事活动")
                risk_level = self._escalate_risk(risk_level, "medium")

            if conflict_risks:
                highest_risk = max([r.get("risk_level", "low") for r in conflict_risks],
                                 key=lambda x: self._risk_level_to_value(x))
                insights.append(f"评估了 {len(conflict_risks)} 个冲突风险点，最高风险: {highest_risk}")
                risk_level = self._escalate_risk(risk_level, highest_risk)

            if posture_changes:
                insights.append(f"检测到 {len(posture_changes)} 个军事态势变化")
                risk_level = self._escalate_risk(risk_level, "medium")

            if balance_assessment.get("imbalance_detected", False):
                insights.append(f"检测到军事力量失衡: {balance_assessment.get('imbalance_type', '未知')}")
                risk_level = self._escalate_risk(risk_level, "high")

            if llm_analysis.get("insights"):
                insights.extend(llm_analysis["insights"])
                risk_level = self._escalate_risk(risk_level, llm_analysis.get("risk_level", "low"))

            if llm_analysis.get("recommendations"):
                recommendations.extend(llm_analysis["recommendations"])

            # 确定地理范围
            geographic_scope = self._determine_geographic_scope(military_data)

            # 计算置信度
            confidence = self._calculate_confidence(military_data, len(anomalies), len(conflict_risks))

            # 计算影响评分
            impact_score = self._calculate_impact_score(anomalies, conflict_risks, posture_changes, balance_assessment)

            # 生成时间线预测
            timeline = self._generate_timeline(military_data, anomalies, conflict_risks)

            return AnalysisResult(
                data={
                    "units_analyzed": len(military_data.get("units", [])),
                    "exercises_analyzed": len(military_data.get("exercises", [])),
                    "deployments_analyzed": len(military_data.get("deployments", [])),
                    "anomalies": anomalies,
                    "conflict_risks": conflict_risks,
                    "posture_changes": posture_changes,
                    "balance_assessment": balance_assessment,
                    "geographic_scope": geographic_scope
                },
                confidence=confidence,
                insights=insights,
                recommendations=recommendations,
                risk_level=risk_level,
                impact_score=impact_score,
                geographic_scope=geographic_scope,
                timeline=timeline,
                metadata={
                    "analyzer": self.name,
                    "data_source": "military_intelligence",
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "data_classification": "confidential"
                }
            )

        except Exception as e:
            logger.error(f"军事部署分析失败: {str(e)}", exc_info=True)
            return AnalysisResult(
                data=data,
                confidence=0.0,
                errors=[f"军事部署分析失败: {str(e)}"],
                risk_level="unknown"
            )

    def _parse_military_data(self, data: Any) -> Dict[str, Any]:
        """解析军事部署数据"""
        result = {
            "units": [],
            "exercises": [],
            "deployments": []
        }

        if isinstance(data, dict):
            # 直接包含军事数据
            if "units" in data and isinstance(data["units"], list):
                for unit_data in data["units"]:
                    try:
                        unit = MilitaryUnit(
                            unit_id=str(unit_data.get("unit_id", "")),
                            unit_type=unit_data.get("unit_type", "unknown"),
                            country=unit_data.get("country", "unknown"),
                            location=unit_data.get("location"),
                            strength=unit_data.get("strength"),
                            equipment=unit_data.get("equipment", []),
                            readiness_level=unit_data.get("readiness_level", "normal"),
                            movement_status=unit_data.get("movement_status", "stationary"),
                            last_update=unit_data.get("last_update")
                        )
                        result["units"].append(unit)
                    except Exception as e:
                        logger.warning(f"解析军事单位失败: {e}")

            if "exercises" in data and isinstance(data["exercises"], list):
                for exercise_data in data["exercises"]:
                    try:
                        # 处理日期
                        start_date = exercise_data.get("start_date")
                        end_date = exercise_data.get("end_date")
                        if isinstance(start_date, str):
                            try:
                                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                            except:
                                start_date = None
                        if isinstance(end_date, str):
                            try:
                                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            except:
                                end_date = None

                        exercise = MilitaryExercise(
                            exercise_id=str(exercise_data.get("exercise_id", "")),
                            name=exercise_data.get("name", ""),
                            participating_countries=exercise_data.get("participating_countries", []),
                            location=exercise_data.get("location", {}),
                            start_date=start_date,
                            end_date=end_date,
                            exercise_type=exercise_data.get("exercise_type", "joint"),
                            scale=exercise_data.get("scale", "medium"),
                            objectives=exercise_data.get("objectives", [])
                        )
                        result["exercises"].append(exercise)
                    except Exception as e:
                        logger.warning(f"解析军事演习失败: {e}")

            if "deployments" in data and isinstance(data["deployments"], list):
                for deployment_data in data["deployments"]:
                    try:
                        # 处理日期
                        start_time = deployment_data.get("start_time")
                        estimated_arrival = deployment_data.get("estimated_arrival")
                        if isinstance(start_time, str):
                            try:
                                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            except:
                                start_time = None
                        if isinstance(estimated_arrival, str):
                            try:
                                estimated_arrival = datetime.fromisoformat(estimated_arrival.replace('Z', '+00:00'))
                            except:
                                estimated_arrival = None

                        deployment = MilitaryDeployment(
                            deployment_id=str(deployment_data.get("deployment_id", "")),
                            unit_id=str(deployment_data.get("unit_id", "")),
                            from_location=deployment_data.get("from_location", {}),
                            to_location=deployment_data.get("to_location", {}),
                            start_time=start_time,
                            estimated_arrival=estimated_arrival,
                            purpose=deployment_data.get("purpose", "routine"),
                            visibility=deployment_data.get("visibility", "public")
                        )
                        result["deployments"].append(deployment)
                    except Exception as e:
                        logger.warning(f"解析军事部署失败: {e}")

        logger.info(f"解析军事数据: {len(result['units'])} 个单位, {len(result['exercises'])} 个演习, {len(result['deployments'])} 个部署")
        return result

    async def _detect_anomalies(self, military_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测异常军事活动"""
        anomalies = []

        # 检查异常部署
        for deployment in military_data.get("deployments", []):
            # 检查突然性部署
            if deployment.purpose in ["deterrent", "offensive"] and deployment.visibility == "discreet":
                anomalies.append({
                    "type": "covert_deployment",
                    "description": f"检测到隐蔽军事部署: {deployment.unit_id}",
                    "severity": "high",
                    "deployment_id": deployment.deployment_id,
                    "from_country": self._get_country_from_location(deployment.from_location),
                    "to_region": self._get_region_from_location(deployment.to_location)
                })

            # 检查向热点区域部署
            to_region = self._get_region_from_location(deployment.to_location)
            if self._is_flashpoint_region(to_region):
                anomalies.append({
                    "type": "deployment_to_flashpoint",
                    "description": f"军事部署至热点区域: {to_region}",
                    "severity": "high",
                    "deployment_id": deployment.deployment_id,
                    "region": to_region
                })

        # 检查异常演习
        for exercise in military_data.get("exercises", []):
            # 检查突然宣布的演习
            days_until_start = (exercise.start_date - datetime.now()).days if exercise.start_date else 999
            if days_until_start < 3:  # 3天内开始的演习
                anomalies.append({
                    "type": "short_notice_exercise",
                    "description": f"短时间通知的军事演习: {exercise.name}",
                    "severity": "medium",
                    "exercise_id": exercise.exercise_id,
                    "countries": exercise.participating_countries
                })

            # 检查涉及对立国家的演习
            if self._involves_adversarial_countries(exercise.participating_countries):
                anomalies.append({
                    "type": "adversarial_exercise",
                    "description": f"涉及对立国家的联合演习: {exercise.name}",
                    "severity": "high",
                    "exercise_id": exercise.exercise_id,
                    "countries": exercise.participating_countries
                })

            # 检查核演习
            if exercise.exercise_type == "nuclear":
                anomalies.append({
                    "type": "nuclear_exercise",
                    "description": f"核军事演习: {exercise.name}",
                    "severity": "critical",
                    "exercise_id": exercise.exercise_id,
                    "countries": exercise.participating_countries
                })

        # 检查战备等级提升
        for unit in military_data.get("units", []):
            if unit.readiness_level in ["high", "maximum"]:
                anomalies.append({
                    "type": "elevated_readiness",
                    "description": f"部队战备等级提升: {unit.unit_id} ({unit.readiness_level})",
                    "severity": "medium",
                    "unit_id": unit.unit_id,
                    "country": unit.country,
                    "readiness_level": unit.readiness_level
                })

        return anomalies

    async def _assess_conflict_risks(self, military_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """评估冲突风险"""
        conflict_risks = []

        # 分析热点区域的军事存在
        flashpoint_assessments = self._assess_flashpoints(military_data)
        conflict_risks.extend(flashpoint_assessments)

        # 分析部队对峙
        confrontation_risks = self._assess_confrontations(military_data)
        conflict_risks.extend(confrontation_risks)

        # 分析历史冲突模式
        historical_risks = await self._assess_historical_patterns(military_data)
        conflict_risks.extend(historical_risks)

        return conflict_risks

    async def _analyze_posture_changes(self, military_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析军事态势变化"""
        posture_changes = []

        # 这里需要历史数据对比
        # 简化实现：基于当前数据推断变化

        # 检查部队移动
        moving_units = [u for u in military_data.get("units", []) if u.movement_status == "moving"]
        if moving_units:
            posture_changes.append({
                "type": "troop_movement",
                "description": f"检测到 {len(moving_units)} 支部队在移动",
                "units_affected": len(moving_units),
                "countries": list(set([u.country for u in moving_units]))
            })

        # 检查演习活动
        active_exercises = [e for e in military_data.get("exercises", [])
                          if e.start_date and e.end_date and e.start_date <= datetime.now() <= e.end_date]
        if active_exercises:
            posture_changes.append({
                "type": "active_exercises",
                "description": f"正在进行 {len(active_exercises)} 个军事演习",
                "exercises": [e.name for e in active_exercises],
                "countries": list(set([c for e in active_exercises for c in e.participating_countries]))
            })

        return posture_changes

    async def _assess_military_balance(self, military_data: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """评估军事平衡"""
        assessment = {
            "imbalance_detected": False,
            "imbalance_type": None,
            "affected_regions": [],
            "assessment": "stable"
        }

        # 按地区分析军事力量
        regional_balance = self._analyze_regional_balance(military_data)

        # 检测重大失衡
        for region, balance in regional_balance.items():
            if balance.get("imbalance_score", 0) > 0.7:  # 失衡阈值
                assessment["imbalance_detected"] = True
                assessment["imbalance_type"] = balance.get("imbalance_type")
                assessment["affected_regions"].append(region)

        if assessment["imbalance_detected"]:
            assessment["assessment"] = "unstable"
        elif any(b.get("imbalance_score", 0) > 0.4 for b in regional_balance.values()):
            assessment["assessment"] = "concerning"
        else:
            assessment["assessment"] = "stable"

        return assessment

    async def _analyze_with_llm(self, military_data: Dict[str, Any], anomalies: List[Dict[str, Any]],
                               conflict_risks: List[Dict[str, Any]], posture_changes: List[Dict[str, Any]],
                               context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM进行综合分析"""
        try:
            # 准备分析数据
            analysis_data = {
                "units_count": len(military_data.get("units", [])),
                "exercises_count": len(military_data.get("exercises", [])),
                "deployments_count": len(military_data.get("deployments", [])),
                "anomalies_count": len(anomalies),
                "conflict_risks_count": len(conflict_risks),
                "posture_changes_count": len(posture_changes),
                "sample_anomalies": anomalies[:3],
                "sample_conflict_risks": conflict_risks[:3],
                "geographic_focus": context.get("region") if context else "全球",
                "analysis_timeframe": context.get("timeframe") if context else "实时",
                "data_classification": "confidential"
            }

            prompt = f"""
作为军事战略和地缘政治分析专家，请分析以下军事部署数据：

数据摘要（机密）:
- 军事单位数量: {analysis_data['units_count']}
- 军事演习数量: {analysis_data['exercises_count']}
- 军事部署数量: {analysis_data['deployments_count']}
- 异常活动数: {analysis_data['anomalies_count']}
- 冲突风险点数: {analysis_data['conflict_risks_count']}
- 态势变化数: {analysis_data['posture_changes_count']}
- 分析区域: {analysis_data['geographic_focus']}
- 时间范围: {analysis_data['analysis_timeframe']}

详细数据（节选）:
{json.dumps(analysis_data, indent=2, default=str)}

请提供专业的军事战略分析:
1. 关键洞察（3-5条，关注战略意义）
2. 风险评估（low/medium/high/critical）
3. 战略建议（3-5条，针对决策者）
4. 潜在的地缘政治后果
5. 需要监控的特定军事活动

请用JSON格式回复，包含以下字段:
- insights: 字符串列表
- risk_level: 字符串
- recommendations: 字符串列表
- geopolitical_consequences: 字符串
- activities_to_monitor: 字符串列表
"""

            result = await LLMManager.generate_structured(
                prompt=prompt,
                output_schema={
                    "insights": ["string"],
                    "risk_level": "string",
                    "recommendations": ["string"],
                    "geopolitical_consequences": "string",
                    "activities_to_monitor": ["string"]
                },
                system_prompt="你是军事战略和地缘政治分析专家，拥有高级安全许可。你擅长从军事部署数据中识别战略意图、评估冲突风险并提供决策建议。保持专业、客观、战略性的分析视角。",
                model=LLMModel.CLAUDE_3_SONNET,
                provider=LLMProvider.ANTHROPIC,
                temperature=0.1,
                max_tokens=2500
            )

            return result

        except Exception as e:
            logger.error(f"LLM分析失败: {str(e)}")
            return {
                "insights": ["LLM分析暂时不可用"],
                "risk_level": "unknown",
                "recommendations": ["检查LLM配置"],
                "geopolitical_consequences": "无法评估",
                "activities_to_monitor": []
            }

    def _assess_flashpoints(self, military_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估热点区域"""
        flashpoint_risks = []

        for flashpoint in self._flashpoints:
            region = flashpoint.get("region", "")
            countries_involved = flashpoint.get("countries", [])
            historical_tensions = flashpoint.get("tension_level", "medium")

            # 检查该区域的军事存在
            units_in_region = self._get_units_in_region(military_data.get("units", []), region)
            exercises_in_region = self._get_exercises_in_region(military_data.get("exercises", []), region)

            if units_in_region or exercises_in_region:
                risk_score = self._calculate_flashpoint_risk(units_in_region, exercises_in_region, historical_tensions)

                flashpoint_risks.append({
                    "region": region,
                    "type": "flashpoint_risk",
                    "description": f"热点区域军事活动: {region}",
                    "risk_level": self._score_to_risk_level(risk_score),
                    "risk_score": risk_score,
                    "units_count": len(units_in_region),
                    "exercises_count": len(exercises_in_region),
                    "countries_involved": countries_involved
                })

        return flashpoint_risks

    def _assess_confrontations(self, military_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估部队对峙风险"""
        confrontations = []

        # 按地区和国家分组部队
        regional_forces = {}
        for unit in military_data.get("units", []):
            region = self._get_region_from_location(unit.location) if unit.location else "unknown"
            if region not in regional_forces:
                regional_forces[region] = {}
            if unit.country not in regional_forces[region]:
                regional_forces[region][unit.country] = []
            regional_forces[region][unit.country].append(unit)

        # 检查同一区域内的多国部队
        for region, country_forces in regional_forces.items():
            if len(country_forces) > 1:
                # 多个国家在同一区域有部队
                countries = list(country_forces.keys())
                if self._are_countries_adversarial(countries):
                    total_units = sum(len(units) for units in country_forces.values())
                    confrontations.append({
                        "region": region,
                        "type": "potential_confrontation",
                        "description": f"对立国家在 {region} 区域均有军事存在",
                        "risk_level": "high",
                        "countries_involved": countries,
                        "total_units": total_units
                    })

        return confrontations

    async def _assess_historical_patterns(self, military_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估历史冲突模式"""
        # 简化实现：基于已知历史模式
        historical_risks = []
        return historical_risks

    def _analyze_regional_balance(self, military_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """分析地区军事平衡"""
        regional_balance = {}

        # 按地区分析
        for unit in military_data.get("units", []):
            region = self._get_region_from_location(unit.location) if unit.location else "global"
            if region not in regional_balance:
                regional_balance[region] = {
                    "countries": {},
                    "total_units": 0,
                    "imbalance_score": 0.0,
                    "imbalance_type": None
                }

            if unit.country not in regional_balance[region]["countries"]:
                regional_balance[region]["countries"][unit.country] = 0

            regional_balance[region]["countries"][unit.country] += 1
            regional_balance[region]["total_units"] += 1

        # 计算每个地区的平衡度
        for region, data in regional_balance.items():
            if len(data["countries"]) >= 2:
                # 计算赫芬达尔-赫希曼指数（HHI）来衡量集中度
                total_units = data["total_units"]
                if total_units > 0:
                    hhi = sum((count / total_units) ** 2 for count in data["countries"].values())
                    # HHI接近1表示高度集中，接近0表示分散
                    imbalance_score = abs(hhi - 0.5) * 2  # 标准化到0-1
                    data["imbalance_score"] = imbalance_score

                    if imbalance_score > 0.7:
                        dominant_country = max(data["countries"].items(), key=lambda x: x[1])[0]
                        data["imbalance_type"] = f"{dominant_country} dominance"

        return regional_balance

    def _get_country_from_location(self, location: Optional[Dict[str, float]]) -> str:
        """从位置获取国家（简化）"""
        if not location:
            return "unknown"
        # 这里应调用地理编码服务，简化实现
        return "unknown"

    def _get_region_from_location(self, location: Optional[Dict[str, float]]) -> str:
        """从位置获取地区"""
        if not location or "latitude" not in location or "longitude" not in location:
            return "global"

        lat = location["latitude"]
        lon = location["longitude"]

        if 20 <= lat <= 50 and 100 <= lon <= 140:
            return "east_asia"
        elif 30 <= lat <= 50 and -10 <= lon <= 40:
            return "europe"
        elif 10 <= lat <= 40 and 30 <= lon <= 60:
            return "middle_east"
        elif 25 <= lat <= 50 and -130 <= lon <= -60:
            return "north_america"
        else:
            return "other"

    def _is_flashpoint_region(self, region: str) -> bool:
        """检查是否为热点区域"""
        flashpoint_regions = ["east_asia_south_china_sea", "europe_ukraine", "middle_east_persian_gulf"]
        return region in flashpoint_regions

    def _involves_adversarial_countries(self, countries: List[str]) -> bool:
        """检查是否涉及对立国家"""
        adversarial_pairs = [("US", "Russia"), ("US", "China"), ("India", "Pakistan"), ("Israel", "Iran")]
        for country1, country2 in adversarial_pairs:
            if country1 in countries and country2 in countries:
                return True
        return False

    def _are_countries_adversarial(self, countries: List[str]) -> bool:
        """检查国家是否对立"""
        return self._involves_adversarial_countries(countries)

    def _get_units_in_region(self, units: List[MilitaryUnit], region: str) -> List[MilitaryUnit]:
        """获取指定区域的部队"""
        return [u for u in units if self._get_region_from_location(u.location) == region]

    def _get_exercises_in_region(self, exercises: List[MilitaryExercise], region: str) -> List[MilitaryExercise]:
        """获取指定区域的演习"""
        # 简化实现：检查演习位置是否匹配区域
        return exercises  # 实际应基于位置过滤

    def _calculate_flashpoint_risk(self, units: List[MilitaryUnit], exercises: List[MilitaryExercise], historical_tension: str) -> float:
        """计算热点区域风险评分"""
        risk_score = 0.0

        # 部队数量贡献
        risk_score += min(len(units) / 10, 1.0) * 0.4

        # 演习贡献
        risk_score += min(len(exercises) / 5, 1.0) * 0.3

        # 历史紧张程度贡献
        tension_scores = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 0.9}
        risk_score += tension_scores.get(historical_tension, 0.3) * 0.3

        return min(risk_score, 1.0)

    def _score_to_risk_level(self, score: float) -> str:
        """评分转换为风险等级"""
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"

    def _risk_level_to_value(self, risk_level: str) -> int:
        """风险等级转换为数值"""
        levels = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return levels.get(risk_level, 0)

    def _escalate_risk(self, current_risk: str, new_risk: str) -> str:
        """升级风险等级"""
        current_value = self._risk_level_to_value(current_risk)
        new_value = self._risk_level_to_value(new_risk)
        return new_risk if new_value > current_value else current_risk

    def _determine_geographic_scope(self, military_data: Dict[str, Any]) -> List[str]:
        """确定地理范围"""
        regions = set()

        # 从部队位置获取地区
        for unit in military_data.get("units", []):
            if unit.location:
                region = self._get_region_from_location(unit.location)
                if region != "global" and region != "other":
                    regions.add(region)

        # 从演习位置获取地区
        for exercise in military_data.get("exercises", []):
            if "region" in exercise.location:
                regions.add(exercise.location["region"])

        return list(regions) if regions else ["global"]

    def _calculate_confidence(self, military_data: Dict[str, Any], anomaly_count: int, conflict_risk_count: int) -> float:
        """计算分析置信度"""
        total_units = len(military_data.get("units", []))
        total_exercises = len(military_data.get("exercises", []))
        total_deployments = len(military_data.get("deployments", []))

        if total_units + total_exercises + total_deployments == 0:
            return 0.0

        # 数据量置信度
        data_confidence = min((total_units + total_exercises * 5 + total_deployments * 3) / 50, 1.0)

        # 异常检测置信度
        anomaly_confidence = min(anomaly_count / 10, 1.0) if anomaly_count > 0 else 0.5

        # 冲突风险评估置信度
        risk_confidence = min(conflict_risk_count / 5, 1.0) if conflict_risk_count > 0 else 0.3

        # 加权平均
        return 0.4 * data_confidence + 0.4 * anomaly_confidence + 0.2 * risk_confidence

    def _calculate_impact_score(self, anomalies: List[Dict[str, Any]], conflict_risks: List[Dict[str, Any]],
                               posture_changes: List[Dict[str, Any]], balance_assessment: Dict[str, Any]) -> float:
        """计算影响评分（0-10）"""
        score = 0.0

        # 异常活动贡献
        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            if severity == "critical":
                score += 4.0
            elif severity == "high":
                score += 2.5
            elif severity == "medium":
                score += 1.5
            else:
                score += 0.5

        # 冲突风险贡献
        for risk in conflict_risks:
            risk_level = risk.get("risk_level", "low")
            if risk_level == "critical":
                score += 5.0
            elif risk_level == "high":
                score += 3.0
            elif risk_level == "medium":
                score += 1.5
            else:
                score += 0.5

        # 态势变化贡献
        score += len(posture_changes) * 1.0

        # 军事失衡贡献
        if balance_assessment.get("imbalance_detected", False):
            score += 3.0
        elif balance_assessment.get("assessment") == "concerning":
            score += 1.5

        return min(score, 10.0)

    def _generate_timeline(self, military_data: Dict[str, Any], anomalies: List[Dict[str, Any]],
                          conflict_risks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成时间线预测"""
        timeline = {
            "events": [],
            "trends": [],
            "milestones": []
        }

        # 基于演习预测事件
        for exercise in military_data.get("exercises", []):
            if exercise.end_date and exercise.end_date > datetime.now():
                timeline["events"].append({
                    "id": f"exercise_end_{exercise.exercise_id}",
                    "type": "exercise_completion",
                    "description": f"军事演习结束: {exercise.name}",
                    "predicted_time": exercise.end_date.isoformat(),
                    "confidence": 0.9
                })

        # 基于部署预测事件
        for deployment in military_data.get("deployments", []):
            if deployment.estimated_arrival and deployment.estimated_arrival > datetime.now():
                timeline["events"].append({
                    "id": f"deployment_arrival_{deployment.deployment_id}",
                    "type": "deployment_arrival",
                    "description": f"军事部署到达目的地",
                    "predicted_time": deployment.estimated_arrival.isoformat(),
                    "confidence": 0.8
                })

        # 基于异常预测事件
        for anomaly in anomalies[:3]:
            if anomaly.get("severity") in ["high", "critical"]:
                timeline["events"].append({
                    "id": f"anomaly_escalation_{anomaly.get('type', 'unknown')}",
                    "type": "potential_escalation",
                    "description": anomaly.get("description", ""),
                    "predicted_time": (datetime.now() + timedelta(hours=12)).isoformat(),
                    "confidence": 0.6
                })

        # 添加趋势预测
        if len(anomalies) > 5 or len(conflict_risks) > 0:
            timeline["trends"].append({
                "id": "trend_increasing_military_tension",
                "description": "军事紧张局势呈上升趋势",
                "timeframe": "未来48小时",
                "direction": "increasing"
            })

        # 添加里程碑
        timeline["milestones"].append({
            "id": "next_intelligence_update",
            "description": "下一次情报更新",
            "estimated_time": (datetime.now() + timedelta(hours=6)).isoformat(),
            "importance": "medium"
        })

        return timeline

    async def analyze_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """分析文本数据（军事报告）"""
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