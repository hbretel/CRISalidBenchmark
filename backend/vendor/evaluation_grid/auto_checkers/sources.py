# -*- coding: utf-8 -*-
"""
Fonctions d'accès aux bases bibliométriques gratuites et sans clé d'API, pour la grille
d'évaluation qualitative du projet.

Chaque fonction ci-dessous fait UN appel HTTP à une API publique et renvoie soit le JSON
brut décodé (un dict Python), soit None accompagné d'une raison si l'appel échoue —
jamais une exception laissée à découvert, pour que run_auto_answers.py puisse continuer
sur les critères suivants même si une source est indisponible.

IMPORTANT — limite connue de cet environnement de développement : le bac à sable dans
lequel ce code a été écrit et testé (session Claude) fait passer les appels réseau du
Bash par un proxy de sortie strictement limité à une liste blanche (registres de paquets,
endpoints Anthropic) ; les domaines ci-dessous (api.openalex.org, api.crossref.org,
doaj.org, theses.fr, api.archives-ouvertes.fr, eutils.ncbi.nlm.nih.gov) y sont bloqués.
Le code a donc été validé par appels ponctuels via l'outil WebFetch (qui, lui, a accès à
ces domaines) pour capturer des exemples réels (voir fixtures/), puis testé unitairement
hors-ligne sur ces exemples (test_checkers.py). Depuis un poste ou un environnement sans
cette restriction (poste de travail de l'auteur, session Claude Code avec accès réseau standard,
serveur CI classique), ces fonctions `requests.get(...)` s'exécutent normalement : ce sont
des API publiques conçues pour un usage programmatique, sans authentification.

Toutes les fonctions acceptent un paramètre `timeout` (secondes) et lèvent uniquement des
erreurs réseau imprévues ; les cas attendus (notice introuvable, DOI invalide) renvoient
None plutôt qu'une exception.
"""
import time
import urllib.parse

import requests

USER_AGENT = (
    "GrilleEvaluationQualitative/1.0 "
    "(projet de recherche academique, usage non commercial; "
    "mailto:contact@example.org)"
)
# NB : les bonnes pratiques OpenAlex/Crossref ("polite pool") demandent un User-Agent
# identifiable avec une adresse de contact -- cela accélère et fiabilise les réponses.
# Remplacer l'adresse mailto ci-dessus par une adresse de contact réelle avant usage.

DEFAULT_TIMEOUT = 15
DEFAULT_HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _get_json(url, params=None, timeout=DEFAULT_TIMEOUT, headers=None):
    """Requête GET générique -> JSON décodé, ou None si échec (statut != 200, JSON
    invalide, timeout, erreur réseau). N'écrit jamais sur stderr : l'appelant décide quoi
    faire d'un retour None."""
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers=headers or DEFAULT_HEADERS,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------
# OpenAlex (openalex.org) -- gratuit, sans clé, très large couverture de métadonnées.
# Documentation : https://docs.openalex.org/
# ---------------------------------------------------------------------------------------

def openalex_work_by_doi(doi, timeout=DEFAULT_TIMEOUT):
    """Notice OpenAlex d'un travail identifié par son DOI (avec ou sans préfixe
    https://doi.org/). Renvoie le JSON complet de la notice "work", ou None."""
    doi_clean = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi_clean.lower().startswith(prefix):
            doi_clean = doi_clean[len(prefix):]
            break
    url = f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi_clean)}"
    return _get_json(url, timeout=timeout)


def openalex_author(author_id_or_orcid, timeout=DEFAULT_TIMEOUT):
    """Notice OpenAlex d'un auteur, à partir de son ID OpenAlex (ex. 'A5018716633') ou de
    son ORCID (ex. '0000-0003-4055-8431' ou son URL complète). Renvoie le JSON complet, ou
    None."""
    ident = author_id_or_orcid.strip()
    if "orcid.org" in ident or (len(ident) == 19 and ident.count("-") == 3):
        if not ident.startswith("http"):
            ident = f"https://orcid.org/{ident}"
        url = f"https://api.openalex.org/authors/{ident}"
    else:
        url = f"https://api.openalex.org/authors/{ident}"
    return _get_json(url, timeout=timeout)


def openalex_citing_works(work_openalex_id, per_page=25, timeout=DEFAULT_TIMEOUT):
    """Liste (première page) des travaux qui citent le travail donné (ID OpenAlex complet
    ou court, ex. 'W4406721876'), pour évaluer si au moins une citation provient d'une
    équipe extérieure (critère 66). Renvoie le JSON de la liste, ou None."""
    short_id = work_openalex_id.rsplit("/", 1)[-1]
    url = "https://api.openalex.org/works"
    params = {"filter": f"cites:{short_id}", "per_page": per_page}
    return _get_json(url, params=params, timeout=timeout)


