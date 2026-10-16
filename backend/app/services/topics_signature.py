"""Topics signature of the reference institution.

Definition: for a given comparison group, the signature topics of the
reference institution are the OpenAlex topics (finest level of the taxonomy,
~4 500 topics) in which it ranks first of the group on the global score.
Computed for the reference institution only, and never fed back into the
global score itself.

Topic-level global score — exactly the institution-level score of the
comparison-group benchmark (group_benchmark.score_scope), computed on the
topic instead of a domain: every institution of the group is described on the
topic by the same counts as at institution level — total and every
comparable criterion (quality/comparable.py COMPARABLE_FILTERS), one
paginated group_by=primary_topic.id call per count (peer_topic_counts, filled
by the peer cache, current Leiden window). Hence, on each topic:

  - impact axis: percentiles of the 8 shares (PP(top 1 %), PP(top 10 %),
    FWCI ≥ 1, ≥ 10 citations, cited, OA, international and industry
    collaboration);
  - volume axis: percentiles of the 9 matching numbers of publications (P,
    P(FWCI ≥ 1), …);
  - specialization axis: percentile of the topic's share of the institution's
    output (topic-level counterpart of the specialization rate; denominator:
    the institution's publications with a primary topic, as at domain level);
  - quality axis: estimated grid coefficients per category from the topic's
    criterion shares, and their percentiles;

weighted with the profile and the instance-wide quality category weights.

Only institutions with at least instance_config.min_publications publications
in a topic are compared on it (shares over a handful of publications are
noise), and only topics where the reference institution itself reaches that
threshold can be signature topics.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import Text, cast, delete, select
from sqlalchemy.dialects.postgresql import ARRAY, array
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroupMember, PeerTopicCount
from app.models.profiles import WeightProfile
from app.models.works import Topic
from app.services.group_benchmark import score_scope
from app.services.openalex_client import OpenAlexClient
from app.services.quality.comparable import (
    COMPARABLE_FILTERS,
    TOTAL_KEY,
    category_weights,
    criteria_terms,
    current_window,
)
from app.services.ror import normalize_ror

logger = logging.getLogger(__name__)

# Count key → extra OpenAlex filter: the institution-level counts, per topic.
TOPIC_COUNT_FILTERS: dict[str, str] = {TOTAL_KEY: "", **COMPARABLE_FILTERS}
_CONCURRENCY = 4


def fresh_topic_counts():
    """SQL condition: the row holds every count currently needed (rows from
    before a criterion was added are refetched)."""
    return PeerTopicCount.counts.has_all(cast(array(list(TOPIC_COUNT_FILTERS)), ARRAY(Text)))


# ── Cache fill ────────────────────────────────────────────────────────────────

async def has_fresh_topic_stats(openalex_id: str, years: tuple[int, int]) -> bool:
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(PeerTopicCount.id).where(
                PeerTopicCount.openalex_institution_id == openalex_id,
                PeerTopicCount.period_start == years[0],
                PeerTopicCount.period_end == years[1],
                fresh_topic_counts(),
            ).limit(1)
        )).scalar_one_or_none()
    return row is not None


async def ensure_topic_stats(
    client: OpenAlexClient, openalex_id: str, ror_id: str | None, years: tuple[int, int], force: bool = False
) -> None:
    """Fetch and store the per-topic counts of one institution for the current
    window, unless already cached for it. Rows of a previous window are
    replaced (a topic absent from the new window must not linger)."""
    if not force and await has_fresh_topic_stats(openalex_id, years):
        return
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def fetch(extra: str) -> list[dict]:
        async with sem:
            return await client.get_topic_counts_for_institution(openalex_id, years, extra)

    keys = list(TOPIC_COUNT_FILTERS)
    results = await asyncio.gather(*(fetch(TOPIC_COUNT_FILTERS[k]) for k in keys))
    per_topic: dict[str, dict[str, int]] = {}
    for key, groups in zip(keys, results):
        for group in groups:
            per_topic.setdefault(group["key"], {})[key] = int(group.get("count", 0))

    async with AsyncSessionLocal() as session:
        known = set((await session.execute(
            select(Topic.id).where(Topic.id.in_(list(per_topic)))
        )).scalars().all()) if per_topic else set()
        now = datetime.now(timezone.utc)
        rows = [
            {
                "openalex_institution_id": openalex_id,
                "ror_id": ror_id,
                "topic_id": topic_id,
                "works_count": stats.get(TOTAL_KEY, 0),
                # Every key present (0 when OpenAlex returned no group).
                "counts": {key: stats.get(key, 0) for key in keys},
                "period_start": years[0],
                "period_end": years[1],
                "fetched_at": now,
            }
            # Topics missing from the local taxonomy (not yet synced) would
            # violate the foreign key: skipped until the next taxonomy sync.
            for topic_id, stats in per_topic.items()
            if topic_id in known and stats.get(TOTAL_KEY)
        ]
        await session.execute(delete(PeerTopicCount).where(PeerTopicCount.openalex_institution_id == openalex_id))
        # asyncpg caps a statement at 32 767 bind parameters (9 per row).
        for start in range(0, len(rows), 3000):
            await session.execute(pg_insert(PeerTopicCount).values(rows[start:start + 3000]))
        await session.commit()


# ── Signature computation ────────────────────────────────────────────────────

async def get_topics_signature(session: AsyncSession, peer_group_id: int, weight_profile_id: int) -> dict:
    profile = (await session.execute(
        select(WeightProfile).where(WeightProfile.id == weight_profile_id)
    )).scalar_one_or_none()
    if not profile:
        raise ValueError(f"WeightProfile {weight_profile_id} not found")
    config = (await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))).scalar_one()
    own_ror = normalize_ror(config.ror_id)
    min_publications = config.min_publications
    members = list((await session.execute(
        select(PeerGroupMember.ror_id).where(PeerGroupMember.peer_group_id == peer_group_id)
    )).scalars().all())
    years = await current_window(session)

    weights = await category_weights(session)
    terms = criteria_terms()
    sub_weights = {**profile.sub_indicator_weights, "qualite": weights}

    base = {
        "min_publications": min_publications,
        "period_start": years[0] if years else None,
        "period_end": years[1] if years else None,
        "group_size": len(set(members) - {own_ror}),
        "axis_weights": profile.axis_weights,
        "items": [],
    }
    if not years or not own_ror:
        return {**base, "own_cache_populated": False, "peer_cache_populated": False, "institutions_with_data": 0}

    ror_ids = list({*members, own_ror})
    rows = (await session.execute(
        select(PeerTopicCount.ror_id, PeerTopicCount.topic_id, PeerTopicCount.counts).where(
            PeerTopicCount.ror_id.in_(ror_ids),
            PeerTopicCount.period_start == years[0],
            PeerTopicCount.period_end == years[1],
            fresh_topic_counts(),
        )
    )).all()

    stats: dict[str, dict[str, dict]] = {}  # ror → topic → counts
    totals: dict[str, int] = {}
    for ror, topic_id, counts in rows:
        stats.setdefault(ror, {})[topic_id] = counts
        totals[ror] = totals.get(ror, 0) + int(counts.get(TOTAL_KEY, 0))
    own_stats = stats.get(own_ror, {})
    result = {
        **base,
        "own_cache_populated": bool(own_stats),
        "peer_cache_populated": len(set(stats) - {own_ror}) > 0,
        "institutions_with_data": len(stats),
    }
    # Without any peer statistics, "first of the group" would hold for every
    # topic: nothing is listed until the peer cache has been filled.
    if not own_stats or not result["peer_cache_populated"]:
        return result

    names = dict((await session.execute(
        select(LeidenSnapshot.ror_id, LeidenSnapshot.university_name)
        .where(LeidenSnapshot.ror_id.in_(list(stats)))
        .distinct()
    )).all())

    candidate_topics = [tid for tid, c in own_stats.items() if c.get(TOTAL_KEY, 0) >= min_publications]
    topics = {
        t.id: t for t in (await session.execute(
            select(Topic).where(Topic.id.in_(candidate_topics))
        )).scalars().all()
    } if candidate_topics else {}

    items = []
    for topic_id in candidate_topics:
        scoped = {ror: by_topic[topic_id] for ror, by_topic in stats.items() if topic_id in by_topic}
        specialization = {ror: 100.0 * c.get(TOTAL_KEY, 0) / totals[ror] for ror, c in scoped.items()}
        scores = score_scope(
            scoped, specialization, min_publications, profile.axis_weights, sub_weights, terms, weights,
            with_quality_top=False,
        )
        own = scores[own_ror]
        own_score = own["composite_score"]
        others = sorted(
            ((s["composite_score"], ror) for ror, s in scores.items() if ror != own_ror and s["compared"]),
            reverse=True,
        )
        if others and others[0][0] > own_score + 1e-9:
            continue
        runner_up_score, runner_up = others[0] if others else (None, None)
        topic = topics.get(topic_id)
        items.append({
            "topic_id": topic_id,
            "topic_name": topic.display_name if topic else topic_id,
            "subfield_name": topic.subfield_name if topic else None,
            "field_name": topic.field_name if topic else None,
            "own_publications": own["p"],
            "own_share_permille": round(1000.0 * own["p"] / totals[own_ror], 2),
            "own_impact": own["impact"],
            "own_volume": own["volume"],
            "own_quality": own["quality"]["estimates"]["global"] if own["quality"] else None,
            "own_score": own_score,
            "breakdown": own["breakdown"],
            "runner_up_score": runner_up_score,
            "runner_up_name": (names.get(runner_up) or runner_up) if runner_up else None,
            "margin": round(own_score - runner_up_score, 1) if runner_up_score is not None else None,
            "n_compared": 1 + len(others),
        })

    # Clearest leads first; topics where no peer reaches the threshold (no
    # margin) after them, largest first.
    items.sort(key=lambda i: (i["margin"] is None, -(i["margin"] or 0), -i["own_publications"]))
    result["items"] = items
    return result
