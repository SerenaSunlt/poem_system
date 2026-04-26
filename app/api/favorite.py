# app/api/favorites.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas.common import success, error
from app.schemas.favorite import (
    FavoriteCreateIn, FavoriteUpdateIn,
)
from app.services.favorite_service import (
    add_favorite, remove_favorite, update_favorite,
    list_favorites, list_user_tags,
    FavoriteServiceError,
)

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.post("")
def create_favorite(
        payload: FavoriteCreateIn,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """添加收藏"""
    try:
        favorite = add_favorite(
            db,
            user_id=current_user.id,
            poem_id=payload.poem_id,
            user_tags=payload.user_tags,
            note=payload.note,
        )
    except FavoriteServiceError as e:
        return error(e.code, e.message)

    return success({
        "favorite_id": favorite.id,
        "poem_id": favorite.poem_id,
        "user_tags": favorite.user_tags or [],
        "note": favorite.note,
        "created_at": favorite.created_at.isoformat(),
    })


@router.delete("/{poem_id}")
def delete_favorite(
        poem_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """取消收藏"""
    try:
        remove_favorite(db, user_id=current_user.id, poem_id=poem_id)
    except FavoriteServiceError as e:
        return error(e.code, e.message)

    return success(None)


@router.patch("/{poem_id}")
def patch_favorite(
        poem_id: int,
        payload: FavoriteUpdateIn,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """修改收藏的标签或备注"""
    try:
        favorite = update_favorite(
            db,
            user_id=current_user.id,
            poem_id=poem_id,
            user_tags=payload.user_tags,
            note=payload.note,
        )
    except FavoriteServiceError as e:
        return error(e.code, e.message)

    return success({
        "favorite_id": favorite.id,
        "user_tags": favorite.user_tags or [],
        "note": favorite.note,
    })


@router.get("")
def get_favorites(
        tag: str | None = Query(None, max_length=20),
        keyword: str | None = Query(None, max_length=50),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=50),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """收藏列表"""
    items, total = list_favorites(
        db,
        user_id=current_user.id,
        tag=tag,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "favorite_id": fav.id,
                "poem": {
                    "id": fav.poem.id,
                    "title": fav.poem.title,
                    "author": fav.poem.author,
                    "dynasty": fav.poem.dynasty,
                    "content": fav.poem.content,
                    "type": fav.poem.type,
                },
                "user_tags": fav.user_tags or [],
                "note": fav.note,
                "created_at": fav.created_at.isoformat(),
            }
            for fav in items
        ],
    })


@router.get("/tags")
def get_my_tags(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """我用过的所有标签 + 每个标签的使用次数"""
    tags = list_user_tags(db, user_id=current_user.id)
    return success({"tags": tags})