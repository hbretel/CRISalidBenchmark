"""Composite benchmark score calculation.

Two-level aggregation:
  1. Each sub-indicator is converted to a percentile rank within the peer group (0–100).
  2. Sub-indicator percentiles are weighted within each axis → axis score (0–100).
  3. Axis scores are weighted → composite score (0–100).

Used by the comparison-group benchmark (services/group_benchmark.py) and the
topics signature (services/topics_signature.py).

Missing data never counts as 0: a sub-indicator without a value is left out
of its axis (the other sub-indicators' weights are renormalized), and an axis
without any sub-indicator value is left out of the composite (the other axes'
weights are renormalized). This is what happens to the specificity axis in
"Tous les domaines" mode, and to the quality axis before the peer cache is
filled.

Weights: axis weights and the impact / specificity sub-weights come from the
weight profile; the quality sub-weights (grid categories) are instance-wide
("Paramètres d'évaluation qualitative", see services/quality/comparable.py).

score_breakdown() returns the full calculation (values, percentiles, weights
actually applied, contributions) so the frontend can show how a global score
was obtained.

Recalculated entirely on-demand from data in the DB — no scheduled job.
"""

import logging

from app.services.quality.comparable import SUB_INDICATORS as QUALITY_SUB_INDICATORS

logger = logging.getLogger(__name__)

AXES = ("impact_scientifique", "specificite_disciplinaire", "qualite")


def component(key: str, value: float | None, percentile: float | None, unit: str = "") -> dict:
    return {"key": key, "value": value, "unit": unit, "percentile": percentile}


def quality_components(institution_quality: dict | None) -> list[dict]:
    """Quality-axis components of one institution (quality_scores() entry)."""
    if not institution_quality:
        return [component(key, None, None, "×") for key in QUALITY_SUB_INDICATORS]
    return [
        component(key, institution_quality["estimates"][key], institution_quality["percentiles"][key], "×")
        for key in QUALITY_SUB_INDICATORS
    ]


def score_breakdown(
    components: dict[str, list[dict]],
    axis_weights: dict[str, float],
    sub_weights: dict[str, dict[str, float]],
) -> dict:
    """Composite score and its full derivation.

    components: {axis: [component(...)]} — an axis absent or with an empty
    list is reported as not applicable. Returns {"composite_score", "axes":
    [{"axis", "score", "weight", "applied_weight", "contribution",
    "components": [{..., "weight", "applied_weight"}]}]}.
    """
    axes = []
    for axis in AXES:
        comps = components.get(axis) or []
        weights = sub_weights.get(axis, {})
        present = [c for c in comps if c["percentile"] is not None and weights.get(c["key"], 0) > 0]
        total = sum(weights[c["key"]] for c in present)
        out_comps = []
        for c in comps:
            w = weights.get(c["key"], 0.0)
            in_score = c in present and total > 0
            out_comps.append({**c, "weight": w, "applied_weight": round(w / total, 4) if in_score else None})
        score = sum(c["percentile"] * weights[c["key"]] for c in present) / total if total > 0 else None
        axes.append({
            "axis": axis,
            "applicable": bool(comps),
            "score": round(score, 1) if score is not None else None,
            "weight": axis_weights.get(axis, 0.0),
            "components": out_comps,
        })

    scored = [a for a in axes if a["score"] is not None and a["weight"] > 0]
    total_axis = sum(a["weight"] for a in scored)
    composite = 0.0
    for a in axes:
        if a in scored and total_axis > 0:
            a["applied_weight"] = round(a["weight"] / total_axis, 4)
            a["contribution"] = round(a["score"] * a["weight"] / total_axis, 1)
            composite += a["score"] * a["weight"] / total_axis
        else:
            a["applied_weight"] = None
            a["contribution"] = None
    return {"composite_score": round(composite, 1), "axes": axes}


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
