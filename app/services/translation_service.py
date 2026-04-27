# app/services/translation_service.py
import time
from collections import defaultdict
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Translation, Poem
from app.services.kimi_service import translate_poem as kimi_translate_poem, KimiServiceError


class TranslationServiceError(Exception):
    """翻译服务相关业务错误"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


# ============ 简单限流(进程内内存) ============

# {user_id: [timestamp1, timestamp2, ...]}
# 每次调用时,清掉超过 60 秒的记录,看剩下的数量
_rate_limit_store: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60.0  # 60 秒窗口
RATE_LIMIT_MAX = 5  # 窗口内最多 5 次


def _check_rate_limit(user_id: int) -> None:
    """检查用户是否触发限流。触发则抛 TranslationServiceError。"""
    now = time.time()
    history = _rate_limit_store[user_id]

    # 清掉过期的(超过 60 秒)
    cutoff = now - RATE_LIMIT_WINDOW
    history[:] = [t for t in history if t > cutoff]

    if len(history) >= RATE_LIMIT_MAX:
        # 算还要等多久
        wait = int(RATE_LIMIT_WINDOW - (now - history[0])) + 1
        raise TranslationServiceError(
            3001,
            f"翻译过于频繁,请 {wait} 秒后再试"
        )

    # 记录这次
    history.append(now)


# ============ 数据库 CRUD ============

def get_translation(
        db: Session,
        user_id: int,
        poem_id: int,
) -> Optional[Translation]:
    """查询用户对某首诗的翻译,没有返回 None"""
    return (
        db.query(Translation)
        .filter(Translation.user_id == user_id, Translation.poem_id == poem_id)
        .first()
    )


def upsert_translation(
        db: Session,
        user_id: int,
        poem_id: int,
        translation_data: dict,
) -> Translation:
    """新建或更新翻译记录"""
    # 验证诗存在
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise TranslationServiceError(2001, "诗词不存在")

    existing = get_translation(db, user_id, poem_id)

    if existing:
        existing.translation_data = translation_data
        try:
            db.commit()
            db.refresh(existing)
        except IntegrityError:
            db.rollback()
            raise TranslationServiceError(3002, "保存翻译失败")
        return existing

    record = Translation(
        user_id=user_id,
        poem_id=poem_id,
        translation_data=translation_data,
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        # 并发兜底:重读
        existing = get_translation(db, user_id, poem_id)
        if existing:
            return existing
        raise TranslationServiceError(3002, "保存翻译失败")
    return record


# ============ 翻译流程(调 Kimi) ============

async def request_translation(
        db: Session,
        user_id: int,
        poem_id: int,
) -> dict:
    """
    调 Kimi 翻译一首诗,返回翻译数据(不入库)。

    流程:
    1. 限流检查
    2. 查诗是否存在
    3. 调 Kimi
    4. 返回翻译结果(由 API 层决定要不要入库)
    """
    _check_rate_limit(user_id)

    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise TranslationServiceError(2001, "诗词不存在")

    # 翻译用简体内容,如果没有 fallback 到 content
    content = poem.content_simplified or poem.content

    try:
        result = await kimi_translate_poem(
            title=poem.title,
            author=poem.author,
            dynasty=poem.dynasty,
            content=content,
        )
    except KimiServiceError as e:
        raise TranslationServiceError(3003, str(e))

    return result