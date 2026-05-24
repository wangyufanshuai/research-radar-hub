from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models.scientist import (
    ScientistArtifact,
    ScientistRun,
    ScientistTask,
    ScientistTaskItem,
)
from backend.repositories.base import BaseRepository


class ScientistTaskRepository(BaseRepository[ScientistTask]):
    def __init__(self, session: Session):
        super().__init__(ScientistTask, session)

    def get_detail(self, task_id: int) -> ScientistTask | None:
        stmt = (
            select(ScientistTask)
            .where(ScientistTask.id == task_id)
            .options(
                selectinload(ScientistTask.items),
                selectinload(ScientistTask.artifacts),
                selectinload(ScientistTask.runs),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_recent(self, offset: int = 0, limit: int = 20) -> list[ScientistTask]:
        stmt = select(ScientistTask).order_by(ScientistTask.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())


class ScientistTaskItemRepository(BaseRepository[ScientistTaskItem]):
    def __init__(self, session: Session):
        super().__init__(ScientistTaskItem, session)

    def replace_task_items(self, task_id: int, items: list[dict]) -> list[ScientistTaskItem]:
        existing = {
            (item.source, item.source_id): item
            for item in self.session.execute(
                select(ScientistTaskItem).where(ScientistTaskItem.task_id == task_id)
            ).scalars()
        }
        seen: set[tuple[str, str]] = set()
        saved: list[ScientistTaskItem] = []
        for data in items:
            key = (data["source"], data["source_id"])
            seen.add(key)
            current = existing.get(key)
            if current is None:
                current = ScientistTaskItem(task_id=task_id, **data)
                self.session.add(current)
            else:
                for field, value in data.items():
                    setattr(current, field, value)
            saved.append(current)
        self.session.flush()
        return saved


class ScientistArtifactRepository(BaseRepository[ScientistArtifact]):
    def __init__(self, session: Session):
        super().__init__(ScientistArtifact, session)


class ScientistRunRepository(BaseRepository[ScientistRun]):
    def __init__(self, session: Session):
        super().__init__(ScientistRun, session)
