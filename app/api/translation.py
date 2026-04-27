# app/api/translation.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas.common import success, error
from app.schemas.translation import SaveTranslationIn
from app.services.translation_service import (
    get_translation,
    upsert_translation,
    request_translation,
    TranslationServiceError,
)

router = APIRouter(prefix="/api/translations", tags=["translations"])


@router.get("/{poem_id}")
def get_my_translation(
        poem_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """查询用户对某首诗的翻译(已保存的)"""
    record = get_translation(db, user_id=current_user.id, poem_id=poem_id)
    if not record:
        return success({
            "poem_id": poem_id,
            "is_saved": False,
            "translation": None,
        })

    return success({
        "poem_id": record.poem_id,
        "is_saved": True,
        "translation": record.translation_data,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    })


@router.post("/{poem_id}")
async def create_translation(
        poem_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """触发翻译(调 Kimi)。返回翻译结果但不入库,前端拿到后展示给用户。"""
    try:
        translation = await request_translation(
            db, user_id=current_user.id, poem_id=poem_id
        )
    except TranslationServiceError as e:
        return error(e.code, e.message)

    return success({
        "poem_id": poem_id,
        "is_saved": False,
        "translation": translation,
    })


@router.put("/{poem_id}")
def save_translation(
        poem_id: int,
        payload: SaveTranslationIn,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """保存翻译到数据库(用户点'保存'时调)"""
    try:
        record = upsert_translation(
            db,
            user_id=current_user.id,
            poem_id=poem_id,
            translation_data=payload.translation.model_dump(),
        )
    except TranslationServiceError as e:
        return error(e.code, e.message)

    return success({
        "poem_id": record.poem_id,
        "is_saved": True,
        "translation": record.translation_data,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    })