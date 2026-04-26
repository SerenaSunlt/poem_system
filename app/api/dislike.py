# app/api/dislikes.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas.common import success, error
from app.schemas.favorite import DislikeCreateIn
from app.services.favorite_service import (
    add_dislike, remove_dislike, list_dislikes,
    FavoriteServiceError,
)

router = APIRouter(prefix="/api/dislikes", tags=["dislikes"])


@router.post("")
def create_dislike(
        payload: DislikeCreateIn,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """标记不感兴趣"""
    try:
        add_dislike(db, user_id=current_user.id, poem_id=payload.poem_id)
    except FavoriteServiceError as e:
        return error(e.code, e.message)

    return success(None)


@router.delete("/{poem_id}")
def delete_dislike(
        poem_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """取消不感兴趣"""
    remove_dislike(db, user_id=current_user.id, poem_id=poem_id)
    return success(None)


@router.get("")
def get_dislikes(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """屏蔽列表"""
    items, total = list_dislikes(
        db, user_id=current_user.id, page=page, page_size=page_size,
    )

    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "poem": {
                    "id": d.poem.id,
                    "title": d.poem.title,
                    "author": d.poem.author,
                    "dynasty": d.poem.dynasty,
                },
                "created_at": d.created_at.isoformat(),
            }
            for d in items
        ],
    })