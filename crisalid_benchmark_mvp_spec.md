# CRISalid Benchmark — Spécification technique du MVP (v1)

*Document destiné au développement (ex. via Claude Code) — v1.7 — 21 août 2026*

> Ce document traduit les décisions actées dans `crisalid_benchmark_plan_v1.md` en spécifications techniques directement implémentables. Il complète les « prochaines étapes » 1 et 2 du plan v0.2 : un MVP centré sur le **mode Basique uniquement**, au **niveau établissement uniquement**, sur les axes **impact scientifique** et **spécificité disciplinaire** uniquement.
>
> Quatre choix techniques structurants ont été tranchés avec Henri avant rédaction (résumés en §0.3). Les choix d'implémentation restants, plus mineurs, sont posés comme **défauts documentés** (marqués **[Défaut — modifiable]**) plutôt que comme blocages : à valider ou changer librement en cours de développement.
>
> **Changelog v1.1** : suite à la relecture de la v1.0, quatre corrections/ajouts ont été intégrés — (1) le Leiden Ranking Open Edition ne publie ses indicateurs qu'au niveau établissement et, au mieux, sur 5 grands domaines disciplinaires, insuffisant pour une comparaison au niveau fin des Topics OpenAlex (cf. §3.5, §4.4) ; (2) la détection de topics signature (§5.2) nécessite désormais des données de comparaison peer-relative au niveau Topic, ajoutées via un nouveau mécanisme d'ingestion à coût maîtrisé (§4.4) ; (3) l'authentification OpenAlex par clé API, désormais obligatoire, est intégrée à la configuration (§2, §3.1) ; (4) décision prise sur l'impact pondéré par citations au niveau Topic pour les pairs (§4.5) : version intermédiaire retenue, limitée aux 5 grands domaines Leiden pour le MVP, le niveau Topic fin restant en comptage seul (option (b), plus coûteuse, reportée en v2).
>
> **Changelog v1.2** : deux ajustements méthodologiques supplémentaires — (5) distinction des **publications « core »** de Leiden (sous-ensemble plus restrictif que le corpus complet, sur lequel Leiden calcule ses indicateurs d'impact) désormais intégrée : OpenAlex expose nativement un champ `is_core` sur l'objet **Source** (liste CWTS Core, ~36 000 sources), utilisé pour dériver un indicateur `is_core_publication` sur chaque `work` ingéré (cf. §3.2, §4.1, §5.1) — évite d'avoir à importer le fichier externe de classification (~3 Go) ; (6) le MVP se limite explicitement au **comptage complet (« full counting »)** pour tous les indicateurs Leiden, plus simple à expliquer à un public non bibliométricien — le **comptage fractionnel**, que CWTS privilégie pourtant par défaut pour ses propres indicateurs d'impact, est explicitement reporté en v2 (cf. §3.5, §0.2).
>
> **Changelog v1.3** : (7) le périmètre institutionnel retenu pour l'ingestion OpenAlex de l'établissement configuré passe du filtre strict `institutions.id` au filtre **`institutions.lineage`**, qui inclut les publications affiliées aux structures « enfants » ROR (composantes) de l'établissement — pertinent notamment pour les universités fusionnées/fédérales (cf. §2, §3.1, §4.1). Le même principe est appliqué aux établissements pairs dans le mécanisme de comptage par Topic (§4.4). Un écart méthodologique résiduel avec le périmètre retenu par Leiden est documenté et ne peut pas être totalement éliminé (cf. §4.1) : Leiden n'applique pas une hiérarchie ROR automatique mais une sélection curatée au cas par cas (composantes + installations conjointes, hors « organisations associées »), et les données ROR pour le système français restent, de l'aveu même d'OpenAlex, incomplètes sur ce point.
>
> **Changelog v1.4** : le schéma de `leiden_snapshot` (§3.5) est intégralement révisé sur la base du fichier réel `colonnes_leiden_open_2025.xlsx` fourni par Henri, très différent de ce qui était anticipé — (8) le fichier Zenodo est au format **XLSX**, pas CSV (§3.5, §4.2) ; (9) `Core_pubs_only` et `Frac_counting` sont des **dimensions du fichier source** (une ligne par combinaison), pas des colonnes séparées comme supposé en v1.2/v1.3 — le MVP n'importe que les lignes `Core_pubs_only=1`/`Frac_counting=0`, cohérent avec les décisions déjà prises ; (10) les noms de colonnes réels remplacent les noms anticipés (`pp_top10` → `pp_top_10`, `p_count` → `p`, `field_scope` → `field`, `counting_method` → `core_pubs_only`+`frac_counting`), avec en bonus l'indicateur normalisé continu `mncs` et les intervalles de confiance (`_lb`/`_ub`) disponibles pour la plupart des indicateurs ; (11) un risque de désalignement entre le format de `Country` (nom vs code ISO) et le `country_code` utilisé pour le groupe de pairs géographique est signalé (§3.5, §4.3).
>
> **Changelog v1.5** : à partir d'un extrait réel de données (`leiden_open_2025_sample.xlsx`, 60 lignes = 1 établissement × 1 champ × 15 périodes × les 4 combinaisons `Core_pubs_only`/`Frac_counting`), plusieurs points « à vérifier » de la v1.4 sont tranchés et de nouveaux points sont identifiés — (12) `Country` est confirmé en **nom de pays en clair** (« Pakistan »), pas en code ISO : une table de correspondance nom→ISO2 est désormais une tâche d'implémentation ferme, pas une hypothèse (§3.5, §4.3) ; (13) `ROR_ID` est stocké **sans le préfixe** `https://ror.org/` (ex. `0549hdw45`), à normaliser à la jointure avec le champ `ror` d'OpenAlex qui renvoie l'URI complète (§3.5) ; (14) `Period` est confirmé comme une **fenêtre glissante de 4 ans** (ex. `2020–2023`, avec un tiret cadratin) et **15 valeurs de périodes coexistent dans un seul fichier téléchargé** — le MVP importe désormais explicitement la période la plus récente uniquement (§3.5, §4.2) ; (15) les pourcentages (`PP_*`) sont confirmés comme des **proportions 0–1**, pas 0–100 ; (16) **point non résolu, signalé à Henri plutôt que tranché arbitrairement** : `P` (nombre de publications) prend des valeurs **non entières** dans l'extrait réel (ex. 391,166667), alors que la documentation officielle CWTS (édition Traditional) le définit comme « nombre total de publications » — écart à clarifier avant de faire confiance à ce chiffre dans l'UI (§3.5) ; (17) l'extrait ne couvrant qu'un seul `Field`, **la valeur « établissement entier » de la colonne `Field` reste non confirmée** — point bloquant pour la conception actuelle de l'axe impact scientifique au niveau établissement (§3.5, §5.1), à lever en priorité avant développement.
>
> **Changelog v1.6** : les deux points laissés en suspens en v1.5 sont **résolus** à partir d'un second extrait réel (`leiden_open_2025_full_sample.xlsx`, même établissement sur les 6 valeurs de `Field`) — (18) **`Field` prend exactement 6 valeurs** : `All sciences` (repère établissement entier, confirmé présent nativement — aucun recalcul par agrégation n'est nécessaire) et les 5 grands domaines déjà identifiés ; toutes les références à `field='all'` dans cette spec sont mises à jour vers `field='All sciences'` (§3.5, §4.3, §5.1) ; (19) la non-intégralité de `P` n'était **pas une erreur** — sur `field='All sciences'`, `P` est un entier exact ; les valeurs fractionnaires n'apparaissent que sur les lignes par domaine et s'expliquent par un fractionnement des publications interdisciplinaires entre les 5 grands domaines (mécanisme indépendant de `Frac_counting`), vérifié par sommation exacte des 5 domaines retrouvant le total `All sciences` (§3.5). **Aucun point technique n'est plus en suspens sur le schéma Leiden** (§10).
>
> **Changelog v1.7** : suite à la question d'Henri sur la cohérence du toggle core/non-core de l'axe impact scientifique (§7) avec les indicateurs Leiden réellement disponibles — **confirmé**, sur la base de l'analyse déjà conduite sur l'extrait réel (`leiden_open_2025_sample.xlsx`) : les indicateurs normalisés par percentile (`PP_top_1/5/10/50`, `MNCS`) ne sont renseignés que sur les lignes `Core_pubs_only=1` ; ils sont vides sur les lignes `Core_pubs_only=0`, où Leiden expose à la place une famille d'indicateurs différente, basée sur des **seuils de citations absolus, non normalisés par champ** (`PP_10_cits`/`PP_20_cits`/`PP_50_cits`/`PP_100_cits`). Le toggle core/non-core de `/impact-scientifique` (ajouté en v1.2) n'avait donc, jusqu'ici, aucune source Leiden valide en position « toutes les publications » pour son indicateur vedette — les lignes `Core_pubs_only=0` n'étant pas importées (décision v1.4). **Correction apportée**, exactement selon la demande d'Henri : (20) la décision d'import Leiden (§3.5, §4.2) est étendue pour charger **également** les lignes `Core_pubs_only=0` (toujours filtrées sur `Frac_counting=0`) — `leiden_snapshot` passe donc d'une ligne par (établissement, `field`, période) à une ligne par (établissement, `field`, période, `core_pubs_only`) ; (21) les colonnes `pp_10_cits`/`pp_20_cits`/`pp_50_cits`/`pp_100_cits` (chacune avec `_lb`/`_ub`) sont ajoutées au schéma (§3.5) ; (22) l'indicateur vedette de l'axe impact scientifique (§5.1) devient toggle-dépendant : `pp_top_10` en position « publications core », `pp_10_cits` en position « toutes les publications » — **ce ne sont pas des indicateurs équivalents** (percentile normalisé par champ vs seuil de citations brut), l'écart est explicitement documenté dans l'UI (§7) plutôt que présenté comme une bascule transparente du même chiffre ; (23) `weight_profiles.sub_indicator_weights` (§3.8) référence désormais une clé abstraite (`impact_normalise_leiden`) plutôt que le nom de colonne littéral `pp_top_10`, pour que le profil de pondération reste valide quel que soit l'état du toggle.

---

## 0. Cadrage

### 0.1 Ce que le MVP fait

- Un utilisateur configure l'outil pour **un seul établissement** (son ID OpenAlex / son ROR), en mode Basique (aucune dépendance à une instance CRISalid).
- L'outil synchronise chaque nuit les publications de cet établissement depuis OpenAlex, et importe annuellement le jeu de données CWTS Leiden Ranking Open Edition.
- L'utilisateur consulte deux familles d'indicateurs : **impact scientifique** et **spécificité disciplinaire**, comparés à des groupes de pairs.
- L'utilisateur construit des groupes de pairs (prédéfinis — géographiques et par tranche de taille — ou personnalisés en sélectionnant des établissements) et des profils de pondération à deux niveaux (grand critère → sous-indicateurs), sauvegardables en « vues » de benchmark.
- Toute donnée brute est rafraîchie la nuit ; les indicateurs pondérés (scores composites) sont recalculés à la demande à partir des données brutes déjà en base.

### 0.2 Ce que le MVP ne fait pas (hors périmètre explicite v1)

