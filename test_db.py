# test_db.py(临时文件,验证完可删)
from app.database import SessionLocal
from app.models import User
from datetime import datetime


def main():
    db = SessionLocal()
    try:
        # 插入一个测试用户
        test_user = User(
            username="test_user",
            password_hash="placeholder",  # 占位,实际密码哈希后面做
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"创建成功: {test_user}")

        # 查询
        users = db.query(User).all()
        print(f"当前所有用户: {users}")

        # 清理(避免污染)
        db.delete(test_user)
        db.commit()
        print("已清理")
    finally:
        db.close()


if __name__ == "__main__":
    main()