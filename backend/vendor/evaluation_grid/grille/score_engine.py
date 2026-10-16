#!/usr/bin/env python3
"""
Moteur de score : calcule le score final d'un travail évalué à partir :
  - de ses réponses (Oui/Non/Indéterminé) à un sous-ensemble des critères de
    data/criteres_grille_evaluation.csv,
  - des colonnes de pondération du CSV : poids_points, poids_coefficient,
    modulateur_de, facteur_modulation, desactive_si, exclusif_de.

RENOMMÉ DEPUIS score_test.py (réorganisation du 25/09/2026 en projet logiciel) : le nom
"score_test" datait d'un script de test ponctuel ; la logique elle-même n'a pas changé
d'une ligne, seul CSV_PATH pointe désormais vers data/ par défaut (au lieu du même
répertoire que le script) pour refléter la nouvelle arborescence.

RÈGLE DES TROIS RÔLES EXCLUSIFS (grille simplifiée du 11/09/2026)
------------------------------------------------------------------
Depuis la simplification drastique de la grille par l'auteur le 11/09/2026, chaque critère
a EXACTEMENT UN SEUL rôle de pondération parmi les trois suivants (jamais deux, jamais
plus) — colonnes reponse_attendue, statut et remarque abandonnées à la même occasion :

  - « points »       : poids_points renseigné. Contribue à score_base si répondu "Oui".
  - « coefficient »  : poids_coefficient renseigné. Contribue au coefficient global si
                        répondu "Oui".
  - « modulateur »   : modulateur_de (+ facteur_modulation) renseigné. Ne contribue
                        JAMAIS directement à score_base ni au coefficient ; ne fait
                        qu'affiner le poids d'un ou plusieurs autres critères (ses
                        cibles) quand il est lui-même répondu "Oui".
  - aucun des trois  : critère purement descriptif/gate, sans effet chiffré direct.

Cette exclusivité est vérifiée mécaniquement par validate_grid() à chaque chargement de
la grille (load_grid) : toute violation lève une ValueError listant tous les critères en
cause, pour que l'auteur puisse corriger la grille en une seule passe. classify_role() fait
office de garde-fou supplémentaire au moment du calcul.

Important : le rôle d'un critère ne dépend plus de son type_critere (Positif de
qualité / Zéro-défaut / Descriptif). Le type_critere reste une étiquette descriptive utile
pour la documentation de la grille, mais ne conditionne plus rien dans le calcul : par
exemple le critère 46 (Descriptif) porte tout de même un poids_points, et de nombreux
critères Zéro-défaut (ex. 30, 58) portent un poids_coefficient — ces deux faits sont
désormais normaux et attendus.

Formule : score_final = score_base × coefficient

  - score_base démarre à 0. Chaque critère de rôle « points » répondu "Oui" ajoute son
    poids_points (éventuellement affiné par ses modulateurs directs, voir plus bas).
  - coefficient démarre à 1 (plancher 0, pas de plafond). Chaque critère de rôle
    « coefficient » répondu "Oui" multiplie le coefficient par son poids_coefficient
    (également affiné par ses modulateurs directs).
  - Un critère MODULATEUR (modulateur_de renseigné) affine le poids d'un ou plusieurs
    critères cibles quand sa propre réponse est "Oui". DEPUIS LA CORRECTION DU 11/09/2026
    (signalée par l'auteur après le test réel sur Chaignon 2025), un facteur de modulation
    n'agit PLUS par multiplication directe sur le poids cible : il agit uniquement sur
    l'ÉVOLUTION INDUITE par ce poids par rapport à une valeur neutre (« identité »), qui
    vaut 1 pour un poids de coefficient (et pour le facteur_modulation d'un modulateur —
    tous deux sont des grandeurs multiplicatives centrées sur 1, où « pas d'effet » = 1),
    et 0 pour un poids en points (grandeur additive, où « pas d'effet » = 0 : pour les
    points, cette règle redonne donc exactement la multiplication directe d'origine,
    puisque identité + (poids − identité) × facteur = 0 + poids × facteur).

    Concrètement, pour un poids cible de rôle « coefficient » (ou pour le facteur_modulation
    d'un modulateur cible d'un AUTRE modulateur, cf. chaînes ci-dessous) :

        poids_effectif = 1 + (poids_de_base − 1) × facteur_modulation_effectif

    Exemple (signalé par l'auteur) : le critère 65 (poids_coefficient = 1.1, soit "+10 %")
    est modulé par le critère 63 (facteur_modulation = 0.7) lorsque la publication a
    moins de 2 ans. Avant la correction, le poids effectif de 65 valait 1.1 × 0.7 = 0.77
    — un effet NÉGATIF sur le score final, alors que 65 est un critère positif. Après
    correction : 1 + (1.1 − 1) × 0.7 = 1.07, soit une augmentation amoindrie de +7 % (au
    lieu de +10 %) — l'effet reste bien positif, seulement atténué, comme voulu.

    Un modulateur peut lui-même être la cible d'un AUTRE modulateur (chaîne de
    modulateurs, ex. la grille du 11/09/2026 contient 4.1.1.1 → 4.1.1 → 4.1 → 4, un
    raffinement en cascade de la qualité de l'accès ouvert : voie dorée, puis gold pur,
    puis voie diamant). Le facteur_modulation d'un modulateur est lui aussi une grandeur
    multiplicative centrée sur 1 (« pas d'effet » = 1), donc la même règle d'identité
    s'applique de proche en proche : le facteur effectif d'un modulateur est
        1 + (son propre facteur_modulation − 1) × (produit des facteurs effectifs de ses
        propres modulateurs directs répondus "Oui" et non désactivés)
    — résolu RÉCURSIVEMENT par effective_modulation_factor(). Quand plusieurs modulateurs
    actifs ciblent directement le même critère (coefficient, points, ou un autre
    modulateur), leurs facteurs effectifs individuels sont d'abord multipliés entre eux,
    puis cette unique règle d'identité leur est appliquée une seule fois — l'ordre dans
    lequel les modulateurs sont pris en compte n'a donc aucune importance sur le résultat.
    Un critère de rôle « modulateur » ne contribue donc jamais lui-même à score_base ou au
    coefficient (cf. classify_role ci-dessus) : son seul effet passe par cette cascade
    jusqu'au critère de rôle « points » ou « coefficient » qu'il affine en bout de chaîne.
    Un cycle dans une chaîne de modulateurs est une erreur de grille (ValueError), pas un
    cas à gérer silencieusement.
  - Un critère "gate" (doté d'une colonne desactive_si non vide, c'est-à-dire id_parent
    d'au moins un autre critère) DÉSACTIVE tous ses descendants — directs et indirects,
    via la chaîne id_parent — quand sa réponse égale desactive_si (en pratique "Non" pour
    tous les gates actuels de la grille : un sous-critère de décomposition infinitésimale
    n'est pertinent que si le fait décrit par son parent est avéré). Un critère désactivé
    est EXCLU du calcul (score_base, coefficient, et rôle de modulateur), quelle que soit
    sa propre réponse — plutôt que simplement neutre — pour bien traduire l'idée de « non
    pertinent » plutôt que « non renseigné ».
  - Des critères peuvent être mutuellement EXCLUSIFS (colonne exclusif_de — ex. le XOR
    entre 5 « revue académique », 25 « actes de colloque » et 26 « ouvrage »). Avant tout
    calcul, resolve_exclusions() parcourt les réponses : si un critère d'un groupe répond
    "Oui", les autres membres du groupe sont automatiquement inférés "Non" (sauf s'ils ont
    eux-mêmes déjà reçu une réponse "Oui" explicite, auquel cas c'est une contradiction et
    une ValueError est levée plutôt que de la résoudre silencieusement). Cette inférence
    réutilise ensuite le mécanisme desactive_si déjà en place : 25 et 26 sont eux-mêmes
    des gates de leurs propres enfants, donc les inférer "Non" suffit à exclure toute leur
    sous-arborescence du calcul.
  - Un critère non répondu (absent du dict de réponses), ou répondu "Indéterminé" (ou
    "Vide", libellé de la grille du 30/09/2026), est traité comme neutre : il ne contribue
    ni au score_base ni au coefficient, et un modulateur non observé ne modifie rien —
    convention à valider par l'auteur.

RÉPONSE QUI ACTIVE UN CRITÈRE (colonne optionnelle active_si, ajout du 02/10/2026)
-----------------------------------------------------------------------------------
Un critère contribue (points, coefficient, ou modulation de ses cibles) quand sa réponse
égale active_si — "Oui" par défaut, ce qui redonne exactement le comportement antérieur.
Convention des grilles (rétablie le 02/10/2026) : tout critère est formulé de sorte que
son poids s'applique à "Oui" (un Zéro-défaut décrit le défaut : « fait-il l'objet d'un avis
de rétractation ? »). active_si ne sert que de garde-fou pour une grille qui formulerait
encore un critère pénalisant en « exempt de… » : la pénalité vaut alors pour "Non".

FORMAT « CALIBRATION » (ponderation_calibration_*.csv)
------------------------------------------------------
load_grid() accepte aussi les fichiers de calibration (colonnes reponse_attendue, statut,
remarque, parametre, automatisation ; pas de desactive_si, exclusif_de ni active_si). Les
colonnes manquantes sont reconstituées par complete_missing_columns() :
  - desactive_si = "Non" pour tout critère parent d'au moins un autre (règle vérifiée sur
    la grille canonique : ses 38 gates sont exactement ses 38 parents) ;
  - exclusif_de = groupes de DEFAULT_EXCLUSIVE_GROUPS (5 XOR 25 XOR 26, documenté dans les
    remarques de ces critères) ;
  - active_si = "Non" pour un critère formulé négativement (« exempt… », « Aucun… ») et
    doté d'un poids de pénalité (coefficient ou facteur < 1, points < 0), "Oui" sinon —
    aucun dans la grille canonique ni dans ponderation_calibration_20261002.csv.

Usage :
    python3 -m grille.score_engine                  # lance les exemples de démonstration
    python3 -m grille.score_engine mon_travail.json  # calcule le score pour un jeu de
                                                      # réponses fourni en JSON
                                                      # ({"1": "Oui", "31": "Non", ...})
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Par défaut : data/criteres_grille_evaluation.csv, relatif à la racine du projet (un
# niveau au-dessus de ce fichier, qui vit dans grille/) — remplace l'ancien
# CSV_PATH = "criteres_grille_evaluation.csv" qui supposait une exécution depuis le même
# répertoire que le script. Reste surchargeable (argument path= de compute_score/load_grid,
# ou premier argument CLI d'un autre outil qui les appelle).
CSV_PATH = str(Path(__file__).resolve().parent.parent / "data" / "criteres_grille_evaluation.csv")


NUMERIC_FIELDS = ("poids_points", "poids_coefficient", "facteur_modulation")

# Réponses équivalentes à une absence de réponse ("Vide" : grille du 30/09/2026).
EMPTY_ANSWERS = ("", "Vide")

# Groupes d'exclusion mutuelle appliqués à une grille sans colonne exclusif_de.
DEFAULT_EXCLUSIVE_GROUPS = (("5", "25", "26"),)

# Formulation négative d'un critère : « … est-il exempt de … ? », « Aucun des auteurs … ».
NEGATIVE_WORDING = re.compile(r"\bexempte?s?\b|^\s*Aucun", re.IGNORECASE)


def active_answer(row):
    """Réponse qui fait contribuer le critère ("Oui" par défaut, cf. docstring du module)."""
    return (row.get("active_si") or "").strip() or "Oui"


def _normalize_decimal(value):
    """Accepte les deux notations décimales (« 1.5 » et « 1,5 » à l'européenne) : renvoie
    la valeur avec un point comme séparateur. Toute autre chaîne est laissée telle quelle,
    pour que validate_grid la signale comme non numérique."""
    if value is None:
        return value
    stripped = value.strip()
    if stripped.count(",") == 1 and "." not in stripped:
        return stripped.replace(",", ".")
    return value


def flatten_answers(answers):
    """Ramène un jeu de réponses à {id: "Oui"|"Non"|"Indéterminé"}. Accepte aussi bien
    l'ancien format plat que le format enrichi de answers.json (une entrée par critère,
    {"intitulé", "conditionne", "est conditionné par", "activé si", "réponse", "preuve"}).
    Une réponse vide est ignorée (critère non répondu ou inactif)."""
    flat = {}
    for crit_id, value in answers.items():
        if isinstance(value, dict):
            value = value.get("réponse", "")
        if value not in EMPTY_ANSWERS:
            flat[crit_id] = value
    return flat


def _has(value):
    return value is not None and value.strip() != ""


def classify_role(row):
    """Détermine le rôle de pondération d'un critère (points / coefficient / modulateur /
    aucun), et lève une ValueError si plusieurs rôles sont simultanément renseignés — un
    garde-fou de calcul en plus de la validation structurelle de validate_grid()."""
    present = {
        "points": _has(row.get("poids_points")),
        "coefficient": _has(row.get("poids_coefficient")),
        "modulateur": _has(row.get("modulateur_de")),
    }
    roles = [name for name, is_present in present.items() if is_present]
    if len(roles) > 1:
        raise ValueError(
            f"Critère {row.get('id')} : rôles de pondération multiples {roles} — un critère "
            f"ne peut avoir qu'un seul rôle parmi poids_points, poids_coefficient et "
            f"modulateur_de/facteur_modulation (règle du 11/09/2026)"
        )
    return roles[0] if roles else "aucun"


def validate_grid(criteria):
    """Valide la structure de la grille et lève une ValueError unique listant TOUTES les
    violations trouvées (plutôt que de s'arrêter à la première), pour permettre de
    corriger la grille en une seule passe après une édition manuelle.

    Vérifie : unicité des ids (garantie par construction, contrôlée par sécurité),
    existence des id_parent référencés, exclusivité des trois rôles de pondération par
    critère, cohérence modulateur_de/facteur_modulation (les deux ensemble ou ni l'un ni
    l'autre), existence des ids ciblés par modulateur_de et exclusif_de, symétrie de
    exclusif_de, validité numérique de poids_points/poids_coefficient/facteur_modulation,
    et absence de cycle dans le graphe des modulateurs (indispensable à la résolution
    récursive des chaînes de modulateurs).
    """
    problems = []

    for crit_id, row in criteria.items():
        # id_parent référencé
        parent = (row.get("id_parent") or "").strip()
        if parent and parent not in criteria:
            problems.append(f"{crit_id} : id_parent {parent!r} inconnu")

        # exclusivité des rôles
        try:
            classify_role(row)
        except ValueError as e:
            problems.append(str(e))

        # cohérence modulateur_de / facteur_modulation
        has_mod = _has(row.get("modulateur_de"))
        has_fact = _has(row.get("facteur_modulation"))
        if has_mod != has_fact:
            problems.append(
                f"{crit_id} : modulateur_de ({row.get('modulateur_de')!r}) et facteur_modulation "
                f"({row.get('facteur_modulation')!r}) doivent être renseignés ensemble ou ni l'un ni l'autre"
            )

        # réponse d'activation
        if active_answer(row) not in ("Oui", "Non"):
            problems.append(f"{crit_id} : active_si doit valoir \"Oui\" ou \"Non\" ({row.get('active_si')!r})")

        # validité numérique
        for field in ("poids_points", "poids_coefficient", "facteur_modulation"):
            v = (row.get(field) or "").strip()
            if v:
                try:
                    float(v)
                except ValueError:
                    problems.append(f"{crit_id} : {field} non numérique ({v!r})")

        # cibles de modulateur_de
        if has_mod:
            for target_id in row["modulateur_de"].split(";"):
                target_id = target_id.strip()
                if target_id and target_id not in criteria:
                    problems.append(f"{crit_id} : modulateur_de référence un id inconnu {target_id!r}")

        # exclusif_de : cibles connues + symétrie
        excl = (row.get("exclusif_de") or "").strip()
        if excl:
            for other_id in excl.split(";"):
                other_id = other_id.strip()
                if not other_id:
                    continue
                if other_id not in criteria:
                    problems.append(f"{crit_id} : exclusif_de référence un id inconnu {other_id!r}")
                    continue
                other_excl = {o.strip() for o in (criteria[other_id].get("exclusif_de") or "").split(";") if o.strip()}
                if crit_id not in other_excl:
                    problems.append(
                        f"{crit_id} : exclusif_de liste {other_id!r}, mais {other_id!r} ne liste pas {crit_id!r} en retour (asymétrie)"
                    )

    # cycles dans le graphe des modulateurs (modulateur_id -> cible_id)
    graph = defaultdict(list)
    for crit_id, row in criteria.items():
        if _has(row.get("modulateur_de")):
            for target_id in row["modulateur_de"].split(";"):
                target_id = target_id.strip()
                if target_id in criteria:
                    graph[crit_id].append(target_id)

    WHITE, GREY, BLACK = 0, 1, 2
    color = {crit_id: WHITE for crit_id in criteria}

    def visit(node, path):
        color[node] = GREY
        for neighbor in graph.get(node, []):
            if color[neighbor] == GREY:
                cycle = " → ".join(path[path.index(neighbor):] + [neighbor])
                problems.append(f"cycle détecté dans le graphe des modulateurs : {cycle}")
            elif color[neighbor] == WHITE:
                visit(neighbor, path + [neighbor])
        color[node] = BLACK

    for crit_id in criteria:
        if color[crit_id] == WHITE:
            visit(crit_id, [crit_id])

    if problems:
        raise ValueError(
            f"Grille invalide : {len(problems)} problème(s) détecté(s) :\n" + "\n".join(f"  - {p}" for p in problems)
        )


def _is_penalty(row):
    """Le poids du critère réduit-il le score (coefficient ou facteur < 1, points < 0) ?"""
    try:
        role = classify_role(row)
        if role == "points":
            return float(row["poids_points"]) < 0
        if role == "coefficient":
            return float(row["poids_coefficient"]) < 1
        if role == "modulateur":
            return float(row["facteur_modulation"]) < 1
    except ValueError:
        pass  # rôles multiples ou valeur non numérique : signalés par validate_grid
    return False


def complete_missing_columns(criteria, fieldnames):
    """Reconstitue desactive_si, exclusif_de et active_si quand la grille ne les fournit pas
    (format « calibration », cf. docstring du module). Modifie criteria sur place."""
    if "desactive_si" not in fieldnames:
        parents = {(row.get("id_parent") or "").strip() for row in criteria.values()}
        for crit_id, row in criteria.items():
            row["desactive_si"] = "Non" if crit_id in parents else ""
    if "exclusif_de" not in fieldnames:
        for row in criteria.values():
            row["exclusif_de"] = ""
        for group in DEFAULT_EXCLUSIVE_GROUPS:
            if all(crit_id in criteria for crit_id in group):
                for crit_id in group:
                    criteria[crit_id]["exclusif_de"] = ";".join(o for o in group if o != crit_id)
    if "active_si" not in fieldnames:
        for row in criteria.values():
            negative = bool(NEGATIVE_WORDING.search(row.get("critere") or ""))
            row["active_si"] = "Non" if negative and _is_penalty(row) else "Oui"


def load_grid(path=CSV_PATH):
    # Depuis la grille simplifiée du 11/09/2026, le fichier est exporté au format
    # point-virgule avec BOM UTF-8 (convention utilisée par l'auteur pour tous ses fichiers
    # de calibration/grille manuels) plutôt qu'au format virgule sans BOM du générateur
    # d'origine — d'où encoding="utf-8-sig" et delimiter=";" ci-dessous.
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        criteria = {row["id"]: row for row in reader}
        fieldnames = reader.fieldnames or []

    for row in criteria.values():
        for field in NUMERIC_FIELDS:
            if field in row:
                row[field] = _normalize_decimal(row[field])

    complete_missing_columns(criteria, fieldnames)
    validate_grid(criteria)

    # Enfants directs de chaque critère (pour la propagation récursive de la désactivation).
    children_of = defaultdict(list)
    for row in criteria.values():
        if row["id_parent"]:
            children_of[row["id_parent"]].append(row["id"])

    # Index des modulateurs actifs, groupés par critère cible : cible_id -> [modulateur_id, ...]
    # (le facteur n'est plus stocké ici : il est recalculé par effective_modulation_factor,
    # qui tient compte des éventuelles chaînes de modulateurs.)
    modulators_by_target = defaultdict(list)
    for row in criteria.values():
        targets = (row.get("modulateur_de") or "").strip()
        if not targets:
            continue
        for target_id in targets.split(";"):
            target_id = target_id.strip()
            if target_id:
                modulators_by_target[target_id].append(row["id"])

    return criteria, children_of, modulators_by_target


def effective_modulation_factor(criteria, modulators_by_target, answers, deactivated, modulator_id, _visiting=frozenset()):
    """Facteur de modulation effectif d'un critère modulateur, chaînes comprises.

    CORRECTION DU 11/09/2026 : un modulateur n'agit plus par multiplication directe de son
    facteur_modulation sur la grandeur qu'il cible. Le facteur_modulation d'un modulateur
    étant lui-même une grandeur multiplicative centrée sur 1 (« pas d'effet » = 1, comme un
    poids_coefficient), un modulateur qui cible un AUTRE modulateur (chaîne, ex.
    4.1.1.1 → 4.1.1 → 4.1 → 4) doit agir sur l'écart à 1 de ce dernier, pas sur sa valeur
    brute — cf. docstring du module pour l'exemple qui a motivé cette correction (critères
    63 → 65/66). Le facteur effectif d'un modulateur est donc :

        1 + (son propre facteur_modulation − 1) × (produit des facteurs effectifs de ses
        propres modulateurs directs, répondus "Oui" et non désactivés)

    résolu récursivement, de proche en proche jusqu'au bout de la chaîne. Un modulateur
    sans modulateur actif le ciblant renvoie simplement son propre facteur_modulation,
    inchangé (le produit vide vaut 1, donc 1 + (f−1)×1 = f). validate_grid() garantit
    l'absence de cycle en amont ; _visiting reste une sécurité de dernier recours en cas
    d'appel direct hors du chemin normal (ex. tests unitaires sur une grille non validée).
    """
    if modulator_id in _visiting:
        raise ValueError(f"Cycle détecté dans la chaîne de modulateurs impliquant {modulator_id!r}")
    row = criteria[modulator_id]
    own_factor = float(row["facteur_modulation"])
    combined_sub_factor = 1.0
    for sub_modulator_id in modulators_by_target.get(modulator_id, []):
        if sub_modulator_id in deactivated:
            continue
        if answers.get(sub_modulator_id) != active_answer(criteria[sub_modulator_id]):
            continue
        combined_sub_factor *= effective_modulation_factor(
            criteria, modulators_by_target, answers, deactivated, sub_modulator_id, _visiting | {modulator_id}
        )
    return 1.0 + (own_factor - 1.0) * combined_sub_factor


def effective_weight(criteria, modulators_by_target, answers, deactivated, crit_id, base_weight, identity=1.0):
    """Applique au poids de base d'un critère (rôle points ou coefficient) les facteurs de
    tout modulateur direct actif le ciblant, chaînes de modulateurs comprises.

    CORRECTION DU 11/09/2026 : les modulateurs actifs ciblant directement crit_id sont
    d'abord combinés entre eux par simple produit de leurs facteurs effectifs individuels
    (effective_modulation_factor, qui applique déjà la règle d'identité de proche en
    proche pour les chaînes) ; cette combinaison est ensuite appliquée UNE SEULE FOIS au
    poids de base via la règle d'identité : identity + (base_weight − identity) × produit.
    `identity` vaut 1.0 pour un rôle « coefficient » (grandeur multiplicative — c'est le
    cas par défaut) et 0.0 pour un rôle « points » (grandeur additive : la formule se
    réduit alors à base_weight × produit, identique au comportement d'origine — les
    critères de rôle points ne sont pas concernés par la correction du 11/09/2026, qui ne
    porte que sur les grandeurs centrées sur 1 : poids_coefficient et facteur_modulation).
    """
    combined_factor = 1.0
    for modulator_id in modulators_by_target.get(crit_id, []):
        if modulator_id in deactivated:
            continue
        if answers.get(modulator_id) == active_answer(criteria[modulator_id]):
            combined_factor *= effective_modulation_factor(criteria, modulators_by_target, answers, deactivated, modulator_id)
    return identity + (base_weight - identity) * combined_factor


def resolve_exclusions(criteria, answers):
    """Applique les relations d'exclusion mutuelle (colonne exclusif_de).

    Si un critère répond "Oui" et possède une colonne exclusif_de non vide, chaque autre
    membre du groupe qu'elle désigne est automatiquement inféré "Non" dans le dict de
    réponses retourné (une copie : le dict passé en argument n'est jamais modifié). Si un
    autre membre du groupe a lui-même déjà reçu une réponse "Oui" explicite, c'est une
    contradiction avec la relation d'exclusion documentée dans la grille : une ValueError
    est levée plutôt que de trancher silencieusement en faveur de l'un ou l'autre.

    Un critère répondu "Non" ou "Indéterminé" par ailleurs n'est jamais modifié par cette
    fonction ; seule une réponse absente peut être complétée par une inférence "Non".
    """
    resolved = dict(answers)
    for crit_id, row in criteria.items():
        excl = (row.get("exclusif_de") or "").strip()
        if not excl:
            continue
        if resolved.get(crit_id) != "Oui":
            continue
        for other_id in excl.split(";"):
            other_id = other_id.strip()
            if not other_id:
                continue
            if other_id not in criteria:
                raise ValueError(f"Critère {crit_id} : exclusif_de référence un id inconnu {other_id!r}")
            if resolved.get(other_id) == "Oui":
                raise ValueError(
                    f"Contradiction : {crit_id} et {other_id} sont mutuellement exclusifs "
                    f"(exclusif_de) mais tous deux répondus \"Oui\""
                )
            resolved[other_id] = "Non"
    return resolved


def compute_deactivated(criteria, children_of, answers):
    """Calcule l'ensemble des critères désactivés par un gate parent (récursivement).

    Un gate (desactive_si non vide) désactive tous ses descendants quand sa PROPRE
    réponse égale desactive_si. La désactivation se propage : si un descendant est
    lui-même un gate désactivé, ses propres enfants sont désactivés aussi, que ce
    descendant ait ou non été répondu.
    """
    deactivated = set()

    def deactivate_subtree(crit_id):
        for child_id in children_of.get(crit_id, []):
            if child_id not in deactivated:
                deactivated.add(child_id)
                deactivate_subtree(child_id)

    for crit_id, row in criteria.items():
        gate_trigger = (row.get("desactive_si") or "").strip()
        if gate_trigger and answers.get(crit_id) == gate_trigger:
            deactivate_subtree(crit_id)

    return deactivated


def compute_score(answers, path=CSV_PATH, verbose=True):
    """
    answers : dict {id_critere: "Oui"|"Non"|"Indéterminé"}. Les critères absents du
    dict, répondus "Indéterminé", ou désactivés par un gate parent, sont traités comme
    neutres (aucune contribution). Retourne (score_base, coefficient, score_final, détail)
    où détail liste les contributions individuelles pour audit/débogage.

    Avant tout calcul, les relations d'exclusion mutuelle (exclusif_de) sont résolues via
    resolve_exclusions(). Le rôle de chaque critère (points / coefficient / modulateur /
    aucun) est ensuite déterminé par classify_role() : seuls les rôles "points" et
    "coefficient" contribuent directement au score ; un critère "modulateur" n'agit que
    sur le poids de ses cibles, jamais sur le score de façon autonome.
    """
    criteria, children_of, modulators_by_target = load_grid(path)
    answers = resolve_exclusions(criteria, flatten_answers(answers))
    deactivated = compute_deactivated(criteria, children_of, answers)

    score_base = 0.0
    coefficient = 1.0
    detail = []

    for crit_id, row in criteria.items():
        if crit_id in deactivated:
            continue
        role = classify_role(row)
        if role in ("modulateur", "aucun"):
            continue  # pas de contribution directe : cf. docstring du module
        if answers.get(crit_id) != active_answer(row):
            continue  # neutre : absent, "Indéterminé", ou réponse ≠ active_si ("Oui" par défaut)

        if role == "points":
            base_pts = float(row["poids_points"])
            pts = effective_weight(criteria, modulators_by_target, answers, deactivated, crit_id, base_pts, identity=0.0)
            score_base += pts
            detail.append(("points", crit_id, row["critere"][:70], pts))
        elif role == "coefficient":
            base_coef = float(row["poids_coefficient"])
            coef = effective_weight(criteria, modulators_by_target, answers, deactivated, crit_id, base_coef, identity=1.0)
            if coef != 1.0:
                coefficient *= coef
                detail.append(("coefficient", crit_id, row["critere"][:70], coef))

    coefficient = max(coefficient, 0.0)  # plancher à 0, pas de plafond
    score_final = score_base * coefficient

    if verbose:
        print(f"score_base      = {score_base}")
        print(f"coefficient     = {coefficient}")
        print(f"score_final     = {score_final}")
        if deactivated:
            print(f"critères désactivés par un gate ({len(deactivated)}) : {sorted(deactivated, key=lambda x: [int(p) for p in x.split('.')])}")
        if detail:
            print("détail des contributions :")
            for kind, cid, txt, val in detail:
                print(f"  [{kind:11}] {cid:8} x{val:<6} {txt}")
    return score_base, coefficient, score_final, detail


def demo():
    print("=== Exemple 1 : peer-review + quelques critères structurels (rôle points) ===")
    answers_1 = {
        "1": "Oui",     # peer-review existe (coefficient 5.0)
        "1.1": "Oui", "1.2": "Oui", "1.3": "Oui",   # modalités de qualité (modulent 1, x1.5 chacune)
        "1.4": "Non", "1.5": "Non", "1.6": "Non",   # pas de défaut de conformité (modulateurs à 0,7 non déclenchés)
        "47": "Oui", "48": "Oui", "49": "Oui", "50": "Oui", "51": "Oui",  # structure IMRaD complète (rôle points)
        "45": "Oui",  # résultats originaux mentionnés (rôle points)
    }
    compute_score(answers_1)

    print("\n=== Exemple 2 : même travail, mais le gate 1 répond \"Non\" (pas de peer-review) ===")
    print("(1.1 à 1.6 sont désormais hors de propos : desactive_si de 1 vaut \"Non\" et 1 répond \"Non\" ;")
    print(" même si on leur avait quand même donné une réponse, ils seraient exclus du calcul.)")
    answers_2 = dict(answers_1, **{"1": "Non", "1.1": "Oui", "1.2": "Oui", "1.3": "Oui"})
    compute_score(answers_2)

    print("\n=== Exemple 3 : rétractation avérée (critère 30, coefficient calibré à 0.1) ===")
    answers_3 = dict(answers_1, **{"30": "Oui"})
    compute_score(answers_3)

    print("\n=== Exemple 4 : cumul de plusieurs manquements éthiques Retraction Watch (58.x) ===")
    answers_4 = dict(answers_1, **{"58": "Oui", "58.5": "Oui", "58.6": "Oui"})
    compute_score(answers_4)

    print("\n=== Exemple 5a : chaîne de modulateurs — un seul niveau (4 + 4.1) ===")
    print("(critère 4 « accès ouvert », coefficient 2.0 ; 4.1 « voie dorée » le module x1.1 ;")
    print(" depuis la correction du 11/09/2026, le poids effectif de 4 vaut")
    print(" 1 + (2.0 − 1) × 1.1 = 2.1, et non plus 2.0 × 1.1 = 2.2.)")
    answers_5a = dict(answers_1, **{"4": "Oui", "4.1": "Oui"})
    compute_score(answers_5a)

    print("\n=== Exemple 5b : même chaîne, complète sur ses 3 niveaux (4 + 4.1 + 4.1.1 + 4.1.1.1) ===")
    print("(4.1.1 « gold pur » module 4.1 x1.5, et 4.1.1.1 « voie diamant » module 4.1.1 x1.5 — chaque")
    print(" niveau applique désormais la règle d'identité à son tour : facteur effectif de 4.1.1.1 = 1.5")
    print(" (rien ne le module) ; de 4.1.1 = 1 + (1.5−1)×1.5 = 1.75 ; de 4.1 = 1 + (1.1−1)×1.75 = 1.175 ;")
    print(" et le poids effectif de 4 = 1 + (2.0−1)×1.175 = 2.175 — au lieu de 4.95 avec l'ancienne")
    print(" multiplication directe (2.0×1.1×1.5×1.5) : chaque niveau de raffinement compte toujours,")
    print(" mais son effet reste borné par l'écart à l'identité plutôt que de composer sans limite.)")
    answers_5b = dict(answers_1, **{"4": "Oui", "4.1": "Oui", "4.1.1": "Oui", "4.1.1.1": "Oui"})
    compute_score(answers_5b)

    print("\n=== Exemple 6 : critère 5 (revue académique) répondu \"Oui\" — exclusion de 25 et 26 ===")
    print("(exclusif_de infère automatiquement 25 = \"Non\" et 26 = \"Non\" ; comme 25 et 26 sont")
    print(" eux-mêmes des gates de leurs propres enfants, 25.1 — répondu \"Oui\" ci-dessous par")
    print(" hypothèse, comme si on avait rempli la grille en pensant, à tort, que ce travail")
    print(" relevait à la fois d'une revue et d'actes de colloque — se retrouve exclu du calcul")
    print(" au même titre que le reste de la sous-arborescence de 25 et de 26.)")
    answers_6 = dict(answers_1, **{"5": "Oui", "5.1": "Oui", "25.1": "Oui"})
    compute_score(answers_6)

    print("\n=== Exemple 7 : contradiction — 5 et 25 répondus \"Oui\" simultanément ===")
    print("(devrait lever une ValueError plutôt que de trancher silencieusement en faveur de l'un des deux)")
    answers_7 = dict(answers_1, **{"5": "Oui", "25": "Oui"})
    try:
        compute_score(answers_7)
    except ValueError as e:
        print(f"ValueError (attendue) : {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            answers = json.load(f)
        compute_score(answers)  # format plat ou enrichi, cf. flatten_answers
    else:
        demo()
