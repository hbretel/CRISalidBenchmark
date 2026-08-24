"""Leiden Ranking Open Edition ingestion (annual, manual trigger). Spec v1.7.

Source file: XLSX export from Zenodo (long/tidy format — one row per
institution × field × period × Core_pubs_only × Frac_counting combination).
Read via openpyxl in read_only (streaming) mode — the full workbook can be
several hundred MB and must never be loaded whole via pandas.read_excel.

Import filters applied (§3.5, §4.2):
  - Frac_counting = 0 only (full/whole counting; fractional deferred to v2).
  - Both values of Core_pubs_only are kept (0 and 1) — needed since the
    field-normalised percentile family (PP_top_*, MNCS) only exists on
    Core_pubs_only=1 rows, while the absolute-citation-threshold family
    (PP_*_cits) only exists on Core_pubs_only=0 rows (§5.1/§7 toggle).
  - Only the single most recent Period present in the file is imported (a
    file contains up to 15 rolling 4-year windows per institution/field);
    determined by sorting distinct values, never hard-coded.

Two full passes over the sheet are required because openpyxl's read_only
worksheets are single-iteration streams: pass 1 determines the latest Period,
pass 2 performs the actual filtered import.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import pycountry
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.leiden import LeidenSnapshot
from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)

# ── Column map: leiden_snapshot column -> candidate source header names ────
# Source headers per the real Zenodo export (colonnes_leiden_open_2025.xlsx).
LEIDEN_COLUMN_MAP: dict[str, list[str]] = {
    "ror_id":          ["ROR_ID"],
    "university_name": ["University"],
    "country":         ["Country"],
    "period":          ["Period"],
    "field":           ["Field"],
    "core_pubs_only":  ["Core_pubs_only"],
    "frac_counting":   ["Frac_counting"],
    "p":               ["P"],
    "tcs":             ["TCS"],
    "mcs":             ["MCS"], "mcs_lb": ["MCS_lb"], "mcs_ub": ["MCS_ub"],
    "mncs":            ["MNCS"], "mncs_lb": ["MNCS_lb"], "mncs_ub": ["MNCS_ub"],
    "pp_top_1":        ["PP_top_1"], "pp_top_1_lb": ["PP_top_1_lb"], "pp_top_1_ub": ["PP_top_1_ub"],
    "pp_top_5":        ["PP_top_5"], "pp_top_5_lb": ["PP_top_5_lb"], "pp_top_5_ub": ["PP_top_5_ub"],
    "pp_top_10":       ["PP_top_10"], "pp_top_10_lb": ["PP_top_10_lb"], "pp_top_10_ub": ["PP_top_10_ub"],
    "pp_top_50":       ["PP_top_50"], "pp_top_50_lb": ["PP_top_50_lb"], "pp_top_50_ub": ["PP_top_50_ub"],
    "pp_10_cits":      ["PP_10_cits"], "pp_10_cits_lb": ["PP_10_cits_lb"], "pp_10_cits_ub": ["PP_10_cits_ub"],
    "pp_20_cits":      ["PP_20_cits"], "pp_20_cits_lb": ["PP_20_cits_lb"], "pp_20_cits_ub": ["PP_20_cits_ub"],
    "pp_50_cits":      ["PP_50_cits"], "pp_50_cits_lb": ["PP_50_cits_lb"], "pp_50_cits_ub": ["PP_50_cits_ub"],
    "pp_100_cits":     ["PP_100_cits"], "pp_100_cits_lb": ["PP_100_cits_lb"], "pp_100_cits_ub": ["PP_100_cits_ub"],
    "pp_int_collab":   ["PP_int_collab"], "pp_int_collab_lb": ["PP_int_collab_lb"], "pp_int_collab_ub": ["PP_int_collab_ub"],
    "pp_oa":           ["PP_OA"], "pp_oa_lb": ["PP_OA_lb"], "pp_oa_ub": ["PP_OA_ub"],
}

# Manual corrections for country names pycountry cannot resolve directly
# (common/ambiguous names vs. ISO official names, disputed territories, etc.).
# Extend this table as unresolved countries are logged during real imports.
COUNTRY_NAME_OVERRIDES: dict[str, str] = {
    "Russia": "RU",
    "South Korea": "KR",
    "North Korea": "KP",
    "Iran": "IR",
    "Vietnam": "VN",
    "Syria": "SY",
    "Taiwan": "TW",
    "Bolivia": "BO",
    "Venezuela": "VE",
    "Tanzania": "TZ",
    "Moldova": "MD",
    "Laos": "LA",
    "Brunei": "BN",
    "Ivory Coast": "CI",
    "Czech Republic": "CZ",
    "Macedonia": "MK",
    "Congo": "CG",
    "Democratic Republic of Congo": "CD",
    "Democratic Republic of the Congo": "CD",
    "USA": "US",
    "United States": "US",
    "United Kingdom": "GB",
    "UK": "GB",
}

_ROR_PREFIX = "https://ror.org/"


def normalize_ror(ror_id: str | None) -> str | None:
    """Strip the https://ror.org/ prefix if present. Convention: stored bare."""
    if not ror_id:
        return None
    ror_id = ror_id.strip()
    if ror_id.startswith(_ROR_PREFIX):
        return ror_id[len(_ROR_PREFIX):]
    return ror_id


