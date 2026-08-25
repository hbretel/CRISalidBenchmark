Front : 
- [x] indiquer des informations sur le fichier Leiden utilisé (actuellement seule la date d'import est indiquée, il faut au minimum la date d'import, la période couverte, le nombre de lignes, le nombre d'institutions)
- [x] trier les déciles de 1 à 10 dans la liste des groupes de comparaison disponibles. Actuellement le décile 10 est entre le décile 1 et le décile 2 (tri alphabétique)
- [x] indiquer le décile Leiden d'appartenance de l'établissement de référence, actuellement seulement nom, ROR ID, pays.
- [x] indiquer les années sur lesquelles le h-index est calculé (habituellement le h-index n'a pas d'année de départ, ici nous le limitons à la période concernée)
- [x] bug probable : la carte thématique ne montre qu'un seul domaine, malgré un taux de spécialisation faible. Elle ne doit pas fonctionner correctement.
- [x] la section "Topics signature" indique "Le cache de distribution par topic des pairs n'est pas encore peuplé. Rendez-vous sur Paramètres du benchmark pour déclencher le calcul." mais la page Paramètres du benchmark ne comporte pas de moyen de lancer le calcul
- [x] Améliorer la treemap des sujets openalex : 
  - [x] actuellement elle ne prend en compte que les sujets de niveau "Field, sans interactivité, alors que son titre indique "Topics OpenAlex". La rendre interactive (cliquer sur un domaine pour drilldown).
  - [x] actuellement elle n'affiche les titres des sujets que dans certains cas. Afficher les noms des sujets et le nombre de publications correspondant autant que possible.
  - [x] actuellement elle affiche tous les sujets dans la même couleur (bleu). Distinguer les sujets par couleur (une couleur différente par Field puis déclinaisons de la couleur du Field en cas de drilldown).
- [x] Améliorer le tableau des Topics signature :
  - [x] actuellement les topics sont désignés par leur ID sous forme "https://openalex.org/T****". Les désigner par leur nom OpenAlex
  - [x] actuellement les colonnes ne sont pas nommées et non triables. Les nommer par exemple [Nom du Topic, Part établissement/monde, Moyenne groupe de comparaison/monde, Taux de spécialisation], ajouter une colonne "Nombre de publications établissement" avant "Part établissement/monde" et rendre le tableau triable sur chaque colonne.
  - [x] actuellement les parts établissement et moyennes du groupe de comparaison sont en %, ce qui donne toujours des 0,*%. Les compter en &permil;
- [x] placer la section "Indice de Herfindahl" avant la treemap par sujets, mais mieux expliciter la signification : au lieu de "peu spécialisé", "moyennement spécialisé", "très spécialisé", indiquer par exemple "établissement généraliste : *n* fields OpenAlex sur 26 comptent au moins *n*% des publications chacun", ou bien "établissement très spécialisé : *n* fields représentent à eux seuls *n*% des publications", en fonction du niveau de spécialisation calculé.

Back : 
- [x] Quand c'est possible, utiliser les dates de modif openalex (sync filters) avec les clés API membres (https://help.openalex.org/api/filtering/#sync-filters-paid-plans) pour consommer moins de requêtes quotidiennes.

Bonus (trouvé en cours de route, non listé initialement) :
- [x] Bug de comparaison ROR : `instance_config.ror_id` est stocké avec le préfixe complet `https://ror.org/...` (format OpenAlex) alors que `leiden_snapshot.ror_id` est stocké sans préfixe. Les comparaisons directes entre les deux ne matchaient donc jamais, ce qui cassait silencieusement deux choses : (1) l'établissement de référence n'était jamais exclu de ses propres groupes de comparaison géographique/décile, (2) l'indicateur Leiden "own value" (percentile top 10%, MNCS) affichait toujours "—". Fix centralisé dans `app/services/ror.py::normalize_ror`.