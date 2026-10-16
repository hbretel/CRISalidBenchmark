"""Comparison-group table: every institution in a peer group (+ the reference
institution) side by side, with a "global score" comparable to composite_score.py's
own-institution composite — but computable for every peer using only already-
ingested leiden_snapshot data (no OpenAlex works/topics ingestion for peers).

Impact axis: reuses the exact same weighted-average logic as composite_score.py,
against Leiden-sourced sub-indicator percentiles (headline top-10%/10-cits share,
%OA, %intl collab). citations_brutes_moyennes and h_index_core are OpenAlex-only
and already never contribute to the impact axis today (their percentile is always
None even for the reference institution — see indicators_impact.py) — so this is
not a reduction in fidelity versus the existing own-institution composite.

Specificity axis: the real Herfindahl (indicators_specificity.py) needs OpenAlex
Topic data that only exists for the reference institution. As a peer-comparable
proxy, this computes a *simplified* Herfindahl from each institution's Leiden `p`
(publication count) split across the 5 Leiden macro-domains — a coarser, 5-bucket
taxonomy, but one every institution in leiden_snapshot already has. This is NOT
the same methodology as the OpenAlex-Topic Herfindahl shown in Domaines de
spécialité; the weight profile's `nb_topics_signature` sub-indicator has no
peer-computable equivalent and is dropped (not renormalized into `herfindahl`).
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroupMember
from app.models.profiles import WeightProfile
from app.services.composite_score import _weighted_average, combine_axes
from app.services.quality.comparable import quality_axis
from app.services.indicators_impact import _percentile_rank
from app.services.ror import normalize_ror

logger = logging.getLogger(__name__)

SPECIFICITY_NOTE = (
    "Score de spécificité simplifié : indice de Herfindahl calculé à partir du nombre de "
    "publications (P) par grand domaine Leiden (5 domaines), et non de la taxonomie Topics "
    "OpenAlex utilisée dans la section Domaines de spécialité — nécessaire pour comparer tous "
    "les établissements du groupe sans ingestion OpenAlex supplémentaire pour les pairs. Le "
    "sous-indicateur « nb_topics_signature » du profil de pondération n'a pas d'équivalent "
    "calculable pour les pairs et est ignoré ici (non redistribué sur l'indice de Herfindahl)."
)


async def get_peer_comparison_table(
    session: AsyncSession,
    peer_group_id: int,
    weight_profile_id: int,
    core_only: bool = True,
    field: str = "All sciences",
) -> dict:
    config_result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
    config = config_result.scalar_one_or_none()
    if not config:
        raise ValueError("Instance not configured")
    own_ror = normalize_ror(config.ror_id)

    profile_result = await session.execute(
        select(WeightProfile).where(WeightProfile.id == weight_profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise ValueError(f"WeightProfile {weight_profile_id} not found")
    axis_weights: dict[str, float] = profile.axis_weights
    impact_sub_weights: dict[str, float] = profile.sub_indicator_weights.get("impact_scientifique", {})
    quality_sub_weights: dict[str, float] = profile.sub_indicator_weights.get("qualite", {})

    snapshot_result = await session.execute(select(func.max(LeidenSnapshot.snapshot_year)))
    snapshot_year = snapshot_result.scalar_one_or_none()

    members_result = await session.execute(
        select(PeerGroupMember.ror_id).where(PeerGroupMember.peer_group_id == peer_group_id)
    )
    ror_ids = [r[0] for r in members_result.all()]
    if own_ror and own_ror not in ror_ids:
        ror_ids.append(own_ror)

    headline_column = "pp_top_10" if core_only else "pp_10_cits"

    if not ror_ids or not snapshot_year:
        return {
            "rows": [],
            "snapshot_year": snapshot_year,
            "core_only": core_only,
            "field": field,
            "headline_column": headline_column,
            "specificity_note": SPECIFICITY_NOTE,
        }

    # Impact columns (P, headline, %OA, %collab) follow the dashboard's global
    # Leiden domain filter; the simplified Herfindahl below is by construction a
    # whole-institution measure across the 5 domains and ignores it.
    all_sciences_result = await session.execute(
        select(LeidenSnapshot).where(
            LeidenSnapshot.ror_id.in_(ror_ids),
            LeidenSnapshot.snapshot_year == snapshot_year,
            LeidenSnapshot.field == field,
            LeidenSnapshot.core_pubs_only.is_(core_only),
            LeidenSnapshot.frac_counting.is_(False),
        )
    )
    all_sciences_rows = {r.ror_id: r for r in all_sciences_result.scalars().all()}

    # Domain-level P is independent of the core_only toggle (Herfindahl is a
    # volume-based measure, computed the same way regardless of the citation
    # toggle — matches indicators_specificity.py, which also ignores core_only).
    domain_result = await session.execute(
        select(LeidenSnapshot.ror_id, LeidenSnapshot.p).where(
            LeidenSnapshot.ror_id.in_(ror_ids),
            LeidenSnapshot.snapshot_year == snapshot_year,
            LeidenSnapshot.field != "All sciences",
            LeidenSnapshot.core_pubs_only.is_(False),
            LeidenSnapshot.frac_counting.is_(False),
        )
    )
    domain_p_by_ror: dict[str, list[float]] = {}
    for ror_id, p in domain_result.all():
        if p is None:
            continue
        domain_p_by_ror.setdefault(ror_id, []).append(float(p))

    headline_values = [
        getattr(row, headline_column) for row in all_sciences_rows.values()
        if getattr(row, headline_column) is not None
    ]
    oa_values = [row.pp_oa for row in all_sciences_rows.values() if row.pp_oa is not None]
    collab_values = [row.pp_int_collab for row in all_sciences_rows.values() if row.pp_int_collab is not None]

    # Quality axis: estimated grid coefficient from OpenAlex counts, percentiles
    # among the institutions of this table that have cached counts.
    quality = await quality_axis(session, ror_ids)

    rows = []
    for ror_id in ror_ids:
        snap = all_sciences_rows.get(ror_id)
        headline_raw = getattr(snap, headline_column, None) if snap else None
        oa_raw = snap.pp_oa if snap else None
        collab_raw = snap.pp_int_collab if snap else None

        impact_percentiles = {}
        if headline_raw is not None:
            impact_percentiles["impact_normalise_leiden"] = _percentile_rank(headline_raw, headline_values)
        if oa_raw is not None:
            impact_percentiles["oa_pct"] = _percentile_rank(oa_raw, oa_values)
        if collab_raw is not None:
            impact_percentiles["collab_intl_pct"] = _percentile_rank(collab_raw, collab_values)
        impact_score = _weighted_average(impact_percentiles, impact_sub_weights)

        domain_ps = domain_p_by_ror.get(ror_id, [])
        domain_total = sum(domain_ps)
        herfindahl_simplified = (
            sum((p / domain_total) ** 2 for p in domain_ps) if domain_total > 0 else None
        )
        specificity_score = (
            _weighted_average({"herfindahl": herfindahl_simplified * 100}, {"herfindahl": 1.0})
            if herfindahl_simplified is not None else 0.0
        )

        axis_scores = {"impact_scientifique": impact_score, "specificite_disciplinaire": specificity_score}
        institution_quality = quality.get(ror_id)
        if institution_quality:
            axis_scores["qualite"] = _weighted_average(institution_quality["percentiles"], quality_sub_weights)
        composite = combine_axes(axis_scores, axis_weights)

        rows.append({
            "ror_id": ror_id,
            "name": snap.university_name if snap else None,
            "country_code": snap.country_code if snap else None,
            "is_own": ror_id == own_ror,
            "p_total": float(snap.p) if snap and snap.p is not None else None,
            "headline_value": round(headline_raw * 100, 2) if headline_raw is not None else None,
            "headline_percentile": impact_percentiles.get("impact_normalise_leiden"),
            "mncs": (round(snap.mncs, 2) if (snap and core_only and snap.mncs is not None) else None),
            "oa_pct": round(oa_raw * 100, 2) if oa_raw is not None else None,
            "collab_pct": round(collab_raw * 100, 2) if collab_raw is not None else None,
            "herfindahl_simplified": (
                round(herfindahl_simplified, 4) if herfindahl_simplified is not None else None
            ),
            "impact_axis_score": round(impact_score, 1),
            "specificity_axis_score": round(specificity_score, 1),
            "quality_coefficient": (
                round(institution_quality["estimates"]["global"], 3) if institution_quality else None
            ),
            "quality_axis_score": round(axis_scores["qualite"], 1) if "qualite" in axis_scores else None,
            "composite_score": round(composite, 1),
        })

    rows.sort(key=lambda r: r["composite_score"], reverse=True)

    return {
        "rows": rows,
        "snapshot_year": snapshot_year,
        "core_only": core_only,
        "field": field,
        "headline_column": headline_column,
        "specificity_note": SPECIFICITY_NOTE,
    }
