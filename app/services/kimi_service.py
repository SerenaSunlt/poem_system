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

class KeywordExtractResult(TypedDict, total=False):
    """Kimi 解析出的结构化检索意图。

    intent 决定后端走哪条匹配路径:
    - "verse":   用户输入了诗句片段(连续 4+ 字符的诗句),走全文精准匹配
    - "specific": 用户在找特定诗(给了标题/作者/朝代),走精确字段匹配
    - "scene":   用户描述场景或氛围,走关键词模糊匹配
    - "random":  无明确意图(空输入、随机请求),走随机推荐
    """
    intent: str
    verse_phrase: Optional[str]
    title: Optional[str]
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


# ===== 默认空结果 =====

def _empty_result() -> KeywordExtractResult:
    return {
        "intent": "random",
        "verse_phrase": None,
        "title": None,
        "authors": [],
        "dynasties": [],
        "keywords": [],
    }


# ===== Prompt 设计 =====

SYSTEM_PROMPT = """你是一个中国古典诗词检索助手。

任务:把用户输入解析成结构化的检索意图,用于在古诗词数据库中检索。

## 第一步:判断 intent

把用户输入归类为以下四种之一:

- "verse":     用户输入包含一句完整的古诗句(连续 4 个或更多汉字,符合古诗语感),例如"空山新雨后"、"床前明月光"、"大江东去"。即使夹杂作者名、错别字、残缺,只要能识别出诗句片段,都归 verse。
- "specific": 用户在找一首特定的诗,给了标题、作者、朝代或别称中的一个或多个,但没有给出诗句本身。例如"对酒 曹操"、"念奴娇 怀古"、"东坡的水调歌头"、"易安居士"。
- "scene":    用户描述一种场景、情感、意象或现代说法,需要做模糊推荐。例如"秋天的离别"、"宋词 思乡"、"给我一首可以发朋友圈的"、"想家了"。
- "random":   用户没有任何检索意图。例如空输入、纯标点、"换一首"、"随便来一个"、无意义乱码。

## 第二步:根据 intent,提取对应字段

根据 intent 给不同字段赋值,其他字段为空数组或 null:

### intent = "verse"
- verse_phrase: 提取出的完整诗句(去掉作者名、纠正明显错别字、补全合理的残句),且verse_phrase 必须尽量保留用户输入的连续诗句，不要主动插入空格、书名号或引号；如果原句中有标点，可保留标点，但不要把一句诗拆成关键词。
- authors: 如果用户也提到了作者,识别并规范化
- 其他字段: null 或空数组

### intent = "specific"
- title: 如果用户给了标题,提取出来(规范化为常见名)
- authors: 如果用户给了作者,提取并规范化(详见规范化规则)
- dynasties: 如果用户给了朝代,提取并规范化(唐/宋/元/明/清/汉/魏晋/南北朝/先秦)
- 其他字段: null 或空数组

### intent = "scene"
- keywords: 3-6 个适合检索的古诗常见意象、季节、自然景物、情感词
  - 优先用单字或双字词,贴近古诗用词(用"暮"而非"傍晚",用"舟"而非"船",用"月"而非"月亮")
  - 包含字面词和意境延伸词
- authors / dynasties: 如果用户也提到,顺便提取
- 其他字段: null 或空数组

### intent = "random"
- 所有字段为空数组或 null

## 规范化规则

- 作者:用标准姓名("苏东坡"→"苏轼","太白"→"李白","易安居士"→"李清照","老杜"→"杜甫","摩诘"→"王维")
- 朝代:用单字("唐朝"→"唐","宋代"→"宋"),诗经/楚辞→"先秦",魏晋时期→"魏晋"

## 输出格式

严格 JSON,只输出一个对象,不要 markdown 标记或额外文字:
{"intent": "...", "verse_phrase": null|"...", "title": null|"...", "authors": [...], "dynasties": [...], "keywords": [...]}

## 示例

示例 1(诗句片段):
输入:"空山新雨后王维"
输出:{"intent": "verse", "verse_phrase": "空山新雨后", "title": null, "authors": ["王维"], "dynasties": [], "keywords": []}

示例 2(诗句片段,无作者):
输入:"床前明月光"
输出:{"intent": "verse", "verse_phrase": "床前明月光", "title": null, "authors": [], "dynasties": [], "keywords": []}

示例 3(残句 / 错别字):
输入:"举头望明日"
输出:{"intent": "verse", "verse_phrase": "举头望明月", "title": null, "authors": [], "dynasties": [], "keywords": []}

示例 4(完整一句以上):
输入:"床前明月光,疑是地上霜"
输出:{"intent": "verse", "verse_phrase": "床前明月光", "title": null, "authors": [], "dynasties": [], "keywords": []}

示例 5(诗名 + 作者):
输入:"对酒 曹操"
输出:{"intent": "specific", "verse_phrase": null, "title": "对酒", "authors": ["曹操"], "dynasties": [], "keywords": []}

示例 6(只有诗名):
输入:"短歌行"
输出:{"intent": "specific", "verse_phrase": null, "title": "短歌行", "authors": [], "dynasties": [], "keywords": []}

示例 7(作者别称):
输入:"东坡"
输出:{"intent": "specific", "verse_phrase": null, "title": null, "authors": ["苏轼"], "dynasties": [], "keywords": []}

示例 8(朝代 + 体裁):
输入:"宋词"
输出:{"intent": "specific", "verse_phrase": null, "title": null, "authors": [], "dynasties": ["宋"], "keywords": []}

示例 9(场景):
输入:"西湖傍晚"
输出:{"intent": "scene", "verse_phrase": null, "title": null, "authors": [], "dynasties": [], "keywords": ["西湖", "湖", "暮", "夕阳", "晚霞"]}

示例 10(场景 + 朝代):
输入:"宋词 思乡"
输出:{"intent": "scene", "verse_phrase": null, "title": null, "authors": [], "dynasties": ["宋"], "keywords": ["故乡", "思", "归", "乡"]}

示例 11(现代意图):
输入:"给我一首可以发朋友圈的"
输出:{"intent": "scene", "verse_phrase": null, "title": null, "authors": [], "dynasties": [], "keywords": ["美", "景", "意", "趣"]}

示例 12(场景 + 作者):
输入:"李白写的关于月亮的诗"
输出:{"intent": "scene", "verse_phrase": null, "title": null, "authors": ["李白"], "dynasties": [], "keywords": ["月", "明月", "夜"]}

示例 13(随机意图):
输入:"换一首"
输出:{"intent": "random", "verse_phrase": null, "title": null, "authors": [], "dynasties": [], "keywords": []}

示例 14(无意义输入):
输入:"asdfgh"
输出:{"intent": "random", "verse_phrase": null, "title": null, "authors": [], "dynasties": [], "keywords": []}
"""


