from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class Paper(TimestampMixin, Base):
    __tablename__ = "papers"

    arxiv_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[str | None] = mapped_column(Text)
    categories: Mapped[str | None] = mapped_column(Text)
    primary_category: Mapped[str | None] = mapped_column(String)
    published: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated: Mapped[datetime | None] = mapped_column(DateTime)
    doi: Mapped[str | None] = mapped_column(String)
    pdf_url: Mapped[str | None] = mapped_column(String)
    entry_url: Mapped[str | None] = mapped_column(String)
    comment: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_papers_published", published.desc()),
        Index("idx_papers_primary_category", "primary_category"),
    )
