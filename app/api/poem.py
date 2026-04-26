# app/api/poem.py
import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user_optional
from app.models import User
from app.schemas.common import success, error
from app.services.poem_service import (
    random_recommend,
    prompt_recommend,
    get_poem_by_id,
    get_user_favorite,
    attach_favorite_status,
    PoemServiceError,
)
from app.services.kimi_service import expand_keywords, KimiServiceError


router = APIRouter(prefix="/api/poems", tags=["poems"])


def _split_user_terms(prompt: str) -> list[str]:
    """把用户原始输入按常见分隔符切成词,过滤空和过长。"""
    raw = re.split(r"[\s,,。.、/;;]+", prompt)
    return [t.strip() for t in raw if t.strip() and len(t.strip()) <= 10]


def _merge_keep_order(*lists: list[str]) -> list[str]:
    """多个列表合并,去重保持顺序。"""
    seen = set()
    merged = []
    for lst in lists:
        for item in lst:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


@router.get("/recommend")
async def recommend(
    prompt: Optional[str] = Query(None, max_length=100),
    count: int = Query(1, ge=1, le=5),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """诗词推荐(游客可访问)"""
    user_id = current_user.id if current_user else None

    # 用于响应字段:把所有传给 service 的检索词合并展示给前端
    display_keywords: list[str] = []

    if prompt and prompt.strip():
        user_prompt = prompt.strip()
        user_terms = _split_user_terms(user_prompt)

        # 调 Kimi 拆分意图
        try:
            extracted = await expand_keywords(user_prompt)
        except KimiServiceError:
            # 降级:全部用户原词当 keywords
            extracted = {"authors": [], "dynasties": [], "keywords": user_terms}

        kimi_authors = extracted.get("authors", [])
        kimi_dynasties = extracted.get("dynasties", [])
        kimi_keywords = extracted.get("keywords", [])

        # 兜底:把用户原始输入也合并到 keywords 里(放前面),
        # 确保即使 Kimi 没把"曹操"识别成 author,也能被 LIKE 命中
        merged_keywords = _merge_keep_order(user_terms, kimi_keywords)

        # 调推荐
        try:
            poems = prompt_recommend(
                db,
                user_id,
                keywords=merged_keywords,
                authors=kimi_authors,
                dynasties=kimi_dynasties,
                count=count,
            )
        except PoemServiceError as e:
            return error(e.code, e.message)

        # prompt 模式没匹配到 → 走随机兜底
        if not poems:
            poems = random_recommend(db, user_id, count)

        # 给前端展示用:作者 / 朝代 / 关键词 全部合并(顺序:作者 > 朝代 > 关键词)
        display_keywords = _merge_keep_order(
            kimi_authors, kimi_dynasties, merged_keywords
        )
    else:
        # 随机模式
        try:
            poems = random_recommend(db, user_id, count)
        except PoemServiceError as e:
            return error(e.code, e.message)

    # 收藏状态
    if current_user:
        poems_with_status = attach_favorite_status(db, current_user.id, poems)
    else:
        poems_with_status = [
            {
                "id": p.id, "title": p.title, "author": p.author,
                "dynasty": p.dynasty, "content": p.content, "type": p.type,
                "tags": p.tags or [], "is_favorited": False,
            }
            for p in poems
        ]

    return success({
        "poems": poems_with_status,
        "prompt_keywords": display_keywords,
    })


@router.get("/{poem_id}")
def get_poem(
    poem_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """诗词详情(游客可访问)"""
    try:
        poem = get_poem_by_id(db, poem_id)
    except PoemServiceError as e:
        return error(e.code, e.message)

    data = {
        "id": poem.id, "title": poem.title, "author": poem.author,
        "dynasty": poem.dynasty, "content": poem.content, "type": poem.type,
        "tags": poem.tags or [],
        "is_favorited": False, "favorite_info": None,
    }

    if current_user:
        favorite = get_user_favorite(db, current_user.id, poem.id)
        if favorite:
            data["is_favorited"] = True
            data["favorite_info"] = {
                "user_tags": favorite.user_tags or [],
                "note": favorite.note,
                "created_at": favorite.created_at.isoformat(),
            }

    return success(data)