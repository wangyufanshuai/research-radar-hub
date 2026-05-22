from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class CVEItem(TimestampMixin, Base):
    __tablename__ = "cve_items"

    cve_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String)
    cvss_score: Mapped[float | None] = mapped_column(Float)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime)
    references_json: Mapped[str | None] = mapped_column(Text)
    affected_json: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_cve_items_published", published_at.desc()),
        Index("idx_cve_items_severity", "severity"),
    )
