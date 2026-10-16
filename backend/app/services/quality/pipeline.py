"""Nightly qualitative-indicators job (evaluation grid on every synced work).

Steps, each resumable — a crash loses at most the current batch:
  1. refresh the DOAJ and Retraction Watch dumps (weekly);
  2. fetch Crossref / HAL / PubMed records for works never fetched or older
     than QUALITY_SOURCES_TTL_DAYS (batched, see sources.py);
  3. if a vLLM endpoint is configured, assess the peer review of journals
     absent from DOAJ from their website (most-published journals first, at
     most VLLM_MAX_JOURNALS_PER_RUN per run, each journal once);
  4. evaluate every work against the grid (re-run daily: the age criteria
     62-64 depend on the run date), in a worker thread so the API stays
     responsive;
  5. store institution-level aggregates (quality_snapshot), per scope
     "all" / "core".

First run on a large corpus (~10^5 works) is dominated by step 2 — a few
hours, once; later runs only fetch new or stale works.
"""

import asyncio
import logging
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, or_, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.instance_config import InstanceConfig
from app.models.quality import JournalQuality, QualitySnapshot, WorkQuality, WorkQualitySource
from app.models.sync_log import SyncLog
from app.models.works import Work
from app.services.openalex_client import OpenAlexClient
from app.services.quality import grid, llm, sources

logger = logging.getLogger(__name__)

JOB_NAME = "quality_nightly"
RECOMPUTE_JOB_NAME = "quality_recompute"
FETCH_CHUNK = 500
EVAL_CHUNK = 1000
JOURNAL_RECHECK_DAYS = 365
HISTOGRAM_BINS = 20

_running = asyncio.Lock()


def is_running() -> bool:
    return _running.locked()


async def run_quality_sync() -> None:
    if _running.locked():
        logger.info("Quality job already running — skipped")
        return
    async with _running:
        await _run()


async def run_quality_recompute() -> None:
    """Re-evaluate every work from the cached sources only (no dump refresh,
    no fetch, no LLM) — after the grid calibration changed. Weights and
    thresholds both take effect: thresholds change the checkers' verdicts,
    weights the coefficients."""
    if _running.locked():
        logger.info("Quality job already running — recompute skipped")
        return
    async with _running:
        await _run(recompute_only=True)


async def _run(recompute_only: bool = False) -> None:
    async with AsyncSessionLocal() as session:
        config = (await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))).scalar_one_or_none()
        if not config:
            logger.warning("Quality job skipped: instance not yet configured")
            return
        log = SyncLog(job_name=RECOMPUTE_JOB_NAME if recompute_only else JOB_NAME, status="running")
        session.add(log)
        await session.commit()
        log_id = log.id

    try:
        if recompute_only:
            evaluated = await _evaluate_all(sources.doaj_index(), log_id)
            logger.info("Quality recompute done: %d works re-evaluated with the current grid", evaluated)
            await _finish(log_id, "success", evaluated)
            return
        await sources.refresh_dump(sources.DOAJ_CSV_URL, sources.doaj_csv_path(), config.contact_email)
        await sources.refresh_dump(sources.RETRACTION_WATCH_URL, sources.retraction_watch_path(), config.contact_email)
        fetched = await _fetch_sources(config.contact_email, log_id)
        doaj = sources.doaj_index()
        llm_checked = await _assess_journals(config, doaj) if llm.is_enabled() else 0
        evaluated = await _evaluate_all(doaj, log_id)
        await _refresh_own_comparable_counts(config)
        logger.info(
            "Quality job done: %d works fetched, %d journals assessed by LLM, %d works evaluated",
            fetched, llm_checked, evaluated,
        )
        await _finish(log_id, "success", evaluated)
    except Exception as exc:
        logger.exception("Quality job failed")
        await _finish(log_id, "failed", None, str(exc)[:1000])


