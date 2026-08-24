Front : 
- [x] indiquer des informations sur le fichier Leiden utilisé (actuellement seule la date d'import est indiquée, il faut au minimum la date d'import, la période couverte, le nombre de lignes, le nombre d'institutions)
- [x] trier les déciles de 1 à 10 dans la liste des groupes de comparaison disponibles. Actuellement le décile 10 est entre le décile 1 et le décile 2 (tri alphabétique)
- [x] indiquer le décile Leiden d'appartenance de l'établissement de référence, actuellement seulement nom, ROR ID, pays.

Back : 
- [x] Quand c'est possible, utiliser les dates de modif openalex (sync filters) avec les clés API membres (https://help.openalex.org/api/filtering/#sync-filters-paid-plans) pour consommer moins de requêtes quotidiennes.

Bonus (trouvé en cours de route, non listé initialement) :
- [x] Bug de comparaison ROR : `instance_config.ror_id` est stocké avec le préfixe complet `https://ror.org/...` (format OpenAlex) alors que `leiden_snapshot.ror_id` est stocké sans préfixe. Les comparaisons directes entre les deux ne matchaient donc jamais, ce qui cassait silencieusement deux choses : (1) l'établissement de référence n'était jamais exclu de ses propres groupes de comparaison géographique/décile, (2) l'indicateur Leiden "own value" (percentile top 10%, MNCS) affichait toujours "—". Fix centralisé dans `app/services/ror.py::normalize_ror`.