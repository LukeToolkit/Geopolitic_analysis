"""
认证和授权中间件
处理API密钥验证和JWT认证
"""

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from ..config import settings
from ..models.response import ErrorResponse

logger = logging.getLogger(__name__)

# API密钥认证方案
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# JWT Bearer认证方案
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key_header: Optional[str] = Depends(api_key_header),
    api_key_query: Optional[str] = Depends(api_key_query)
) -> Dict[str, Any]:
    """
    验证API密钥
    支持Header和Query两种方式
    """
    api_key = api_key_header or api_key_query

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                message="缺少API密钥",
                errors=["请提供有效的API密钥"],
                code="MISSING_API_KEY"
            ).dict()
        )

    # 检查API密钥是否有效
    # 这里可以从数据库或配置中检查
    valid_keys = settings.API_KEYS

    if not valid_keys:
        logger.warning("未配置API密钥，允许所有请求")
        return {"api_key": api_key, "client_id": "default"}

    if api_key not in valid_keys.values():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                message="无效的API密钥",
                errors=["请提供有效的API密钥"],
                code="INVALID_API_KEY"
            ).dict()
        )

    # 查找对应的客户端ID
    client_id = None
    for key, value in valid_keys.items():
        if value == api_key:
            client_id = key
            break

    return {"api_key": api_key, "client_id": client_id or "unknown"}


async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    验证JWT令牌
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                message="缺少认证令牌",
                errors=["请提供Bearer令牌"],
                code="MISSING_TOKEN"
            ).dict()
        )

    token = credentials.credentials

    try:
        # 解码JWT令牌
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # 检查令牌是否过期
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    message="令牌已过期",
                    errors=["请重新登录获取新令牌"],
                    code="TOKEN_EXPIRED"
                ).dict()
            )

        return payload

    except JWTError as e:
        logger.error(f"JWT解码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                message="无效的令牌",
                errors=["令牌格式不正确或已损坏"],
                code="INVALID_TOKEN"
            ).dict()
        )


async def get_current_user(
    token_data: Dict[str, Any] = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """
    获取当前用户信息
    """
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                message="无效的用户令牌",
                errors=["令牌中缺少用户标识"],
                code="INVALID_USER_TOKEN"
            ).dict()
        )

    # 这里可以从数据库获取用户详细信息
    # user = await get_user_from_db(user_id)

    # 暂时返回令牌中的基本信息
    return {
        "id": user_id,
        "username": token_data.get("username", "unknown"),
        "email": token_data.get("email"),
        "roles": token_data.get("roles", []),
        "permissions": token_data.get("permissions", [])
    }


async def require_role(required_role: str, user: Dict[str, Any] = Depends(get_current_user)):
    """
    检查用户是否具有特定角色
    """
    user_roles = user.get("roles", [])
    if required_role not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse.create(
                message="权限不足",
                errors=[f"需要角色: {required_role}"],
                code="INSUFFICIENT_ROLE"
            ).dict()
        )
    return user


async def require_permission(required_permission: str, user: Dict[str, Any] = Depends(get_current_user)):
    """
    检查用户是否具有特定权限
    """
    user_permissions = user.get("permissions", [])
    if required_permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse.create(
                message="权限不足",
                errors=[f"需要权限: {required_permission}"],
                code="INSUFFICIENT_PERMISSION"
            ).dict()
        )
    return user


async def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


async def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建刷新令牌
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


async def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    使用刷新令牌获取新的访问令牌
    """
    try:
        # 验证刷新令牌
        payload = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # 检查令牌类型
        if payload.get("type") != "refresh":
            return None

        # 检查是否过期
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None

        # 创建新的访问令牌
        user_data = {
            "sub": payload.get("sub"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", [])
        }

        new_access_token = await create_access_token(user_data)
        return new_access_token

    except JWTError:
        return None


# 速率限制装饰器（简化版）
def rate_limit(limit: str = "100/hour"):
    """
    速率限制装饰器
    limit格式: "100/hour", "10/minute", "1000/day"
    """
    # 这里应该实现真正的速率限制逻辑
    # 暂时只是占位符
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 速率限制检查
            # 可以从Redis等存储中检查请求频率
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# API密钥管理
class APIKeyManager:
    """API密钥管理器"""

    @staticmethod
    async def generate_api_key(client_id: str) -> str:
        """生成新的API密钥"""
        import secrets
        api_key = secrets.token_urlsafe(32)

        # 这里应该将API密钥存储到数据库或配置中
        # await store_api_key(client_id, api_key)

        return api_key

    @staticmethod
    async def revoke_api_key(client_id: str) -> bool:
        """撤销API密钥"""
        # 这里应该从数据库或配置中删除API密钥
        # await delete_api_key(client_id)
        return True

    @staticmethod
    async def validate_api_key(api_key: str) -> Optional[str]:
        """验证API密钥并返回客户端ID"""
        # 这里应该从数据库或配置中验证API密钥
        valid_keys = settings.API_KEYS
        for client_id, key in valid_keys.items():
            if key == api_key:
                return client_id
        return None