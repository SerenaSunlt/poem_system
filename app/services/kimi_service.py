# app/services/kimi_service.py
import asyncio
from collections import OrderedDict
import time
import json
import logging
from typing import List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# 简单的内存缓存,LRU + TTL
class _SimpleCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 86400):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.store: OrderedDict[str, tuple[float, list]] = OrderedDict()
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[List[str]]:
        async with self.lock:
            if key not in self.store:
                return None
            timestamp, value = self.store[key]
            if time.time() - timestamp > self.ttl:
                del self.store[key]
                return None
            # LRU:命中后移到末尾
            self.store.move_to_end(key)
            return value

    async def set(self, key: str, value: List[str]):
        async with self.lock:
            self.store[key] = (time.time(), value)
            self.store.move_to_end(key)
            # 淘汰最旧的
            while len(self.store) > self.max_size:
                self.store.popitem(last=False)


_cache = _SimpleCache(max_size=500, ttl_seconds=86400)  # 24 小时

# System prompt:角色 + 任务 + 输出格式
SYSTEM_PROMPT = """你是一个中国古典诗词检索助手。

你的任务是:把用户输入的场景、情绪或检索意图,解析为结构化的检索条件,用于在古诗词数据库中检索。

输出三类信息:
1. authors:用户明确提到的诗人名字。请使用诗人的标准姓名(例如"苏东坡"应规范化为"苏轼","太白"应规范化为"李白","易安居士"规范化为"李清照")。如果用户没提诗人,返回空数组。
2. dynasties:用户提到的朝代。请严格使用以下单字或词:唐、宋、元、明、清、汉、魏晋、南北朝。诗经/楚辞时代统一用"先秦"。如果用户说"唐朝"、"唐代",规范化为"唐"。如果用户没提朝代,返回空数组。
3. keywords:5~8 个适合在古诗词数据库中做关键词检索的词:
   - 优先用古诗常见的意象、季节、自然景物、情感词
   - 优先用单字或双字词,贴近古诗用词(用"暮"而非"傍晚",用"舟"而非"船",用"月"而非"月亮")
   - 包含字面词和意境延伸词
   - 如果用户只提了诗人或朝代没提具体场景,keywords 可以为空数组

示例 1:
输入:"李白写的关于月亮的诗"
输出:{"authors": ["李白"], "dynasties": [], "keywords": ["月", "明月", "夜"]}

示例 2:
输入:"西湖傍晚"
输出:{"authors": [], "dynasties": [], "keywords": ["西湖", "湖", "暮", "夕阳", "晚霞"]}

示例 3:
输入:"宋词 思乡"
输出:{"authors": [], "dynasties": ["宋"], "keywords": ["故乡", "思", "归", "乡"]}

示例 4:
输入:"东坡"
输出:{"authors": ["苏轼"], "dynasties": [], "keywords": []}

严格按 JSON 格式返回,不要任何其他文字:
{"authors": [...], "dynasties": [...], "keywords": [...]}"""


class KimiServiceError(Exception):
    """Kimi 调用失败"""
    pass


async def expand_keywords(prompt: str, timeout: float = 10.0) -> List[str]:
    """调用 Kimi 扩展关键词,带缓存。"""
    if not prompt or not prompt.strip():
        return []

    cache_key = prompt.strip().lower()

    # 先查缓存
    cached = await _cache.get(cache_key)
    if cached is not None:
        logger.info(f"Kimi 缓存命中: {prompt}")
        return cached

    # 调 Kimi(把原来 expand_keywords 的核心逻辑搬这里)
    keywords = await _call_kimi(prompt, timeout)

    # 写缓存
    await _cache.set(cache_key, keywords)
    return keywords

from typing import TypedDict

class KeywordExtractResult(TypedDict):
    authors: List[str]
    dynasties: List[str]
    keywords: List[str]
async def _call_kimi(prompt: str, timeout: float) -> List[str]:
    """实际调用 Kimi 的内部函数(无缓存)"""
    if not settings.kimi_api_key:
        raise KimiServiceError("Kimi API key 未配置")

    payload = {
        "model": settings.kimi_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt.strip()},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.kimi_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.kimi_base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.warning(f"Kimi 调用超时, prompt={prompt}")
        raise KimiServiceError("Kimi 服务超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"Kimi HTTP 错误: {e.response.status_code} {e.response.text}")
        raise KimiServiceError(f"Kimi 服务错误: {e.response.status_code}")
    except Exception as e:
        logger.exception(f"Kimi 调用异常: {e}")
        raise KimiServiceError("Kimi 服务异常")

    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        keywords = parsed.get("keywords", [])
        if not isinstance(keywords, list):
            raise ValueError("keywords 不是数组")
        cleaned = []
        seen = set()
        for kw in keywords:
            if not isinstance(kw, str):
                continue
            kw = kw.strip()
            if not kw or kw in seen:
                continue
            if len(kw) > 10:
                kw = kw[:10]
            seen.add(kw)
            cleaned.append(kw)
        return cleaned[:8]
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Kimi 返回解析失败: {data}, error: {e}")
        raise KimiServiceError("Kimi 返回格式错误")

