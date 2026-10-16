"""Batched access to the free sources of the evaluation grid.

Upstream auto_checkers/sources.py queries each source once per DOI, which is
fine for evaluating one publication but not an institution's whole corpus
(~10^5 works). Same sources, fetched in bulk:
  - Crossref: /works?filter=doi:A,doi:B,… (OR'd), CROSSREF_BATCH DOIs per call;
  - HAL: Solr doiId_s:("A" OR "B" …), HAL_BATCH DOIs per call;
  - PubMed: EFetch on the PMIDs OpenAlex already provides, PUBMED_BATCH per call;
  - DOAJ: the public journal CSV dump (one download instead of one call per
    journal), turned into the bibjson shape the checkers read;
  - Retraction Watch: the public CSV published by Crossref.
Each fetcher returns per-DOI/PMID records already trimmed to the fields the
vendored checkers read, in the shape they expect. A failed batch returns None
for each of its keys (source not reached), never an empty result (which the
checkers would read as a negative answer).
"""

import asyncio
import csv
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings
from app.services.quality.grid import VENDOR_ROOT  # noqa: F401 -- sets up sys.path
from auto_checkers.retraction_watch import load_index

logger = logging.getLogger(__name__)

CROSSREF_BATCH = 50
HAL_BATCH = 50
PUBMED_BATCH = 200

DOAJ_CSV_URL = "https://doaj.org/csv"
RETRACTION_WATCH_URL = "https://gitlab.com/crossref/retraction-watch-data/-/raw/main/retraction_watch.csv"

_ASSERTION_NAMES = ("received", "accepted")


def bare_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
    return doi.lower() or None


def http_client(contact_email: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        headers={"User-Agent": f"CRISalidBenchmark/1.0 (mailto:{contact_email})"},
        follow_redirects=True,
    )


async def _get(client: httpx.AsyncClient, url: str, params: dict, attempts: int = 3) -> httpx.Response | None:
    for attempt in range(attempts):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPError, ValueError) as exc:
            if attempt == attempts - 1:
                logger.warning("Request to %s failed after %d attempts: %s", url, attempts, exc)
                return None
            await asyncio.sleep(2 ** (attempt + 1))
    return None


# ── Crossref ────────────────────────────────────────────────────────────────

def trim_crossref(item: dict) -> dict:
    """Keep only what the checkers read (see checkers.py): type, funders,
    relations, Crossmark dates, update notices, references (DOIs only — length
    preserved for 11.1), counts, abstract presence (11), author ORCIDs (11.2)."""
    return {
        "DOI": item.get("DOI"),
        "type": item.get("type"),
        "funder": [
            {k: f.get(k) for k in ("name", "DOI", "award") if f.get(k)} for f in item.get("funder") or []
        ],
        "relation": {
            k: [{"id": r.get("id")} for r in v]
            for k, v in (item.get("relation") or {}).items() if k in ("has-review", "has-preprint")
        },
        "assertion": [
            {"name": a.get("name"), "value": a.get("value")}
            for a in item.get("assertion") or [] if (a.get("name") or "").lower() in _ASSERTION_NAMES
        ],
        "updated-by": [
            {k: u.get(k) for k in ("type", "DOI", "source")} for u in item.get("updated-by") or []
        ],
        "update-to": [
            {k: u.get(k) for k in ("type", "DOI", "source")} for u in item.get("update-to") or []
        ],
        **(
            {"reference": [{"DOI": r["DOI"]} if r.get("DOI") else {} for r in item["reference"]]}
            if item.get("reference") is not None else {}
        ),
        "reference-count": item.get("reference-count"),
        "is-referenced-by-count": item.get("is-referenced-by-count"),
        "abstract": bool(item.get("abstract")),
        "author": [{"ORCID": a["ORCID"]} if a.get("ORCID") else {} for a in item.get("author") or []],
    }


async def fetch_crossref(client: httpx.AsyncClient, dois: list[str], contact_email: str) -> dict[str, dict | None]:
    """{doi: trimmed record, or None if not found / batch failed}."""
    out: dict[str, dict | None] = {d: None for d in dois}
    filter_value = ",".join(f"doi:{d}" for d in dois)
    resp = await _get(
        client, "https://api.crossref.org/works",
        {"filter": filter_value, "rows": len(dois), "mailto": contact_email},
    )
    if resp is None:
        return out
    for item in resp.json().get("message", {}).get("items", []):
        doi = bare_doi(item.get("DOI"))
        if doi in out:
            out[doi] = trim_crossref(item)
    return out


# ── HAL ─────────────────────────────────────────────────────────────────────

async def fetch_hal(client: httpx.AsyncClient, dois: list[str]) -> dict[str, dict | None]:
    """{doi: HAL Solr response shaped like sources.hal_search_by_doi(), or None
    for the whole batch if HAL could not be reached}."""
    quoted = " OR ".join(f'"{d}"' for d in dois)
    resp = await _get(
        client, "https://api.archives-ouvertes.fr/search/",
        {"q": f"doiId_s:({quoted})", "fl": "halId_s,doiId_s", "rows": 10 * len(dois), "wt": "json"},
    )
    if resp is None:
        return {d: None for d in dois}
    by_doi: dict[str, list[dict]] = {d: [] for d in dois}
    for doc in resp.json().get("response", {}).get("docs", []):
        doi = bare_doi(doc.get("doiId_s"))
        if doi in by_doi:
            by_doi[doi].append({"halId_s": doc.get("halId_s")})
    return {d: {"response": {"numFound": len(docs), "docs": docs}} for d, docs in by_doi.items()}


