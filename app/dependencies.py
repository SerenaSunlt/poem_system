# app/dependencies.py
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.utils.security import decode_access_token


# OAuth2PasswordBearer 是 FastAPI 内置的认证 scheme
# tokenUrl 指向登录接口,Swagger 上会生成"登录"按钮
# auto_error=False 让我们手动处理"没传 token"的情况
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/users/login", auto_error=False
)


def get_db() -> Generator[Session, None, None]:
    """数据库 session 依赖。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    强制认证:从 JWT 解出当前用户。
    没登录或 token 无效都抛 401。
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期或无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    可选认证:有 token 且有效则返回 User,否则返回 None。
    用于游客可访问的接口(推荐、详情)。
    """
    if not token:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()