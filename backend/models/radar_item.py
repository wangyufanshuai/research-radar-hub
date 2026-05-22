from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class RadarItem(TimestampMixin, Base):
    __tablename__ = "radar_items"

    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    source_table_id: Mapped[int | None] = mapped_column(Integer)
    topic_key: Mapped[str] = mapped_column(String, nullable=False)
    topic_name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    value_score: Mapped[int | None] = mapped_column(Integer)
    include_in_report: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_radar_item_identity", "source", "source_id", "topic_key", unique=True),
        Index("idx_radar_item_topic_score", "topic_key", "score"),
        Index("idx_radar_item_published", "published_at"),
    )
