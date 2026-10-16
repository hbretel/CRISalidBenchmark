"""Per-institution OpenAlex counts behind the comparison-group benchmark
(services/group_benchmark.py): impact and volume indicators and quality axis.

Only the reference institution's works are ingested. For the benchmark, every
institution (reference included, for a like-for-like comparison) is described
by the number of its publications in the current Leiden window meeting each
evaluation-grid criterion that an OpenAlex filter can count. One query per
criterion, grouped by OpenAlex domain (group_by=primary_topic.domain.id): the
groups give the per-domain counts and meta.count the all-domains count, at the
cost of a plain count. Cached per institution (peer_quality_counts):

    {"_total": n, "<criterion>": n, ..., "by_domain": {"1": {"_total": n, ...}, ...}}

The domain of a work is the domain of its primary topic — one domain per
work, no fractional counting; works without a primary topic only appear in the
all-domains counts.

Criteria that mirror Leiden impact indicators (citations, open access,
collaboration — IMPACT_CRITERIA) are reported as impact indicators of the
benchmark and left out of the quality estimate below, so they are not counted
twice in the global score.

From those shares and the *current* grid weights (instance overrides included),
an estimated quality coefficient is derived per grid category:

    ln(coef) = Σ_c share_c × ln(w_c)                 (coefficient criteria)
             + Σ_m share_m × [ln(1 + (w_t − 1) × f_m) − ln(w_t)]   (modulators m → target t)

i.e. the geometric mean, over the institution's publications, of the grid
coefficient restricted to these criteria, assuming criteria independent and
modulator chains one level deep. It is an approximation of the per-work
coefficient shown in "Qualité des publications" — which uses ~190 criteria
and the real answer combinations — but it is computed identically for every
institution, which is what a percentile within the peer group requires.

Weighting between categories (instance-wide, "Paramètres d'évaluation
qualitative" page, instance_config.quality_category_weights): weights w_k
summing to 1 over the three categories. They set
  - the quality axis score: Σ w_k × percentile_k;
  - the global coefficient: ln(global) = 3 × Σ w_k × ln(coef_k) — equal
    thirds give back the grid's own product of the category coefficients.

Leiden-like indicators (P, P/PP top 50 / 25 / 10 % in quality): under the same
independence assumption, the shares above describe for each institution the
distribution of the (weighted) per-publication log-coefficient — a sum of
independent two-valued terms, computed exactly by convolution on a 1e-3 grid.
The thresholds of the top 50 / 25 / 10 % are taken on the pooled publications
of the institutions compared (comparison group + reference institution,
above the instance's minimum publication count), and
publications exactly at a threshold are counted fractionally, as Leiden does
for citation ties — so the pooled PP(top x %) is exactly x %. Everything is
computed on one scope at a time (all domains, or one OpenAlex domain).
"""

import asyncio
import bisect
import logging
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.quality import PeerQualityCount
from app.services.openalex_client import OpenAlexClient
from app.services.quality import grid
from grille.results import is_complement_wording
from grille.score_engine import classify_role

logger = logging.getLogger(__name__)

# criterion id → OpenAlex works filter (verified against the live API on
# 2026-10-16). Each must select works for which the criterion, worded
# affirmatively, is "Oui".
COMPARABLE_FILTERS: dict[str, str] = {
    "4": "open_access.is_oa:true",
    "4.1": "open_access.oa_status:gold|hybrid",
    "4.1.1": "primary_location.source.is_oa:true,primary_location.source.type:journal",
    "4.2": "open_access.any_repository_has_fulltext:true",
    "4.3": "best_oa_location.license:cc-by|cc-by-sa|cc-by-nc|cc-by-nd|cc-by-nc-sa|cc-by-nc-nd|cc0|public-domain",
    "4.3.1": "best_oa_location.license:cc-by|cc-by-sa|cc0|public-domain",
    "5": "primary_location.source.type:journal",
    "5.2": "primary_location.source.is_core:true",
    "5.9": "primary_location.source.is_in_doaj:true",
    "8": "has_pmid:true",
    "10": "has_doi:true",
    "11": "has_abstract:true",
    "11.2": "has_orcid:true",
    "13": "funders.id:!null",
    "14": "authors_count:>1",
    "14.3": "authorships.institutions.type:company,authorships.institutions.type:education|facility",
    "14.4": "countries_distinct_count:>1",
    "14.5": "authors_count:>100",
    "16": "authorships.institutions.type:education|facility",
    "25": "primary_location.source.type:conference",
    "26": "type:book|book-chapter",
    "26.1": "type:book",
    "30": "is_retracted:true",
    "40": "language:en",
    "46": "referenced_works_count:>0",
    "65": "cited_by_count:>0",
    "69": "cited_by_count:>9",
    "73": "sustainable_development_goals.id:!null",
    "106": "citation_normalized_percentile.is_in_top_10_percent:true",
    "106.1": "citation_normalized_percentile.is_in_top_1_percent:true",
    "107": "fwci:>0.9999",
}
TOTAL_KEY = "_total"
DOMAIN_KEY = "by_domain"