async def _finish(log_id: int, status: str, processed: int | None, error: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        log = (await session.execute(select(SyncLog).where(SyncLog.id == log_id))).scalar_one()
        log.status = status
        log.finished_at = datetime.now(timezone.utc)
        if processed is not None:
            log.records_processed = processed
        log.error_message = error
        await session.commit()


async def _set_progress(log_id: int, processed: int) -> None:
    async with AsyncSessionLocal() as session:
        log = (await session.execute(select(SyncLog).where(SyncLog.id == log_id))).scalar_one()
        log.records_processed = processed
        await session.commit()


async def _refresh_own_comparable_counts(config: InstanceConfig) -> None:
    """Reference institution's counts for the benchmark quality axis (peers
    are filled from Paramètres du benchmark), refreshed when stale."""
    from app.services.quality.comparable import current_window, ensure_counts
    from app.services.ror import normalize_ror

    async with AsyncSessionLocal() as session:
        years = await current_window(session)
    if not years:
        return
    async with OpenAlexClient(config.openalex_api_key, config.contact_email) as client:
        await ensure_counts(client, config.openalex_institution_id, normalize_ror(config.ror_id), years)


# ── Step 2: per-work sources ────────────────────────────────────────────────

async def _fetch_sources(contact_email: str, log_id: int) -> int:
    stale_before = datetime.now(timezone.utc) - timedelta(days=settings.QUALITY_SOURCES_TTL_DAYS)
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(Work.id, Work.raw_json["doi"].astext, Work.raw_json["ids"]["pmid"].astext)
            .outerjoin(WorkQualitySource, WorkQualitySource.work_id == Work.id)
            .where(or_(WorkQualitySource.work_id.is_(None), WorkQualitySource.fetched_at < stale_before))
            .order_by(Work.id)
        )).all()
    logger.info("Quality sources: %d works to fetch", len(rows))

    done = 0
    async with sources.http_client(contact_email) as client:
        for start in range(0, len(rows), FETCH_CHUNK):
            chunk = rows[start:start + FETCH_CHUNK]
            doi_of = {wid: sources.bare_doi(doi) for wid, doi, _ in chunk}
            pmid_of = {wid: (pmid or "").rsplit("/", 1)[-1] or None for wid, _, pmid in chunk}
            dois = sorted({d for d in doi_of.values() if d})
            pmids = sorted({p for p in pmid_of.values() if p})

            crossref: dict = {}
            hal: dict = {}
            pubmed: dict = {}

            async def crossref_all():
                for i in range(0, len(dois), sources.CROSSREF_BATCH):
                    crossref.update(await sources.fetch_crossref(client, dois[i:i + sources.CROSSREF_BATCH], contact_email))

            async def hal_all():
                for i in range(0, len(dois), sources.HAL_BATCH):
                    hal.update(await sources.fetch_hal(client, dois[i:i + sources.HAL_BATCH]))

            async def pubmed_all():
                for i in range(0, len(pmids), sources.PUBMED_BATCH):
                    pubmed.update(await sources.fetch_pubmed(client, pmids[i:i + sources.PUBMED_BATCH]))
                    await asyncio.sleep(0.4)  # E-utilities: 3 req/s without API key

            await asyncio.gather(crossref_all(), hal_all(), pubmed_all())

            now = datetime.now(timezone.utc)
            values = [
                {
                    "work_id": wid,
                    "crossref": crossref.get(doi_of[wid]) if doi_of[wid] else None,
                    "hal": hal.get(doi_of[wid]) if doi_of[wid] else None,
                    "pubmed": pubmed.get(pmid_of[wid]) if pmid_of[wid] else None,
                    "fetched_at": now,
                }
                for wid, _, _ in chunk
            ]
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(WorkQualitySource).values(values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["work_id"],
                    set_={c: stmt.excluded[c] for c in ("crossref", "hal", "pubmed", "fetched_at")},
                )
                await session.execute(stmt)
                await session.commit()
            done += len(chunk)
            await _set_progress(log_id, done)
            logger.info("Quality sources: %d/%d works fetched", done, len(rows))
    return done


# ── Step 3: journals outside DOAJ, read by the small LLM ────────────────────

