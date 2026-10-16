# -*- coding: utf-8 -*-
"""
Chargement et interrogation des listes d'appartenance à des structures fédératives
d'éditeurs académiques (critère 12 et sous-critères), stockées dans
publisher_lists_data.json (cf. ce fichier pour la méthode de mise à jour).
"""
import json
import os
import unicodedata

_DATA_PATH = os.path.join(os.path.dirname(__file__), "publisher_lists_data.json")

with open(_DATA_PATH, encoding="utf-8") as _f:
    _LISTS = json.load(_f)


_LEADING_ARTICLES = ("the ", "les ", "la ", "le ", "l'", "der ", "die ", "das ")


def _normalize(name):
    """Normalise un nom d'éditeur pour une comparaison tolérante aux accents, à la casse,
    aux espaces multiples et aux articles initiaux ("The MIT Press" == "MIT Press" --
    erreur réellement rencontrée lors de la validation de ce module : la correspondance
    stricte manquait "The MIT Press" (nom exact dans la liste AUPresses) contre "MIT
    Press" (nom tel que retenu par Crossref pour Chaignon 2025), ce qui aurait fait
    manquer une appartenance pourtant déjà confirmée manuellement). Reste volontairement
    strict au-delà de ça (pas de résolution d'abréviations/sigles), pour éviter les faux
    positifs silencieux."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    normalized = " ".join(name.lower().split())
    for article in _LEADING_ARTICLES:
        if normalized.startswith(article):
            normalized = normalized[len(article):]
            break
    return normalized.strip()


def check_membership(publisher_name, list_key):
    """Vérifie si `publisher_name` figure dans la liste `list_key` (ex. "aeup", "aupresses",
    "une", "eulac", "library_publishing_coalition", "scholarled" -- cf.
    publisher_lists_data.json). Renvoie un tuple (verdict, evidence) où verdict vaut
    "Oui", "Non", ou "Indéterminé" (si la liste est vide/non renseignée -- pas de preuve
    disponible, distinct d'une vérification qui aurait conclu "Non")."""
    entry = _LISTS.get(list_key)
    if entry is None:
        raise KeyError(f"Liste inconnue : {list_key!r} (clés valides : {list(_LISTS)})")

    members = entry.get("members", [])
    target = _normalize(publisher_name)

    if not members:
        return (
            "Indéterminé",
            f"Liste « {entry['full_name']} » non renseignée dans ce projet "
            f"(coverage_caveat : {entry['coverage_caveat']})",
        )

    for member in members:
        if _normalize(member) == target:
            src = entry.get("source_url") or "source non renseignée"
            ver = entry.get("verified_on") or "date de vérification non renseignée"
            return (
                "Oui",
                f"« {publisher_name} » figure dans la liste des membres de "
                f"{entry['full_name']} (relevé le {ver} sur {src}).",
            )

    src = entry.get("source_url") or "source non renseignée"
    ver = entry.get("verified_on")
    if ver is None:
        # Liste non vérifiée à jour : un "Non" ici serait un faux négatif potentiel.
        return (
            "Indéterminé",
            f"« {publisher_name} » n'apparaît pas dans la liste partielle de "
            f"{entry['full_name']} actuellement enregistrée ({entry['coverage_caveat']}) "
            f"-- à vérifier directement sur {src} avant de conclure.",
        )
    return (
        "Non",
        f"« {publisher_name} » n'apparaît pas dans la liste des membres de "
        f"{entry['full_name']} relevée le {ver} sur {src}.",
    )


def check_any_federative_structure(publisher_name):
    """Vérifie l'appartenance à N'IMPORTE LAQUELLE des structures listées -- pour le
    critère générique 12 (« éditeur membre d'une structure fédérative reconnue »), qui se
    satisfait de l'appartenance à une seule d'entre elles. Renvoie (verdict, evidence,
    matched_list_key_or_None). Si au moins une liste renvoie "Oui", le résultat global est
    "Oui" ; si toutes renvoient "Non" (aucune "Indéterminé" parmi elles), le résultat est
    "Non" ; sinon (au moins une "Indéterminé" et aucun "Oui"), le résultat est
    "Indéterminé"."""
    any_indetermine = False
    for list_key in _LISTS:
        if list_key.startswith("_"):
            continue
        verdict, evidence = check_membership(publisher_name, list_key)
        if verdict == "Oui":
            return "Oui", evidence, list_key
        if verdict == "Indéterminé":
            any_indetermine = True
    if any_indetermine:
        return (
            "Indéterminé",
            f"Aucune appartenance confirmée pour « {publisher_name} » parmi les listes "
            f"renseignées, mais au moins une liste est incomplète -- voir le détail par "
            f"structure.",
            None,
        )
    return "Non", f"« {publisher_name} » n'apparaît dans aucune des listes renseignées.", None
