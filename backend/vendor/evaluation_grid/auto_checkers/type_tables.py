# -*- coding: utf-8 -*-
"""
Tables de correspondance "type de document renvoyé par une base" -> "id de critère de la
grille", extraites directement des libellés de criteres_grille_evaluation.csv (colonne
`critere`, sous-catégorie "Type de document").

Ces tables remplacent, pour chacun des ~85 critères concernés, un raisonnement du type
« quel critère de la grille correspond à ce type de document ? » par un simple accès
dict[type] -> id. Elles sont volontairement séparées des fonctions d'appel réseau
(sources.py) : une fois qu'on a le champ "type" renvoyé par une base (par API, ou même
relevé manuellement par un humain sur une base payante comme Scopus/WoS), la conversion en
id de critère ne nécessite plus aucune recherche ni lecture.

Une même notice peut avoir plusieurs types vrais simultanément d'après ces classifications
(rare, mais par ex. Crossref distingue "book" de "monograph" : un ouvrage à auteur unique
peut légitimement être typé "monograph" et non "book"). C'est pourquoi les fonctions de
checkers.py qui utilisent ces tables répondent "Oui" au SEUL id correspondant au type
effectivement renvoyé, et "Non" à tous les autres ids de la même famille (cf. la règle
« un seul type vrai à la fois » déjà appliquée manuellement lors des tests Chaignon/
Renisio & Sinthon/Gozlan).
"""

# --- OpenAlex : champ "type" de la notice work (api.openalex.org/works/...) -----------
# Critères 9.1 à 9.25 (modulateurs du critère-parent 9 "indexé dans OpenAlex").
OPENALEX_TYPE_TO_CRITERION = {
    "article": "9.1",
    "book": "9.2",
    "book-chapter": "9.3",
    "book-review": "9.4",
    "conference-abstract": "9.5",
    "conference-paper": "9.6",
    "data-paper": "9.7",
    "dataset": "9.8",
    "dissertation": "9.9",
    "editorial": "9.10",
    "erratum": "9.11",
    "letter": "9.12",
    "libguides": "9.13",
    "other": "9.14",
    "paratext": "9.15",
    "peer-review": "9.16",
    "preprint": "9.17",
    "reference-entry": "9.18",
    "report": "9.19",
    "retraction": "9.20",
    "review": "9.21",
    "software": "9.22",
    "software-paper": "9.23",
    "standard": "9.24",
    "supplementary-materials": "9.25",
}

# --- Crossref : champ "type" de la notice work (api.crossref.org/works/<doi>) ---------
# Critères 10.1 à 10.30 (modulateurs du critère-parent 10 "doté d'un DOI Crossref").
CROSSREF_TYPE_TO_CRITERION = {
    "book-section": "10.1",
    "monograph": "10.2",
    "report-component": "10.3",
    "report": "10.4",
    "peer-review": "10.5",
    "book-track": "10.6",
    "journal-article": "10.7",
    "book-part": "10.8",
    "other": "10.9",
    "book": "10.10",
    "journal-volume": "10.11",
    "book-set": "10.12",
    "reference-entry": "10.13",
    "proceedings-article": "10.14",
    "journal": "10.15",
    "component": "10.16",
    "book-chapter": "10.17",
    "proceedings-series": "10.18",
    "report-series": "10.19",
    "proceedings": "10.20",
    "database": "10.21",
    "standard": "10.22",
    "reference-book": "10.23",
    "posted-content": "10.24",
    "journal-issue": "10.25",
    "dissertation": "10.26",
    "grant": "10.27",
    "dataset": "10.28",
    "book-series": "10.29",
    "edited-book": "10.30",
}

