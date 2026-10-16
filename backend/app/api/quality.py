"""Qualitative indicators (evaluation grid) — see app/services/quality/."""

import asyncio
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.config import settings
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.models.quality import (
    JournalQuality, QualityGridOverride, QualitySnapshot, WorkQuality, WorkQualitySource,
)
from app.models.works import Work
from app.services.quality import grid, llm, pipeline, sources
from app.services.quality.comparable import COMPARABLE_FILTERS, quality_axis
from grille.score_engine import classify_role

router = APIRouter(prefix="/quality", tags=["quality"])
logger = logging.getLogger(__name__)


def _criterion_stats(counts: dict, n_works: int) -> dict:
    yes, no, undetermined = counts.get("O", 0), counts.get("N", 0), counts.get("I", 0)
    decided = yes + no
    return {
        "yes": yes,
        "no": no,
        "undetermined": undetermined,
        # Share of "Oui" among works where the criterion could be decided.
        "share_yes": round(100.0 * yes / decided, 1) if decided else None,
        # Share of the corpus for which a source answered at all.
        "coverage": round(100.0 * (decided + undetermined) / n_works, 1) if n_works else None,
    }


@router.get("/summary")
async def quality_summary(
    core_only: bool = Query(default=False),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    snapshot = (await session.execute(
        select(QualitySnapshot).where(QualitySnapshot.scope == ("core" if core_only else "all"))
    )).scalar_one_or_none()
    n_corpus = (await session.execute(
        select(func.count()).select_from(Work).where(*([Work.is_core_publication.is_(True)] if core_only else []))
    )).scalar_one()
    if snapshot is None:
        return {"available": False, "running": pipeline.is_running(), "core_only": core_only, "n_corpus": n_corpus}

    data = snapshot.data
    n_works = data["n_works"]
    criteria_counts: dict = data.get("criteria", {})
    categories: dict[str, dict[str, list]] = {}
    for meta in grid.criteria_metadata():
        counts = criteria_counts.get(meta["id"])
        if not counts:
            continue
        categories.setdefault(meta["category"], {}).setdefault(meta["subcategory"], []).append(
            {**meta, **_criterion_stats(counts, n_works)}
        )

    return {
        "available": True,
        "running": pipeline.is_running(),
        "core_only": core_only,
        "computed_at": snapshot.computed_at,
        "run_date": data.get("run_date"),
        "n_corpus": n_corpus,
        "n_works": n_works,
        "n_scored": data["n_scored"],
        "n_errors": data["n_errors"],
        "coefficient": data["coefficient"],
        "grid_file": data.get("grid_file"),
        "n_criteria_grid": data.get("n_criteria_grid"),
        "n_criteria_reached": len(criteria_counts),
        "sources": data.get("sources", {}),
        "categories": [
            {"name": cat, "subcategories": [{"name": sub, "criteria": rows} for sub, rows in subs.items()]}
            for cat, subs in categories.items()
        ],
    }


@router.get("/works")
async def quality_works(
    core_only: bool = Query(default=False),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    filters = [WorkQuality.coefficient.isnot(None)]
    if core_only:
        filters.append(Work.is_core_publication.is_(True))
    # Ranked on the coefficient — see pipeline._Aggregate for why score_final
    # (always 0 without full-text criteria) is not a usable ranking.
    score_order = WorkQuality.coefficient.asc() if order == "asc" else WorkQuality.coefficient.desc()
    rows = (await session.execute(
        select(Work.id, Work.title, Work.publication_year, Work.raw_json["doi"].astext, WorkQuality.coefficient)
        .join(WorkQuality, WorkQuality.work_id == Work.id)
        .where(*filters)
        .order_by(score_order, Work.id)
        .limit(limit)
        .offset(offset)
    )).all()
    total = (await session.execute(
        select(func.count()).select_from(WorkQuality).join(Work, Work.id == WorkQuality.work_id).where(*filters)
    )).scalar_one()
    return {
        "total": total,
        "works": [
            {"id": wid, "title": title, "publication_year": year, "doi": doi, "coefficient": round(coef, 3)}
            for wid, title, year, doi, coef in rows
        ],
    }


@router.get("/work")
async def quality_work_detail(
    id: str = Query(..., description="OpenAlex work id, e.g. https://openalex.org/W123"),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """One work's answers with their evidence, rebuilt from the cached sources
    (evidence is not stored per work — see models/quality.py)."""
    row = (await session.execute(
        select(Work, WorkQualitySource, WorkQuality)
        .outerjoin(WorkQualitySource, WorkQualitySource.work_id == Work.id)
        .outerjoin(WorkQuality, WorkQuality.work_id == Work.id)
        .where(Work.id == id)
    )).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Work not found")
    work, src, quality = row
    oa_work = work.raw_json or {}
    source_id = (((oa_work.get("primary_location") or {}).get("source")) or {}).get("id")
    journal_llm = None
    if source_id:
        journal_llm = (await session.execute(
            select(JournalQuality.llm_result).where(JournalQuality.source_id == source_id)
        )).scalar_one_or_none()

    run_date = quality.computed_at.date() if quality else date.today()
    results = grid.evaluate_work(
        oa_work,
        src.crossref if src else None,
        src.hal if src else None,
        src.pubmed if src else None,
        sources.doaj_result_for(oa_work, sources.doaj_index()),
        journal_llm,
        sources.retraction_watch_index(),
        run_date,
    )
    answers = grid.encode_answers(results)
    meta = {m["id"]: m for m in grid.criteria_metadata()}
    criteria = [
        {
            **meta[cid],
            "verdict": r.verdict,
            "confidence": r.confidence,
            "evidence": r.evidence,
        }
        for cid, r in results.items() if cid in meta and r.verdict is not None
    ]
    criteria.sort(key=lambda c: [int(p) for p in c["id"].split(".")])
    return {
        "id": work.id,
        "title": work.title,
        "doi": oa_work.get("doi"),
        "publication_year": work.publication_year,
        "type": work.type,
        "source": (((oa_work.get("primary_location") or {}).get("source")) or {}).get("display_name"),
        "score": grid.score_answers(answers),
        "contributions": grid.score_detail(answers),
        "criteria": criteria,
    }


@router.get("/llm-status")
async def quality_llm_status(config: InstanceConfig = Depends(get_config)) -> dict:
    return await llm.check_connection()


# ── Grid calibration ("Paramètres d'évaluation qualitative") ────────────────

class GridOverrideIn(BaseModel):
    weight: float | None = None
    parameters: dict[str, float] | None = None


class GridUpdate(BaseModel):
    # Full replacement of the instance calibration: criteria absent from this
    # dict revert to the default grid.
    overrides: dict[str, GridOverrideIn]


async def _grid_payload(session: AsyncSession) -> dict:
    from grille.parameters import parameter_units, parse_parameters

    defaults = grid.load_default_criteria()
    effective = grid.load_criteria()
    snapshot = (await session.execute(
        select(QualitySnapshot).where(QualitySnapshot.scope == "all")
    )).scalar_one_or_none()
    automated = set((snapshot.data.get("criteria") or {}) if snapshot else {})
    updated_at = (await session.execute(select(func.max(QualityGridOverride.updated_at)))).scalar_one_or_none()

    criteria = []
    for meta in grid.criteria_metadata():
        cid = meta["id"]
        field = grid.WEIGHT_FIELDS.get(meta["role"])
        default_params = parse_parameters(defaults[cid].get("parametre"))
        current_params = parse_parameters(effective[cid].get("parametre"))
        units = parameter_units(defaults[cid].get("parametre"))
        criteria.append({
            **meta,
            "modulates": (defaults[cid].get("modulateur_de") or "").strip() or None,
            "weight": float(effective[cid][field]) if field else None,
            "default_weight": float(defaults[cid][field]) if field else None,
            "parameters": [
                {"name": name, "value": current_params.get(name, value), "default": value, "unit": units.get(name, "")}
                for name, value in default_params.items()
            ],
            "automated": cid in automated,
            "comparable": cid in COMPARABLE_FILTERS,
        })
    return {
        "has_overrides": grid.has_overrides(),
        "updated_at": updated_at,
        "running": pipeline.is_running(),
        "default_grid_file": grid.GRID_FILE.name,
        "criteria": criteria,
    }


@router.get("/grid")
async def get_grid(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await _grid_payload(session)


async def _save_overrides(session: AsyncSession, overrides: dict[str, dict]) -> None:
    if pipeline.is_running():
        raise HTTPException(
            status_code=409,
            detail="Un calcul des indicateurs qualitatifs est en cours : réessayez une fois celui-ci terminé.",
        )
    try:
        grid.set_overrides(overrides, settings.QUALITY_DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Grille invalide : {exc}")
    await session.execute(delete(QualityGridOverride))
    now = datetime.now(timezone.utc)
    for cid, values in overrides.items():
        session.add(QualityGridOverride(criterion_id=cid, values=values, updated_at=now))
    await session.commit()
    asyncio.create_task(pipeline.run_quality_recompute())


@router.put("/grid")
async def update_grid(
    body: GridUpdate,
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Save the instance calibration and re-evaluate every work in the
    background from cached sources (no API call). Values equal to the default
    grid are dropped, so the stored overrides are exactly the differences."""
    from grille.parameters import parse_parameters

    defaults = grid.load_default_criteria()
    overrides: dict[str, dict] = {}
    for cid, item in body.overrides.items():
        if cid not in defaults:
            raise HTTPException(status_code=400, detail=f"Critère inconnu : {cid}")
        entry: dict = {}
        field = grid.WEIGHT_FIELDS.get(classify_role(defaults[cid]))
        if item.weight is not None:
            if not field:
                raise HTTPException(status_code=400, detail=f"Critère {cid} : aucun poids modifiable.")
            if item.weight < 0:
                raise HTTPException(status_code=400, detail=f"Critère {cid} : poids négatif interdit.")
            if abs(item.weight - float(defaults[cid][field])) > 1e-9:
                entry["weight"] = item.weight
        if item.parameters:
            default_params = parse_parameters(defaults[cid].get("parametre"))
            changed = {
                name: value for name, value in item.parameters.items()
                if name in default_params and abs(value - default_params[name]) > 1e-9
            }
            if changed:
                entry["parameters"] = changed
        if entry:
            overrides[cid] = entry
    await _save_overrides(session, overrides)
    return await _grid_payload(session)


@router.delete("/grid")
async def reset_grid(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Back to the vendored default calibration (and re-evaluate)."""
    await _save_overrides(session, {})
    return await _grid_payload(session)


async def load_grid_overrides() -> None:
    """Apply the stored calibration at startup (falls back to the default grid,
    with a warning, if it no longer validates — e.g. after re-vendoring)."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(QualityGridOverride))).scalars().all()
    overrides = {r.criterion_id: r.values for r in rows}
    try:
        grid.set_overrides(overrides, settings.QUALITY_DATA_DIR)
    except ValueError as exc:
        logger.warning("Stored grid calibration rejected, using the default grid: %s", exc)


# ── Benchmark quality axis (dashboard card) ──────────────────────────────────

@router.get("/benchmark")
async def quality_benchmark(
    peer_group_id: int = Query(...),
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reference institution on the peer-comparable quality axis."""
    from app.models.peers import PeerGroupMember
    from app.services.ror import normalize_ror

    own_ror = normalize_ror(config.ror_id)
    members = (await session.execute(
        select(PeerGroupMember.ror_id).where(PeerGroupMember.peer_group_id == peer_group_id)
    )).scalars().all()
    axis = await quality_axis(session, [*members, own_ror] if own_ror else list(members))
    own = axis.get(own_ror) if own_ror else None
    return {
        "available": own is not None,
        "group_size": len(set(members)),
        "institutions_with_data": len(axis),
        "n_criteria": len(COMPARABLE_FILTERS),
        "estimates": own["estimates"] if own else None,
        "percentiles": own["percentiles"] if own else None,
        "global_percentile": own["global_percentile"] if own else None,
    }