# ── PubMed ──────────────────────────────────────────────────────────────────

async def fetch_pubmed(client: httpx.AsyncClient, pmids: list[str]) -> dict[str, dict | None]:
    """{pmid: {"types": [...], "accessions": [...]}} from one EFetch call."""
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    if settings.NCBI_API_KEY:
        params["api_key"] = settings.NCBI_API_KEY
    resp = await _get(client, "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params)
    out: dict[str, dict | None] = {p: None for p in pmids}
    if resp is None:
        return out
    for article in re.split(r"(?=<PubmedArticle>)", resp.text)[1:]:
        m = re.search(r"<PMID[^>]*>(\d+)</PMID>", article)
        if m and m.group(1) in out:
            out[m.group(1)] = {
                "types": re.findall(r"<PublicationType[^>]*>([^<]+)</PublicationType>", article),
                "accessions": re.findall(r"<AccessionNumber>([^<]+)</AccessionNumber>", article),
            }
    return out


# ── Reference dumps (DOAJ, Retraction Watch) ────────────────────────────────

def _data_dir() -> Path:
    path = Path(settings.QUALITY_DATA_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def doaj_csv_path() -> Path:
    return _data_dir() / "doaj_journals.csv"


def retraction_watch_path() -> Path:
    return _data_dir() / "retraction_watch.csv"


def dump_date(path: Path) -> datetime | None:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) if path.exists() else None


async def refresh_dump(url: str, dest: Path, contact_email: str) -> bool:
    """Download url to dest if missing or older than QUALITY_DUMPS_MAX_AGE_DAYS.
    Returns whether a usable file exists afterwards (a failed refresh keeps the
    previous copy)."""
    max_age = settings.QUALITY_DUMPS_MAX_AGE_DAYS * 86400
    if dest.exists() and time.time() - dest.stat().st_mtime < max_age:
        return True
    tmp = dest.with_suffix(".part")
    try:
        async with http_client(contact_email) as client:
            async with client.stream("GET", url, timeout=httpx.Timeout(300.0, connect=15.0)) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as f:
                    async for chunk in resp.aiter_bytes(1 << 20):
                        f.write(chunk)
        tmp.replace(dest)
        logger.info("Downloaded %s (%d bytes)", dest.name, dest.stat().st_size)
    except (httpx.HTTPError, OSError) as exc:
        logger.warning("Could not refresh %s from %s: %s", dest.name, url, exc)
        tmp.unlink(missing_ok=True)
    return dest.exists()


_doaj_cache: tuple[float, dict[str, dict]] | None = None
_rw_cache: tuple[float, dict | None] | None = None


def doaj_index() -> dict[str, dict]:
    """{ISSN: bibjson-like dict} from the DOAJ journal CSV (cached per file mtime).

    The CSV flattens the DOAJ API's bibjson: review processes are joined with
    ", ", APC is "Yes"/"No", the delay is a plain number — rebuilt here into
    the editorial.review_process / apc.has_apc / publication_time_weeks keys
    check_1_doaj_review, check_4_1_1_1_diamond and check_1_7_publication_time read.
    """
    global _doaj_cache
    path = doaj_csv_path()
    if not path.exists():
        return {}
    mtime = path.stat().st_mtime
    if _doaj_cache and _doaj_cache[0] == mtime:
        return _doaj_cache[1]
    index: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            weeks = (row.get("Average number of weeks between article submission and publication") or "").strip()
            apc = (row.get("APC") or "").strip().lower()
            bibjson = {
                "title": row.get("Journal title"),
                "editorial": {
                    "review_process": [
                        p.strip() for p in (row.get("Review process") or "").split(",") if p.strip()
                    ],
                },
                "apc": {"has_apc": True if apc == "yes" else (False if apc == "no" else None)},
                "publication_time_weeks": int(weeks) if weeks.isdigit() else None,
            }
            for key in ("Journal ISSN (print version)", "Journal EISSN (online version)"):
                issn = (row.get(key) or "").strip().upper()
                if issn:
                    index[issn] = bibjson
    _doaj_cache = (mtime, index)
    return index


def doaj_result_for(oa_work: dict, index: dict[str, dict]) -> dict | None:
    """DOAJ search-API-shaped result for the work's journal, None without ISSN
    (or when the DOAJ dump is unavailable)."""
    if not index:
        return None
    source = ((oa_work.get("primary_location") or {}).get("source")) or {}
    issns = [i.upper() for i in source.get("issn") or [] if i]
    if not issns:
        return None
    for issn in issns:
        if issn in index:
            return {"total": 1, "results": [{"bibjson": index[issn]}]}
    return {"total": 0, "results": []}


def retraction_watch_index() -> dict | None:
    global _rw_cache
    path = retraction_watch_path()
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _rw_cache and _rw_cache[0] == mtime:
        return _rw_cache[1]
    _rw_cache = (mtime, load_index(str(path)))
    return _rw_cache[1]
