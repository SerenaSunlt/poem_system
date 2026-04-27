# app/schemas/poem.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


class PoemBase(BaseModel):
    """诗词基础字段(在多个响应里复用)"""
    id: int
    title: str
    author: Optional[str] = None
    dynasty: Optional[str] = None
    content: str
    content_simplified: str = ""
    type: str
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FavoriteInfo(BaseModel):
    """诗词详情里附带的收藏信息(已收藏时才有)"""
    user_tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PoemCard(PoemBase):
    """推荐列表里的诗词卡片"""
    is_favorited: bool = False


class PoemDetail(PoemBase):
    """诗词详情"""
    is_favorited: bool = False
    favorite_info: Optional[FavoriteInfo] = None
    has_translation: bool = False


class RecommendOut(BaseModel):
    """推荐接口的响应数据"""
    poems: List[PoemCard]
    prompt_keywords: List[str] = Field(default_factory=list)  # AI 阶段用,先留空