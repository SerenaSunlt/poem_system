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


def _parse_seen_ids(seen_ids_str: str | None) -> set[int]:
    """把前端传的逗号分隔字符串转成 set[int]"""
    if not seen_ids_str:
        return set()
    result = set()
    for part in seen_ids_str.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


@router.get("/recommend")
async def recommend(
        prompt: str | None = Query(None, max_length=100),
        count: int = Query(1, ge=1, le=5),
        seen_ids: str | None = Query(None, description="已展示过的诗 ID,逗号分隔"),
        db: Session = Depends(get_db),
        current_user: User | None = Depends(get_current_user_optional),
):
    """
    诗词推荐(游客可访问)。

    流程:
    1. 没 prompt → 走随机
    2. 有 prompt → Kimi 解析 intent,按 intent 走对应路径:
       - intent=random → 走随机(用户输了"换一首"这种)
       - intent=verse  → 用 verse_phrase 全文匹配
       - intent=specific → 用 title/authors/dynasties 精确匹配
       - intent=scene → 用 keywords 模糊匹配
    3. 精准路径(verse/specific)若没结果,降级到 scene
    4. scene 仍没结果,最后兜底随机
    """
    user_id = current_user.id if current_user else None
    seen_ids_set = _parse_seen_ids(seen_ids)

    extracted = {
        "intent": "random",
        "verse_phrase": None,
        "title": None,
        "authors": [],
        "dynasties": [],
        "keywords": [],
    }
    is_random_load = True  # 是否是无意义推荐(决定前端是否需要清空 seen)

    if prompt and prompt.strip():
        try:
            extracted = await expand_keywords(prompt)
        except KimiServiceError:
            # Kimi 挂了,把整段 prompt 当一个关键词降级处理
            extracted = {
                "intent": "scene",
                "verse_phrase": None,
                "title": None,
                "authors": [],
                "dynasties": [],
                "keywords": [prompt.strip()],
            }

        intent = extracted.get("intent", "scene")

        if intent == "random":
            # 用户意图是"换一个",走随机
            poems = random_recommend(
                db, user_id, count, exclude_ids=seen_ids_set
            )
            is_random_load = True
        else:
            # verse / specific / scene 都走 prompt_recommend
            try:
                poems = prompt_recommend(
                    db,
                    user_id,
                    intent=intent,
                    verse_phrase=extracted.get("verse_phrase"),
                    title=extracted.get("title"),
                    keywords=extracted.get("keywords") or [],
                    authors=extracted.get("authors") or [],
                    dynasties=extracted.get("dynasties") or [],
                    seen_ids=seen_ids_set,
                    count=count,
                )
            except PoemServiceError as e:
                return error(e.code, e.message)

            # 没匹配到,降级随机
            if not poems:
                poems = random_recommend(
                    db, user_id, count, exclude_ids=seen_ids_set
                )
                is_random_load = True
            else:
                is_random_load = False
    else:
        # 没 prompt,纯随机(场景 4)
        try:
            poems = random_recommend(
                db, user_id, count, exclude_ids=seen_ids_set
            )
        except PoemServiceError as e:
            return error(e.code, e.message)
        is_random_load = True

    # 附加收藏状态
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

    # 给前端展示用的扁平 chip 数组
    flat_keywords = []
    if extracted.get("verse_phrase"):
        flat_keywords.append(f"「{extracted['verse_phrase']}」")
    if extracted.get("title"):
        flat_keywords.append(f"《{extracted['title']}》")
    flat_keywords.extend(extracted.get("authors") or [])
    flat_keywords.extend(extracted.get("dynasties") or [])
    flat_keywords.extend(extracted.get("keywords") or [])

    return success({
        "poems": poems_with_status,
        "prompt_keywords": flat_keywords,
        "intent": extracted.get("intent", "random"),
        "is_random_load": is_random_load,
        "exhausted": len(poems) == 0,
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