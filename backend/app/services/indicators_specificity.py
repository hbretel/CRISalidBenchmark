"""Disciplinary Specificity indicator calculations.

Uses the full corpus (not filtered on is_core_publication) because the core
definition favours international English-language journals and would artificially
under-represent SSH or applied-research profiles.

Herfindahl index (H) is computed at the 'field' level (second level of the
OpenAlex hierarchy, below domain). H ∈ [0, 1]:
  - H close to 0: very diffuse, spread across many fields
  - H ≈ 0.1–0.3: moderate specialisation
  - H close to 1: highly concentrated in one field

Topics signature: topics where the institution's publication share exceeds the
peer-group average by a configurable threshold (default ×1.5). Comparison is
peer-relative via peer_topic_counts (volume-only, not citation-weighted — see §4.5).
"""

import logging
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.peers import PeerGroupMember, PeerTopicCount
from app.models.works import Work, WorkTopic, Topic

logger = logging.getLogger(__name__)

SIGNATURE_THRESHOLD = 1.5  # [Défaut — modifiable]


async def get_specificity_indicators(
    session: AsyncSession,
    peer_group_id: int,
) -> dict:
    """Return disciplinary specificity indicators for the configured institution."""

    # ── Thematic profile: distribution over Topics hierarchy ──────────────
    profile_result = await session.execute(
        select(
            Topic.domain_name,
            Topic.field_name,
            func.count(WorkTopic.work_id).label("count"),
        )
        .join(WorkTopic, WorkTopic.topic_id == Topic.id)
        .group_by(Topic.domain_name, Topic.field_name)
        .order_by(func.count(WorkTopic.work_id).desc())
    )
    profile_rows = profile_result.all()

    # Restructure as nested dict for treemap rendering
    domain_map: dict[str, dict] = {}
    total_works = sum(r.count for r in profile_rows)
    for row in profile_rows:
        domain = row.domain_name or "Inconnu"
        field = row.field_name or "Inconnu"
        if domain not in domain_map:
            domain_map[domain] = {"name": domain, "children": [], "total": 0}
        domain_map[domain]["children"].append({"name": field, "value": row.count})
        domain_map[domain]["total"] += row.count

    thematic_profile = list(domain_map.values())

    # ── Herfindahl index at field level ───────────────────────────────────
    field_result = await session.execute(
        select(Topic.field_id, func.count(WorkTopic.work_id).label("count"))
        .join(WorkTopic, WorkTopic.topic_id == Topic.id)
        .where(Topic.field_id.is_not(None))
        .group_by(Topic.field_id)
    )
    field_counts = {row.field_id: row.count for row in field_result.all()}
    field_total = sum(field_counts.values())

    herfindahl = 0.0
    if field_total > 0:
        herfindahl = sum((c / field_total) ** 2 for c in field_counts.values())

    # ── Topic-level distribution of own institution ───────────────────────
    topic_result = await session.execute(
        select(WorkTopic.topic_id, func.count(WorkTopic.work_id).label("count"))
        .group_by(WorkTopic.topic_id)
    )
    own_topic_counts = {row.topic_id: row.count for row in topic_result.all()}
    own_total = sum(own_topic_counts.values())
    own_shares = (
        {tid: c / own_total for tid, c in own_topic_counts.items()}
        if own_total > 0 else {}
    )

    # ── Peer average topic shares ─────────────────────────────────────────
    members_result = await session.execute(
        select(PeerGroupMember.ror_id).where(
            PeerGroupMember.peer_group_id == peer_group_id
        )
    )
    peer_ror_ids = [r[0] for r in members_result.all()]

    # Get all peer topic counts (only for peers with cached data)
    peer_topic_result = await session.execute(
        select(
            PeerTopicCount.topic_id,
            func.avg(PeerTopicCount.works_count).label("avg_count"),
            func.sum(PeerTopicCount.works_count).label("total_count"),
        )
        .where(PeerTopicCount.ror_id.in_(peer_ror_ids))
        .group_by(PeerTopicCount.topic_id)
    )
    peer_topic_rows = peer_topic_result.all()

    # Compute peer total to convert counts to shares
    peer_grand_total = sum(r.total_count for r in peer_topic_rows)
    peer_avg_shares: dict[str, float] = {}
    if peer_grand_total > 0:
        # Normalise each topic's average count relative to the grand total
        peer_avg_shares = {
            r.topic_id: r.avg_count / (peer_grand_total / len(peer_ror_ids))
            if peer_ror_ids else 0.0
            for r in peer_topic_rows
        }
        # Re-normalise so shares sum to 1
        peer_share_total = sum(peer_avg_shares.values())
        if peer_share_total > 0:
            peer_avg_shares = {k: v / peer_share_total for k, v in peer_avg_shares.items()}

    cache_populated = len(peer_avg_shares) > 0

    # ── Topics signature ──────────────────────────────────────────────────
    signature_topics: list[dict] = []
    for tid, own_share in own_shares.items():
        peer_share = peer_avg_shares.get(tid, 0.0)
        if peer_share > 0 and own_share / peer_share >= SIGNATURE_THRESHOLD:
            signature_topics.append({
                "topic_id": tid,
                "own_share": round(own_share * 100, 2),
                "peer_avg_share": round(peer_share * 100, 2),
                "ratio": round(own_share / peer_share, 2),
            })

    signature_topics.sort(key=lambda x: x["ratio"], reverse=True)

    return {
        "thematic_profile": thematic_profile,
        "herfindahl": {
            "value": round(herfindahl, 4),
            "label": _herfindahl_label(herfindahl),
            "description": (
                "Indice de Herfindahl calculé au niveau 'field' (niveau 2 de la "
                "hiérarchie Topics OpenAlex). H proche de 0 = production diffuse ; "
                "H proche de 1 = forte spécialisation. Basé sur le volume de "
                "publications, non pondéré par l'impact."
            ),
        },
        "topics_signature": {
            "items": signature_topics[:50],  # cap at 50 for UI
            "threshold": SIGNATURE_THRESHOLD,
            "peer_cache_populated": cache_populated,
            "description": (
                f"Topics où la part de l'établissement est ≥ {SIGNATURE_THRESHOLD}× "
                "la part moyenne du groupe de pairs. Comparaison basée sur le volume "
                "(pas l'impact). Triés par ratio décroissant."
            ),
        },
        "total_works_analysed": total_works,
        "peer_group_size": len(peer_ror_ids),
    }


def _herfindahl_label(h: float) -> str:
    if h < 0.1:
        return "peu spécialisé"
    if h < 0.3:
        return "moyennement spécialisé"
    return "très spécialisé"
