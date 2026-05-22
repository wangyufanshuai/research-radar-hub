from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class Story(TimestampMixin, Base):
    __tablename__ = "stories"

    hn_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String)
    text: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, default=0)
    author: Mapped[str | None] = mapped_column(String)
    descendants: Mapped[int] = mapped_column(Integer, default=0)
    time_published: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_stories_score", score.desc()),
        Index("idx_stories_time", time_published.desc()),
    )