# Benchmark impact indicator → criterion whose share it is (Leiden
# counterparts: PP(top 1 %), PP(top 10 %), ~MNCS > 1, PP(≥ 10 cits),
# share cited, PP(OA), PP(int. collab), PP(industry collab)).
IMPACT_CRITERIA: dict[str, str] = {
    "pp_top_1": "106.1",
    "pp_top_10": "106",
    "pp_fwci_1": "107",
    "pp_10_cits": "69",
    "pp_cited": "65",
    "pp_oa": "4",
    "pp_int_collab": "14.4",
    "pp_industry_collab": "14.3",
}
QUALITY_EXCLUDED = set(IMPACT_CRITERIA.values())

# Benchmark volume indicator → count it reads: the Leiden P-type counterparts
# of the impact indicators (numbers of publications, not shares), in display
# order.
VOLUME_COUNTS: dict[str, str] = {
    "p": TOTAL_KEY,
    "p_fwci_1": "107",
    "p_oa": "4",
    "p_top_1": "106.1",
    "p_cited": "65",
    "p_top_10": "106",
    "p_10_cits": "69",
    "p_int_collab": "14.4",
    "p_industry_collab": "14.3",
}

# Grid category → weight-profile sub-indicator of the "qualite" axis.
CATEGORY_KEYS = {
    "Facteurs extrinsèques ex-ante": "qualite_ex_ante",
    "Facteurs intrinsèques": "qualite_intrinseque",
    "Facteurs extrinsèques ex-post": "qualite_ex_post",
}
SUB_INDICATORS = list(CATEGORY_KEYS.values())
DEFAULT_CATEGORY_WEIGHTS = {key: 1 / len(SUB_INDICATORS) for key in SUB_INDICATORS}
TOP_LEVELS = (50, 25, 10)
_LOG_STEP = 1e-3

CACHE_TTL_DAYS = 90
_CONCURRENCY = 4
_MIN_WEIGHT = 1e-6  # a 0 coefficient (hard exclusion) would make ln() diverge


def _base_filter(openalex_id: str, years: tuple[int, int]) -> str:
    short = openalex_id.rsplit("/", 1)[-1]
    span = "|".join(str(y) for y in range(years[0], years[1] + 1))
    return f"authorships.institutions.lineage:{short},publication_year:{span}"


async def fetch_counts(client: OpenAlexClient, openalex_id: str, years: tuple[int, int]) -> dict:
    base = _base_filter(openalex_id, years)
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def count(extra: str) -> tuple[int, dict[str, int]]:
        async with sem:
            data = await client.get_with_retry(
                "/works",
                params={"filter": f"{base},{extra}" if extra else base, "group_by": "primary_topic.domain.id"},
            )
        by_domain = {
            g["key"].rsplit("/", 1)[-1]: int(g.get("count", 0)) for g in data.get("group_by", []) if g.get("key")
        }
        return int(data.get("meta", {}).get("count", 0)), by_domain

    keys = [TOTAL_KEY, *COMPARABLE_FILTERS]
    results = await asyncio.gather(*(count(COMPARABLE_FILTERS.get(k, "")) for k in keys))
    counts: dict = {key: total for key, (total, _) in zip(keys, results)}
    domains: dict[str, dict[str, int]] = {}
    for key, (_, by_domain) in zip(keys, results):
        for domain, n in by_domain.items():
            domains.setdefault(domain, {})[key] = n
    counts[DOMAIN_KEY] = domains
    return counts


