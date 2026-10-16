# -*- coding: utf-8 -*-
"""
Seuils paramétrables des critères (colonne `parametre` des grilles de calibration).

Un critère « à seuil » nomme son seuil N (et parfois un minimum M) dans son libellé —
« La part des citations … est-elle inférieure ou égale à N % ? » — et en donne la valeur
dans la colonne `parametre` : « N = 30 % ; calcul si au moins M = 10 citations
(paramétrables) ». Ce module lit et réécrit ces valeurs sans toucher au reste du texte, et
substitue les valeurs dans le libellé pour l'affichage.
"""
import re

PARAM_RE = re.compile(r"\b([NM])\s*=\s*(\d+(?:[.,]\d+)?)\s*([^;(]*)")
LABEL_PLACEHOLDER = re.compile(r"\b([NM])\b")


def parse_parameters(text):
    """{"N": 30.0, "M": 10.0} d'après le texte de la colonne parametre (dict vide sinon)."""
    return {name: float(value.replace(",", ".")) for name, value, _unit in PARAM_RE.findall(text or "")}


def parameter_units(text):
    """Unité de chaque seuil, telle qu'écrite après sa valeur : {"N": "%", "M": "citations"}."""
    units = {}
    for name, _value, unit in PARAM_RE.findall(text or ""):
        units[name] = unit.replace("par défaut", "").strip()
    return units


def format_value(value):
    """30.0 -> "30" ; 1.5 -> "1,5" (convention décimale des grilles)."""
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:g}".replace(".", ",")


def set_parameters(text, values):
    """Réécrit les valeurs de `values` ({"N": 25}) dans le texte de la colonne parametre,
    sans modifier le reste du texte."""
    def replace(match):
        name = match.group(1)
        if name not in values:
            return match.group(0)
        return match.group(0).replace(match.group(2), format_value(values[name]), 1)

    return PARAM_RE.sub(replace, text or "")


def is_threshold_criterion(row):
    """Le critère dépend-il d'un seuil (N/M dans le libellé, ou colonne parametre renseignée —
    y compris un seuil non numérique comme la table SCImago de 52) ?"""
    return bool(LABEL_PLACEHOLDER.search(row.get("critere") or "") or (row.get("parametre") or "").strip())


def render_label(label, values, fmt="{}"):
    """Libellé avec N/M remplacés par leur valeur (chaque valeur mise en forme par `fmt`,
    ex. "**{}**" pour l'afficher en gras). Un N/M sans valeur reste tel quel."""
    def replace(match):
        name = match.group(1)
        return fmt.format(format_value(values[name])) if name in values else name

    return LABEL_PLACEHOLDER.sub(replace, label or "")