# ---------------------------------------------------------------------------------------
# Crossref (crossref.org) -- gratuit, sans clé.
# Documentation : https://api.crossref.org/swagger-ui/index.html
# ---------------------------------------------------------------------------------------

def crossref_work_by_doi(doi, timeout=DEFAULT_TIMEOUT):
    """Notice Crossref d'un travail identifié par son DOI. Renvoie le contenu du champ
    "message" de la réponse (le dict décrivant le travail), ou None."""
    doi_clean = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi_clean.lower().startswith(prefix):
            doi_clean = doi_clean[len(prefix):]
            break
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi_clean)}"
    data = _get_json(url, timeout=timeout)
    if data is None:
        return None
    return data.get("message")


# ---------------------------------------------------------------------------------------
# DOAJ (doaj.org) -- gratuit, sans clé. Critère 5.9.
# Documentation : https://doaj.org/api/docs
# ---------------------------------------------------------------------------------------

def doaj_search_by_issn(issn, timeout=DEFAULT_TIMEOUT):
    """Cherche une revue dans DOAJ par ISSN (le plus fiable -- une recherche par titre est
    trop sujette aux faux positifs/négatifs pour une décision automatique). Renvoie le
    JSON de la réponse (avec `results` et `total`), ou None."""
    url = f"https://doaj.org/api/search/journals/issn:{urllib.parse.quote(issn.strip())}"
    return _get_json(url, timeout=timeout)


# ---------------------------------------------------------------------------------------
# HAL (archives ouvertes -- CCSD/CNRS) -- gratuit, sans clé. Critère 2.
# Documentation : https://api.archives-ouvertes.fr/docs
# ---------------------------------------------------------------------------------------

def hal_search_by_doi(doi, timeout=DEFAULT_TIMEOUT):
    """Cherche un dépôt HAL correspondant à un DOI donné. Renvoie le JSON de la réponse
    Solr HAL (avec response.numFound et response.docs), ou None."""
    doi_clean = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi_clean.lower().startswith(prefix):
            doi_clean = doi_clean[len(prefix):]
            break
    url = "https://api.archives-ouvertes.fr/search/"
    params = {
        "q": f'doiId_s:"{doi_clean}"',
        "fl": "halId_s,doiId_s,submittedDate_s,docType_s,fileMain_s",
        "wt": "json",
    }
    return _get_json(url, params=params, timeout=timeout)


# ---------------------------------------------------------------------------------------
# theses.fr (ABES) -- gratuit, sans clé. Critères 15.2, 21 (partiel).
# Documentation : https://theses.fr/?q=&fq=&checkedfacets=&start=0&status=&access=&format=json
# (API non formellement documentée publiquement mais couramment utilisée en JSON)
# ---------------------------------------------------------------------------------------

def theses_fr_search_person(nom, prenom=None, timeout=DEFAULT_TIMEOUT):
    """Cherche une personne dans theses.fr par nom (et prénom optionnel), pour savoir si
    elle est titulaire d'un doctorat (critère 15.2) et/ou a encadré des thèses. Renvoie le
    JSON de la réponse, ou None. À utiliser avec prudence : la recherche par nom seul peut
    produire des homonymes -- vérifier l'affiliation/discipline avant de conclure "Oui"."""
    q = nom if not prenom else f"{prenom} {nom}"
    url = "https://theses.fr/api/v1/personnes/recherche/"
    params = {"q": q}
    return _get_json(url, params=params, timeout=timeout)


# ---------------------------------------------------------------------------------------
# PubMed / Medline (NCBI E-utilities) -- gratuit, sans clé (clé optionnelle pour une
# limite de débit plus généreuse : voir NCBI_API_KEY ci-dessous). Critères 8, 8.1-8.30.
# Documentation : https://www.ncbi.nlm.nih.gov/books/NBK25501/
# Note : le robots.txt de ncbi.nlm.nih.gov bloque certains agents automatisés génériques
# (constaté avec l'outil WebFetch lors du développement) ; les E-utilities restent conçues
# pour un usage programmatique standard via un client HTTP tel que `requests`, comme
# utilisé ici -- ce blocage n'est pas censé s'appliquer à un usage normal de l'API.
# ---------------------------------------------------------------------------------------

NCBI_API_KEY = None  # optionnel -- cf. https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/


def pubmed_search_by_doi(doi, timeout=DEFAULT_TIMEOUT):
    """Cherche un PMID correspondant à un DOI via ESearch. Renvoie la liste des PMID
    trouvés (liste vide si non indexé dans PubMed/Medline), ou None en cas d'échec réseau
    (à distinguer d'une liste vide, qui est une réponse valide = "Non")."""
    doi_clean = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi_clean.lower().startswith(prefix):
            doi_clean = doi_clean[len(prefix):]
            break
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": f"{doi_clean}[doi]", "retmode": "json"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    data = _get_json(url, params=params, timeout=timeout)
    if data is None:
        return None
    return data.get("esearchresult", {}).get("idlist", [])