def counts_for(counts: dict, domain: str | None) -> dict:
    """Counts on one OpenAlex domain ("1".."4"), or all domains if None."""
    if domain is None:
        return counts
    return (counts.get(DOMAIN_KEY) or {}).get(domain, {TOTAL_KEY: 0})


async def ensure_counts(
    client: OpenAlexClient, openalex_id: str, ror_id: str | None, years: tuple[int, int], force: bool = False
) -> dict[str, int] | None:
    """Cached counts for one institution, (re)fetched if missing, stale, or for
    another Leiden window. None if OpenAlex could not be queried."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(PeerQualityCount).where(PeerQualityCount.openalex_institution_id == openalex_id)
        )).scalar_one_or_none()
    fresh = (
        row is not None
        and (row.period_start, row.period_end) == years
        and row.fetched_at > datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)
        and set(COMPARABLE_FILTERS) <= set(row.counts)
        and DOMAIN_KEY in row.counts
    )
    if fresh and not force:
        return row.counts
    try:
        counts = await fetch_counts(client, openalex_id, years)
    except Exception as exc:
        logger.warning("Benchmark counts failed for %s: %s", openalex_id, exc)
        return row.counts if row else None
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(PeerQualityCount).values(
            openalex_institution_id=openalex_id, ror_id=ror_id, period_start=years[0], period_end=years[1],
            counts=counts, fetched_at=datetime.now(timezone.utc),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_institution_id"],
            set_={c: stmt.excluded[c] for c in ("ror_id", "period_start", "period_end", "counts", "fetched_at")},
        )
        await session.execute(stmt)
        await session.commit()
    return counts


async def cached_counts_by_ror(session: AsyncSession, ror_ids: list[str], years: tuple[int, int] | None) -> dict[str, dict]:
    if not ror_ids or not years:
        return {}
    rows = (await session.execute(
        select(PeerQualityCount).where(
            PeerQualityCount.ror_id.in_(ror_ids),
            PeerQualityCount.period_start == years[0],
            PeerQualityCount.period_end == years[1],
        )
    )).scalars().all()
    # Rows from before the per-domain breakdown are treated as missing (they
    # are refetched by the next peer-cache fill).
    return {r.ror_id: r.counts for r in rows if DOMAIN_KEY in r.counts}


def criteria_terms() -> list[dict]:
    """The comparable quality criteria (impact ones excluded) with their current
    (effective) grid weight and role, shared by every institution's estimate."""
    criteria = grid.load_criteria()
    terms = []
    for cid in COMPARABLE_FILTERS:
        if cid in QUALITY_EXCLUDED:
            continue
        row = criteria.get(cid)
        if row is None:
            continue
        role = classify_role(row)
        term = {
            "id": cid,
            "role": role,
            "category": CATEGORY_KEYS.get(row.get("categorie") or ""),
            "negated": is_complement_wording(row.get("critere") or ""),
        }
        if role == "coefficient":
            term["weight"] = float(row["poids_coefficient"])
        elif role == "modulateur":
            target = (row.get("modulateur_de") or "").split(";")[0].strip()
            target_row = criteria.get(target)
            if not target_row or classify_role(target_row) != "coefficient":
                continue  # chains / non-coefficient targets: out of the approximation
            term["factor"] = float(row["facteur_modulation"])
            term["target_weight"] = float(target_row["poids_coefficient"])
            term["category"] = CATEGORY_KEYS.get(target_row.get("categorie") or "")
        else:
            continue  # points criteria (score_base) are not part of the coefficient
        if term["category"]:
            terms.append(term)
    return terms


def normalize_category_weights(weights: dict | None) -> dict[str, float]:
    """Instance category weights, defaulting to equal thirds; renormalized to
    sum to 1 (unknown keys ignored)."""
    if not weights:
        return dict(DEFAULT_CATEGORY_WEIGHTS)
    clean = {key: max(float(weights.get(key, 0.0) or 0.0), 0.0) for key in SUB_INDICATORS}
    total = sum(clean.values())
    return {k: v / total for k, v in clean.items()} if total > 0 else dict(DEFAULT_CATEGORY_WEIGHTS)


