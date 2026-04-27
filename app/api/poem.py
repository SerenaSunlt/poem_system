# app/api/poem.py
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
from app.services.translation_service import get_translation

router = APIRouter(prefix="/api/poems", tags=["poems"])


@router.get("/recommend")
async def recommend(
        prompt: str | None = Query(None, max_length=100),
        count: int = Query(1, ge=1, le=5),
        db: Session = Depends(get_db),
        current_user: User | None = Depends(get_current_user_optional),
):
    """诗词推荐(游客可访问)"""
    user_id = current_user.id if current_user else None

    # Kimi 解析出的结构化检索意图,默认空
    extracted = {"authors": [], "dynasties": [], "keywords": []}

    if prompt and prompt.strip():
        try:
            extracted = await expand_keywords(prompt)
        except KimiServiceError:
            # Kimi 失败就把原 prompt 当一个普通关键词
            extracted = {
                "authors": [],
                "dynasties": [],
                "keywords": [prompt.strip()],
            }

        # 用结构化意图查诗
        try:
            poems = prompt_recommend(
                db,
                user_id,
                keywords=extracted["keywords"],
                authors=extracted["authors"],
                dynasties=extracted["dynasties"],
                count=count,
            )
        except PoemServiceError as e:
            return error(e.code, e.message)

        # 没匹配到,fallback 随机
        if not poems:
            poems = random_recommend(db, user_id, count)
    else:
        try:
            poems = random_recommend(db, user_id, count)
        except PoemServiceError as e:
            return error(e.code, e.message)

    if current_user:
        poems_with_status = attach_favorite_status(db, current_user.id, poems)
    else:
        poems_with_status = [
            {
                "id": p.id, "title": p.title, "author": p.author,
                "dynasty": p.dynasty,
                "content": p.content,
                "content_simplified": p.content_simplified or p.content,
                "type": p.type,
                "tags": p.tags or [], "is_favorited": False,
            }
            for p in poems
        ]

    # 把三类合并成一个扁平数组,方便前端展示
    flat_keywords = (
            extracted["authors"]
            + extracted["dynasties"]
            + extracted["keywords"]
    )

    return success({
        "poems": poems_with_status,
        "prompt_keywords": flat_keywords,
    })


@router.get("/{poem_id}")
def get_poem(
        poem_id: int,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(get_current_user_optional),
):
    """诗词详情(游客可访问)"""
    try:
        poem = get_poem_by_id(db, poem_id)
    except PoemServiceError as e:
        return error(e.code, e.message)

    data = {
        "id": poem.id, "title": poem.title, "author": poem.author,
        "dynasty": poem.dynasty,
        "content": poem.content,
        "content_simplified": poem.content_simplified or poem.content,
        "type": poem.type,
        "tags": poem.tags or [],
        "is_favorited": False,
        "favorite_info": None,
        "has_translation": False,
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

        translation = get_translation(db, current_user.id, poem.id)
        if translation:
            data["has_translation"] = True

    return success(data)