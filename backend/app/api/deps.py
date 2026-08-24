from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.instance_config import InstanceConfig


async def get_config(session: AsyncSession = Depends(get_db)) -> InstanceConfig:
    """Dependency that returns the instance config or raises 404 if not yet configured."""
    result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not yet configured. Complete setup at /setup.",
        )
    return config
