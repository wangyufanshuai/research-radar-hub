from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class CourseItem(TimestampMixin, Base):
    __tablename__ = "course_items"

    institution: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(String)
    level: Mapped[str | None] = mapped_column(String)
    topics: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        Index("idx_course_items_institution", "institution"),
        Index("idx_course_items_source", "source_id"),
        Index("idx_course_items_seen", last_seen_at.desc()),
    )
