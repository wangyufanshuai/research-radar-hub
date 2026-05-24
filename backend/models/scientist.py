from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin


class ScientistTask(TimestampMixin, Base):
    __tablename__ = "scientist_tasks"

    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="created", nullable=False)
    query: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["ScientistTaskItem"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["ScientistArtifact"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    runs: Mapped[list["ScientistRun"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class ScientistTaskItem(TimestampMixin, Base):
    __tablename__ = "scientist_task_items"

    task_id: Mapped[int] = mapped_column(ForeignKey("scientist_tasks.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reproducibility_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped[ScientistTask] = relationship(back_populates="items")

    __table_args__ = (
        Index("idx_scientist_items_task_source", "task_id", "source", "source_id", unique=True),
        Index("idx_scientist_items_scores", "task_id", "relevance_score", "novelty_score"),
    )


class ScientistArtifact(TimestampMixin, Base):
    __tablename__ = "scientist_artifacts"

    task_id: Mapped[int] = mapped_column(ForeignKey("scientist_tasks.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    html_path: Mapped[str | None] = mapped_column(Text)
    created_at_artifact: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    task: Mapped[ScientistTask] = relationship(back_populates="artifacts")

    __table_args__ = (
        Index("idx_scientist_artifacts_task_kind", "task_id", "kind"),
    )


class ScientistRun(TimestampMixin, Base):
    __tablename__ = "scientist_runs"

    task_id: Mapped[int] = mapped_column(ForeignKey("scientist_tasks.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    message: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    task: Mapped[ScientistTask] = relationship(back_populates="runs")

    __table_args__ = (
        Index("idx_scientist_runs_task_stage", "task_id", "stage"),
    )