async def _assess_journals(config: InstanceConfig, doaj: dict) -> int:
    source = Work.raw_json["primary_location"]["source"]
    async with AsyncSessionLocal() as session:
        journal_rows = (await session.execute(
            select(source["id"].astext, source["display_name"].astext, source["issn"], func.count())
            .where(source["type"].astext == "journal")
            # Ordinal GROUP BY: the JSON-path expressions carry bind parameters,
            # which Postgres would not match between SELECT and GROUP BY.
            .group_by(text("1"), text("2"), text("3"))
            .order_by(func.count().desc())
        )).all()
        recent = datetime.now(timezone.utc) - timedelta(days=JOURNAL_RECHECK_DAYS)
        already = set((await session.execute(
            select(JournalQuality.source_id).where(JournalQuality.checked_at >= recent)
        )).scalars().all())

    todo: dict[str, str] = {}
    for sid, name, issns, _count in journal_rows:
        if not sid or sid in already or sid in todo:
            continue
        if any((i or "").upper() in doaj for i in issns or []):
            continue  # peer review already answered by DOAJ
        todo[sid] = name or sid
        if len(todo) >= settings.VLLM_MAX_JOURNALS_PER_RUN:
            break
    if not todo:
        return 0

    homepages: dict[str, str | None] = {}
    ids = list(todo)
    async with OpenAlexClient(config.openalex_api_key, config.contact_email) as oa_client:
        for i in range(0, len(ids), 50):
            chunk = [s.rsplit("/", 1)[-1] for s in ids[i:i + 50]]
            data = await oa_client.get_with_retry(
                "/sources",
                params={"filter": f"openalex:{'|'.join(chunk)}", "select": "id,homepage_url", "per-page": 50},
            )
            for src in data.get("results", []):
                homepages[src["id"]] = src.get("homepage_url")

    checked = 0
    async with sources.http_client(config.contact_email) as client:
        for sid, name in todo.items():
            url = homepages.get(sid)
            result = await llm.assess_peer_review(client, name, url) if url else None
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(JournalQuality).values(
                    source_id=sid, display_name=name, homepage_url=url, llm_result=result,
                    checked_at=datetime.now(timezone.utc),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["source_id"],
                    set_={c: stmt.excluded[c] for c in ("display_name", "homepage_url", "llm_result", "checked_at")},
                )
                await session.execute(stmt)
                await session.commit()
            checked += 1
    logger.info("Quality LLM: %d journals assessed", checked)
    return checked


# ── Steps 4-5: evaluation and aggregates ────────────────────────────────────

class _Aggregate:
    """Distribution of the grid *coefficient* (extrinsic factors), not of
    score_final: score_final = score_base × coefficient, and every points
    criterion feeding score_base (27-29, 43-51, 61) needs the full text or an
    LLM reading of it — out of reach of the bulk pipeline, so score_base is
    always 0 here."""

    def __init__(self) -> None:
        self.n_works = 0
        self.n_errors = 0
        self.scores: list[float] = []
        self.criteria: dict[str, Counter] = defaultdict(Counter)

    def add(self, answers: dict[str, str], score: dict) -> None:
        self.n_works += 1
        for cid, code in answers.items():
            self.criteria[cid][code] += 1
        if score["coefficient"] is None:
            self.n_errors += 1
        else:
            self.scores.append(score["coefficient"])

    def to_dict(self) -> dict:
        scores = sorted(self.scores)
        summary = None
        if scores:
            # Bins span [0, p99] so a handful of extreme coefficients don't
            # flatten the histogram; the last bin is open-ended.
            upper = scores[min(len(scores) - 1, int(0.99 * len(scores)))] or scores[-1] or 1.0
            width = upper / HISTOGRAM_BINS or 1.0
            counts = [0] * HISTOGRAM_BINS
            for s in scores:
                counts[min(HISTOGRAM_BINS - 1, max(0, int(s / width)))] += 1
            summary = {
                "mean": round(statistics.fmean(scores), 2),
                "median": round(statistics.median(scores), 2),
                "p10": round(scores[int(0.1 * (len(scores) - 1))], 2),
                "p90": round(scores[int(0.9 * (len(scores) - 1))], 2),
                "min": round(scores[0], 2),
                "max": round(scores[-1], 2),
                "histogram": [
                    {"start": round(i * width, 2), "end": round((i + 1) * width, 2), "count": c, "open_ended": i == HISTOGRAM_BINS - 1}
                    for i, c in enumerate(counts)
                ],
            }
        return {
            "n_works": self.n_works,
            "n_scored": len(self.scores),
            "n_errors": self.n_errors,
            "coefficient": summary,
            "criteria": {cid: dict(c) for cid, c in self.criteria.items()},
        }


