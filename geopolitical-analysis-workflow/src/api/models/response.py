"""
API响应模型
定义统一的API响应格式
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict, Union
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Pagination(BaseModel):
    """分页信息"""
    page: int = Field(default=1, description="当前页码")
    size: int = Field(default=10, description="每页大小")
    total: int = Field(default=0, description="总记录数")
    pages: int = Field(default=0, description="总页数")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """计算限制数量"""
        return self.size

    def update_total(self, total: int):
        """更新总数并重新计算页数"""
        self.total = total
        self.pages = (total + self.size - 1) // self.size if self.size > 0 else 0


class BaseResponse(BaseModel):
    """基础响应模型"""
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="响应状态")
    message: Optional[str] = Field(default=None, description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SuccessResponse(BaseResponse):
    """成功响应"""
    data: Optional[Any] = Field(default=None, description="响应数据")
    pagination: Optional[Pagination] = Field(default=None, description="分页信息")

    @classmethod
    def create(
        cls,
        data: Any = None,
        message: str = "操作成功",
        pagination: Optional[Pagination] = None
    ) -> "SuccessResponse":
        """创建成功响应"""
        return cls(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            pagination=pagination
        )


class ErrorResponse(BaseResponse):
    """错误响应"""
    errors: Optional[List[Union[str, Dict[str, Any]]]] = Field(default=None, description="错误详情")
    code: Optional[str] = Field(default=None, description="错误代码")

    @classmethod
    def create(
        cls,
        message: str = "操作失败",
        errors: Optional[List[Union[str, Dict[str, Any]]]] = None,
        code: Optional[str] = None
    ) -> "ErrorResponse":
        """创建错误响应"""
        return cls(
            status=ResponseStatus.ERROR,
            message=message,
            errors=errors or [],
            code=code
        )


class WarningResponse(BaseResponse):
    """警告响应"""
    data: Optional[Any] = Field(default=None, description="响应数据")
    warnings: Optional[List[str]] = Field(default=None, description="警告信息")

    @classmethod
    def create(
        cls,
        message: str = "操作完成但有警告",
        data: Any = None,
        warnings: Optional[List[str]] = None
    ) -> "WarningResponse":
        """创建警告响应"""
        return cls(
            status=ResponseStatus.WARNING,
            message=message,
            data=data,
            warnings=warnings or []
        )


class InfoResponse(BaseResponse):
    """信息响应"""
    data: Optional[Any] = Field(default=None, description="响应数据")
    info: Optional[List[str]] = Field(default=None, description="附加信息")

    @classmethod
    def create(
        cls,
        message: str = "信息",
        data: Any = None,
        info: Optional[List[str]] = None
    ) -> "InfoResponse":
        """创建信息响应"""
        return cls(
            status=ResponseStatus.INFO,
            message=message,
            data=data,
            info=info or []
        )


# 类型别名
ApiResponse = Union[SuccessResponse, ErrorResponse, WarningResponse, InfoResponse]


class ValidationErrorDetail(BaseModel):
    """验证错误详情"""
    field: str = Field(description="字段名")
    message: str = Field(description="错误消息")
    type: Optional[str] = Field(default=None, description="错误类型")


class ValidationErrorResponse(ErrorResponse):
    """验证错误响应"""
    validation_errors: Optional[List[ValidationErrorDetail]] = Field(default=None, description="验证错误详情")

    @classmethod
    def from_pydantic_errors(cls, errors: List[Dict[str, Any]]) -> "ValidationErrorResponse":
        """从Pydantic错误创建验证错误响应"""
        validation_errors = []
        for error in errors:
            field = ".".join(str(loc) for loc in error.get("loc", []))
            validation_errors.append(ValidationErrorDetail(
                field=field,
                message=error.get("msg", "验证错误"),
                type=error.get("type")
            ))

        return cls(
            status=ResponseStatus.ERROR,
            message="数据验证失败",
            errors=["请检查输入数据"],
            validation_errors=validation_errors
        )


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    checks: Dict[str, str] = Field(description="各项检查状态")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="检查时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    system: Dict[str, Any] = Field(description="系统信息")
    application: Dict[str, Any] = Field(description="应用信息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="状态时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }