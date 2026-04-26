# app/models/favorite.py
from sqlalchemy import Text, DateTime, ForeignKey, UniqueConstraint, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    poem_id: Mapped[int] = mapped_column(ForeignKey("poems.id"))
    user_tags: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="favorites")
    poem: Mapped["Poem"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "poem_id", name="uq_user_poem_favorite"),
        Index("idx_user_favorites", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, poem_id={self.poem_id})>"