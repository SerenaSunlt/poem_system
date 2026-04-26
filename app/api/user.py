# app/api/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas.user import UserRegisterIn, UserLoginIn, UserOut, LoginOut
from app.schemas.common import success, error
from app.services.auth import register_user, login_user, AuthError

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register")
def register(payload: UserRegisterIn, db: Session = Depends(get_db)):
    """用户注册"""
    # 用户名格式校验(Pydantic Field 已做了长度,这里补正则)
    try:
        payload.validate_username()
    except ValueError as e:
        return error(1001, str(e))

    try:
        user = register_user(db, payload.username, payload.password)
    except AuthError as e:
        return error(e.code, e.message)

    return success({
        "user_id": user.id,
        "username": user.username,
    })


@router.post("/login")
def login(payload: UserLoginIn, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        user, token = login_user(db, payload.username, payload.password)
    except AuthError as e:
        return error(e.code, e.message)

    return success({
        "token": token,
        "user": UserOut.model_validate(user).model_dump(by_alias=True),
    })


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return success(UserOut.model_validate(current_user).model_dump(by_alias=True))