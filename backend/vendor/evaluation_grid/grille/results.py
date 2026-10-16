#!/usr/bin/env python3
"""
Format des résultats d'une évaluation (answers.json) : preuves incluses.

Pour chaque critère de la grille, une entrée :

    "<id>": {
        "intitulé":            texte du critère,
        "conditionne":         ids des critères enfants que ce critère active/désactive
                               (vide si le critère n'est pas un gate),
        "est conditionné par": id du critère parent qui le conditionne (vide sinon),
        "activé si":           réponse qui active le critère (colonne active_si de la
                               grille : "Oui" par défaut, "Non" pour un critère
                               « exempt de défaut » pénalisant),
        "réponse":             "Oui" | "Non" | "Indéterminé", ou "" si le critère est
                               rendu inactif par un critère qui le conditionne (ou non
                               répondu),
        "preuve":              élément de preuve ; vide si la réponse est vide ou si le
                               critère n'est pas activé (réponse ≠ "activé si")
    }

load_answers() relit ce format (et l'ancien format plat + preuves.py migré), et
build_results() le produit.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grille.score_engine import (  # noqa: E402
    CSV_PATH,
    active_answer,
    compute_deactivated,
    flatten_answers,
    load_grid,
    resolve_exclusions,
)

def sort_key(crit_id):
    return [int(p) for p in crit_id.split(".")]


def build_results(answers, preuves=None, path=CSV_PATH):
    """answers : {id: réponse} (ou format enrichi) ; preuves : {id: texte}. Renvoie le dict
    enrichi pour TOUS les critères de la grille, dans l'ordre des ids."""
    preuves = preuves or {}
    criteria, children_of, _mods = load_grid(path)
    flat = resolve_exclusions(criteria, flatten_answers(answers))
    deactivated = compute_deactivated(criteria, children_of, flat)
    raw = flatten_answers(answers)

    results = {}
    for crit_id in sorted(criteria, key=sort_key):
        row = criteria[crit_id]
        gate = (row.get("desactive_si") or "").strip()
        parent = (row.get("id_parent") or "").strip()
        parent_is_gate = bool(parent and (criteria[parent].get("desactive_si") or "").strip())
        answer = "" if crit_id in deactivated else raw.get(crit_id, "")
        activated_if = active_answer(row)
        proof = preuves.get(crit_id, "") if answer == activated_if else ""
        if isinstance(answers.get(crit_id), dict) and answer == activated_if:
            proof = answers[crit_id].get("preuve", "") or proof
        results[crit_id] = {
            "intitulé": row["critere"],
            "conditionne": sorted(children_of.get(crit_id, []), key=sort_key) if gate else [],
            "est conditionné par": parent if parent_is_gate else "",
            "activé si": activated_if,
            "réponse": answer,
            "preuve": proof,
        }
    return results


# Formulation complémentaire du fait affirmatif : « exempt de… », « Aucun des auteurs… »,
# « publié depuis moins de… » (complément de « depuis au moins… »).
COMPLEMENT_WORDING = re.compile(r"\bexempte?s?\b|^\s*Aucun|depuis moins de", re.IGNORECASE)
FLIP = {"Oui": "Non", "Non": "Oui"}


def is_complement_wording(text):
    return bool(COMPLEMENT_WORDING.search(text or ""))


def reorient_answers(answers, source_criteria, target_criteria):
    """Transpose des réponses plates {id: réponse} d'une grille à une autre : une réponse
    Oui/Non est inversée quand un critère est formulé dans un sens dans la grille source
    et dans le sens contraire dans la grille cible (ex. 30 « fait-il l'objet d'un avis de
    rétractation ? » dans la grille canonique, « est-il exempt d'avis de rétractation ? »
    dans celle du 30/09/2026). Les ids absents de la grille cible sont abandonnés."""
    reoriented = {}
    for crit_id, answer in answers.items():
        if crit_id not in target_criteria:
            continue
        source_text = (source_criteria.get(crit_id) or {}).get("critere", "")
        target_text = target_criteria[crit_id].get("critere", "")
        if answer in FLIP and is_complement_wording(source_text) != is_complement_wording(target_text):
            answer = FLIP[answer]
        reoriented[crit_id] = answer
    return reoriented


def write_results(results, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def load_answers(path):
    """Charge un answers.json (format enrichi ou ancien format plat) et renvoie
    (réponses plates {id: réponse}, preuves {id: texte})."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    preuves = {
        cid: v.get("preuve", "") for cid, v in data.items() if isinstance(v, dict) and v.get("preuve")
    }
    return flatten_answers(data), preuves


def _load_legacy_preuves(preuves_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"legacy_{preuves_path.parent.name}", preuves_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PREUVES


def migrate_directory(directory, answers_name="answers.json", preuves_name="preuves.py", path=CSV_PATH):
    """Fusionne un couple (answers plat, preuves.py) d'un dossier en un answers.json
    enrichi ; les anciens fichiers sont déplacés dans <directory>/legacy/."""
    directory = Path(directory)
    answers_file, preuves_file = directory / answers_name, directory / preuves_name
    with open(answers_file, encoding="utf-8") as f:
        answers = json.load(f)
    preuves = _load_legacy_preuves(preuves_file) if preuves_file.exists() else {}
    results = build_results(answers, preuves, path)
    legacy = directory / "legacy"
    legacy.mkdir(exist_ok=True)
    answers_file.replace(legacy / answers_name)
    if preuves_file.exists():
        preuves_file.replace(legacy / preuves_name)
    write_results(results, answers_file)
    return results


if __name__ == "__main__":
    for d in sys.argv[1:]:
        migrate_directory(d)
        print(f"Migré : {d}")
