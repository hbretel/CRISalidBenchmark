"""Scientific Impact indicator calculations. Spec v1.7.

All OpenAlex-recalculated sub-indicators are filtered on is_core_publication=True
by default (toggle-able). This maintains methodological coherence with Leiden's
pp_top_10, which is also computed on core publications only.

Percentiles are calculated within the selected peer group — not against a global
universe. "80th percentile" means "higher than 80% of peer institutions in the
selected Leiden peer group."

Toggle-dependent headline Leiden indicator (§5.1/§7, non-equivalence warning):
  - core_only=True  -> leiden_snapshot.pp_top_10 (core_pubs_only=True rows).
    % publications in the top 10% most cited, FIELD-NORMALISED by CWTS.
  - core_only=False -> leiden_snapshot.pp_10_cits (core_pubs_only=False rows).
    % publications with at least 10 citations, an ABSOLUTE threshold, NOT
    field-normalised.
  These are NOT the same kind of indicator. Both are exposed under the same
  abstract weight-profile key `impact_normalise_leiden` (see models/profiles.py)
  so a saved weighting stays valid across toggle states, but the API response
  always reports which concrete Leiden column backs the value and flags the
  non-equivalence explicitly for the frontend to surface.

mncs (field-normalised mean citations) is only populated on core_pubs_only=True
rows in leiden_snapshot — it is returned as None when core_only=False, with no
continuous field-normalised substitute available in that mode (mcs, non
field-normalised, could be shown as a raw cross-check but is not surfaced here).
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.peers import PeerGroup, PeerGroupMember
from app.models.works import Work
from app.services.leiden_period import parse_period_years
from app.services.ror import normalize_ror

logger = logging.getLogger(__name__)


def _percentile_rank(value: float, peer_values: list[float]) -> float:
    """0–100 percentile rank of value within peer_values (higher is better)."""
    if not peer_values:
        return 50.0
    below = sum(1 for v in peer_values if v < value)
    return round(100.0 * below / len(peer_values), 1)


async def _compute_h_index(session: AsyncSession, core_only: bool) -> int:
    query = select(Work.cited_by_count).order_by(Work.cited_by_count.desc())
    if core_only:
        query = query.where(Work.is_core_publication.is_(True))
    result = await session.execute(query)
    counts = [row[0] for row in result.all()]
    h = 0
    for i, c in enumerate(counts, start=1):
        if c >= i:
            h = i
        else:
            break
    return h


async def get_impact_indicators(
    session: AsyncSession,
    peer_group_id: int,
    field: str = "All sciences",
    core_only: bool = True,
) -> dict:
    """Return impact sub-indicators for the configured institution + peer percentiles."""

    # ── Load config ──────────────────────────────────────────────────────
    result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
    config = result.scalar_one_or_none()
    if not config:
        raise ValueError("Instance not configured")

    snapshot_result = await session.execute(
        select(func.max(LeidenSnapshot.snapshot_year))
    )
    snapshot_year = snapshot_result.scalar_one_or_none()

    # Works ingestion is restricted to the current Leiden period window (see
    # openalex_sync.py), so the h-index / citation counts below are implicitly
    # scoped to these publication years — surfaced here for the frontend.
    period_result = await session.execute(
        select(LeidenSnapshot.period)
        .where(LeidenSnapshot.snapshot_year == snapshot_year, LeidenSnapshot.period.isnot(None))
        .limit(1)
    )
    period_years = parse_period_years(period_result.scalar_one_or_none())
    period_start, period_end = period_years if period_years else (None, None)

    # ── Own Leiden indicators (row selected by field + core_pubs_only toggle) ──
    own_leiden = None
    own_ror = normalize_ror(config.ror_id)
    if own_ror and snapshot_year:
        leiden_result = await session.execute(
            select(LeidenSnapshot).where(
                LeidenSnapshot.ror_id == own_ror,
                LeidenSnapshot.snapshot_year == snapshot_year,
                LeidenSnapshot.field == field,
                LeidenSnapshot.core_pubs_only.is_(core_only),
                LeidenSnapshot.frac_counting.is_(False),
            )
        )
        own_leiden = leiden_result.scalar_one_or_none()

    # ── Own OpenAlex indicators ───────────────────────────────────────────
    base_query = select(Work)
    if core_only:
        base_query = base_query.where(Work.is_core_publication.is_(True))

    counts_result = await session.execute(
        select(
            func.count().label("total"),
            func.sum(Work.cited_by_count).label("total_citations"),
            func.count().filter(Work.is_oa.is_(True)).label("oa_count"),
            func.count().filter(Work.is_international_collab.is_(True)).label("intl_count"),
        ).where(*(
            [Work.is_core_publication.is_(True)] if core_only else []
        ))
    )
    row = counts_result.one()
    total = row.total or 0
    citations_moyenne = round(row.total_citations / total, 2) if total else 0.0
    oa_pct = round(100.0 * row.oa_count / total, 1) if total else 0.0
    collab_pct = round(100.0 * row.intl_count / total, 1) if total else 0.0
    h_index = await _compute_h_index(session, core_only)

    # ── Peer Leiden values for percentile calculation ─────────────────────
    members_result = await session.execute(
        select(PeerGroupMember.ror_id).where(
            PeerGroupMember.peer_group_id == peer_group_id
        )
    )
    peer_ror_ids = [r[0] for r in members_result.all()]

    peer_leiden: list[LeidenSnapshot] = []
    if peer_ror_ids and snapshot_year:
        peer_result = await session.execute(
            select(LeidenSnapshot).where(
                LeidenSnapshot.ror_id.in_(peer_ror_ids),
                LeidenSnapshot.snapshot_year == snapshot_year,
                LeidenSnapshot.field == field,
                LeidenSnapshot.core_pubs_only.is_(core_only),
                LeidenSnapshot.frac_counting.is_(False),
            )
        )
        peer_leiden = peer_result.scalars().all()

    # ── Headline normalised indicator: toggle-dependent, NOT equivalent across
    #    states — pp_top_10 (core) vs pp_10_cits (all publications). Leiden
    #    stores these as 0-1 proportions; ×100 is applied here for display
    #    (never in the DB, per spec §3.5) — percentile is computed on the
    #    raw 0-1 peer values first, then the own value is scaled for display.
    if core_only:
        headline_column = "pp_top_10"
        raw_value = own_leiden.pp_top_10 if own_leiden else None
        raw_lb = own_leiden.pp_top_10_lb if own_leiden else None
        raw_ub = own_leiden.pp_top_10_ub if own_leiden else None
        peer_headline = [p.pp_top_10 for p in peer_leiden if p.pp_top_10 is not None]
        headline_description = (
            "% publications dans le top 10% le plus cité (normalisé par domaine, "
            "Leiden, publications core, comptage complet)"
        )
    else:
        headline_column = "pp_10_cits"
        raw_value = own_leiden.pp_10_cits if own_leiden else None
        raw_lb = own_leiden.pp_10_cits_lb if own_leiden else None
        raw_ub = own_leiden.pp_10_cits_ub if own_leiden else None
        peer_headline = [p.pp_10_cits for p in peer_leiden if p.pp_10_cits is not None]
        headline_description = (
            "% publications ayant reçu au moins 10 citations (seuil absolu, non "
            "normalisé par domaine — indicateur différent de pp_top_10, affiché "
            "en mode 'toutes les publications' faute d'équivalent normalisé)"
        )

    headline_percentile = _percentile_rank(raw_value, peer_headline) if raw_value is not None else None
    headline_value = round(raw_value * 100, 2) if raw_value is not None else None
    headline_lb = round(raw_lb * 100, 2) if raw_lb is not None else None
    headline_ub = round(raw_ub * 100, 2) if raw_ub is not None else None

    def _round2(v: float | None) -> float | None:
        return round(v, 2) if v is not None else None

    mncs_value = _round2(own_leiden.mncs) if (own_leiden and core_only) else None
    mncs_lb = _round2(own_leiden.mncs_lb) if (own_leiden and core_only) else None
    mncs_ub = _round2(own_leiden.mncs_ub) if (own_leiden and core_only) else None

    peer_pp_int_collab = [p.pp_int_collab for p in peer_leiden if p.pp_int_collab is not None]
    peer_pp_oa = [p.pp_oa for p in peer_leiden if p.pp_oa is not None]

    return {
        "field": field,
        "core_only": core_only,
        "snapshot_year": snapshot_year,
        "period_start": period_start,
        "period_end": period_end,
        "peer_group_size": len(peer_leiden),
        "indicators": {
            "impact_normalise_leiden": {
                "value": headline_value,
                "value_lb": headline_lb,
                "value_ub": headline_ub,
                "percentile": headline_percentile,
                "source": "leiden",
                "leiden_column": headline_column,
                "non_equivalent_across_toggle": True,
                "description": headline_description,
            },
            "mncs": {
                "value": mncs_value,
                "value_lb": mncs_lb,
                "value_ub": mncs_ub,
                "percentile": None,
                "source": "leiden",
                "description": (
                    "Citations moyennes normalisées par domaine (1.0 = moyenne mondiale). "
                    "Disponible uniquement en mode 'publications core' — pas d'équivalent "
                    "normalisé par domaine sur le corpus complet."
                ),
            },
            "citations_brutes_moyennes": {
                "value": citations_moyenne,
                "percentile": None,  # OpenAlex-only; peer data not ingested
                "source": "openalex",
                "description": "Citations moyennes par publication (depuis OpenAlex, non normalisé)",
            },
            "h_index_core": {
                "value": h_index,
                "percentile": None,
                "source": "openalex",
                "description": (
                    f"Indice h sur les publications core, calculé en local sur la période "
                    f"{period_start}–{period_end} (fenêtre du Leiden Ranking en cours)"
                    if period_start and period_end
                    else "Indice h sur les publications core (calculé en local)"
                ),
            },
            "oa_pct": {
                "value": oa_pct,
                "percentile": _percentile_rank(oa_pct, [p * 100 for p in peer_pp_oa]) if peer_pp_oa else None,
                "source": "openalex+leiden",
                "description": "% publications en accès ouvert",
            },
            "collab_intl_pct": {
                "value": collab_pct,
                "percentile": _percentile_rank(collab_pct, [p * 100 for p in peer_pp_int_collab]) if peer_pp_int_collab else None,
                "source": "openalex+leiden",
                "description": "% publications en collaboration internationale",
            },
        },
    }
