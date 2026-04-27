# app/services/kimi_service.py
import asyncio
import json
import logging
import time
from collections import OrderedDict
from typing import List, Optional, TypedDict

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


# ===== 数据结构 =====

class KeywordExtractResult(TypedDict):
    """Kimi 解析出的结构化检索意图"""
    authors: List[str]
    dynasties: List[str]
    keywords: List[str]


class KimiServiceError(Exception):
    """Kimi 调用失败"""
    pass


# ===== 缓存 =====

class _SimpleCache:
    """LRU + TTL 内存缓存"""

    def __init__(self, max_size: int = 500, ttl_seconds: int = 86400):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.store: "OrderedDict[str, tuple[float, KeywordExtractResult]]" = OrderedDict()
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[KeywordExtractResult]:
        async with self.lock:
            if key not in self.store:
                return None
            timestamp, value = self.store[key]
            if time.time() - timestamp > self.ttl:
                del self.store[key]
                return None
            self.store.move_to_end(key)
            return value

    async def set(self, key: str, value: KeywordExtractResult):
        async with self.lock:
            self.store[key] = (time.time(), value)
            self.store.move_to_end(key)
            while len(self.store) > self.max_size:
                self.store.popitem(last=False)


_cache = _SimpleCache(max_size=500, ttl_seconds=86400)


# ===== Prompt 设计 =====

SYSTEM_PROMPT = """你是一个中国古典诗词检索助手。

你的任务是:把用户输入的描述,解析为结构化的检索条件,用于在古诗词数据库中检索。

输出三类信息:
1. authors:用户明确提到的诗人名字。请使用诗人的标准姓名(例如"苏东坡"应规范化为"苏轼","太白"应规范化为"李白","易安居士"规范化为"李清照")。如果用户没提诗人,返回空数组。
2. dynasties:用户提到的朝代。请严格使用以下单字或词:唐、宋、元、明、清、汉、魏晋、南北朝。诗经/楚辞时代统一用"先秦"。如果用户说"唐朝"、"唐代",规范化为"唐"。如果用户没提朝代,返回空数组。
3. keywords:适合在古诗词数据库中做关键词检索的词:
   - 如果用户输入像诗名(2-5 字精炼词,可能跟作者一起出现),把它作为 keywords 的第一项,用于匹配标题
   - 此外,根据语境再扩 2-5 个意象词、季节词、情感词
   - 优先用单字或双字词,贴近古诗用词(用"暮"而非"傍晚",用"舟"而非"船",用"月"而非"月亮")
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

示例 5(诗名 + 作者):
输入:"对酒 曹操"
输出:{"authors": ["曹操"], "dynasties": [], "keywords": ["对酒"]}

示例 6(只有诗名):
输入:"短歌行"
输出:{"authors": [], "dynasties": [], "keywords": ["短歌行"]}

示例 7(诗名 + 场景):
输入:"念奴娇 怀古"
输出:{"authors": [], "dynasties": [], "keywords": ["念奴娇", "怀古", "古"]}

严格按 JSON 格式返回,不要任何其他文字:
{"authors": [...], "dynasties": [...], "keywords": [...]}"""


# ===== 主入口 =====

async def expand_keywords(prompt: str, timeout: float = 10.0) -> KeywordExtractResult:
    """
    调用 Kimi 解析用户检索意图,返回 authors/dynasties/keywords 三类。
    带缓存,失败抛 KimiServiceError。
    """
    if not prompt or not prompt.strip():
        return {"authors": [], "dynasties": [], "keywords": []}

    cache_key = prompt.strip().lower()

    cached = await _cache.get(cache_key)
    if cached is not None:
        logger.info(f"Kimi 缓存命中: {prompt}")
        return cached

    result = await _call_kimi(prompt, timeout)
    await _cache.set(cache_key, result)
    return result


async def _call_kimi(prompt: str, timeout: float) -> KeywordExtractResult:
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
        logger.info(f"Kimi raw response: {content}")
        parsed = json.loads(content)
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Kimi 返回解析失败: {data}, error: {e}")
        raise KimiServiceError("Kimi 返回格式错误")

    # 清洗每个字段
    return {
        "authors": _clean_str_list(parsed.get("authors"), max_len=20, max_count=5),
        "dynasties": _clean_str_list(parsed.get("dynasties"), max_len=10, max_count=5),
        "keywords": _clean_str_list(parsed.get("keywords"), max_len=10, max_count=8),
    }