def pubmed_record_xml(pmid, timeout=DEFAULT_TIMEOUT):
    """Notice PubMed complète au format XML (EFetch), ou None en cas d'échec."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "pubmed", "id": pmid, "retmode": "xml", "rettype": "abstract"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        resp = requests.get(url, params=params, timeout=timeout, headers=DEFAULT_HEADERS)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.text


def pubmed_publication_types(pmid, timeout=DEFAULT_TIMEOUT, record_xml=None):
    """Liste des PublicationType d'une notice PubMed (critères 8.1-8.30), via EFetch au
    format XML minimal analysé à la main (pas de dépendance XML lourde). Renvoie une liste
    de chaînes (ex. ["Journal Article", "Review"]), ou None en cas d'échec. `record_xml`
    évite un second appel quand la notice a déjà été récupérée (pubmed_record_xml)."""
    import re

    text = record_xml if record_xml is not None else pubmed_record_xml(pmid, timeout=timeout)
    if text is None:
        return None
    return re.findall(r"<PublicationType[^>]*>([^<]+)</PublicationType>", text)


def pubmed_accession_numbers(record_xml):
    """Identifiants de registres déclarés dans la notice PubMed (DataBankList, ex.
    ClinicalTrials.gov NCT…) : liste de chaînes, vide si aucun."""
    import re

    return re.findall(r"<AccessionNumber>([^<]+)</AccessionNumber>", record_xml or "")


# ---------------------------------------------------------------------------------------
# OpenAlex -- requêtes sur des ENSEMBLES de travaux (grille du 30/09/2026 : critères
# 15/15.1, 20.1, 53, 92-103). Une requête filtrée renvoie meta.count sans rapatrier les
# notices : c'est le moyen le plus économe de répondre « existe-t-il au moins un autre
# travail tel que… ». Les identifiants d'auteurs se combinent en OU avec « | ».
# ---------------------------------------------------------------------------------------

def _short_openalex_id(openalex_id):
    return openalex_id.rsplit("/", 1)[-1]


def openalex_works_count(filter_expr, timeout=DEFAULT_TIMEOUT):
    """Nombre de travaux OpenAlex correspondant à un filtre (ex. "author.id:A1|A2,
    is_retracted:true"), ou None en cas d'échec."""
    data = _get_json(
        "https://api.openalex.org/works",
        params={"filter": filter_expr, "per_page": 1, "select": "id"},
        timeout=timeout,
    )
    return None if data is None else (data.get("meta") or {}).get("count")


def openalex_works_group_by(filter_expr, group_by, timeout=DEFAULT_TIMEOUT):
    """Comptes groupés (ex. group_by="publication_year") : liste de {key, count}, ou None."""
    data = _get_json(
        "https://api.openalex.org/works",
        params={"filter": filter_expr, "group_by": group_by},
        timeout=timeout,
    )
    return None if data is None else data.get("group_by")


WORK_SET_FIELDS = "id,doi,primary_location,authorships,is_retracted"


def openalex_citing_works_all(work_openalex_id, max_works=200, timeout=DEFAULT_TIMEOUT):
    """Travaux citant le travail donné (jusqu'à max_works, une seule page de 200), avec
    les seuls champs utiles aux comparaisons source/éditeur/auteurs/institutions. Renvoie
    le JSON de la liste (results + meta.count), ou None."""
    return _get_json(
        "https://api.openalex.org/works",
        params={
            "filter": f"cites:{_short_openalex_id(work_openalex_id)}",
            "per_page": min(max_works, 200),
            "select": WORK_SET_FIELDS,
        },
        timeout=timeout,
    )


def openalex_works_by_ids(openalex_ids, timeout=DEFAULT_TIMEOUT):
    """Notices (champs réduits) d'une liste de travaux OpenAlex, par lots de 50 (limite
    des filtres en OU). Renvoie la liste des notices trouvées, ou None si un lot échoue."""
    ids = [_short_openalex_id(i) for i in openalex_ids]
    works = []
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        data = _get_json(
            "https://api.openalex.org/works",
            params={"filter": "openalex_id:" + "|".join(batch), "per_page": 50, "select": WORK_SET_FIELDS},
            timeout=timeout,
        )
        if data is None:
            return None
        works.extend(data.get("results") or [])
    return works


# ---------------------------------------------------------------------------------------
# Wikipédia (API MediaWiki) -- gratuit, sans clé. Critère 79.
# ---------------------------------------------------------------------------------------

def wikipedia_doi_search(doi, lang="en", timeout=DEFAULT_TIMEOUT):
    """Nombre d'articles de Wikipédia (édition `lang`) dont le wikicode contient le DOI,
    et leurs titres : (total, [titres]) ou None."""
    data = _get_json(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "query", "list": "search", "format": "json", "srlimit": 5,
            "srsearch": f'insource:"{doi}"',
        },
        timeout=timeout,
    )
    if data is None or "query" not in data:
        return None
    query = data["query"]
    return query.get("searchinfo", {}).get("totalhits", 0), [s["title"] for s in query.get("search", [])]


