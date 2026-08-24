"""Resolve ROR IDs to OpenAlex institution IDs, with a DB cache."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.peers import InstitutionIdMap
from app.services.openalex_client import OpenAlexClient

logger = logging.getLogger(__name__)


def compute_effective_lineage(institution: dict) -> list[str]:
    """Return the set of OpenAlex institution IDs that make up this institution's scope.

    Confirmed bug (2026-08-21, real-data check on Université Paris-Saclay,
    I277688954): OpenAlex's own `lineage` field on the Institution object
    reflects strict ROR Parent/Child relations, and for many French institutions
    this is EMPTY beyond self — even for a textbook federated university with
    184 real component/child entities in OpenAlex. Those children ARE present
    in OpenAlex, just under a different field: `associated_institutions`, each
    entry carrying a `relationship` of "parent", "child", or "related".

    This function merges both signals: the configured institution itself,
    `lineage` (in case some institutions DO have it populated), and any
    `associated_institutions` entry marked relationship="child" — deduplicated,
    self always first. This is still an approximation (OpenAlex's own curation,
    not an official ROR hierarchy — some entries may be over- or under-inclusive,
    e.g. a "child" lab that later moved, cf. §4.1 of the spec), but it is far
    more complete than `lineage` alone for exactly the case (French federated
    universities) the spec flagged as most exposed to ROR data incompleteness.
    """
    self_id = institution.get("id")
    seen: list[str] = []
    if self_id:
        seen.append(self_id)

    for lid in institution.get("lineage") or []:
        if lid not in seen:
            seen.append(lid)

    for assoc in institution.get("associated_institutions") or []:
        if assoc.get("relationship") == "child" and assoc.get("id"):
            if assoc["id"] not in seen:
                seen.append(assoc["id"])

    return seen


async def resolve_ror(
    ror_id: str,
    session: AsyncSession,
    client: OpenAlexClient,
) -> str | None:
    """Return the OpenAlex institution ID for a given ROR ID.

    Checks the institution_id_map cache first; fetches from OpenAlex if missing.
    Returns None if no institution is found (e.g. ROR ID not in OpenAlex).
    """
    result = await session.execute(
        select(InstitutionIdMap).where(InstitutionIdMap.ror_id == ror_id)
    )
    cached = result.scalar_one_or_none()
    if cached:
        return cached.openalex_institution_id

    institution = await client.get_institution_by_ror(ror_id)
    if not institution:
        logger.warning("No OpenAlex institution found for ROR %s", ror_id)
        return None

    openalex_id = institution.get("id")
    if not openalex_id:
        return None

    stmt = pg_insert(InstitutionIdMap).values(
        ror_id=ror_id,
        openalex_institution_id=openalex_id,
        resolved_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        index_elements=["ror_id"],
        set_={"openalex_institution_id": openalex_id, "resolved_at": datetime.now(timezone.utc)},
    )
    await session.execute(stmt)
    await session.commit()
    return openalex_id