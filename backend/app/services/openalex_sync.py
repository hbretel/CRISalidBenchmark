"""Nightly OpenAlex ingestion job.

Ingests publications attributed to the configured institution (and its full
ROR descendant hierarchy, any depth) via the authorships.institutions.lineage
filter, then updates the institution object to refresh lineage_ids.

Publication-year scope: restricted to the current Leiden period (e.g.
2020-2023) rather than the institution's entire history — see
_current_leiden_window(). Leiden's own peer indicators (pp_top_10, mncs, ...)
are computed only on that same window, so ingesting more would both cost far
more (≈5x pages for a typical large university) and be methodologically
mismatched against the very indicators we're comparing against. The `works`
table is pruned to match the window on every sync (handles the window
shifting forward each year when a new Leiden edition is imported).

is_core_publication approximation — §4.1 point 3bis:
  A work is flagged is_core_publication=True when:
    - primary_location.source.is_core is True  (CWTS Core list, ~36 000 sources)
    - type ∈ {article, review, book-chapter}
    - language = 'en'
    - is_retracted = False

  This is an intentional approximation of Leiden's "core publication" definition.
  The official Leiden definition additionally applies criteria not exposed by OpenAlex
  without importing a separate ~3 GB per-work classification file (work.tsv).
  That file is explicitly excluded from the MVP scope; the approximation avoids
  ~3 GB of extra ingestion for an edge case that rarely affects aggregate indicators
  at the institution level. Re-evaluate in v2 if the gap proves material in practice.

is_international_collab:
  True if any authorship affiliation carries a country_code different from the
  configured institution's country. Null country_codes in affiliations are skipped.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.instance_config import InstanceConfig
from app.models.leiden import LeidenSnapshot
from app.models.sync_log import SyncLog
from app.models.works import Work, WorkTopic, Topic
from app.services.openalex_client import OpenAlexClient
from app.services.institution_resolver import compute_effective_lineage
from app.services.leiden_period import parse_period_years

logger = logging.getLogger(__name__)


async def _current_leiden_window(session: AsyncSession) -> tuple[int, int] | None:
    """The (start_year, end_year) of the most recent Leiden snapshot's period.

    None if no Leiden data has been imported yet — the caller then skips
    works ingestion entirely rather than falling back to an unrestricted
    full-history sync (see run_openalex_sync).
    """
    result = await session.execute(
        select(LeidenSnapshot.period)
        .where(LeidenSnapshot.snapshot_year == select(func.max(LeidenSnapshot.snapshot_year)).scalar_subquery())
        .limit(1)
    )
    period = result.scalar_one_or_none()
    return parse_period_years(period)


def _calc_is_core(work: dict) -> bool:
    """Approximate Leiden 'core publication' flag from OpenAlex work fields.

    Dev-time note: verify that primary_location.source.is_core is present inline
    in the /works list response. If not, a batch source-fetch fallback is needed.
    """
    source = (work.get("primary_location") or {}).get("source") or {}
    return (
        source.get("is_core", False) is True
        and work.get("type") in {"article", "review", "book-chapter"}
        and work.get("language") == "en"
        and not work.get("is_retracted", False)
    )


def _calc_is_intl_collab(work: dict, institution_country: str | None) -> bool:
    if not institution_country:
        return False
    for authorship in work.get("authorships", []):
        for inst in authorship.get("institutions", []):
            cc = inst.get("country_code")
            if cc and cc != institution_country:
                return True
    return False


async def _upsert_topics(session: AsyncSession, works_page: list[dict]) -> None:
    """Upsert all topics referenced in this page before upserting works."""
    seen: dict[str, dict] = {}
    for work in works_page:
        for topic_entry in work.get("topics", []):
            t = topic_entry.get("topic") or topic_entry  # handle both shapes
            tid = t.get("id")
            if tid and tid not in seen:
                seen[tid] = t

        pt = work.get("primary_topic") or {}
        if pt.get("id") and pt["id"] not in seen:
            seen[pt["id"]] = pt

    if not seen:
        return

    rows = [
        {
            "id": t.get("id"),
            "display_name": t.get("display_name", ""),
            "subfield_id": (t.get("subfield") or {}).get("id"),
            "subfield_name": (t.get("subfield") or {}).get("display_name"),
            "field_id": (t.get("field") or {}).get("id"),
            "field_name": (t.get("field") or {}).get("display_name"),
            "domain_id": (t.get("domain") or {}).get("id"),
            "domain_name": (t.get("domain") or {}).get("display_name"),
        }
        for t in seen.values()
        if t.get("id")
    ]

    if not rows:
        return

    stmt = pg_insert(Topic).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "display_name": stmt.excluded.display_name,
            "subfield_id": stmt.excluded.subfield_id,
            "subfield_name": stmt.excluded.subfield_name,
            "field_id": stmt.excluded.field_id,
            "field_name": stmt.excluded.field_name,
            "domain_id": stmt.excluded.domain_id,
            "domain_name": stmt.excluded.domain_name,
        },
    )
    await session.execute(stmt)


async def _upsert_works_page(
    session: AsyncSession,
    works_page: list[dict],
    institution_country: str | None,
) -> int:
    """Upsert one page of works (and their work_topics). Returns count inserted/updated."""
    now = datetime.now(timezone.utc)

    work_rows = []
    work_topic_rows = []

    for work in works_page:
        wid = work.get("id")
        if not wid:
            continue

        oa = work.get("open_access") or {}
        pt = work.get("primary_topic") or {}

        work_rows.append(
            {
                "id": wid,
                "title": work.get("title"),
                "publication_year": work.get("publication_year"),
                "type": work.get("type"),
                "cited_by_count": work.get("cited_by_count", 0) or 0,
                "is_oa": oa.get("is_oa", False),
                "oa_status": oa.get("oa_status"),
                "is_international_collab": _calc_is_intl_collab(work, institution_country),
                "is_core_publication": _calc_is_core(work),
                "primary_topic_id": pt.get("id"),
                "raw_json": work,
                "last_synced_at": now,
            }
        )

        for topic_entry in work.get("topics", []):
            t = topic_entry.get("topic") or topic_entry
            tid = t.get("id")
            if tid:
                work_topic_rows.append(
                    {"work_id": wid, "topic_id": tid, "score": topic_entry.get("score")}
                )

    if not work_rows:
        return 0

    # Upsert works
    stmt = pg_insert(Work).values(work_rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={c: stmt.excluded[c] for c in Work.__table__.columns.keys() if c != "id"},
    )
    await session.execute(stmt)

    # Delete existing work_topics for these works, then re-insert
    wids = [r["id"] for r in work_rows]
    await session.execute(
        text("DELETE FROM work_topics WHERE work_id = ANY(:ids)"),
        {"ids": wids},
    )
    if work_topic_rows:
        await session.execute(pg_insert(WorkTopic).values(work_topic_rows))

    return len(work_rows)


async def _sync_topics_taxonomy(client: OpenAlexClient, session: AsyncSession) -> None:
    """Sync the full OpenAlex topics taxonomy (run once before works ingestion)."""
    logger.info("Syncing OpenAlex topics taxonomy…")
    total = 0
    async for page in client.paginate_topics():
        rows = [
            {
                "id": t.get("id"),
                "display_name": t.get("display_name", ""),
                "subfield_id": (t.get("subfield") or {}).get("id"),
                "subfield_name": (t.get("subfield") or {}).get("display_name"),
                "field_id": (t.get("field") or {}).get("id"),
                "field_name": (t.get("field") or {}).get("display_name"),
                "domain_id": (t.get("domain") or {}).get("id"),
                "domain_name": (t.get("domain") or {}).get("display_name"),
            }
            for t in page
            if t.get("id")
        ]
        stmt = pg_insert(Topic).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c: stmt.excluded[c] for c in Topic.__table__.columns.keys() if c != "id"},
        )
        await session.execute(stmt)
        await session.commit()
        total += len(rows)
    logger.info("Topics taxonomy sync complete: %d topics", total)


async def run_openalex_sync() -> None:
    """Entry point called by APScheduler and POST /admin/sync/openalex."""
    async with AsyncSessionLocal() as session:
        # Load configuration
        result = await session.execute(select(InstanceConfig).where(InstanceConfig.id == 1))
        config = result.scalar_one_or_none()
        if not config:
            logger.warning("OpenAlex sync skipped: instance not yet configured")
            return

        # Restrict ingestion to the current Leiden period — see module docstring.
        leiden_window = await _current_leiden_window(session)

        # Last successful sync — used as an OpenAlex "sync filter" cutoff so
        # keys on a plan with sync-filter access only re-fetch works
        # created/updated since then instead of re-ingesting the full corpus
        # every night (see help.openalex.org/api/filtering/#sync-filters-paid-plans).
        # A 1-day buffer absorbs clock skew and any partial-day updates an
        # exact cutoff would miss. None on the very first sync (full ingest).
        prev_sync_result = await session.execute(
            select(SyncLog.finished_at)
            .where(SyncLog.job_name == "openalex_nightly", SyncLog.status == "success")
            .order_by(SyncLog.finished_at.desc())
            .limit(1)
        )
        prev_sync_at = prev_sync_result.scalar_one_or_none()
        from_updated_date = (
            (prev_sync_at - timedelta(days=1)).date().isoformat() if prev_sync_at else None
        )

        # If the Leiden window has shifted since the works table was last
        # filled (or this is the first sync ever), from_updated_date alone
        # would miss publications that are newly in-window but weren't
        # recently modified in OpenAlex — e.g. a paper published years ago
        # that just entered scope because the window rolled forward. Force a
        # full re-sync of the window in that case instead of an incremental one.
        if leiden_window:
            bounds_result = await session.execute(
                select(func.min(Work.publication_year), func.max(Work.publication_year))
            )
            existing_bounds = tuple(bounds_result.one())
            if existing_bounds != leiden_window:
                logger.info(
                    "Leiden window is %s but works table currently spans %s — forcing a "
                    "full re-sync of the new window instead of an incremental one.",
                    leiden_window,
                    existing_bounds,
                )
                from_updated_date = None

        # Create sync log entry
        log = SyncLog(job_name="openalex_nightly", status="running")
        session.add(log)
        await session.commit()
        await session.refresh(log)
        log_id = log.id

    if not leiden_window:
        logger.warning(
            "OpenAlex works ingestion skipped: no Leiden data imported yet, so the "
            "publication-year window to restrict ingestion to is unknown. Import Leiden "
            "data (Paramètres du benchmark) — works will be ingested on the next sync."
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SyncLog).where(SyncLog.id == log_id))
            log_row = result.scalar_one()
            log_row.status = "success"
            log_row.finished_at = datetime.now(timezone.utc)
            log_row.records_processed = 0
            await session.commit()
        return

    publication_years = list(range(leiden_window[0], leiden_window[1] + 1))

    total_processed = 0
    async with OpenAlexClient(config.openalex_api_key, config.contact_email) as client:
        try:
            async with AsyncSessionLocal() as session:
                await _sync_topics_taxonomy(client, session)

            # Refresh the institution object FIRST. Works ingestion itself now
            # uses the recursive authorships.institutions.lineage filter (see
            # OpenAlexClient.paginate_works), so it no longer depends on this
            # direct-children list to know what to fetch. We still compute and
            # store it as informational metadata (shown in the Configuration
            # page, "N structure(s) dans le périmètre") and to log when
            # OpenAlex's direct associated_institutions data changes — it's
            # just no longer the scoping mechanism for ingestion.
            institution = await client.get_institution(config.openalex_institution_id)
            new_lineage = compute_effective_lineage(institution)

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(InstanceConfig).where(InstanceConfig.id == 1)
                )
                cfg = result.scalar_one()
                old_lineage = cfg.openalex_lineage_ids or []
                if set(new_lineage) != set(old_lineage):
                    logger.warning(
                        "Institution lineage changed during sync. "
                        "Old: %s  New: %s  — manual review recommended.",
                        old_lineage,
                        new_lineage,
                    )
                cfg.openalex_lineage_ids = new_lineage
                await session.commit()

            logger.info(
                "Starting works ingestion for institution %s (recursive lineage scope, "
                "publication_years=%d-%d, from_updated_date=%s)",
                config.openalex_institution_id,
                leiden_window[0],
                leiden_window[1],
                from_updated_date or "none (full sync)",
            )

            async def _ingest(from_date: str | None) -> None:
                nonlocal total_processed
                async for page in client.paginate_works(
                    config.openalex_institution_id,
                    from_updated_date=from_date,
                    publication_years=publication_years,
                ):
                    async with AsyncSessionLocal() as session:
                        await _upsert_topics(session, page)
                        count = await _upsert_works_page(session, page, config.country_code)
                        await session.commit()
                    total_processed += count
                    logger.info("Ingested %d works (total so far: %d)", count, total_processed)

            try:
                await _ingest(from_updated_date)
            except httpx.HTTPStatusError as exc:
                if from_updated_date and exc.response.status_code in (400, 403):
                    logger.warning(
                        "OpenAlex rejected the from_updated_date sync filter (HTTP %d) — this "
                        "API key's plan likely doesn't have sync-filter access. Falling back to "
                        "a full sync.",
                        exc.response.status_code,
                    )
                    await _ingest(None)
                else:
                    raise

            # Prune any works now outside the current window — handles the
            # window shifting forward each year (a publication_year that just
            # fell out of scope would otherwise stay in the DB forever, since
            # the incremental from_updated_date sync only adds/updates rows,
            # never removes them). CASCADE on work_topics.work_id (ondelete)
            # removes the matching topic rows too.
            async with AsyncSessionLocal() as session:
                prune_result = await session.execute(
                    text(
                        "DELETE FROM works WHERE publication_year IS NULL "
                        "OR publication_year < :start OR publication_year > :end"
                    ),
                    {"start": publication_years[0], "end": publication_years[-1]},
                )
                pruned = prune_result.rowcount
                await session.commit()
            if pruned:
                logger.info("Pruned %d works outside the current Leiden window", pruned)

            # Mark success
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(SyncLog).where(SyncLog.id == log_id))
                log_row = result.scalar_one()
                log_row.status = "success"
                log_row.finished_at = datetime.now(timezone.utc)
                log_row.records_processed = total_processed
                await session.commit()

            logger.info("OpenAlex sync complete: %d works processed", total_processed)

        except Exception as exc:
            logger.exception("OpenAlex sync failed: %s", exc)
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(SyncLog).where(SyncLog.id == log_id))
                log_row = result.scalar_one()
                log_row.status = "failed"
                log_row.finished_at = datetime.now(timezone.utc)
                log_row.records_processed = total_processed
                log_row.error_message = str(exc)
                await session.commit()
            raise
