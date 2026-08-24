"""Async HTTP client for the OpenAlex API.

Authentication note (verify at dev time):
  OpenAlex introduced mandatory API key authentication in early 2026.
  This client passes the key as a query parameter (?api_key=...) based on
  the current specification, but the exact format (query param vs. header)
  should be verified against the live OpenAlex documentation before first use
  as this mechanism was recently introduced and may still be evolving.

Rate limits (verify at dev time):
  The spec cites ~10 req/s as an estimate; verify the actual limit and whether
  OpenAlex returns rate-limit headers (X-RateLimit-* or similar) for tracking.
  A tarification-à-l'usage applies beyond a free daily credit; check current
  thresholds in the OpenAlex pricing documentation.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org"

# OpenAlex practical limit on OR-separated values within a single filter.
OR_FILTER_CHUNK_SIZE = 50


def _chunk_ids(ids: list[str], size: int) -> list[list[str]]:
    return [ids[i:i + size] for i in range(0, len(ids), size)]


class RateLimitError(Exception):
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after


def _is_retryable_openalex_error(exc: BaseException) -> bool:
    """Transient errors worth retrying: rate limits, network issues, 5xx.

    4xx client errors (bad API key, unknown institution ID, …) are permanent —
    retrying them wastes ~15s of exponential backoff before surfacing the same
    error the first attempt already had.
    """
    if isinstance(exc, (RateLimitError, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


class OpenAlexClient:
    def __init__(self, api_key: str, contact_email: str):
        self._api_key = api_key
        self._contact_email = contact_email
        self._client = httpx.AsyncClient(
            base_url=OPENALEX_BASE,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": f"CRISalidBenchmark/1.0 (mailto:{contact_email})"},
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Single GET call with auth params injected. Raises on non-2xx."""
        full_params = {
            "api_key": self._api_key,
            "mailto": self._contact_email,
            **(params or {}),
        }
        response = await self._client.get(path, params=full_params)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(retry_after=retry_after)

        response.raise_for_status()
        return response.json()

    @retry(
        # Only retry transient failures: rate limiting, transport-level errors,
        # and 5xx server errors. 4xx client errors (401 bad key, 404 unknown
        # institution, etc.) are permanent — retrying them just adds ~15s of
        # exponential backoff before surfacing the same error to the user.
        retry=retry_if_exception(_is_retryable_openalex_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get_with_retry(self, path: str, params: dict[str, Any] | None = None) -> dict:
        try:
            return await self._get(path, params)
        except RateLimitError as e:
            logger.warning("Rate limited by OpenAlex; waiting %ss", e.retry_after)
            await asyncio.sleep(e.retry_after)
            raise  # let tenacity handle the retry

    async def get_institution(self, openalex_id: str) -> dict:
        """Fetch a single institution object by OpenAlex ID."""
        return await self.get_with_retry(f"/institutions/{openalex_id}")

    async def get_institution_by_ror(self, ror_id: str) -> dict | None:
        """Resolve a ROR ID to an OpenAlex institution object.

        Returns None if no institution is found for the given ROR ID.

        Dev-time note: verify the exact filter syntax for ROR resolution —
        either GET /institutions/ror:{ror_id} or filter=ror:{ror_id}.
        """
        data = await self.get_with_retry("/institutions", params={"filter": f"ror:{ror_id}"})
        results = data.get("results", [])
        return results[0] if results else None

    async def paginate_works(
        self,
        institution_ids: str | list[str],
        per_page: int = 200,
        from_updated_date: str | None = None,
    ) -> AsyncGenerator[list[dict], None]:
        """Cursor-paginate all works across one or more institution IDs.

        Accepts either a single OpenAlex institution ID or a full "effective
        lineage" list (self + associated_institutions relationship="child" —
        see institution_resolver.compute_effective_lineage).

        IMPORTANT — this used to filter on institutions.lineage:{id}, relying
        on OpenAlex's own ROR-derived lineage. Confirmed broken 2026-08-21 on
        real data (Université Paris-Saclay, I277688954): OpenAlex's lineage
        field is empty beyond self for this institution despite 184 real child
        entities recorded under associated_institutions — so the lineage
        filter silently ingested only the parent's own directly-affiliated
        works, missing every component institution's publications. Filtering
        on institutions.id with the full effective-lineage ID list (OR'd) is
        the only way to actually capture them.

        Large ID lists are chunked to stay within OpenAlex's practical
        per-filter OR-value limit. A work affiliated with institutions from two
        different chunks may be yielded twice — upserting by work ID on the
        caller side makes this harmless.

        from_updated_date: optional "sync filter" (YYYY-MM-DD) restricting
        results to works created/updated on or after that date — see
        https://help.openalex.org/api/filtering/#sync-filters-paid-plans.
        Only available to API keys on a plan with sync-filter access; the
        caller (openalex_sync.run_openalex_sync) is responsible for falling
        back to a full sync (this param omitted) if OpenAlex rejects it.

        Yields one page (list of work dicts) at a time.
        """
        ids = [institution_ids] if isinstance(institution_ids, str) else list(institution_ids)
        for chunk in _chunk_ids(ids, OR_FILTER_CHUNK_SIZE):
            filter_value = "|".join(chunk)
            filter_str = f"institutions.id:{filter_value}"
            if from_updated_date:
                filter_str += f",from_updated_date:{from_updated_date}"
            cursor = "*"
            while cursor:
                data = await self.get_with_retry(
                    "/works",
                    params={
                        "filter": filter_str,
                        "per-page": per_page,
                        "cursor": cursor,
                        "select": (
                            "id,title,publication_year,type,cited_by_count,"
                            "is_oa,open_access,authorships,primary_topic,topics,"
                            "primary_location,language,is_retracted"
                        ),
                    },
                )
                results = data.get("results", [])
                if not results:
                    break
                yield results
                cursor = data.get("meta", {}).get("next_cursor")

    async def get_topic_counts_for_institution(
        self, institution_ids: str | list[str]
    ) -> list[dict]:
        """Return per-topic publication counts for one or more institution IDs.

        Calls GET /works?filter=institutions.id:{ids}&group_by=primary_topic.id
        which OpenAlex resolves server-side — far cheaper than paginating all
        works. Accepts a single ID (peers, not known to have this lineage issue
        at time of writing) or a list (effective lineage — see paginate_works).
        Counts from different chunks are summed per topic; a work affiliated
        with institutions from two chunks may be double-counted — acceptable
        approximation for a volume-based specificity comparison (see §4.5).

        Returns a list of {"key": topic_id, "key_display_name": name, "count": N}.

        Dev-time note: verify the exact response field names for the grouped result.
        """
        ids = [institution_ids] if isinstance(institution_ids, str) else list(institution_ids)
        merged_counts: dict[str, dict] = {}
        for chunk in _chunk_ids(ids, OR_FILTER_CHUNK_SIZE):
            for group in await self._get_topic_counts_chunk("|".join(chunk)):
                key = group.get("key")
                if not key:
                    continue
                if key in merged_counts:
                    merged_counts[key]["count"] += group.get("count", 0)
                else:
                    merged_counts[key] = dict(group)
        return list(merged_counts.values())

    async def _get_topic_counts_chunk(self, filter_value: str) -> list[dict]:
        all_groups: list[dict] = []
        cursor = "*"
        while cursor:
            data = await self.get_with_retry(
                "/works",
                params={
                    "filter": f"institutions.id:{filter_value}",
                    "group_by": "primary_topic.id",
                    "per-page": 200,
                    "cursor": cursor,
                },
            )
            groups = data.get("group_by", [])
            all_groups.extend(groups)
            cursor = data.get("meta", {}).get("next_cursor")
            if not groups:
                break
        return all_groups

    async def paginate_topics(self, per_page: int = 200) -> AsyncGenerator[list[dict], None]:
        """Paginate the full OpenAlex topics taxonomy."""
        page = 1
        while True:
            data = await self.get_with_retry(
                "/topics",
                params={"per-page": per_page, "page": page},
            )
            results = data.get("results", [])
            if not results:
                break
            yield results
            meta = data.get("meta", {})
            if page * per_page >= meta.get("count", 0):
                break
            page += 1

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "OpenAlexClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
