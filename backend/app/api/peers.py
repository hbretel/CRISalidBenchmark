from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroup, PeerGroupMember
from app.services.peer_topic_cache import fill_cache_for_group, get_fill_progress

router = APIRouter(prefix="/peer-groups", tags=["peer-groups"])


class PeerGroupSummary(BaseModel):
    id: int
    name: str
    type: str
    member_count: int
    generated_at: datetime | None
    params: dict


class PeerGroupCreate(BaseModel):
    name: str
    ror_ids: list[str]


class PeerMemberInfo(BaseModel):
    ror_id: str
    university_name: str | None
    country_code: str | None
    p: float | None


@router.get("", response_model=list[PeerGroupSummary])
async def list_peer_groups(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> list[PeerGroupSummary]:
    result = await session.execute(
        select(PeerGroup, func.count(PeerGroupMember.ror_id).label("member_count"))
        .outerjoin(PeerGroupMember, PeerGroupMember.peer_group_id == PeerGroup.id)
        .group_by(PeerGroup.id)
        .order_by(PeerGroup.type, PeerGroup.name)
    )
    rows = result.all()
    return [
        PeerGroupSummary(
            id=pg.id,
            name=pg.name,
            type=pg.type,
            member_count=count,
            generated_at=pg.generated_at,
            params=pg.params or {},
        )
        for pg, count in rows
    ]


@router.post("", status_code=201)
async def create_peer_group(
    body: PeerGroupCreate,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> PeerGroupSummary:
    """Create a custom peer group from a list of ROR IDs.

    All ROR IDs must be present in the leiden_snapshot table.
    Custom groups can be used immediately for composite score calculation —
    no sync required (composite scores use leiden_snapshot data already in DB).
    Topic-distribution comparison may require cache filling on first use.
    """
    snapshot_result = await session.execute(
        select(func.max(LeidenSnapshot.snapshot_year))
    )
    snapshot_year = snapshot_result.scalar_one_or_none()

    if snapshot_year:
        valid_result = await session.execute(
            select(LeidenSnapshot.ror_id).where(
                LeidenSnapshot.ror_id.in_(body.ror_ids),
                LeidenSnapshot.snapshot_year == snapshot_year,
                LeidenSnapshot.field == "All sciences",
                LeidenSnapshot.frac_counting.is_(False),
                LeidenSnapshot.core_pubs_only.is_(False),
            )
        )
        valid_rors = {r[0] for r in valid_result.all()}
        invalid = [r for r in body.ror_ids if r not in valid_rors]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"ROR IDs not found in Leiden snapshot: {invalid}",
            )

    group = PeerGroup(name=body.name, type="custom", generated_at=None, params={})
    session.add(group)
    await session.flush()

    for ror_id in body.ror_ids:
        session.add(PeerGroupMember(peer_group_id=group.id, ror_id=ror_id))

    await session.commit()
    return PeerGroupSummary(
        id=group.id,
        name=group.name,
        type=group.type,
        member_count=len(body.ror_ids),
        generated_at=group.generated_at,
        params={},
    )


@router.put("/{group_id}", response_model=PeerGroupSummary)
async def update_peer_group(
    group_id: int,
    body: PeerGroupCreate,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> PeerGroupSummary:
    """Rename a custom peer group and replace its member list.

    Only custom groups can be edited — predefined groups (geographic,
    size_bracket) are regenerated automatically after each Leiden import.
    """
    result = await session.execute(select(PeerGroup).where(PeerGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Peer group not found")
    if group.type != "custom":
        raise HTTPException(status_code=400, detail="Seuls les groupes personnalisés peuvent être modifiés.")

    snapshot_result = await session.execute(select(func.max(LeidenSnapshot.snapshot_year)))
    snapshot_year = snapshot_result.scalar_one_or_none()
    if snapshot_year:
        valid_result = await session.execute(
            select(LeidenSnapshot.ror_id).where(
                LeidenSnapshot.ror_id.in_(body.ror_ids),
                LeidenSnapshot.snapshot_year == snapshot_year,
                LeidenSnapshot.field == "All sciences",
                LeidenSnapshot.frac_counting.is_(False),
                LeidenSnapshot.core_pubs_only.is_(False),
            )
        )
        valid_rors = {r[0] for r in valid_result.all()}
        invalid = [r for r in body.ror_ids if r not in valid_rors]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"ROR IDs not found in Leiden snapshot: {invalid}",
            )

    group.name = body.name
    await session.execute(delete(PeerGroupMember).where(PeerGroupMember.peer_group_id == group_id))
    for ror_id in body.ror_ids:
        session.add(PeerGroupMember(peer_group_id=group_id, ror_id=ror_id))

    await session.commit()
    return PeerGroupSummary(
        id=group.id,
        name=group.name,
        type=group.type,
        member_count=len(body.ror_ids),
        generated_at=group.generated_at,
        params=group.params or {},
    )


@router.delete("/{group_id}", status_code=204)
async def delete_peer_group(
    group_id: int,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> None:
    result = await session.execute(select(PeerGroup).where(PeerGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Peer group not found")
    if group.type != "custom":
        raise HTTPException(status_code=400, detail="Seuls les groupes personnalisés peuvent être supprimés.")
    await session.delete(group)
    await session.commit()


@router.get("/{group_id}/members", response_model=list[PeerMemberInfo])
async def list_members(
    group_id: int,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> list[PeerMemberInfo]:
    snapshot_result = await session.execute(
        select(func.max(LeidenSnapshot.snapshot_year))
    )
    snapshot_year = snapshot_result.scalar_one_or_none()

    members_result = await session.execute(
        select(PeerGroupMember.ror_id).where(PeerGroupMember.peer_group_id == group_id)
    )
    ror_ids = [r[0] for r in members_result.all()]

    if not ror_ids:
        return []

    leiden_result = await session.execute(
        select(
            LeidenSnapshot.ror_id,
            LeidenSnapshot.university_name,
            LeidenSnapshot.country_code,
            LeidenSnapshot.p,
        ).where(
            LeidenSnapshot.ror_id.in_(ror_ids),
            LeidenSnapshot.snapshot_year == snapshot_year,
            LeidenSnapshot.field == "All sciences",
            LeidenSnapshot.frac_counting.is_(False),
            LeidenSnapshot.core_pubs_only.is_(False),
        )
    )
    leiden_map = {r.ror_id: r for r in leiden_result.all()}

    return [
        PeerMemberInfo(
            ror_id=ror_id,
            university_name=(leiden_map[ror_id].university_name if ror_id in leiden_map else None),
            country_code=(leiden_map[ror_id].country_code if ror_id in leiden_map else None),
            p=(float(leiden_map[ror_id].p) if ror_id in leiden_map and leiden_map[ror_id].p is not None else None),
        )
        for ror_id in ror_ids
    ]


@router.get("/{group_id}/topic-distribution")
async def topic_distribution(
    group_id: int,
    background_tasks: BackgroundTasks,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger and/or report progress of the peer topic count cache fill.

    For small groups (< 20 members): fills synchronously, returns data.
    For large groups: triggers background fill, returns progress status.
    Poll this endpoint until status == "complete".
    """
    progress = get_fill_progress(group_id)
    if progress and not progress.running:
        return {"status": "complete", "progress": {"done": progress.done, "total": progress.total}}
    if progress and progress.running:
        return {"status": "in_progress", "progress": {"done": progress.done, "total": progress.total}}

    # Not started yet — kick off
    progress = await fill_cache_for_group(group_id)
    if not progress.running:
        return {"status": "complete", "progress": {"done": progress.done, "total": progress.total}}
    return {"status": "in_progress", "progress": {"done": 0, "total": progress.total}}


@router.get("/leiden-institutions")
async def search_leiden_institutions(
    q: str = Query(default="", min_length=2),
    country: str | None = Query(default=None),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Search institutions in the Leiden universe by name/country for custom group building."""
    snapshot_result = await session.execute(
        select(func.max(LeidenSnapshot.snapshot_year))
    )
    snapshot_year = snapshot_result.scalar_one_or_none()
    if not snapshot_year:
        return []

    query = (
        select(
            LeidenSnapshot.ror_id,
            LeidenSnapshot.university_name,
            LeidenSnapshot.country_code,
            LeidenSnapshot.p,
        )
        .where(
            LeidenSnapshot.snapshot_year == snapshot_year,
            LeidenSnapshot.field == "All sciences",
            LeidenSnapshot.frac_counting.is_(False),
            LeidenSnapshot.core_pubs_only.is_(False),
        )
        .limit(50)
        .order_by(LeidenSnapshot.p.desc())
    )

    if q:
        query = query.where(LeidenSnapshot.university_name.ilike(f"%{q}%"))
    if country:
        query = query.where(LeidenSnapshot.country_code == country.upper())

    result = await session.execute(query)
    return [
        {
            "ror_id": r.ror_id,
            "university_name": r.university_name,
            "country_code": r.country_code,
            "p": float(r.p) if r.p is not None else None,
        }
        for r in result.all()
    ]