| Hors périmètre v1 | Renvoi au plan | Raison |
|---|---|---|
| Mode Complet / intégration `crisalid-ikg` | §3, §4.2 | Décision v1 : mode Basique uniquement pour ce MVP |
| Granularité laboratoire/pôle | §2 | Décision v1 : niveau établissement uniquement |
| Sources HAL, Scopus, Web of Science via `svp-harvester` | §4.2 | Décision v1 : OpenAlex uniquement |
| Axes impact sociétal (SDG) et impact économique | §4.4, §5 | Décision v1 : aucune source hors OpenAlex+Leiden ; ces deux axes nécessitent des sources externes non retenues pour le MVP |
| Clustering par embeddings sémantiques | §6.3 | Décision v1 : Topics OpenAlex uniquement |
| Génération de synthèses par IA (`crisalid-agents`) | §6.5 | Décision v1 : visualisations/tableaux uniquement |
| Intégration SoVisu+ / connecteur Keycloak | §7 | Décision v1 : application autonome |
| Réconciliation des écarts Basique/Complet | §3 | Sans objet : mode Complet non construit en v1 |
| Authentification multi-établissement | (nouveau) | Décision de cadrage MVP : single-tenant |
| Impact pondéré par citations au niveau fin des Topics OpenAlex pour les pairs (option (b) de §4.5) | §4.5 | Décision v1.1 : reporté en v2 ; le MVP couvre ce besoin au niveau des 5 grands domaines Leiden (option (c)) et au niveau volume pour les Topics fins (§4.4) |
| Comptage fractionnel (« fractional counting ») des indicateurs Leiden | §3.5 | Décision v1.2 : le MVP utilise uniquement le comptage complet (« full counting »), plus simple à expliquer ; le fractionnel — pourtant privilégié par CWTS par défaut pour ses indicateurs d'impact — est reporté en v2 |

Cette liste doit être tenue à jour : toute demande d'ajout de fonctionnalité en cours de dev qui touche l'une de ces lignes doit être traitée comme un changement de périmètre, pas comme un détail d'implémentation.

### 0.3 Choix techniques structurants (tranchés)

1. **Déploiement single-tenant** : une instance déployée = un établissement. Pas de gestion de comptes multi-établissements, pas d'authentification utilisateur pour le MVP (l'accès à l'instance elle-même peut être protégé au niveau infra — reverse proxy avec auth basique — mais ce n'est pas une fonctionnalité applicative). Le modèle de partage « accès à ses propres données + données publiques des autres » décidé dans le plan est de fait satisfait : l'instance ne connaît que les données de son propre établissement (privées, jamais exposées) et les données publiques Leiden Ranking Open Edition des autres (déjà publiques par nature).
2. **Stack alignée sur l'écosystème CRISalid** : backend **Python 3.11+ / FastAPI**, base de données **PostgreSQL**, frontend **Next.js / TypeScript**. Choix qui facilite une éventuelle intégration future (connecteur Keycloak, réutilisation de composants SoVisu+).
3. **Groupes de pairs prédéfinis** : calculés automatiquement, sans curation manuelle, selon deux logiques combinables :
   - **Géographique** : autres établissements du même pays (voire région si le découpage est disponible) dans l'univers Leiden Ranking Open Edition.
   - **Tranche de taille** : autres établissements dont le volume de publications (`works_count`) place l'établissement dans le même quantile (ex. déciles) de l'univers Leiden Ranking Open Edition.
   - Ces groupes sont complétés par des **groupes personnalisés** que l'utilisateur construit lui-même en sélectionnant des établissements dans l'univers Leiden.
4. **Calcul des indicateurs d'impact scientifique** : les indicateurs *normalisés par champ* (comparables entre disciplines/tailles) sont **repris tels quels du Leiden Ranking Open Edition** (rafraîchis une fois par an). Les indicateurs *bruts* (non normalisés) sont **recalculés depuis OpenAlex** et rafraîchis chaque nuit. Le MVP ne réplique pas la méthodologie de normalisation par champ de CWTS.
   > **Précision v1.1** : le Leiden Ranking Open Edition normalise en interne sur environ 4 500 « micro-fields », mais ne **publie/expose** ses indicateurs qu'au niveau établissement entier et, pour la lecture par discipline, sur seulement **5 grands domaines** (Biomedical and health sciences, Life and earth sciences, Mathematics and computer science, Physical sciences and engineering, Social sciences and humanities). Cette granularité est nettement plus grossière que la hiérarchie Topics d'OpenAlex (domaine → champ → sous-champ → topic). Leiden reste donc la source à utiliser pour l'impact scientifique **au niveau établissement** (et, en complément, au niveau des 5 grands domaines si besoin), mais **ne peut pas** servir de référence pour une comparaison peer-relative au niveau fin des Topics OpenAlex — cf. §4.4 et §4.5 pour la manière dont cette limite est traitée.

---

## 1. Architecture générale

```
┌──────────────────────────┐        ┌──────────────────────────────┐
│  Frontend (Next.js/TS)    │◄──────►│  Backend API (FastAPI)         │
│  - Dashboard               │  REST  │  - Endpoints indicateurs        │
│  - Pondération / vues      │        │  - Endpoints groupes de pairs   │
│  - Groupes de pairs         │        │  - Endpoints config instance    │
└──────────────────────────┘        └───────────────┬────────────────┘
                                                       │
                                     ┌─────────────────▼─────────────────┐
                                     │        PostgreSQL                  │
                                     │  works, topics, leiden_snapshot,   │
                                     │  peer_groups, weight_profiles,     │
                                     │  benchmark_views, sync_log         │
                                     └─────────────────▲─────────────────┘
                                                       │
                                     ┌─────────────────┴─────────────────┐
                                     │   Jobs planifiés (APScheduler)      │
                                     │  - sync_openalex_nightly (quotidien)│
                                     │  - sync_leiden_annual (annuel/manuel)│
                                     └───────────┬─────────────┬──────────┘
                                                 │             │
                                    ┌─────────────▼──┐   ┌──────▼───────────┐
                                    │  OpenAlex API   │   │ Leiden Open Edition│
                                    │ (works, institu- │   │ (export XLSX       │
                                    │  tions, topics)  │   │  Zenodo)           │
                                    └──────────────────┘   └────────────────────┘
```

**[Défaut — modifiable]** API REST (pas GraphQL) côté backend, pour rester simple malgré l'usage de GraphQL ailleurs dans l'écosystème CRISalid (`crisalid-ikg`) : le MVP n'a pas de graphe complexe à interroger, une API REST classique suffit et sera plus rapide à développer et à tester.

**[Défaut — modifiable]** Déploiement MVP via Docker Compose (backend, frontend, Postgres, éventuellement Adminer pour le debug). Un passage à des manifests Kubernetes alignés sur `crisalid-deployment` peut intervenir dans une phase ultérieure si l'outil doit être opéré en production mutualisée.

**[Défaut — modifiable]** Scheduler des jobs nocturnes : APScheduler intégré au process backend (pas de dépendance à un broker externe type Celery/RabbitMQ, qui serait sur-dimensionné pour un unique job quotidien et un job annuel).

---

## 2. Configuration de l'instance

Au premier lancement, un assistant de configuration (`/setup`) doit permettre de renseigner :

- L'**ID OpenAlex de l'institution** (format `https://openalex.org/I...` ou juste l'ID court) — avec validation en direct (appel à `GET /institutions/{id}` d'OpenAlex, affichage du nom retourné pour confirmation).
- L'**identifiant ROR** correspondant (généralement récupérable directement depuis l'objet Institution OpenAlex — champ `ror`).
- *(ajout v1.3)* **Confirmation du périmètre institutionnel (lineage)** : à partir du champ `lineage` de l'objet Institution renvoyé par OpenAlex (liste construite depuis les relations ROR Parent/Child, incluant l'institution elle-même et ses structures « enfants » — cf. §4.1), l'assistant affiche la **liste des établissements qui seront inclus dans le périmètre de l'établissement configuré** (ex. écoles/composantes rattachées pour une université fédérale) et invite l'utilisateur à la valider. Cette étape sert de garde-fou étant donné que les données ROR pour le système français sont, de l'aveu d'OpenAlex lui-même, encore incomplètes sur certains établissements (cf. §4.1) — un enfant manquant ou une inclusion erronée doit pouvoir être repéré avant la première synchronisation.
- Une **clé API OpenAlex** — **champ obligatoire, bloquant la fin de l'assistant de configuration**. Depuis début 2026, OpenAlex requiert une clé API pour la quasi-totalité des appels en usage réel (au-delà de quelques appels de démonstration) et applique une tarification à l'usage au-delà d'un crédit gratuit quotidien. La clé s'obtient gratuitement en quelques secondes via un compte sur openalex.org (page des paramètres du compte) et se transmet en paramètre d'URL (`api_key=...`) sur chaque appel. **Tâche d'implémentation à prévoir** : revérifier au moment du développement le format exact d'authentification (paramètre `api_key` vs header), les seuils de crédit gratuit et la tarification au-delà, ces éléments ayant été introduits récemment et étant susceptibles d'évoluer.
- Un **email de contact** technique, conservé en complément de la clé API et utilisé dans le paramètre `mailto` des appels à l'API OpenAlex (identification supplémentaire recommandée par OpenAlex, désormais secondaire par rapport à la clé mais toujours utile).
- Le **nom d'affichage** de l'établissement pour l'interface (pré-rempli depuis OpenAlex, éditable).

Ces informations sont stockées dans une table de configuration à ligne unique (`instance_config`), lue au démarrage des jobs et de l'API. La clé API doit être stockée de façon sécurisée (a minima non affichée en clair après saisie côté UI, idéalement chiffrée au repos ou déportée dans un secret manager si l'environnement de déploiement en propose un).

Tant que la configuration n'est pas complète, l'application redirige toutes les routes vers `/setup`.

---

## 3. Modèle de données (PostgreSQL)

### 3.1 `instance_config`
| Colonne | Type | Notes |
|---|---|---|
| `id` | int, PK, toujours 1 | ligne unique |
| `openalex_institution_id` | text | ex. `I4210140050` |
| `ror_id` | text | |
| `institution_name` | text | |
| `openalex_lineage_ids` | jsonb | *(ajout v1.3)* copie du champ `lineage` de l'objet Institution OpenAlex (liste d'IDs OpenAlex, self-inclusive) au moment de la configuration ; rafraîchi à chaque `sync_openalex_nightly` (cf. §4.1 point 4) pour suivre d'éventuelles évolutions ROR |
| `openalex_api_key` | text | **obligatoire** ; à stocker de façon sécurisée (cf. §2) |
| `contact_email` | text | utilisé pour `mailto` OpenAlex, en complément de la clé |
| `country_code` | text | dénormalisé depuis OpenAlex, sert au groupe géographique |
| `configured_at` | timestamptz | |

### 3.2 `works`
Publications de l'établissement configuré (mode Basique = tout ce qu'OpenAlex attribue à `openalex_institution_id` **et à ses structures enfants** via le filtre `institutions.lineage`, cf. §4.1 — révisé v1.3, auparavant limité au filtre strict `institutions.id`).

