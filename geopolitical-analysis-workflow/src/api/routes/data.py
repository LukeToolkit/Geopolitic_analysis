"""
数据路由
处理数据收集、查询和管理相关API
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..models.response import SuccessResponse, ErrorResponse, Pagination
from ..middleware.auth import verify_api_key
from ...data_collection.manager import get_manager, DataCollectionManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sources", summary="获取数据源列表")
async def get_data_sources(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取所有可用的数据源"""
    try:
        manager = await get_manager()
        collectors = manager.registry.get_all_collectors()

        sources = []
        for collector in collectors:
            stats = collector.get_stats()
            sources.append({
                "name": collector.name,
                "type": collector.source_type.value,
                "enabled": collector.config.enabled,
                "interval": collector.config.interval_seconds,
                "last_collection": stats.get("last_collection_time"),
                "total_collected": stats["total_collected"],
                "total_errors": stats["total_errors"]
            })

        return SuccessResponse.create(
            data=sources,
            message="数据源列表获取成功"
        )

    except Exception as e:
        logger.error(f"获取数据源列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取数据源列表失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/collectors", summary="获取收集器状态")
async def get_collector_status(
    name: Optional[str] = Query(None, description="收集器名称"),
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取收集器状态信息"""
    try:
        manager = await get_manager()

        if name:
            collector = manager.registry.get_collector(name)
            if not collector:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse.create(
                        message="收集器未找到",
                        errors=[f"收集器 '{name}' 不存在"]
                    ).dict()
                )
            stats = collector.get_stats()
            return SuccessResponse.create(
                data=stats,
                message=f"收集器 '{name}' 状态获取成功"
            )
        else:
            stats = manager.registry.get_stats()
            return SuccessResponse.create(
                data=stats,
                message="所有收集器状态获取成功"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取收集器状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取收集器状态失败",
                errors=[str(e)]
            ).dict()
        )


@router.post("/collect", summary="立即收集数据")
async def collect_data_now(
    background_tasks: BackgroundTasks,
    collector_names: Optional[List[str]] = Query(None, description="收集器名称列表"),
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """立即触发数据收集"""
    try:
        manager = await get_manager()

        # 异步执行数据收集
        async def collect_async():
            try:
                results = await manager.collect_now(collector_names)
                logger.info(f"立即收集完成: {len(results)} 个收集器")
            except Exception as e:
                logger.error(f"立即收集失败: {str(e)}")

        background_tasks.add_task(collect_async)

        return SuccessResponse.create(
            data={"task_started": True},
            message="数据收集任务已启动"
        )

    except Exception as e:
        logger.error(f"启动数据收集失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="启动数据收集失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/status", summary="获取数据收集状态")
async def get_collection_status(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取数据收集整体状态"""
    try:
        manager = await get_manager()
        status_info = manager.get_status()

        return SuccessResponse.create(
            data=status_info,
            message="数据收集状态获取成功"
        )

    except Exception as e:
        logger.error(f"获取数据收集状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取数据收集状态失败",
                errors=[str(e)]
            ).dict()
        )


@router.post("/collectors/{name}/enable", summary="启用收集器")
async def enable_collector(
    name: str,
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """启用指定收集器"""
    try:
        manager = await get_manager()
        collector = manager.registry.get_collector(name)

        if not collector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.create(
                    message="收集器未找到",
                    errors=[f"收集器 '{name}' 不存在"]
                ).dict()
            )

        collector.config.enabled = True

        return SuccessResponse.create(
            data={"enabled": True},
            message=f"收集器 '{name}' 已启用"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用收集器失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="启用收集器失败",
                errors=[str(e)]
            ).dict()
        )


@router.post("/collectors/{name}/disable", summary="禁用收集器")
async def disable_collector(
    name: str,
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """禁用指定收集器"""
    try:
        manager = await get_manager()
        collector = manager.registry.get_collector(name)

        if not collector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.create(
                    message="收集器未找到",
                    errors=[f"收集器 '{name}' 不存在"]
                ).dict()
            )

        collector.config.enabled = False

        return SuccessResponse.create(
            data={"enabled": False},
            message=f"收集器 '{name}' 已禁用"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用收集器失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="禁用收集器失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/test-connections", summary="测试数据源连接")
async def test_connections(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """测试所有数据源连接"""
    try:
        manager = await get_manager()
        results = await manager.test_all_connections()

        # 统计结果
        total = len(results)
        successful = sum(1 for result in results.values() if result)
        failed = total - successful

        return SuccessResponse.create(
            data={
                "results": results,
                "summary": {
                    "total": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": successful / total if total > 0 else 0
                }
            },
            message=f"连接测试完成: {successful} 成功, {failed} 失败"
        )

    except Exception as e:
        logger.error(f"测试连接失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="测试连接失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/recent", summary="获取最近收集的数据")
async def get_recent_data(
    source_type: Optional[str] = Query(None, description="数据源类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取最近收集的数据"""
    try:
        # 这里应该从数据库查询数据
        # 暂时返回模拟数据
        import random
        from datetime import datetime, timedelta

        # 生成模拟数据
        sources = ["news", "financial", "social_media", "ads_b", "ais"]
        if source_type and source_type in sources:
            sources = [source_type]

        data = []
        for i in range(min(limit, 50)):  # 限制模拟数据量
            source = random.choice(sources)
            timestamp = datetime.utcnow() - timedelta(hours=random.randint(0, hours))

            data.append({
                "id": f"{source}_{timestamp.timestamp()}",
                "source_type": source,
                "timestamp": timestamp.isoformat(),
                "title": f"{source.capitalize()} 数据示例 {i+1}",
                "content": f"这是来自 {source} 的示例数据内容...",
                "metadata": {
                    "source": f"{source}_api",
                    "confidence": random.uniform(0.7, 0.99),
                    "language": "en"
                }
            })

        # 按时间排序
        data.sort(key=lambda x: x["timestamp"], reverse=True)

        return SuccessResponse.create(
            data=data[:limit],
            message="最近数据获取成功"
        )

    except Exception as e:
        logger.error(f"获取最近数据失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取最近数据失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/stats/daily", summary="获取每日数据统计")
async def get_daily_stats(
    days: int = Query(7, ge=1, le=30, description="天数"),
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取每日数据收集统计"""
    try:
        # 这里应该从数据库查询统计信息
        # 暂时返回模拟数据
        import random
        from datetime import datetime, timedelta

        stats = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            stats.append({
                "date": date.strftime("%Y-%m-%d"),
                "total_records": random.randint(100, 1000),
                "successful_collections": random.randint(5, 20),
                "failed_collections": random.randint(0, 3),
                "by_source": {
                    "news": random.randint(20, 200),
                    "financial": random.randint(50, 300),
                    "social_media": random.randint(100, 400),
                    "ads_b": random.randint(200, 500),
                    "ais": random.randint(50, 150)
                }
            })

        # 按日期排序
        stats.sort(key=lambda x: x["date"])

        return SuccessResponse.create(
            data=stats,
            message="每日统计获取成功"
        )

    except Exception as e:
        logger.error(f"获取每日统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取每日统计失败",
                errors=[str(e)]
            ).dict()
        )