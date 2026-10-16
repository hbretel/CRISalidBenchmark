"""Peer-comparable quality axis (evaluation grid criteria countable in OpenAlex).

The full grid is evaluated per work, which needs the works themselves — only
ingested for the reference institution. For the benchmark, every institution
(reference included, for a like-for-like comparison) is instead described by
the share of its publications in the current Leiden window meeting each grid
criterion that an OpenAlex filter can count: one `meta.count` query per
criterion, cached per institution (peer_quality_counts).

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
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone

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

# Grid category → weight-profile sub-indicator of the "qualite" axis.
CATEGORY_KEYS = {
    "Facteurs extrinsèques ex-ante": "qualite_ex_ante",
    "Facteurs intrinsèques": "qualite_intrinseque",
    "Facteurs extrinsèques ex-post": "qualite_ex_post",
}
SUB_INDICATORS = list(CATEGORY_KEYS.values())

CACHE_TTL_DAYS = 90
_CONCURRENCY = 4
_MIN_WEIGHT = 1e-6  # a 0 coefficient (hard exclusion) would make ln() diverge


def _base_filter(openalex_id: str, years: tuple[int, int]) -> str:
    short = openalex_id.rsplit("/", 1)[-1]
    span = "|".join(str(y) for y in range(years[0], years[1] + 1))
    return f"authorships.institutions.lineage:{short},publication_year:{span}"


async def fetch_counts(client: OpenAlexClient, openalex_id: str, years: tuple[int, int]) -> dict[str, int]:
    base = _base_filter(openalex_id, years)
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def count(extra: str) -> int:
        async with sem:
            data = await client.get_with_retry(
                "/works", params={"filter": f"{base},{extra}" if extra else base, "per-page": 1, "select": "id"}
            )
            return int(data.get("meta", {}).get("count", 0))

    keys = [TOTAL_KEY, *COMPARABLE_FILTERS]
    values = await asyncio.gather(*(count(COMPARABLE_FILTERS.get(k, "")) for k in keys))
    return dict(zip(keys, values))


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
    )
    if fresh and not force:
        return row.counts
    try:
        counts = await fetch_counts(client, openalex_id, years)
    except Exception as exc:
        logger.warning("Quality counts failed for %s: %s", openalex_id, exc)
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
    return {r.ror_id: r.counts for r in rows}


def criteria_terms() -> list[dict]:
    """The comparable criteria with their current (effective) grid weight and
    role, shared by every institution's estimate."""
    criteria = grid.load_criteria()
    terms = []
    for cid in COMPARABLE_FILTERS:
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


def estimate(counts: dict, terms: list[dict]) -> dict[str, float] | None:
    """Estimated coefficient per sub-indicator, plus "global" (their product)."""
    total = counts.get(TOTAL_KEY) or 0
    if total <= 0:
        return None
    logs = {key: 0.0 for key in SUB_INDICATORS}
    for term in terms:
        share = min(1.0, counts.get(term["id"], 0) / total)
        if term["negated"]:
            share = 1.0 - share
        if term["role"] == "coefficient":
            logs[term["category"]] += share * math.log(max(term["weight"], _MIN_WEIGHT))
        else:
            w = max(term["target_weight"], _MIN_WEIGHT)
            modulated = max(1.0 + (w - 1.0) * term["factor"], _MIN_WEIGHT)
            logs[term["category"]] += share * (math.log(modulated) - math.log(w))
    out = {key: math.exp(v) for key, v in logs.items()}
    out["global"] = math.exp(sum(logs.values()))
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


async def current_window(session: AsyncSession) -> tuple[int, int] | None:
    from app.services.openalex_sync import _current_leiden_window
    return await _current_leiden_window(session)


async def quality_axis(session: AsyncSession, ror_ids: list[str]) -> dict[str, dict]:
    """{ror_id: {"estimates": {sub: coef, "global": coef}, "percentiles": {sub: 0-100}}}
    for the institutions in `ror_ids` that have cached counts for the current
    window. Percentiles are taken among those institutions only. Read-only:
    counts are fetched by the peer-cache fill and the nightly quality job,
    never during a request."""
    years = await current_window(session)
    counts = await cached_counts_by_ror(session, ror_ids, years)
    terms = criteria_terms()
    estimates = {ror: est for ror, c in counts.items() if (est := estimate(c, terms)) is not None}
    result = {}
    for ror, est in estimates.items():
        result[ror] = {
            "estimates": {k: round(v, 4) for k, v in est.items()},
            "percentiles": {
                key: percentile_midrank(est[key], [e[key] for e in estimates.values()]) for key in SUB_INDICATORS
            },
            "global_percentile": percentile_midrank(est["global"], [e["global"] for e in estimates.values()]),
        }
    return result
