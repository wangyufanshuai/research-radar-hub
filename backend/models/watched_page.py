from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class WatchedPage(TimestampMixin, Base):
    __tablename__ = "watched_pages"

    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    selector: Mapped[str | None] = mapped_column(String)
    render: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=360)
    robots_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_status_code: Mapped[int | None] = mapped_column(Integer)
    last_hash: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        Index("idx_watched_pages_enabled", "enabled"),
    )
