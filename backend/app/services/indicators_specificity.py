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
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.peers import PeerGroupMember, PeerTopicCount
from app.models.works import WorkTopic, Topic

logger = logging.getLogger(__name__)

SIGNATURE_THRESHOLD = 1.5  # [Défaut — modifiable]

# A field is considered "significant" in the generalist framing below this
# share of the institution's total publications. [Défaut — modifiable]
BROAD_FIELD_SHARE_THRESHOLD = 0.05

# Cumulative share of top fields used to define "concentration" in the
# specialised/moderate framing. [Défaut — modifiable]
CONCENTRATION_TARGET = 0.8

# OpenAlex's topic taxonomy has a fixed 26-field second level — used only as
# a fallback when the local `topics` table (populated by _sync_topics_taxonomy)
# hasn't been synced yet, so the explanation sentence still reads sensibly.
FALLBACK_TOTAL_FIELDS = 26


async def get_specificity_indicators(
    session: AsyncSession,
    peer_group_id: int,
) -> dict:
    """Return disciplinary specificity indicators for the configured institution."""

    # ── Thematic profile: full Domain > Field > Subfield > Topic hierarchy,
    #    grouped at topic granularity so the treemap can drill down without a
    #    second round-trip. Bounded by the number of *distinct* topics this
    #    institution has actually published in (typically a few hundred at
    #    most), not the full ~4 500-topic OpenAlex taxonomy. ────────────────
    profile_result = await session.execute(
        select(
            Topic.domain_id,
            Topic.domain_name,
            Topic.field_id,
            Topic.field_name,
            Topic.subfield_id,
            Topic.subfield_name,
            Topic.id.label("topic_id"),
            Topic.display_name.label("topic_name"),
            func.count(WorkTopic.work_id).label("count"),
        )
        .join(WorkTopic, WorkTopic.topic_id == Topic.id)
        .group_by(
            Topic.domain_id, Topic.domain_name,
            Topic.field_id, Topic.field_name,
            Topic.subfield_id, Topic.subfield_name,
            Topic.id, Topic.display_name,
        )
    )
    topic_rows = profile_result.all()
    total_works = sum(r.count for r in topic_rows)
    topic_name_map = {r.topic_id: (r.topic_name or r.topic_id) for r in topic_rows}

    # Build the nested Domain > Field > Subfield > Topic tree. Recharts'
    # <Treemap> computes each node's size by summing `dataKey` recursively
    # from the leaves, so every level shares the same "value" key (see the
    # bugfix note in git history — a domain-only "total" key left every leaf
    # at size 0 and collapsed the whole map into one rectangle).
    domain_map: dict[str, dict] = {}
    field_counts: dict[str, int] = {}  # field_id -> count, for the Herfindahl index below
    for row in topic_rows:
        domain_key = row.domain_name or "Inconnu"
        field_key = row.field_name or "Inconnu"
        subfield_key = row.subfield_name or "Inconnu"

        domain_node = domain_map.setdefault(
            domain_key,
            {"id": row.domain_id or domain_key, "name": domain_key, "value": 0, "children": {}},
        )
        domain_node["value"] += row.count

        field_node = domain_node["children"].setdefault(
            field_key,
            {"id": row.field_id or field_key, "name": field_key, "value": 0, "children": {}},
        )
        field_node["value"] += row.count

        subfield_node = field_node["children"].setdefault(
            subfield_key,
            {"id": row.subfield_id or subfield_key, "name": subfield_key, "value": 0, "children": {}},
        )
        subfield_node["value"] += row.count
        subfield_node["children"][row.topic_id] = {
            "id": row.topic_id,
            "name": row.topic_name or row.topic_id,
            "value": row.count,
        }

        if row.field_id:
            field_counts[row.field_id] = field_counts.get(row.field_id, 0) + row.count

    thematic_profile = [_flatten_children(node) for node in domain_map.values()]

    # ── Herfindahl index at field level ───────────────────────────────────
    field_total = sum(field_counts.values())

    herfindahl = 0.0
    if field_total > 0:
        herfindahl = sum((c / field_total) ** 2 for c in field_counts.values())

    total_fields_available_result = await session.execute(
        select(func.count(func.distinct(Topic.field_id))).where(Topic.field_id.is_not(None))
    )
    total_fields_available = total_fields_available_result.scalar_one() or FALLBACK_TOTAL_FIELDS

    herfindahl_label, herfindahl_explanation = _specialisation_explanation(
        herfindahl, field_counts, field_total, total_fields_available
    )

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

    # Compute peer total to convert counts to shares. avg()/sum() over an
    # Integer column come back from Postgres as numeric/bigint, decoded by
    # asyncpg as Decimal/int respectively — cast both to float up front so
    # the division below doesn't mix Decimal with the float that `int / int`
    # produces in Python (TypeError: unsupported operand type(s) for /).
    peer_grand_total = float(sum(r.total_count for r in peer_topic_rows))
    peer_avg_shares: dict[str, float] = {}
    if peer_grand_total > 0:
        # Normalise each topic's average count relative to the grand total
        peer_avg_shares = {
            r.topic_id: float(r.avg_count) / (peer_grand_total / len(peer_ror_ids))
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
                "topic_name": topic_name_map.get(tid, tid),
                "own_publication_count": own_topic_counts.get(tid, 0),
                # Per-mille rather than % — at signature-topic scale, % values
                # round to a handful of "0.x%" entries that are hard to compare.
                "own_share_permille": round(own_share * 1000, 2),
                "peer_avg_share_permille": round(peer_share * 1000, 2),
                "ratio": round(own_share / peer_share, 2),
            })

    signature_topics.sort(key=lambda x: x["ratio"], reverse=True)

    return {
        "thematic_profile": thematic_profile,
        "herfindahl": {
            "value": round(herfindahl, 4),
            "label": herfindahl_label,
            "explanation": herfindahl_explanation,
            "description": (
                "Indice de Herfindahl calculé au niveau 'field' (niveau 2 de la "
                "hiérarchie Topics OpenAlex). H proche de 0 = production diffuse ; "
                "H proche de 1 = forte spécialisation. Basé sur le volume de "
                "publications, non pondéré par l'impact."
            ),
        },
        "topics_signature": {
            "items": signature_topics[:10],  # limit to the 10 most specific
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


def _flatten_children(node: dict) -> dict:
    """Recursively turn the {name: node} children dicts built while grouping
    into sorted (by value desc) lists, as expected by the frontend treemap."""
    children = node.get("children")
    if not children:
        return {"id": node["id"], "name": node["name"], "value": node["value"]}
    flattened = sorted(
        (_flatten_children(child) for child in children.values()),
        key=lambda c: c["value"],
        reverse=True,
    )
    return {"id": node["id"], "name": node["name"], "value": node["value"], "children": flattened}


def _specialisation_explanation(
    herfindahl: float,
    field_counts: dict[str, int],
    field_total: int,
    total_fields_available: int,
) -> tuple[str, str]:
    """Pick a badge label + a one-sentence, numbers-backed explanation.

    "Peu/moyennement/très spécialisé" alone doesn't tell a reader what the
    number means — this computes the two concrete framings requested (how
    many fields cross a "significant share" bar, vs. how few fields it takes
    to account for most of the output) and picks whichever framing matches
    the computed Herfindahl bucket.
    """
    if field_total == 0:
        return "non déterminé", "Aucune publication classifiée par Topic OpenAlex."

    shares_desc = sorted((c / field_total for c in field_counts.values()), reverse=True)

    broad_count = sum(1 for s in shares_desc if s >= BROAD_FIELD_SHARE_THRESHOLD)

    cumulative = 0.0
    concentration_k = 0
    for s in shares_desc:
        cumulative += s
        concentration_k += 1
        if cumulative >= CONCENTRATION_TARGET:
            break
    concentration_share = round(cumulative * 100, 1)

    if herfindahl < 0.1:
        label = "généraliste"
        explanation = (
            f"Établissement généraliste : {broad_count} fields OpenAlex sur "
            f"{total_fields_available} comptent chacun au moins "
            f"{round(BROAD_FIELD_SHARE_THRESHOLD * 100)} % des publications."
        )
    elif herfindahl < 0.3:
        label = "modérément spécialisé"
        explanation = (
            f"Établissement modérément spécialisé : les {concentration_k} fields "
            f"principaux représentent {concentration_share} % des publications "
            f"(sur {total_fields_available} fields OpenAlex)."
        )
    else:
        label = "très spécialisé"
        if concentration_k == 1:
            explanation = (
                f"Établissement très spécialisé : 1 field représente à lui seul "
                f"{concentration_share} % des publications."
            )
        else:
            explanation = (
                f"Établissement très spécialisé : {concentration_k} fields "
                f"représentent à eux seuls {concentration_share} % des publications."
            )

    return label, explanation
