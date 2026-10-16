# -*- coding: utf-8 -*-
"""
Fonctions de décision automatique par critère : à partir des données brutes renvoyées par
sources.py (notices OpenAlex/Crossref/DOAJ/HAL/PubMed/theses.fr), chaque fonction
`check_<id>(...)` renvoie un AutoResult(verdict, evidence, confidence) pour UN critère de
la grille, sans aucune étape de lecture ou d'interprétation libre : uniquement des accès à
des champs structurés, des comparaisons de dates/nombres, et des correspondances de table
(type_tables.py, publisher_lists.py).

Convention de verdict, identique à celle utilisée dans answers_*.json pour les trois
travaux déjà testés (Chaignon 2025, Renisio & Sinthon 2014, Gozlan 2020) :
  - "Oui" / "Non"       : réponse positive/négative avec preuve directe.
  - "Indéterminé"       : la source consultée ne permet pas de trancher (absence
                            d'information, et non readout négatif).
  - None (verdict)      : le critère est structurellement hors de portée de cette source
                            (ex. demander le facteur SJR d'une revue à une API qui ne
                            connaît pas SJR) -- distinct d'« Indéterminé », qui signifie
                            « la bonne source a été interrogée mais n'a pas su répondre ».

`confidence` vaut "haute" (champ structuré explicite, ex. type Crossref) ou "heuristique"
(inférence indirecte, ex. déduire l'anglais du travail à partir du seul champ `language`)
-- à faire apparaître dans le fichier de preuves généré, pour que l'évaluateur humain sache
où porter son attention en priorité s'il relit les résultats.
"""
import re
from collections import namedtuple
from datetime import date, datetime

from . import sources
from .type_tables import (
    CROSSREF_TYPE_TO_CRITERION,
    OPENALEX_TYPE_TO_CRITERION,
    PUBMED_PUBTYPE_TO_CRITERION,
)
from .publisher_lists import check_any_federative_structure, check_membership

AutoResult = namedtuple("AutoResult", ["verdict", "evidence", "confidence"])


def _oa_work(oa):
    """Accès sûr, quelle que soit la présence des sous-champs, à une notice OpenAlex."""
    return oa or {}


# ---------------------------------------------------------------------------------------
# Accès ouvert (critères 4, 4.1, 4.1.1) -- source : OpenAlex
# ---------------------------------------------------------------------------------------

def check_4_open_access(oa_work):
    """4 : La publication est-elle en libre accès, à un titre ou un autre ?"""
    oa = _oa_work(oa_work).get("open_access") or _oa_work(oa_work).get("is_oa") or {}
    is_oa = oa.get("is_oa")
    if is_oa is None:
        return AutoResult(None, "Champ open_access absent de la notice OpenAlex.", "haute")
    status = oa.get("oa_status", "?")
    url = oa.get("oa_url", "")
    verdict = "Oui" if is_oa else "Non"
    return AutoResult(
        verdict,
        f"OpenAlex : open_access.is_oa={is_oa}, oa_status=\"{status}\""
        + (f", oa_url={url}" if url else "") + ".",
        "haute",
    )


def check_4_1_gold(oa_work):
    """4.1 : En libre accès chez l'éditeur (voie dorée) et non en dépôt seul (voie verte)."""
    oa = _oa_work(oa_work).get("open_access") or _oa_work(oa_work).get("is_oa") or {}
    status = oa.get("oa_status")
    url = oa.get("oa_url", "")
    if status is None:
        return AutoResult(None, "oa_status absent.", "haute")
    if status in ("gold", "hybrid"):
        return AutoResult("Oui", f"OpenAlex oa_status=\"{status}\" (accès chez l'éditeur).", "haute")
    if status == "green":
        # NE PAS conclure "Non" ici -- trouvé lors de la validation contre le cas Gozlan
        # (2020) : OpenAlex classe la version ouverte d'un livre ENS Éditions/OpenEdition
        # (Freemium, HTML gratuit chez l'éditeur lui-même, PDF/ePub payants) comme "green"
        # au même titre qu'un simple dépôt en archive tierce -- alors que la réponse
        # retenue manuellement pour ce critère était "Oui" (accès chez l'éditeur). Le champ
        # oa_status ne distingue donc pas de façon fiable "dépôt en archive tierce" de
        # "diffusion Freemium par l'éditeur lui-même" : laisser trancher un humain.
        return AutoResult(
            "Indéterminé",
            f"OpenAlex oa_status=\"green\" : ambigu entre un simple dépôt en archive "
            f"tierce (voie verte classique, répondrait \"Non\" ici) et une diffusion "
            f"Freemium par l'éditeur lui-même sur sa propre plateforme (répondrait "
            f"\"Oui\" -- cas réel rencontré avec Gozlan 2020/ENS Éditions/OpenEdition) : "
            f"vérifier manuellement qui héberge oa_url (\"{url}\").",
            "heuristique",
        )
    if status in ("bronze", "closed"):
        return AutoResult("Non", f"OpenAlex oa_status=\"{status}\".", "haute")
    return AutoResult("Indéterminé", f"oa_status inattendu : {status!r}.", "haute")


def check_4_1_1_diamond_or_full_gold(oa_work, crossref_license=None):
    """4.1.1 : Revue intégralement en accès ouvert (gold pur), plutôt qu'hybride.
    OpenAlex ne distingue pas directement "gold pur" de "hybride" au niveau de la notice
    work -- il faut consulter le champ source.is_oa de la revue elle-même (si le travail
    est publié dans une revue plutôt qu'une plateforme de livre)."""
    source = (
        _oa_work(oa_work).get("primary_location", {}) or {}
    ).get("source") or {}
    source_is_oa = source.get("is_oa")
    source_type = source.get("type")
    if source_is_oa is None:
        return AutoResult(
            "Indéterminé",
            "primary_location.source.is_oa absent de la notice OpenAlex -- vérifier "
            "manuellement le statut de la revue (gold pur vs hybride).",
            "haute",
        )
    if source_type != "journal":
        return AutoResult(
            None,
            f"primary_location.source.type=\"{source_type}\" (pas une revue) -- ce "
            f"critère, formulé pour des revues, ne s'applique pas directement ; traiter "
            f"manuellement pour un ouvrage/une plateforme.",
            "haute",
        )
    verdict = "Oui" if source_is_oa else "Non"
    return AutoResult(
        verdict,
        f"OpenAlex primary_location.source.is_oa={source_is_oa} pour la revue "
        f"\"{source.get('display_name', '?')}\".",
        "haute",
    )


# ---------------------------------------------------------------------------------------
# Type de publication (critères 5, 26) -- source : OpenAlex
# ---------------------------------------------------------------------------------------

def check_5_journal(oa_work):
    """5 : Le travail a-t-il été publié dans une revue académique ?"""
    source = (
        _oa_work(oa_work).get("primary_location", {}) or {}
    ).get("source") or {}
    source_type = source.get("type")
    if source_type is None:
        return AutoResult(None, "primary_location.source.type absent.", "haute")
    verdict = "Oui" if source_type == "journal" else "Non"
    return AutoResult(
        verdict,
        f"OpenAlex primary_location.source.type=\"{source_type}\" "
        f"(source : \"{source.get('display_name', '?')}\").",
        "haute",
    )


def check_26_book(oa_work):
    """26 : Le travail a-t-il été publié sous forme d'ouvrage (monographie/collectif) ?"""
    work_type = _oa_work(oa_work).get("type")
    if work_type is None:
        return AutoResult(None, "Champ type absent.", "haute")
    verdict = "Oui" if work_type in ("book", "book-chapter") else "Non"
    return AutoResult(verdict, f"OpenAlex type=\"{work_type}\".", "haute")


def check_26_1_monograph_not_chapter(oa_work):
    """26.1 : S'agit-il d'une monographie plutôt que d'un chapitre au sein d'un collectif ?"""
    work_type = _oa_work(oa_work).get("type")
    if work_type not in ("book", "book-chapter"):
        return AutoResult(None, f"type=\"{work_type}\" -- 26 lui-même n'est pas \"Oui\".", "haute")
    verdict = "Oui" if work_type == "book" else "Non"
    return AutoResult(verdict, f"OpenAlex type=\"{work_type}\".", "haute")


# ---------------------------------------------------------------------------------------
# Type de document détaillé (critères 9.x, 10.x, 8.x) -- tables génériques
# ---------------------------------------------------------------------------------------

def check_9_x_family(oa_work):
    """9.1 à 9.25 : type de document précis dans OpenAlex. Renvoie un dict {id: AutoResult}
    pour TOUTE la famille en une seule passe -- un seul type est "Oui", les 24 autres
    "Non", à partir d'un seul appel réseau déjà effectué (oa_work)."""
    work_type = _oa_work(oa_work).get("type")
    results = {}
    matched_id = OPENALEX_TYPE_TO_CRITERION.get(work_type) if work_type else None
    for oa_type, crit_id in OPENALEX_TYPE_TO_CRITERION.items():
        if work_type is None:
            results[crit_id] = AutoResult(None, "Champ type OpenAlex absent.", "haute")
        elif crit_id == matched_id:
            results[crit_id] = AutoResult("Oui", f"OpenAlex type=\"{work_type}\".", "haute")
        else:
            results[crit_id] = AutoResult(
                "Non", f"OpenAlex type=\"{work_type}\" (≠ \"{oa_type}\").", "haute"
            )
    return results


def check_10_x_family(cr_work):
    """10.1 à 10.30 : type de document précis dans Crossref. Même principe que
    check_9_x_family, sur le champ "type" de la notice Crossref."""
    work_type = (cr_work or {}).get("type")
    results = {}
    matched_id = CROSSREF_TYPE_TO_CRITERION.get(work_type) if work_type else None
    for cr_type, crit_id in CROSSREF_TYPE_TO_CRITERION.items():
        if work_type is None:
            results[crit_id] = AutoResult(None, "Champ type Crossref absent.", "haute")
        elif crit_id == matched_id:
            results[crit_id] = AutoResult("Oui", f"Crossref type=\"{work_type}\".", "haute")
        else:
            results[crit_id] = AutoResult(
                "Non", f"Crossref type=\"{work_type}\" (≠ \"{cr_type}\").", "haute"
            )
    return results