def _clean_str_list(raw, max_len: int, max_count: int) -> List[str]:
    """清洗字符串列表:类型校验、去空、去重保序、限长。"""
    if not isinstance(raw, list):
        return []
    seen = set()
    cleaned: List[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item or item in seen:
            continue
        if len(item) > max_len:
            item = item[:max_len]
        seen.add(item)
        cleaned.append(item)
    return cleaned[:max_count]


# ============ 翻译相关 ============

# 翻译用的 system prompt
TRANSLATE_SYSTEM_PROMPT = """你是一位古典诗词翻译家。任务是把一首古诗翻译成现代汉语,帮助现代读者理解。

请严格按 JSON 格式返回。结构如下:
{
  "overall": "整首诗的现代汉语意译,2-3 句话,通顺自然,传达诗的整体意境与情感。",
  "lines": [
    {
      "original": "原文一句(包含标点)",
      "translation": "这一句的现代汉语翻译,12-25 字。要忠于原意,但用流畅的白话。",
      "annotations": [
        {"word": "字或词", "meaning": "解释"}
      ]
    }
  ]
}

要求:
1. lines 数组里每个对象对应原文的一个分句(以中文逗号、句号、问号、感叹号、分号为界)。
2. original 字段必须严格保留原文的字和标点,不要篡改。
3. translation 字段要让现代人一读就懂,但保留诗意,不要太白话。例如"举头望明月"翻译成"抬头望见空中的明月"比"我抬头看月亮"好。
4. annotations 是可选的,只在以下情况添加:
   - 古今异义字(如"床"在古义指井栏)
   - 典故词(如"陶令"指陶渊明)
   - 较生僻或多义的字
   - 通常每句 0-3 个,大多数句子可能为空数组 []
5. overall 是整体翻译,不是简单把所有 translation 拼起来,而是用 2-3 句白话讲明诗在写什么、表达什么情感。

只返回 JSON,不要任何其他文字、解释、markdown 代码块标记。"""


async def translate_poem(
        title: str,
        author: str | None,
        dynasty: str | None,
        content: str,
        timeout: float = 30.0,
) -> dict:
    """调用 Kimi 翻译一首诗。失败抛 KimiServiceError。"""
    if not settings.kimi_api_key:
        raise KimiServiceError("Kimi API key 未配置")

    if not content or not content.strip():
        raise KimiServiceError("诗词内容为空")

    meta_parts = []
    if author:
        meta_parts.append(f"作者:{author}")
    if dynasty:
        meta_parts.append(f"朝代:{dynasty}")
    meta_str = "(" + " ".join(meta_parts) + ")" if meta_parts else ""

    user_message = f"《{title}》{meta_str}\n\n{content.strip()}"

    payload = {
        "model": settings.kimi_model,
        "messages": [
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.5,
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
        logger.warning(f"Kimi 翻译超时, title={title}")
        raise KimiServiceError("翻译超时,请稍后再试")
    except httpx.HTTPStatusError as e:
        logger.error(f"Kimi 翻译 HTTP 错误: {e.response.status_code} {e.response.text}")
        raise KimiServiceError(f"翻译服务错误: {e.response.status_code}")
    except Exception as e:
        logger.exception(f"Kimi 翻译异常: {e}")
        raise KimiServiceError("翻译服务异常")

    try:
        raw_content = data["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Kimi 翻译返回解析失败: {data}, error: {e}")
        raise KimiServiceError("翻译返回格式错误")

    if not isinstance(parsed, dict):
        raise KimiServiceError("翻译返回不是对象")

    overall = parsed.get("overall")
    lines = parsed.get("lines")

    if not isinstance(overall, str) or not overall.strip():
        raise KimiServiceError("翻译缺少 overall 字段")

    if not isinstance(lines, list) or len(lines) == 0:
        raise KimiServiceError("翻译缺少 lines 字段")

    cleaned_lines = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        original = line.get("original", "").strip()
        translation = line.get("translation", "").strip()
        if not original or not translation:
            continue
        annotations = line.get("annotations", [])
        if not isinstance(annotations, list):
            annotations = []
        cleaned_annotations = []
        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            word = ann.get("word", "").strip()
            meaning = ann.get("meaning", "").strip()
            if word and meaning:
                cleaned_annotations.append({"word": word, "meaning": meaning})

        cleaned_lines.append({
            "original": original,
            "translation": translation,
            "annotations": cleaned_annotations,
        })

    if not cleaned_lines:
        raise KimiServiceError("翻译结果格式错误,没有有效行")

    return {
        "overall": overall.strip(),
        "lines": cleaned_lines,
    }