"""
API配置模块
使用pydantic-settings管理配置
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator, PostgresDsn, RedisDsn, AnyUrl
from typing import List, Optional, Dict, Any
import secrets
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "地缘政治分析AI工作流系统"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", env="APP_ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="APP_DEBUG")
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # 服务器配置
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")

    # 数据库配置
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://geopolitical_user:geopolitical_pass@localhost:5432/geopolitical",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")

    # Redis配置
    REDIS_URL: RedisDsn = Field(
        default="redis://:redis_pass@localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")

    # MinIO配置
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", env="MINIO_SECRET_KEY")
    MINIO_BUCKET: str = Field(default="geopolitical-data", env="MINIO_BUCKET")
    MINIO_SECURE: bool = Field(default=False, env="MINIO_SECURE")

    # CORS配置
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")

    # 安全配置
    TRUSTED_HOSTS: str = Field(default="localhost,127.0.0.1", env="TRUSTED_HOSTS")
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_DEFAULT: str = Field(default="100/hour", env="RATE_LIMIT_DEFAULT")
    RATE_LIMIT_API: str = Field(default="1000/hour", env="RATE_LIMIT_API")

    # JWT配置
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # API密钥配置
    API_KEYS: Dict[str, str] = Field(default_factory=dict, env="API_KEYS")

    # 外部API配置
    NEWS_API_KEY: Optional[str] = Field(default=None, env="NEWS_API_KEY")
    NEWS_API_URL: str = Field(default="https://newsapi.org/v2", env="NEWS_API_URL")

    FINANCIAL_API_KEY: Optional[str] = Field(default=None, env="FINANCIAL_API_KEY")
    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY")

    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")

    ADS_B_API_KEY: Optional[str] = Field(default=None, env="ADS_B_API_KEY")
    ADS_B_API_URL: str = Field(default="https://opensky-network.org/api", env="ADS_B_API_URL")

    AIS_API_KEY: Optional[str] = Field(default=None, env="AIS_API_KEY")
    AIS_API_URL: str = Field(default="https://services.marinetraffic.com/api", env="AIS_API_URL")

    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")

    # 监控配置
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # 工作流配置
    WORKFLOW_MAX_RETRIES: int = Field(default=3, env="WORKFLOW_MAX_RETRIES")
    WORKFLOW_RETRY_DELAY: int = Field(default=60, env="WORKFLOW_RETRY_DELAY")
    WORKFLOW_TIMEOUT: int = Field(default=3600, env="WORKFLOW_TIMEOUT")

    # 数据收集配置
    DATA_COLLECTION_BATCH_SIZE: int = Field(default=100, env="DATA_COLLECTION_BATCH_SIZE")
    DATA_COLLECTION_INTERVAL: int = Field(default=3600, env="DATA_COLLECTION_INTERVAL")
    DATA_RETENTION_DAYS: int = Field(default=90, env="DATA_RETENTION_DAYS")

    # 预测配置
    PREDICTION_HORIZON_DAYS: int = Field(default=30, env="PREDICTION_HORIZON_DAYS")
    PREDICTION_CONFIDENCE_THRESHOLD: float = Field(default=0.7, env="PREDICTION_CONFIDENCE_THRESHOLD")

    # 邮件配置（可选）
    SMTP_SERVER: Optional[str] = Field(default=None, env="SMTP_SERVER")
    SMTP_PORT: Optional[int] = Field(default=None, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    NOTIFICATION_EMAIL: Optional[str] = Field(default=None, env="NOTIFICATION_EMAIL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("CORS_ORIGINS")
    def parse_cors_origins(cls, v):
        """解析CORS origins字符串"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @validator("TRUSTED_HOSTS")
    def parse_trusted_hosts(cls, v):
        """解析可信主机字符串"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @validator("API_KEYS", pre=True)
    def parse_api_keys(cls, v):
        """解析API密钥字符串"""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                # 如果是key1:value1,key2:value2格式
                api_keys = {}
                for item in v.split(","):
                    if ":" in item:
                        key, value = item.split(":", 1)
                        api_keys[key.strip()] = value.strip()
                return api_keys
        return v or {}

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT.lower() == "testing"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（缓存）"""
    return Settings()


# 全局配置实例
settings = get_settings()