def check_8_x_family(pubmed_types):
    """8.1 à 8.30 : PublicationType PubMed/Medline. Contrairement aux deux familles
    ci-dessus, PLUSIEURS valeurs peuvent être simultanément vraies (une notice PubMed a
    souvent 2-3 PublicationType). `pubmed_types` est la liste renvoyée par
    sources.pubmed_publication_types(), ou None si le travail n'est pas indexé."""
    results = {}
    types_set = set(pubmed_types or [])
    for pt, crit_id in PUBMED_PUBTYPE_TO_CRITERION.items():
        if pubmed_types is None:
            results[crit_id] = AutoResult(
                None, "Travail non indexé dans PubMed (critère 8 = Non) -- sans objet.", "haute"
            )
        elif pt in types_set:
            results[crit_id] = AutoResult("Oui", f"PubMed PublicationType inclut \"{pt}\".", "haute")
        else:
            results[crit_id] = AutoResult("Non", f"PubMed PublicationType ne contient pas \"{pt}\".", "haute")
    return results


# ---------------------------------------------------------------------------------------
# Trouvabilité / métadonnées (critères 10, 11) -- OpenAlex + Crossref
# ---------------------------------------------------------------------------------------

def check_10_has_doi(cr_work, oa_work=None):
    """10 : Le travail est-il doté d'un DOI Crossref ?"""
    if cr_work and cr_work.get("DOI"):
        return AutoResult("Oui", f"Crossref DOI={cr_work['DOI']}.", "haute")
    oa_doi = _oa_work(oa_work).get("doi")
    if oa_doi:
        return AutoResult(
            "Oui",
            f"DOI présent dans la notice OpenAlex ({oa_doi}) bien que la notice Crossref "
            f"n'ait pas pu être récupérée directement.",
            "heuristique",
        )
    return AutoResult("Non", "Aucun DOI trouvé dans les notices Crossref/OpenAlex consultées.", "haute")


def check_11_metadata_open(oa_work, cr_work=None):
    """11 : Les métadonnées (y compris le résumé) sont-elles librement accessibles ?
    Approximé par la présence d'un résumé structuré dans OpenAlex (lui-même agrégé à
    partir de sources ouvertes) et/ou dans Crossref."""
    has_abstract_oa = bool(_oa_work(oa_work).get("abstract_inverted_index"))
    has_abstract_cr = bool((cr_work or {}).get("abstract"))
    if has_abstract_oa or has_abstract_cr:
        src = "OpenAlex" if has_abstract_oa else "Crossref"
        return AutoResult(
            "Oui",
            f"Un résumé structuré est exposé publiquement par l'API {src} pour ce "
            f"travail (métadonnées donc librement accessibles même si le texte intégral "
            f"peut rester payant).",
            "heuristique",
        )
    # L'absence de résumé exposé ne prouve pas l'absence d'accès aux métadonnées de base
    # (titre, auteurs, DOI) : rester prudent plutôt que de répondre "Non".
    return AutoResult(
        "Indéterminé",
        "Aucun résumé structuré trouvé via OpenAlex/Crossref -- les métadonnées de base "
        "(titre, auteurs, DOI) sont presque toujours publiques, mais l'absence de résumé "
        "exposé ne permet pas de conclure avec certitude sur ce critère précis sans "
        "vérification manuelle de la page éditeur.",
        "heuristique",
    )


# ---------------------------------------------------------------------------------------
# Financement (critère 13) -- Crossref
# ---------------------------------------------------------------------------------------

def check_13_funding(cr_work):
    """13 : Le travail est-il financé dans le cadre d'un projet national/international ?
    Crossref expose un champ "funder" quand l'éditeur l'a déclaré -- couverture partielle
    (de nombreux éditeurs, notamment en SHS francophone, ne déclarent pas ce champ même
    quand un financement existe réellement : un "Non"/"Indéterminé" ici est donc plus
    fragile qu'un "Oui")."""
    funders = (cr_work or {}).get("funder") or []
    if funders:
        names = ", ".join(f.get("name", "?") for f in funders)
        return AutoResult("Oui", f"Crossref funder déclaré(s) : {names}.", "haute")
    return AutoResult(
        "Indéterminé",
        "Aucun financeur déclaré dans le champ funder de Crossref -- ce champ n'est "
        "renseigné par l'éditeur que sur une base volontaire ; son absence ne prouve pas "
        "l'absence de financement (vérifier les remerciements du texte intégral si "
        "disponible).",
        "heuristique",
    )


# ---------------------------------------------------------------------------------------
# Collaborations et profil des auteurs (critères 14.x, 15.x, 16) -- OpenAlex
# ---------------------------------------------------------------------------------------

def check_14_multiple_authors(oa_work):
    """14 : Le travail compte-t-il plusieurs auteurs ?"""
    authorships = _oa_work(oa_work).get("authorships") or []
    n = len(authorships)
    verdict = "Oui" if n > 1 else "Non"
    return AutoResult(verdict, f"OpenAlex authorships : {n} auteur(s) recensé(s).", "haute")


def _institutions_of(authorships):
    names = set()
    countries = set()
    for a in authorships or []:
        for inst in a.get("institutions") or []:
            if inst.get("display_name"):
                names.add(inst["display_name"])
            if inst.get("country_code"):
                countries.add(inst["country_code"])
    return names, countries


def check_14_1_multiple_research_groups(oa_work):
    """14.1 : Collaboration entre plusieurs collectifs de recherche différents ?
    Approximé par le nombre d'institutions distinctes (>1) recensées sur l'ensemble des
    auteurs -- une approximation raisonnable mais imparfaite d'un "collectif de recherche"
    au sens strict (équipe/laboratoire), qui n'est pas un champ structuré des API."""
    names, _ = _institutions_of(_oa_work(oa_work).get("authorships"))
    if not names:
        return AutoResult("Indéterminé", "Aucune institution renseignée dans les authorships.", "heuristique")
    verdict = "Oui" if len(names) > 1 else "Non"
    return AutoResult(
        verdict,
        f"{len(names)} institution(s) distincte(s) recensée(s) : {', '.join(sorted(names))}.",
        "heuristique",
    )


def check_14_2_multiple_institutions(oa_work):
    """14.2 : Collaboration entre plusieurs institutions différentes ? (même champ que
    14.1 dans les données OpenAlex disponibles -- les deux critères ne sont, en pratique,
    distingués qu'en théorie par cette source)."""
    return check_14_1_multiple_research_groups(oa_work)


def check_14_4_multiple_countries(oa_work):
    """14.4 : Collaboration entre plusieurs pays différents ?"""
    _, countries = _institutions_of(_oa_work(oa_work).get("authorships"))
    if not countries:
        return AutoResult("Indéterminé", "Aucun pays d'affiliation renseigné.", "heuristique")
    verdict = "Oui" if len(countries) > 1 else "Non"
    return AutoResult(verdict, f"Pays d'affiliation recensés : {', '.join(sorted(countries))}.", "haute")


RESEARCH_INSTITUTION_TYPES = ("education", "facility")


def check_16_institutional_affiliation(oa_work):
    """16 : Au moins un des auteurs a-t-il une affiliation à une institution de type
    « education » ou « facility » selon ROR ? (grille du 30/09/2026 ; « établissement de
    recherche » dans la grille canonique). Le type ROR est lu dans
    authorships[].institutions[].type d'OpenAlex ; une notice sans type d'institution
    retombe sur l'ancien test (au moins une institution recensée, confiance heuristique).
    ATTENTION (trouvé lors de la validation contre le cas Gozlan 2020) : le lien
    auteur-institution d'OpenAlex est fréquemment incomplet pour les ouvrages/monographies
    en SHS (authorships[].institutions renvoie une liste vide alors que l'autrice était en
    réalité affiliée au CSO/Sciences Po au moment de la publication -- affiliation
    confirmée manuellement via son profil institutionnel, absente d'OpenAlex). Une liste
    vide ne doit donc PAS être lue comme "Non" mais comme "Indéterminé"."""
    institutions = [
        inst for a in _oa_work(oa_work).get("authorships") or [] for inst in a.get("institutions") or []
    ]
    typed = {inst.get("display_name", "?"): inst.get("type") for inst in institutions if inst.get("type")}
    matching = sorted(name for name, t in typed.items() if t in RESEARCH_INSTITUTION_TYPES)
    if matching:
        return AutoResult(
            "Oui", f"Institution(s) de type education/facility (ROR, via OpenAlex) : {', '.join(matching)}.", "haute"
        )
    if typed and len(typed) == len({inst.get("display_name") for inst in institutions}):
        listing = ", ".join(f"{name} ({t})" for name, t in sorted(typed.items()))
        return AutoResult("Non", f"Aucune institution de type education/facility : {listing}.", "haute")
    names, _ = _institutions_of(_oa_work(oa_work).get("authorships"))
    if names:
        return AutoResult(
            "Oui",
            f"Institution(s) recensée(s) dans OpenAlex (type ROR non renseigné) : {', '.join(sorted(names))}.",
            "heuristique",
        )
    return AutoResult(
        "Indéterminé",
        "Aucune institution recensée dans les authorships OpenAlex -- ce champ est "
        "fréquemment incomplet pour les ouvrages/monographies (cf. cas Gozlan 2020) : "
        "absence de lien ≠ absence d'affiliation réelle. Vérifier le profil de l'auteur "
        "(ORCID, page institutionnelle) avant de conclure \"Non\".",
        "heuristique",
    )


