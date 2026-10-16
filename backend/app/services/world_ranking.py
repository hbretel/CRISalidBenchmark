"""Worldwide view ("Monde entier" tab) — Leiden Ranking Open Edition only.

Mirrors the Leiden Ranking itself: every ranked university, per main field and
"core publications" toggle, with its indicators as published by CWTS — no
recomputation (field-normalised citation indicators would be far too costly to
rebuild) and, as in Leiden, no composite score. The reference institution gets
its rank and percentile on each indicator among the universities with at least
instance_config.min_publications publications on the selected field.

Indicators depend on the toggle, as in the Leiden files: the pp_top_* family
and MNCS only exist on core-publication rows; pp_*_cits and MCS are the
non-normalised counterparts on all-publication rows.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.services.quality.comparable import percentile_midrank
from app.services.ror import normalize_ror

LEIDEN_FIELDS = {
    "All sciences",
    "Biomedical and health sciences",
    "Life and earth sciences",
    "Mathematics and computer science",
    "Physical sciences and engineering",
    "Social sciences and humanities",
}

# (column, is a 0–1 proportion shown as %)
CORE_INDICATORS = [
    ("pp_top_1", True), ("pp_top_10", True), ("pp_top_50", True), ("mncs", False),
    ("pp_oa", True), ("pp_int_collab", True),
]
ALL_PUBLICATIONS_INDICATORS = [
    ("pp_10_cits", True), ("pp_50_cits", True), ("mcs", False), ("pp_oa", True), ("pp_int_collab", True),
]


async def get_world_ranking(session: AsyncSession, field: str, core_only: bool) -> dict:
    if field not in LEIDEN_FIELDS:
        raise ValueError(f"field must be one of {sorted(LEIDEN_FIELDS)}")
    config = (await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))).scalar_one()
    own_ror = normalize_ror(config.ror_id)
    min_publications = config.min_publications
    indicators = CORE_INDICATORS if core_only else ALL_PUBLICATIONS_INDICATORS
    keys = ["p", *(col for col, _ in indicators)]

    snapshot_year = (await session.execute(select(func.max(LeidenSnapshot.snapshot_year)))).scalar_one_or_none()
    base = {
        "field": field,
        "core_only": core_only,
        "snapshot_year": snapshot_year,
        "period": None,
        "min_publications": min_publications,
        "indicators": [col for col, _ in indicators],
        "rows": [],
        "own": None,
    }
    if not snapshot_year:
        return base

    snaps = (await session.execute(
        select(LeidenSnapshot).where(
            LeidenSnapshot.snapshot_year == snapshot_year,
            LeidenSnapshot.field == field,
            LeidenSnapshot.core_pubs_only.is_(core_only),
            LeidenSnapshot.frac_counting.is_(False),
        )
    )).scalars().all()

    rows = []
    for snap in snaps:
        p = float(snap.p) if snap.p is not None else None
        row = {
            "ror_id": snap.ror_id,
            "name": snap.university_name,
            "country_code": snap.country_code,
            "is_own": snap.ror_id == own_ror,
            "compared": p is not None and p >= min_publications,
            "p": round(p, 1) if p is not None else None,
        }
        for col, proportion in indicators:
            value = getattr(snap, col)
            row[col] = None if value is None else round(value * 100, 2) if proportion else round(value, 3)
        rows.append(row)
        base["period"] = base["period"] or snap.period

    compared = [r for r in rows if r["compared"]]
    own_row = next((r for r in rows if r["is_own"]), None)
    own = None
    if own_row:
        own = {"compared": own_row["compared"], "n_compared": len(compared), "indicators": {}}
        for key in keys:
            value = own_row[key]
            column = [r[key] for r in compared if r[key] is not None]
            ranked = own_row["compared"] and value is not None
            own["indicators"][key] = {
                "value": value,
                "rank": 1 + sum(1 for v in column if v > value) if ranked else None,
                "percentile": percentile_midrank(value, column) if ranked else None,
                "n": len(column),
            }

    rows.sort(key=lambda r: -(r["p"] or 0))
    return {**base, "rows": rows, "own": own}
