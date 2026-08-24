from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.models.profiles import WeightProfile

router = APIRouter(tags=["profiles"])


class WeightProfileCreate(BaseModel):
    name: str
    axis_weights: dict[str, float]
    sub_indicator_weights: dict[str, dict[str, float]]

    @model_validator(mode="after")
    def validate_sums(self) -> "WeightProfileCreate":
        axis_sum = sum(self.axis_weights.values())
        if abs(axis_sum - 1.0) > 0.001:
            raise ValueError(f"axis_weights must sum to 1.0 (got {axis_sum:.4f})")
        for axis, sub in self.sub_indicator_weights.items():
            sub_sum = sum(sub.values())
            if abs(sub_sum - 1.0) > 0.001:
                raise ValueError(
                    f"sub_indicator_weights['{axis}'] must sum to 1.0 (got {sub_sum:.4f})"
                )
        return self


class WeightProfileResponse(BaseModel):
    id: int
    name: str
    axis_weights: dict
    sub_indicator_weights: dict
    is_default: bool
    created_at: datetime


@router.get("/weight-profiles", response_model=list[WeightProfileResponse])
async def list_weight_profiles(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> list[WeightProfileResponse]:
    result = await session.execute(
        select(WeightProfile).order_by(WeightProfile.is_default.desc(), WeightProfile.created_at.desc())
    )
    return [
        WeightProfileResponse(
            id=p.id, name=p.name, axis_weights=p.axis_weights,
            sub_indicator_weights=p.sub_indicator_weights, is_default=p.is_default,
            created_at=p.created_at,
        )
        for p in result.scalars().all()
    ]


@router.post("/weight-profiles", response_model=WeightProfileResponse, status_code=201)
async def create_weight_profile(
    body: WeightProfileCreate,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> WeightProfileResponse:
    profile = WeightProfile(
        name=body.name,
        axis_weights=body.axis_weights,
        sub_indicator_weights=body.sub_indicator_weights,
        is_default=False,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return WeightProfileResponse(
        id=profile.id, name=profile.name, axis_weights=profile.axis_weights,
        sub_indicator_weights=profile.sub_indicator_weights, is_default=profile.is_default,
        created_at=profile.created_at,
    )


@router.get("/weight-profiles/{profile_id}", response_model=WeightProfileResponse)
async def get_weight_profile(
    profile_id: int,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> WeightProfileResponse:
    result = await session.execute(select(WeightProfile).where(WeightProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Weight profile not found")
    return WeightProfileResponse(
        id=profile.id, name=profile.name, axis_weights=profile.axis_weights,
        sub_indicator_weights=profile.sub_indicator_weights, is_default=profile.is_default,
        created_at=profile.created_at,
    )


@router.put("/weight-profiles/{profile_id}", response_model=WeightProfileResponse)
async def update_weight_profile(
    profile_id: int,
    body: WeightProfileCreate,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> WeightProfileResponse:
    result = await session.execute(select(WeightProfile).where(WeightProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Weight profile not found")
    if profile.is_default:
        raise HTTPException(
            status_code=400,
            detail="Le profil par défaut 'Équilibré' ne peut pas être modifié. Créez un nouveau profil.",
        )
    profile.name = body.name
    profile.axis_weights = body.axis_weights
    profile.sub_indicator_weights = body.sub_indicator_weights
    await session.commit()
    await session.refresh(profile)
    return WeightProfileResponse(
        id=profile.id, name=profile.name, axis_weights=profile.axis_weights,
        sub_indicator_weights=profile.sub_indicator_weights, is_default=profile.is_default,
        created_at=profile.created_at,
    )


@router.delete("/weight-profiles/{profile_id}", status_code=204)
async def delete_weight_profile(
    profile_id: int,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> None:
    result = await session.execute(select(WeightProfile).where(WeightProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Weight profile not found")
    if profile.is_default:
        raise HTTPException(status_code=400, detail="Le profil par défaut 'Équilibré' ne peut pas être supprimé.")
    await session.delete(profile)
    await session.commit()
