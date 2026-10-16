"""Bridge to the vendored evaluation-grid code (vendor/evaluation_grid/).

evaluate_work() is the bulk counterpart of upstream
auto_checkers/run_auto_answers.run(): the same checkers, fed with records
already fetched in batches (see sources.py) instead of one round of HTTP calls
per DOI. Criteria whose upstream checker needs per-work or per-author API
calls that do not scale to an institution's whole corpus are deliberately left
out ("bulk léger" scope, validated with the user):
  - author-level history: 15, 15.1, 20, 20.1, 53 (OpenAlex counts per author),
    17.x, 18.x (ORCID/HAL/Zenodo profiles);
  - citing / referenced works sets: 36, 66, 92-103;
  - one-off lookups: 3.1 (ClinicalTrials.gov), 79 (Wikipedia), 88.1 (SUDOC).
They are reported as "non couverts" in the coverage figures, never as "Non".
"""

import functools
import sys
from datetime import date
from pathlib import Path
from typing import Any

VENDOR_ROOT = Path(__file__).resolve().parents[3] / "vendor" / "evaluation_grid"
if str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))

from auto_checkers import checkers  # noqa: E402
from auto_checkers.checkers import AutoResult  # noqa: E402
from auto_checkers.orientation import grid_parameters, orient  # noqa: E402
from auto_checkers.retraction_watch import entries_for  # noqa: E402
from grille import score_engine  # noqa: E402
from grille.score_engine import classify_role, compute_score  # noqa: E402

# Working version of the grid (upstream README: "C'est la version de travail
# de la grille"), in calibration format — load_grid() rebuilds its gates,
# exclusions and active answers. This is the *default* calibration; the
# instance-wide overrides edited on the "Paramètres d'évaluation qualitative"
# page are applied on top of it (set_overrides) into an effective grid file.
GRID_FILE = VENDOR_ROOT / "data" / "ponderation_calibration_20261002.csv"
DEFAULT_GRID_PATH = str(GRID_FILE)

WEIGHT_FIELDS = {"points": "poids_points", "coefficient": "poids_coefficient", "modulateur": "facteur_modulation"}

_state: dict[str, Any] = {"path": DEFAULT_GRID_PATH, "overrides": {}}

# compute_score() reloads and re-validates the CSV on every call, which is
# fine for one DOI but not for ~10^5 works: cache it per path. compute_score
# resolves load_grid through the module global, so patching the module
# attribute is enough; the returned structures are only read, never mutated.
_upstream_load_grid = score_engine.load_grid


@functools.lru_cache(maxsize=4)
def _cached_load_grid(path: str):
    return _upstream_load_grid(path)


score_engine.load_grid = lambda path=score_engine.CSV_PATH: _cached_load_grid(str(path))

VERDICT_CODES = {"Oui": "O", "Non": "N", "Indéterminé": "I"}
CODE_VERDICTS = {v: k for k, v in VERDICT_CODES.items()}

# Mutually exclusive channel criteria (journal / proceedings / book): the
# engine raises on two "Oui" in one group. OpenAlex and Crossref legitimately
# disagree on some records (a conference paper in a source typed "journal"),
# so such conflicts are downgraded to "Indéterminé" before scoring.
_EXCLUSIVE_GROUPS = score_engine.DEFAULT_EXCLUSIVE_GROUPS


def grid_path() -> str:
    """Effective grid (default calibration + instance overrides)."""
    return _state["path"]


def has_overrides() -> bool:
    return bool(_state["overrides"])


def load_criteria() -> dict[str, dict]:
    return score_engine.load_grid(grid_path())[0]


def load_default_criteria() -> dict[str, dict]:
    return score_engine.load_grid(DEFAULT_GRID_PATH)[0]