| Colonne | Type | Notes |
|---|---|---|
| `id` | text, PK | ID OpenAlex du work |
| `title` | text | |
| `publication_year` | int | |
| `type` | text | article, book-chapter, etc. |
| `cited_by_count` | int | |
| `is_oa` | boolean | depuis `open_access.is_oa` |
| `oa_status` | text | gold/green/hybrid/bronze/closed |
| `is_international_collab` | boolean | calculé : au moins une affiliation hors du pays de l'établissement |
| `is_core_publication` | boolean | *(ajout v1.2)* calculé à l'ingestion — approxime la notion de « core publication » de Leiden (cf. §4.1, §5.1) |
| `primary_topic_id` | text, FK → `topics.id` | topic principal (`primary_topic`) |
| `raw_json` | jsonb | réponse OpenAlex brute, pour ré-exploitation future sans re-fetch |
| `last_synced_at` | timestamptz | |

### 3.3 `work_topics`
Table d'association pour les topics secondaires d'un work (OpenAlex renvoie une liste de topics scorés, pas seulement le `primary_topic`).

| Colonne | Type | Notes |
|---|---|---|
| `work_id` | text, FK → `works.id` | |
| `topic_id` | text, FK → `topics.id` | |
| `score` | float | score de pertinence renvoyé par OpenAlex |

### 3.4 `topics`
Référentiel de la taxonomie Topics d'OpenAlex (synchronisé une fois, rafraîchi occasionnellement — la taxonomie change peu).

| Colonne | Type | Notes |
|---|---|---|
| `id` | text, PK | ex. `T10175` |
| `display_name` | text | |
| `subfield_id` / `subfield_name` | text | |
| `field_id` / `field_name` | text | |
| `domain_id` / `domain_name` | text | niveau le plus agrégé de la hiérarchie |

### 3.5 `leiden_snapshot` *(schéma révisé v1.4 d'après le fichier réel)*

Import annuel du Leiden Ranking Open Edition. **Révision v1.4** : le fichier réel (`colonnes_leiden_open_2025.xlsx`, vérifié par Henri) est au format **XLSX** (pas CSV) et structuré en **format long/tidy** : une ligne par combinaison (établissement, `Field`, `Period`, `Core_pubs_only`, `Frac_counting`), et non une ligne par établissement avec des colonnes séparées par méthode. `Core_pubs_only` (0/1) et `Frac_counting` (0/1) sont donc des **dimensions du fichier source**, pas des colonnes à choisir a posteriori comme supposé en v1.2/v1.3. Selon ces deux indicatrices, différentes colonnes de métriques sont renseignées ou laissées vides — cf. table de correspondance ci-dessous.

**Décision d'import v1.4, étendue v1.7** : pour rester aligné sur les décisions déjà prises (comptage complet uniquement, §0.3 point 4/§3.5 v1.2), **les lignes `Frac_counting = 0` sont importées, pour les deux valeurs de `Core_pubs_only` (0 et 1)**, dans les colonnes typées de `leiden_snapshot` pour le MVP — extension v1.7 par rapport à la décision initiale v1.4, qui ne chargeait que `Core_pubs_only = 1`. **Raison de l'extension** : les indicateurs normalisés par percentile utilisés par défaut pour l'axe impact scientifique (`PP_top_*`, `MNCS`) ne sont renseignés que sur les lignes `Core_pubs_only=1` ; sans les lignes `Core_pubs_only=0`, le toggle « toutes les publications » de `/impact-scientifique` (§7) n'avait aucun indicateur Leiden valide à afficher, faute d'importer la famille d'indicateurs alternative (`PP_*_cits`) qui n'existe, elle, que sur les lignes `Core_pubs_only=0` (cf. §5.1). `leiden_snapshot` compte donc désormais, pour un établissement/`field`/période donné, **deux lignes** (une par valeur de `Core_pubs_only`) plutôt qu'une seule. **Contrainte d'unicité recommandée, révisée v1.7** : (`ror_id`, `field`, `period`, `core_pubs_only`, `snapshot_year`) plutôt que (`ror_id`, `field`, `period`, `snapshot_year`) comme implicite jusqu'ici. La combinaison `Frac_counting = 1` reste hors périmètre v1 (comptage fractionnel, décision v1.2 inchangée) — elle pourra être importée en v2 sans changement de schéma si le comptage fractionnel devient utile **[Défaut — modifiable]**.

**Décision d'import v1.5 — filtre sur `Period`** : un seul fichier téléchargé contient **15 fenêtres glissantes historiques** par établissement/champ (confirmé sur l'extrait réel, de `2006–2009` à `2020–2023`). Pour rester au plus simple, le MVP n'importe que la **période la plus récente** (la dernière valeur de `Period` présente dans le fichier, déterminée par tri plutôt que codée en dur puisque la fenêtre la plus récente évolue à chaque édition) — les 14 autres périodes ne sont ni chargées en colonnes typées ni conservées en `raw_row` pour le MVP **[Défaut — modifiable : les périodes historiques sont déjà présentes « gratuitement » dans le fichier source si un suivi temporel devient utile en v2 — l'implémentation peut choisir de toutes les importer dès maintenant sans surcoût API, au prix d'un volume de lignes ~15× plus élevé, cf. note de volumétrie ci-dessous]**. Cette décision réduit aussi mécaniquement le volume à ingérer (cf. note de volumétrie ci-dessous).

