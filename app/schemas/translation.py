# app/schemas/translation.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class Annotation(BaseModel):
    """单个字词注释"""
    word: str
    meaning: str


class TranslationLine(BaseModel):
    """逐句翻译"""
    original: str
    translation: str
    annotations: List[Annotation] = Field(default_factory=list)


class TranslationData(BaseModel):
    """翻译数据(整体 + 逐句)"""
    overall: str
    lines: List[TranslationLine]


class TranslationOut(BaseModel):
    """翻译响应"""
    poem_id: int
    is_saved: bool                  # True 表示数据库里有这条;False 表示是临时翻译
    translation: TranslationData
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SaveTranslationIn(BaseModel):
    """保存翻译的请求体(直接传 translation 数据)"""
    translation: TranslationData