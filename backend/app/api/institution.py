from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.api.indicators import LEIDEN_FIELDS
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroup
from app.models.sync_log import SyncLog
from app.models.works import Work
from app.services.ror import normalize_ror

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
    leiden_decile: int | None
    leiden_decile_label: str | None


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

    # Which Leiden size-bracket decile the reference institution itself falls
    # into — found by matching its own publication count (p) against the
    # [p_min, p_max] boundaries stored on each size_bracket peer group at the
    # last recalculation (see services/peer_groups.py).
    leiden_decile: int | None = None
    leiden_decile_label: str | None = None
    own_ror = normalize_ror(config.ror_id)
    if own_ror and snapshot_year:
        own_p_result = await session.execute(
            select(LeidenSnapshot.p).where(
                LeidenSnapshot.ror_id == own_ror,
                LeidenSnapshot.snapshot_year == snapshot_year,
                LeidenSnapshot.field == "All sciences",
                LeidenSnapshot.frac_counting.is_(False),
                LeidenSnapshot.core_pubs_only.is_(False),
            )
        )
        own_p = own_p_result.scalar_one_or_none()
        if own_p is not None:
            deciles_result = await session.execute(
                select(PeerGroup).where(PeerGroup.type == "size_bracket")
            )
            for group in deciles_result.scalars().all():
                p_min = group.params.get("p_min")
                p_max = group.params.get("p_max")
                if p_min is not None and p_max is not None and p_min <= float(own_p) <= p_max:
                    leiden_decile = group.params.get("decile")
                    leiden_decile_label = group.name
                    break

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
        leiden_decile=leiden_decile,
        leiden_decile_label=leiden_decile_label,
    )



class SynthesisCounts(BaseModel):
    field: str
    core_only: bool
    # "openalex" on the whole-institution scope; "leiden" when a Leiden macro-
    # domain is selected (OpenAlex works carry no Leiden domain).
    source: str
    publications: float | None
    citations: float | None


@router.get("/synthesis", response_model=SynthesisCounts)
async def get_synthesis(
    field: str = Query(default="All sciences"),
    core_only: bool = Query(default=True),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> SynthesisCounts:
    """Publication and citation totals for the dashboard's Synthèse section,
    following its active filters (core/non-core toggle + Leiden macro-domain).

    Whole-institution scope ("All sciences") is counted on the synced OpenAlex
    works, as in /summary. A Leiden macro-domain has no counterpart on OpenAlex
    works, so the reference institution's own Leiden row for that domain is
    used instead: P (publication count — fractional, interdisciplinary
    publications being split across domains) and TCS (total citations). Both
    are None when the institution is not ranked by Leiden.
    """
    if field not in LEIDEN_FIELDS:
        raise HTTPException(status_code=400, detail=f"field must be one of {LEIDEN_FIELDS}")

    if field == "All sciences":
        filters = [Work.is_core_publication.is_(True)] if core_only else []
        result = await session.execute(
            select(func.count(), func.coalesce(func.sum(Work.cited_by_count), 0)).where(*filters)
        )
        publications, citations = result.one()
        return SynthesisCounts(
            field=field, core_only=core_only, source="openalex",
            publications=publications, citations=citations,
        )

    publications = citations = None
    own_ror = normalize_ror(config.ror_id)
    if own_ror:
        result = await session.execute(
            select(LeidenSnapshot.p, LeidenSnapshot.tcs).where(
                LeidenSnapshot.ror_id == own_ror,
                LeidenSnapshot.snapshot_year == select(func.max(LeidenSnapshot.snapshot_year)).scalar_subquery(),
                LeidenSnapshot.field == field,
                LeidenSnapshot.core_pubs_only.is_(core_only),
                LeidenSnapshot.frac_counting.is_(False),
            )
        )
        row = result.one_or_none()
        if row:
            publications = float(row.p) if row.p is not None else None
            citations = row.tcs
    return SynthesisCounts(
        field=field, core_only=core_only, source="leiden",
        publications=publications, citations=citations,
    )
