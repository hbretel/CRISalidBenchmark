"""Composite benchmark score calculation.

Two-level aggregation:
  1. Each sub-indicator is converted to a percentile rank within the peer group (0–100).
  2. Sub-indicator percentiles are weighted within each axis → axis score (0–100).
  3. Axis scores are weighted → composite score (0–100).

Recalculated entirely on-demand from data in the DB — no scheduled job. Takes a
weight_profile_id and a peer_group_id directly (no persisted "view" object —
the frontend picks both independently via the profile/group selectors).
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.peers import PeerGroupMember
from app.models.profiles import WeightProfile
from app.services.quality.comparable import quality_axis
from app.services.ror import normalize_ror
from app.services.indicators_impact import get_impact_indicators
from app.services.indicators_specificity import get_specificity_indicators

logger = logging.getLogger(__name__)


async def calculate_composite(
    session: AsyncSession,
    weight_profile_id: int,
    peer_group_id: int,
) -> dict:
    profile_result = await session.execute(
        select(WeightProfile).where(WeightProfile.id == weight_profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise ValueError(f"WeightProfile {weight_profile_id} not found")

    axis_weights: dict[str, float] = profile.axis_weights
    sub_weights: dict[str, dict[str, float]] = profile.sub_indicator_weights

    # ── Impact scientifique ───────────────────────────────────────────────
    impact_data = await get_impact_indicators(session, peer_group_id)
    impact_percentiles = {
        k: v["percentile"]
        for k, v in impact_data["indicators"].items()
        if v["percentile"] is not None
    }
    impact_sub_weights = sub_weights.get("impact_scientifique", {})
    impact_score = _weighted_average(impact_percentiles, impact_sub_weights)

    # ── Spécificité disciplinaire ─────────────────────────────────────────
    specificity_data = await get_specificity_indicators(session, peer_group_id)
    nb_signature = len(specificity_data["topics_signature"]["items"])
    specificity_values = {
        "herfindahl": specificity_data["herfindahl"]["value"] * 100,  # scale to 0–100
        "nb_topics_signature": min(nb_signature, 100),  # cap raw count for percentile
    }
    specificity_sub_weights = sub_weights.get("specificite_disciplinaire", {})
    # For specificity, these are absolute values, not pre-computed percentiles —
    # use as-is scaled to 0–100 (herfindahl already ×100; nb_topics capped at 100)
    specificity_score = _weighted_average(specificity_values, specificity_sub_weights)

    axis_scores = {
        "impact_scientifique": impact_score,
        "specificite_disciplinaire": specificity_score,
    }

    # ── Qualité (evaluation grid, peer-comparable criteria) ───────────────
    # Percentiles of the estimated quality coefficients within the peer group
    # (services/quality/comparable.py). Unavailable until the peer cache has
    # been filled — the axis is then left out and the others renormalized,
    # rather than counted as 0.
    config = (await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))).scalar_one()
    own_ror = normalize_ror(config.ror_id)
    member_rors = (await session.execute(
        select(PeerGroupMember.ror_id).where(PeerGroupMember.peer_group_id == peer_group_id)
    )).scalars().all()
    quality = await quality_axis(session, [*member_rors, own_ror] if own_ror else list(member_rors))
    own_quality = quality.get(own_ror) if own_ror else None
    if own_quality:
        axis_scores["qualite"] = _weighted_average(own_quality["percentiles"], sub_weights.get("qualite", {}))

    composite = combine_axes(axis_scores, axis_weights)

    return {
        "weight_profile_id": weight_profile_id,
        "peer_group_id": peer_group_id,
        "composite_score": round(composite, 1),
        "axis_scores": {k: round(v, 1) for k, v in axis_scores.items()},
        "axis_weights": axis_weights,
        "quality_available": own_quality is not None,
        "sub_weights": sub_weights,
    }


def combine_axes(axis_scores: dict[str, float], axis_weights: dict[str, float]) -> float:
    """Weighted sum of the axis scores, renormalized over the axes that have a
    score (an axis without data is excluded, not counted as 0)."""
    present = {axis: w for axis, w in axis_weights.items() if axis in axis_scores}
    total = sum(present.values())
    if total <= 0:
        return 0.0
    return sum(axis_scores[axis] * w for axis, w in present.items()) / total


def _weighted_average(values: dict[str, float], weights: dict[str, float]) -> float:
    if not weights or not values:
        return 0.0
    total_weight = 0.0
    total = 0.0
    for key, weight in weights.items():
        if key in values and values[key] is not None:
            total += values[key] * weight
            total_weight += weight
    return total / total_weight if total_weight > 0 else 0.0
