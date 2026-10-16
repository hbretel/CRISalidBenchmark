"""Small conversational LLM served by vLLM (OpenAI-compatible API).

Used only where the evaluation grid itself plans a "LLM léger" step: criterion 1
(peer review) for journals absent from DOAJ, read from the journal's own
website and cached per journal (journal_quality table) — see the grid's
`automatisation` column for criterion 1. Disabled unless VLLM_BASE_URL and
VLLM_MODEL are set.

Grounding: the model must quote the sentence its answer rests on, and the
quote is checked against the page text — an answer whose quote is not found
verbatim is downgraded to "Indéterminé" rather than trusted.
"""

import json
import logging
import re
from html import unescape
from urllib.parse import urljoin

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MAX_PAGE_BYTES = 1_000_000
MAX_PROMPT_CHARS = 12_000
PER_PAGE_CHARS = 4_000
POLICY_LINK = re.compile(r"peer|review|referee|relecture|évaluation|evaluation|editorial|polic|politique|guideline", re.I)

SYSTEM_PROMPT = (
    "You read text extracted from a scholarly journal's website and report what it states about "
    "the peer review of submitted articles. Answer only from the text. Reply with a single JSON "
    'object: {"peer_review": "yes" | "no" | "unknown", "anonymity": "double" | "single" | "open" '
    '| "unknown", "quote": "<the exact sentence from the text supporting your answer, empty if unknown>"}. '
    '"yes": the text states that submissions are peer reviewed (refereed) by external reviewers. '
    '"no": the text explicitly states that articles are not peer reviewed (e.g. editorial review only). '
    '"unknown": the text does not say. "double": authors and reviewers are both anonymous '
    '(double-blind); "single": only reviewers are anonymous (single-blind); "open": identities are disclosed.'
)

_VERDICTS = {"yes": "Oui", "no": "Non", "unknown": "Indéterminé"}


def is_enabled() -> bool:
    return bool(settings.VLLM_BASE_URL and settings.VLLM_MODEL)


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.VLLM_API_KEY}"} if settings.VLLM_API_KEY else {}


def _base() -> str:
    return settings.VLLM_BASE_URL.rstrip("/")


async def check_connection() -> dict:
    """Status shown on the Configuration page."""
    if not is_enabled():
        return {"enabled": False, "reachable": False, "model": settings.VLLM_MODEL or None, "models": []}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_base()}/models", headers=_headers())
            resp.raise_for_status()
            models = [m.get("id") for m in resp.json().get("data", [])]
    except (httpx.HTTPError, ValueError) as exc:
        return {"enabled": True, "reachable": False, "model": settings.VLLM_MODEL, "models": [], "error": str(exc)}
    return {
        "enabled": True,
        "reachable": True,
        "model": settings.VLLM_MODEL,
        "models": models,
        "model_available": settings.VLLM_MODEL in models,
    }


async def _chat_json(client: httpx.AsyncClient, user_content: str) -> dict | None:
    payload = {
        "model": settings.VLLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = await client.post(f"{_base()}/chat/completions", json=payload, headers=_headers(), timeout=120.0)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.warning("vLLM call failed: %s", exc)
        return None
    match = re.search(r"\{.*\}", content or "", re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url, timeout=20.0)
        if resp.status_code != 200 or "html" not in resp.headers.get("content-type", ""):
            return None
        return resp.text[:MAX_PAGE_BYTES]
    except httpx.HTTPError:
        return None


async def fetch_journal_text(client: httpx.AsyncClient, homepage_url: str) -> tuple[str, list[str]]:
    """Up to two linked pages whose link looks like an editorial / peer-review
    policy, then the homepage — policy pages first and each capped at
    PER_PAGE_CHARS, so a long homepage cannot push them out of the prompt.
    Returns (text, urls actually read)."""
    html = await _fetch_html(client, homepage_url)
    if html is None:
        return "", []
    texts, urls = [], []
    candidates = []
    for href, label in re.findall(r'(?is)<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html):
        if POLICY_LINK.search(href) or POLICY_LINK.search(html_to_text(label)):
            absolute = urljoin(homepage_url, href)
            if absolute.startswith("http") and absolute != homepage_url and absolute not in candidates:
                candidates.append(absolute)
    for url in candidates[:2]:
        page = await _fetch_html(client, url)
        if page:
            texts.append(html_to_text(page)[:PER_PAGE_CHARS])
            urls.append(url)
    texts.append(html_to_text(html)[:PER_PAGE_CHARS])
    urls.append(homepage_url)
    return " ".join(texts), urls


async def assess_peer_review(client: httpx.AsyncClient, journal_name: str, homepage_url: str) -> dict | None:
    """llm_result for journal_quality, or None if the site or the LLM could not
    be reached (the attempt is still recorded by the caller)."""
    text, urls = await fetch_journal_text(client, homepage_url)
    if not text:
        return None
    answer = await _chat_json(
        client, f"Journal: {journal_name}\nWebsite text:\n{text[:MAX_PROMPT_CHARS]}"
    )
    if not answer:
        return None
    verdict = _VERDICTS.get(str(answer.get("peer_review", "")).lower(), "Indéterminé")
    anonymity = str(answer.get("anonymity", "unknown")).lower()
    quote = (answer.get("quote") or "").strip()
    normalized_text = re.sub(r"\s+", " ", text).lower()
    if verdict != "Indéterminé" and (not quote or re.sub(r"\s+", " ", quote).lower() not in normalized_text):
        verdict, anonymity = "Indéterminé", "unknown"
        evidence = "Réponse du LLM non étayée par une citation exacte du site : ignorée."
    else:
        evidence = f"Site de la revue : « {quote[:300]} »." if quote else "Le site de la revue ne mentionne pas le processus d'évaluation."
    return {
        "verdict": verdict,
        "anonymity": anonymity if anonymity in ("double", "single", "open") else "unknown",
        "evidence": evidence,
        "url": " ; ".join(urls),
        "model": settings.VLLM_MODEL,
    }
