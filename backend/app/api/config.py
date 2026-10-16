"""Instance configuration endpoints.

GET /config  — returns current config (api_key_set: bool, never the key itself)
POST /config — saves initial configuration (from /setup wizard)
GET /config/validate — validates an OpenAlex institution ID without persisting
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config as get_current_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.services.openalex_client import OpenAlexClient
from app.services.institution_resolver import compute_effective_lineage
from app.services.openalex_sync import run_openalex_sync

router = APIRouter(prefix="/config", tags=["config"])
logger = logging.getLogger(__name__)


class ConfigResponse(BaseModel):
    openalex_institution_id: str
    ror_id: str | None
    institution_name: str
    openalex_lineage_ids: list[str]
    api_key_set: bool  # never expose the raw key
    contact_email: str
    country_code: str | None
    min_publications: int
    configured_at: datetime


class ConfigCreate(BaseModel):
    openalex_institution_id: str
    openalex_api_key: str
    contact_email: str
    institution_name: str | None = None  # pre-filled from OpenAlex if omitted


class LineageInfo(BaseModel):
    openalex_id: str
    display_name: str
    ror_id: str | None
    country_code: str | None


class ValidateResponse(BaseModel):
    openalex_institution_id: str
    institution_name: str
    ror_id: str | None
    country_code: str | None
    lineage: list[LineageInfo]


@router.get("", response_model=ConfigResponse)
async def get_config(session: AsyncSession = Depends(get_db)) -> ConfigResponse:
    result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Instance not yet configured")
    return ConfigResponse(
        openalex_institution_id=config.openalex_institution_id,
        ror_id=config.ror_id,
        institution_name=config.institution_name,
        openalex_lineage_ids=config.openalex_lineage_ids or [],
        api_key_set=bool(config.openalex_api_key),
        contact_email=config.contact_email,
        country_code=config.country_code,
        min_publications=config.min_publications,
        configured_at=config.configured_at,
    )


@router.get("/validate", response_model=ValidateResponse)
async def validate_institution(
    openalex_id: str,
    api_key: str,
    contact_email: str,
) -> ValidateResponse:
    """Validate an OpenAlex institution ID and return institution details + lineage.

    Called from step 1 of the /setup wizard to confirm the ID is valid before
    persisting. Also returns the effective lineage (child structures) so the
    user can verify the ingestion scope before committing.

    IMPORTANT (found 2026-08-21 on real data): OpenAlex's own `lineage` field is
    NOT a reliable source of child institutions for many French institutions —
    it comes back empty (self only) even for large federated universities.
    `associated_institutions` (relationship="child") is the field that's
    actually populated for these cases. See compute_effective_lineage() for
    the full explanation; this endpoint uses that merged/deduplicated set.
    """
    async with OpenAlexClient(api_key, contact_email) as client:
        try:
            institution = await client.get_institution(openalex_id)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"OpenAlex lookup failed: {exc}. Check the institution ID and API key.",
            )

    lineage_ids = compute_effective_lineage(institution)

    # associated_institutions entries carry display_name/ror inline — no extra
    # API calls needed to enrich child entries beyond the self one.
    assoc_by_id = {
        a["id"]: a
        for a in (institution.get("associated_institutions") or [])
        if a.get("id")
    }

    lineage_details: list[LineageInfo] = []
    for lid in lineage_ids:
        if lid == institution.get("id"):
            lineage_details.append(LineageInfo(
                openalex_id=lid,
                display_name=institution.get("display_name", lid),
                ror_id=institution.get("ror"),
                country_code=institution.get("country_code"),
            ))
        elif lid in assoc_by_id:
            lineage_details.append(LineageInfo(
                openalex_id=lid,
                display_name=assoc_by_id[lid].get("display_name", lid),
                ror_id=assoc_by_id[lid].get("ror"),
                country_code=None,  # not included in the associated_institutions payload
            ))
        else:
            lineage_details.append(LineageInfo(
                openalex_id=lid,
                display_name=lid,  # placeholder — enriched after save if needed
                ror_id=None,
                country_code=None,
            ))

    return ValidateResponse(
        openalex_institution_id=institution.get("id", openalex_id),
        institution_name=institution.get("display_name", ""),
        ror_id=institution.get("ror"),
        country_code=institution.get("country_code"),
        lineage=lineage_details,
    )


@router.post("", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    body: ConfigCreate,
    session: AsyncSession = Depends(get_db),
) -> ConfigResponse:
    """Persist the instance configuration.

    Calls OpenAlex to fill in ror_id, country_code, and lineage_ids from the
    institution object. The api_key is stored in the DB and never returned.

    If this is the very first configuration (no row existed before), a
    first OpenAlex sync is kicked off automatically in the background —
    the user shouldn't have to know about /admin/sync/openalex to see any
    data on first use. Subsequent edits via PATCH /config (changing the
    institution later) do NOT auto-trigger a sync — see update_config().
    """
    existing_result = await session.execute(select(InstanceConfig.id).where(InstanceConfig.id == 1))
    is_first_configuration = existing_result.scalar_one_or_none() is None

    async with OpenAlexClient(body.openalex_api_key, body.contact_email) as client:
        try:
            institution = await client.get_institution(body.openalex_institution_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"OpenAlex lookup failed: {exc}")

    lineage_ids = compute_effective_lineage(institution)
    country_code = institution.get("country_code")
    ror_id = institution.get("ror")
    institution_name = body.institution_name or institution.get("display_name", "")

    stmt = pg_insert(InstanceConfig).values(
        id=1,
        openalex_institution_id=body.openalex_institution_id,
        ror_id=ror_id,
        institution_name=institution_name,
        openalex_lineage_ids=lineage_ids,
        openalex_api_key=body.openalex_api_key,
        contact_email=body.contact_email,
        country_code=country_code,
        min_publications=10,
        configured_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        index_elements=["id"],
        set_={
            "openalex_institution_id": body.openalex_institution_id,
            "ror_id": ror_id,
            "institution_name": institution_name,
            "openalex_lineage_ids": lineage_ids,
            "openalex_api_key": body.openalex_api_key,
            "contact_email": body.contact_email,
            "country_code": country_code,
            "configured_at": datetime.now(timezone.utc),
        },
    )
    await session.execute(stmt)
    await session.commit()

    logger.info("Instance configured: %s (%s)", institution_name, body.openalex_institution_id)

    if is_first_configuration:
        logger.info("First-ever configuration — triggering initial OpenAlex sync in the background")
        asyncio.create_task(run_openalex_sync())

    return ConfigResponse(
        openalex_institution_id=body.openalex_institution_id,
        ror_id=ror_id,
        institution_name=institution_name,
        openalex_lineage_ids=lineage_ids,
        api_key_set=True,
        contact_email=body.contact_email,
        country_code=country_code,
        min_publications=10,
        configured_at=datetime.now(timezone.utc),
    )


class ConfigUpdate(BaseModel):
    """Partial update — the settings page sends only the field(s) actually changed.

    openalex_api_key is write-only (never echoed back, cf. ConfigResponse), so
    the frontend never needs to know the current key to change an unrelated field.
    Changing openalex_institution_id re-resolves ror_id/country_code/lineage from
    OpenAlex (using the newly supplied api_key/contact_email if provided in the
    same request, otherwise the values already stored) but — unlike the initial
    /setup flow — does NOT trigger an immediate sync: the new institution's data
    will only appear after the next nightly sync_openalex_nightly run. The
    frontend is responsible for surfacing that delay to the user.
    """
    openalex_institution_id: str | None = None
    openalex_api_key: str | None = None
    contact_email: str | None = None
    institution_name: str | None = None
    # Minimum publications for an institution to be compared on a scope
    # (see InstanceConfig.min_publications).
    min_publications: int | None = Field(default=None, ge=1, le=100_000)


@router.patch("", response_model=ConfigResponse)
async def update_config(
    body: ConfigUpdate,
    config: InstanceConfig = Depends(get_current_config),
    session: AsyncSession = Depends(get_db),
) -> ConfigResponse:
    values: dict = {}

    if body.openalex_institution_id and body.openalex_institution_id != config.openalex_institution_id:
        api_key = body.openalex_api_key or config.openalex_api_key
        contact_email = body.contact_email or config.contact_email
        async with OpenAlexClient(api_key, contact_email) as client:
            try:
                institution = await client.get_institution(body.openalex_institution_id)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"OpenAlex lookup failed: {exc}")
        values["openalex_institution_id"] = body.openalex_institution_id
        values["ror_id"] = institution.get("ror")
        values["country_code"] = institution.get("country_code")
        values["openalex_lineage_ids"] = compute_effective_lineage(institution)
        values["institution_name"] = body.institution_name or institution.get("display_name", "")
        logger.info(
            "Instance institution changed: %s -> %s (new data effective at next nightly sync)",
            config.openalex_institution_id, body.openalex_institution_id,
        )
    elif body.institution_name:
        values["institution_name"] = body.institution_name

    if body.openalex_api_key:
        values["openalex_api_key"] = body.openalex_api_key
    if body.contact_email:
        values["contact_email"] = body.contact_email
    if body.min_publications is not None:
        values["min_publications"] = body.min_publications

    if not values:
        raise HTTPException(status_code=400, detail="No fields to update")

    for key, value in values.items():
        setattr(config, key, value)
    await session.commit()
    await session.refresh(config)

    return ConfigResponse(
        openalex_institution_id=config.openalex_institution_id,
        ror_id=config.ror_id,
        institution_name=config.institution_name,
        openalex_lineage_ids=config.openalex_lineage_ids or [],
        api_key_set=bool(config.openalex_api_key),
        contact_email=config.contact_email,
        country_code=config.country_code,
        min_publications=config.min_publications,
        configured_at=config.configured_at,
    )
