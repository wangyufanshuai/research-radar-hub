from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import CollectResponse
from backend.services.collection import COLLECTORS, collect_source

router = APIRouter(tags=["collection"])


@router.post("/api/v1/collect/{source}", response_model=CollectResponse)
async def trigger_collection(
    source: str,
    incremental: bool = Query(False),
    db: Session = Depends(get_db),
) -> CollectResponse:
    if source == "all":
        totals = {"records_fetched": 0, "records_new": 0, "records_updated": 0, "duration_secs": 0.0}
        errors: list[str] = []
        for src in COLLECTORS:
            try:
                result = collect_source(db, src, incremental=incremental)
                for key in totals:
                    totals[key] += result[key]
            except Exception as exc:
                errors.append(f"{src}: {exc}")
        return CollectResponse(
            source="all",
            status="failed" if errors else "success",
            records_fetched=int(totals["records_fetched"]),
            records_new=int(totals["records_new"]),
            records_updated=int(totals["records_updated"]),
            duration_secs=round(float(totals["duration_secs"]), 2),
            error="; ".join(errors) if errors else None,
        )

    try:
        return CollectResponse(**collect_source(db, source, incremental=incremental))
    except Exception as exc:
        return CollectResponse(
            source=source,
            status="failed",
            records_fetched=0,
            records_new=0,
            records_updated=0,
            duration_secs=0,
            error=str(exc),
        )
