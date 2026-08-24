from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.sync_log import SyncLog
from app.models.works import Work

router = APIRouter(prefix="/institution", tags=["institution"])


class InstitutionSummary(BaseModel):
    institution_name: str
    openalex_institution_id: str
    country_code: str | None
    total_works: int
    core_works: int
    total_citations: int
    core_citations: int
    h_index: int
    period_start: int | None
    period_end: int | None
    last_openalex_sync: datetime | None
    leiden_snapshot_year: int | None


@router.get("/summary", response_model=InstitutionSummary)
async def get_summary(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> InstitutionSummary:
    # Aggregate from works table
    result = await session.execute(
        select(
            func.count().label("total"),
            func.count().filter(Work.is_core_publication.is_(True)).label("core"),
            func.coalesce(func.sum(Work.cited_by_count), 0).label("citations"),
            func.coalesce(
                func.sum(Work.cited_by_count).filter(Work.is_core_publication.is_(True)), 0
            ).label("core_citations"),
        )
    )
    row = result.one()

    # Publication year range covered by the synced corpus — shown in the
    # dashboard's sticky header ("période d'années de publications concernée").
    period_result = await session.execute(
        select(func.min(Work.publication_year), func.max(Work.publication_year))
    )
    period_start, period_end = period_result.one()

    # H-index (standard algorithm on all works)
    counts_result = await session.execute(
        select(Work.cited_by_count).order_by(Work.cited_by_count.desc())
    )
    cite_counts = [r[0] for r in counts_result.all()]
    h = 0
    for i, c in enumerate(cite_counts, start=1):
        if c >= i:
            h = i
        else:
            break

    # Last successful OpenAlex sync
    sync_result = await session.execute(
        select(SyncLog.finished_at)
        .where(SyncLog.job_name == "openalex_nightly", SyncLog.status == "success")
        .order_by(SyncLog.finished_at.desc())
        .limit(1)
    )
    last_sync = sync_result.scalar_one_or_none()

    # Latest Leiden snapshot year
    leiden_result = await session.execute(
        select(func.max(LeidenSnapshot.snapshot_year))
    )
    snapshot_year = leiden_result.scalar_one_or_none()

    return InstitutionSummary(
        institution_name=config.institution_name,
        openalex_institution_id=config.openalex_institution_id,
        country_code=config.country_code,
        total_works=row.total,
        core_works=row.core,
        total_citations=row.citations,
        core_citations=row.core_citations,
        h_index=h,
        period_start=period_start,
        period_end=period_end,
        last_openalex_sync=last_sync,
        leiden_snapshot_year=snapshot_year,
    )
