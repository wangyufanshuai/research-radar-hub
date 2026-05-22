from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class PageSnapshot(TimestampMixin, Base):
    __tablename__ = "page_snapshots"

    watched_page_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("watched_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    text_excerpt: Mapped[str | None] = mapped_column(Text)
    diff_summary: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        Index("idx_page_snapshots_page_time", "watched_page_id", fetched_at.desc()),
        Index("idx_page_snapshots_hash", "content_hash"),
    )