> ⚠️ **Note de volumétrie (v1.5, révisée v1.7)** : le fichier complet (tous établissements, tous champs, toutes périodes, les 4 combinaisons `Core_pubs_only`/`Frac_counting`) peut représenter, en ordre de grandeur, plusieurs centaines de milliers à plus d'un million de lignes (~2 800 établissements du classement × jusqu'à 6 valeurs de `Field` × 15 périodes × 4 combinaisons). Le filtre `Frac_counting=0` (décision v1.2) élimine la moitié des lignes ; le filtre « dernière période uniquement » (v1.5, ci-dessus) élimine encore un facteur ~15. **Révision v1.7** : à la différence de la v1.4-v1.6, les **deux valeurs** de `Core_pubs_only` sont désormais conservées (cf. décision d'import étendue ci-dessus) plutôt qu'un filtre supplémentaire `Core_pubs_only=1` — le volume réellement importé, de l'ordre de quelques dizaines de milliers de lignes en v1.4-v1.6, **double approximativement** avec cette extension (probablement de l'ordre de 50 000 à 100 000 lignes selon l'édition), restant néanmoins largement gérable. **Tâche d'implémentation à prévoir** : un classeur XLSX de cette taille peut peser plusieurs centaines de Mo et ne doit pas être chargé intégralement en mémoire — utiliser le mode `read_only` d'`openpyxl` (lecture en flux, ligne par ligne) plutôt qu'un chargement complet via `pandas.read_excel`, ou filtrer en streaming avant matérialisation en DataFrame.

| Colonne | Type | Notes |
|---|---|---|
| `id` | serial, PK | |
| `ror_id` | text | source : `ROR_ID`. **Confirmé v1.5** : stocké **sans préfixe** (ex. `0549hdw45`, pas `https://ror.org/0549hdw45`). **Tâche d'implémentation ferme** : normaliser (retirer le préfixe `https://ror.org/`) côté application partout où l'on compare à un ROR issu d'OpenAlex (champ `ror` de l'objet Institution, qui renvoie l'URI complète) — sous peine de jointures silencieusement vides. |
| `university_name` | text | source : `University` |
| `country_code` | text | source : `Country`, **transformé à l'import**. **Confirmé v1.5** : `Country` est un **nom de pays en clair** (ex. « Pakistan »), pas un code ISO — l'hypothèse « à vérifier » de la v1.4 est donc confirmée dans le sens le plus contraignant. `instance_config.country_code` et l'objet Institution OpenAlex utilisés pour le groupe de pairs géographique (§4.3) sont en code ISO 2 lettres : une **table de correspondance nom de pays → ISO 3166-1 alpha-2** est requise à l'import (ex. bibliothèque `pycountry` côté Python, avec table de correction manuelle pour les libellés ambigus — « Russia » vs « Russian Federation », noms d'usage vs noms officiels, territoires, etc.) — cf. tâche d'implémentation en §4.2. |
| `snapshot_year` | int | année du fichier importé (ex. 2025), pas une colonne du fichier source — renseignée par le job d'import |
| `period` | text | source : `Period`. **Confirmé v1.5** : fenêtres glissantes de 4 ans avec tiret cadratin Unicode (ex. `2020–2023`, caractère `–` U+2013, pas un simple tiret `-`) — attention à l'encodage lors du parsing/des comparaisons de chaînes. **15 périodes coexistent dans un seul fichier téléchargé** (de `2006–2009` à `2020–2023` dans l'extrait reçu) : cf. décision d'import ci-dessous. |
| `field` | text | source : `Field`. **Résolu v1.6** sur un second extrait couvrant tous les domaines d'un même établissement : exactement **6 valeurs possibles**, confirmées telles quelles — `All sciences` (repère établissement entier, existe nativement, pas besoin de recalcul par agrégation), `Biomedical and health sciences`, `Life and earth sciences`, `Mathematics and computer science`, `Physical sciences and engineering`, `Social sciences and humanities`. `field='All sciences'` est donc la valeur à utiliser partout où cette spec référençait jusqu'ici `field='all'` (§4.3, §5.1). |
| `core_pubs_only` | boolean | source : `Core_pubs_only`. **Révisé v1.7** : les deux valeurs (`true`/`false`) sont désormais importées (cf. décision d'import étendue ci-dessus, auparavant toujours `true` en v1.4-v1.6) — cette colonne fait partie de la clé de recherche d'une ligne `leiden_snapshot` (avec `ror_id`/`field`/`period`), au même titre que `frac_counting`. Le code applicatif doit systématiquement filtrer explicitement sur `core_pubs_only` selon le contexte (indicateur core par défaut vs toggle « toutes les publications », cf. §5.1) plutôt que de supposer une seule ligne par (établissement, `field`, période). |
| `frac_counting` | boolean | source : `Frac_counting`. Toujours `false` pour les lignes importées en v1, même logique que ci-dessus pour le comptage fractionnel. *(Remplace la colonne `counting_method` prévue en v1.2, désormais alignée sur les vrais noms/valeurs de colonnes du fichier source.)* |
| `p` | **numeric** *(type conservé, cf. explication ci-dessous)* | source : `P` — nombre de publications (jamais vide). Utilisé comme mesure de taille pour les groupes de pairs par tranche de taille (§4.3, auparavant `p_count`). **Résolu v1.6, ce n'est pas une erreur** : sur `field='All sciences'`, `P` est bien un **entier exact** (ex. `1887`, confirmé sur le second extrait) — Henri a raison, il n'y a pas d'artefact au niveau établissement. La non-intégralité observée en v1.5 (ex. `391.166667`) n'apparaît que sur les lignes **par domaine** (`field≠'All sciences'`), et s'explique entièrement : un travail interdisciplinaire relevant de plusieurs des 5 grands domaines y est compté **fractionnellement dans chacun** — la somme des `P` des 5 domaines reproduit exactement le `P` entier de la ligne `All sciences` (vérifié sur l'extrait : 391,17 + 239,17 + 361,83 + 835,67 + 59,17 = 1887,0). Cette fraction-par-domaine est **indépendante de `Frac_counting`** (qui ne concerne que le partage entre établissements co-auteurs, cf. §0.3 point 4/§3.5) : les deux mécanismes de fractionnement coexistent sans lien entre eux. **Conséquence pour l'implémentation** : `p` doit rester typé `numeric` (pas `int`) pour couvrir les lignes par domaine, mais la ligne `field='All sciences'` utilisée pour les groupes de pairs (§4.3) et l'axe impact scientifique établissement entier (§5.1) sera systématiquement un entier — l'UI peut afficher les valeurs par domaine arrondies avec une info-bulle expliquant le fractionnement interdisciplinaire plutôt que de s'en inquiéter. |
| `tcs` | float | source : `TCS` — citations totales non normalisées (vide seulement si `P=0`) |
| `mcs` / `mcs_lb` / `mcs_ub` | float | source : `MCS`/`MCS_lb`/`MCS_ub` — citations moyennes par publication, non normalisées, avec intervalle de confiance (vide seulement si `P=0`) |
| `mncs` / `mncs_lb` / `mncs_ub` | float | source : `MNCS`/`MNCS_lb`/`MNCS_ub` — citations moyennes **normalisées par champ** (1.0 = moyenne mondiale du champ), l'indicateur d'impact normalisé le plus direct de Leiden ; disponible uniquement sur les lignes `Core_pubs_only=1`. **Confirmé v1.5** sur l'extrait réel (ex. `MNCS=1.084` pour la ligne testée). **Révisé v1.7** : depuis l'import des lignes `Core_pubs_only=0` (cf. décision étendue ci-dessus), cette colonne n'est **plus systématiquement renseignée** — elle reste `NULL` sur les lignes `core_pubs_only=false` (la normalisation par champ nécessite la classification en revues « core », indisponible pour le corpus complet). Seule `mcs` (non normalisée, ci-dessus) reste disponible sur les deux valeurs de `core_pubs_only`, comme équivalent brut. |
| `pp_top_1` / `_lb` / `_ub` | float | source : `PP_top_1`/`PP_top_1_lb`/`PP_top_1_ub` — % de publications dans le top 1% le plus cité (normalisé par champ), avec intervalle de confiance. **Révisé v1.7** : comme `mncs`, disponible uniquement sur les lignes `core_pubs_only=true` (`NULL` sur `core_pubs_only=false`). |
| `pp_top_5` / `_lb` / `_ub` | float | source : `PP_top_5`/`PP_top_5_lb`/`PP_top_5_ub`. Même condition de disponibilité que `pp_top_1` ci-dessus (`NULL` sur `core_pubs_only=false`, révisé v1.7). |
| `pp_top_10` / `_lb` / `_ub` | float | source : `PP_top_10`/`PP_top_10_lb`/`PP_top_10_ub` — **remplace `pp_top10`** utilisé dans les versions précédentes de cette spec ; c'est l'indicateur central de l'axe impact scientifique en position « publications core » (§5.1). **Confirmé v1.5** : stocké en **proportion 0–1** (ex. `0.1094` = 10,94%), pas en pourcentage 0–100 — à multiplier par 100 uniquement à l'affichage, jamais en base. Vaut la même règle pour l'ensemble des colonnes `PP_*` de ce tableau. **Révisé v1.7** : `NULL` sur les lignes `core_pubs_only=false` — cf. `pp_10_cits` ci-dessous, indicateur **non équivalent** utilisé en remplacement quand le toggle est sur « toutes les publications » (§5.1, §7). |
| `pp_top_50` / `_lb` / `_ub` | float | source : `PP_top_50`/`PP_top_50_lb`/`PP_top_50_ub`. Même condition de disponibilité que `pp_top_1`/`pp_top_10` ci-dessus (révisé v1.7). |
| `pp_10_cits` / `_lb` / `_ub` | float | *(ajout v1.7)* source : `PP_10_cits`/`PP_10_cits_lb`/`PP_10_cits_ub` — % de publications ayant reçu **au moins 10 citations** (seuil absolu, **non normalisé par champ**, à la différence de `pp_top_*`). Disponible uniquement sur les lignes `core_pubs_only=false` (`NULL` sur `core_pubs_only=true` — exactement l'inverse de `pp_top_*`/`mncs`). Proportion 0–1, même règle d'affichage que les autres `PP_*`. C'est cette colonne qui **remplace `pp_top_10`** comme indicateur vedette de l'axe impact scientifique quand le toggle est sur « toutes les publications » (§5.1) — cf. avertissement de non-équivalence en §5.1. |
| `pp_20_cits` / `_lb` / `_ub` | float | *(ajout v1.7)* source : `PP_20_cits`/`PP_20_cits_lb`/`PP_20_cits_ub` — % de publications ayant reçu au moins 20 citations. Même condition de disponibilité que `pp_10_cits`. |
| `pp_50_cits` / `_lb` / `_ub` | float | *(ajout v1.7)* source : `PP_50_cits`/`PP_50_cits_lb`/`PP_50_cits_ub` — % de publications ayant reçu au moins 50 citations. Même condition de disponibilité que `pp_10_cits`. |
| `pp_100_cits` / `_lb` / `_ub` | float | *(ajout v1.7)* source : `PP_100_cits`/`PP_100_cits_lb`/`PP_100_cits_ub` — % de publications ayant reçu au moins 100 citations. Même condition de disponibilité que `pp_10_cits`. |
| `pp_int_collab` / `_lb` / `_ub` | float | source : `PP_int_collab`/`PP_int_collab_lb`/`PP_int_collab_ub` — % de publications en collaboration internationale (vide si `Frac_counting=1`, donc systématiquement présent dans les lignes importées, quelle que soit la valeur de `core_pubs_only`) |
| `pp_oa` / `_lb` / `_ub` | float | source : `PP_OA`/`PP_OA_lb`/`PP_OA_ub` — % de publications en accès ouvert (même condition que ci-dessus) |
| `raw_row` | jsonb | ligne source complète (toutes les ~88 colonnes du fichier, y compris celles non promues en colonnes typées ci-dessus : `P_10_cits`/`P_20_cits`/`P_50_cits`/`P_100_cits` (effectifs bruts correspondant à `PP_*_cits`, non promus — **révisé v1.7** : seules les proportions `PP_*_cits` sont désormais promues en colonnes typées, cf. ci-dessus, symétriquement à `P_top_*` qui reste lui aussi en `raw_row` en regard de `PP_top_*`), `P_industry_collab`/`PP_industry_collab`, `P_short_dist_collab`, `P_long_dist_collab`, le détail par sous-type d'accès ouvert `*_gold_OA`/`*_hybrid_OA`/`*_bronze_OA`/`*_green_OA`, `P_top_1`/`P_top_5`/`P_top_10`/`P_top_50` en effectifs bruts, etc.) — permet de promouvoir ces indicateurs en colonnes typées en v2 sans ré-import. **Piste à noter pour Henri (v1.5, non actée)** : `P_industry_collab`/`PP_industry_collab` (collaboration avec l'industrie) est un candidat naturel de proxy pour l'axe « impact économique », actuellement hors périmètre v1 faute de source (§0.2) — disponible sans coût d'ingestion supplémentaire puisqu'il est déjà dans le fichier Leiden importé, à réévaluer si cet axe est un jour remis à l'ordre du jour. |

> ⚠️ **Comptage complet vs fractionnel (rappel v1.2, précisé v1.4)** : confirmé par le fichier réel — `Frac_counting` est bien une dimension à part entière du dataset (une ligne par établissement/champ/période existe pour `Frac_counting=0` **et** pour `Frac_counting=1`), pas une paire de colonnes séparées comme anticipé initialement. La décision v1.2 (comptage complet uniquement) se traduit donc simplement par un filtre `WHERE Frac_counting = 0` à l'import, cf. décision d'import ci-dessus.
>
> ⚠️ **Format du fichier (v1.4)** : le fichier récupéré depuis Zenodo est un **classeur XLSX** (confirmé par Henri), pas un CSV comme anticipé en v1.0-v1.3 — l'import doit utiliser un lecteur Excel (ex. `openpyxl`/`pandas.read_excel` côté Python) plutôt qu'un parseur CSV. L'option BigQuery mentionnée dans les versions précédentes de cette spec reste une alternative possible mais n'est plus la voie par défaut documentée ici, faute de confirmation.
>
> ✅ **Points confirmés v1.5 sur extrait réel** (`leiden_open_2025_sample.xlsx`) : format XLSX en lignes « longues » avec `Core_pubs_only`/`Frac_counting`/`Field`/`Period` comme dimensions de ligne (structure anticipée en v1.4 validée telle quelle) ; `Country` en nom de pays en clair ; `ROR_ID` sans préfixe URI ; `Period` en fenêtres glissantes de 4 ans (15 par établissement/champ) ; proportions `PP_*` en échelle 0–1.
>
> ✅ **Points résolus v1.6 sur second extrait** (`leiden_open_2025_full_sample.xlsx`, même établissement sur les 6 valeurs de `Field`) : la valeur « établissement entier » de `Field` est `All sciences`, confirmée présente nativement (pas de recalcul par agrégation nécessaire) ; la non-intégralité de `P` observée en v1.5 est expliquée et non problématique — fractionnement interdisciplinaire entre les 5 domaines, absent au niveau `All sciences` où `P` est entier. **Plus aucun point n'est en suspens sur le schéma `leiden_snapshot`** (cf. §10, mis à jour).
>
> ✅ **Confirmé v1.7** : l'hypothèse d'Henri sur le désalignement des familles d'indicateurs `pp_top_*` (core-only) / `pp_*_cits` (non-core-only) avec le toggle `/impact-scientifique` est vérifiée sur `leiden_open_2025_sample.xlsx` — `PP_top_1/5/10/50` et `MNCS` ne sont renseignés que sur les lignes `Core_pubs_only=1` ; `PP_10/20/50/100_cits` ne le sont que sur les lignes `Core_pubs_only=0`. Correction intégrée au schéma et à l'axe impact scientifique (§3.5, §5.1, §7).

### 3.11 `peer_topic_counts` *(ajout v1.1)*
Distribution des publications par **Topic OpenAlex** (comptages uniquement, pas de citations) pour chaque établissement d'un groupe de pairs actif — alimente une comparaison peer-relative de la spécificité disciplinaire à une granularité bien plus fine que les 5 domaines Leiden. Cf. §4.4 pour le mécanisme d'ingestion et §5.2 pour l'usage.

| Colonne | Type | Notes |
|---|---|---|
| `id` | serial, PK | |
| `openalex_institution_id` | text | établissement pair concerné |
| `ror_id` | text | pour rapprochement avec `leiden_snapshot` / `peer_group_members` |
| `topic_id` | text, FK → `topics.id` | |
| `works_count` | int | nombre de publications de cet établissement dans ce topic, sur la fenêtre retenue **[Défaut — modifiable : fenêtre glissante à définir, ex. 5 dernières années, pour cohérence avec les fenêtres Leiden]** |
| `fetched_at` | timestamptz | pilote le rafraîchissement (cache, cf. §4.4) |

Contrainte d'unicité recommandée : (`openalex_institution_id`, `topic_id`).

### 3.12 `institution_id_map` *(ajout v1.3)*
Cache de résolution ROR → ID OpenAlex pour les établissements pairs (cf. §4.4).

| Colonne | Type | Notes |
|---|---|---|
| `ror_id` | text, PK | |
| `openalex_institution_id` | text | |
| `resolved_at` | timestamptz | |

### 3.6 `peer_groups`
| Colonne | Type | Notes |
|---|---|---|
| `id` | serial, PK | |
| `name` | text | |
| `type` | text | `geographic` \| `size_bracket` \| `custom` |
| `generated_at` | timestamptz | null pour les groupes personnalisés |
| `params` | jsonb | ex. `{"country_code": "FR"}` ou `{"decile": 7}` |

### 3.7 `peer_group_members`
| Colonne | Type | Notes |
|---|---|---|
| `peer_group_id` | int, FK | |
| `ror_id` | text | référence vers une ligne de `leiden_snapshot` (univers Leiden) |

### 3.8 `weight_profiles`
Pondération à deux niveaux : critère → sous-indicateurs.

| Colonne | Type | Notes |
|---|---|---|
| `id` | serial, PK | |
| `name` | text | |
| `axis_weights` | jsonb | ex. `{"impact_scientifique": 0.6, "specificite_disciplinaire": 0.4}` (somme = 1) |
| `sub_indicator_weights` | jsonb | ex. `{"impact_scientifique": {"impact_normalise_leiden": 0.5, "citations_brutes": 0.2, "oa_pct": 0.15, "collab_intl_pct": 0.15}, "specificite_disciplinaire": {"herfindahl": 0.7, "nb_topics_signature": 0.3}}` (somme = 1 à l'intérieur de chaque axe) — *(clé `impact_normalise_leiden` révisée v1.7, auparavant `pp_top_10`, cf. note ci-dessous)* |
| `created_at` | timestamptz | |

> **Précision v1.7** : la clé `impact_normalise_leiden` est un identifiant **abstrait** de sous-indicateur, pas un nom de colonne littéral — le backend résout, au moment du calcul (§5.3), la colonne `leiden_snapshot` réellement utilisée (`pp_top_10` ou `pp_10_cits`) selon l'état du toggle core/non-core actif au moment de la consultation (§5.1, §7). Ce choix évite de dupliquer les poids saisis par l'utilisateur pour chaque état du toggle, au prix d'un mapping explicite à documenter dans le code (ex. `LEIDEN_HEADLINE_COLUMN = {"core": "pp_top_10", "all": "pp_10_cits"}`), et rappelle que ces deux colonnes ne sont pas des indicateurs équivalents (cf. §5.1).

### 3.9 `benchmark_views`
Une « vue » sauvegardée = combinaison d'un profil de pondération et d'un groupe de pairs.

| Colonne | Type | Notes |
|---|---|---|
| `id` | serial, PK | |
| `name` | text | |
| `weight_profile_id` | int, FK | |
| `peer_group_id` | int, FK | |
| `created_at` | timestamptz | |

### 3.10 `sync_log`
| Colonne | Type | Notes |
|---|---|---|
| `id` | serial, PK | |
| `job_name` | text | `openalex_nightly` \| `leiden_annual` |
| `started_at` / `finished_at` | timestamptz | |
| `status` | text | `success` \| `failed` \| `running` |
| `records_processed` | int | |
| `error_message` | text | nullable |

---

## 4. Ingestion des données

### 4.1 Job `sync_openalex_nightly` (quotidien)

1. Créer une entrée `sync_log` (`status=running`).
2. Appeler l'API OpenAlex `GET /works?filter=institutions.lineage:{openalex_institution_id}&per-page=200&cursor=*` *(filtre `institutions.lineage` retenu depuis v1.3, à la place de `institutions.id` — cf. note ci-dessous)* en pagination par curseur jusqu'à épuisement, avec les paramètres `api_key={openalex_api_key}` (obligatoire, cf. §2) et `mailto={contact_email}` (en complément).
3. Pour chaque work : upsert dans `works` (calcul de `is_international_collab` à partir des `authorships[].institutions[].country_code` comparés au `country_code` de l'instance), upsert des lignes `work_topics` depuis le champ `topics` du work, upsert du `primary_topic_id` depuis `primary_topic`.
3bis. *(ajout v1.2)* Calcul de `is_core_publication` : OpenAlex expose un champ **`is_core`** directement sur l'objet **Source** (`GET /sources/{id}`, ou déjà inclus dans `primary_location.source.is_core` au sein de la réponse `works` — à confirmer au moment du développement pour éviter un appel séparé par source), indiquant l'appartenance à la liste CWTS Core (~36 000 sources). `is_core_publication` est dérivé comme : `primary_location.source.is_core = true` **ET** `type` ∈ {`article`, `review`, `book-chapter`} **ET** `language = 'en'` **ET** `is_retracted = false`. **Limite à documenter** : il s'agit d'une **approximation pragmatique** de la définition officielle « core publications » de Leiden (qui exclut en outre explicitement les actes de conférence et applique des critères additionnels sur la revue elle-même) — pas une reproduction garantie à l'identique des chiffres publiés par CWTS. Une parité stricte nécessiterait d'importer le jeu de données externe de classification travaux-par-travaux publié par CWTS/OpenAlex (fichier `work.tsv`, ~3 Go, champ `is_core_work`), volontairement écarté du MVP pour rester léger — option à réévaluer en v2 si l'écart avec les chiffres officiels de Leiden s'avère significatif en pratique.
4. Synchroniser également l'objet `GET /institutions/{openalex_institution_id}` pour rafraîchir les compteurs agrégés utilisés en page d'accueil (`works_count`, `cited_by_count`, `summary_stats.h_index`, `summary_stats.i10_index`) **et le champ `lineage`** (persisté dans `instance_config.openalex_lineage_ids`, cf. §3.1) — un changement de composition (ajout/retrait d'une structure enfant côté ROR) doit être détectable d'une nuit à l'autre, même s'il n'entraîne pas d'action automatique en v1 au-delà d'une trace dans les logs **[Défaut — modifiable : une alerte utilisateur en cas de changement de lineage pourrait être ajoutée ultérieurement]**.

> ⚠️ **Note v1.3 — écart méthodologique résiduel avec Leiden** : `institutions.lineage` reflète strictement les relations ROR **Parent/Child**. Le Leiden Ranking Open Edition, lui, ne s'appuie pas sur une hiérarchie ROR automatique : il retient les composantes et installations de recherche conjointes (« joint research facilities ») mais **exclut explicitement** les « organisations associées » (relation ROR plus lâche), et applique au cas par cas des choix reflétant « la manière dont ces institutions sont perçues localement » (ex. certains systèmes universitaires fédéraux sont scindés en établissements distincts plutôt qu'agrégés). Le périmètre `institutions.lineage` utilisé ici pour l'ingestion OpenAlex de l'établissement configuré est donc la meilleure approximation disponible **sans curation manuelle**, mais peut différer du périmètre exact retenu par la ligne Leiden correspondante — un écart à documenter dans l'UI (ex. courte mention méthodologique sur `/impact-scientifique`) plutôt qu'à masquer. OpenAlex indique par ailleurs que les enregistrements ROR pour le système de recherche français ne sont, à ce jour, pas encore complètement développés pour l'ensemble des établissements — un facteur d'imprécision supplémentaire, en cours d'amélioration via la collaboration ROR/ABES/MESR, à garder en tête notamment pour les universités fusionnées.
5. Marquer `sync_log.status=success` avec le nombre de works traités, ou `failed` avec le message d'erreur (garder les données déjà en base intactes en cas d'échec partiel — ne pas vider la table avant d'avoir confirmé le succès du fetch, upsert incrémental).

**Gestion des limites d'API** : respecter le rate-limit OpenAlex associé à la clé configurée (documentation faisant état, selon les sources consultées, d'un ordre de grandeur de 10 req/s et d'un volume gratuit quotidien, au-delà duquel une tarification à l'usage s'applique — **chiffres précis à revérifier dans la documentation officielle au moment du développement**, ce mécanisme ayant été introduit récemment et étant encore amené à évoluer), avec retry/backoff exponentiel sur erreurs 429/5xx et suivi de la consommation de crédits si la tarification à l'usage est active.

**[Défaut — modifiable]** Le job tourne sur l'établissement configuré uniquement (single-tenant). Il ne synchronise pas les *works* détaillés des établissements pairs — seuls leurs agrégats (via `leiden_snapshot` et, si besoin ponctuel, l'objet Institution OpenAlex) sont utilisés, ce qui évite une ingestion massive et coûteuse pour des milliers d'établissements.

### 4.2 Job `sync_leiden_annual` (annuel, déclenchable manuellement)

1. Télécharger le dernier export du Leiden Ranking Open Edition depuis Zenodo — **fichier XLSX** (confirmé v1.4, cf. §3.5), à parser avec un lecteur Excel en mode flux (`openpyxl` en `read_only=True`, cf. note de volumétrie §3.5) plutôt qu'un chargement complet en DataFrame.
2. Filtrer les lignes du fichier sur `Frac_counting = 0` (cf. décision d'import §3.5, étendue v1.7) ; conserver les **deux valeurs** de `Core_pubs_only` (`0` et `1`) — *(révisé v1.7 ; la v1.4-v1.6 ne conservait que `Core_pubs_only=1`)*. Les lignes `Frac_counting = 1` restent ignorées pour le MVP (non chargées, ni en colonnes typées ni en `raw_row` — à revoir en v2 si besoin).
3. *(ajout v1.5)* Déterminer la **période la plus récente** présente dans le fichier (tri des valeurs distinctes de `Period`, pas une valeur codée en dur) et ne conserver que les lignes correspondant à cette période (cf. décision d'import §3.5).
4. *(ajout v1.5)* Normaliser `ROR_ID` (retirer un éventuel préfixe `https://ror.org/` s'il est présent, l'ajouter en interne si absent — à fixer une convention unique et s'y tenir dans tout le schéma) et résoudre `Country` (nom en clair) vers un `country_code` ISO alpha-2 via une table de correspondance (ex. bibliothèque `pycountry` + table de correction manuelle pour les cas ambigus, cf. §3.5) — **journaliser tout pays non résolu** plutôt que d'échouer silencieusement (un établissement avec `country_code` NULL serait invisible du groupe de pairs géographique sans avertissement).
5. Recharger intégralement la table `leiden_snapshot` pour le nouveau `snapshot_year` (conserver les snapshots précédents pour permettre une lecture d'évolution historique dans une phase ultérieure — ne pas écraser les années passées).
6. Marquer le job dans `sync_log`.

Ce job n'a pas besoin d'automatisation cron stricte pour le MVP (le Leiden Ranking n'est pas republié souvent) : un déclenchement manuel via un endpoint d'administration (`POST /admin/sync/leiden`) suffit, complété si souhaité par une vérification mensuelle automatique de la disponibilité d'une nouvelle édition.

### 4.3 Calcul des groupes de pairs prédéfinis

Recalculé après chaque `sync_leiden_annual` (les groupes prédéfinis dépendent de l'univers Leiden) :

- **Groupe géographique** : tous les établissements de `leiden_snapshot` (dernier `snapshot_year`, `field='All sciences'`, cf. §3.5) partageant le `country_code` de l'instance, calculé à l'import via la table de correspondance nom→ISO (§3.5, §4.2 point 4).
- **Groupes par tranche de taille** : répartir l'ensemble des établissements de `leiden_snapshot` (`field='All sciences'`) en déciles sur `p` *(renommé depuis `p_count`, cf. §3.5 v1.4 — type `numeric` ; toujours entier sur `field='All sciences'`, cf. §3.5)*, l'instance étant positionnée dans l'un de ces déciles ; le peer group proposé par défaut est le décile de l'établissement configuré **[Défaut — modifiable : nombre de déciles à ajuster, ex. quintiles si le nombre de pairs dans un décile est jugé trop faible pour être pertinent]**.

### 4.4 Distribution par Topic OpenAlex pour les groupes de pairs — comptages *(ajout v1.1)*

Comme précisé en §0.3 point 4 et §3.5, le Leiden Ranking Open Edition ne descend qu'à 5 grands domaines : insuffisant pour comparer la spécificité disciplinaire de l'établissement à ses pairs au niveau fin des Topics OpenAlex (`topics_signature`, §5.2). OpenAlex permet cependant d'obtenir, **à faible coût**, le nombre de publications par Topic pour un établissement donné, sans avoir à récupérer chaque publication individuellement :

`GET /works?filter=institutions.lineage:{id},primary_topic.id:*&group_by=primary_topic.id&api_key=...`

*(filtre `institutions.lineage` retenu depuis v1.3, par cohérence avec le périmètre de l'établissement configuré — cf. §4.1 — plutôt que `institutions.id`, pour que les établissements pairs ayant eux aussi une structure fédérale/composée ne soient pas artificiellement sous-comptés dans la comparaison)*

Cet appel (paginé sur les groupes retournés, pas sur les publications) renvoie directement un comptage de publications par topic pour l'établissement filtré — un coût de quelques appels par établissement, sans rapport avec une ingestion complète des publications.

**Résolution ROR → ID OpenAlex des pairs** *(précision v1.3)* : `peer_group_members`/`leiden_snapshot` n'identifient les pairs que par leur `ror_id` (fourni par le dataset Leiden). L'appel ci-dessus nécessite l'ID OpenAlex de l'institution : prévoir une résolution `GET /institutions/ror:{ror_id}` (ou `filter=ror:{ror_id}`), mise en cache dans une petite table de correspondance `institution_id_map` (`ror_id` PK, `openalex_institution_id`, `resolved_at`) pour éviter de refaire cet appel à chaque consultation d'un groupe de pairs.

**Mécanisme retenu** :
1. Ce comptage est déclenché **à la demande**, lors de la première consultation d'un groupe de pairs donné (prédéfini ou personnalisé), pour chaque établissement membre n'ayant pas encore d'entrée récente dans `peer_topic_counts`.
2. Les résultats sont mis en cache dans `peer_topic_counts`, avec une politique de rafraîchissement plus lâche que les données de l'établissement configuré **[Défaut — modifiable : TTL proposé de l'ordre de la fenêtre entre deux imports Leiden, ex. rafraîchi lors de chaque `sync_leiden_annual` plutôt que nocturnement, le profil thématique d'un établissement évoluant lentement]**.
3. Pour un groupe de pairs de grande taille (ex. un décile de taille pouvant compter plusieurs centaines d'établissements dans l'univers Leiden), le premier chargement peut prendre plusieurs minutes : prévoir un indicateur de progression / état de cache dans l'UI (« calcul de la comparaison en cours pour N établissements ») plutôt qu'un calcul bloquant synchrone.

Ce mécanisme permet de recalculer `indice_herfindahl` et `topics_signature` (§5.2) en comparaison réellement peer-relative, à la granularité des Topics OpenAlex, sans ingérer les publications complètes des établissements pairs.

### 4.5 Impact pondéré par citations au niveau Topic pour les pairs *(ajout v1.1 — tranché)*

Le mécanisme ci-dessus (§4.4) résout la comparaison **par volume** (nombre de publications par topic). Il ne résout pas un besoin plus exigeant, identifié par Henri : un indicateur d'impact scientifique **pondéré par les citations, au niveau fin des Topics, pour les pairs** (ex. « citations moyennes par publication dans le Topic X, comparées au groupe de pairs sélectionné »). OpenAlex ne propose pas d'agrégation serveur de ce type (`group_by` ne renvoie que des comptages, jamais de somme/moyenne d'un autre champ comme `cited_by_count`) : obtenir cette information exigerait de récupérer, pour chaque établissement pair, l'ensemble de ses publications avec au minimum leurs champs `id`, `cited_by_count` et `primary_topic.id` (via `select=` pour limiter la charge utile) — un ordre de grandeur de coût comparable à l'ingestion complète actuellement réservée à l'établissement configuré (§4.1), multiplié par la taille du groupe de pairs.

Trois options, avec un arbitrage à trancher :

- **(a) Hors périmètre v1** : le MVP livré n'inclut pas d'impact pondéré par citations au niveau Topic pour les pairs. L'impact scientifique reste comparé au niveau établissement (Leiden + OpenAlex brut, §5.1) et, en complément, au niveau des 5 grands domaines Leiden si utile. La spécificité disciplinaire (§5.2) reste basée sur le volume (comptages, §4.4), sans pondération par citations. *Recommandé pour un MVP au sens strict — reporté en v2, cohérent avec la logique de simplicité déjà retenue pour les autres points de décision.*
- **(b) Inclus au MVP, à coût maîtrisé** : ingestion à la demande et mise en cache (mêmes principes qu'en §4.4) des publications des établissements pairs **du groupe actuellement sélectionné uniquement** (pas de pré-calcul pour tous les groupes possibles), avec champs minimaux (`select=id,cited_by_count,primary_topic`). Fonctionnellement plus riche, mais alourdit sensiblement le développement du MVP et la consommation de crédits API (facturation à l'usage désormais en vigueur chez OpenAlex, cf. §2) pour des groupes de pairs de grande taille.
- **(c) Version intermédiaire** : se limiter à un impact pondéré par citations au niveau des **5 grands domaines Leiden** (déjà disponible sans coût additionnel via la colonne `field` de §3.5), et garder le niveau Topic fin uniquement en comptage (§4.4). Moins précis que (b), mais gratuit et déjà couvert par les évolutions de cette révision.

**décision v1.1 — impact pondéré par citations au niveau Topic pour les pairs**
Option retenue : **(c) version intermédiaire**. Le MVP inclut donc un impact pondéré par citations comparé aux pairs au niveau des **5 grands domaines Leiden** (`leiden_snapshot.field`, §3.5 — sans coût d'ingestion supplémentaire), tandis que la comparaison au niveau fin des Topics OpenAlex (`peer_topic_counts`, §4.4) reste **basée sur le volume uniquement**, sans pondération par citations. L'option (b) (ingestion complète des publications des pairs pour un impact pondéré par citations au niveau Topic fin) est explicitement reportée à une v2 — cf. §0.2.

---

## 5. Calcul des indicateurs

### 5.1 Axe « Impact scientifique »

**Portée des publications (v1.2, colonnes précisées v1.4)** : `pp_top_10`/`pp_top_1`/`mncs` proviennent de Leiden et sont donc, par construction, déjà calculés sur les **publications « core »** au sens de Leiden (`Core_pubs_only=1`, cf. §3.5) et en **comptage complet** (`Frac_counting=0`, cf. §3.5). Pour une cohérence méthodologique avec ces indicateurs de référence, les sous-indicateurs recalculés depuis OpenAlex ci-dessous sont, **par défaut**, également filtrés sur `is_core_publication = true` (§3.2, §4.1) **[Défaut — modifiable : un bandeau ou toggle « toutes publications / publications core » peut être ajouté sur `/impact-scientifique`, cf. §7, pour permettre de voir aussi le corpus complet]**.

> ⚠️ **Non-équivalence `pp_top_10` / `pp_10_cits` (ajout v1.7)** : le toggle core/non-core existe depuis v1.2 côté indicateurs OpenAlex recalculés (`is_core_publication`), mais jusqu'en v1.6 aucun indicateur Leiden valide n'existait côté « toutes les publications » — `pp_top_10`/`mncs` sont vides sur les lignes `Core_pubs_only=0` (cf. §3.5). **Depuis v1.7**, `leiden_snapshot` importe aussi ces lignes, qui exposent une famille d'indicateurs différente (`pp_10_cits`/`pp_20_cits`/`pp_50_cits`/`pp_100_cits`, cf. §3.5) : un **seuil de citations absolu** (ex. « au moins 10 citations »), et non un **percentile normalisé par champ** comme `pp_top_10`. Ce ne sont donc **pas des indicateurs équivalents** : un établissement peut avoir un `pp_top_10` élevé (fort par rapport à son champ disciplinaire) et un `pp_10_cits` plus modeste, ou l'inverse — notamment selon le profil disciplinaire de l'établissement, les champs à fort volume de citations (ex. sciences biomédicales) atteignant plus facilement un seuil absolu que les champs à faible volume (ex. SHS). Le sous-indicateur vedette de l'axe impact scientifique (tableau ci-dessous) est donc **toggle-dépendant** : `pp_top_10` en position « publications core » (comportement inchangé depuis v1.2), `pp_10_cits` en position « toutes les publications » (nouveau en v1.7). Cette bascule doit être rendue visible à l'utilisateur (libellé de la carte, info-bulle, §7) plutôt que présentée comme une continuité transparente du même chiffre.

| Sous-indicateur | Source | Calcul |
|---|---|---|
| `pp_top_10` *(toggle = « publications core », défaut)* | Leiden (annuel) | Repris tel quel de `leiden_snapshot` (`field='All sciences'`, `core_pubs_only=true`, cf. §3.5) pour l'établissement — *(renommé depuis `pp_top10` dans les versions précédentes de cette spec, pour coller au nom réel de la colonne source, cf. §3.5 v1.4)*. Les bornes `pp_top_10_lb`/`pp_top_10_ub` (intervalle de confiance fourni par Leiden) peuvent être affichées en complément (ex. « entre X% et Y% ») **[Défaut — modifiable]**. Proportion 0–1 à l'affichage ×100 (confirmé v1.5, cf. §3.5). |
| `pp_10_cits` *(toggle = « toutes les publications », ajout v1.7)* | Leiden (annuel) | Repris de `leiden_snapshot` (`field='All sciences'`, `core_pubs_only=false`, cf. §3.5) — **remplace `pp_top_10`** quand le toggle est désactivé, seul indicateur Leiden normalisé disponible sur le corpus complet (cf. §3.5 et avertissement de non-équivalence ci-dessus). Proportion 0–1 à l'affichage ×100. Les deux variantes (`pp_top_10`/`pp_10_cits`) alimentent le même emplacement pondérable abstrait `impact_normalise_leiden` (§3.8). |
| `mncs` | Leiden (annuel) | *(ajout v1.4, bonus)* Repris de `leiden_snapshot.mncs` — citations moyennes normalisées par champ (1.0 = moyenne mondiale). Complète `pp_top_10` par une lecture continue plutôt que par seuil ; à inclure ou non dans les sous-indicateurs pondérables **[Défaut — modifiable]**. **Révisé v1.7** : `NULL` en position « toutes les publications » (`core_pubs_only=false`, cf. §3.5) — pas d'équivalent continu normalisé par champ disponible dans ce mode ; `mcs` (non normalisée) reste affichable comme repère brut si besoin. |
| `citations_brutes_moyennes` | OpenAlex (nocturne) | `SUM(cited_by_count) / COUNT(*)` sur `works WHERE is_core_publication = true`, filtrable par fenêtre d'années. `leiden_snapshot.mcs` (annuel, non normalisé) peut servir de valeur de référence/cross-check sans remplacer ce calcul nocturne. |
| `h_index_core` | OpenAlex (nocturne, calculé en base) | *(ajout v1.2)* Calculé côté application (pas depuis `summary_stats`, qui porte sur tout le corpus, cf. note ci-dessous) à partir des `cited_by_count` des `works WHERE is_core_publication = true` de l'établissement, par l'algorithme standard du h-index |
| `oa_pct` | OpenAlex (nocturne) | `COUNT(is_oa=true) / COUNT(*)` sur `works WHERE is_core_publication = true`. `leiden_snapshot.pp_oa` (annuel) sert de référence/cross-check. |
| `collab_intl_pct` | OpenAlex (nocturne) | `COUNT(is_international_collab=true) / COUNT(*)` sur `works WHERE is_core_publication = true`. `leiden_snapshot.pp_int_collab` (annuel) sert de référence/cross-check. |

> **Note v1.2** : le `summary_stats.h_index` renvoyé par l'objet Institution OpenAlex (mentionné en §4.1 point 4) porte sur l'ensemble du corpus, pas seulement les publications core — il reste utile en page d'accueil comme compteur général de l'établissement (§4.1), mais `h_index_core` ci-dessus, recalculé en base sur le sous-ensemble core, est la version à utiliser pour la comparaison peer-relative de l'axe impact scientifique, par cohérence avec `pp_top_10`.

Pour la comparaison à un groupe de pairs, chaque sous-indicateur est converti en **percentile au sein du groupe de pairs sélectionné** avant pondération (cf. §5.3) — `pp_top_10` étant déjà lui-même un pourcentage normalisé par Leiden, il peut aussi être affiché brut en plus de son percentile intra-groupe. *(ajout v1.7)* Ce même raisonnement s'applique à `pp_10_cits` quand le toggle est sur « toutes les publications » — avec la réserve que, n'étant pas normalisé par champ contrairement à `pp_top_10`, sa conversion en percentile intra-groupe reste sensible à la composition disciplinaire du groupe de pairs sélectionné (cf. avertissement ci-dessus).

**Drill-down par grand domaine (v1.1, décision §4.5, colonne précisée v1.4)** : en complément de la vue établissement entier ci-dessus, l'écran `/impact-scientifique` propose un sélecteur des **5 grands domaines Leiden** (`leiden_snapshot.field`) permettant de rejouer les mêmes sous-indicateurs `pp_top_10`/`mncs`/`pp_int_collab`/`pp_oa` filtrés sur un domaine, comparés au même groupe de pairs (chaque pair disposant potentiellement de ses propres lignes par `field` dans `leiden_snapshot`). Les indicateurs bruts OpenAlex (`citations_brutes_moyennes`, `oa_pct`, `collab_intl_pct`) peuvent être filtrés de façon équivalente sur `works` via une jointure `work_topics → topics.domain_name`, à condition de faire correspondre les noms de domaines OpenAlex aux 5 domaines Leiden **[Tâche d'implémentation à prévoir : la correspondance entre les 4 domaines OpenAlex et les 5 domaines Leiden n'est pas triviale (nomenclatures différentes), et les valeurs exactes de la colonne `field` restent à confirmer sur un extrait réel du fichier (§3.5) — à établir manuellement lors du développement, table de correspondance à documenter dans le code]**.

### 5.2 Axe « Spécificité disciplinaire »

**Portée des publications (v1.2)** : à la différence de l'axe impact scientifique (§5.1), cet axe utilise par défaut le **corpus complet** (`works`, sans filtre `is_core_publication`), et non le seul sous-ensemble core. Justification : la définition « core » de Leiden exclut structurellement une partie des types de publication (actes de conférence notamment) et favorise les revues internationales anglophones — un filtrage core-only risquerait de sous-représenter artificiellement le profil disciplinaire d'un établissement fort en SHS ou en recherche appliquée, à l'opposé de l'objectif de cet axe (rendre compte fidèlement du profil réel de l'établissement) **[Défaut — modifiable]**.

| Sous-indicateur | Calcul |
|---|---|
| `profil_thematique` | Distribution des `works` de l'établissement sur la hiérarchie Topics (ex. répartition par `domain_name`, puis drill-down par `field_name`) — sert de support de visualisation (treemap ou barres empilées), pas un score en soi |
| `indice_herfindahl` | $H = \sum_i s_i^2$ où $s_i$ est la part des publications de l'établissement dans le topic $i$ (au niveau `field` **[Défaut — modifiable : niveau de granularité de la taxonomie à utiliser, field vs subfield vs topic]**), calculée à partir de `works`/`work_topics` pour l'établissement configuré. Un $H$ élevé indique une spécialisation forte, un $H$ faible une production diffuse sur de nombreux champs. **Limite documentée (v1.1)** : cet indice reste basé sur le volume de publications, pas sur leur impact — cf. §4.5 pour l'option de pondération par citations, actuellement hors périmètre par défaut. |
| `topics_signature` | Liste des topics où la part de l'établissement (depuis `works`/`work_topics`) est significativement supérieure à la part moyenne du groupe de pairs sélectionné (depuis `peer_topic_counts`, §4.4 — comparaison désormais réellement peer-relative au niveau fin des Topics OpenAlex, et non plus seulement au niveau établissement), ex. ratio part\_établissement / part\_moyenne\_groupe > seuil **[Défaut — modifiable : seuil à calibrer, ex. ×1.5]**, triés par écart décroissant. Basé sur le volume, pas sur l'impact (même limite que ci-dessus). |

### 5.3 Score composite pondéré

1. Pour chaque sous-indicateur et pour l'établissement + chaque membre du groupe de pairs sélectionné, calculer un **percentile intra-groupe** (0 à 100).
   **[Défaut — modifiable]** Choix du percentile plutôt que du z-score : plus intuitif pour un public de gouvernance non bibliométricien (« vous êtes au 80e percentile » se lit plus facilement qu'un score centré-réduit), et robuste aux valeurs extrêmes.
2. Agréger les percentiles des sous-indicateurs d'un axe selon `sub_indicator_weights` → score d'axe (0-100).
3. Agréger les scores d'axes selon `axis_weights` → score composite final (0-100).
4. Ce calcul est **entièrement déclenché à la demande** (pas de job planifié) : à chaque changement de profil de pondération ou de groupe de pairs dans l'UI, l'API recalcule à partir des données déjà en base (`works`, `leiden_snapshot`), sans re-fetch externe. C'est ce qui permet, comme décidé, de tester plusieurs pondérations sur des données stables entre deux synchronisations nocturnes.
5. Cas particulier : un groupe de pairs personnalisé fraîchement créé n'a pas besoin d'attendre le lendemain pour ses scores composites (ceux-ci ne dépendent que de `leiden_snapshot`, déjà en base) — la contrainte « attendre le lendemain » du plan v0.2 concerne uniquement le cas où l'établissement configuré lui-même vient d'être ajouté/modifié et nécessite un premier `sync_openalex_nightly` complet.

---

## 6. API backend (contrats d'endpoints)

**[Défaut — modifiable]** Toutes les routes sous préfixe `/api/v1`.

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/config` | Renvoie la configuration de l'instance (ou 404 si non configurée) |
| `POST` | `/config` | Enregistre la configuration initiale (ID OpenAlex, ROR, email, nom) |
| `GET` | `/institution/summary` | Compteurs agrégés (works_count, citations, h-index, dernière sync) |
| `GET` | `/indicators/impact-scientifique?peer_group_id=&weight_profile_id=` | Sous-indicateurs bruts + percentiles + score d'axe |
| `GET` | `/indicators/specificite-disciplinaire?peer_group_id=&weight_profile_id=` | Profil thématique, indice de Herfindahl, topics signature |
| `GET` | `/indicators/composite?benchmark_view_id=` | Score composite final + détail par axe |
| `GET` | `/peer-groups` | Liste des groupes (prédéfinis + personnalisés) |
| `POST` | `/peer-groups` | Création d'un groupe personnalisé (liste de `ror_id`) |
| `GET` | `/peer-groups/{id}/members` | Détail des membres d'un groupe |
| `GET` | `/peer-groups/{id}/topic-distribution` *(v1.1)* | Distribution par Topic OpenAlex du groupe (déclenche le remplissage du cache `peer_topic_counts` si absent/expiré, cf. §4.4) |
| `GET` | `/weight-profiles` / `POST /weight-profiles` | CRUD des profils de pondération |
| `GET` | `/benchmark-views` / `POST /benchmark-views` | CRUD des vues sauvegardées |
| `GET` | `/sync/status` | Dernier statut des jobs (`sync_log`) |
| `POST` | `/admin/sync/leiden` | Déclenchement manuel du job annuel Leiden |
| `POST` | `/admin/sync/openalex` | Déclenchement manuel hors planification (utile en debug/démo) |

---

## 7. Frontend — écrans

1. **`/setup`** — assistant de configuration initiale (cf. §2).
2. **`/` (tableau de bord)** — vue de synthèse : nom de l'établissement, compteurs clés, fraîcheur des données (horodatage dernière sync OpenAlex, année du snapshot Leiden en cours), accès rapide aux deux axes et aux vues sauvegardées.
3. **`/impact-scientifique`** — sous-indicateurs sous forme de cartes/graphiques, sélecteur de groupe de pairs, positionnement en percentile visualisé (ex. jauge ou distribution avec marqueur), sélecteur de grand domaine Leiden (§5.1). *(v1.2, comportement Leiden précisé v1.7)* Bandeau/toggle « publications core (recommandé, comparable à Leiden) / toutes les publications », core sélectionné par défaut, avec une info-bulle expliquant simplement la différence pour un public non bibliométricien. **Précision v1.7** : en plus de refiltrer les indicateurs OpenAlex recalculés (`is_core_publication`), ce toggle change désormais aussi la **source Leiden** de l'indicateur normalisé vedette — `pp_top_10` en position core, `pp_10_cits` en position « toutes les publications » (§5.1) — deux indicateurs conceptuellement différents (percentile normalisé par champ vs seuil de citations absolu). L'info-bulle doit le mentionner explicitement (ex. « en mode "toutes les publications", cet indicateur change de nature : il mesure la part de publications ayant reçu au moins 10 citations, sans normalisation par discipline ») plutôt que de laisser croire à une continuité du même chiffre.
4. **`/specificite-disciplinaire`** — carte thématique (treemap sur la hiérarchie Topics), indice de Herfindahl affiché avec une échelle de lecture (peu/moyennement/très spécialisé), liste des topics signature.
5. **`/pondération`** (benchmark builder) — interface à deux niveaux : curseurs par axe, puis curseurs par sous-indicateur à l'intérieur de chaque axe (somme contrainte à 100% par niveau), aperçu en direct du score composite, bouton de sauvegarde en tant que profil nommé.
6. **`/groupes-de-pairs`** — liste des groupes prédéfinis (géographique, tranches de taille) avec leur composition, interface de création d'un groupe personnalisé (recherche/sélection d'établissements dans l'univers Leiden par nom/pays).
7. **`/vues`** — liste des vues sauvegardées (profil de pondération + groupe de pairs), pour rappel rapide d'une configuration déjà utilisée.

**[Défaut — modifiable]** Pas d'export CSV/PDF dans le MVP initial (non demandé explicitement dans les décisions v1, et l'axe « génération de synthèse » a été explicitement exclu) — à ajouter en incrément rapide si le besoin se confirme à l'usage, la donnée étant déjà structurée pour un export trivial.

**[Défaut — modifiable]** Librairie de graphiques : au choix de l'équipe de dev (ex. Recharts/Observable Plot pour Next.js) ; aucune contrainte imposée par ce document.

---

## 8. Découpage en tickets de développement (ordre suggéré)

1. **Socle** : projet FastAPI + PostgreSQL + Docker Compose ; projet Next.js ; migrations (Alembic) pour le schéma §3.
2. **Configuration d'instance** : endpoints `/config`, page `/setup`, validation contre l'API OpenAlex, affichage et confirmation du périmètre `lineage` résolu (cf. §2).
3. **Ingestion OpenAlex** : job `sync_openalex_nightly` (filtre `institutions.lineage`, cf. §4.1), table `works`/`work_topics`/`topics` (dont calcul de `is_core_publication`, cf. §4.1 point 3bis), endpoint `/institution/summary`, page tableau de bord minimal (compteurs + fraîcheur).
4. **Ingestion Leiden** : job `sync_leiden_annual` (à partir d'un export Zenodo téléchargé manuellement dans un premier temps si l'automatisation du téléchargement pose des difficultés), table `leiden_snapshot`, parsing XLSX en flux, filtres `Frac_counting=0`/dernière `Period`/`Field='All sciences'` pour les besoins établissement entier (§3.5, §4.2) — les **deux valeurs** de `Core_pubs_only` sont conservées depuis v1.7 (auparavant `Core_pubs_only=1` uniquement) —, normalisation `ROR_ID` et résolution `country_code` (§4.2 point 4). *(Schéma entièrement confirmé depuis v1.6, étendu v1.7 pour les métriques `pp_*_cits` — plus aucun blocage.)*
5. **Groupes de pairs prédéfinis** : calcul géographique + tranche de taille, endpoints `/peer-groups`, page `/groupes-de-pairs` (lecture seule d'abord).
6. **Distribution par Topic pour les pairs (comptages)** *(v1.1, filtre lineage v1.3)* : mécanisme à la demande + cache décrit en §4.4, table `peer_topic_counts`, résolution ROR→OpenAlex via `institution_id_map`.
7. **Indicateurs impact scientifique** : endpoint + page, avec percentile intra-groupe. *(précisé v1.7)* le backend doit résoudre l'indicateur Leiden vedette (`pp_top_10` vs `pp_10_cits`) selon l'état du toggle core/non-core (§5.1, §7, §3.8).
8. **Indicateurs spécificité disciplinaire** : indice de Herfindahl et topics signature réellement peer-relatifs (appuyés sur le ticket 6), endpoint + page (treemap).
9. **Groupes de pairs personnalisés** : création côté UI + API.
10. **Pondération à deux niveaux et score composite** : `weight_profiles`, `benchmark_views`, endpoint `/indicators/composite`, page `/pondération`.
11. **Durcissement** : gestion des erreurs/retries et suivi de consommation OpenAlex (clé API, crédits), page `/vues`, `sync/status` visible dans l'UI (bandeau de fraîcheur des données sur toutes les pages).
12. **Drill-down impact scientifique par grand domaine Leiden** *(décision §4.5 = option (c))* : exploitation de `leiden_snapshot.field`, table de correspondance domaines OpenAlex ↔ 5 domaines Leiden, sélecteur de domaine sur `/impact-scientifique`.
13. *(ajout v1.4, précisé v1.5, filtre étendu v1.7)* **Ingestion Leiden XLSX en format long** : parsing en flux du classeur Excel réel, filtres `Frac_counting=0`/dernière `Period` (les **deux valeurs** de `Core_pubs_only` sont conservées depuis v1.7, cf. §3.5), normalisation `ROR_ID` et résolution `country_code` (table nom→ISO). *(Format et structure confirmés sur extrait réel depuis v1.6 — plus aucun blocage technique.)*

---

## 9. Critères d'acceptation du MVP

- Un établissement quelconque (pas seulement un établissement pilote) peut être configuré via `/setup` en saisissant son ID OpenAlex.
- Pour un établissement disposant de structures enfants au sens ROR (ex. université fédérale/fusionnée), l'assistant de configuration affiche la liste des établissements inclus dans le périmètre avant validation, et les publications ingérées couvrent bien l'établissement configuré et ses enfants (`institutions.lineage`), pas uniquement l'établissement au sens strict.
- Après une synchronisation nocturne réussie, le tableau de bord affiche des compteurs cohérents avec l'objet Institution OpenAlex de l'établissement (élargi au périmètre lineage).
- Les deux groupes de pairs prédéfinis (géographique, tranche de taille) sont calculés automatiquement sans intervention manuelle, à partir du dernier import Leiden.
- La liste des topics signature et l'indice de Herfindahl sont comparés à une distribution par Topic réellement calculée pour le groupe de pairs sélectionné (via `peer_topic_counts`, §4.4), et non plus uniquement à l'établissement seul.
- Un utilisateur peut créer un groupe de pairs personnalisé et obtenir un score composite sur ce groupe sans attendre de synchronisation nocturne (la comparaison par Topic peut nécessiter un temps de calcul initial le temps du premier remplissage du cache, cf. §4.4).
- Un utilisateur peut créer un profil de pondération à deux niveaux, l'appliquer à un groupe de pairs, et voir le score composite se recalculer en direct.
- Un utilisateur peut filtrer l'axe impact scientifique sur l'un des 5 grands domaines Leiden et obtenir des sous-indicateurs et un positionnement peer-relatif cohérents avec ce filtre.
- Les sous-indicateurs d'impact scientifique recalculés depuis OpenAlex (citations moyennes, h-index, %OA, %collaboration internationale) sont, par défaut, cohérents avec la base « publications core » utilisée par Leiden pour `pp_top_10`, avec possibilité de basculer sur le corpus complet.
- *(critère ajouté v1.7)* En mode « toutes les publications » (toggle désactivé), l'indicateur normalisé vedette de l'axe impact scientifique affiche `pp_10_cits` (et non une valeur vide ou périmée), et son libellé/info-bulle indique explicitement qu'il s'agit d'un indicateur différent de `pp_top_10` (seuil de citations absolu, non normalisé par champ, cf. §5.1).
- Le fichier Leiden Ranking Open Edition est correctement importé au format XLSX réel (pas CSV), avec les lignes `Frac_counting=0`/dernière `Period` chargées dans `leiden_snapshot` pour les **deux valeurs** de `Core_pubs_only` *(étendu v1.7, auparavant `Core_pubs_only=1` uniquement)*, `ROR_ID` normalisé et `country_code` résolu depuis le nom de pays.
- Le groupe de pairs géographique renvoie effectivement des établissements du même pays que l'instance configurée (validation manuelle sur quelques pays, dont la France) — preuve que la résolution nom de pays → ISO fonctionne correctement.
- Tous les indicateurs Leiden affichés (établissement entier et par grand domaine) sont en comptage complet ; aucune version fractionnelle n'est présente dans le MVP livré.
- Aucune fonctionnalité listée en §0.2 (hors périmètre) n'est présente dans le MVP livré.
- La fraîcheur des données (horodatage dernière sync OpenAlex, année du snapshot Leiden) est visible à tout moment dans l'interface.

---

*Document construit à partir de `crisalid_benchmark_plan_v1.md` (décisions v1) et des choix techniques structurants validés le 20 août 2026 (cf. §0.3). Révisé en v1.1 à v1.6 le 20 août 2026, puis en v1.7 le 21 août 2026, suite aux relectures d'Henri et à deux extraits réels du Leiden Ranking Open Edition (cf. changelog en tête de document) — toutes les décisions et tous les points techniques identifiés sont désormais tranchés/résolus (§10).*

---

## 10. Points en suspens sur le schéma Leiden — historique de résolution

Les deux points laissés en suspens en v1.5 ont été **résolus en v1.6** à partir d'un second extrait réel (`leiden_open_2025_full_sample.xlsx`, même établissement couvrant les 6 valeurs de `Field`) :

1. ✅ **Valeur « établissement entier » de la colonne `Field` — résolu.** Confirmé : `Field` prend exactement 6 valeurs, dont `All sciences` comme repère établissement entier, présente nativement dans le fichier (pas de recalcul par agrégation des 5 domaines nécessaire). Toutes les références de cette spec sont mises à jour vers `field='All sciences'` (§3.5, §4.3, §5.1).
2. ✅ **Nature non entière de l'indicateur `P` — résolu, ce n'était pas une erreur.** Sur `field='All sciences'`, `P` est un entier exact (ex. `1887`). La non-intégralité observée en v1.5 n'apparaît que sur les lignes par domaine, et s'explique par un fractionnement des publications interdisciplinaires entre les 5 grands domaines — mécanisme indépendant de `Frac_counting`, vérifié par sommation exacte (les 5 valeurs par domaine reproduisent le total `All sciences` au centième près). Le champ reste typé `numeric` pour couvrir ce cas, mais `p` est garanti entier sur les lignes utilisées pour les groupes de pairs et l'axe impact scientifique établissement entier (§3.5).

**Aucun point technique n'est plus en suspens sur le schéma `leiden_snapshot`** à ce stade. Le reste des hypothèses de structure (format XLSX en lignes longues, dimensions `Core_pubs_only`/`Frac_counting`/`Field`/`Period`, format `Country`/`ROR_ID`, échelle des proportions) est confirmé par les deux extraits réels reçus et ne nécessite plus de vérification avant développement.

3. ✅ **Désalignement `pp_top_*` (core-only) / `pp_*_cits` (non-core-only) avec le toggle core/non-core — résolu en v1.7.** Confirmé sur `leiden_open_2025_sample.xlsx` : `PP_top_1/5/10/50` et `MNCS` ne sont renseignés que sur les lignes `Core_pubs_only=1` ; `PP_10/20/50/100_cits` ne le sont que sur les lignes `Core_pubs_only=0`. La décision d'import est étendue pour charger les deux valeurs de `Core_pubs_only` (§3.5, §4.2), les colonnes `pp_*_cits` sont ajoutées au schéma, et l'axe impact scientifique (§5.1) comme le toggle (§7) utilisent désormais `pp_10_cits` en remplacement de `pp_top_10` en position « toutes les publications » — avec un avertissement explicite sur la non-équivalence conceptuelle des deux familles d'indicateurs (§5.1).