def resolve_country_code(country_name: str | None) -> str | None:
    """Resolve a plain-text country name (Leiden format) to ISO 3166-1 alpha-2."""
    if not country_name:
        return None
    country_name = country_name.strip()

    if country_name in COUNTRY_NAME_OVERRIDES:
        return COUNTRY_NAME_OVERRIDES[country_name]

    match = pycountry.countries.get(name=country_name)
    if match:
        return match.alpha_2

    match = pycountry.countries.get(common_name=country_name)
    if match:
        return match.alpha_2

    try:
        results = pycountry.countries.search_fuzzy(country_name)
        if results:
            return results[0].alpha_2
    except LookupError:
        pass

    logger.warning("Could not resolve country name to ISO code: %r", country_name)
    return None


def _header_index_map(header_row: tuple) -> dict[str, int]:
    """Map raw source header name -> column index (0-based)."""
    return {
        str(cell).strip(): idx
        for idx, cell in enumerate(header_row)
        if cell is not None
    }


def _build_column_indices(header_map: dict[str, int]) -> dict[str, int | None]:
    """Resolve each leiden_snapshot column to a source column index, or None if absent."""
    indices: dict[str, int | None] = {}
    for target, candidates in LEIDEN_COLUMN_MAP.items():
        indices[target] = next((header_map[c] for c in candidates if c in header_map), None)
    return indices


def _cell(row: tuple, idx: int | None):
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _parse_float(v) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _parse_bool_flag(v) -> bool | None:
    """Parse a 0/1 (or True/False) flag column."""
    if v in (None, ""):
        return None
    if isinstance(v, bool):
        return v
    try:
        return bool(int(v))
    except (ValueError, TypeError):
        return str(v).strip().lower() in {"true", "yes"}


_PERIOD_START_YEAR_RE = re.compile(r"(\d{4})")

# The Zenodo export has multiple sheets (e.g. "Explanation", "Results") — the
# actual tidy data lives on "Results". `wb.active` picks whichever sheet was
# active when the file was saved (typically "Explanation"), which has none of
# the expected headers and would silently import zero rows.
RESULTS_SHEET_NAME = "Results"


def _period_sort_key(period: str) -> int:
    """Sort key for a Period string like '2020–2023' — the starting year."""
    match = _PERIOD_START_YEAR_RE.search(period)
    return int(match.group(1)) if match else -1


def _get_results_sheet(wb):
    if RESULTS_SHEET_NAME in wb.sheetnames:
        return wb[RESULTS_SHEET_NAME]
    raise ValueError(
        f"Expected a {RESULTS_SHEET_NAME!r} sheet in the Leiden XLSX export, "
        f"found: {wb.sheetnames}"
    )


def _find_latest_period(xlsx_path: Path) -> str | None:
    """Pass 1: scan the Period column only, return the most recent distinct value."""
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = _get_results_sheet(wb)
        rows = ws.iter_rows(values_only=True)
        header_map = _header_index_map(next(rows))
        period_idx = next(
            (header_map[c] for c in LEIDEN_COLUMN_MAP["period"] if c in header_map), None
        )
        if period_idx is None:
            logger.warning("No Period column found — cannot filter by latest period")
            return None

        periods: set[str] = set()
        for row in rows:
            value = _cell(row, period_idx)
            if value:
                periods.add(str(value).strip())

        if not periods:
            return None
        return max(periods, key=_period_sort_key)
    finally:
        wb.close()