# --- PubMed/Medline : champ PublicationType de la notice EFetch/ESummary --------------
# Critères 8.1 à 8.30 (modulateurs du critère-parent 8 "indexé dans Medline/PubMed").
# Une notice PubMed porte SOUVENT plusieurs PublicationType simultanément (ex. "Journal
# Article" + "Randomized Controlled Trial") : contrairement aux tables OpenAlex/Crossref
# ci-dessus, il est normal ici de répondre "Oui" à plusieurs ids à la fois.
PUBMED_PUBTYPE_TO_CRITERION = {
    "Journal Article": "8.1",
    "Case Reports": "8.2",
    "Comparative Study": "8.3",
    "Multicenter Study": "8.4",
    "Observational Study": "8.5",
    "Clinical Trial": "8.6",
    "Clinical Trial, Phase I": "8.7",
    "Clinical Trial, Phase II": "8.8",
    "Clinical Trial, Phase III": "8.9",
    "Clinical Trial, Phase IV": "8.10",
    "Controlled Clinical Trial": "8.11",
    "Randomized Controlled Trial": "8.12",
    "Pragmatic Clinical Trial": "8.13",
    "Evaluation Study": "8.14",
    "Meta-Analysis": "8.15",
    "Network Meta-Analysis": "8.16",
    "Systematic Review": "8.17",
    "Review": "8.18",
    "Practice Guideline": "8.19",
    "Guideline": "8.20",
    "Historical Article": "8.21",
    "Preprint": "8.22",
    "Editorial": "8.23",
    "Letter": "8.24",
    "Comment": "8.25",
    "Expression of Concern": "8.26",
    "Published Erratum": "8.27",
    "Retraction of Publication": "8.28",
    "Retracted Publication": "8.29",
    "Duplicate Publication": "8.30",
}

# --- Scopus : champ "Document Type" (pas d'API publique gratuite -- relevé manuel) -----
# Critères 6.1 à 6.16. Fournie pour convertir un relevé manuel (ou via un futur accès
# Scopus API with a key) en id de critère sans avoir à rechercher le bon numéro à chaque
# fois -- cf. check_scopus_doctype() dans checkers.py.
SCOPUS_DOCTYPE_TO_CRITERION = {
    "Article": "6.1",
    "Abstract Report": "6.2",
    "Book": "6.3",
    "Book Chapter": "6.4",
    "Conference Paper": "6.5",
    "Conference Review": "6.6",
    "Data Paper": "6.7",
    "Editorial": "6.8",
    "Erratum": "6.9",
    "Letter": "6.10",
    "Multimedia": "6.11",
    "Note": "6.12",
    "Report": "6.13",
    "Retracted": "6.14",
    "Review": "6.15",
    "Short Survey": "6.16",
}

# --- Web of Science : champ "Document Type" (pas d'API publique gratuite) -------------
# Critères 7.1 à 7.40.
WOS_DOCTYPE_TO_CRITERION = {
    "Article": "7.1",
    "Art Exhibit Review": "7.2",
    "Bibliography": "7.3",
    "Biographical-Item": "7.4",
    "Book": "7.5",
    "Book Chapter": "7.6",
    "Book Review": "7.7",
    "Correction": "7.8",
    "Dance Performance Review": "7.9",
    "Data Paper": "7.10",
    "Database Review": "7.11",
    "Early Access": "7.12",
    "Editorial Material": "7.13",
    "Excerpt": "7.14",
    "Expression of Concern": "7.15",
    "Fiction, Creative Prose": "7.16",
    "Film Review": "7.17",
    "Hardware Review": "7.18",
    "Item Withdrawal": "7.19",
    "Letter": "7.20",
    "Meeting": "7.21",
    "Meeting Abstract": "7.22",
    "Meeting Summary": "7.23",
    "Music Performance Review": "7.24",
    "Music Score": "7.25",
    "Music Score Review": "7.26",
    "News Item": "7.27",
    "Poetry": "7.28",
    "Proceedings Paper": "7.29",
    "Publication with Expression of Concern": "7.30",
    "Record Review": "7.31",
    "Reprint": "7.32",
    "Retracted Publication": "7.33",
    "Retraction": "7.34",
    "Review": "7.35",
    "Script": "7.36",
    "Software Review": "7.37",
    "Theater Review": "7.38",
    "TV Review, Radio Review": "7.39",
    "Withdrawn Publication": "7.40",
}


def invert_unique(table):
    """Inverse une table {source_value: id} en {id: source_value}, pour retrouver la
    valeur attendue d'une base à partir d'un id de critère (utile pour construire des cas
    de test ou des messages d'erreur explicites)."""
    return {v: k for k, v in table.items()}
