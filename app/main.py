# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import user, poem, dislike, favorite


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    description="场景化诗词推荐与收藏系统",
    version="0.1.0",
)

# CORS 配置(给 Vue 前端用,本地开发时必备)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vue 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(user.router)
app.include_router(poem.router)
app.include_router(favorite.router)
app.include_router(dislike.router)


@app.get("/")
def root():
    return {"message": "Poem System is running"}


@app.get("/health")
def health():
    return {"status": "ok"}