def check_15_other_publications(author_record):
    """15 : Le ou les auteurs ont-ils produit d'autres publications scientifiques ?
    `author_record` = notice OpenAlex author (sources.openalex_author) ; works_count > 1
    signifie qu'il existe au moins un autre travail que celui évalué."""
    if not author_record:
        return AutoResult("Indéterminé", "Notice auteur OpenAlex non trouvée.", "haute")
    works_count = author_record.get("works_count", 0)
    verdict = "Oui" if works_count > 1 else "Non"
    return AutoResult(
        verdict,
        f"OpenAlex author.works_count={works_count} pour "
        f"{author_record.get('display_name', '?')}.",
        "haute",
    )


def check_15_2_has_doctorate(theses_result):
    """15.2 : Le ou les auteurs sont-ils auteurs d'une thèse de doctorat ?
    `theses_result` = réponse de sources.theses_fr_search_person(). Ne concerne que les
    auteurs susceptibles d'avoir soutenu en France -- pour un auteur non-francophone,
    laisser ce critère à "Indéterminé" (source hors périmètre) plutôt que d'appeler cette
    fonction."""
    if not theses_result:
        return AutoResult(None, "Réponse theses.fr absente/vide.", "haute")
    results = theses_result.get("results") or theses_result.get("data") or []
    if results:
        return AutoResult(
            "Oui",
            f"{len(results)} thèse(s) trouvée(s) sur theses.fr pour cette recherche -- "
            f"VÉRIFIER l'homonymie (nom seul) avant de valider.",
            "heuristique",
        )
    return AutoResult(
        "Indéterminé",
        "Aucune thèse trouvée sur theses.fr pour cette recherche -- l'auteur n'a "
        "peut-être pas soutenu en France, ou le nom recherché ne correspond pas "
        "exactement à la forme indexée.",
        "heuristique",
    )


# ---------------------------------------------------------------------------------------
# Dépôt en archive ouverte (critère 2) -- HAL
# ---------------------------------------------------------------------------------------

def check_2_hal_deposit(hal_result):
    """2 : La publication est-elle déposée en preprint dans une archive ouverte ?"""
    if hal_result is None:
        return AutoResult(None, "Requête HAL non aboutie.", "haute")
    n = (hal_result.get("response") or {}).get("numFound", 0)
    if n > 0:
        docs = hal_result["response"].get("docs", [])
        hal_ids = ", ".join(d.get("halId_s", "?") for d in docs)
        return AutoResult("Oui", f"{n} notice(s) HAL trouvée(s) pour ce DOI : {hal_ids}.", "haute")
    return AutoResult("Non", "Aucune notice HAL trouvée pour ce DOI.", "haute")


# ---------------------------------------------------------------------------------------
# Indexation DOAJ (critère 5.9)
# ---------------------------------------------------------------------------------------

def check_5_9_doaj(doaj_result):
    """5.9 : La revue est-elle indexée dans DOAJ ?"""
    if doaj_result is None:
        return AutoResult(None, "Requête DOAJ non aboutie.", "haute")
    total = doaj_result.get("total", 0)
    verdict = "Oui" if total > 0 else "Non"
    return AutoResult(verdict, f"DOAJ : {total} revue(s) trouvée(s) pour cet ISSN.", "haute")


# ---------------------------------------------------------------------------------------
# Éditeur membre d'une structure fédérative (critère 12 et sous-critères)
# ---------------------------------------------------------------------------------------

def check_12_federative_structure(publisher_name):
    """12 : Éditeur membre d'une structure fédérative d'éditeurs académiques reconnue ?"""
    verdict, evidence, _ = check_any_federative_structure(publisher_name)
    return AutoResult(verdict, evidence, "haute")


def check_12_x_specific(publisher_name, list_key):
    verdict, evidence = check_membership(publisher_name, list_key)
    return AutoResult(verdict, evidence, "haute")


# ---------------------------------------------------------------------------------------
# Rétractation (critère 30) -- Crossref update-to
# ---------------------------------------------------------------------------------------

def _crossref_update_check(cr_work, types, label):
    """Cherche dans la notice Crossref du travail un avis de l'un des `types` donnés.
    `updated-by` (porté par le travail mis à jour) inclut, depuis l'intégration de la
    Retraction Watch Database à l'API Crossref, les avis relevés par Retraction Watch
    (source "retraction-watch") en plus de ceux déclarés par l'éditeur (CrossMark) :
    l'absence de tout avis y vaut donc "Non". `update-to` est conservé par compatibilité
    (il est en principe porté par la notice de l'avis, pas par le travail)."""
    if not cr_work:
        return AutoResult(None, "Notice Crossref indisponible.", "haute")
    notices = [
        u for field in ("updated-by", "update-to") for u in cr_work.get(field) or []
        if (u.get("type") or "").lower() in types
    ]
    if notices:
        described = "; ".join(
            f"{u.get('type')} {u.get('DOI', '')} (source : {u.get('source', 'éditeur')})".strip() for u in notices
        )
        return AutoResult("Oui", f"Crossref signale un avis de type {label} : {described}.", "haute")
    return AutoResult(
        "Non",
        f"Aucun avis de type {label} dans la notice Crossref (champ updated-by, qui intègre "
        f"les avis de la Retraction Watch Database).",
        "haute",
    )


def check_30_retraction(cr_work):
    """30 : Le travail fait-il l'objet d'un avis de rétractation ? (fait affirmatif ; la
    grille du 30/09/2026 le formule « exempt d'avis de rétractation », cf. orientation.py)."""
    return _crossref_update_check(cr_work, ("retraction", "withdrawal", "removal"), "rétractation")


def check_31_expression_of_concern(cr_work):
    """31 : Le travail fait-il l'objet d'une expression of concern ?"""
    return _crossref_update_check(cr_work, ("expression_of_concern", "expression-of-concern"), "expression of concern")


def check_31_1_correction(cr_work):
    """31.1 : Le travail a-t-il fait l'objet d'au moins une correction publiée ?"""
    return _crossref_update_check(
        cr_work, ("correction", "erratum", "corrigendum", "addendum"), "correction/erratum"
    )


# ---------------------------------------------------------------------------------------
# Langue (critères 40, 41) -- OpenAlex
# ---------------------------------------------------------------------------------------

def check_40_41_english(oa_work):
    """40/41 : Titre/résumé en anglais ? Approximé par le champ `language` de la notice
    OpenAlex (langue principale déclarée du travail) -- une seule vérification sert aux
    deux critères, le titre et le résumé étant presque toujours dans la même langue."""
    lang = _oa_work(oa_work).get("language")
    if lang is None:
        return AutoResult(None, "Champ language absent.", "haute")
    verdict = "Oui" if lang == "en" else "Non"
    return AutoResult(verdict, f"OpenAlex language=\"{lang}\".", "heuristique")


# ---------------------------------------------------------------------------------------
# Ancienneté (critères 62, 63, 64) -- calcul de date pur, aucune API nécessaire
# ---------------------------------------------------------------------------------------

