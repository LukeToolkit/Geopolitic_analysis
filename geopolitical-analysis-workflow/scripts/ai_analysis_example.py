#!/usr/bin/env python3
"""
AI分析模块使用示例
演示如何使用AI分析模块分析多源数据
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_analysis import (
    get_analysis_manager,
    start_analysis,
    stop_analysis,
    analyze_data,
    analyze_multimodal_data,
    AnalysisType,
    AISAnalyzer,
    ADS_BAnalyzer,
    MilitaryAnalyzer,
    FusionAnalyzer,
    AnalyzerConfig
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_ais_data() -> list:
    """创建示例AIS数据"""
    return [
        {
            "mmsi": "123456789",
            "ship_name": "OCEAN_TRADER",
            "ship_type": "cargo",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "speed": 15.5,
            "course": 120.5,
            "destination": "Shanghai",
            "cargo": "electronics",
            "flag": "Panama",
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "mmsi": "987654321",
            "ship_name": "UNKNOWN",
            "ship_type": "unknown",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "speed": 0.0,
            "course": 0.0,
            "destination": "N/A",
            "cargo": "unknown",
            "flag": "North Korea",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]


def create_sample_adsb_data() -> list:
    """创建示例ADS-B数据"""
    return [
        {
            "icao24": "abc123",
            "callsign": "UAL123",
            "origin_country": "United States",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10000,
            "velocity": 250.0,
            "squawk": "1234",
            "on_ground": False,
            "aircraft_type": "commercial",
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "icao24": "def456",
            "callsign": "SPAR19",
            "origin_country": "United States",
            "latitude": 38.9072,
            "longitude": -77.0369,
            "altitude": 5000,
            "velocity": 0.0,
            "squawk": "0000",
            "on_ground": False,
            "aircraft_type": "military",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]


def create_sample_military_data() -> Dict[str, Any]:
    """创建示例军事数据"""
    return {
        "units": [
            {
                "unit_id": "unit_001",
                "unit_type": "navy",
                "country": "United States",
                "location": {"latitude": 35.6895, "longitude": 139.6917},
                "strength": 1500,
                "equipment": ["destroyer", "helicopter"],
                "readiness_level": "elevated",
                "movement_status": "stationary"
            }
        ],
        "exercises": [
            {
                "exercise_id": "ex_001",
                "name": "Joint Pacific Exercise",
                "participating_countries": ["United States", "Japan", "South Korea"],
                "location": {"region": "east_asia"},
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "exercise_type": "joint",
                "scale": "large",
                "objectives": ["interoperability", "deterrence"]
            }
        ],
        "deployments": []
    }


async def example_single_analysis():
    """示例：单数据源分析"""
    logger.info("=== 单数据源分析示例 ===")

    # 获取分析管理器
    manager = await get_analysis_manager()

    # 分析AIS数据
    logger.info("1. 分析AIS数据...")
    ais_data = create_sample_ais_data()
    ais_result = await analyze_data(AnalysisType.AIS_ANALYSIS, ais_data)
    logger.info(f"AIS分析结果:")
    logger.info(f"  置信度: {ais_result.confidence:.2f}")
    logger.info(f"  风险等级: {ais_result.risk_level}")
    logger.info(f"  洞察: {ais_result.insights[:2]}")

    # 分析ADS-B数据
    logger.info("\n2. 分析ADS-B数据...")
    adsb_data = create_sample_adsb_data()
    adsb_result = await analyze_data(AnalysisType.ADS_B_ANALYSIS, adsb_data)
    logger.info(f"ADS-B分析结果:")
    logger.info(f"  置信度: {adsb_result.confidence:.2f}")
    logger.info(f"  风险等级: {adsb_result.risk_level}")
    logger.info(f"  洞察: {adsb_result.insights[:2]}")

    # 分析军事数据
    logger.info("\n3. 分析军事数据...")
    military_data = create_sample_military_data()
    military_result = await analyze_data(AnalysisType.MILITARY_ANALYSIS, military_data)
    logger.info(f"军事分析结果:")
    logger.info(f"  置信度: {military_result.confidence:.2f}")
    logger.info(f"  风险等级: {military_result.risk_level}")
    logger.info(f"  洞察: {military_result.insights[:2]}")

    return [ais_result, adsb_result, military_result]


async def example_multimodal_analysis():
    """示例：多模态融合分析"""
    logger.info("\n=== 多模态融合分析示例 ===")

    # 准备多源数据
    multimodal_data = {
        "ais_data": create_sample_ais_data(),
        "adsb_data": create_sample_adsb_data(),
        "military_data": create_sample_military_data()
    }

    # 执行融合分析
    logger.info("执行多模态融合分析...")
    fusion_result = await analyze_multimodal_data(multimodal_data, {
        "region": "east_asia",
        "timeframe": "recent",
        "analysis_purpose": "综合风险评估"
    })

    logger.info(f"融合分析结果:")
    logger.info(f"  置信度: {fusion_result.confidence:.2f}")
    logger.info(f"  风险等级: {fusion_result.risk_level}")
    logger.info(f"  影响评分: {fusion_result.impact_score:.2f}/10.0")
    logger.info(f"  地理范围: {fusion_result.geographic_scope}")
    logger.info(f"  关键洞察:")
    for i, insight in enumerate(fusion_result.insights[:3], 1):
        logger.info(f"    {i}. {insight}")
    logger.info(f"  建议:")
    for i, recommendation in enumerate(fusion_result.recommendations[:3], 1):
        logger.info(f"    {i}. {recommendation}")

    # 显示时间线预测
    if fusion_result.timeline:
        logger.info(f"  时间线预测:")
        for event_type, events in fusion_result.timeline.items():
            if events:
                logger.info(f"    {event_type}: {len(events)} 项")

    return fusion_result


async def example_direct_analyzer():
    """示例：直接使用分析器"""
    logger.info("\n=== 直接使用分析器示例 ===")

    # 创建AIS分析器配置
    ais_config = AnalyzerConfig(
        name="example_ais_analyzer",
        processor_type="ais_analyzer",
        model_provider="anthropic",
        model_name="claude-3-sonnet-20240229",
        geographic_focus=["east_asia"],
        analysis_depth="standard"
    )

    # 创建分析器实例
    ais_analyzer = AISAnalyzer(ais_config)

    # 直接分析数据
    ais_data = create_sample_ais_data()
    result = await ais_analyzer.analyze(ais_data, {"region": "east_asia"})

    logger.info(f"直接分析结果:")
    logger.info(f"  分析器: {ais_analyzer.name}")
    logger.info(f"  处理数据量: {len(ais_data)}")
    logger.info(f"  结果置信度: {result.confidence:.2f}")

    return result


async def example_analysis_manager():
    """示例：使用分析管理器的高级功能"""
    logger.info("\n=== 分析管理器高级功能示例 ===")

    # 启动分析服务
    logger.info("启动分析服务...")
    await start_analysis()

    # 获取管理器实例
    manager = await get_analysis_manager()

    # 获取统计信息
    stats = manager.get_stats()
    logger.info(f"分析管理器统计:")
    logger.info(f"  运行状态: {'运行中' if stats['running'] else '已停止'}")
    logger.info(f"  分析器数量: {stats['analyzers_count']}")
    logger.info(f"  工作线程: {stats['active_workers']}")
    logger.info(f"  任务队列大小: {stats['queue_size']}")
    logger.info(f"  总任务数: {stats['jobs']['total_jobs']}")

    # 停止分析服务
    logger.info("\n停止分析服务...")
    await stop_analysis()

    return stats


async def main():
    """主函数"""
    logger.info("地缘政治分析AI模块使用示例")
    logger.info("=" * 60)

    try:
        # 示例1: 单数据源分析
        single_results = await example_single_analysis()

        # 示例2: 多模态融合分析
        fusion_result = await example_multimodal_analysis()

        # 示例3: 直接使用分析器
        direct_result = await example_direct_analyzer()

        # 示例4: 分析管理器高级功能
        manager_stats = await example_analysis_manager()

        logger.info("\n" + "=" * 60)
        logger.info("所有示例执行完成!")
        logger.info(f"单数据源分析: {len(single_results)} 个结果")
        logger.info(f"融合分析风险等级: {fusion_result.risk_level}")
        logger.info(f"直接分析置信度: {direct_result.confidence:.2f}")

        # 保存示例结果
        output_data = {
            "single_analysis_results": [r.to_dict() for r in single_results],
            "fusion_analysis_result": fusion_result.to_dict(),
            "direct_analysis_result": direct_result.to_dict(),
            "manager_stats": manager_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

        output_file = "ai_analysis_example_output.json"
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"示例结果已保存到: {output_file}")

    except Exception as e:
        logger.error(f"示例执行失败: {str(e)}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    # 需要导入timedelta
    from datetime import timedelta

    # 运行示例
    exit_code = asyncio.run(main())
    sys.exit(exit_code)