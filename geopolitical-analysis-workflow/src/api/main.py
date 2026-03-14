"""
地缘政治分析API主模块
基于FastAPI构建的REST API服务
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any, Optional

from .config import settings
from .middleware.auth import get_current_user, verify_api_key
from .routes import data, analysis, prediction, workflow, system
from .models.response import ErrorResponse, SuccessResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时
    logger.info("启动地缘政治分析API服务")
    logger.info(f"环境: {settings.ENVIRONMENT}")
    logger.info(f"调试模式: {settings.DEBUG}")

    # 初始化数据库连接等
    # await init_database()

    yield

    # 关闭时
    logger.info("关闭地缘政治分析API服务")
    # await close_database()


# 创建FastAPI应用
app = FastAPI(
    title="地缘政治分析AI工作流系统",
    description="基于AI和大模型的地缘政治分析系统API",
    version="0.1.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse, "description": "请求错误"},
        401: {"model": ErrorResponse, "description": "未授权"},
        403: {"model": ErrorResponse, "description": "禁止访问"},
        404: {"model": ErrorResponse, "description": "未找到"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    }
)

# 中间件配置
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if settings.TRUSTED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS.split(",")
    )

# 自定义中间件
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def log_requests(request, call_next):
    """记录请求日志"""
    logger.info(f"请求: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"响应: {request.method} {request.url.path} - {response.status_code}")
    return response


# 自定义文档端点（如果需要额外的安全控制）
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义Swagger UI"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """自定义Redoc UI"""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


# 根路由
@app.get("/", tags=["系统"])
async def root():
    """API根端点"""
    return SuccessResponse(
        message="地缘政治分析AI工作流系统API",
        data={
            "name": "地缘政治分析AI工作流系统",
            "version": "0.1.0",
            "description": "基于AI和大模型的地缘政治分析系统",
            "docs": "/docs",
            "health": "/health",
            "status": "/status"
        }
    )


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    # 这里可以添加数据库连接检查、外部服务检查等
    checks = {
        "api": "healthy",
        "timestamp": time.time(),
        # "database": await check_database_health(),
        # "redis": await check_redis_health(),
    }

    all_healthy = all(status == "healthy" for status in checks.values() if isinstance(status, str))

    if all_healthy:
        return SuccessResponse(
            message="系统健康",
            data=checks
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                message="系统不健康",
                errors=[f"{service}: {status}" for service, status in checks.items() if status != "healthy"]
            ).dict()
        )


@app.get("/status", tags=["系统"])
async def system_status():
    """系统状态端点"""
    import psutil
    import platform

    # 系统信息
    system_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": psutil.cpu_count(),
        "memory_total": psutil.virtual_memory().total,
        "memory_available": psutil.virtual_memory().available,
        "disk_usage": psutil.disk_usage('/').percent,
    }

    # 应用信息
    app_info = {
        "name": app.title,
        "version": app.version,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "start_time": time.time() - psutil.boot_time(),
    }

    return SuccessResponse(
        message="系统状态",
        data={
            "system": system_info,
            "application": app_info,
            "timestamp": time.time()
        }
    )


@app.get("/metrics", tags=["系统"])
async def metrics():
    """Prometheus指标端点"""
    # 这里应该返回Prometheus格式的指标
    # 暂时返回简单指标
    import psutil

    metrics_data = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "process_count": len(psutil.pids()),
    }

    # 转换为Prometheus格式
    prometheus_metrics = []
    for key, value in metrics_data.items():
        prometheus_metrics.append(f"geo_system_{key} {value}")

    return "\n".join(prometheus_metrics)


# 路由注册
# 公开路由（不需要认证）
public_routes = [
    app.include_router(data.router, prefix="/api/v1/data", tags=["数据"]),
    app.include_router(system.router, prefix="/api/v1/system", tags=["系统"]),
]

# 需要API密钥的路由
api_key_routes = [
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["分析"], dependencies=[Depends(verify_api_key)]),
    app.include_router(prediction.router, prefix="/api/v1/prediction", tags=["预测"], dependencies=[Depends(verify_api_key)]),
]

# 需要用户认证的路由
protected_routes = [
    app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["工作流"], dependencies=[Depends(get_current_user)]),
]

# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            errors=[str(exc)]
        ).dict()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="内部服务器错误",
            errors=[str(exc)] if settings.DEBUG else ["请稍后重试"]
        ).dict()
    )


# 启动应用
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )