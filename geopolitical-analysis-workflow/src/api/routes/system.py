"""
系统管理路由
处理系统配置、监控、日志等API
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any
import logging
import psutil
import platform
import os

from ..models.response import SuccessResponse, ErrorResponse
from ..middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/info", summary="获取系统信息")
async def get_system_info(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取系统基本信息"""
    try:
        system_info = {
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler()
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "hardware": {
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_total": psutil.disk_usage('/').total if os.path.exists('/') else None
            },
            "process": {
                "pid": os.getpid(),
                "name": psutil.Process().name(),
                "memory_percent": psutil.Process().memory_percent(),
                "cpu_percent": psutil.Process().cpu_percent(),
                "create_time": psutil.Process().create_time()
            }
        }

        return SuccessResponse.create(
            data=system_info,
            message="系统信息获取成功"
        )

    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取系统信息失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/metrics", summary="获取系统指标")
async def get_system_metrics(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取系统实时指标"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)

        # 内存使用情况
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # 磁盘使用情况
        disk = psutil.disk_usage('/') if os.path.exists('/') else None

        # 网络IO
        net_io = psutil.net_io_counters()

        # 进程信息
        process = psutil.Process()
        process_info = {
            "memory_info": process.memory_info()._asdict(),
            "cpu_times": process.cpu_times()._asdict(),
            "num_threads": process.num_threads(),
            "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None
        }

        metrics = {
            "cpu": {
                "percent": cpu_percent,
                "percent_per_core": cpu_percent_per_core,
                "count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            },
            "disk": {
                "total": disk.total if disk else None,
                "used": disk.used if disk else None,
                "free": disk.free if disk else None,
                "percent": disk.percent if disk else None
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            },
            "process": process_info,
            "timestamp": psutil.boot_time()
        }

        return SuccessResponse.create(
            data=metrics,
            message="系统指标获取成功"
        )

    except Exception as e:
        logger.error(f"获取系统指标失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取系统指标失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/logs", summary="获取系统日志")
async def get_system_logs(
    level: Optional[str] = Query(None, description="日志级别"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取系统日志"""
    try:
        # 这里应该从日志文件或日志系统查询
        # 暂时返回模拟数据
        import random
        from datetime import datetime, timedelta

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level and level.upper() in levels:
            levels = [level.upper()]

        sources = ["api", "data_collection", "analysis", "workflow", "database"]

        logs = []
        for i in range(min(limit, 100)):
            log_level = random.choice(levels)
            timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))  # 24小时内

            logs.append({
                "timestamp": timestamp.isoformat(),
                "level": log_level,
                "source": random.choice(sources),
                "message": f"这是来自 {random.choice(sources)} 的 {log_level} 日志消息示例 {i+1}",
                "module": f"module_{random.randint(1, 10)}",
                "function": f"function_{random.randint(1, 20)}",
                "extra": {
                    "request_id": f"req_{random.randint(1000, 9999)}",
                    "user_id": f"user_{random.randint(1, 100)}" if random.random() > 0.5 else None
                }
            })

        # 按时间排序
        logs.sort(key=lambda x: x["timestamp"], reverse=True)

        return SuccessResponse.create(
            data=logs[:limit],
            message="系统日志获取成功"
        )

    except Exception as e:
        logger.error(f"获取系统日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取系统日志失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/config", summary="获取配置信息")
async def get_configuration(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """获取系统配置信息（不包含敏感信息）"""
    try:
        from ..config import settings

        # 只返回非敏感配置
        config = {
            "app": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG
            },
            "server": {
                "host": settings.HOST,
                "port": settings.PORT,
                "workers": settings.WORKERS
            },
            "database": {
                "url": str(settings.DATABASE_URL).split('@')[1] if '@' in str(settings.DATABASE_URL) else "hidden",
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW
            },
            "cors": {
                "origins": settings.CORS_ORIGINS[:3] if settings.CORS_ORIGINS else [],  # 只显示前3个
                "allow_credentials": settings.CORS_ALLOW_CREDENTIALS
            },
            "security": {
                "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
                "trusted_hosts": settings.TRUSTED_HOSTS[:3] if settings.TRUSTED_HOSTS else []  # 只显示前3个
            },
            "jwt": {
                "algorithm": settings.JWT_ALGORITHM,
                "access_token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
                "refresh_token_expire_days": settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            },
            "workflow": {
                "max_retries": settings.WORKFLOW_MAX_RETRIES,
                "retry_delay": settings.WORKFLOW_RETRY_DELAY,
                "timeout": settings.WORKFLOW_TIMEOUT
            },
            "data_collection": {
                "batch_size": settings.DATA_COLLECTION_BATCH_SIZE,
                "interval": settings.DATA_COLLECTION_INTERVAL,
                "retention_days": settings.DATA_RETENTION_DAYS
            },
            "prediction": {
                "horizon_days": settings.PREDICTION_HORIZON_DAYS,
                "confidence_threshold": settings.PREDICTION_CONFIDENCE_THRESHOLD
            }
        }

        return SuccessResponse.create(
            data=config,
            message="配置信息获取成功"
        )

    except Exception as e:
        logger.error(f"获取配置信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取配置信息失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/health/detailed", summary="详细健康检查")
async def detailed_health_check(
    api_key_info: Dict[str, Any] = Depends(verify_api_key)
):
    """执行详细的健康检查"""
    try:
        checks = {}

        # 1. 系统检查
        try:
            checks["system"] = {
                "status": "healthy",
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent if os.path.exists('/') else None
            }
        except Exception as e:
            checks["system"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # 2. 进程检查
        try:
            process = psutil.Process()
            checks["process"] = {
                "status": "healthy",
                "memory_rss": process.memory_info().rss,
                "cpu_percent": process.cpu_percent(interval=0.1),
                "num_threads": process.num_threads()
            }
        except Exception as e:
            checks["process"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # 3. API检查（自检）
        checks["api"] = {
            "status": "healthy",
            "endpoints": len(router.routes),
            "version": "0.1.0"
        }

        # 4. 外部服务检查（这里可以添加数据库、Redis等检查）
        # 暂时标记为未知
        checks["external_services"] = {
            "status": "unknown",
            "services": ["database", "redis", "minio"]
        }

        # 计算总体状态
        all_healthy = all(
            check["status"] == "healthy"
            for check in checks.values()
            if isinstance(check, dict) and "status" in check
        )

        return SuccessResponse.create(
            data={
                "checks": checks,
                "overall_status": "healthy" if all_healthy else "unhealthy",
                "timestamp": psutil.boot_time()
            },
            message="详细健康检查完成"
        )

    except Exception as e:
        logger.error(f"详细健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="详细健康检查失败",
                errors=[str(e)]
            ).dict()
        )


@router.get("/version", summary="获取版本信息")
async def get_version_info():
    """获取系统版本信息（公开接口）"""
    try:
        from ..config import settings

        version_info = {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "api_version": "v1",
            "build_date": "2024-01-01",  # 这里应该从构建信息获取
            "commit_hash": "unknown"  # 这里应该从Git获取
        }

        return SuccessResponse.create(
            data=version_info,
            message="版本信息获取成功"
        )

    except Exception as e:
        logger.error(f"获取版本信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                message="获取版本信息失败",
                errors=[str(e)]
            ).dict()
        )