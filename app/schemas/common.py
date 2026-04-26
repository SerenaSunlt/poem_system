# app/schemas/common.py
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


def success(data=None, message: str = "ok") -> dict:
    """成功响应的快捷构造器。"""
    return {"code": 0, "message": message, "data": data}


def error(code: int, message: str) -> dict:
    """失败响应的快捷构造器。"""
    return {"code": code, "message": message, "data": None}