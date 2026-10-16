# -*- coding: utf-8 -*-
"""
Accès local à la Retraction Watch Database (critères 37, 54 à 60).

L'API REST Crossref signale les rétractations et expressions of concern relevées par
Retraction Watch (champ updated-by, cf. checkers._crossref_update_check), mais pas leurs
MOTIFS (« Reason »). Ceux-ci figurent dans l'export CSV public et gratuit de la base,
publié par Crossref (https://gitlab.com/crossref/retraction-watch-data), à télécharger
périodiquement. Indiquer son chemin dans la variable d'environnement RETRACTION_WATCH_CSV
(ou dans le fichier .env) ; sans elle, les critères concernés restent hors de portée.

Colonnes utilisées : OriginalPaperDOI, Reason (motifs préfixés par « + » et séparés par
« ; »), RetractionNature (Retraction, Expression of concern, Correction…).
"""
import csv
import os
from collections import defaultdict

ENV_VAR = "RETRACTION_WATCH_CSV"


def load_index(path=None):
    """{doi en minuscules: [lignes RW]} à partir du CSV, ou None si aucun fichier n'est
    configuré ou lisible."""
    path = path or os.environ.get(ENV_VAR)
    if not path or not os.path.exists(path):
        return None
    index = defaultdict(list)
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            doi = (row.get("OriginalPaperDOI") or "").strip().lower()
            if doi and doi != "unavailable":
                index[doi].append(row)
    return dict(index)


def entries_for(index, doi):
    """Notices RW d'un DOI (liste éventuellement vide), ou None si l'index est absent."""
    if index is None:
        return None
    return index.get(doi.strip().lower(), [])
