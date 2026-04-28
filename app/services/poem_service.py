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
    exclude_ids: Optional[Set[int]] = None,
) -> List[Poem]:
    """随机推荐 count 首诗,排除用户已 dislike 的 + 调用方传入的 exclude_ids"""
    if count < 1 or count > 5:
        raise PoemServiceError(1001, "count 必须在 1~5 之间")

    disliked_ids = _get_disliked_poem_ids(db, user_id)
    exclude_ids = exclude_ids or set()
    excluded_all = disliked_ids | exclude_ids

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

        skip_ids = selected_ids | excluded_all
        query = db.query(Poem).filter(Poem.id >= random_id)
        if skip_ids:
            query = query.filter(not_(Poem.id.in_(skip_ids)))

        poem = query.order_by(Poem.id).first()

        if poem is None:
            query = db.query(Poem)
            if skip_ids:
                query = query.filter(not_(Poem.id.in_(skip_ids)))
            poem = query.order_by(Poem.id).first()

        if poem and poem.id not in selected_ids:
            selected.append(poem)
            selected_ids.add(poem.id)

    return selected


def prompt_recommend(
    db: Session,
    user_id: Optional[int],
    intent: str = "scene",
    verse_phrase: Optional[str] = None,
    title: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    authors: Optional[List[str]] = None,
    dynasties: Optional[List[str]] = None,
    seen_ids: Optional[Set[int]] = None,
    count: int = 1,
) -> List[Poem]:
    """
    基于结构化检索意图推荐。打分体系:
    - 诗句片段命中 +100  (intent=verse)
    - 标题精确匹配 +60   (intent=specific 时,title 字段)
    - 关键词命中标题 +50 (intent=scene 时,keyword 命中标题)
    - 作者命中 +10
    - 朝代命中 +3
    - 关键词命中正文 +1

    高分(>=50)直接按分数顺序取,不参与随机;低分用随机抽样保证多样性。
    seen_ids 中的诗会被排除,实现"换一首"的换不重复语义。
    """
    if count < 1 or count > 5:
        raise PoemServiceError(1001, "count 必须在 1~5 之间")

    keywords = keywords or []
    authors = authors or []
    dynasties = dynasties or []
    seen_ids = seen_ids or set()

    # 完全没条件,返回空(由调用方走随机)
    if not (verse_phrase or title or keywords or authors or dynasties):
        return []

    disliked_ids = _get_disliked_poem_ids(db, user_id)
    excluded_ids = disliked_ids | seen_ids

    score_exprs = []
    or_filters = []

    # 诗句片段全文匹配 +100(用 content_simplified)
    if verse_phrase:
        verse_pattern = f"%{verse_phrase}%"
        verse_hit = Poem.content_simplified.like(verse_pattern)
        score_exprs.append(case((verse_hit, 100), else_=0))
        or_filters.append(verse_hit)

    # 标题精确匹配 +60(intent=specific 用)
    if title:
        title_exact = (Poem.title == title)
        title_like = Poem.title.like(f"%{title}%")
        score_exprs.append(case((title_exact, 60), else_=0))
        # 模糊命中标题加 50,跟下面 keyword 命中标题同等
        score_exprs.append(case((title_like, 50), else_=0))
        or_filters.append(title_like)

    # 关键词命中标题 +50,命中正文 +1
    for kw in keywords:
        like_pattern = f"%{kw}%"
        title_hit = Poem.title.like(like_pattern)
        text_hit = Poem.search_text.like(like_pattern)
        score_exprs.append(case((title_hit, 50), else_=0))
        score_exprs.append(case((text_hit, 1), else_=0))
        or_filters.append(text_hit)

    # 作者 +10
    for author in authors:
        condition = (Poem.author == author)
        score_exprs.append(case((condition, 10), else_=0))
        or_filters.append(condition)

    # 朝代 +3
    for dynasty in dynasties:
        condition = (Poem.dynasty == dynasty)
        score_exprs.append(case((condition, 3), else_=0))
        or_filters.append(condition)

    if not score_exprs:
        return []

    score = sum(score_exprs[1:], score_exprs[0]).label("score")

    query = db.query(Poem, score).filter(or_(*or_filters))
    if excluded_ids:
        query = query.filter(~Poem.id.in_(excluded_ids))

    # 候选量:取多一点,保证"换一首"够换
    candidate_limit = max(count * 10, 20)
    candidates = (
        query.order_by(literal_column("score").desc(), Poem.id)
        .limit(candidate_limit)
        .all()
    )

    if not candidates:
        return []

    HIGH_SCORE_THRESHOLD = 50
    high_score = [(p, s) for p, s in candidates if s >= HIGH_SCORE_THRESHOLD]

    if high_score:
        # 高分:按分数顺序取(精准命中,不随机)
        selected = high_score[:count]
    else:
        # 低分:随机抽样,保证多样
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