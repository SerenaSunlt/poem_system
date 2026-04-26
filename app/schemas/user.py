# app/schemas/user.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import re


class UserRegisterIn(BaseModel):
    """注册请求体"""
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6, max_length=32)

    def validate_username(self):
        """用户名只允许字母数字下划线"""
        if not re.match(r"^[a-zA-Z0-9_]+$", self.username):
            raise ValueError("用户名只能包含字母、数字、下划线")


class UserLoginIn(BaseModel):
    """登录请求体"""
    username: str
    password: str


class UserOut(BaseModel):
    """用户信息输出(不含密码)"""
    user_id: int = Field(..., alias="id")
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LoginOut(BaseModel):
    """登录响应"""
    token: str
    user: UserOut