# app/services/favorite_service.py
from typing import Optional, List, Tuple
from collections import Counter
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Favorite, Dislike, Poem


class FavoriteServiceError(Exception):
    """收藏/屏蔽相关业务错误"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


# ============ 收藏 ============

def add_favorite(
        db: Session,
        user_id: int,
        poem_id: int,
        user_tags: Optional[List[str]] = None,
        note: Optional[str] = None,
) -> Favorite:
    """添加收藏"""
    # 检查诗存在
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise FavoriteServiceError(2001, "诗词不存在")

    # 检查是否已收藏
    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.poem_id == poem_id)
        .first()
    )
    if existing:
        raise FavoriteServiceError(2002, "已收藏过该诗词")

    # 标签去重 + 清理空字符串
    cleaned_tags = _clean_tags(user_tags)

    favorite = Favorite(
        user_id=user_id,
        poem_id=poem_id,
        user_tags=cleaned_tags,
        note=note,
    )
    db.add(favorite)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise FavoriteServiceError(2002, "已收藏过该诗词")
    db.refresh(favorite)
    return favorite


def remove_favorite(db: Session, user_id: int, poem_id: int) -> None:
    """取消收藏"""
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.poem_id == poem_id)
        .first()
    )
    if not favorite:
        raise FavoriteServiceError(2003, "收藏不存在")

    db.delete(favorite)
    db.commit()


def update_favorite(
        db: Session,
        user_id: int,
        poem_id: int,
        user_tags: Optional[List[str]] = None,
        note: Optional[str] = None,
) -> Favorite:
    """修改收藏的标签或备注。字段为 None 表示不修改。"""
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.poem_id == poem_id)
        .first()
    )
    if not favorite:
        raise FavoriteServiceError(2003, "收藏不存在")

    if user_tags is not None:
        favorite.user_tags = _clean_tags(user_tags)
    if note is not None:
        favorite.note = note

    db.commit()
    db.refresh(favorite)
    return favorite


def list_favorites(
        db: Session,
        user_id: int,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
) -> Tuple[List[Favorite], int]:
    """查询收藏列表,支持标签和关键词筛选 + 分页"""
    from sqlalchemy import text

    query = (
        db.query(Favorite)
        .join(Poem, Favorite.poem_id == Poem.id)
        .filter(Favorite.user_id == user_id)
    )

    # 标签筛选:用 MySQL 的 JSON_CONTAINS
    if tag:
        query = query.filter(
            text("JSON_CONTAINS(favorites.user_tags, :tag_json)")
        ).params(tag_json=f'"{tag}"')

    # 关键词筛选:在诗的标题、作者、纯文本里搜
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(
                Poem.title.like(kw),
                Poem.author.like(kw),
                Poem.content_plain.like(kw),
            )
        )

    total = query.count()

    items = (
        query.order_by(Favorite.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return items, total


def list_user_tags(db: Session, user_id: int) -> List[dict]:
    """
    统计用户用过的所有标签 + 每个标签下的收藏数。
    """
    rows = db.query(Favorite.user_tags).filter(Favorite.user_id == user_id).all()

    counter: Counter = Counter()
    for row in rows:
        tags = row[0] or []
        for tag in tags:
            if tag:  # 排除空标签
                counter[tag] += 1

    # 按使用次数倒序
    return [
        {"name": name, "count": count}
        for name, count in counter.most_common()
    ]


# ============ 不感兴趣 ============

def add_dislike(db: Session, user_id: int, poem_id: int) -> Dislike:
    """标记不感兴趣"""
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise FavoriteServiceError(2001, "诗词不存在")

    existing = (
        db.query(Dislike)
        .filter(Dislike.user_id == user_id, Dislike.poem_id == poem_id)
        .first()
    )
    if existing:
        # 重复标记不算错误,直接返回已有记录
        return existing

    dislike = Dislike(user_id=user_id, poem_id=poem_id)
    db.add(dislike)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # 并发兜底
        return (
            db.query(Dislike)
            .filter(Dislike.user_id == user_id, Dislike.poem_id == poem_id)
            .first()
        )
    db.refresh(dislike)
    return dislike


def remove_dislike(db: Session, user_id: int, poem_id: int) -> None:
    """取消不感兴趣"""
    dislike = (
        db.query(Dislike)
        .filter(Dislike.user_id == user_id, Dislike.poem_id == poem_id)
        .first()
    )
    if not dislike:
        # 不存在也算成功(幂等)
        return

    db.delete(dislike)
    db.commit()


def list_dislikes(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
) -> Tuple[List[Dislike], int]:
    """查询屏蔽列表"""
    query = (
        db.query(Dislike)
        .join(Poem, Dislike.poem_id == Poem.id)
        .filter(Dislike.user_id == user_id)
    )
    total = query.count()
    items = (
        query.order_by(Dislike.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


# ============ 工具函数 ============

def _clean_tags(tags: Optional[List[str]]) -> List[str]:
    """清理标签:去空、去前后空格、去重(保持顺序)、限长"""
    if not tags:
        return []
    seen = set()
    cleaned = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        tag = tag.strip()
        if not tag:
            continue
        if len(tag) > 20:
            tag = tag[:20]
        if tag in seen:
            continue
        seen.add(tag)
        cleaned.append(tag)
    return cleaned[:10]  # 最多 10 个