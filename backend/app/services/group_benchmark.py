"""Comparison-group benchmark ("Groupes de comparaison" tab) — OpenAlex only.

Every institution of the peer group, plus the reference institution, is
described by the same cached OpenAlex counts (services/quality/comparable.py,
current Leiden window), on one scope at a time: all domains, or one of the 4
OpenAlex domains (the counterpart of Leiden's main fields — no Leiden ↔
OpenAlex mapping needed).

Indicators (all shares of publications, the Leiden indicators that counts can
reproduce — no mean/total citations, no confidence intervals):
  - impact: PP(top 1 %), PP(top 10 %) (citation_normalized_percentile), share
    with FWCI ≥ 1, PP(≥ 10 citations), share cited, PP(open access),
    PP(international collaboration), PP(industry collaboration);
  - specialization: share of the institution's domain-classified publications
    in the selected domain (not defined on "all domains");
  - quality: estimated grid coefficients and P / PP top 50 / 25 / 10 % in
    quality (impact criteria excluded).

Only institutions with at least instance_config.min_publications publications
on the scope are compared: the others are listed with their values but no
percentile, rank or score. Percentiles (mid-rank) are taken among the compared
institutions; the global score aggregates them with the weight profile
(composite_score.score_breakdown).
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroupMember
from app.models.profiles import WeightProfile
from app.services.composite_score import component, quality_components, score_breakdown
from app.services.quality.comparable import (
    DOMAIN_KEY,
    IMPACT_CRITERIA,
    TOTAL_KEY,
    active_categories,
    cached_counts_by_ror,
    category_weights,
    counts_for,
    criteria_terms,
    current_window,
    percentile_midrank,
    quality_scores,
)
from app.services.ror import normalize_ror

logger = logging.getLogger(__name__)

OPENALEX_DOMAINS = {"1": "Life Sciences", "2": "Social Sciences", "3": "Physical Sciences", "4": "Health Sciences"}


async def institution_names(session: AsyncSession, ror_ids: list[str]) -> dict[str, tuple[str | None, str | None]]:
    """{ror: (name, country)} from the latest Leiden snapshot (peer groups are
    built from the Leiden universe)."""
    if not ror_ids:
        return {}
    latest = select(func.max(LeidenSnapshot.snapshot_year)).scalar_subquery()
    rows = (await session.execute(
        select(LeidenSnapshot.ror_id, LeidenSnapshot.university_name, LeidenSnapshot.country_code).where(
            LeidenSnapshot.ror_id.in_(ror_ids),
            LeidenSnapshot.snapshot_year == latest,
            LeidenSnapshot.field == "All sciences",
        )
    )).all()
    return {ror: (name, country) for ror, name, country in rows}


def specialization_rate(counts: dict, domain: str) -> float | None:
    """Share of the domain-classified publications falling in `domain`."""
    by_domain = counts.get(DOMAIN_KEY) or {}
    classified = sum(d.get(TOTAL_KEY, 0) for d in by_domain.values())
    if classified <= 0:
        return None
    return by_domain.get(domain, {}).get(TOTAL_KEY, 0) / classified


async def get_group_benchmark(
    session: AsyncSession,
    peer_group_id: int,
    weight_profile_id: int,
    domain: str | None = None,
) -> dict:
    if domain is not None and domain not in OPENALEX_DOMAINS:
        raise ValueError(f"domain must be one of {sorted(OPENALEX_DOMAINS)}")
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
    ror_ids = list(dict.fromkeys([*members, *([own_ror] if own_ror else [])]))
    years = await current_window(session)
    all_counts = await cached_counts_by_ror(session, ror_ids, years)
    names = await institution_names(session, ror_ids)

    weights = await category_weights(session)
    terms = criteria_terms()
    sub_weights = {**profile.sub_indicator_weights, "qualite": weights}
    meta = {
        "domain": domain,
        "period_start": years[0] if years else None,
        "period_end": years[1] if years else None,
        "min_publications": min_publications,
        "group_size": len(set(members) - {own_ror}),
        "institutions_with_data": len(all_counts),
        "specialization_applicable": domain is not None,
        "axis_weights": profile.axis_weights,
        "sub_weights": sub_weights,
        "category_weights": weights,
        "quality_active_categories": sorted(active_categories(terms)),
    }

    # Values on the selected scope, for every institution with cached counts.
    scoped = {ror: counts_for(c, domain) for ror, c in all_counts.items()}
    values: dict[str, dict] = {}
    for ror, c in scoped.items():
        p = int(c.get(TOTAL_KEY, 0))
        values[ror] = {
            "p": p,
            "impact": {key: (100.0 * c.get(cid, 0) / p if p else None) for key, cid in IMPACT_CRITERIA.items()},
            "specialization": (
                100.0 * rate if domain is not None and (rate := specialization_rate(all_counts[ror], domain)) is not None
                else None
            ),
        }
    compared = [ror for ror, v in values.items() if v["p"] >= min_publications]
    quality = quality_scores({ror: scoped[ror] for ror in compared}, terms, weights)

    def pct(ror: str, value: float | None, column: list[float]) -> float | None:
        return percentile_midrank(value, column) if ror in compared and value is not None else None

    impact_columns = {
        key: [values[r]["impact"][key] for r in compared if values[r]["impact"][key] is not None]
        for key in IMPACT_CRITERIA
    }
    specialization_column = [values[r]["specialization"] for r in compared if values[r]["specialization"] is not None]

    rows = []
    for ror in ror_ids:
        name, country = names.get(ror, (None, None))
        v = values.get(ror)
        row = {
            "ror_id": ror,
            "name": name,
            "country_code": country,
            "is_own": ror == own_ror,
            "has_data": v is not None,
            "compared": ror in compared,
            "p": v["p"] if v else None,
            "impact": {k: (round(x, 2) if x is not None else None) for k, x in v["impact"].items()} if v else {},
            "impact_percentiles": {},
            "specialization_rate": round(v["specialization"], 2) if v and v["specialization"] is not None else None,
            "specialization_percentile": None,
            "quality": quality.get(ror),
            "composite_score": None,
            "rank": None,
            "breakdown": [],
        }
        if ror in compared:
            impact = [
                component(key, row["impact"][key], pct(ror, v["impact"][key], impact_columns[key]), "%")
                for key in IMPACT_CRITERIA
            ]
            specificity = [component(
                "taux_specialisation", row["specialization_rate"],
                pct(ror, v["specialization"], specialization_column), "%",
            )] if domain is not None else []
            breakdown = score_breakdown(
                {
                    "impact_scientifique": impact,
                    "specificite_disciplinaire": specificity,
                    "qualite": quality_components(quality.get(ror)),
                },
                profile.axis_weights,
                sub_weights,
            )
            row["impact_percentiles"] = {c["key"]: c["percentile"] for c in impact}
            row["specialization_percentile"] = specificity[0]["percentile"] if specificity else None
            row["composite_score"] = breakdown["composite_score"]
            row["breakdown"] = breakdown["axes"]
        rows.append(row)

    ranked = sorted((r for r in rows if r["composite_score"] is not None), key=lambda r: -r["composite_score"])
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, -(r["p"] or 0)))
    return {**meta, "institutions_compared": len(compared), "rows": rows}
