# app/models/translation.py
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database import Base


class Translation(Base):
    """用户对某首诗的翻译记录"""
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    poem_id: Mapped[int] = mapped_column(ForeignKey("poems.id", ondelete="CASCADE"))

    # 翻译数据(JSON 结构):
    # {
    #   "overall": "整首诗的现代汉语意译",
    #   "lines": [
    #     {
    #       "original": "床前明月光,",
    #       "translation": "床前洒满了如霜的月光",
    #       "annotations": [{"char": "床", "meaning": "井栏"}]
    #     }
    #   ]
    # }
    translation_data: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # 关系
    user = relationship("User")
    poem = relationship("Poem")

    __table_args__ = (
        # 一个用户对一首诗只有一份翻译,重复翻译就 update
        UniqueConstraint("user_id", "poem_id", name="uq_user_poem_translation"),
        Index("idx_user_translations", "user_id"),
    )

    def __repr__(self):
        return f"<Translation(user_id={self.user_id}, poem_id={self.poem_id})>"