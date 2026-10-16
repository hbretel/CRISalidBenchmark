"""Thematic profile of the reference institution (treemap of the
"Groupes de comparaison" tab): its own OpenAlex Domain > Field > Subfield >
Topic hierarchy, full corpus (not filtered on is_core_publication: the core
definition favours international English-language journals and would
under-represent SSH or applied-research profiles). Descriptive, not an
indicator — the specialization rate is computed for every institution in
services/group_benchmark.py, the topics signature in services/topics_signature.py.
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.works import WorkTopic, Topic

logger = logging.getLogger(__name__)


async def get_thematic_profile(session: AsyncSession) -> dict:
    """Full Domain > Field > Subfield > Topic hierarchy of the reference
    institution, grouped at topic granularity so the treemap can drill down
    without a second round-trip. Bounded by the number of *distinct* topics
    this institution has actually published in (typically a few hundred at
    most), not the full ~4 500-topic OpenAlex taxonomy."""
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

    # Build the nested Domain > Field > Subfield > Topic tree. Recharts'
    # <Treemap> computes each node's size by summing `dataKey` recursively
    # from the leaves, so every level shares the same "value" key (see the
    # bugfix note in git history — a domain-only "total" key left every leaf
    # at size 0 and collapsed the whole map into one rectangle).
    domain_map: dict[str, dict] = {}
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

    return {
        "thematic_profile": [_flatten_children(node) for node in domain_map.values()],
        "total_works_analysed": total_works,
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
