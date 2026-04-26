# app/api/poems.py
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


@router.get("/recommend")
async def recommend(
        prompt: str | None = Query(None, max_length=100),
        count: int = Query(1, ge=1, le=5),
        db: Session = Depends(get_db),
        current_user: User | None = Depends(get_current_user_optional),
):
    """诗词推荐(游客可访问)"""
    user_id = current_user.id if current_user else None
    keywords: list[str] = []

    if prompt and prompt.strip():
        try:
            keywords = await expand_keywords(prompt)
        except KimiServiceError:
            keywords = [prompt.strip()]

        try:
            poems = prompt_recommend(db, user_id, keywords, count)
        except PoemServiceError as e:
            return error(e.code, e.message)

        if not poems:
            poems = random_recommend(db, user_id, count)
    else:
        try:
            poems = random_recommend(db, user_id, count)
        except PoemServiceError as e:
            return error(e.code, e.message)

    # 游客没有收藏状态,统一返回 false
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
        "prompt_keywords": keywords,
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