# ---------------------------------------------------------------------------------------
# SUDOC (ABES) -- web services gratuits. Critère 88.1.
# ---------------------------------------------------------------------------------------

def sudoc_ppns_for_isbn(isbn, timeout=DEFAULT_TIMEOUT):
    """PPN des notices SUDOC correspondant à un ISBN : liste (vide si aucune), ou None."""
    data = _get_json(
        f"https://www.sudoc.fr/services/isbn2ppn/{urllib.parse.quote(isbn)}",
        params={"format": "text/json"},
        timeout=timeout,
    )
    if data is None:
        return None
    result = ((data.get("sudoc") or {}).get("query") or {}).get("result")
    if result is None:
        return []
    items = result if isinstance(result, list) else [result]
    return [i["ppn"] for i in items if i.get("ppn")]


def sudoc_library_count(ppn, timeout=DEFAULT_TIMEOUT):
    """Nombre de bibliothèques du réseau SUDOC localisant une notice (multiwhere), ou None."""
    data = _get_json(
        f"https://www.sudoc.fr/services/multiwhere/{urllib.parse.quote(ppn)}",
        params={"format": "text/json"},
        timeout=timeout,
    )
    if data is None:
        return None
    libraries = (((data.get("sudoc") or {}).get("query") or {}).get("result") or {}).get("library") or []
    return len(libraries if isinstance(libraries, list) else [libraries])


# ---------------------------------------------------------------------------------------
# ClinicalTrials.gov (API v2) -- gratuit, sans clé. Critère 3.1.
# ---------------------------------------------------------------------------------------

def clinicaltrials_status(nct_id, timeout=DEFAULT_TIMEOUT):
    """statusModule de l'étude (dates de premier dépôt et de début), ou None."""
    data = _get_json(
        f"https://clinicaltrials.gov/api/v2/studies/{urllib.parse.quote(nct_id)}",
        params={"fields": "protocolSection.statusModule"},
        timeout=timeout,
    )
    return None if data is None else (data.get("protocolSection") or {}).get("statusModule")


# ---------------------------------------------------------------------------------------
# Profils d'auteurs : ORCID (API publique), HAL, Zenodo -- gratuits, sans clé.
# Critères 17.x et 18.x (indices d'enseignement et de vulgarisation).
# ---------------------------------------------------------------------------------------

def _bare_orcid(orcid):
    return orcid.rstrip("/").rsplit("/", 1)[-1]


def orcid_work_types(orcid, timeout=DEFAULT_TIMEOUT):
    """Types des œuvres déclarées dans le profil ORCID public (ex. "journal-article",
    "lecture", "blog-post") : liste, ou None."""
    data = _get_json(f"https://pub.orcid.org/v3.0/{_bare_orcid(orcid)}/works", timeout=timeout)
    if data is None:
        return None
    return [s.get("type") for g in data.get("group") or [] for s in g.get("work-summary") or []]


def hal_documents_by_orcid(orcid, doc_types, timeout=DEFAULT_TIMEOUT):
    """Dépôts HAL rattachés à un ORCID et d'un des types donnés (ex. ["LECTURE"]) :
    JSON Solr (response.numFound, response.docs), ou None."""
    return _get_json(
        "https://api.archives-ouvertes.fr/search/",
        params={
            "q": f'authORCIDIdExt_s:"{_bare_orcid(orcid)}"',
            "fq": "docType_s:(" + " OR ".join(doc_types) + ")",
            "fl": "halId_s,docType_s,title_s",
            "wt": "json",
            "rows": 5,
        },
        timeout=timeout,
    )


def zenodo_records_count(query, timeout=DEFAULT_TIMEOUT):
    """Nombre d'enregistrements Zenodo correspondant à une requête, ou None."""
    data = _get_json("https://zenodo.org/api/records", params={"q": query, "size": 1}, timeout=timeout)
    return None if data is None else ((data.get("hits") or {}).get("total"))


# ---------------------------------------------------------------------------------------
# Utilitaire générique : pause polie entre appels successifs à une même API dans une
# boucle (aucune des API ci-dessus n'impose de délai strict sans clé, mais rester
# raisonnable évite les 429).
# ---------------------------------------------------------------------------------------

def polite_pause(seconds=0.15):
    time.sleep(seconds)
