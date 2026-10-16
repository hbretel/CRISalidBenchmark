"""Pure-function tests for the benchmark scoring (no database needed)."""

import itertools

import pytest

from app.services.composite_score import component, score_breakdown
from app.services.quality import comparable as q


def test_breakdown_renormalizes_missing_axis_and_components():
    result = score_breakdown(
        {
            "impact_scientifique": [
                component("impact_normalise_leiden", 12.0, 80.0, "%"),
                component("oa_pct", 60.0, 40.0, "%"),
                component("citations_brutes_moyennes", 5.0, None),  # no percentile: left out
            ],
            "specificite_disciplinaire": [],  # "Tous les domaines": not applicable
            "qualite": [component("qualite_ex_ante", 1.2, 100.0, "×")],
        },
        {"impact_scientifique": 0.5, "specificite_disciplinaire": 0.25, "qualite": 0.25},
        {
            "impact_scientifique": {"impact_normalise_leiden": 0.5, "oa_pct": 0.25, "citations_brutes_moyennes": 0.25},
            "qualite": {"qualite_ex_ante": 1.0},
        },
    )
    axes = {a["axis"]: a for a in result["axes"]}
    # (80 × 0.5 + 40 × 0.25) / 0.75
    assert axes["impact_scientifique"]["score"] == pytest.approx(66.7, abs=0.05)
    assert axes["specificite_disciplinaire"]["applicable"] is False
    assert axes["specificite_disciplinaire"]["applied_weight"] is None
    # Remaining axis weights 0.5 / 0.25 renormalized to 2/3 / 1/3.
    assert axes["impact_scientifique"]["applied_weight"] == pytest.approx(2 / 3, abs=1e-4)
    assert result["composite_score"] == pytest.approx((200 / 3) * 2 / 3 + 100 / 3, abs=0.05)
    assert sum(a["contribution"] or 0 for a in result["axes"]) == pytest.approx(result["composite_score"], abs=0.1)


def _terms():
    return [
        {"id": "a", "role": "coefficient", "category": "qualite_ex_ante", "negated": False, "weight": 2.0},
        {"id": "b", "role": "coefficient", "category": "qualite_intrinseque", "negated": False, "weight": 0.5},
        {"id": "c", "role": "coefficient", "category": "qualite_ex_post", "negated": True, "weight": 1.5},
    ]


def test_log_distribution_matches_enumeration():
    terms = _terms()
    counts = {q.TOTAL_KEY: 100, "a": 30, "b": 10, "c": 60}
    weights = q.DEFAULT_CATEGORY_WEIGHTS
    offset, dist = q.log_distribution(counts, terms, weights)
    assert dist.sum() == pytest.approx(1.0)
    expected: dict[int, float] = {}
    for combo in itertools.product([0, 1], repeat=len(terms)):
        prob, k = 1.0, 0
        for on, term in zip(combo, terms):
            share = q._term_share(counts, term, 100)
            prob *= share if on else 1 - share
            k += round(3 * weights[term["category"]] * q._term_log(term) / q._LOG_STEP) if on else 0
        expected[k] = expected.get(k, 0.0) + prob
    got = {offset + i: p for i, p in enumerate(dist) if p > 0}
    assert got.keys() == expected.keys()
    for k, p in expected.items():
        assert got[k] == pytest.approx(p)


def test_top_shares_pool_to_exact_levels():
    terms = _terms()
    weights = q.DEFAULT_CATEGORY_WEIGHTS
    counts = {
        "x": {q.TOTAL_KEY: 1000, "a": 900, "b": 0, "c": 0},
        "y": {q.TOTAL_KEY: 3000, "a": 100, "b": 300, "c": 2000},
    }
    sizes = {r: c[q.TOTAL_KEY] for r, c in counts.items()}
    tops = q.top_shares({r: q.log_distribution(c, terms, weights) for r, c in counts.items()}, sizes)
    for level in q.TOP_LEVELS:
        pooled = sum(tops[r][level] * sizes[r] for r in counts) / sum(sizes.values())
        assert pooled == pytest.approx(level / 100)
    # "x" has the better profile: over-represented in every top.
    assert all(tops["x"][level] > level / 100 for level in q.TOP_LEVELS)


def test_equal_weights_reproduce_grid_product():
    terms = _terms()
    counts = {q.TOTAL_KEY: 100, "a": 30, "b": 10, "c": 60}
    est = q.estimate(counts, terms, q.DEFAULT_CATEGORY_WEIGHTS)
    product = est["qualite_ex_ante"] * est["qualite_intrinseque"] * est["qualite_ex_post"]
    assert est["global"] == pytest.approx(product)
    skewed = q.estimate(counts, terms, q.normalize_category_weights({"qualite_ex_ante": 1, "qualite_intrinseque": 0, "qualite_ex_post": 0}))
    assert skewed["global"] == pytest.approx(est["qualite_ex_ante"] ** 3)


def test_impact_criteria_are_not_counted_in_quality():
    term_ids = {t["id"] for t in q.criteria_terms()}
    assert term_ids and not term_ids & q.QUALITY_EXCLUDED


def test_domain_scope_and_specialization():
    from app.services.group_benchmark import specialization_rate

    counts = {
        q.TOTAL_KEY: 110, "4": 60,
        q.DOMAIN_KEY: {"1": {q.TOTAL_KEY: 25, "4": 20}, "3": {q.TOTAL_KEY: 75, "4": 35}},
    }
    assert q.counts_for(counts, None) is counts
    assert q.counts_for(counts, "1")["4"] == 20
    assert q.counts_for(counts, "2") == {q.TOTAL_KEY: 0}
    # 10 works without a primary topic are left out of the denominator.
    assert specialization_rate(counts, "1") == pytest.approx(0.25)


def test_inactive_category_weight_forced_to_zero():
    weights = q.effective_category_weights(
        {"qualite_ex_ante": 0.4, "qualite_intrinseque": 0.5, "qualite_ex_post": 0.1},
        {"qualite_ex_ante", "qualite_intrinseque"},
    )
    assert weights["qualite_ex_post"] == 0
    assert weights["qualite_ex_ante"] == pytest.approx(0.4 / 0.9)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_volume_counts_mirror_impact_criteria():
    # Every impact share has its P-type count (same criterion), plus P itself.
    assert q.VOLUME_COUNTS["p"] == q.TOTAL_KEY
    assert {k: v for k, v in q.VOLUME_COUNTS.items() if k != "p"} == {
        "p" + key[2:]: cid for key, cid in q.IMPACT_CRITERIA.items()
    }


def test_midrank_percentiles_match_single_value_version():
    values = {"a": 1.0, "b": 2.0, "c": 2.0, "d": 5.0, "e": 0.5}
    expected = {k: q.percentile_midrank(v, list(values.values())) for k, v in values.items()}
    assert q.midrank_percentiles(values) == expected
    assert q.midrank_percentiles({"a": 3.0}) == {"a": 50.0}
