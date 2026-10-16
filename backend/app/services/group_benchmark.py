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
  - volume: the P-type counterparts of the impact indicators — numbers of
    publications (P, P(FWCI ≥ 1), P(OA), P(top 1 %), …), which favour large
    institutions where the shares do not;
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
    VOLUME_COUNTS,
    active_categories,
    cached_counts_by_ror,
    category_weights,
    counts_for,
    criteria_terms,
    current_window,
    midrank_percentiles,
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
    specialization = {
        ror: (100.0 * rate if (rate := specialization_rate(c, domain)) is not None else None)
        for ror, c in all_counts.items()
    } if domain is not None else None
    scores = score_scope(scoped, specialization, min_publications, profile.axis_weights, sub_weights, terms, weights)

    rows = []
    for ror in ror_ids:
        name, country = names.get(ror, (None, None))
        s = scores.get(ror)
        rows.append({
            "ror_id": ror,
            "name": name,
            "country_code": country,
            "is_own": ror == own_ror,
            "has_data": s is not None,
            "rank": None,
            **(s or {
                "compared": False, "p": None, "impact": {}, "impact_percentiles": {}, "volume": {},
                "volume_percentiles": {}, "specialization_rate": None, "specialization_percentile": None,
                "quality": None, "composite_score": None, "breakdown": [],
            }),
        })

    ranked = sorted((r for r in rows if r["composite_score"] is not None), key=lambda r: -r["composite_score"])
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, -(r["p"] or 0)))
    return {**meta, "institutions_compared": sum(1 for s in scores.values() if s["compared"]), "rows": rows}


def score_scope(
    scoped: dict[str, dict],
    specialization: dict[str, float | None] | None,
    min_publications: int,
    axis_weights: dict[str, float],
    sub_weights: dict[str, dict[str, float]],
    terms: list[dict],
    category_weights: dict[str, float],
    with_quality_top: bool = True,
) -> dict[str, dict]:
    """Indicators, percentiles and global score of every institution on one
    scope — all domains, one OpenAlex domain, or one topic (topics signature,
    services/topics_signature.py): {ror: {"compared", "p", "impact",
    "impact_percentiles", "volume", "volume_percentiles",
    "specialization_rate", "specialization_percentile", "quality",
    "composite_score", "breakdown"}}.

    scoped: {ror: counts restricted to the scope} (comparable.py layout);
    specialization: {ror: specialization rate in %} on the scope, None where
    the axis does not apply (all domains). Only institutions with at least
    min_publications publications on the scope are compared: the others keep
    their values but get no percentile nor score.
    """
    values: dict[str, dict] = {}
    for ror, c in scoped.items():
        p = int(c.get(TOTAL_KEY, 0))
        values[ror] = {
            "p": p,
            "impact": {key: (100.0 * c.get(cid, 0) / p if p else None) for key, cid in IMPACT_CRITERIA.items()},
            "volume": {key: int(c.get(cid, 0)) for key, cid in VOLUME_COUNTS.items()},
            "specialization": specialization.get(ror) if specialization is not None else None,
        }
    compared = [ror for ror, v in values.items() if v["p"] >= min_publications]
    quality = quality_scores({ror: scoped[ror] for ror in compared}, terms, category_weights, with_top=with_quality_top)

    def ranks(get) -> dict[str, float]:
        return midrank_percentiles({r: x for r in compared if (x := get(values[r])) is not None})

    impact_ranks = {key: ranks(lambda v, k=key: v["impact"][k]) for key in IMPACT_CRITERIA}
    volume_ranks = {key: ranks(lambda v, k=key: v["volume"][k]) for key in VOLUME_COUNTS}
    specialization_ranks = ranks(lambda v: v["specialization"])

    out = {}
    for ror, v in values.items():
        entry = {
            "compared": ror in compared,
            "p": v["p"],
            "impact": {k: (round(x, 2) if x is not None else None) for k, x in v["impact"].items()},
            "impact_percentiles": {},
            "volume": dict(v["volume"]),
            "volume_percentiles": {},
            "specialization_rate": round(v["specialization"], 2) if v["specialization"] is not None else None,
            "specialization_percentile": None,
            "quality": quality.get(ror),
            "composite_score": None,
            "breakdown": [],
        }
        if ror in compared:
            impact = [
                component(key, entry["impact"][key], impact_ranks[key].get(ror), "%") for key in IMPACT_CRITERIA
            ]
            volume = [component(key, v["volume"][key], volume_ranks[key].get(ror)) for key in VOLUME_COUNTS]
            specificity = [component(
                "taux_specialisation", entry["specialization_rate"], specialization_ranks.get(ror), "%",
            )] if specialization is not None else []
            breakdown = score_breakdown(
                {
                    "impact_scientifique": impact,
                    "volume_publications": volume,
                    "specificite_disciplinaire": specificity,
                    "qualite": quality_components(quality.get(ror)),
                },
                axis_weights,
                sub_weights,
            )
            entry["impact_percentiles"] = {c["key"]: c["percentile"] for c in impact}
            entry["volume_percentiles"] = {c["key"]: c["percentile"] for c in volume}
            entry["specialization_percentile"] = specificity[0]["percentile"] if specificity else None
            entry["composite_score"] = breakdown["composite_score"]
            entry["breakdown"] = breakdown["axes"]
        out[ror] = entry
    return out
