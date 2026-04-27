# scripts/import_poems.py
"""
诗词数据导入脚本。

用法:
    python scripts/import_poems.py --source D:/path/to/chinese-poetry --types tang,song,shijing

可选参数:
    --source     chinese-poetry 仓库根目录路径
    --types      要导入的诗词类型,逗号分隔。可选: tang, song, shijing
    --limit      每个类型最多导入多少首(用于小批量测试)
    --batch      批量插入的批次大小,默认 500
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator

from opencc import OpenCC
from sqlalchemy.orm import Session

# 让脚本能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine
from app.models import Poem

# 繁→简转换器(t2s = traditional to simplified)
cc = OpenCC("t2s")

# 标点符号正则,用于生成 content_plain
PUNCTUATION_PATTERN = re.compile(
    r"[,。!?;:、""''()《》〈〉「」『』【】〔〕\s,.!?;:\"'()\[\]<>—…·\-]"
)
NOTE_PATTERN = re.compile(r"[\(()].*?[\))]")


def to_simplified(text: str) -> str:
    """繁体转简体。"""
    return cc.convert(text) if text else text


def strip_punctuation(text: str) -> str:
    """去除标点和空白字符。"""
    return PUNCTUATION_PATTERN.sub("", text)


def iter_json_files(directory: Path, pattern: str) -> Iterator[Path]:
    """遍历目录下符合 pattern 的 JSON 文件。"""
    if not directory.exists():
        print(f"⚠️  目录不存在: {directory}")
        return
    for path in sorted(directory.glob(pattern)):
        yield path


def parse_poem(raw: dict, dynasty: str, poem_type: str, default_author: str | None = None) -> dict | None:
    """
    把原始记录转换成 Poem 字段字典。
    转换失败返回 None。

    default_author: 如果原始数据没有 author 字段,使用这个默认值
    """
    title_raw = raw.get("title") or raw.get("rhythmic")
    author_raw = raw.get("author") or default_author
    paragraphs = raw.get("paragraphs") or raw.get("content") or []

    if not title_raw or not paragraphs:
        return None

    # 拼接正文(保留原始形态,带换行)
    content_original = "\n".join(paragraphs)

    # 简体转换
    title = to_simplified(title_raw).strip()
    author = to_simplified(author_raw).strip() if author_raw else None
    content_simplified_with_punct = to_simplified(content_original)  # 这里改名,清晰一点

    # 先去除括号注释,再去标点 → 干净的检索文本
    content_no_notes = NOTE_PATTERN.sub("", content_simplified_with_punct)
    content_plain = strip_punctuation(content_no_notes)

    search_text = " ".join(filter(None, [title, author or "", content_plain]))

    return {
        "title": title[:200],
        "author": (author or "")[:100] or None,
        "dynasty": dynasty,
        "content": content_original,  # 保留原文,带注释
        "content_simplified": content_simplified_with_punct,
        "content_plain": content_plain,  # 简体无标点无注释,用于搜索
        "type": poem_type,
        "tags": [],
        "search_text": search_text,
    }


def load_from_dir(
        directory: Path,
        file_pattern: str,
        dynasty: str,
        poem_type: str,
        limit: int | None,
        default_author: str | None = None,
) -> list[dict]:
    """从一个目录加载所有诗词。"""
    poems = []
    for json_file in iter_json_files(directory, file_pattern):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  读取失败 {json_file.name}: {e}")
            continue

        if not isinstance(data, list):
            data = [data]

        for raw in data:
            parsed = parse_poem(raw, dynasty, poem_type, default_author=default_author)
            if parsed:
                poems.append(parsed)
                if limit and len(poems) >= limit:
                    return poems

        print(f"  读取 {json_file.name},累计 {len(poems)} 首")
    return poems


def batch_insert(db: Session, poems: list[dict], batch_size: int = 500) -> int:
    """批量插入,失败的批次跳过。"""
    inserted = 0
    total = len(poems)
    for i in range(0, total, batch_size):
        batch = poems[i:i + batch_size]
        try:
            db.bulk_insert_mappings(Poem, batch)
            db.commit()
            inserted += len(batch)
            print(f"  已插入 {inserted}/{total}")
        except Exception as e:
            db.rollback()
            print(f"⚠️  批次 {i}-{i + len(batch)} 失败: {e}")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="导入诗词到数据库")
    parser.add_argument("--source", required=True, help="诗词数据根目录")
    parser.add_argument("--types", default="tang,song,shijing", help="要导入的类型,逗号分隔")
    parser.add_argument("--limit", type=int, default=None, help="每类最多导入数量(测试用)")
    parser.add_argument("--batch", type=int, default=500, help="批量插入大小")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"❌ 源目录不存在: {source}")
        return

    types = [t.strip() for t in args.types.split(",") if t.strip()]

    # 配置:类型 → (子目录名, 文件 glob, 朝代, 体裁, 默认作者)
    # 默认作者为 None 表示从原始数据读 author 字段
    config = {
        "tang": ("全唐诗", "poet.tang.*.json", "唐", "诗", None),
        "song": ("宋词", "ci.song.*.json", "宋", "词", None),
        "shijing": ("诗经", "shijing.json", "先秦", "诗", None),
        "caocao": ("曹操诗集", "caocao.json", "汉", "诗", "曹操"),
    }

    db = SessionLocal()
    try:
        total_inserted = 0
        for type_key in types:
            if type_key not in config:
                print(f"⚠️  未知类型: {type_key},跳过")
                continue

            subdir, pattern, dynasty, poem_type, default_author = config[type_key]
            author_hint = f", 作者: {default_author}" if default_author else ""
            print(f"\n=== 导入 {type_key}({dynasty}{poem_type}{author_hint}) ===")

            directory = source / subdir
            poems = load_from_dir(
                directory, pattern, dynasty, poem_type,
                limit=args.limit,
                default_author=default_author,
            )
            print(f"共解析 {len(poems)} 首,开始入库...")

            inserted = batch_insert(db, poems, args.batch)
            total_inserted += inserted
            print(f"=== {type_key} 完成,入库 {inserted} 首 ===")

        print(f"\n✅ 全部完成,总计入库 {total_inserted} 首")
    finally:
        db.close()


if __name__ == "__main__":
    main()