"""
Moteur de grille : chargement, validation et calcul de score de la grille de critères
d'évaluation qualitative (data/criteres_grille_evaluation.csv).

Modules :
  - score_engine  : chargement/validation de la grille (load_grid, validate_grid,
                    classify_role) et calcul du score d'un travail (compute_score),
                    en tenant compte des modulateurs, gates (desactive_si) et relations
                    d'exclusion mutuelle (exclusif_de). Anciennement score_test.py.
  - validate      : point d'entrée CLI de validation structurelle, autour de
                    score_engine.validate_grid()/load_grid(). Anciennement build_csv.py.
  - build_coef_div10 : génère une variante rééquilibrée de la grille canonique (tous les
                    poids_coefficient > 1 rapprochés de 1) pour des tests comparatifs.
                    Anciennement build_csv_coef_div10.py.
"""