def check_age_criteria(publication_date_str, today=None):
    """62/63/64 : Publié depuis AU MOINS 6 mois / 2 ans / 10 ans (formulation de la grille
    du 30/09/2026). La grille canonique formule 62 et 63 « depuis moins de… » :
    orientation.py inverse alors la réponse. Renvoie un dict
    {id: AutoResult}. `publication_date_str` : "AAAA-MM-JJ" ou "AAAA" (année seule, auquel
    cas le 1er janvier est supposé -- cf. comportement d'OpenAlex.publication_date)."""
    today = today or date.today()
    if not publication_date_str:
        msg = "Date de publication absente."
        return {cid: AutoResult(None, msg, "haute") for cid in ("62", "63", "64")}
    try:
        if len(publication_date_str) == 4:
            pub_date = date(int(publication_date_str), 1, 1)
        else:
            pub_date = datetime.strptime(publication_date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        msg = f"Date de publication non interprétable : {publication_date_str!r}."
        return {cid: AutoResult(None, msg, "haute") for cid in ("62", "63", "64")}

    age_days = (today - pub_date).days
    evidence = f"Date de publication {pub_date.isoformat()}, date du test {today.isoformat()} -> {age_days} jours."
    return {
        "62": AutoResult("Oui" if age_days >= 182 else "Non", evidence, "haute"),
        "63": AutoResult("Oui" if age_days >= 730 else "Non", evidence, "haute"),
        "64": AutoResult("Oui" if age_days >= 3650 else "Non", evidence, "haute"),
    }


# ---------------------------------------------------------------------------------------
# Citations (critères 65, 66, 69, 73) -- OpenAlex
# ---------------------------------------------------------------------------------------

def check_65_has_citation(oa_work):
    """65 : Le travail a-t-il reçu au moins une citation ?"""
    n = _oa_work(oa_work).get("cited_by_count")
    if n is None:
        return AutoResult(None, "cited_by_count absent.", "haute")
    return AutoResult("Oui" if n >= 1 else "Non", f"OpenAlex cited_by_count={n}.", "haute")


def check_69_ten_citations(oa_work, cr_work=None):
    """69 : Le travail a-t-il reçu au moins dix citations ?
    ATTENTION (trouvé lors de la validation contre le cas Gozlan 2020, où OpenAlex
    indiquait 9 citations et Crossref 10 -- un désaccord pile sur le seuil de ce critère) :
    ne se fier à une seule source est fragile exactement autour de ce seuil. Quand les deux
    comptes sont disponibles et ne s'accordent pas sur le côté du seuil, la réponse la plus
    honnête est "Indéterminé" plutôt qu'un choix arbitraire d'une source contre l'autre."""
    n_oa = _oa_work(oa_work).get("cited_by_count")
    n_cr = (cr_work or {}).get("is-referenced-by-count")
    if n_oa is None and n_cr is None:
        return AutoResult(None, "Aucun compte de citations disponible.", "haute")
    if n_oa is not None and n_cr is not None and (n_oa >= 10) != (n_cr >= 10):
        return AutoResult(
            "Indéterminé",
            f"Désaccord entre sources de part et d'autre du seuil : OpenAlex "
            f"cited_by_count={n_oa}, Crossref is-referenced-by-count={n_cr}.",
            "heuristique",
        )
    n = n_oa if n_oa is not None else n_cr
    src = "OpenAlex cited_by_count" if n_oa is not None else "Crossref is-referenced-by-count"
    return AutoResult("Oui" if n >= 10 else "Non", f"{src}={n}.", "haute")


def check_66_external_citation(oa_work, citing_works_result):
    """66 : Citation par des auteurs extérieurs au travail lui-même ?
    Compare le jeu d'auteurs (OpenAlex author id, à défaut nom) du travail évalué à ceux
    des travaux citants (citing_works_result = sources.openalex_citing_works())."""
    own_authors = {
        a.get("author", {}).get("id") or a.get("author_name")
        for a in _oa_work(oa_work).get("authorships") or []
    }
    if not own_authors:
        return AutoResult(None, "Impossible de déterminer les auteurs du travail évalué.", "haute")
    if citing_works_result is None:
        return AutoResult(None, "Requête des travaux citants non aboutie.", "haute")
    citing = citing_works_result.get("results") or []
    own_cited_by_count = _oa_work(oa_work).get("cited_by_count", 0)
    if not citing:
        if own_cited_by_count >= 1:
            # Incohérence : cited_by_count>0 mais la recherche des travaux citants ne
            # renvoie rien (retard d'indexation entre les deux endpoints OpenAlex, ou
            # citation par un type de document non couvert par ce filtre) -- ne pas
            # conclure "Non" sur une base contradictoire.
            return AutoResult(
                "Indéterminé",
                f"Incohérence : cited_by_count={own_cited_by_count} mais la recherche "
                f"des travaux citants (filter=cites:...) ne renvoie aucun résultat -- "
                f"probable retard d'indexation entre les deux endpoints OpenAlex ; "
                f"vérifier manuellement.",
                "heuristique",
            )
        return AutoResult(
            "Non", "Aucun travail citant trouvé (cohérent avec cited_by_count=0).", "haute"
        )
    for c in citing:
        citing_authors = {
            a.get("author", {}).get("id") or a.get("author_name")
            for a in c.get("authorships") or []
        }
        if not (citing_authors & own_authors):
            return AutoResult(
                "Oui",
                f"Le travail citant \"{c.get('display_name', '?')}\" "
                f"(id {c.get('id', '?')}) ne partage aucun auteur avec le travail évalué.",
                "haute",
            )
    return AutoResult(
        "Non",
        f"Les {len(citing)} travaux citants examinés partagent tous au moins un auteur "
        f"avec le travail évalué (auto-citations) -- vérifier au-delà de la première "
        f"page de résultats si cited_by_count > {len(citing)}.",
        "heuristique",
    )


def check_73_sdg(oa_work):
    """73 : Le travail est-il classé dans l'un des ODD (SDG) selon OpenAlex ?"""
    sdgs = _oa_work(oa_work).get("sustainable_development_goals")
    if sdgs is None:
        return AutoResult(None, "Champ sustainable_development_goals absent.", "haute")
    if sdgs:
        names = ", ".join(s.get("display_name", "?") for s in sdgs)
        return AutoResult("Oui", f"OpenAlex SDG classifiés : {names}.", "haute")
    return AutoResult("Non", "Aucun ODD classifié par OpenAlex pour ce travail.", "haute")


# =======================================================================================
# Grille du 30/09/2026 (data/ponderation_calibration_20260930.csv) -- critères nouveaux ou
# reformulés de façon à être tranchés par un champ structuré d'une source gratuite.
#
# Convention : chaque fonction répond au fait AFFIRMATIF (« la revue figure dans… », « un
# auteur a un autre travail rétracté », « publié depuis au moins… »). Quand une grille
# formule le critère négativement (« exempt de… », « Aucun des auteurs… »),
# orientation.orient() inverse Oui/Non -- la preuve reste celle du fait constaté.
# Les seuils N/M paramétrables (colonne `parametre` de la grille) sont passés en argument,
# avec pour valeur par défaut celle de la grille du 30/09/2026.
# =======================================================================================

def aggregate(sub_results, label):
    """Agrégat « Oui si au moins un sous-critère est Oui » (17, 18, 20, 54, 58…) : "Non"
    seulement si tous les sous-critères ont été tranchés "Non", "Indéterminé" sinon."""
    verdicts = [r.verdict for r in sub_results.values()]
    yes = [cid for cid, r in sub_results.items() if r.verdict == "Oui"]
    if yes:
        return AutoResult("Oui", f"{label} : sous-critère(s) vérifié(s) {', '.join(yes)}.", "haute")
    if verdicts and all(v == "Non" for v in verdicts):
        return AutoResult("Non", f"{label} : tous les sous-critères ({', '.join(sub_results)}) sont \"Non\".", "haute")
    if all(v is None for v in verdicts):
        return AutoResult(None, f"{label} : aucun sous-critère vérifiable.", "haute")
    return AutoResult(
        "Indéterminé",
        f"{label} : aucun sous-critère \"Oui\", mais certains n'ont pas pu être tranchés.",
        "heuristique",
    )


def _source_of(work):
    return ((work or {}).get("primary_location") or {}).get("source") or {}


def _author_ids(work):
    return {
        a["author"]["id"] for a in (work or {}).get("authorships") or []
        if (a.get("author") or {}).get("id")
    }


def _ror_ids(work):
    return {
        inst["ror"] for a in (work or {}).get("authorships") or []
        for inst in a.get("institutions") or [] if inst.get("ror")
    }


def _countries(work):
    return {
        inst["country_code"] for a in (work or {}).get("authorships") or []
        for inst in a.get("institutions") or [] if inst.get("country_code")
    }


def _publisher_ids(work):
    return set(_source_of(work).get("host_organization_lineage") or [])


def abstract_text(oa_work):
    """Résumé OpenAlex reconstitué à partir de abstract_inverted_index (texte vide sinon)."""
    index = _oa_work(oa_work).get("abstract_inverted_index") or {}
    positions = [(pos, word) for word, poss in index.items() for pos in poss]
    return " ".join(word for _pos, word in sorted(positions))


# --- Peer-review déclaré dans DOAJ (1, 1.1, 1.2, 1.7, 4.1.1.1) ------------------------

def _doaj_bibjson(doaj_result):
    results = (doaj_result or {}).get("results") or []
    return (results[0].get("bibjson") or {}) if results else None


def check_1_doaj_review(doaj_result):
    """1 / 1.1 / 1.2 : peer-review et anonymat d'après DOAJ bibjson.editorial.review_process
    (hors DOAJ : hors de portée, verdict None). « Double anonymous » cache les deux
    identités ; « single anonymous » / « blind » seulement celle des évaluateurs ; « open »
    aucune ; « editorial review » seule n'est pas un peer-review."""
    bib = _doaj_bibjson(doaj_result)
    ids = ("1", "1.1", "1.2")
    if bib is None:
        return {cid: AutoResult(None, "Revue absente de DOAJ (ou requête non aboutie).", "haute") for cid in ids}
    processes = [p.lower() for p in (bib.get("editorial") or {}).get("review_process") or []]
    evidence = f"DOAJ review_process = {processes or 'non renseigné'}."
    if not processes:
        return {cid: AutoResult("Indéterminé", evidence, "haute") for cid in ids}
    peer = [p for p in processes if "peer review" in p or "peer-review" in p]
    double = any("double" in p for p in peer)
    reviewers_hidden = double or any(("single" in p or "anonymous" in p or "blind" in p) for p in peer)
    only_open = bool(peer) and all("open" in p for p in peer)
    return {
        "1": AutoResult("Oui" if peer else "Non", evidence, "haute"),
        "1.1": AutoResult("Oui" if double else ("Non" if peer else "Indéterminé"), evidence, "heuristique"),
        "1.2": AutoResult(
            "Oui" if reviewers_hidden else ("Non" if only_open else "Indéterminé"), evidence, "heuristique"
        ),
    }


def check_1_7_publication_time(doaj_result, weeks=4):
    """1.7 : Délai moyen soumission-publication déclaré dans DOAJ d'au moins N semaines ?"""
    bib = _doaj_bibjson(doaj_result)
    if bib is None:
        return AutoResult(None, "Revue absente de DOAJ (ou requête non aboutie).", "haute")
    value = bib.get("publication_time_weeks")
    if value is None:
        return AutoResult("Indéterminé", "DOAJ publication_time_weeks non renseigné.", "haute")
    return AutoResult(
        "Oui" if value >= weeks else "Non", f"DOAJ publication_time_weeks = {value} (seuil N = {weeks}).", "haute"
    )


def check_4_1_1_1_diamond(doaj_result):
    """4.1.1.1 : Revue sans frais de publication (APC) d'après DOAJ bibjson.apc.has_apc."""
    bib = _doaj_bibjson(doaj_result)
    if bib is None:
        return AutoResult(None, "Revue absente de DOAJ (ou requête non aboutie).", "haute")
    has_apc = (bib.get("apc") or {}).get("has_apc")
    if has_apc is None:
        return AutoResult("Indéterminé", "DOAJ apc.has_apc non renseigné.", "haute")
    return AutoResult("Non" if has_apc else "Oui", f"DOAJ apc.has_apc = {has_apc}.", "haute")


# --- Rapports de relecture publiés (1.3, 1.4, 22, 22.1) et délai de relecture (1.5) ----

def check_published_reviews(cr_work, min_reports=2):
    """1.3 / 1.4 / 22 / 22.1 : rapports de relecture publiés et liés au travail par DOI
    (1.4, formulé en défaut depuis le 02/10/2026 : MOINS de N rapports distincts ?)
    (relation Crossref « has-review »). Les rapports d'évaluateurs se distinguent des
    décisions et réponses d'auteurs par leur suffixe « …/reviewN » ; ils sont dédoublonnés
    par numéro d'évaluateur à travers les versions (v1/review1 et v2/review1 = un même
    évaluateur). DataCite et Sciety ne sont pas interrogés : 22 et 22.1 restent
    "Indéterminé" faute de lien Crossref."""
    ids = ("1.3", "1.4", "22", "22.1")
    if not cr_work:
        return {cid: AutoResult(None, "Notice Crossref indisponible.", "haute") for cid in ids}
    linked = [r.get("id", "") for r in (cr_work.get("relation") or {}).get("has-review") or []]
    reviewers = sorted({m.group(1).lower() for m in (re.search(r"/(review\d+)$", d, re.I) for d in linked) if m})
    reports = [d for d in linked if re.search(r"review\d*$", d, re.I)]
    if not linked:
        evidence = "Aucune relation « has-review » dans la notice Crossref."
        return {
            "1.3": AutoResult("Non", evidence, "heuristique"),
            "1.4": AutoResult("Oui", evidence, "heuristique"),
            "22": AutoResult("Indéterminé", evidence + " Sciety non interrogé.", "heuristique"),
            "22.1": AutoResult("Indéterminé", evidence + " DataCite non interrogé.", "heuristique"),
        }
    evidence = f"Crossref relation has-review : {', '.join(linked)}."
    return {
        "1.3": AutoResult("Oui" if reports else "Non", evidence, "haute"),
        "1.4": AutoResult(
            "Oui" if len(reviewers) < min_reports else "Non",
            evidence + f" Évaluateurs distincts : {len(reviewers)} (seuil N = {min_reports}).",
            "heuristique",
        ),
        "22": AutoResult("Oui", evidence, "haute"),
        "22.1": AutoResult("Oui", evidence, "haute"),
    }


_DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y", "%Y/%m/%d", "%d/%m/%Y")


def _parse_free_date(value):
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def check_1_5_review_delay(cr_work, days=30):
    """1.5 (formulé en défaut) : délai réception -> acceptation inférieur à N jours ? D'après les assertions
    Crossmark « received » / « accepted » déposées dans Crossref (texte libre)."""
    if not cr_work:
        return AutoResult(None, "Notice Crossref indisponible.", "haute")
    dates = {}
    for a in cr_work.get("assertion") or []:
        name = (a.get("name") or "").lower()
        if name in ("received", "accepted") and a.get("value"):
            dates[name] = _parse_free_date(a["value"])
    if not (dates.get("received") and dates.get("accepted")):
        return AutoResult(None, "Dates received/accepted absentes (ou illisibles) dans Crossref.", "haute")
    delay = (dates["accepted"] - dates["received"]).days
    return AutoResult(
        "Oui" if delay < days else "Non",
        f"Crossref : reçu le {dates['received']}, accepté le {dates['accepted']} -> {delay} jours (seuil N = {days}).",
        "haute",
    )


# --- Préprint et dépôt en archive (2, 4.2), licences (4.3, 4.3.1) -----------------------

def check_2_preprint(hal_result, cr_work=None, oa_work=None):
    """2 : Déposé en preprint dans une archive ouverte ? HAL, relation Crossref
    « has-preprint », ou localisation OpenAlex « submittedVersion » dans un entrepôt."""
    evidence = []
    preprints = ((cr_work or {}).get("relation") or {}).get("has-preprint") or []
    if preprints:
        evidence.append("Crossref has-preprint : " + ", ".join(p.get("id", "?") for p in preprints))
    for loc in _oa_work(oa_work).get("locations") or []:
        source = loc.get("source") or {}
        if loc.get("version") == "submittedVersion" and source.get("type") == "repository":
            evidence.append(f"OpenAlex : version soumise dans {source.get('display_name', '?')}")
    hal = check_2_hal_deposit(hal_result)
    if hal.verdict == "Oui":
        evidence.append(hal.evidence)
    if evidence:
        return AutoResult("Oui", " ; ".join(evidence) + ".", "haute")
    if hal.verdict is None and not (cr_work or oa_work):
        return hal
    return AutoResult("Non", "Ni dépôt HAL, ni relation has-preprint, ni version soumise en entrepôt.", "heuristique")


def check_4_2_repository_copy(oa_work):
    """4.2 : Une version du texte intégral est-elle déposée dans une archive ouverte ?"""
    if not oa_work:
        return AutoResult(None, "Notice OpenAlex indisponible.", "haute")
    repos = sorted({
        (loc.get("source") or {}).get("display_name", "?")
        for loc in oa_work.get("locations") or []
        if (loc.get("source") or {}).get("type") == "repository" and loc.get("is_oa")
    })
    if repos:
        return AutoResult("Oui", f"OpenAlex : copie ouverte en entrepôt ({', '.join(repos)}).", "haute")
    return AutoResult("Non", "OpenAlex : aucune localisation ouverte de type repository.", "heuristique")


OPEN_LICENSES = ("cc-by", "cc-by-sa", "cc0", "public-domain")


def check_4_3_license(oa_work):
    """4.3 : Version en libre accès sous licence Creative Commons ou équivalente ?
    4.3.1 : licence permettant réutilisation commerciale et modifications (CC BY, CC BY-SA,
    CC0, domaine public) ? D'après OpenAlex best_oa_location.license."""
    if not oa_work:
        return {cid: AutoResult(None, "Notice OpenAlex indisponible.", "haute") for cid in ("4.3", "4.3.1")}
    best = oa_work.get("best_oa_location") or {}
    if not best:
        msg = "OpenAlex : aucune version en libre accès."
        return {"4.3": AutoResult("Non", msg, "haute"), "4.3.1": AutoResult("Non", msg, "haute")}
    license_ = (best.get("license") or "").lower()
    evidence = f"OpenAlex best_oa_location.license = {license_ or 'non renseignée'}."
    if not license_:
        return {cid: AutoResult("Indéterminé", evidence, "heuristique") for cid in ("4.3", "4.3.1")}
    is_open = license_.startswith("cc") or license_ in OPEN_LICENSES
    return {
        "4.3": AutoResult("Oui" if is_open else "Non", evidence, "haute"),
        "4.3.1": AutoResult("Oui" if license_ in OPEN_LICENSES else "Non", evidence, "haute"),
    }


# --- Listes de revues intégrées à OpenAlex (source.listed_in) --------------------------
# OpenAlex intègre plusieurs listes de revues dans le champ `listed_in` de la source :
# un accès direct, sans relevé manuel ni import de fichier.
LISTED_IN_CRITERIA = {
    "5.1": (("erih-plus",), "ERIH PLUS"),
    "5.2": (("cwts-core",), "CWTS Leiden Ranking (liste Core)"),
    "5.4": (("doyens",), "liste des revues recommandables CDD–CNU santé"),
    "5.10": (("latindex",), "Latindex"),
    "5.11": (("scielo",), "SciELO"),
    "5.12": (("fecyt-seal",), "Sello de Calidad FECYT"),
    "5.13": (("anvur-scientific", "anvur-class-a"), "listes ANVUR"),
    "5.13.1": (("anvur-class-a",), "ANVUR, Classe A"),
    "5.17": (("poland-20", "poland-40", "poland-70", "poland-100", "poland-140", "poland-200"),
             "wykaz czasopism MEiN"),
    "5.17.1": (("poland-140", "poland-200"), "wykaz MEiN, 140 ou 200 points"),
    "5.18": (("norway-2",), "Kanalregisteret, niveau 2"),
    "5.20": (("jufo-2", "jufo-3"), "JUFO, niveau 2 ou 3"),
    "5.22": (("abdc-a-star", "abdc-a", "abdc-b", "abdc-c"), "ABDC Journal Quality List"),
    "5.22.1": (("abdc-a-star",), "ABDC, rang A*"),
    "5.25": (("ft50",), "FT50"),
    "5.26": (("utd24",), "UTD24"),
    "5.27": (("fnege-1-star", "fnege-1", "fnege-2", "fnege-3", "fnege-4"), "classement FNEGE"),
    # Le rang 1* (au-dessus du rang 1) est compté avec le rang 1 : choix de l'auteur.
    "5.27.1": (("fnege-1-star", "fnege-1"), "FNEGE, rang 1* ou 1"),
    # Dans OpenAlex, ccf-* ne marque que des revues : 25.3 (conférences CCF) reste manuel.
    "5.29": (("ccf-a", "ccf-b", "ccf-c"), "liste CCF (revues)"),
    "5.29.1": (("ccf-a",), "CCF, catégorie A"),
}


def check_listed_in(oa_work):
    """Critères de LISTED_IN_CRITERIA (5.1 à 5.29.1) : présence de la revue dans une
    liste, d'après primary_location.source.listed_in d'OpenAlex. Absence -> "Non" de
    confiance heuristique (mise à jour des listes dans OpenAlex possiblement en retard)."""
    source = _source_of(oa_work)
    if source.get("type") != "journal" or "listed_in" not in source:
        msg = "Pas de revue (ou champ listed_in absent) dans la notice OpenAlex."
        return {cid: AutoResult(None, msg, "haute") for cid in LISTED_IN_CRITERIA}
    listed = set(source.get("listed_in") or [])
    results = {}
    for cid, (keys, label) in LISTED_IN_CRITERIA.items():
        found = listed & set(keys)
        evidence = f"OpenAlex source « {source.get('display_name', '?')} » listed_in = {sorted(listed)} ({label})."
        results[cid] = AutoResult("Oui" if found else "Non", evidence, "haute" if found else "heuristique")
    return results


# --- Métadonnées ouvertes (11.1-11.4), financements (13.1, 13.2) ------------------------

def check_11_1_open_references(cr_work):
    """11.1 : Références déposées ET ouvertes dans Crossref (champ reference[] exposé) ?"""
    if not cr_work:
        return AutoResult(None, "Notice Crossref indisponible.", "haute")
    n_open = len(cr_work.get("reference") or [])
    n_declared = cr_work.get("reference-count", 0)
    if n_open:
        return AutoResult("Oui", f"Crossref : {n_open} référence(s) ouverte(s).", "haute")
    detail = "déposées mais non ouvertes" if n_declared else "non déposées"
    return AutoResult("Non", f"Crossref : reference-count = {n_declared}, références {detail}.", "haute")


def check_11_orcid_ror(oa_work, cr_work=None):
    """11.2 : au moins un auteur avec ORCID ; 11.3 : tous les auteurs avec ORCID ; 11.4 : au
    moins une affiliation identifiée par ROR -- dans les métadonnées du travail (OpenAlex,
    complété par Crossref author[].ORCID)."""
    authorships = _oa_work(oa_work).get("authorships") or []
    cr_authors = (cr_work or {}).get("author") or []
    if not authorships and not cr_authors:
        return {cid: AutoResult(None, "Aucune liste d'auteurs disponible.", "haute") for cid in ("11.2", "11.3", "11.4")}
    if authorships:
        with_orcid = [bool((a.get("author") or {}).get("orcid")) for a in authorships]
        if len(cr_authors) == len(with_orcid):
            with_orcid = [o or bool(c.get("ORCID")) for o, c in zip(with_orcid, cr_authors)]
    else:
        with_orcid = [bool(a.get("ORCID")) for a in cr_authors]
    n, k = len(with_orcid), sum(with_orcid)
    rors = sorted(_ror_ids(oa_work))
    return {
        "11.2": AutoResult("Oui" if k else "Non", f"{k} auteur(s) sur {n} avec ORCID.", "haute"),
        "11.3": AutoResult("Oui" if k == n else "Non", f"{k} auteur(s) sur {n} avec ORCID.", "haute"),
        "11.4": AutoResult(
            "Oui" if rors else "Non",
            f"ROR des affiliations (OpenAlex) : {', '.join(rors) if rors else 'aucun'}.",
            "haute",
        ),
    }


def check_13_1_award_number(cr_work, oa_work=None):
    """13.1 : Au moins un numéro de subvention déclaré (Crossref funder[].award, OpenAlex
    awards[]) ?"""
    if not (cr_work or oa_work):
        return AutoResult(None, "Notices Crossref et OpenAlex indisponibles.", "haute")
    awards = [a for f in (cr_work or {}).get("funder") or [] for a in f.get("award") or []]
    awards += [
        a.get("funder_award_id") or a.get("award_id") or a.get("display_name")
        for a in _oa_work(oa_work).get("awards") or [] if isinstance(a, dict)
    ]
    awards = [str(a) for a in awards if a]
    if awards:
        return AutoResult("Oui", f"Numéro(s) de subvention déclaré(s) : {', '.join(awards)}.", "haute")
    return AutoResult("Non", "Aucun numéro de subvention dans les métadonnées Crossref/OpenAlex.", "heuristique")


# Funder Registry : Commission européenne et ERC (identifiants sûrs), le reste par nom.
EC_FUNDER_DOIS = ("10.13039/501100000780", "10.13039/501100000781")
EC_FUNDER_NAME = re.compile(
    r"European Commission|European Research Council|Horizon 2020|Horizon Europe|H2020|"
    r"Seventh Framework Programme|Framework Programme|Marie Sk[łl]odowska|Research Executive Agency|"
    r"European Innovation Council|\bERC\b",
    re.IGNORECASE,
)


def check_13_2_ec_funder(cr_work, oa_work=None):
    """13.2 : Un financeur déclaré est-il la Commission européenne ou l'une de ses agences
    (programmes-cadres, ERC) ? Identifiant Funder Registry, à défaut nom du financeur."""
    if not (cr_work or oa_work):
        return AutoResult(None, "Notices Crossref et OpenAlex indisponibles.", "haute")
    cr_funders = (cr_work or {}).get("funder") or []
    oa_funders = _oa_work(oa_work).get("funders") or []
    for f in cr_funders:
        if (f.get("DOI") or "").lower() in EC_FUNDER_DOIS:
            return AutoResult("Oui", f"Crossref funder {f.get('name')} ({f.get('DOI')}).", "haute")
    names = [f.get("name", "") for f in cr_funders] + [f.get("display_name", "") for f in oa_funders]
    names = [n for n in names if n]
    matching = [n for n in names if EC_FUNDER_NAME.search(n)]
    if matching:
        return AutoResult("Oui", f"Financeur(s) européen(s) déclaré(s) : {', '.join(matching)}.", "heuristique")
    if not names:
        return AutoResult("Non", "Aucun financeur déclaré dans les métadonnées.", "heuristique")
    return AutoResult("Non", f"Financeurs déclarés, aucun européen : {', '.join(names)}.", "haute")


# --- Auteurs et affiliations (14.3, 14.5, 14.6, 16.1) -------------------------------------

def check_14_3_company_academic(oa_work):
    """14.3 : Au moins une institution « company » ET au moins une « education » ou
    « facility » (types ROR, via OpenAlex) ?"""
    types = {
        inst.get("type") for a in _oa_work(oa_work).get("authorships") or []
        for inst in a.get("institutions") or [] if inst.get("type")
    }
    if not types:
        return AutoResult("Indéterminé", "Aucun type d'institution renseigné dans OpenAlex.", "heuristique")
    ok = "company" in types and bool(types & set(RESEARCH_INSTITUTION_TYPES))
    return AutoResult("Oui" if ok else "Non", f"Types d'institutions affiliées : {', '.join(sorted(types))}.", "haute")


def check_14_5_6_many_authors(oa_work):
    """14.5 / 14.6 : Plus de 100 / plus de 1000 auteurs ? (OpenAlex authorships ; une liste
    tronquée -- is_authors_truncated -- compte plus de 100 auteurs)."""
    if not oa_work:
        return {cid: AutoResult(None, "Notice OpenAlex indisponible.", "haute") for cid in ("14.5", "14.6")}
    n = len(oa_work.get("authorships") or [])
    truncated = bool(oa_work.get("is_authors_truncated"))
    evidence = f"OpenAlex : {n} auteur(s) listé(s)" + (" (liste tronquée)." if truncated else ".")
    return {
        "14.5": AutoResult("Oui" if n > 100 or truncated else "Non", evidence, "haute"),
        "14.6": AutoResult("Oui" if n > 1000 else ("Indéterminé" if truncated else "Non"), evidence, "haute"),
    }


def check_16_1_all_affiliated(oa_work):
    """16.1 : Tous les auteurs ont-ils au moins une affiliation identifiée ?"""
    authorships = _oa_work(oa_work).get("authorships") or []
    if not authorships:
        return AutoResult(None, "Aucun auteur dans la notice OpenAlex.", "haute")
    missing = [
        (a.get("author") or {}).get("display_name") or a.get("raw_author_name") or "?"
        for a in authorships if not a.get("institutions")
    ]
    if missing:
        return AutoResult("Non", f"Sans affiliation identifiée : {', '.join(missing)}.", "heuristique")
    return AutoResult("Oui", f"Les {len(authorships)} auteur(s) ont une affiliation identifiée.", "haute")


# --- Production antérieure des auteurs (15, 15.1), intégrité (20.1), 53 -------------------

def check_15_other_works(n_works_by_authors):
    """15 : Au moins un auteur a-t-il produit une autre publication ? `n_works_by_authors`
    = nombre de travaux OpenAlex de l'ensemble des auteurs (travail évalué compris)."""
    if n_works_by_authors is None:
        return AutoResult(None, "Comptage OpenAlex des travaux des auteurs non abouti.", "haute")
    return AutoResult(
        "Oui" if n_works_by_authors >= 2 else "Non",
        f"OpenAlex : {n_works_by_authors} travail(aux) signé(s) par au moins un des auteurs (travail évalué compris).",
        "haute",
    )


def check_15_1_same_subfield(n_works_in_subfield, subfield_name):
    """15.1 : Au moins un auteur a-t-il une autre publication dans le même sous-domaine
    OpenAlex (primary_topic.subfield) que le travail ?"""
    if n_works_in_subfield is None:
        return AutoResult(None, "Sous-domaine du travail inconnu ou comptage non abouti.", "haute")
    return AutoResult(
        "Oui" if n_works_in_subfield >= 2 else "Non",
        f"OpenAlex : {n_works_in_subfield} travail(aux) des auteurs dans le sous-domaine « {subfield_name} » "
        f"(travail évalué compris).",
        "haute",
    )


def check_20_1_other_retracted(n_retracted_other_works):
    """20.1 (fait affirmatif) : un des auteurs signe-t-il un autre travail rétracté ?
    D'après le filtre OpenAlex is_retracted (alimenté par Retraction Watch)."""
    if n_retracted_other_works is None:
        return AutoResult(None, "Comptage OpenAlex non abouti (auteurs non identifiés ?).", "haute")
    return AutoResult(
        "Oui" if n_retracted_other_works else "Non",
        f"OpenAlex : {n_retracted_other_works} autre(s) travail(aux) rétracté(s) signé(s) par les auteurs.",
        "haute",
    )


def check_53_hyperprolific(counts_by_author, threshold=72):
    """53 (fait affirmatif) : un des auteurs a-t-il plus de N publications indexées au cours
    d'une même année civile ? `counts_by_author` = {nom: [{key: année, count: n}, ...]}
    (OpenAlex group_by=publication_year, types article/review/conference-paper)."""
    if not counts_by_author:
        return AutoResult(None, "Aucun auteur identifié dans OpenAlex.", "haute")
    if any(groups is None for groups in counts_by_author.values()):
        return AutoResult(None, "Comptage OpenAlex par année non abouti pour au moins un auteur.", "haute")
    peaks = {name: max(groups, key=lambda g: g["count"]) for name, groups in counts_by_author.items() if groups}
    over = {name: g for name, g in peaks.items() if g["count"] > threshold}
    if over:
        detail = ", ".join(f"{name} : {g['count']} en {g['key']}" for name, g in over.items())
        return AutoResult("Oui", f"Plus de {threshold} publications dans l'année : {detail}.", "haute")
    detail = ", ".join(f"{name} : {g['count']} ({g['key']})" for name, g in peaks.items())
    return AutoResult("Non", f"Maximum annuel par auteur (seuil N = {threshold}) : {detail or 'aucune'}.", "haute")


# --- Type de canal (25) ----------------------------------------------------------------

def check_25_proceedings(oa_work, cr_work=None):
    """25 : Publié dans des actes de colloque ? (source OpenAlex de type « conference »,
    type OpenAlex conference-paper, ou type Crossref proceedings-article)."""
    if not (oa_work or cr_work):
        return AutoResult(None, "Notices OpenAlex et Crossref indisponibles.", "haute")
    source_type = _source_of(oa_work).get("type")
    oa_type = _oa_work(oa_work).get("type")
    cr_type = (cr_work or {}).get("type")
    yes = source_type == "conference" or oa_type == "conference-paper" or cr_type == "proceedings-article"
    return AutoResult(
        "Oui" if yes else "Non",
        f"OpenAlex source.type = {source_type}, type = {oa_type} ; Crossref type = {cr_type}.",
        "haute",
    )


# --- Préenregistrement (3, 3.1) ---------------------------------------------------------

REGISTRATION_ID = re.compile(
    r"\b(NCT\d{8}|ISRCTN\d{8}|CRD\d{11}|\d{4}-\d{6}-\d{2}|osf\.io/[a-z0-9]{5}|aspredicted\.org/[a-z0-9_/]+)",
    re.IGNORECASE,
)


def check_3_registration(oa_work, pubmed_accessions=None):
    """3 : Au moins un identifiant de préenregistrement (NCT, ISRCTN, EU CTR, PROSPERO CRD,
    OSF, AsPredicted) dans la notice PubMed (DataBankList) ou le résumé ? Renvoie
    (AutoResult, [identifiants]). Le texte intégral n'est pas lu : sans identifiant
    trouvé, la réponse reste "Indéterminé"."""
    found = [a.strip() for a in pubmed_accessions or [] if REGISTRATION_ID.fullmatch(a.strip())]
    found += [m.group(1) for m in REGISTRATION_ID.finditer(abstract_text(oa_work))]
    found = sorted(set(found))
    if found:
        return AutoResult("Oui", f"Identifiant(s) de registre : {', '.join(found)}.", "haute"), found
    return AutoResult(
        "Indéterminé",
        "Aucun identifiant de registre dans la notice PubMed ni dans le résumé (texte intégral non lu).",
        "heuristique",
    ), []


def check_3_1_prospective(status_module, nct_id):
    """3.1 : Enregistrement prospectif (premier dépôt <= début de l'étude) ? D'après
    l'API ClinicalTrials.gov v2 ; les autres registres sont hors de portée."""
    if not status_module:
        return AutoResult(None, "Aucun identifiant ClinicalTrials.gov exploitable.", "haute")
    submitted = status_module.get("studyFirstSubmitDate")
    start = (status_module.get("startDateStruct") or {}).get("date")
    if not (submitted and start):
        return AutoResult("Indéterminé", f"{nct_id} : dates de dépôt/début incomplètes.", "haute")
    # Une date de début au seul mois (AAAA-MM) est comparée au premier jour du mois.
    start_cmp = start if len(start) == 10 else start + "-01"
    return AutoResult(
        "Oui" if submitted <= start_cmp else "Non",
        f"ClinicalTrials.gov {nct_id} : premier dépôt {submitted}, début de l'étude {start}.",
        "haute",
    )


# --- Références et citations (36, 46, 92-103, 106, 107) ---------------------------------

def check_46_has_references(cr_work, oa_work=None):
    """46 (grille du 30/09/2026) : au moins une référence bibliographique ?"""
    n_cr = (cr_work or {}).get("reference-count")
    n_oa = _oa_work(oa_work).get("referenced_works_count")
    if n_cr is None and n_oa is None:
        return AutoResult(None, "Aucun comptage de références disponible.", "haute")
    n = max(n_cr or 0, n_oa or 0)
    return AutoResult(
        "Oui" if n else "Non",
        f"Crossref reference-count = {n_cr} ; OpenAlex referenced_works_count = {n_oa}.",
        "haute" if n else "heuristique",
    )


def check_36_cites_retracted(referenced_works):
    """36 (fait affirmatif) : le travail cite-t-il des travaux rétractés ? (références
    OpenAlex, champ is_retracted)."""
    if referenced_works is None:
        return AutoResult(None, "Références OpenAlex non récupérées.", "haute")
    retracted = [w.get("doi") or w.get("id") for w in referenced_works if w.get("is_retracted")]
    if retracted:
        return AutoResult("Oui", f"Référence(s) rétractée(s) : {', '.join(retracted)}.", "haute")
    return AutoResult("Non", f"Aucune des {len(referenced_works)} références OpenAlex n'est rétractée.", "haute")


def _share(matching, total):
    return 100.0 * matching / total if total else 0.0


def check_citation_sets(oa_work, citing_result, n_self=30, n_source=30, n_publisher=50, n_institution=30,
                        min_citations=10):
    """92-95, 97-100 : comparaison du travail aux travaux qui le citent (OpenAlex) --
    autre source, autre éditeur, aucune institution ou aucun pays commun (92-95, « au
    moins une citation telle que… ») ; parts de citations partageant un auteur, la source,
    l'éditeur ou une institution inférieures ou égales à N % (97-100, calculées seulement
    à partir de M citations). Les citations sont examinées jusqu'à 200 (une page)."""
    ids = ("92", "93", "94", "95", "97", "98", "99", "100")
    if not oa_work or citing_result is None:
        return {cid: AutoResult(None, "Travaux citants non récupérés.", "haute") for cid in ids}
    citing = citing_result.get("results") or []
    total = (citing_result.get("meta") or {}).get("count", len(citing))
    note = f" ({len(citing)} examinée(s) sur {total})" if total > len(citing) else ""
    own_source = _source_of(oa_work).get("id")
    own_publishers, own_authors = _publisher_ids(oa_work), _author_ids(oa_work)
    own_rors, own_countries = _ror_ids(oa_work), _countries(oa_work)

    def first(predicate, label):
        for w in citing:
            if predicate(w):
                return AutoResult("Oui", f"{label} : {w.get('doi') or w.get('id')}.", "haute")
        if not citing:
            return AutoResult("Non", "Aucune citation reçue (OpenAlex).", "haute")
        return AutoResult("Non", f"Aucune des citations examinées{note} ne remplit la condition.", "heuristique")

    def ratio(predicate, threshold, label):
        if len(citing) < min_citations:
            return AutoResult(
                "Indéterminé", f"{len(citing)} citation(s) : en deçà du minimum M = {min_citations}.", "haute"
            )
        k = sum(1 for w in citing if predicate(w))
        share = _share(k, len(citing))
        return AutoResult(
            "Oui" if share <= threshold else "Non",
            f"{k}/{len(citing)} citations {label} ({share:.0f} %, seuil N = {threshold} %){note}.",
            "haute",
        )

    def same_source(w):
        return _source_of(w).get("id") == own_source

    def same_publisher(w):
        return bool(own_publishers & _publisher_ids(w))

    def shares_author(w):
        return bool(own_authors & _author_ids(w))

    def shares_ror(w):
        return bool(own_rors & _ror_ids(w))

    results = {
        "92": first(lambda w: _source_of(w).get("id") and not same_source(w), "Citation depuis une autre source"),
        "93": first(lambda w: _publisher_ids(w) and not same_publisher(w), "Citation chez un autre éditeur"),
        "94": first(lambda w: _ror_ids(w) and not shares_ror(w), "Citation sans institution commune"),
        "95": first(lambda w: _countries(w) and not (own_countries & _countries(w)), "Citation sans pays commun"),
        "97": ratio(shares_author, n_self, "partageant un auteur"),
        "98": ratio(same_source, n_source, "de la même source"),
        "99": ratio(same_publisher, n_publisher, "du même éditeur"),
        "100": ratio(shares_ror, n_institution, "partageant une institution"),
    }
    unknown = []
    if not own_source:
        unknown += [("92", "Source du travail inconnue."), ("98", "Source du travail inconnue.")]
    if not own_publishers:
        unknown += [("93", "Éditeur du travail inconnu."), ("99", "Éditeur du travail inconnu.")]
    if not own_rors:
        unknown += [("94", "Aucune institution ROR pour le travail."), ("100", "Aucune institution ROR pour le travail.")]
    if not own_countries:
        unknown.append(("95", "Aucun pays d'affiliation pour le travail."))
    if not own_authors:
        unknown.append(("97", "Auteurs du travail non identifiés."))
    for cid, msg in unknown:
        results[cid] = AutoResult(None, msg, "haute")
    return results


def check_reference_sets(oa_work, referenced_works, n_source=20, n_publisher=50, n_self=25, min_references=10):
    """101-103 : parts des références du travail renvoyant à sa propre source, à son
    éditeur, à ses propres auteurs, inférieures ou égales à N % (à partir de M références
    retrouvées dans OpenAlex)."""
    ids = ("101", "102", "103")
    if not oa_work or referenced_works is None:
        return {cid: AutoResult(None, "Références OpenAlex non récupérées.", "haute") for cid in ids}
    n = len(referenced_works)
    if n < min_references:
        msg = f"{n} référence(s) retrouvée(s) dans OpenAlex : en deçà du minimum M = {min_references}."
        return {cid: AutoResult("Indéterminé", msg, "haute") for cid in ids}
    source_id, publishers, authors = _source_of(oa_work).get("id"), _publisher_ids(oa_work), _author_ids(oa_work)

    def ratio(predicate, threshold, label, known, unknown_msg):
        if not known:
            return AutoResult(None, unknown_msg, "haute")
        k = sum(1 for w in referenced_works if predicate(w))
        share = _share(k, n)
        return AutoResult(
            "Oui" if share <= threshold else "Non",
            f"{k}/{n} références {label} ({share:.0f} %, seuil N = {threshold} %).",
            "haute",
        )

    return {
        "101": ratio(lambda w: _source_of(w).get("id") == source_id, n_source, "vers la même source",
                     source_id, "Source du travail inconnue."),
        "102": ratio(lambda w: bool(publishers & _publisher_ids(w)), n_publisher, "vers le même éditeur",
                     publishers, "Éditeur du travail inconnu."),
        "103": ratio(lambda w: bool(authors & _author_ids(w)), n_self, "vers des travaux des mêmes auteurs",
                     authors, "Auteurs du travail non identifiés."),
    }


def check_106_top_cited(oa_work):
    """106 / 106.1 : dans les 10 % / 1 % des travaux les plus cités (même domaine, type et
    année) ? D'après OpenAlex citation_normalized_percentile."""
    pct = _oa_work(oa_work).get("citation_normalized_percentile")
    if not pct:
        return {cid: AutoResult(None, "citation_normalized_percentile absent.", "haute") for cid in ("106", "106.1")}
    evidence = f"OpenAlex citation_normalized_percentile = {pct.get('value')}."
    return {
        "106": AutoResult("Oui" if pct.get("is_in_top_10_percent") else "Non", evidence, "haute"),
        "106.1": AutoResult("Oui" if pct.get("is_in_top_1_percent") else "Non", evidence, "haute"),
    }


def check_107_fwci(oa_work, threshold=1.0):
    """107 : FWCI (impact citationnel normalisé par domaine) supérieur ou égal à N ?"""
    fwci = _oa_work(oa_work).get("fwci")
    if fwci is None:
        return AutoResult(None, "fwci absent de la notice OpenAlex.", "haute")
    return AutoResult("Oui" if fwci >= threshold else "Non", f"OpenAlex fwci = {fwci} (seuil N = {threshold}).", "haute")


# --- Retraction Watch : motifs (54-60) et citations d'expressions of concern (37) --------
# Les motifs (« Reason ») ne sont pas exposés par l'API REST Crossref : ils proviennent du
# fichier CSV public de la Retraction Watch Database (cf. retraction_watch.py).
RW_REASON_CRITERIA = {
    "54.1": r"concerns/issues about (authorship|affiliation)",
    "54.2": r"false/forged authorship",
    "54.3": r"false/forged affiliation",
    "54.4": r"lack of approval from (co-?)?author",
    "55": r"(falsification|fabrication|manipulation)[^;]*(data|results)|unreliable (data|results)",
    "56": r"image",
    "57": r"peer review|citation manipulation|rogue editor|paper mill",
    "58.1": r"lack of irb/iacuc approval",
    "58.2": r"informed/patient consent",
    "58.3": r"animal welfare",
    "58.4": r"human subject welfare",
    "58.5": r"conflict of interest",
    "58.6": r"ethical violations by author",
    "58.7": r"ethical violations by (company|institution|third party)",
    "59": r"duplication of/in article|euphemisms for duplication|duplicate publication",
    "60": r"investigation by (company|institution|third party|ori|government)",
}
# Motifs repérés par mots-clés (catégories non nommées explicitement dans la grille).
RW_HEURISTIC_CRITERIA = ("55", "56", "57", "59", "60")


def check_retraction_watch_reasons(rw_entries):
    """54-60 (faits affirmatifs) : le travail est-il mentionné dans la Retraction Watch
    Database au titre de tel motif ? `rw_entries` = notices RW du DOI (liste éventuellement
    vide), ou None si le fichier RW n'est pas disponible."""
    ids = list(RW_REASON_CRITERIA) + ["54", "58"]
    if rw_entries is None:
        msg = "Fichier Retraction Watch non configuré (variable RETRACTION_WATCH_CSV)."
        return {cid: AutoResult(None, msg, "haute") for cid in ids}
    reasons = sorted({
        r.strip().lstrip("+").strip() for e in rw_entries for r in (e.get("Reason") or "").split(";") if r.strip()
    })
    results = {}
    for cid, pattern in RW_REASON_CRITERIA.items():
        hits = [r for r in reasons if re.search(pattern, r, re.IGNORECASE)]
        if hits:
            results[cid] = AutoResult(
                "Oui", f"Retraction Watch, motif(s) : {'; '.join(hits)}.",
                "heuristique" if cid in RW_HEURISTIC_CRITERIA else "haute",
            )
        else:
            detail = f"motifs relevés : {'; '.join(reasons)}" if reasons else "aucune notice pour ce DOI"
            results[cid] = AutoResult("Non", f"Retraction Watch : {detail}.", "haute")
    results["54"] = aggregate({c: results[c] for c in ("54.1", "54.2", "54.3", "54.4")}, "Motifs d'autorat")
    results["58"] = aggregate({c: results[c] for c in RW_REASON_CRITERIA if c.startswith("58.")}, "Motifs éthiques")
    return results


def check_37_cites_concern(referenced_dois, rw_index):
    """37 (fait affirmatif) : le travail cite-t-il des travaux concernés par une expression
    of concern ? (DOI des références croisés avec la Retraction Watch Database)."""
    if rw_index is None:
        return AutoResult(None, "Fichier Retraction Watch non configuré (variable RETRACTION_WATCH_CSV).", "haute")
    if referenced_dois is None:
        return AutoResult(None, "Références non récupérées.", "haute")
    concerned = [
        d for d in referenced_dois
        if any("concern" in (e.get("RetractionNature") or "").lower() for e in rw_index.get(d.lower(), []))
    ]
    if concerned:
        return AutoResult("Oui", f"Référence(s) avec expression of concern : {', '.join(concerned)}.", "haute")
    return AutoResult("Non", f"Aucune des {len(referenced_dois)} références (DOI) n'a d'expression of concern.", "haute")


# --- Visibilité hors de la recherche (79, 88.1) -----------------------------------------

def check_79_wikipedia(searches):
    """79 : mentionné dans au moins un article de Wikipédia ? `searches` = {langue:
    (total, titres) ou None} (recherche du DOI dans le wikicode)."""
    done = {lang: res for lang, res in searches.items() if res is not None}
    if not done:
        return AutoResult(None, "Recherche Wikipédia non aboutie.", "haute")
    hits = {lang: res for lang, res in done.items() if res[0]}
    if hits:
        detail = " ; ".join(f"{lang} : {', '.join(titles)}" for lang, (_n, titles) in hits.items())
        return AutoResult("Oui", f"DOI cité dans Wikipédia ({detail}).", "haute")
    return AutoResult(
        "Non", f"DOI absent du wikicode des éditions {', '.join(done)} (autres langues non vérifiées).", "heuristique"
    )


def check_88_1_sudoc(isbns, library_counts):
    """88.1 : ouvrage détenu par au moins une bibliothèque du réseau SUDOC ?
    `library_counts` = {ppn: nombre de bibliothèques} pour les PPN trouvés par ISBN."""
    if not isbns:
        return AutoResult(None, "Aucun ISBN dans la notice Crossref.", "haute")
    if library_counts is None:
        return AutoResult(None, "Web services SUDOC non aboutis.", "haute")
    held = {ppn: n for ppn, n in library_counts.items() if n}
    if held:
        detail = ", ".join(f"PPN {ppn} : {n} bibliothèque(s)" for ppn, n in held.items())
        return AutoResult("Oui", f"SUDOC ({', '.join(isbns)}) : {detail}.", "haute")
    return AutoResult("Non", f"Aucune localisation SUDOC pour les ISBN {', '.join(isbns)}.", "haute")


# --- Indices d'enseignement et de vulgarisation des auteurs (17.x, 18.x) -----------------

ORCID_TEACHING_TYPES = ("lecture", "learning-object")
ORCID_OUTREACH_BLOG = ("blog-post",)
ORCID_OUTREACH_PRESS = ("magazine-article", "newspaper-article")


def check_author_profiles(profiles):
    """17.2, 17.3, 17.5, 18.1, 18.2, 18.3, à partir des profils publics des auteurs dotés
    d'un ORCID. `profiles` = {orcid: {"orcid_types": [...] | None, "hal_types": [...] |
    None, "zenodo_lessons": int | None}}. 17.1 (emploi ROR « education ») et 17.4 (FUN
    MOOC, recherche par nom) restent hors de portée ; les agrégats 17 et 18 sont calculés
    par aggregate() dans run_auto_answers."""
    ids = ("17.2", "17.3", "17.5", "18.1", "18.2", "18.3")
    if not profiles:
        return {cid: AutoResult(None, "Aucun auteur doté d'un ORCID dans les métadonnées.", "haute") for cid in ids}

    def scan(key, predicate, label):
        found, unknown = [], []
        for orcid, profile in profiles.items():
            value = profile.get(key)
            if value is None:
                unknown.append(orcid)
            elif predicate(value):
                found.append(orcid)
        if found:
            return AutoResult("Oui", f"{label} : ORCID {', '.join(found)}.", "haute")
        if unknown:
            return AutoResult("Indéterminé", f"{label} : profil(s) non consulté(s) {', '.join(unknown)}.", "haute")
        return AutoResult("Non", f"{label} : rien trouvé pour {len(profiles)} auteur(s) avec ORCID.", "heuristique")

    def has_type(types):
        return lambda values: any(v in types for v in values)

    return {
        "17.2": scan("hal_types", has_type(("LECTURE",)), "Dépôt HAL de type Cours"),
        "17.3": scan("orcid_types", has_type(ORCID_TEACHING_TYPES), "Œuvre ORCID lecture/learning-object"),
        "17.5": scan("zenodo_lessons", lambda n: n > 0, "Ressource Zenodo de type lesson"),
        "18.1": scan("orcid_types", has_type(ORCID_OUTREACH_BLOG), "Œuvre ORCID blog-post"),
        "18.2": scan("hal_types", has_type(("BLOG",)), "Dépôt HAL de type BLOG"),
        "18.3": scan("orcid_types", has_type(ORCID_OUTREACH_PRESS), "Œuvre ORCID magazine/newspaper-article"),
    }