def _term_log(term: dict) -> float:
    if term["role"] == "coefficient":
        return math.log(max(term["weight"], _MIN_WEIGHT))
    w = max(term["target_weight"], _MIN_WEIGHT)
    return math.log(max(1.0 + (w - 1.0) * term["factor"], _MIN_WEIGHT)) - math.log(w)


def _term_share(counts: dict, term: dict, total: int) -> float:
    share = min(1.0, counts.get(term["id"], 0) / total)
    return 1.0 - share if term["negated"] else share


def estimate(counts: dict, terms: list[dict], weights: dict[str, float] | None = None) -> dict[str, float] | None:
    """Estimated coefficient per sub-indicator, plus "global" (their weighted
    geometric combination, see module docstring)."""
    total = counts.get(TOTAL_KEY) or 0
    if total <= 0:
        return None
    weights = weights or DEFAULT_CATEGORY_WEIGHTS
    logs = {key: 0.0 for key in SUB_INDICATORS}
    for term in terms:
        logs[term["category"]] += _term_share(counts, term, total) * _term_log(term)
    out = {key: math.exp(v) for key, v in logs.items()}
    out["global"] = math.exp(len(SUB_INDICATORS) * sum(weights[k] * v for k, v in logs.items()))
    return out


def log_distribution(counts: dict, terms: list[dict], weights: dict[str, float]) -> tuple[int, np.ndarray]:
    """Distribution of the weighted per-publication log-coefficient when each
    criterion holds independently with its observed share, on a grid of
    _LOG_STEP: (offset, probabilities) — probabilities[i] is the mass of the
    bin offset + i."""
    total = counts.get(TOTAL_KEY) or 0
    offset, dist = 0, np.ones(1)
    if total <= 0:
        return offset, dist
    n = len(SUB_INDICATORS)
    for term in terms:
        step = round(n * weights[term["category"]] * _term_log(term) / _LOG_STEP)
        share = _term_share(counts, term, total)
        if step == 0 or share <= 0.0:
            continue
        if share >= 1.0:
            offset += step
            continue
        nxt = np.zeros(len(dist) + abs(step))
        if step > 0:
            nxt[: len(dist)] += dist * (1.0 - share)
            nxt[step:] += dist * share
        else:
            nxt[-step:] += dist * (1.0 - share)
            nxt[: len(dist)] += dist * share
            offset += step
        dist = nxt
    return offset, dist


def top_shares(distributions: dict[str, tuple[int, np.ndarray]], sizes: dict[str, int]) -> dict[str, dict[int, float]]:
    """{ror: {level: share of its publications in the pooled top level %}}."""
    grand_total = sum(sizes[r] for r in distributions)
    if grand_total <= 0:
        return {}
    lo = min(off for off, _ in distributions.values())
    hi = max(off + len(d) for off, d in distributions.values())
    aligned = {}
    for ror, (off, d) in distributions.items():
        full = np.zeros(hi - lo)
        full[off - lo: off - lo + len(d)] = d
        aligned[ror] = full
    pooled = sum(aligned[r] * (sizes[r] / grand_total) for r in aligned)
    # Mass strictly above each bin, from the highest bin down.
    above = np.concatenate([np.cumsum(pooled[::-1])[::-1][1:], [0.0]])
    out: dict[str, dict[int, float]] = {ror: {} for ror in distributions}
    for level in TOP_LEVELS:
        target = level / 100.0
        # Threshold bin: the highest bin whose inclusion reaches the target.
        candidates = np.nonzero((above < target - 1e-12) & (above + pooled >= target - 1e-12) & (pooled > 0))[0]
        if len(candidates) == 0:
            continue
        k = candidates[-1]
        fraction = (target - above[k]) / pooled[k]
        for ror, full in aligned.items():
            share = full[k + 1:].sum() + fraction * full[k]
            out[ror][level] = float(min(max(share, 0.0), 1.0))
    return out


def percentile_midrank(value: float, values: list[float]) -> float:
    """0-100 rank of value among values (itself included), ties counted half —
    so a criterion every institution shares (e.g. all weights still at 1)
    yields 50 for everyone instead of 0."""
    if not values:
        return 50.0
    below = sum(1 for v in values if v < value - 1e-12)
    equal = sum(1 for v in values if abs(v - value) <= 1e-12)
    return round(100.0 * (below + 0.5 * (equal - 1)) / max(len(values) - 1, 1), 1) if len(values) > 1 else 50.0


