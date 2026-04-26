# app/schemas/favorite.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


# ===== 请求体 =====

class FavoriteCreateIn(BaseModel):
    """添加收藏的请求体"""
    poem_id: int
    user_tags: List[str] = Field(default_factory=list, max_length=10)
    note: Optional[str] = Field(None, max_length=500)


class FavoriteUpdateIn(BaseModel):
    """修改收藏的请求体,字段都可选,只更新传了的"""
    user_tags: Optional[List[str]] = Field(None, max_length=10)
    note: Optional[str] = Field(None, max_length=500)


class DislikeCreateIn(BaseModel):
    """标记不感兴趣的请求体"""
    poem_id: int


# ===== 响应字段 =====

class PoemBrief(BaseModel):
    """诗词简要信息(收藏列表里嵌套使用)"""
    id: int
    title: str
    author: Optional[str] = None
    dynasty: Optional[str] = None
    content: str
    type: str

    model_config = ConfigDict(from_attributes=True)


class FavoriteItem(BaseModel):
    """收藏列表的单项"""
    favorite_id: int
    poem: PoemBrief
    user_tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    created_at: datetime


class TagInfo(BaseModel):
    """标签 + 使用次数"""
    name: str
    count: int