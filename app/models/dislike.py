# app/models/dislike.py
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database import Base


class Dislike(Base):
    __tablename__ = "dislikes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    poem_id: Mapped[int] = mapped_column(ForeignKey("poems.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="dislikes")
    poem: Mapped["Poem"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "poem_id", name="uq_user_poem_dislike"),
        Index("idx_user_dislikes", "user_id"),
    )

    def __repr__(self):
        return f"<Dislike(user_id={self.user_id}, poem_id={self.poem_id})>"