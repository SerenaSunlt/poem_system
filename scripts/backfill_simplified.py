# scripts/backfill_simplified.py
"""
一次性脚本:把所有 Poem 的 content 字段从繁体转成简体,带标点,
写入 content_simplified 字段。

用法:
    python scripts/backfill_simplified.py

可选:
    --batch  每批处理多少条,默认 500
    --dry-run  只打印,不写入(测试用)
"""
import argparse
import sys
from pathlib import Path

# 让脚本能 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from opencc import OpenCC
from app.database import SessionLocal
from app.models import Poem

cc = OpenCC("t2s")  # 繁体转简体


def to_simplified(text: str) -> str:
    return cc.convert(text) if text else ""


def main():
    parser = argparse.ArgumentParser(description="回填 content_simplified 字段")
    parser.add_argument("--batch", type=int, default=500, help="每批处理多少条")
    parser.add_argument("--dry-run", action="store_true", help="只打印,不写入")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        total = db.query(Poem).count()
        print(f"诗词总数: {total}")

        # 找需要回填的(content_simplified 为空的)
        offset = 0
        updated = 0

        while True:
            batch = (
                db.query(Poem)
                .filter((Poem.content_simplified == "") | (Poem.content_simplified == None))
                .order_by(Poem.id)
                .limit(args.batch)
                .all()
            )

            if not batch:
                break

            for poem in batch:
                simplified = to_simplified(poem.content)
                if args.dry_run:
                    print(f"[DRY] id={poem.id} title={poem.title}: {simplified[:50]}")
                else:
                    poem.content_simplified = simplified
                updated += 1

            if not args.dry_run:
                db.commit()
                print(f"已处理 {updated} 首...")
            else:
                # dry-run 不 commit,但要把这一批"假装处理过"才能继续
                # 不然会死循环。这里 break 退出,只看一批样例
                print(f"\n[DRY-RUN] 共预览 {updated} 首样例,不会写入数据库")
                break

        print(f"\n✅ 完成,共回填 {updated} 首")
    finally:
        db.close()


if __name__ == "__main__":
    main()