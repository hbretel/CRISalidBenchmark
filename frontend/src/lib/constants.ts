// Leiden Ranking field values (exactly 6: "All sciences" + 5 macro-domains,
// as they literally appear in the leiden_snapshot.field column — confirmed
// v1.6 on a real Leiden export). Used directly as `field` query param values.
// Note: Leiden uses 5 domains; OpenAlex uses 4 different domain names —
// a mapping table is needed for cross-referencing raw OpenAlex indicators
// by domain (see §12 of the spec, deferred/not yet built).
export const LEIDEN_DOMAINS = [
  { value: "All sciences", label: "Tous les domaines" },
  { value: "Biomedical and health sciences",    label: "Sciences biomédicales et de la santé" },
  { value: "Life and earth sciences",            label: "Sciences de la vie et de la Terre" },
  { value: "Mathematics and computer science",  label: "Mathématiques et informatique" },
  { value: "Physical sciences and engineering", label: "Sciences physiques et ingénierie" },
  { value: "Social sciences and humanities",    label: "Sciences sociales et humaines" },
] as const;

// Default weight profile values
export const DEFAULT_AXIS_WEIGHTS = {
  impact_scientifique: 0.6,
  specificite_disciplinaire: 0.4,
};

export const DEFAULT_SUB_WEIGHTS = {
  impact_scientifique: {
    // Abstract key — backend resolves to pp_top_10 or pp_10_cits depending on
    // the core/all-publications toggle (spec §3.8/§5.1). Never a literal
    // Leiden column name, so a saved profile stays valid across toggle states.
    impact_normalise_leiden: 0.5,
    citations_brutes_moyennes: 0.2,
    oa_pct: 0.15,
    collab_intl_pct: 0.15,
  },
  specificite_disciplinaire: {
    herfindahl: 0.7,
    nb_topics_signature: 0.3,
  },
};

export const AXIS_LABELS: Record<string, string> = {
  impact_scientifique: "Impact en citations",
  specificite_disciplinaire: "Domaines de spécialité",
};

// Human-readable labels for sub-indicators
export const INDICATOR_LABELS: Record<string, string> = {
  impact_normalise_leiden:   "% top 10% / seuil citations (Leiden)",
  citations_brutes_moyennes:  "Citations moyennes",
  h_index_core:               "Indice h (core)",
  oa_pct:                     "% accès ouvert",
  collab_intl_pct:            "% collab. internationale",
  herfindahl:                 "Indice de Herfindahl",
  nb_topics_signature:        "Nb. topics signature",
};

// How each weighted sub-indicator is actually calculated — shown on the
// Pondération page (and reusable as tooltip text elsewhere) for transparency
// about what a weight is actually being applied to, not just its label.
export const SUB_INDICATOR_DESCRIPTIONS: Record<string, string> = {
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
};
