# check_poems.py(临时)
from app.database import SessionLocal
from app.models import Poem

db = SessionLocal()
try:
    total = db.query(Poem).count()
    print(f"总数: {total}")

    # 看几条样本
    samples = db.query(Poem).limit(3).all()
    for p in samples:
        print(f"\n标题: {p.title}")
        print(f"作者: {p.author}")
        print(f"朝代: {p.dynasty}")
        print(f"正文(繁体):\n{p.content}")
        print(f"检索文本(简体):\n{p.content_plain}")
        print(f"search_text: {p.search_text}")

    # 测试一下搜索
    print("\n=== 搜索 '明月' ===")
    results = db.query(Poem).filter(Poem.search_text.like("%明月%")).limit(3).all()
    for r in results:
        print(f"  {r.title} - {r.author}: {r.content[:30]}...")
finally:
    db.close()