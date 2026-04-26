# app/services/poem_service.py
import random
from typing import Optional, List, Set
from sqlalchemy import func, and_, not_
from sqlalchemy.orm import Session

from app.models import Poem, Favorite, Dislike


class PoemServiceError(Exception):
    """诗词服务相关业务错误"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def _get_disliked_poem_ids(db: Session, user_id: int | None) -> Set[int]:
    """获取用户屏蔽的所有 poem_id 集合;游客返回空集"""
    if user_id is None:
        return set()
    rows = db.query(Dislike.poem_id).filter(Dislike.user_id == user_id).all()
    return {row[0] for row in rows}


def _get_favorited_poem_ids(db: Session, user_id: int, poem_ids: List[int]) -> Set[int]:
    """批量查询给定 poem_ids 中,用户收藏过的子集"""
    if not poem_ids:
        return set()
    rows = (
        db.query(Favorite.poem_id)
        .filter(Favorite.user_id == user_id, Favorite.poem_id.in_(poem_ids))
        .all()
    )
    return {row[0] for row in rows}


def random_recommend(
        db: Session,
        user_id: int,
        count: int = 1,
) -> List[Poem]:
    """
    随机推荐 count 首诗,排除用户已 dislike 的。

    实现策略:用 ID 范围随机,而不是 ORDER BY RAND()。
    """
    if count < 1 or count > 5:
        raise PoemServiceError(1001, "count 必须在 1~5 之间")

    # 拿到屏蔽集合
    disliked_ids = _get_disliked_poem_ids(db, user_id)

    # 拿最大 ID
    max_id = db.query(func.max(Poem.id)).scalar()
    if not max_id:
        return []  # 库里没诗

    # 反复抽样,凑够 count 首不重复且不在 dislike 中的
    selected: List[Poem] = []
    selected_ids: Set[int] = set()

    # 防死循环:最多尝试 count * 10 次
    max_attempts = max(count * 10, 50)
    attempts = 0

    while len(selected) < count and attempts < max_attempts:
        attempts += 1
        random_id = random.randint(1, max_id)

        # 取 id >= random_id 的第一条,排除已抽中和已屏蔽
        excluded_ids = selected_ids | disliked_ids
        query = db.query(Poem).filter(Poem.id >= random_id)
        if excluded_ids:
            query = query.filter(not_(Poem.id.in_(excluded_ids)))

        poem = query.order_by(Poem.id).first()

        # 如果没找到(随机 ID 太靠后),回头从 1 开始找一次
        if poem is None:
            query = db.query(Poem)
            if excluded_ids:
                query = query.filter(not_(Poem.id.in_(excluded_ids)))
            poem = query.order_by(Poem.id).first()

        if poem and poem.id not in selected_ids:
            selected.append(poem)
            selected_ids.add(poem.id)

    return selected


def get_poem_by_id(db: Session, poem_id: int) -> Poem:
    """根据 ID 获取诗词详情,不存在抛业务异常"""
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise PoemServiceError(2001, "诗词不存在")
    return poem


def get_user_favorite(db: Session, user_id: int, poem_id: int) -> Optional[Favorite]:
    """获取用户对某首诗的收藏记录,没有则返回 None"""
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
    """
    给一批诗词附加 is_favorited 字段,返回 dict 列表(便于直接序列化)。
    """
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
            "type": poem.type,
            "tags": poem.tags or [],
            "is_favorited": poem.id in favorited_ids,
        })
    return result


# app/services/poem_service.py(在文件末尾追加)
from sqlalchemy import or_, case, literal_column


def prompt_recommend(
        db: Session,
        user_id: int | None,
        keywords: List[str],
        count: int = 3,
) -> List[Poem]:
    """基于关键词推荐"""
    if count < 1 or count > 5:
        raise PoemServiceError(1001, "count 必须在 1~5 之间")

    if not keywords:
        return []

    disliked_ids = _get_disliked_poem_ids(db, user_id)

    score_exprs = []
    or_filters = []
    for kw in keywords:
        like_pattern = f"%{kw}%"
        condition = Poem.search_text.like(like_pattern)
        score_exprs.append(case((condition, 1), else_=0))
        or_filters.append(condition)

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

    selected = random.sample(candidates, min(count, len(candidates)))
    return [poem for poem, _score in selected]