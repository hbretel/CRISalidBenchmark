"""Predefined peer group calculation (geographic + size bracket)."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroup, PeerGroupMember

logger = logging.getLogger(__name__)


async def get_latest_snapshot_year(session: AsyncSession) -> int | None:
    result = await session.execute(
        select(func.max(LeidenSnapshot.snapshot_year))
    )
    return result.scalar_one_or_none()


async def recalculate_predefined_groups(session: AsyncSession) -> None:
    """Rebuild geographic and size-bracket peer groups from the latest Leiden snapshot.

    Called automatically after each successful Leiden import.
    Existing predefined groups are replaced (custom groups are untouched).

    Geographic group: all Leiden institutions with the same country_code as the
    configured institution, from the most recent snapshot year.

    Size-bracket groups: institutions partitioned into deciles by `p` (publication
    count) across the full Leiden universe. Sized on core_pubs_only=False rows
    (total publication volume, not just the core subset) — a more intuitive and
    universally available "institution size" measure than the core-only count.
    The group containing the configured institution is highlighted in the UI as
    the most natural comparison set. Decile boundaries are recomputed on each
    Leiden import.
    """
    result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
    config = result.scalar_one_or_none()
    if not config:
        logger.warning("No instance config — skipping peer group recalculation")
        return

    snapshot_year = await get_latest_snapshot_year(session)
    if not snapshot_year:
        logger.warning("No Leiden snapshot data — skipping peer group recalculation")
        return

    # Load all institutions at field='All sciences', frac_counting=False,
    # core_pubs_only=False (total publication volume — see docstring above).
    result = await session.execute(
        select(LeidenSnapshot).where(
            LeidenSnapshot.snapshot_year == snapshot_year,
            LeidenSnapshot.field == "All sciences",
            LeidenSnapshot.frac_counting.is_(False),
            LeidenSnapshot.core_pubs_only.is_(False),
            LeidenSnapshot.ror_id != config.ror_id,  # exclude configured institution from peers
        )
    )
    all_institutions = result.scalars().all()

    if not all_institutions:
        logger.warning("Leiden snapshot has no institutions for peer group calculation")
        return

    # ── Geographic group ───────────────────────────────────────────────────
    await _upsert_geographic_group(session, all_institutions, config, snapshot_year)

    # ── Size-bracket groups (deciles) ──────────────────────────────────────
    await _upsert_size_bracket_groups(session, all_institutions, config, snapshot_year)

    logger.info("Predefined peer groups recalculated (snapshot_year=%d)", snapshot_year)


async def _upsert_geographic_group(
    session: AsyncSession,
    institutions: list[LeidenSnapshot],
    config: InstanceConfig,
    snapshot_year: int,
) -> None:
    geographic_members = [i for i in institutions if i.country_code == config.country_code]

    # Delete existing geographic group
    await session.execute(
        delete(PeerGroup).where(PeerGroup.type == "geographic")
    )

    group = PeerGroup(
        name=f"Même pays ({config.country_code})",
        type="geographic",
        generated_at=datetime.now(timezone.utc),
        params={"country_code": config.country_code, "snapshot_year": snapshot_year},
    )
    session.add(group)
    await session.flush()  # get group.id

    for inst in geographic_members:
        session.add(PeerGroupMember(peer_group_id=group.id, ror_id=inst.ror_id))

    logger.info("Geographic peer group: %d institutions", len(geographic_members))


async def _upsert_size_bracket_groups(
    session: AsyncSession,
    institutions: list[LeidenSnapshot],
    config: InstanceConfig,
    snapshot_year: int,
    n_deciles: int = 10,
) -> None:
    # Sort by p; institutions with null p go last
    sorted_insts = sorted(institutions, key=lambda i: (float(i.p) if i.p is not None else 0))
    n = len(sorted_insts)

    if n == 0:
        return

    # Delete existing size_bracket groups
    await session.execute(
        delete(PeerGroup).where(PeerGroup.type == "size_bracket")
    )

    # Compute decile boundaries
    decile_size = n / n_deciles
    for d in range(n_deciles):
        start = int(d * decile_size)
        end = int((d + 1) * decile_size)
        decile_members = sorted_insts[start:end]
        if not decile_members:
            continue

        p_min = int(decile_members[0].p) if decile_members[0].p is not None else 0
        p_max = int(decile_members[-1].p) if decile_members[-1].p is not None else 0
        label = f"Décile {d + 1} ({p_min}–{p_max} publications)"

        group = PeerGroup(
            name=label,
            type="size_bracket",
            generated_at=datetime.now(timezone.utc),
            params={
                "decile": d + 1,
                "p_min": p_min,
                "p_max": p_max,
                "snapshot_year": snapshot_year,
            },
        )
        session.add(group)
        await session.flush()

        for inst in decile_members:
            session.add(PeerGroupMember(peer_group_id=group.id, ror_id=inst.ror_id))

    logger.info("Size-bracket peer groups (deciles) recalculated")
