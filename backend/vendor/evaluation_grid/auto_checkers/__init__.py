# -*- coding: utf-8 -*-
"""
auto_checkers -- automatisation partielle de la grille d'évaluation qualitative
(criteres_grille_evaluation.csv) : requêtes préprogrammées vers des bases bibliométriques
publiques, pour remplacer un raisonnement libre par un accès à un champ structuré chaque
fois que c'est possible.

Voir AUTOMATISATION_CRITERES.md (à la racine du projet) pour la table complète des 337
critères avec, pour chacun, son statut d'automatisation et sa justification.

Usage rapide :
    python3 -m auto_checkers.run_auto_answers --doi 10.1162/qss_a_00351 \\
        --out-prefix chaignon_2025

Modules :
    sources.py               -- appels réseau bruts (OpenAlex, Crossref, DOAJ, HAL,
                                 theses.fr, PubMed/Medline).
    type_tables.py            -- tables de correspondance type-de-base -> id-de-critère.
    publisher_lists.py        -- appartenance à des structures fédératives d'éditeurs.
    publisher_lists_data.json -- données de ces listes (à rafraîchir périodiquement).
    checkers.py               -- une fonction de décision par critère (ou famille de
                                 critères), consommant les données brutes de sources.py.
    run_auto_answers.py       -- orchestrateur en ligne de commande.
    fixtures/                 -- exemples réels capturés (Chaignon/Renisio/Gozlan) pour
                                 les tests hors-ligne.
    test_checkers.py          -- tests unitaires sur ces fixtures (aucun accès réseau).
"""