def _evaluate_chunk(rows, doaj, journal_llm, rw_index, today) -> list[tuple[str, bool, dict, dict]]:
    out = []
    for wid, raw, is_core, crossref, hal, pubmed in rows:
        oa_work = raw or {}
        source_id = (((oa_work.get("primary_location") or {}).get("source")) or {}).get("id")
        try:
            results = grid.evaluate_work(
                oa_work, crossref, hal, pubmed,
                sources.doaj_result_for(oa_work, doaj), journal_llm.get(source_id), rw_index, today,
            )
        except Exception as exc:  # one malformed record must not sink the whole chunk
            logger.warning("Quality evaluation failed for %s: %s", wid, exc)
            out.append((wid, bool(is_core), {}, {
                "score_base": None, "coefficient": None, "score_final": None,
                "error": f"{type(exc).__name__}: {exc}"[:500],
            }))
            continue
        answers = grid.encode_answers(results)
        out.append((wid, bool(is_core), answers, grid.score_answers(answers)))
    return out


async def _evaluate_all(doaj: dict, log_id: int) -> int:
    rw_index = sources.retraction_watch_index()
    async with AsyncSessionLocal() as session:
        journal_llm = {
            sid: result for sid, result in (await session.execute(
                select(JournalQuality.source_id, JournalQuality.llm_result).where(JournalQuality.llm_result.isnot(None))
            )).all()
        }
        found = (await session.execute(
            select(
                func.count(WorkQualitySource.crossref),
                func.count().filter(WorkQualitySource.hal["response"]["numFound"].as_integer() > 0),
                func.count(WorkQualitySource.pubmed),
            )
        )).one()

    today = date.today()
    aggregates = {"all": _Aggregate(), "core": _Aggregate()}
    last_id = ""
    evaluated = 0
    while True:
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(
                select(
                    Work.id, Work.raw_json, Work.is_core_publication,
                    WorkQualitySource.crossref, WorkQualitySource.hal, WorkQualitySource.pubmed,
                )
                .outerjoin(WorkQualitySource, WorkQualitySource.work_id == Work.id)
                .where(Work.id > last_id)
                .order_by(Work.id)
                .limit(EVAL_CHUNK)
            )).all()
        if not rows:
            break
        last_id = rows[-1][0]
        evaluated_rows = await asyncio.to_thread(_evaluate_chunk, rows, doaj, journal_llm, rw_index, today)

        now = datetime.now(timezone.utc)
        values = []
        for wid, is_core, answers, score in evaluated_rows:
            aggregates["all"].add(answers, score)
            if is_core:
                aggregates["core"].add(answers, score)
            values.append({"work_id": wid, "answers": answers, **score, "computed_at": now})
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(WorkQuality).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["work_id"],
                set_={c: stmt.excluded[c] for c in ("answers", "score_base", "coefficient", "score_final", "error", "computed_at")},
            )
            await session.execute(stmt)
            await session.commit()
        evaluated += len(rows)
        await _set_progress(log_id, evaluated)

    criteria = grid.load_criteria()
    context = {
        "grid_file": grid.grid_label(),
        "n_criteria_grid": len(criteria),
        "sources": {
            "crossref_records": found[0],
            "hal_deposits": found[1],
            "pubmed_records": found[2],
            "doaj_dump_date": _iso(sources.dump_date(sources.doaj_csv_path())),
            "retraction_watch_dump_date": _iso(sources.dump_date(sources.retraction_watch_path())),
            "llm_journals": len(journal_llm),
            "llm_model": settings.VLLM_MODEL if llm.is_enabled() else None,
        },
        "run_date": today.isoformat(),
    }
    async with AsyncSessionLocal() as session:
        for scope, agg in aggregates.items():
            stmt = pg_insert(QualitySnapshot).values(
                scope=scope, data={**agg.to_dict(), **context}, computed_at=datetime.now(timezone.utc)
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["scope"], set_={"data": stmt.excluded.data, "computed_at": stmt.excluded.computed_at}
            )
            await session.execute(stmt)
        # Works pruned from the corpus are removed by ON DELETE CASCADE.
        await session.commit()
    return evaluated


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
