# scripts/test_translate.py
"""测试 Kimi 翻译,在本地跑"""
import asyncio
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 打开 DEBUG 日志,看 kimi_service 内部输出
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s [%(name)s] %(message)s'
)

from app.services.kimi_service import translate_poem, KimiServiceError


async def main():
    print("开始调用 translate_poem...")

    try:
        result = await translate_poem(
            title="静夜思",
            author="李白",
            dynasty="唐",
            content="床前明月光,疑是地上霜。\n举头望明月,低头思故乡。",
        )
    except KimiServiceError as e:
        print(f"\n❌ Kimi 服务错误: {e}")
        return
    except Exception as e:
        print(f"\n❌ 未知错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n返回类型: {type(result)}")
    print(f"返回内容: {result}")

    if result is None:
        print("❌ result 是 None,这不应该发生")
        return

    print("\n" + "=" * 60)
    print("整体翻译:")
    print(result.get("overall", "(无)"))
    print()
    print("逐句:")
    for i, line in enumerate(result.get("lines", []), 1):
        print(f"\n  [{i}] {line.get('original', '')}")
        print(f"      → {line.get('translation', '')}")
        for ann in line.get("annotations", []):
            print(f"      · {ann.get('word', '')}{ann.get('meaning', '')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())