async def import_leiden_xlsx(xlsx_path: Path, snapshot_year: int) -> int:
    """Parse a Leiden Ranking XLSX export and upsert rows into leiden_snapshot.

    Preserves historical snapshots — rows for previous snapshot_years are kept.
    Filters: frac_counting=False only, latest period only, both core_pubs_only
    values kept. Returns the number of rows upserted.
    """
    logger.info("Loading Leiden XLSX: %s (snapshot_year=%d)", xlsx_path, snapshot_year)

    async with AsyncSessionLocal() as session:
        log = SyncLog(job_name="leiden_annual", status="running")
        session.add(log)
        await session.commit()
        await session.refresh(log)
        log_id = log.id

    total = 0
    try:
        latest_period = _find_latest_period(xlsx_path)
        logger.info("Latest Period selected for import: %s", latest_period)

        wb = load_workbook(xlsx_path, read_only=True, data_only=True)
        try:
            ws = _get_results_sheet(wb)
            rows = ws.iter_rows(values_only=True)
            header_map = _header_index_map(next(rows))
            idx = _build_column_indices(header_map)

            batch: list[dict] = []
            unresolved_countries: set[str] = set()

            for row in rows:
                frac_counting = _parse_bool_flag(_cell(row, idx["frac_counting"]))
                if frac_counting is None or frac_counting:
                    continue  # Frac_counting=1 rows out of MVP scope

                period = _cell(row, idx["period"])
                period = str(period).strip() if period else None
                if latest_period is not None and period != latest_period:
                    continue

                core_pubs_only = _parse_bool_flag(_cell(row, idx["core_pubs_only"]))
                if core_pubs_only is None:
                    continue

                ror_id = normalize_ror(_cell(row, idx["ror_id"]))
                if not ror_id:
                    continue

                country_name = _cell(row, idx["country"])
                country_code = resolve_country_code(
                    str(country_name).strip() if country_name else None
                )
                if country_name and not country_code:
                    unresolved_countries.add(str(country_name))

                field = _cell(row, idx["field"])
                field = str(field).strip() if field else "All sciences"

                record = {
                    "ror_id": ror_id,
                    "university_name": _cell(row, idx["university_name"]),
                    "country_code": country_code,
                    "snapshot_year": snapshot_year,
                    "period": period,
                    "field": field,
                    "core_pubs_only": core_pubs_only,
                    "frac_counting": False,
                    "p": _parse_float(_cell(row, idx["p"])),
                    "tcs": _parse_float(_cell(row, idx["tcs"])),
                    "mcs": _parse_float(_cell(row, idx["mcs"])),
                    "mcs_lb": _parse_float(_cell(row, idx["mcs_lb"])),
                    "mcs_ub": _parse_float(_cell(row, idx["mcs_ub"])),
                    "mncs": _parse_float(_cell(row, idx["mncs"])),
                    "mncs_lb": _parse_float(_cell(row, idx["mncs_lb"])),
                    "mncs_ub": _parse_float(_cell(row, idx["mncs_ub"])),
                    "pp_top_1": _parse_float(_cell(row, idx["pp_top_1"])),
                    "pp_top_1_lb": _parse_float(_cell(row, idx["pp_top_1_lb"])),
                    "pp_top_1_ub": _parse_float(_cell(row, idx["pp_top_1_ub"])),
                    "pp_top_5": _parse_float(_cell(row, idx["pp_top_5"])),
                    "pp_top_5_lb": _parse_float(_cell(row, idx["pp_top_5_lb"])),
                    "pp_top_5_ub": _parse_float(_cell(row, idx["pp_top_5_ub"])),
                    "pp_top_10": _parse_float(_cell(row, idx["pp_top_10"])),
                    "pp_top_10_lb": _parse_float(_cell(row, idx["pp_top_10_lb"])),
                    "pp_top_10_ub": _parse_float(_cell(row, idx["pp_top_10_ub"])),
                    "pp_top_50": _parse_float(_cell(row, idx["pp_top_50"])),
                    "pp_top_50_lb": _parse_float(_cell(row, idx["pp_top_50_lb"])),
                    "pp_top_50_ub": _parse_float(_cell(row, idx["pp_top_50_ub"])),
                    "pp_10_cits": _parse_float(_cell(row, idx["pp_10_cits"])),
                    "pp_10_cits_lb": _parse_float(_cell(row, idx["pp_10_cits_lb"])),
                    "pp_10_cits_ub": _parse_float(_cell(row, idx["pp_10_cits_ub"])),
                    "pp_20_cits": _parse_float(_cell(row, idx["pp_20_cits"])),
                    "pp_20_cits_lb": _parse_float(_cell(row, idx["pp_20_cits_lb"])),
                    "pp_20_cits_ub": _parse_float(_cell(row, idx["pp_20_cits_ub"])),
                    "pp_50_cits": _parse_float(_cell(row, idx["pp_50_cits"])),
                    "pp_50_cits_lb": _parse_float(_cell(row, idx["pp_50_cits_lb"])),
                    "pp_50_cits_ub": _parse_float(_cell(row, idx["pp_50_cits_ub"])),
                    "pp_100_cits": _parse_float(_cell(row, idx["pp_100_cits"])),
                    "pp_100_cits_lb": _parse_float(_cell(row, idx["pp_100_cits_lb"])),
                    "pp_100_cits_ub": _parse_float(_cell(row, idx["pp_100_cits_ub"])),
                    "pp_int_collab": _parse_float(_cell(row, idx["pp_int_collab"])),
                    "pp_int_collab_lb": _parse_float(_cell(row, idx["pp_int_collab_lb"])),
                    "pp_int_collab_ub": _parse_float(_cell(row, idx["pp_int_collab_ub"])),
                    "pp_oa": _parse_float(_cell(row, idx["pp_oa"])),
                    "pp_oa_lb": _parse_float(_cell(row, idx["pp_oa_lb"])),
                    "pp_oa_ub": _parse_float(_cell(row, idx["pp_oa_ub"])),
                    "raw_row": {str(k): v for k, v in zip(header_map.keys(), row)},
                }

                batch.append(record)

                if len(batch) >= 500:
                    async with AsyncSessionLocal() as session:
                        await _upsert_batch(session, batch)
                        await session.commit()
                    total += len(batch)
                    batch = []

            if batch:
                async with AsyncSessionLocal() as session:
                    await _upsert_batch(session, batch)
                    await session.commit()
                total += len(batch)

            if unresolved_countries:
                logger.warning(
                    "Unresolved country names during Leiden import (institutions with these "
                    "names will have country_code=NULL, invisible to the geographic peer "
                    "group): %s",
                    sorted(unresolved_countries),
                )
        finally:
            wb.close()

        if total == 0:
            raise ValueError(
                "Leiden import parsed 0 rows — check that the source file's Period/"
                "Frac_counting columns match the expected format (see LEIDEN_COLUMN_MAP)"
            )

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SyncLog).where(SyncLog.id == log_id))
            log_row = result.scalar_one()
            log_row.status = "success"
            log_row.finished_at = datetime.now(timezone.utc)
            log_row.records_processed = total
            await session.commit()

        logger.info("Leiden import complete: %d rows", total)
        return total

    except Exception as exc:
        logger.exception("Leiden import failed: %s", exc)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SyncLog).where(SyncLog.id == log_id))
            log_row = result.scalar_one()
            log_row.status = "failed"
            log_row.finished_at = datetime.now(timezone.utc)
            log_row.records_processed = total
            log_row.error_message = str(exc)
            await session.commit()
        raise


async def _upsert_batch(session: AsyncSession, batch: list[dict]) -> None:
    stmt = pg_insert(LeidenSnapshot).values(batch)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_leiden_snapshot_key",
        set_={
            c: stmt.excluded[c]
            for c in LeidenSnapshot.__table__.columns.keys()
            if c not in ("id", "ror_id", "field", "period", "core_pubs_only", "snapshot_year")
        },
    )
    await session.execute(stmt)


async def check_leiden_update() -> None:
    """Monthly scheduled check — logs a reminder if a new Leiden edition may be available.

    The Leiden Ranking is published annually (typically mid-year). This job does
    not auto-download; it only logs a reminder so the operator can trigger the
    manual import via POST /admin/sync/leiden.
    """
    logger.info(
        "Monthly Leiden check: verify https://www.leidenranking.com/ranking for a "
        "new edition, then trigger POST /admin/sync/leiden with the downloaded XLSX."
    )
