from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String)


paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

repo_tags = Table(
    "repo_tags",
    Base.metadata,
    Column("repo_id", Integer, ForeignKey("repos.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)
