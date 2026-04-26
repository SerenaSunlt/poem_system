# app/services/auth.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.utils.security import hash_password, verify_password, create_access_token


# 自定义业务异常
class AuthError(Exception):
    """认证相关业务错误的基类。"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def register_user(db: Session, username: str, password: str) -> User:
    """注册用户。用户名重复时抛业务异常。"""
    # 先查一下重名(更友好的错误信息)
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise AuthError(1002, "用户名已存在")

    user = User(
        username=username,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # 并发时也可能撞唯一索引,兜底
        raise AuthError(1002, "用户名已存在")
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    """验证用户名密码,通过则返回 User,否则抛业务异常。"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # 故意不区分"用户不存在"和"密码错误",防枚举攻击
        raise AuthError(1003, "用户名或密码错误")

    if not verify_password(password, user.password_hash):
        raise AuthError(1003, "用户名或密码错误")

    return user


def login_user(db: Session, username: str, password: str) -> tuple[User, str]:
    """登录:验证 + 签发 token。"""
    user = authenticate_user(db, username, password)
    token = create_access_token(user.id)
    return user, token