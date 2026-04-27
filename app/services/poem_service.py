# app/services/poem_service.py
import random
from typing import Optional, List, Set

from sqlalchemy import func, not_, or_, case, literal_column
from sqlalchemy.orm import Session

from app.models import Poem, Favorite, Dislike


class PoemServiceError(Exception):
    """诗词服务相关业务错误"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


# ===== 内部工具 =====

def _get_disliked_poem_ids(db: Session, user_id: Optional[int]) -> Set[int]:
    if user_id is None:
        return set()
    rows = db.query(Dislike.poem_id).filter(Dislike.user_id == user_id).all()
    return {row[0] for row in rows}


def _get_favorited_poem_ids(
        db: Session, user_id: int, poem_ids: List[int]
) -> Set[int]:
    if not poem_ids:
        return set()
    rows = (
        db.query(Favorite.poem_id)
        .filter(Favorite.user_id == user_id, Favorite.poem_id.in_(poem_ids))
        .all()
    )
    return {row[0] for row in rows}


# ===== 推荐 =====

def random_recommend(
        db: Session,
        user_id: Optional[int],
        count: int = 1,
) -> List[Poem]:
    """随机推荐 count 首诗,排除用户已 dislike 的"""
    if count < 1 or count > 5:
        raise PoemServiceError(1001, "count 必须在 1~5 之间")

    disliked_ids = _get_disliked_poem_ids(db, user_id)

    max_id = db.query(func.max(Poem.id)).scalar()
    if not max_id:
        return []

    selected: List[Poem] = []
    selected_ids: Set[int] = set()

    max_attempts = max(count * 10, 50)
    attempts = 0

    while len(selected) < count and attempts < max_attempts:
        attempts += 1
        random_id = random.randint(1, max_id)

        excluded_ids = selected_ids | disliked_ids
        query = db.query(Poem).filter(Poem.id >= random_id)
        if excluded_ids:
            query = query.filter(not_(Poem.id.in_(excluded_ids)))

        poem = query.order_by(Poem.id).first()

        if poem is None:
            query = db.query(Poem)
            if excluded_ids:
                query = query.filter(not_(Poem.id.in_(excluded_ids)))
            poem = query.order_by(Poem.id).first()

        if poem and poem.id not in selected_ids:
            selected.append(poem)
            selected_ids.add(poem.id)

    return selected


def prompt_recommend(
        db: Session,
        user_id: Optional[int],
        keywords: Optional[List[str]] = None,
        authors: Optional[List[str]] = None,
        dynasties: Optional[List[str]] = None,
        count: int = 3,
) -> List[Poem]:
    """
    基于结构化检索意图推荐:
    - 标题命中关键词 +50 分(精准命中)
    - 作者命中 +10 分
    - 朝代命中 +3 分
    - 关键词内容命中 +1 分

    高分(>=50)精准命中不参与随机,按分数顺序取;低分用随机抽样保证多样性。
    """
    if count < 1 or count > 5:
        raise PoemServiceError(1001, "count 必须在 1~5 之间")

    keywords = keywords or []
    authors = authors or []
    dynasties = dynasties or []

    if not keywords and not authors and not dynasties:
        return []

    disliked_ids = _get_disliked_poem_ids(db, user_id)

    score_exprs = []
    or_filters = []

    # 关键词:标题命中权重 +50,内容命中 +1
    for kw in keywords:
        like_pattern = f"%{kw}%"
        title_hit = Poem.title.like(like_pattern)
        text_hit = Poem.search_text.like(like_pattern)
        score_exprs.append(case((title_hit, 50), else_=0))
        score_exprs.append(case((text_hit, 1), else_=0))
        or_filters.append(text_hit)

    # 作者权重 +10
    for author in authors:
        condition = (Poem.author == author)
        score_exprs.append(case((condition, 10), else_=0))
        or_filters.append(condition)

    # 朝代权重 +3
    for dynasty in dynasties:
        condition = (Poem.dynasty == dynasty)
        score_exprs.append(case((condition, 3), else_=0))
        or_filters.append(condition)

    if not score_exprs:
        return []

    score = sum(score_exprs[1:], score_exprs[0]).label("score")

    query = db.query(Poem, score).filter(or_(*or_filters))
    if disliked_ids:
        query = query.filter(~Poem.id.in_(disliked_ids))

    candidates = (
        query.order_by(literal_column("score").desc(), Poem.id)
        .limit(count * 5)
        .all()
    )

    if not candidates:
        return []

    # 高分精准命中(>=50,即标题命中):不参与随机,按分数顺序取前 count 条
    HIGH_SCORE_THRESHOLD = 50
    high_score = [(p, s) for p, s in candidates if s >= HIGH_SCORE_THRESHOLD]

    if high_score:
        selected = high_score[:count]
    else:
        # 中低分:随机抽,保证多样性
        selected = random.sample(candidates, min(count, len(candidates)))

    return [poem for poem, _score in selected]


# ===== 详情 =====

def get_poem_by_id(db: Session, poem_id: int) -> Poem:
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise PoemServiceError(2001, "诗词不存在")
    return poem


def get_user_favorite(
        db: Session, user_id: int, poem_id: int
) -> Optional[Favorite]:
    return (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.poem_id == poem_id)
        .first()
    )


def attach_favorite_status(
        db: Session,
        user_id: int,
        poems: List[Poem],
) -> List[dict]:
    poem_ids = [p.id for p in poems]
    favorited_ids = _get_favorited_poem_ids(db, user_id, poem_ids)

    result = []
    for poem in poems:
        result.append({
            "id": poem.id,
            "title": poem.title,
            "author": poem.author,
            "dynasty": poem.dynasty,
            "content": poem.content,
            "content_simplified": poem.content_simplified or poem.content,
            "type": poem.type,
            "tags": poem.tags or [],
            "is_favorited": poem.id in favorited_ids,
        })
    return result