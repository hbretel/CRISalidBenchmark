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
      "Filtre global : le Leiden Ranking publie ses indicateurs sur 5 grands domaines (+ 'Tous les " +
      "domaines'). S'applique aux sections Synthèse et Impact en citations. La section Domaines de " +
      "spécialité utilise sa propre taxonomie OpenAlex, indépendante de ce filtre.",
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
    sectionFiltersNote:
      "Filtres appliqués à cette section — modifiables depuis l'en-tête (publications core / grand domaine) ci-dessus.",
    fullCorpus: "Corpus complet (non-core)",
    allDomainsOpenAlex: "Tous domaines (taxonomie OpenAlex)",
    specialtyIndependentNote:
      "Cette section n'est pas affectée par les filtres « publications core » et « grand domaine Leiden » " +
      "de l'en-tête : le calcul de spécificité disciplinaire porte toujours sur le corpus complet, et " +
      "utilise la taxonomie Topics OpenAlex (Domain > Field > Subfield > Topic), distincte des 5 grands " +
      "domaines Leiden.",
  },

  synthesis: {
    title: "Synthèse",
    publications: "Nombre de publications",
    publicationsTooltipCore:
      "Publications « core » : approximation de la définition Leiden (source CWTS Core, type article/revue/chapitre, anglais, non rétracté).",
    publicationsTooltipAll: "Ensemble des publications synchronisées depuis OpenAlex, sans filtre core.",
    citations: "Somme des citations",
    citationsTooltipCore: "Somme des citations reçues par les publications core.",
    citationsTooltipAll: "Somme des citations reçues par l'ensemble des publications.",
    publicationsTooltipCoreLeiden: "Publications « core » au sens du Leiden Ranking.",
    publicationsTooltipAllLeiden: "Ensemble des publications de l'établissement comptées par le Leiden Ranking.",
    leidenDomainSourceNote:
      "Grand domaine Leiden sélectionné : valeurs P et TCS du Leiden Ranking pour votre établissement " +
      "(les publications OpenAlex ne portent pas de grand domaine Leiden). Le nombre de publications par " +
      "domaine est fractionnaire (une publication interdisciplinaire est répartie entre domaines), arrondi " +
      "à l'affichage. « — » si l'établissement n'est pas classé par Leiden.",
    headlinePpTop10: "% dans le top 10% le plus cité",
    headlinePp10Cits: "% avec au moins 10 citations",
    headlineTooltip:
      "Indicateur d'impact par défaut du Leiden Ranking : en mode publications core, la part de " +
      "publications dans le top 10% le plus cité (normalisée par domaine) ; en mode toutes les " +
      "publications, la part de publications ayant reçu au moins 10 citations (seuil absolu, non " +
      "normalisé — ce n'est pas le même indicateur).",
  },

  impact: {
    title: "Impact en citations",
    methodologyNote:
      "les indicateurs Leiden (pp_top_10/pp_10_cits, pp_int_collab, pp_oa) proviennent directement du " +
      "Leiden Ranking Open Edition (comptage complet uniquement, édition {year}), normalisés par domaine " +
      "par CWTS. Les indicateurs OpenAlex (citations, h-index) sont recalculés nocturnement et non normalisés.",
    methodologyNoteLabel: "Note méthodologique :",
    toggleNonEquivalenceNote:
      " En mode « toutes les publications », l'indicateur vedette change de nature : il mesure la part " +
      "de publications ayant reçu au moins 10 citations, sans normalisation par discipline — ce n'est " +
      "pas la même chose que pp_top_10 (mode « publications core »).",
    computeError: "Erreur lors du calcul des indicateurs.",
    percentileNote: "Percentiles calculés parmi {count} établissements pairs (univers Leiden Ranking).",
    headlinePpTop10: "% top 10% cités (pp_top_10)",
    headlinePp10Cits: "% avec ≥ 10 citations (pp_10_cits)",
    hIndexWithPeriod: "Indice h (publications core, {start}–{end})",
    hIndex: "Indice h (publications core)",
    mncs: "MNCS (citations normalisées, mode core uniquement)",
    citationsAvg: "Citations moyennes par publication",
    oaPct: "% accès ouvert",
    collabPct: "% collaboration internationale",
  },

  specialty: {
    title: "Domaines de spécialité",
    subtitle: "Profil thématique de l'établissement (corpus complet, pas de filtre core).",
    fullCorpusNote:
      "cet axe utilise le corpus complet (sans filtre core), car la définition core Leiden favorise les " +
      "revues anglophones et exclurait une partie du profil SHS ou recherche appliquée. La comparaison " +
      "aux pairs est basée sur le volume de publications par topic (pas l'impact).",
    fullCorpusNoteLabel: "Note :",
    computeError: "Erreur lors du calcul.",
    herfindahlTitle: "Indice de Herfindahl (spécialisation disciplinaire)",
    herfindahlFooter:
      "Calculé au niveau field (2e niveau de la hiérarchie OpenAlex). H ∈ [0, 1] — H proche de 0 : diffus ; H proche de 1 : très concentré.",
    treemapTitle: "Carte thématique (Topics OpenAlex)",
    treemapTooltip:
      "Répartition des publications selon la taxonomie Topics d'OpenAlex (Domain > Field > Subfield > " +
      "Topic). La surface est proportionnelle au nombre de publications. Cliquez sur une case pour " +
      "explorer le niveau suivant.",
    signatureTitle: "Topics signature",
    signatureCacheNotPopulatedBefore: "Le cache de distribution par topic des pairs n'est pas encore peuplé. Rendez-vous sur",
    signatureCacheNotPopulatedAfter: " pour déclencher le calcul.",
    signatureNoneAboveThreshold: "Aucun topic ne dépasse le seuil (×{threshold}) par rapport aux pairs.",
  },

  topicsSignatureTable: {
    colName: "Nom du Topic",
    colOwnCount: "Nb. publications établissement",
    colOwnShare: "Part établissement (‰)",
    colPeerShare: "Moyenne groupe de comparaison (‰)",
    colRatio: "Taux de spécialisation",
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

  subIndicatorCard: {
    percentileLabel: "Au sein du groupe de comparaison",
    sourceLabel: "Source : {source}",
    sourceLeiden: "Leiden Ranking",
    sourceOpenalex: "OpenAlex (nocturne)",
    sourceBoth: "OpenAlex + Leiden",
  },

  percentileGauge: {
    notComputable: "Percentile non calculable (données OpenAlex uniquement pour cet établissement)",
    nth: "{percentile}e percentile",
  },

  comparisonTable: {
    title: "Tableau comparatif des établissements",
    computeError: "Erreur lors du calcul du tableau comparatif.",
    colInstitution: "Établissement",
    colPublications: "Nb. publications",
    colHeadline: "Indicateur vedette (%)",
    colOa: "% accès ouvert",
    colCollab: "% collab. intl.",
    colSpecificity: "Spécificité (simplifiée)",
    colScore: "Score global",
    colQuality: "Qualité (coef. estimé)",
    tooltipQuality:
      " Qualité : coefficient de la grille d'évaluation estimé à partir des critères comptables dans OpenAlex " +
      "pour chaque établissement (identique pour tous), pondéré par les Paramètres d'évaluation qualitative. " +
      "« — » tant que le cache des pairs n'est pas calculé (Paramètres du benchmark) ; l'axe Qualité est alors " +
      "exclu du score global de l'établissement concerné et les autres axes sont renormalisés.",
    ownTag: "(vous)",
    tooltipHeadlinePpTop10: "% dans le top 10% le plus cité (pp_top_10)",
    tooltipHeadlinePp10Cits: "% avec au moins 10 citations (pp_10_cits)",
    tooltipEdition: " Indicateur vedette : {headline}, édition Leiden {year}.",
    tooltipDomain:
      " Grand domaine sélectionné : nombre de publications, indicateur vedette, % accès ouvert et % collab. " +
      "intl. portent sur ce domaine ; la spécificité simplifiée reste calculée sur l'ensemble de l'établissement.",
  },

  parametresBenchmark: {
    title: "Paramètres du benchmark",
    profilesTitle: "Profils de comparaison",
    profilesIntro:
      "Définissez sous quels angles vous souhaitez comparer votre établissement. Choisissez ou créez " +
      "des profils de comparaison en attribuant des poids aux indicateurs disponibles.",
    currentProfile: "Profil actuel : ",
    currentProfileTooltip:
      "Le profil de comparaison actuel pondère les indicateurs de l'axe impact en citations et de " +
      "l'axe domaines de spécialité pour le score composite. Il peut aussi être changé depuis l'en-tête du tableau de bord.",
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
      "Peuple, pour les membres de ce groupe de pairs, le cache de distribution par topic OpenAlex (section " +
      "« Topics signature ») et les comptages des critères de qualité comparables (axe Qualité du score " +
      "composite, environ 30 requêtes OpenAlex par établissement). Peut prendre plusieurs minutes pour un " +
      "grand groupe ; les comptages qualité sont rafraîchis tous les 90 jours.",
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
      "composite des profils de comparaison. Enregistrer relance l'évaluation de toutes les publications à " +
      "partir des données en cache (aucun appel aux API, une dizaine de minutes).",
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
    badgeComparableTooltip:
      "Critère également compté dans OpenAlex pour chaque établissement du groupe : il entre dans l'axe Qualité " +
      "du score composite.",
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
      "Coefficient de la grille estimé à partir des {n} critères comptables dans OpenAlex, calculé de la même " +
      "façon pour chaque établissement du groupe (y compris le vôtre), pondéré par les Paramètres d'évaluation " +
      "qualitative. C'est l'axe Qualité du score composite. Il diffère du coefficient médian ci-dessus, calculé " +
      "publication par publication sur environ 190 critères.",
    unavailable:
      "Comparaison indisponible : le cache qualité des pairs n'est pas encore calculé. Lancez « Calculer les " +
      "topics et la qualité des pairs » depuis la page Paramètres du benchmark.",
    global: "Coefficient estimé",
    percentile: "{p}e percentile",
    coverage: "{n} établissement(s) sur {total} avec données",
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
    specificite_disciplinaire: "Domaines de spécialité",
    qualite: "Qualité des publications",
  },

  indicator: {
    impact_normalise_leiden: "% top 10% / seuil citations (Leiden)",
    citations_brutes_moyennes: "Citations moyennes",
    h_index_core: "Indice h (core)",
    oa_pct: "% accès ouvert",
    collab_intl_pct: "% collab. internationale",
    herfindahl: "Indice de Herfindahl",
    nb_topics_signature: "Nb. topics signature",
    qualite_ex_ante: "Qualité — facteurs ex-ante",
    qualite_intrinseque: "Qualité — facteurs intrinsèques",
    qualite_ex_post: "Qualité — facteurs ex-post",
  },

  indicatorDescription: {
    impact_normalise_leiden:
      "Indicateur Leiden vedette, dont la source change selon le mode actif sur la page Impact scientifique : " +
      "en mode « publications core » (par défaut) = pp_top_10, le % de publications de l'établissement dans le " +
      "top 10% le plus cité, normalisé par domaine par CWTS. En mode « toutes les publications » = pp_10_cits, " +
      "le % de publications ayant reçu au moins 10 citations — un seuil absolu, non normalisé par domaine. " +
      "Ces deux variantes ne sont pas équivalentes ; le poids ci-dessus s'applique à celle actuellement affichée.",
    citations_brutes_moyennes:
      "Citations moyennes par publication (somme des citations ÷ nombre de publications), recalculées chaque " +
      "nuit depuis OpenAlex sur les publications core par défaut. Non normalisé par domaine — un établissement " +
      "en sciences biomédicales aura mécaniquement des valeurs plus hautes qu'un établissement en SHS.",
    oa_pct:
      "Pourcentage de publications en accès ouvert (champ is_oa d'OpenAlex), recalculé chaque nuit sur le même " +
      "sous-ensemble (core par défaut) que les autres indicateurs OpenAlex de cet axe.",
    collab_intl_pct:
      "Pourcentage de publications avec au moins une affiliation d'auteur dans un pays différent de celui de " +
      "l'établissement configuré, recalculé chaque nuit depuis les données d'affiliation OpenAlex.",
    herfindahl:
      "Indice de concentration disciplinaire H = Σ(part_i)² calculé au niveau 'field' (2e niveau de la " +
      "hiérarchie Topics OpenAlex : Domain > Field > Subfield > Topic), sur l'ensemble du corpus (pas de filtre " +
      "core). H proche de 0 = production diffuse sur de nombreux champs ; H proche de 1 = forte spécialisation. " +
      "Basé sur le volume de publications, pas sur leur impact.",
    nb_topics_signature:
      "Nombre de Topics OpenAlex (niveau le plus fin, ~4500 topics) où la part de publications de l'établissement " +
      "dépasse ×1.5 la part moyenne du groupe de comparaison sélectionné (comparaison peer-relative basée sur le volume, " +
      "via le cache peer_topic_counts — voir la page Paramètres du benchmark si ce cache n'est pas encore peuplé).",
    qualite_ex_ante:
      "Coefficient de qualité estimé sur les critères « ex-ante » de la grille d'évaluation (canal de publication, " +
      "accès ouvert, indexation, métadonnées, financement, collaborations) comptables dans OpenAlex pour chaque " +
      "établissement, pondérés par les poids de la page Paramètres d'évaluation qualitative. Percentile au sein du groupe.",
    qualite_intrinseque:
      "Coefficient de qualité estimé sur les critères intrinsèques comptables dans OpenAlex (rétractation, langue, " +
      "références), pondérés par la grille. Les critères intrinsèques à points (sections, données, code) nécessitent " +
      "le texte intégral et n'y figurent pas. Percentile au sein du groupe.",
    qualite_ex_post:
      "Coefficient de qualité estimé sur les critères « ex-post » comptables dans OpenAlex (citations, top 1 % / " +
      "10 %, FWCI, ODD), pondérés par la grille. Percentile au sein du groupe.",
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
