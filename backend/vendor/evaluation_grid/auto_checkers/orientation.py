# -*- coding: utf-8 -*-
"""
Adapte les verdicts des checkers à la formulation des critères d'une grille donnée.

Les checkers (checkers.py) répondent au fait AFFIRMATIF : « le travail est-il rétracté »,
« la revue figure-t-elle dans… », « publié depuis au moins 6 mois ». Les grilles ne
formulent pas toutes leurs critères dans ce sens : la grille du 30/09/2026 écrit 30 « Le
travail est-il exempt d'avis de rétractation ? » et 53 « Aucun des auteurs n'a-t-il… »,
la grille canonique écrit 62 « publié depuis moins de 6 mois ». Pour ces critères,
orient() inverse Oui/Non ; la preuve, qui décrit le fait constaté, ne change pas.

Un même id peut aussi avoir changé de sens d'une grille à l'autre (ex. 46 : « mention de
résultats précédents » dans la grille canonique, « au moins une référence
bibliographique » dans celle du 30/09/2026). TEXT_GUARDS n'applique alors un checker qu'aux
grilles dont le libellé correspond à ce qu'il vérifie.
"""
from grille.parameters import parse_parameters
from grille.results import FLIP, is_complement_wording

from .checkers import AutoResult

# id -> fragment de libellé requis pour que le checker s'applique.
TEXT_GUARDS = {
    "1.4": "Moins de N rapports de relecture",
    "1.5": "inférieur à N jours",
    "22": "évaluation publique",
    "46": "référence bibliographique",
}


def orient(results, criteria):
    """results : {id: AutoResult} au sens affirmatif ; criteria : grille chargée
    (score_engine.load_grid). Renvoie {id: AutoResult} limité aux critères de la grille,
    verdicts inversés pour les critères formulés négativement."""
    oriented = {}
    for crit_id, result in results.items():
        row = criteria.get(crit_id)
        if row is None:
            continue
        text = row.get("critere") or ""
        guard = TEXT_GUARDS.get(crit_id)
        if guard and guard not in text:
            oriented[crit_id] = AutoResult(
                None, f"Libellé du critère {crit_id} différent dans cette grille (attendu : « {guard} »).",
                result.confidence,
            )
            continue
        if result.verdict in FLIP and is_complement_wording(text):
            result = result._replace(verdict=FLIP[result.verdict])
        oriented[crit_id] = result
    return oriented


def grid_parameters(row):
    """Seuils paramétrables d'un critère (colonne `parametre`, ex. « N = 30 % ; M = 10
    citations ») : {"N": 30.0, "M": 10.0}. Dict vide si la colonne est absente ou vide."""
    return parse_parameters(row.get("parametre"))
