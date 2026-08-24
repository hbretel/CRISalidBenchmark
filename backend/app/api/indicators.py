from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.services.indicators_impact import get_impact_indicators
from app.services.indicators_specificity import get_specificity_indicators
from app.services.composite_score import calculate_composite

router = APIRouter(prefix="/indicators", tags=["indicators"])

LEIDEN_FIELDS = {
    "All sciences",
    "Biomedical and health sciences",
    "Life and earth sciences",
    "Mathematics and computer science",
    "Physical sciences and engineering",
    "Social sciences and humanities",
}


@router.get("/impact-scientifique")
async def impact_scientifique(
    peer_group_id: int = Query(...),
    field: str = Query(default="All sciences"),
    core_only: bool = Query(default=True),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if field not in LEIDEN_FIELDS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"field must be one of {LEIDEN_FIELDS}")
    return await get_impact_indicators(session, peer_group_id, field, core_only)


@router.get("/specificite-disciplinaire")
async def specificite_disciplinaire(
    peer_group_id: int = Query(...),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await get_specificity_indicators(session, peer_group_id)


@router.get("/composite")
async def composite(
    weight_profile_id: int = Query(...),
    peer_group_id: int = Query(...),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await calculate_composite(session, weight_profile_id, peer_group_id)