def midrank_percentiles(values: dict[str, float]) -> dict[str, float]:
    """percentile_midrank of every value among all of them, in O(n log n)."""
    column = sorted(values.values())
    if len(column) <= 1:
        return {key: 50.0 for key in values}
    out = {}
    for key, value in values.items():
        below = bisect.bisect_left(column, value - 1e-12)
        equal = bisect.bisect_right(column, value + 1e-12) - below
        out[key] = round(100.0 * (below + 0.5 * (equal - 1)) / (len(column) - 1), 1)
    return out


async def current_window(session: AsyncSession) -> tuple[int, int] | None:
    from app.services.openalex_sync import _current_leiden_window
    return await _current_leiden_window(session)


async def category_weights(session: AsyncSession) -> dict[str, float]:
    from app.models.instance_config import InstanceConfig

    stored = (await session.execute(
        select(InstanceConfig.quality_category_weights).where(InstanceConfig.id == 1)
    )).scalar_one_or_none()
    return effective_category_weights(stored, active_categories(criteria_terms()))


def effective_category_weights(weights: dict | None, active: set[str]) -> dict[str, float]:
    """Instance weights with every inactive category (no non-neutral criterion
    outside the impact ones — see active_categories) forced to 0 and the
    others renormalized, for as long as the grid gives it no valid criterion.
    Applies to the axis score and to the global coefficient alike."""
    weights = normalize_category_weights(weights)
    kept = {k: (w if k in active else 0.0) for k, w in weights.items()}
    total = sum(kept.values())
    if total <= 0:
        # Stored weights only on inactive categories: equal weights on the active ones.
        kept = {k: (1.0 if k in active else 0.0) for k in weights}
        total = sum(kept.values())
    return {k: w / total for k, w in kept.items()} if total > 0 else weights


def active_categories(terms: list[dict]) -> set[str]:
    """Categories with at least one non-neutral criterion. Since the impact
    criteria moved out of the quality axis, a category can be left with
    neutral weights only (ex-post, with the default grid): its coefficient is
    1 for everyone, so it is excluded from the axis score rather than giving
    every institution the 50th percentile."""
    return {t["category"] for t in terms if abs(_term_log(t)) > 1e-12}


def quality_scores(
    counts_by_ror: dict[str, dict], terms: list[dict], weights: dict[str, float], with_top: bool = True
) -> dict[str, dict]:
    """{ror: {"estimates": {sub: coef, "global": coef}, "percentiles": {sub: 0-100 | None},
    "axis_score", "top": {"50"|"25"|"10": {"share", "count"}}}} for the
    institutions given (counts already restricted to one scope). Percentiles
    and top-x % thresholds are taken among them only; inactive categories
    (active_categories) get no percentile and their weight is redistributed.
    with_top=False skips the top-x % shares ("top" left empty), which only the
    institution-level view displays."""
    active = active_categories(terms)
    active_weight = sum(weights[k] for k in SUB_INDICATORS if k in active)
    estimates = {ror: est for ror, c in counts_by_ror.items() if (est := estimate(c, terms, weights)) is not None}
    sizes = {ror: int(counts_by_ror[ror][TOTAL_KEY]) for ror in estimates}
    tops = top_shares(
        {ror: log_distribution(counts_by_ror[ror], terms, weights) for ror in estimates}, sizes
    ) if with_top else {}
    ranks = {key: midrank_percentiles({ror: e[key] for ror, e in estimates.items()}) for key in SUB_INDICATORS}
    result = {}
    for ror, est in estimates.items():
        percentiles = {key: ranks[key][ror] if key in active else None for key in SUB_INDICATORS}
        axis_score = (
            sum(weights[k] * percentiles[k] for k in SUB_INDICATORS if k in active) / active_weight
            if active_weight > 0 else None
        )
        result[ror] = {
            "estimates": {k: round(v, 4) for k, v in est.items()},
            "percentiles": percentiles,
            "axis_score": round(axis_score, 1) if axis_score is not None else None,
            "top": {
                str(level): {"share": round(100 * share, 1), "count": round(share * sizes[ror])}
                for level, share in tops.get(ror, {}).items()
            },
        }
    return result
