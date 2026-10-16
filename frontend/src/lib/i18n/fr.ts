/**
 * Single source of truth for every UI wording in the app (todo.md item 17).
 * French only for now — adding a second locale later means adding another
 * dictionary file with the same key shape and a locale switch in
 * `lib/i18n/index.ts`'s `t()`, not restructuring this file.
 *
 * Nested by feature area, mirroring the component tree. Dynamic pieces use
 * `{var}`-style placeholders resolved by `t(key, vars)`.
 */
export const fr = {
  common: {
    loading: "Chargement…",
    computing: "Calcul en cours…",
    dash: "—",
    save: "Sauvegarder",
    cancel: "Annuler",
    edit: "Modifier",
    delete: "Supprimer",
    remove: "Retirer",
    saving: "Enregistrement…",
    close: "Fermer",
  },

  nav: {
    dashboard: "Tableau de bord",
    settings: "Paramètres du benchmark",
    qualitySettings: "Paramètres d'évaluation qualitative",
    configuration: "Configuration",
    logout: "Déconnexion",
  },

  freshnessBar: {
    openalexLabel: "OpenAlex :",
    neverSynced: "Synchronisation non encore effectuée",
    syncedOnPrefix: "synchronisé le",
    staleFlag: " (> 48 h)",
    leidenLabel: "Leiden :",
    leidenImported: "importé le {date}",
    leidenPeriod: " · période {period}",
    leidenCounts: "{rows} lignes · {institutions} établissements",
    leidenNever: "aucun import",
    refreshNote: "Données actualisées nuitamment (OpenAlex) et annuellement (Leiden)",
  },

  header: {
    corePublicationsOnly: "Publications core uniquement",
    coreTooltip:
      "Les « publications core » approximent la définition Leiden : source dans la liste CWTS Core " +
      "(~36 000 revues), type article/revue/chapitre d'ouvrage, langue anglaise, non rétracté. " +
      "Activé par défaut pour rester cohérent avec les indicateurs Leiden calculés sur ce sous-ensemble. " +
      "Désactivé, l'indicateur de citation vedette change de nature : il devient le pourcentage de " +
      "publications ayant reçu au moins 10 citations (seuil absolu, non normalisé par domaine), et non " +
      "plus un simple élargissement du même chiffre.",
    domainLabel: "Grand domaine Leiden",
    domainTooltip:
      "Le Leiden Ranking publie ses indicateurs sur 5 grands domaines (+ 'Tous les domaines'), avec sa propre " +
      "classification des publications. Utilisé uniquement dans l'onglet Monde entier.",
    tab_world: "Monde entier",
    tab_groups: "Groupes de comparaison",
    openalexDomainLabel: "Domaine OpenAlex",
    openalexDomainTooltip:
      "Les 4 domaines de la taxonomie Topics d'OpenAlex (niveau le plus large), équivalent des grands domaines " +
      "Leiden dans l'onglet Groupes de comparaison, sans correspondance entre les deux classifications. Le " +
      "domaine d'une publication est celui de son topic principal (une publication = un domaine).",
    profileLabel: "Profil de comparaison",
    groupLabel: "Groupe de comparaison",
    decileTooltip: "Décile Leiden (nombre de publications) d'appartenance",
    neverSyncedTitle: "Aucune synchronisation effectuée.",
    neverSyncedBody:
      "Les données ci-dessous sont vides. Une première synchronisation démarre automatiquement " +
      "après la configuration initiale — si ce message persiste, relancez-la depuis",
    footerLeidenEdition: "Données Leiden : édition {year} · ",
    footerOpenalexSynced: "OpenAlex : {date}",
    footerOpenalexNever: "OpenAlex : jamais synchronisé",
    noGroupAvailableBefore: "Aucun groupe de comparaison disponible pour l'instant — importez les données Leiden Ranking (page",
    noGroupAvailableAfter: ") pour voir votre positionnement.",
    loadError: "Impossible de charger les données. Vérifiez que l'instance est configurée.",
  },

  filters: {
    core: "Publications core",
    allPublications: "Toutes publications",
  },

  world: {
    methodLabel: "Source :",
    method:
      "Leiden Ranking Open Edition (CWTS), indicateurs tels que publiés — calculés par CWTS à partir d'OpenAlex, " +
      "normalisés par domaine fin et par année, en comptage complet ; ils ne sont pas recalculés ici. Comme dans le " +
      "Leiden Ranking, aucun score global n'est calculé. Rangs et percentiles de votre établissement calculés parmi " +
      "les universités ayant au moins {min} publications (P) dans le domaine sélectionné (seuil réglable dans " +
      "Configuration).",
    coreNote:
      "Publications core : indicateurs normalisés par domaine (top 1 / 10 / 50 %, MNCS), disponibles uniquement " +
      "sur ce sous-ensemble dans le Leiden Ranking.",
    allPublicationsNote:
      "Toutes publications : le Leiden Ranking ne fournit alors que des indicateurs à seuil absolu (≥ 10 / ≥ 50 " +
      "citations, MCS), non normalisés par domaine.",
    edition: "Édition {year}",
    loadError: "Erreur lors du chargement des données Leiden.",
    noData: "Aucune donnée Leiden importée (page Paramètres du benchmark).",
    ownTitle: "Votre établissement dans le Leiden Ranking",
    ownNotRanked: "Votre établissement n'est pas classé par le Leiden Ranking dans ce domaine.",
    ownBelowThreshold:
      "Moins de {min} publications dans ce domaine : valeurs affichées sans rang ni percentile.",
    rank: "{rank}e sur {n}",
    tableTitle: "Classement Leiden",
    colUniversity: "Université",
    colCountry: "Pays",
    belowThreshold: "(P < seuil)",
    countryFilter: "Pays",
    allCountries: "Tous les pays",
    myCountry: "Mon pays ({country})",
  },

  worldIndicator: {
    p: "P",
    pp_top_1: "PP(top 1 %)",
    pp_top_10: "PP(top 10 %)",
    pp_top_50: "PP(top 50 %)",
    mncs: "MNCS",
    mcs: "MCS",
    pp_10_cits: "PP(≥ 10 cit.)",
    pp_50_cits: "PP(≥ 50 cit.)",
    pp_oa: "PP(accès ouvert)",
    pp_int_collab: "PP(collab. intl.)",
  },

  worldIndicatorDescription: {
    p: "Nombre de publications (comptage complet).",
    pp_top_1: "Part des publications parmi les 1 % les plus citées de leur domaine et de leur année.",
    pp_top_10: "Part des publications parmi les 10 % les plus citées de leur domaine et de leur année.",
    pp_top_50: "Part des publications parmi les 50 % les plus citées de leur domaine et de leur année.",
    mncs: "Nombre moyen de citations normalisé par domaine et année (1 = moyenne mondiale).",
    mcs: "Nombre moyen de citations par publication, non normalisé.",
    pp_10_cits: "Part des publications citées au moins 10 fois (seuil absolu, non normalisé).",
    pp_50_cits: "Part des publications citées au moins 50 fois (seuil absolu, non normalisé).",
    pp_oa: "Part des publications en accès ouvert.",
    pp_int_collab: "Part des publications co-signées avec au moins un autre pays.",
  },

  groupTab: {
    methodLabel: "Source :",
    method:
      "OpenAlex uniquement, sans dépendance au Leiden Ranking : pour chaque établissement du groupe (le vôtre " +
      "inclus), nombre de publications de la période Leiden courante vérifiant chaque critère, compté par OpenAlex " +
      "(une requête groupée par domaine OpenAlex et par critère). Tous les indicateurs sont des parts de " +
      "publications, les seuls indicateurs Leiden reproductibles à partir de comptages (pas de MNCS ni de " +
      "moyenne de citations). Les établissements sous le seuil de publications sont affichés sans percentile, " +
      "rang ni score.",
    threshold: "Seuil : {min} publications",
    loadError: "Erreur lors du calcul du benchmark du groupe.",
    cacheMissingBefore:
      "Comptages OpenAlex disponibles pour {n} établissement(s) sur {total}. Lancez « Calculer les topics et la " +
      "qualité des pairs » depuis la page",
    cacheMissingAfter: " pour compléter la comparaison.",
  },

  groupOverview: {
    title: "Votre établissement dans le groupe",
    belowThreshold:
      "Moins de {min} publications sur ce périmètre : valeurs affichées sans percentile, rang ni score global.",
    period: "Publications {start}–{end} (OpenAlex)",
    score: "Score global",
    rank: "{rank}e sur {n} établissements comparés",
  },

  openalexDomain: {
    all: "Tous les domaines",
    "1": "Sciences de la vie",
    "2": "Sciences sociales",
    "3": "Sciences physiques",
    "4": "Sciences de la santé",
  },

  specialization: {
    title: "Taux de spécialisation",
    subtitle: "Part des publications de l'établissement dans le domaine OpenAlex sélectionné dans l'en-tête.",
    methodLabel: "Mode de calcul :",
    method:
      "taux de spécialisation = publications du domaine ÷ publications classées dans l'un des 4 domaines OpenAlex " +
      "(domaine du topic principal ; les publications sans topic sont exclues du dénominateur), sur la période " +
      "Leiden courante. Les taux d'un établissement sur les 4 domaines totalisent 100 %. Percentile parmi les " +
      "établissements du groupe au-dessus du seuil de publications. C'est l'unique indicateur de l'axe " +
      "Spécialisation du score global ; il n'est pas calculé en mode « Tous les domaines ».",
    cardTitle: "Taux de spécialisation — {domain}",
    notApplicable:
      "Le taux de spécialisation se calcule par rapport à un domaine : choisissez un domaine OpenAlex dans " +
      "l'en-tête. En mode « Tous les domaines », l'axe Spécialisation est exclu du score global et les autres axes " +
      "sont renormalisés.",
    noData: "Comptages OpenAlex non disponibles pour votre établissement.",
    counts: "{field} publications dans ce domaine (P).",
    groupStats: "Groupe ({n} établissements comparés) : médiane {median} %, maximum {max} %.",
  },

  signature: {
    title: "Topics signature",
    subtitle:
      "Topics OpenAlex dans lesquels votre établissement est premier du groupe de comparaison en score global.",
    methodLabel: "Mode de calcul :",
    method:
      "pour chaque topic OpenAlex (niveau le plus fin, ~4 500 topics) où votre établissement compte au moins {min} " +
      "publications sur {start}–{end}, un score global par topic est calculé pour chaque établissement du groupe " +
      "ayant lui aussi au moins {min} publications dans ce topic, avec les poids du profil de comparaison : axe " +
      "Impact (percentiles de la part des publications dans le top 10 % des plus citées — normalisée par domaine et " +
      "année par OpenAlex —, de la part en accès ouvert et de la part en collaboration internationale) et axe " +
      "Spécialisation (percentile de la part du topic dans la production de l'établissement). L'axe Qualité n'est " +
      "pas disponible à l'échelle des topics : son poids est redistribué sur les deux autres (seuil de publications " +
      "réglable dans Configuration). Un topic est signature " +
      "si votre établissement y obtient le meilleur score (ex æquo inclus). Les topics signature ne sont pas " +
      "utilisés dans le calcul du score global.",
    computeError: "Erreur lors du calcul des topics signature.",
    cacheMissingBefore:
      "Les statistiques par topic ne sont pas encore calculées pour votre établissement et les membres du groupe. " +
      "Lancez « Calculer les " +
      "topics et la qualité des pairs » depuis la page",
    cacheMissingAfter: ".",
    coverage: "{n} établissement(s) sur {total} avec statistiques par topic.",
    none: "Votre établissement n'est premier du groupe dans aucun topic (seuil : {min} publications par topic).",
    alone: "seul du groupe",
    colTopic: "Topic",
    colPublications: "Publications",
    colShare: "Part de la production (‰)",
    colTop10: "Top 10 % cités",
    colOa: "Accès ouvert",
    colIntl: "Collab. intl.",
    colScore: "Score (vous)",
    colRunnerUp: "2e du groupe",
    colMargin: "Écart",
    colCompared: "Étab. comparés",
  },

  dataTable: {
    rows: "Lignes {from}–{to} sur {total}",
    goToOwn: "Aller à mon établissement",
    previous: "Page précédente",
    next: "Page suivante",
  },

  treemap: {
    hintDomain: "Cliquez sur un domaine pour explorer ses fields OpenAlex.",
    hintField: "Cliquez sur un field pour explorer ses subfields.",
    hintSubfield: "Cliquez sur un subfield pour explorer ses topics.",
    hintTopic: "Niveau le plus fin de la taxonomie OpenAlex (topics).",
    allDomains: "Tous les domaines",
    publicationSingular: "publication",
    publicationPlural: "publications",
    clickToExplore: " (cliquer pour explorer)",
    analysedFooter: "{count} publications analysées (corpus complet)",
  },

  percentileGauge: {
    notComputable: "Non classé (sous le seuil de publications ou donnée indisponible)",
    nth: "{percentile}e percentile",
    groupLabel: "Au sein du groupe de comparaison",
  },

  comparisonTable: {
    title: "Tableau comparatif des établissements",
    colRank: "Rang",
    colInstitution: "Établissement",
    colSpecialization: "Taux de spécialisation",
    colQuality: "Qualité (coef. estimé)",
    colQualityTop10: "PP(top 10 %) qualité",
    colScore: "Score global",
    ownTag: "(vous)",
    noData: "comptages OpenAlex non calculés",
    belowThreshold: "sous le seuil de publications : non classé",
    scoreButtonLabel: "Voir le calcul du score global de {name}",
    explainTitle: "Lire ce tableau",
    explainImpactLabel: "Impact —",
    explainImpact:
      "parts de publications {start}–{end} (domaine : {domain}) calculées à partir d'OpenAlex : PP(top 10 %) et " +
      "PP(top 1 %) = parmi les 10 % / 1 % les plus citées de leur domaine et année (percentile de citations " +
      "normalisé d'OpenAlex), accès ouvert, collaboration internationale. Les autres indicateurs d'impact (FWCI ≥ 1, " +
      "≥ 10 citations, citées, collaboration industrielle) figurent au-dessus et dans le détail de chaque score.",
    explainSpecializationLabel: "Taux de spécialisation —",
    explainSpecialization: "part des publications de l'établissement dans le domaine « {domain} ».",
    explainSpecializationNA:
      "non calculé en mode « Tous les domaines » (choisissez un domaine dans l'en-tête) : l'axe Spécialisation est " +
      "alors exclu du score global.",
    explainQualityLabel: "Qualité —",
    explainQuality:
      "coefficient de la grille d'évaluation qualitative estimé à partir des critères comptables dans OpenAlex, hors " +
      "critères d'impact (×1 = neutre ; au-dessus de 1, les facteurs de qualité vérifiés l'emportent), et part des " +
      "publications parmi les 10 % de meilleure qualité des publications du groupe.",
    explainScoreLabel: "Score global (0–100) —",
    explainScore:
      "chaque indicateur est converti en percentile parmi les établissements ayant au moins {min} publications, les " +
      "percentiles sont moyennés par axe, puis les axes pondérés selon le profil « {profile} » : Impact {impact} %, " +
      "Spécialisation {spec} %, Qualité {quality} %. Un axe sans donnée est exclu et les autres renormalisés. " +
      "Cliquez sur un score pour voir son calcul détaillé.",
  },

  scoreBreakdown: {
    title: "Calcul du score global — {name}",
    intro:
      "Chaque indicateur est converti en percentile au sein du groupe de comparaison (0 = plus faible, 100 = plus " +
      "élevé). Score d'axe = moyenne des percentiles pondérée par les poids des indicateurs ; score global = moyenne " +
      "des scores d'axe pondérée par les poids des axes. Les indicateurs ou axes sans donnée sont exclus et leurs " +
      "poids redistribués (colonne « poids appliqué »).",
    profile: "Profil de comparaison : « {profile} ».",
    axisLine: "score {score} × poids {applied} (profil : {weight}) = {contribution} points",
    zeroWeight: "score {score}, poids nul dans le profil : non compté",
    notApplicable: "Non applicable (mode « Tous les domaines ») : axe exclu, poids redistribué",
    noData: "Aucune donnée : axe exclu, poids redistribué",
    colIndicator: "Indicateur",
    colValue: "Valeur",
    colPercentile: "Percentile",
    colWeight: "Poids",
    colApplied: "Poids appliqué",
    qualityWeightsNote:
      "Poids des catégories de qualité : réglés pour toute l'instance dans Paramètres d'évaluation qualitative.",
    total: "Score global =",
    footer:
      "Percentiles calculés parmi les établissements du groupe ayant au moins le seuil de publications (Configuration).",
  },

  parametresBenchmark: {
    title: "Paramètres du benchmark",
    profilesTitle: "Profils de comparaison",
    profilesIntro:
      "Définissez sous quels angles vous souhaitez comparer votre établissement. Choisissez ou créez " +
      "des profils de comparaison en attribuant des poids aux indicateurs disponibles.",
    currentProfile: "Profil actuel : ",
    currentProfileTooltip:
      "Le profil de comparaison actuel pondère les axes du score global (impact en citations, taux de " +
      "spécialisation, qualité des publications) et les indicateurs de l'axe impact. Il peut aussi être changé " +
      "depuis l'en-tête du tableau de bord.",
    defaultBadge: "par défaut",
    deleteProfileConfirm: "Supprimer ce profil de comparaison ?",
    deleteProfileError: "Erreur lors de la suppression.",
    newProfile: "Nouveau profil de comparaison",
    groupsTitle: "Groupes de comparaison",
    groupsIntro:
      "Définissez avec quel groupe vous souhaitez comparer votre établissement. Choisissez parmi " +
      "les groupes disponibles ou créez vos propres groupes.",
    currentGroup: "Groupe actuel : ",
    currentGroupTooltip:
      "Le groupe de comparaison actuel sert de référence pour les percentiles affichés sur le tableau " +
      "de bord. Il peut aussi être changé depuis l'en-tête du tableau de bord.",
    memberCount: "{count} établissements",
    leidenImportRunningNote:
      "Un import Leiden est en cours d'exécution — les groupes de comparaison se rafraîchiront automatiquement.",
    deleteGroupConfirm: "Supprimer ce groupe de comparaison ?",
    deleteGroupError: "Erreur lors de la suppression.",
    newGroup: "Nouveau groupe de comparaison",
    typeGeographic: "Géographique",
    typeSizeBracket: "Tranche de taille",
    typeCustom: "Personnalisé",
  },

  weightProfileModal: {
    editTitle: "Modifier le profil de comparaison",
    newTitle: "Nouveau profil de comparaison",
    nameLabel: "Nom du profil",
    nameEmptyError: "Le nom du profil ne peut pas être vide.",
    unlock: "Déverrouiller ce poids",
    lock: "Verrouiller ce poids",
    advancedIndicators: "Indicateurs avancés",
    saveError: "Erreur lors de l'enregistrement.",
    saveButton: "Sauvegarder le profil",
    defaultProfileName: "Profil de comparaison {n}",
    qualityWeightsNote:
      "La pondération entre facteurs ex-ante, intrinsèques et ex-post se règle dans Paramètres d'évaluation " +
      "qualitative (commune à toute l'instance).",
  },

  peerGroupModal: {
    editTitle: "Modifier le groupe de comparaison",
    newTitle: "Nouveau groupe de comparaison",
    nameLabel: "Nom du groupe",
    namePlaceholder: "Nom du groupe de comparaison",
    selectedCount: "{count} établissement(s) sélectionné(s)",
    addLabel: "Ajouter des établissements",
    searchPlaceholder: "Ex. Sorbonne, MIT, Oxford… (min. 2 caractères)",
    searching: "…",
    search: "Rechercher",
    searchError: "Erreur lors de la recherche.",
    noResults:
      "Aucun établissement trouvé pour « {query} ». La recherche ne porte que sur les établissements " +
      "présents dans le référentiel Leiden Ranking.",
    saveError: "Erreur lors de l'enregistrement.",
    saveButton: "Sauvegarder le groupe",
  },

  leidenImport: {
    title: "Aucune donnée Leiden importée",
    tooltip:
      "Les groupes de comparaison prédéfinis (géographique, tranche de taille) et la recherche " +
      "d'établissements pour un groupe personnalisé dépendent tous du référentiel Leiden Ranking Open " +
      "Edition. Sans un premier import, ces fonctionnalités sont vides — ce n'est pas un bug, juste une étape manquante.",
    body:
      "Les groupes prédéfinis et la recherche d'établissements ci-dessous nécessitent le fichier XLSX " +
      "du Leiden Ranking Open Edition (téléchargé manuellement depuis Zenodo). Importez-le ici pour " +
      "débloquer ces fonctionnalités. Une fois l'import terminé, les groupes de comparaison par défaut " +
      "(géographique, tranches de taille) sont recréés automatiquement.",
    yearPlaceholder: "Année",
    uploading: "Envoi…",
    importButton: "Importer",
    error: "Erreur lors de l'import.",
    successSuffix: " L'import s'exécute en tâche de fond ; les groupes se recalculent automatiquement à la fin.",
  },

  peerTopicCache: {
    computing: "Calcul en cours…",
    trigger: "Calculer les topics et la qualité des pairs",
    tooltip:
      "Calcule, pour votre établissement et les membres de ce groupe, les statistiques par topic OpenAlex " +
      "(section « Topics signature » : 4 requêtes group_by paginées par établissement) et les comptages par " +
      "domaine OpenAlex de l'onglet Groupes de comparaison (impact et qualité : environ 30 requêtes par " +
      "établissement), sur " +
      "la période Leiden courante. Peut prendre plusieurs minutes pour un grand groupe ; les comptages qualité " +
      "sont rafraîchis tous les 90 jours, les statistiques par topic à chaque nouvelle période Leiden.",
    complete: "Terminé ({done}/{total})",
    inProgress: "{done}/{total}",
    error: "Erreur lors du calcul.",
  },

  quality: {
    title: "Qualité des publications (grille d'évaluation qualitative)",
    subtitle:
      "Critères de la grille d'évaluation qualitative appliqués automatiquement à chaque publication, à partir " +
      "de sources ouvertes (OpenAlex, Crossref, HAL, PubMed, DOAJ, Retraction Watch).",
    allDomainsChip: "Tous domaines (non filtré par grand domaine)",
    domainNote:
      "Les publications OpenAlex ne portent pas de grand domaine Leiden : cette section n'est pas affectée par " +
      "le filtre de grand domaine de l'en-tête. Le filtre « publications core » s'applique.",
    notAvailableBefore:
      "Les indicateurs qualitatifs n'ont pas encore été calculés. Le calcul est automatique chaque nuit après la " +
      "synchronisation OpenAlex ; il peut aussi être lancé depuis la page ",
    notAvailableAfter: ".",
    running: "Calcul en cours…",
    loadError: "Erreur lors du chargement des indicateurs qualitatifs.",
    worksEvaluated: "Publications évaluées",
    worksEvaluatedValue: "{n} / {total}",
    worksEvaluatedTooltip:
      "Publications du corpus synchronisé passées dans la grille lors du dernier calcul ({date}). Un écart avec " +
      "le corpus actuel signifie que des publications ont été synchronisées depuis.",
    medianCoefficient: "Coefficient médian",
    medianCoefficientTooltip:
      "Coefficient multiplicatif de la grille (facteurs extrinsèques : canal de publication, évaluation par les " +
      "pairs, accès ouvert, indexation, intégrité, citations…). 1 = aucun facteur positif ni négatif vérifié. " +
      "Le score final de la grille (score de base × coefficient) n'est pas affiché : tous les critères à points " +
      "(sections du texte, données, code, déclarations) nécessitent la lecture du texte intégral et ne sont pas " +
      "automatisés à ce stade.",
    criteriaCovered: "Critères couverts",
    criteriaCoveredValue: "{n} / {total}",
    criteriaCoveredTooltip:
      "Critères de la grille ({grid}) tranchés automatiquement pour au moins une publication. Les autres " +
      "nécessitent le texte intégral, une source payante, ou des appels par auteur trop coûteux à l'échelle " +
      "d'un établissement (historique de publication des auteurs, travaux citants) : ils ne sont pas comptés " +
      "comme « Non ».",
    histogramTitle: "Distribution du coefficient de qualité",
    histogramTooltip:
      "Nombre de publications par tranche de coefficient. La dernière tranche regroupe les valeurs au-delà du " +
      "99e centile. p10 = {p10}, médiane = {median}, p90 = {p90}.",
    histogramPublications: "Publications",
    histogramRange: "Coefficient {start} – {end}",
    histogramRangeOpen: "Coefficient ≥ {start}",
    criteriaTitle: "Résultats par critère",
    criteriaTooltip:
      "% Oui : part des publications répondant « Oui » parmi celles où le critère a pu être tranché (Oui ou Non). " +
      "Couverture : part des publications pour lesquelles une source a répondu (y compris « Indéterminé »). " +
      "Le sens positif ou négatif d'un « Oui » dépend du critère (ex. avis de rétractation).",
    colCriterion: "Critère",
    colRole: "Effet",
    colShareYes: "% Oui",
    colCoverage: "Couverture",
    colCounts: "Oui / Non / Indét.",
    roleCoefficient: "coef.",
    roleCoefficientTooltip: "Multiplie le coefficient de la publication quand le critère est vérifié.",
    rolePoints: "points",
    rolePointsTooltip: "Ajoute des points au score de base quand le critère est vérifié.",
    roleModulator: "modul.",
    roleModulatorTooltip: "Ajuste le poids d'un autre critère quand il est vérifié.",
    roleNone: "—",
    criteriaCount: "{n} critère(s)",
    worksTitle: "Publications",
    worksHighest: "Coefficients les plus élevés",
    worksLowest: "Coefficients les plus faibles",
    worksEmpty: "Aucune publication évaluée.",
    detailTitle: "Détail de l'évaluation",
    detailLoading: "Reconstitution des preuves…",
    detailError: "Erreur lors du chargement du détail.",
    detailCoefficient: "Coefficient : {value}",
    detailSource: "Source : {source}",
    detailNote:
      "Preuves reconstituées à partir des données mises en cache lors du dernier calcul. Confiance « heuristique » : " +
      "inférence indirecte, à vérifier en priorité.",
    verdictYes: "Oui",
    verdictNo: "Non",
    verdictUndetermined: "Indét.",
    confidenceHeuristic: "heuristique",
    sourcesFooter:
      "Grille {grid}. Sources : {crossref} notices Crossref, {hal} publications déposées dans HAL, {pubmed} notices " +
      "PubMed ; dump DOAJ du {doaj}, Retraction Watch du {rw}.",
    sourcesFooterLlm: " Évaluation par les pairs hors DOAJ : {n} revue(s) lue(s) par le modèle {model}.",
    errorsNote: "{n} publication(s) n'ont pas pu être évaluées (données incohérentes).",
  },

  qualitySettings: {
    title: "Paramètres d'évaluation qualitative",
    intro:
      "Poids et seuils de la grille d'évaluation qualitative, communs à toute l'instance. Ils déterminent le " +
      "coefficient de chaque publication (section « Qualité des publications ») et l'axe Qualité du score " +
      "global. Enregistrer relance l'évaluation de toutes les publications à partir des données en cache (aucun " +
      "appel aux API, une dizaine de minutes).",
    gridTitle: "Poids et seuils des critères de la grille",
    categoryWeightsTitle: "Pondération des catégories de facteurs (axe Qualité, onglet Groupes de comparaison)",
    categoryWeightsIntro:
      "Poids relatifs des facteurs extrinsèques ex-ante, intrinsèques et extrinsèques ex-post, communs à toute " +
      "l'instance. Ils déterminent le score de l'axe Qualité (moyenne pondérée des percentiles des trois " +
      "catégories) et le coefficient estimé global de chaque établissement, ainsi que ses parts dans le top " +
      "50 / 25 / 10 % en qualité (des poids égaux redonnent le produit des trois coefficients de la grille). " +
      "Appliqués immédiatement, sans réévaluation des publications. Le coefficient publication par publication de " +
      "la section « Qualité des publications » n'est pas affecté.",
    category_qualite_ex_ante: "Facteurs extrinsèques ex-ante",
    category_qualite_intrinseque: "Facteurs intrinsèques",
    category_qualite_ex_post: "Facteurs extrinsèques ex-post",
    categoryWeightsTotal: "Total : {total} %",
    categoryWeightsNormalize: "Enregistrer (ramené à 100 %)",
    categoryWeightsNormalizeHint: "Les poids seront proportionnellement ramenés à un total de 100 %.",
    categoryWeightsEqual: "Poids égaux",
    categoryInactive: "aucun critère valide hors impact : poids 0",
    categoryWeightsSaved: "Pondération enregistrée : appliquée au tableau de bord.",
    roleHelp:
      "Coefficient : multiplie le coefficient de la publication quand le critère est vérifié (1 = neutre, " +
      "> 1 = bonus, < 1 = pénalité, 0 = exclusion). Points : s'ajoutent au score de base. Modulateur : ajuste " +
      "l'effet d'un autre critère quand il est vérifié (1 = neutre).",
    searchPlaceholder: "Rechercher un critère (numéro ou libellé)…",
    filterAll: "Tous",
    filterAutomated: "Calculés automatiquement",
    filterComparable: "Comparables aux pairs",
    filterModified: "Modifiés",
    save: "Enregistrer ({n} modification(s))",
    saving: "Enregistrement…",
    discard: "Annuler les modifications",
    reset: "Revenir à la grille par défaut",
    resetConfirm:
      "Revenir aux poids et seuils de la grille par défaut ({file}) ? Toutes les modifications enregistrées " +
      "seront perdues et les publications réévaluées.",
    saved: "Enregistré. Réévaluation des publications lancée en arrière-plan.",
    saveError: "Erreur lors de l'enregistrement.",
    running:
      "Réévaluation en cours : les modifications ne peuvent pas être enregistrées avant la fin du calcul.",
    statusDefault: "Grille par défaut ({file}).",
    statusModified: "Grille modifiée le {date}.",
    badgeAutomated: "auto",
    badgeAutomatedTooltip: "Critère tranché automatiquement pour au moins une publication lors du dernier calcul.",
    badgeComparable: "pairs",
    badgeImpact: "impact",
    badgeImpactTooltip:
      "Critère compté dans OpenAlex pour chaque établissement des groupes de comparaison et présenté comme " +
      "indicateur d'impact (citations, accès ouvert, collaborations) : il n'entre pas dans l'axe Qualité, pour ne " +
      "pas être compté deux fois. Son poids reste utilisé pour le coefficient publication par publication.",
    badgeComparableTooltip:
      "Critère également compté dans OpenAlex pour chaque établissement des groupes de comparaison : il entre " +
      "dans l'axe Qualité du score global.",
    roleCoefficient: "×",
    rolePoints: "+ pts",
    roleModulator: "modul. de {target}",
    roleNone: "sans poids",
    defaultValue: "défaut : {value}",
    criteriaShown: "{n} critère(s)",
    noResult: "Aucun critère ne correspond.",
  },

  qualityBenchmark: {
    title: "Positionnement dans le groupe de comparaison",
    tooltip:
      "Calculé de la même façon pour chaque établissement du groupe (y compris le vôtre) à partir des comptages " +
      "OpenAlex : c'est l'axe Qualité du score global. Il diffère du coefficient médian ci-dessus, calculé " +
      "publication par publication sur l'ensemble des critères automatisés.",
    methodLabel: "Mode de calcul :",
    method:
      "pour chaque établissement du groupe ayant au moins {min} publications {start}–{end} sur le périmètre choisi, " +
      "part de ses publications vérifiant chacun des critères de la grille comptables dans OpenAlex (hors critères " +
      "d'impact, présentés comme indicateurs d'impact). En supposant les critères indépendants, on en déduit la " +
      "distribution du coefficient de qualité de ses publications : le coefficient estimé en est la moyenne " +
      "géométrique, et — comme le Leiden Ranking pour les citations — P est le nombre de publications, P(top x %) " +
      "et PP(top x %) le nombre et la part de publications parmi les x % de meilleure qualité de l'ensemble des " +
      "publications du groupe (ex æquo au seuil comptés au prorata). Sur l'ensemble du groupe, PP(top 10 %) vaut " +
      "donc exactement 10 %.",
    weightsNote:
      "Pondération des catégories (Paramètres d'évaluation qualitative) : ex-ante {exAnte} %, intrinsèques " +
      "{intrinsic} %, ex-post {exPost} %.",
    inactiveNote:
      "Sans critère non neutre dans la grille actuelle : {categories} — catégorie exclue du score de l'axe, son " +
      "poids redistribué.",
    inactive: "Aucun critère non neutre : exclu du score",
    unavailable:
      "Comparaison indisponible : comptages OpenAlex non calculés pour votre établissement, ou moins de {min} " +
      "publications sur ce périmètre.",
    leidenTitle: "Indicateurs de type Leiden",
    topLabel: "PP(top {level} %) qualité",
    topCount: "P(top {level} %) = {n} publications",
    axisTitle: "Coefficients estimés par catégorie (axe Qualité du score global)",
    global: "Coefficient estimé",
    axisScore: "Score de l'axe Qualité : {score} / 100",
    tableTitle: "Établissements du groupe",
    colP: "P",
    colPTop: "P(top {level} %)",
    colPPTop: "PP(top {level} %)",
    colCoefficient: "Coef. estimé",
    colAxisScore: "Score axe",
  },

  configuration: {
    title: "Configuration",
    subtitle: "Modifiez les paramètres de l'instance. Chaque section s'enregistre indépendamment.",
    institutionTitle: "Institution de référence",
    lineageCountTooltip:
      "Nombre de structures directement rattachées, tel que connu par OpenAlex (associated_institutions). " +
      "Informatif uniquement : l'ingestion des publications couvre en réalité toute la hiérarchie " +
      "(structures de toute profondeur), pas seulement ce niveau direct.",
    lineageCount: "structure(s) directement rattachée(s)",
    institutionIdLabel: "ID OpenAlex de l'établissement",
    change: "Changer",
    changing: "…",
    changeWarning:
      "Les nouvelles données n'apparaîtront qu'à la prochaine synchronisation automatique (nocturne) — " +
      "contrairement à la configuration initiale, ce changement ne déclenche pas de synchronisation immédiate.",
    genericError: "Erreur lors de la mise à jour.",
    institutionUpdated: "Institution mise à jour.",
    apiKeyTitle: "Clé API OpenAlex",
    apiKeyTooltip: "Par sécurité, la clé actuellement enregistrée n'est jamais affichée. Saisissez une nouvelle clé uniquement si vous souhaitez la remplacer.",
    apiKeyCurrent: "Clé actuelle : enregistrée (masquée)",
    apiKeyLabel: "Nouvelle clé API",
    apiKeyPlaceholder: "Laissez vide pour ne pas changer",
    apiKeyUpdated: "Clé API mise à jour.",
    emailTitle: "Email de service",
    emailLabel: "Email de contact technique",
    emailUpdated: "Email mis à jour.",
    minPublicationsTitle: "Seuil minimal de publications",
    minPublicationsIntro:
      "Nombre minimal de publications pour qu'un établissement soit comparé sur un périmètre (établissement " +
      "entier, domaine, topic) : en dessous, ses valeurs sont affichées sans percentile, rang ni score — des parts " +
      "calculées sur quelques publications ne sont pas significatives. S'applique aux deux onglets du tableau de " +
      "bord et aux topics signature.",
    minPublicationsLabel: "Publications minimum",
    minPublicationsInvalid: "Entrez un nombre entier supérieur ou égal à 1.",
    minPublicationsUpdated: "Seuil mis à jour : classements recalculés.",
    qualityTitle: "Indicateurs qualitatifs (grille d'évaluation)",
    qualityIntro:
      "Calculés automatiquement chaque nuit après la synchronisation OpenAlex. Le premier calcul sur un corpus " +
      "important peut prendre plus d'une heure (notices Crossref, HAL et PubMed récupérées par lots) ; les " +
      "suivants ne récupèrent que les nouvelles publications.",
    qualityRun: "Lancer le calcul maintenant",
    qualityStarted: "Calcul lancé en arrière-plan.",
    qualityAlreadyRunning: "Un calcul est déjà en cours.",
    qualityLastRun: "Dernier calcul : {status}, le {date} ({n} publications)",
    qualityRunning: "Calcul en cours : {n} publications traitées",
    qualityNever: "Aucun calcul effectué pour l'instant.",
    qualityFailed: "échec",
    qualitySuccess: "réussi",
    llmTitle: "Petit LLM (vLLM)",
    llmTooltip:
      "Utilisé uniquement pour le critère « évaluation par les pairs » des revues absentes du DOAJ, à partir de " +
      "leur site web, avec vérification que la citation produite figure bien sur la page. Se configure par les " +
      "variables VLLM_BASE_URL, VLLM_MODEL et VLLM_API_KEY du fichier .env.",
    llmDisabled: "Non configuré (VLLM_BASE_URL / VLLM_MODEL vides) : critère traité via DOAJ uniquement.",
    llmReachable: "Connecté : modèle {model}",
    llmModelMissing: "Connecté, mais le modèle {model} n'est pas servi par le endpoint ({models}).",
    llmUnreachable: "Endpoint injoignable ({error}).",
  },

  setup: {
    title: "Configuration initiale",
    subtitle: "Configurez l'établissement à analyser. Cette étape est requise une seule fois.",
    stepValidate: "Saisie",
    stepConfirm: "Périmètre",
    stepSave: "Enregistrement",
    saving: "Enregistrement en cours…",
    done: "Configuration enregistrée.",
    doneRedirect: "Redirection vers le tableau de bord…",
    saveError: "Erreur lors de l'enregistrement.",
  },

  openAlexValidator: {
    idLabel: "ID OpenAlex de l'établissement",
    idTooltip:
      "L'identifiant OpenAlex commence par 'I' suivi de chiffres (ex. I4210140050). Vous pouvez coller " +
      "l'URL complète (https://openalex.org/I...) — elle sera normalisée automatiquement. Trouvez votre établissement sur openalex.org.",
    idPlaceholder: "I4210140050 ou https://openalex.org/I...",
    apiKeyLabel: "Clé API OpenAlex",
    apiKeyTooltip:
      "Depuis début 2026, OpenAlex requiert une clé API pour les usages en production. Obtenez-la " +
      "gratuitement via votre compte sur openalex.org (paramètres du compte). La clé est stockée en " +
      "base de données et ne sera plus affichée après validation.",
    apiKeyPlaceholder: "Votre clé API OpenAlex",
    emailLabel: "Email de contact technique",
    emailTooltip:
      "Utilisé comme paramètre mailto= dans les appels OpenAlex, en complément de la clé API. " +
      "Recommandé par OpenAlex pour une meilleure identification des flux.",
    emailPlaceholder: "contact@votre-etablissement.fr",
    genericError: "Erreur de connexion à l'API OpenAlex. Vérifiez l'ID et la clé API.",
    submit: "Valider et continuer",
  },

  lineageConfirm: {
    nameLabel: "Nom d'affichage de l'établissement",
    nameHint: "Pré-rempli depuis OpenAlex — modifiable.",
    perimeterLabel: "Périmètre institutionnel (lineage ROR) ",
    perimeterTooltip:
      "Le périmètre d'ingestion inclut l'établissement configuré et ses structures 'enfants' (ex. " +
      "composantes d'une université fédérale). Ces structures sont détectées à partir du champ " +
      "associated_institutions d'OpenAlex (relation 'child'), pas du seul champ lineage — pour de " +
      "nombreux établissements français, lineage revient vide au-delà de l'établissement lui-même alors " +
      "que associated_institutions liste bien les composantes réelles. Note méthodologique : ce " +
      "périmètre reste une curation OpenAlex, pas une hiérarchie ROR officielle, et peut différer de " +
      "celui retenu par le Leiden Ranking (voir §4.1 de la spécification).",
    federatedDetected: "Établissement fédéral/fusionné détecté :",
    federatedBody:
      " l'ingestion couvrira {count} structures. Vérifiez que la liste ci-dessous est correcte avant " +
      "de continuer. Les données ROR pour le système français peuvent être incomplètes (certaines " +
      "composantes manquantes ou incluses par erreur).",
    noChildren:
      "Aucune structure enfant détectée (ni via lineage, ni via associated_institutions). " +
      "L'ingestion couvrira l'établissement seul.",
    mainInstitutionBadge: "établissement principal",
    rorSuffix: " · ROR: {ror}",
    manualEditNote:
      "En v1, le périmètre ne peut pas être modifié manuellement. Si une structure est manquante ou " +
      "incorrecte, signalez-le à l'équipe OpenAlex/ROR ou documentez l'écart.",
    back: "Retour",
    confirm: "Confirmer et enregistrer",
  },

  login: {
    appName: "CRISalid Benchmark",
    title: "Connexion",
    usernameLabel: "Identifiant",
    passwordLabel: "Mot de passe",
    submit: "Se connecter",
    genericError: "Erreur de connexion.",
  },

  axis: {
    impact_scientifique: "Impact en citations",
    specificite_disciplinaire: "Taux de spécialisation",
    qualite: "Qualité des publications",
  },

  indicator: {
    p: "Publications (P)",
    pp_top_1: "PP(top 1 %)",
    pp_top_10: "PP(top 10 %)",
    pp_fwci_1: "FWCI ≥ 1",
    pp_10_cits: "≥ 10 citations",
    pp_cited: "Citées au moins 1 fois",
    pp_oa: "Accès ouvert",
    pp_int_collab: "Collab. internationale",
    pp_industry_collab: "Collab. industrielle",
    taux_specialisation: "Taux de spécialisation",
    qualite_ex_ante: "Qualité — facteurs ex-ante",
    qualite_intrinseque: "Qualité — facteurs intrinsèques",
    qualite_ex_post: "Qualité — facteurs ex-post",
  },

  indicatorDescription: {
    pp_top_1:
      "Part des publications parmi les 1 % les plus citées de leur domaine et de leur année (percentile de " +
      "citations normalisé d'OpenAlex, critère 106.1 de la grille).",
    pp_top_10:
      "Part des publications parmi les 10 % les plus citées de leur domaine et de leur année (percentile de " +
      "citations normalisé d'OpenAlex, critère 106) — équivalent OpenAlex du PP(top 10 %) de Leiden.",
    pp_fwci_1:
      "Part des publications dont l'impact normalisé (FWCI d'OpenAlex) atteint au moins la moyenne mondiale " +
      "(critère 107). Remplace le MNCS, non reproductible à partir de comptages.",
    pp_10_cits: "Part des publications citées au moins 10 fois (seuil absolu, non normalisé ; critère 69).",
    pp_cited: "Part des publications citées au moins une fois (critère 65).",
    pp_oa: "Part des publications en accès ouvert (OpenAlex, critère 4).",
    pp_int_collab: "Part des publications dont les auteurs sont affiliés dans au moins deux pays (critère 14.4).",
    pp_industry_collab:
      "Part des publications co-signées par une entreprise et un établissement académique (critère 14.3).",
    taux_specialisation:
      "Part des publications de l'établissement dans le domaine OpenAlex sélectionné " +
      "dans l'en-tête — valorise les établissements spécialisés dans ce domaine. Percentile au sein du groupe de " +
      "comparaison. Non calculé en mode « Tous les domaines » : l'axe est alors exclu du score global.",
    qualite_ex_ante:
      "Coefficient de qualité estimé sur les critères « ex-ante » de la grille d'évaluation (canal de publication, " +
      "accès ouvert, indexation, métadonnées, financement, collaborations) comptables dans OpenAlex pour chaque " +
      "établissement, pondérés par les poids de la page Paramètres d'évaluation qualitative. Percentile au sein du groupe.",
    qualite_intrinseque:
      "Coefficient de qualité estimé sur les critères intrinsèques comptables dans OpenAlex (rétractation, langue, " +
      "références), pondérés par la grille. Les critères intrinsèques à points (sections, données, code) nécessitent " +
      "le texte intégral et n'y figurent pas. Percentile au sein du groupe.",
    qualite_ex_post:
      "Coefficient de qualité estimé sur les critères « ex-post » comptables dans OpenAlex hors critères d'impact " +
      "(citations et FWCI sont des indicateurs d'impact), pondérés par la grille. Percentile au sein du groupe.",
  },

  leidenDomain: {
    "All sciences": "Tous les domaines",
    "Biomedical and health sciences": "Sciences biomédicales et de la santé",
    "Life and earth sciences": "Sciences de la vie et de la Terre",
    "Mathematics and computer science": "Mathématiques et informatique",
    "Physical sciences and engineering": "Sciences physiques et ingénierie",
    "Social sciences and humanities": "Sciences sociales et humaines",
  },
} as const;
