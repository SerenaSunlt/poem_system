# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings


# 创建引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,        # 连接前 ping 一下,避免拿到失效连接
    pool_recycle=3600,          # 每小时回收连接,避免 MySQL 8 小时超时
    echo=settings.debug,        # debug 模式打印 SQL,排查问题用
)

# Session 工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 所有模型继承的基类
Base = declarative_base()

