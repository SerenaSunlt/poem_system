# app/models/poem.py
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
from app.database import Base


class Poem(Base):
    __tablename__ = "poems"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    author: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    dynasty: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    content: Mapped[str] = mapped_column(Text)
    content_plain: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), default="诗")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    search_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Poem(id={self.id}, title={self.title}, author={self.author})>"