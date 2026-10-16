"""Topics signature of the reference institution.

Definition: for a given comparison group, the signature topics of the
reference institution are the OpenAlex topics (finest level of the taxonomy,
~4 500 topics) in which it ranks first of the group on the global score.
Computed for the reference institution only, and never fed back into the
global score itself.

Topic-level global score — the same two-level aggregation as the
institution-level score (composite_score.py), restricted to what OpenAlex can
count per topic for every institution with one group_by call per statistic
(peer_topic_counts, filled by the peer cache, current Leiden window):

  - impact axis: percentile (mid-rank, ties counted half), among the
    institutions compared on the topic, of
      * share of publications in the top 10 % most cited
        (citation_normalized_percentile) → pp_top_10,
      * share of open-access publications → pp_oa,
      * share of internationally co-authored publications
        (countries_distinct_count > 1) → pp_int_collab,
    weighted with the profile's impact sub-weights (the other impact
    indicators of the group benchmark are not fetched per topic and are left
    out, their weights renormalized);
  - specialization axis: percentile of the topic's share of the institution's
    output (topic-level counterpart of the specialization rate);
  - the quality axis is not available at topic level (it would take ~30
    paginated group_by queries per institution, one per grid criterion) — the
    two axes above are renormalized over their profile weights, exactly as the
    institution-level score does for an axis without data.

Only institutions with at least instance_config.min_publications publications in a topic
are compared on it (shares over a handful of publications are noise), and only
topics where the reference institution itself reaches that threshold can be
signature topics.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroupMember, PeerTopicCount
from app.models.profiles import WeightProfile
from app.models.works import Topic
from app.services.composite_score import _weighted_average, combine_axes
from app.services.openalex_client import OpenAlexClient
from app.services.quality.comparable import current_window, percentile_midrank
from app.services.ror import normalize_ror

logger = logging.getLogger(__name__)

# Statistic → extra OpenAlex filter (verified on the API on 2026-10-16, same
# filters as the quality axis — services/quality/comparable.py).
TOPIC_STAT_FILTERS: dict[str, str] = {
    "works_count": "",
    "top10_count": "citation_normalized_percentile.is_in_top_10_percent:true",
    "oa_count": "open_access.is_oa:true",
    "intl_collab_count": "countries_distinct_count:>1",
}


# ── Cache fill ────────────────────────────────────────────────────────────────

async def has_fresh_topic_stats(openalex_id: str, years: tuple[int, int]) -> bool:
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(PeerTopicCount.id).where(
                PeerTopicCount.openalex_institution_id == openalex_id,
                PeerTopicCount.period_start == years[0],
                PeerTopicCount.period_end == years[1],
                PeerTopicCount.top10_count.is_not(None),
            ).limit(1)
        )).scalar_one_or_none()
    return row is not None


async def ensure_topic_stats(
    client: OpenAlexClient, openalex_id: str, ror_id: str | None, years: tuple[int, int], force: bool = False
) -> None:
    """Fetch and store the per-topic statistics of one institution for the
    current window, unless already cached for it. Rows of a previous window
    are replaced (a topic absent from the new window must not linger)."""
    if not force and await has_fresh_topic_stats(openalex_id, years):
        return
    per_topic: dict[str, dict[str, int]] = {}
    for stat, extra in TOPIC_STAT_FILTERS.items():
        for group in await client.get_topic_counts_for_institution(openalex_id, years, extra):
            per_topic.setdefault(group["key"], {})[stat] = int(group.get("count", 0))

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
                "works_count": stats.get("works_count", 0),
                "top10_count": stats.get("top10_count", 0),
                "oa_count": stats.get("oa_count", 0),
                "intl_collab_count": stats.get("intl_collab_count", 0),
                "period_start": years[0],
                "period_end": years[1],
                "fetched_at": now,
            }
            # Topics missing from the local taxonomy (not yet synced) would
            # violate the foreign key: skipped until the next taxonomy sync.
            for topic_id, stats in per_topic.items()
            if topic_id in known and stats.get("works_count")
        ]
        await session.execute(delete(PeerTopicCount).where(PeerTopicCount.openalex_institution_id == openalex_id))
        # asyncpg caps a statement at 32 767 bind parameters (10 per row).
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

    axis_weights = {k: v for k, v in profile.axis_weights.items() if k in ("impact_scientifique", "specificite_disciplinaire")}
    impact_sub_weights = profile.sub_indicator_weights.get("impact_scientifique", {})

    base = {
        "min_publications": min_publications,
        "period_start": years[0] if years else None,
        "period_end": years[1] if years else None,
        "group_size": len(set(members) - {own_ror}),
        "axis_weights": axis_weights,
        "items": [],
    }
    if not years or not own_ror:
        return {**base, "own_cache_populated": False, "peer_cache_populated": False, "institutions_with_data": 0}

    ror_ids = list({*members, own_ror})
    rows = (await session.execute(
        select(PeerTopicCount).where(
            PeerTopicCount.ror_id.in_(ror_ids),
            PeerTopicCount.period_start == years[0],
            PeerTopicCount.period_end == years[1],
            PeerTopicCount.top10_count.is_not(None),
        )
    )).scalars().all()

    stats: dict[str, dict[str, PeerTopicCount]] = {}  # ror → topic → row
    totals: dict[str, int] = {}
    for row in rows:
        stats.setdefault(row.ror_id, {})[row.topic_id] = row
        totals[row.ror_id] = totals.get(row.ror_id, 0) + row.works_count
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

    candidate_topics = [tid for tid, r in own_stats.items() if r.works_count >= min_publications]
    topics = {
        t.id: t for t in (await session.execute(
            select(Topic).where(Topic.id.in_(candidate_topics))
        )).scalars().all()
    } if candidate_topics else {}

    items = []
    for topic_id in candidate_topics:
        compared = {
            ror: by_topic[topic_id] for ror, by_topic in stats.items()
            if topic_id in by_topic and by_topic[topic_id].works_count >= min_publications and totals.get(ror)
        }
        values = {ror: _topic_values(row, totals[ror]) for ror, row in compared.items()}
        columns = {key: [v[key] for v in values.values()] for key in next(iter(values.values()))}
        scores = {}
        for ror, v in values.items():
            impact = _weighted_average(
                {
                    "pp_top_10": percentile_midrank(v["top10_share"], columns["top10_share"]),
                    "pp_oa": percentile_midrank(v["oa_share"], columns["oa_share"]),
                    "pp_int_collab": percentile_midrank(v["intl_share"], columns["intl_share"]),
                },
                impact_sub_weights,
            )
            specialization = percentile_midrank(v["topic_share"], columns["topic_share"])
            scores[ror] = combine_axes(
                {"impact_scientifique": impact, "specificite_disciplinaire": specialization}, axis_weights
            )
        own_score = scores[own_ror]
        others = sorted(((s, ror) for ror, s in scores.items() if ror != own_ror), reverse=True)
        if others and others[0][0] > own_score + 1e-9:
            continue
        runner_up_score, runner_up = others[0] if others else (None, None)
        own = values[own_ror]
        topic = topics.get(topic_id)
        items.append({
            "topic_id": topic_id,
            "topic_name": topic.display_name if topic else topic_id,
            "subfield_name": topic.subfield_name if topic else None,
            "field_name": topic.field_name if topic else None,
            "own_publications": own_stats[topic_id].works_count,
            "own_share_permille": round(own["topic_share"] * 1000, 2),
            "own_top10_pct": round(own["top10_share"] * 100, 1),
            "own_oa_pct": round(own["oa_share"] * 100, 1),
            "own_intl_pct": round(own["intl_share"] * 100, 1),
            "own_score": round(own_score, 1),
            "runner_up_score": round(runner_up_score, 1) if runner_up_score is not None else None,
            "runner_up_name": (names.get(runner_up) or runner_up) if runner_up else None,
            "margin": round(own_score - runner_up_score, 1) if runner_up_score is not None else None,
            "n_compared": len(compared),
        })

    # Clearest leads first; topics where no peer reaches the threshold (no
    # margin) after them, largest first.
    items.sort(key=lambda i: (i["margin"] is None, -(i["margin"] or 0), -i["own_publications"]))
    result["items"] = items
    return result


def _topic_values(row: PeerTopicCount, institution_total: int) -> dict[str, float]:
    n = row.works_count
    return {
        "top10_share": (row.top10_count or 0) / n,
        "oa_share": (row.oa_count or 0) / n,
        "intl_share": (row.intl_collab_count or 0) / n,
        "topic_share": n / institution_total,
    }
