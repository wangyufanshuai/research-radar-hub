from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class Repo(TimestampMixin, Base):
    __tablename__ = "repos"

    github_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    watchers: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[str | None] = mapped_column(Text)
    license_name: Mapped[str | None] = mapped_column(String)
    homepage: Mapped[str | None] = mapped_column(String)
    html_url: Mapped[str | None] = mapped_column(String)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at_gh: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at_gh: Mapped[datetime | None] = mapped_column(DateTime)
    pushed_at_gh: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_repos_stars", stars.desc()),
        Index("idx_repos_language", "language"),
    )
