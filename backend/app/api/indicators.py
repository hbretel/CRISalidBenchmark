from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.services.indicators_specificity import get_thematic_profile
from app.services.topics_signature import get_topics_signature
from app.services.world_ranking import get_world_ranking

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/world-ranking")
async def world_ranking(
    field: str = Query(default="All sciences"),
    core_only: bool = Query(default=True),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """"Monde entier" tab: Leiden Ranking indicators of every university, and
    the reference institution's ranks (services/world_ranking.py)."""
    try:
        return await get_world_ranking(session, field, core_only)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/thematic-profile")
async def thematic_profile(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """OpenAlex Domain > Field > Subfield > Topic tree of the reference institution."""
    return await get_thematic_profile(session)


@router.get("/topics-signature")
async def topics_signature(
    peer_group_id: int = Query(...),
    weight_profile_id: int = Query(...),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Topics in which the reference institution ranks first of the group on
    the topic-level global score (services/topics_signature.py)."""
    try:
        return await get_topics_signature(session, peer_group_id, weight_profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
