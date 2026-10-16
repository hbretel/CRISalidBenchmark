// Leiden Ranking field values (exactly 6: "All sciences" + 5 macro-domains,
// as they literally appear in the leiden_snapshot.field column — confirmed
// v1.6 on a real Leiden export). Used directly as `field` query param values.
// Note: Leiden uses 5 domains; OpenAlex uses 4 different domain names —
// a mapping table is needed for cross-referencing raw OpenAlex indicators
// by domain (see §12 of the spec, deferred/not yet built).
// Labels live in lib/i18n/fr.ts (leidenDomain.*) — this is enum values only.
export const LEIDEN_DOMAINS = [
  { value: "All sciences" },
  { value: "Biomedical and health sciences" },
  { value: "Life and earth sciences" },
  { value: "Mathematics and computer science" },
  { value: "Physical sciences and engineering" },
  { value: "Social sciences and humanities" },
] as const;

// OpenAlex domains (level 1 of the Topics taxonomy), used by the "Groupes de
// comparaison" tab — the OpenAlex counterpart of Leiden's main fields, no
// mapping between the two. Values are the backend `domain` query parameter
// (OpenAlex domain id); "all" = no domain filter. Labels: openalexDomain.*.
export const OPENALEX_DOMAINS = [
  { value: "all" },
  { value: "1" },
  { value: "2" },
  { value: "3" },
  { value: "4" },
] as const;

// Impact indicators of the comparison-group benchmark, in display order
// (shares of publications from OpenAlex counts — backend
// services/quality/comparable.py IMPACT_CRITERIA). Labels: indicator.*.
export const GROUP_IMPACT_INDICATORS = [
  "pp_top_1",
  "pp_top_10",
  "pp_fwci_1",
  "pp_10_cits",
  "pp_cited",
  "pp_oa",
  "pp_int_collab",
  "pp_industry_collab",
] as const;

// Volume indicators of the comparison-group benchmark, in display order: the
// Leiden P-type counterparts of the impact indicators (numbers of
// publications — backend services/quality/comparable.py VOLUME_COUNTS).
export const GROUP_VOLUME_INDICATORS = [
  "p",
  "p_fwci_1",
  "p_oa",
  "p_top_1",
  "p_cited",
  "p_top_10",
  "p_10_cits",
  "p_int_collab",
  "p_industry_collab",
] as const;

// Default weight profile values
export const DEFAULT_AXIS_WEIGHTS = {
  impact_scientifique: 0.25,
  volume_publications: 0.25,
  specificite_disciplinaire: 0.25,
  qualite: 0.25,
};

export const DEFAULT_SUB_WEIGHTS = {
  impact_scientifique: Object.fromEntries(GROUP_IMPACT_INDICATORS.map((k) => [k, 1 / GROUP_IMPACT_INDICATORS.length])),
  volume_publications: Object.fromEntries(GROUP_VOLUME_INDICATORS.map((k) => [k, 1 / GROUP_VOLUME_INDICATORS.length])),
  // Single indicator: share of the institution's publications in the OpenAlex
  // domain selected in the header (backend services/group_benchmark.py).
  specificite_disciplinaire: {
    taux_specialisation: 1,
  },
  // No "qualite" entry: the weighting between grid categories is
  // instance-wide, set on the "Paramètres d'évaluation qualitative" page.
};

// AXIS_LABELS / INDICATOR_LABELS / SUB_INDICATOR_DESCRIPTIONS moved to
// lib/i18n/fr.ts (axis.*, indicator.*, indicatorDescription.*) — todo.md
// item 17, single-file i18n. Look them up via t(`axis.${key}`) etc.
