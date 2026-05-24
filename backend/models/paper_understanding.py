from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class PaperUnderstanding(TimestampMixin, Base):
    __tablename__ = "paper_understandings"

    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id"), nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String)
    pdf_url: Mapped[str | None] = mapped_column(String)
    text_excerpt: Mapped[str | None] = mapped_column(Text)
    formula_candidates: Mapped[str | None] = mapped_column(Text)
    dataset_mentions: Mapped[str | None] = mapped_column(Text)
    code_mentions: Mapped[str | None] = mapped_column(Text)
    citation_mentions: Mapped[str | None] = mapped_column(Text)
    metric_mentions: Mapped[str | None] = mapped_column(Text)
    understanding_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_paper_understanding_source_id", "source", "source_id", unique=True),
        Index("idx_paper_understanding_paper", "paper_id"),
    )