def build_effective_grid(overrides: dict[str, dict], data_dir: str) -> str:
    """Write the default grid with `overrides` applied and validate it with the
    upstream engine (load_grid → validate_grid). Returns the file path; raises
    ValueError (message from the engine) if the result is not a valid grid.

    overrides: {criterion_id: {"weight": float, "parameters": {"N": float, ...}}}
    — "weight" goes to the single weight column of the criterion's role (a
    criterion has exactly one role, see score_engine.classify_role), so an
    override can never give it a second role.
    """
    import csv
    import hashlib
    import json

    from grille.parameters import set_parameters

    with open(DEFAULT_GRID_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    defaults = load_default_criteria()
    unknown = sorted(set(overrides) - set(defaults))
    if unknown:
        raise ValueError(f"Critères inconnus : {', '.join(unknown)}")
    for row in rows:
        override = overrides.get(row["id"])
        if not override:
            continue
        if "weight" in override:
            role = classify_role(defaults[row["id"]])
            if role not in WEIGHT_FIELDS:
                raise ValueError(f"Critère {row['id']} : aucun poids à modifier (rôle « {role} »).")
            row[WEIGHT_FIELDS[role]] = repr(float(override["weight"]))
        if override.get("parameters"):
            row["parametre"] = set_parameters(row.get("parametre") or "", override["parameters"])

    digest = hashlib.sha256(json.dumps(overrides, sort_keys=True).encode()).hexdigest()[:12]
    out_dir = Path(data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"grille_effective_{digest}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    _upstream_load_grid(str(path))  # validate_grid raises ValueError on an invalid grid
    return str(path)


def set_overrides(overrides: dict[str, dict], data_dir: str) -> None:
    """Make `overrides` the active calibration for this process."""
    path = build_effective_grid(overrides, data_dir) if overrides else DEFAULT_GRID_PATH
    _state["path"] = path
    _state["overrides"] = overrides


def grid_label() -> str:
    return GRID_FILE.name + (" (pondération modifiée)" if has_overrides() else "")


def criteria_metadata() -> list[dict]:
    """Grid rows exposed to the frontend (label, category, role, weights)."""
    rows = []
    for cid, row in load_criteria().items():
        rows.append({
            "id": cid,
            "parent_id": (row.get("id_parent") or "").strip() or None,
            "category": row.get("categorie") or "",
            "subcategory": row.get("sous_categorie") or "",
            "label": row.get("critere") or "",
            "type": row.get("type_critere") or "",
            "role": classify_role(row),
            "active_answer": score_engine.active_answer(row),
        })
    return rows


def _param(criteria: dict, crit_id: str, name: str, default):
    value = grid_parameters(criteria.get(crit_id, {})).get(name)
    if value is None:
        return default
    return int(value) if value.is_integer() and isinstance(default, int) else value


def _publisher_name(oa_work: dict) -> str | None:
    source = ((oa_work.get("primary_location") or {}).get("source")) or {}
    return source.get("host_organization_name")


def evaluate_work(
    oa_work: dict,
    crossref: dict | None,
    hal: dict | None,
    pubmed: dict | None,
    doaj_result: dict | None,
    journal_llm: dict | None,
    rw_index: dict | None,
    today: date | None = None,
) -> dict[str, AutoResult]:
    """All bulk-reachable criteria for one work, oriented to the effective grid.

    oa_work: works.raw_json. crossref / hal / pubmed: work_quality_sources
    columns (None = source not reached). doaj_result: DOAJ search-API-shaped
    dict for the work's journal ({"total": 0, ...} if absent from DOAJ, None if
    the work has no ISSN). journal_llm: journal_quality.llm_result.
    rw_index: Retraction Watch index (None if the dump is unavailable).
    """
    criteria = load_criteria()
    today = today or date.today()
    results: dict[str, AutoResult] = {}

    def add(crit_id: str, result: AutoResult) -> None:
        results[crit_id] = result

    # --- Peer review: DOAJ, then the small-LLM reading of the journal site ----
    results.update(checkers.check_1_doaj_review(doaj_result))
    if results["1"].verdict is None and journal_llm:
        evidence = f"{journal_llm.get('evidence') or ''} (petit LLM {journal_llm.get('model', '?')} sur {journal_llm.get('url', '?')})"
        add("1", AutoResult(journal_llm.get("verdict"), evidence.strip(), "heuristique"))
        anonymity = journal_llm.get("anonymity")
        if journal_llm.get("verdict") == "Oui" and anonymity in ("double", "single", "open"):
            add("1.1", AutoResult("Oui" if anonymity == "double" else "Non", evidence, "heuristique"))
            add("1.2", AutoResult("Non" if anonymity == "open" else "Oui", evidence, "heuristique"))
    results.update(checkers.check_published_reviews(crossref, min_reports=_param(criteria, "1.4", "N", 2)))
    add("1.5", checkers.check_1_5_review_delay(crossref, days=_param(criteria, "1.5", "N", 30)))
    add("1.7", checkers.check_1_7_publication_time(doaj_result, weeks=_param(criteria, "1.7", "N", 4)))

    # --- Preregistration (3.1 needs one ClinicalTrials.gov call per trial) ---
    r3, _registrations = checkers.check_3_registration(oa_work, (pubmed or {}).get("accessions"))
    add("3", r3)

    # --- Open access, repositories, licences ---------------------------------
    add("4", checkers.check_4_open_access(oa_work))
    add("4.1", checkers.check_4_1_gold(oa_work))
    add("4.1.1", checkers.check_4_1_1_diamond_or_full_gold(oa_work))
    add("4.1.1.1", checkers.check_4_1_1_1_diamond(doaj_result))
    add("4.2", checkers.check_4_2_repository_copy(oa_work))
    results.update(checkers.check_4_3_license(oa_work))
    add("2", checkers.check_2_preprint(hal, crossref, oa_work))

    # --- Channel and journal lists --------------------------------------------
    add("5", checkers.check_5_journal(oa_work))
    results.update(checkers.check_listed_in(oa_work))
    if doaj_result is not None:
        add("5.9", checkers.check_5_9_doaj(doaj_result))
    add("25", checkers.check_25_proceedings(oa_work, crossref))
    add("26", checkers.check_26_book(oa_work))
    add("26.1", checkers.check_26_1_monograph_not_chapter(oa_work))

    # --- Indexing and document types ------------------------------------------
    add("9", AutoResult("Oui", "Notice OpenAlex présente (corpus synchronisé depuis OpenAlex).", "haute"))
    results.update(checkers.check_9_x_family(oa_work))
    results.update(checkers.check_10_x_family(crossref))
    pmid = ((oa_work.get("ids") or {}).get("pmid") or "").rsplit("/", 1)[-1]
    if pmid:
        add("8", AutoResult("Oui", f"PMID {pmid} (identifiant PubMed de la notice OpenAlex).", "haute"))
        results.update(checkers.check_8_x_family((pubmed or {}).get("types") if pubmed else None))
    else:
        add("8", AutoResult(
            "Non", "Aucun PMID dans la notice OpenAlex (PubMed non interrogé par DOI en traitement de masse).",
            "heuristique",
        ))

    # --- Findability / metadata -------------------------------------------------
    add("10", checkers.check_10_has_doi(crossref, oa_work))
    add("11", checkers.check_11_metadata_open(oa_work, crossref))
    add("11.1", checkers.check_11_1_open_references(crossref))
    results.update(checkers.check_11_orcid_ror(oa_work, crossref))

    # --- Funding ----------------------------------------------------------------
    add("13", checkers.check_13_funding(crossref))
    add("13.1", checkers.check_13_1_award_number(crossref, oa_work))
    add("13.2", checkers.check_13_2_ec_funder(crossref, oa_work))

    # --- Federative publisher structures (local lists, publisher from OpenAlex) -
    publisher_name = _publisher_name(oa_work)
    if publisher_name:
        add("12", checkers.check_12_federative_structure(publisher_name))
        for list_key, crit_id in (
            ("une", "12.1"), ("eulac", "12.2"), ("aeup", "12.3"),
            ("aupresses", "12.4"), ("library_publishing_coalition", "12.5"), ("scholarled", "26.5"),
        ):
            add(crit_id, checkers.check_12_x_specific(publisher_name, list_key))

    # --- Collaborations / affiliations -----------------------------------------
    add("14", checkers.check_14_multiple_authors(oa_work))
    add("14.1", checkers.check_14_1_multiple_research_groups(oa_work))
    add("14.2", checkers.check_14_2_multiple_institutions(oa_work))
    add("14.3", checkers.check_14_3_company_academic(oa_work))
    add("14.4", checkers.check_14_4_multiple_countries(oa_work))
    results.update(checkers.check_14_5_6_many_authors(oa_work))
    add("16", checkers.check_16_institutional_affiliation(oa_work))
    add("16.1", checkers.check_16_1_all_affiliated(oa_work))

    # --- Integrity: Crossref update notices, Retraction Watch -------------------
    add("30", checkers.check_30_retraction(crossref))
    add("31", checkers.check_31_expression_of_concern(crossref))
    add("31.1", checkers.check_31_1_correction(crossref))
    doi = (oa_work.get("doi") or "").replace("https://doi.org/", "")
    if doi:
        results.update(checkers.check_retraction_watch_reasons(entries_for(rw_index, doi)))
    referenced_dois = None
    if crossref and crossref.get("reference") is not None:
        referenced_dois = [r["DOI"] for r in crossref["reference"] if r.get("DOI")]
    add("37", checkers.check_37_cites_concern(referenced_dois, rw_index))

    # --- Language, references, age, citations -----------------------------------
    lang_result = checkers.check_40_41_english(oa_work)
    add("40", lang_result)
    add("41", lang_result)
    add("46", checkers.check_46_has_references(crossref, oa_work))
    pub_date = oa_work.get("publication_date") or str(oa_work.get("publication_year") or "")
    results.update(checkers.check_age_criteria(pub_date, today=today))
    add("65", checkers.check_65_has_citation(oa_work))
    add("69", checkers.check_69_ten_citations(oa_work, crossref))
    results.update(checkers.check_106_top_cited(oa_work))
    add("107", checkers.check_107_fwci(oa_work, threshold=_param(criteria, "107", "N", 1.0)))
    add("73", checkers.check_73_sdg(oa_work))

    oriented = orient(results, criteria)
    _resolve_channel_conflicts(oriented)
    return oriented


def _resolve_channel_conflicts(results: dict[str, AutoResult]) -> None:
    for group in _EXCLUSIVE_GROUPS:
        yes = [cid for cid in group if results.get(cid) and results[cid].verdict == "Oui"]
        if len(yes) > 1:
            for cid in yes:
                results[cid] = AutoResult(
                    "Indéterminé",
                    results[cid].evidence + f" Sources contradictoires : critères {', '.join(yes)} "
                    "(mutuellement exclusifs) tous vérifiés.",
                    "heuristique",
                )


def encode_answers(results: dict[str, AutoResult]) -> dict[str, str]:
    """{id: "O"|"N"|"I"} for the criteria with a verdict (None = not reachable)."""
    return {cid: VERDICT_CODES[r.verdict] for cid, r in results.items() if r.verdict in VERDICT_CODES}


def score_answers(answers: dict[str, str]) -> dict[str, Any]:
    """Grid score of one work from its encoded answers."""
    flat = {cid: CODE_VERDICTS[code] for cid, code in answers.items()}
    try:
        score_base, coefficient, score_final, _detail = compute_score(flat, path=grid_path(), verbose=False)
    except ValueError as exc:
        return {"score_base": None, "coefficient": None, "score_final": None, "error": str(exc)[:500]}
    return {"score_base": score_base, "coefficient": coefficient, "score_final": score_final, "error": None}


def score_detail(answers: dict[str, str]) -> list[dict]:
    """Individual contributions (points / coefficients) for the work detail view."""
    flat = {cid: CODE_VERDICTS[code] for cid, code in answers.items()}
    try:
        _b, _c, _f, detail = compute_score(flat, path=grid_path(), verbose=False)
    except ValueError:
        return []
    return [{"kind": kind, "id": cid, "value": round(val, 4)} for kind, cid, _label, val in detail]
