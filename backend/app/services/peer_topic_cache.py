"""On-demand cache of per-topic publication counts for peer institutions.

Strategy (§4.4):
  Rather than ingesting all publications for every peer (prohibitively expensive),
  we call the OpenAlex group_by API which returns publication counts per topic for a
  given institution in a single paginated response — one call per statistic (all
  works, top 10 % cited, open access, international collaboration), see
  services/topics_signature.py. Per-publication data for peers (e.g. raw citation
  counts) would require full publication ingestion for each peer — explicitly
  deferred to v2 (§4.5 option b).

  The lineage filter is applied for peers too, for consistency with the configured
  institution's ingestion scope.

Cache refresh policy [Défaut — modifiable]:
  Peer topic counts are refreshed on each sync_leiden_annual (not nightly), since
  institutional topic profiles evolve slowly and the peer list itself only changes
  when Leiden data is refreshed. TTL is therefore on the order of months.
"""

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.instance_config import InstanceConfig
from app.models.peers import PeerGroup, PeerGroupMember, PeerTopicCount
from app.services.openalex_client import OpenAlexClient
from app.services.institution_resolver import resolve_ror
from app.services.quality.comparable import current_window, ensure_counts
from app.services.topics_signature import ensure_topic_stats
from app.services.ror import normalize_ror

logger = logging.getLogger(__name__)

# In-memory progress tracker for large groups
@dataclass
class CacheFillProgress:
    total: int = 0
    done: int = 0
    failed: int = 0
    running: bool = True

_fill_progress: dict[int, CacheFillProgress] = {}


def get_fill_progress(peer_group_id: int) -> CacheFillProgress | None:
    return _fill_progress.get(peer_group_id)


async def fill_cache_for_group(peer_group_id: int) -> CacheFillProgress:
    """Populate peer_topic_counts for all members of a peer group.

    For small groups (< SYNC_THRESHOLD members): runs synchronously and returns
    when complete. For large groups: runs as a background asyncio task, returns
    immediately with progress object that callers can poll.
    """
    # 0: always in the background — with the quality-axis counts (~30 OpenAlex
    # count queries per institution) even a small group no longer fits in one
    # HTTP request. The frontend panel polls the progress.
    SYNC_THRESHOLD = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PeerGroupMember).where(PeerGroupMember.peer_group_id == peer_group_id)
        )
        members = result.scalars().all()
        config_result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
        config = config_result.scalar_one()

    progress = CacheFillProgress(total=len(members), running=True)
    _fill_progress[peer_group_id] = progress

    if len(members) <= SYNC_THRESHOLD:
        await _do_fill(peer_group_id, members, config, progress)
    else:
        asyncio.create_task(_do_fill(peer_group_id, members, config, progress))

    return progress


async def _do_fill(
    peer_group_id: int,
    members: list[PeerGroupMember],
    config: InstanceConfig,
    progress: CacheFillProgress,
) -> None:
    # Same pass fills, for every member and for the reference institution
    # itself, the per-topic statistics (topics signature,
    # services/topics_signature.py) and the quality-axis counts
    # (services/quality/comparable.py), both over the current Leiden window.
    async with AsyncSessionLocal() as session:
        years = await current_window(session)
    if not years:
        logger.warning("Peer cache fill skipped: no Leiden window (import Leiden data first)")
        progress.running = False
        return
    async with OpenAlexClient(config.openalex_api_key, config.contact_email) as client:
        own_ror = normalize_ror(config.ror_id)
        try:
            await ensure_topic_stats(client, config.openalex_institution_id, own_ror, years)
        except Exception as exc:
            logger.warning("Failed to fetch topic statistics of the reference institution: %s", exc)
        await ensure_counts(client, config.openalex_institution_id, own_ror, years)
        for member in members:
            try:
                async with AsyncSessionLocal() as session:
                    openalex_id = await resolve_ror(member.ror_id, session, client)
                if openalex_id:
                    await ensure_topic_stats(client, openalex_id, member.ror_id, years)
                    await ensure_counts(client, openalex_id, member.ror_id, years)
                progress.done += 1
            except Exception as exc:
                logger.warning(
                    "Failed to fetch topic/quality counts for %s: %s", member.ror_id, exc
                )
                progress.failed += 1
    progress.running = False
    logger.info(
        "Peer topic cache fill for group %d complete: %d/%d done, %d failed",
        peer_group_id,
        progress.done,
        progress.total,
        progress.failed,
    )


async def invalidate_cache_for_group(peer_group_id: int, session: AsyncSession) -> None:
    """Remove cached topic counts for all members of a group (e.g. after Leiden refresh)."""
    result = await session.execute(
        select(PeerGroupMember).where(PeerGroupMember.peer_group_id == peer_group_id)
    )
    members = result.scalars().all()
    ror_ids = [m.ror_id for m in members]
    if ror_ids:
        await session.execute(
            select(PeerTopicCount).where(
                PeerTopicCount.ror_id.in_(ror_ids)
            )
        )
