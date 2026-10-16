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

// Default weight profile values
export const DEFAULT_AXIS_WEIGHTS = {
  impact_scientifique: 0.4,
  specificite_disciplinaire: 0.3,
  qualite: 0.3,
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
  // Estimated evaluation-grid coefficient per grid category, from the
  // OpenAlex-countable criteria (backend services/quality/comparable.py).
  qualite: {
    qualite_ex_ante: 1 / 3,
    qualite_intrinseque: 1 / 3,
    qualite_ex_post: 1 / 3,
  },
};

// AXIS_LABELS / INDICATOR_LABELS / SUB_INDICATOR_DESCRIPTIONS moved to
// lib/i18n/fr.ts (axis.*, indicator.*, indicatorDescription.*) — todo.md
// item 17, single-file i18n. Look them up via t(`axis.${key}`) etc.