# ===== 主入口 =====

async def expand_keywords(prompt: str, timeout: float = 10.0) -> KeywordExtractResult:
    """
    调用 Kimi 解析用户检索意图,返回结构化的 KeywordExtractResult。
    带缓存,失败抛 KimiServiceError。
    """
    if not prompt or not prompt.strip():
        return _empty_result()

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

    return _parse_extract_result(parsed)


def _parse_extract_result(parsed: dict) -> KeywordExtractResult:
    """从 Kimi 返回的 JSON 中清洗出 KeywordExtractResult"""
    if not isinstance(parsed, dict):
        return _empty_result()

    # intent
    intent = parsed.get("intent")
    if intent not in ("verse", "specific", "scene", "random"):
        intent = "scene"  # 兜底归到 scene,继续做关键词匹配

    # verse_phrase
    verse_phrase = parsed.get("verse_phrase")
    if isinstance(verse_phrase, str):
        verse_phrase = verse_phrase.strip()
        if len(verse_phrase) < 4:
            verse_phrase = None
    else:
        verse_phrase = None

    # title
    title = parsed.get("title")
    if isinstance(title, str):
        title = title.strip()
        if not title or len(title) > 30:
            title = None
    else:
        title = None

    return {
        "intent": intent,
        "verse_phrase": verse_phrase,
        "title": title,
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


# ============ 翻译相关(保持原样,不改动) ============

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