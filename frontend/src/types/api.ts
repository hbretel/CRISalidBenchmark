// Types mirroring backend Pydantic schemas.
// Keep in sync with the backend API responses.

export interface ConfigResponse {
  openalex_institution_id: string;
  ror_id: string | null;
  institution_name: string;
  openalex_lineage_ids: string[];
  api_key_set: boolean;
  contact_email: string;
  country_code: string | null;
  configured_at: string;
}

export interface LineageInfo {
  openalex_id: string;
  display_name: string;
  ror_id: string | null;
  country_code: string | null;
}

export interface ValidateResponse {
  openalex_institution_id: string;
  institution_name: string;
  ror_id: string | null;
  country_code: string | null;
  lineage: LineageInfo[];
}

export interface InstitutionSummary {
  institution_name: string;
  openalex_institution_id: string;
  country_code: string | null;
  total_works: number;
  core_works: number;
  total_citations: number;
  core_citations: number;
  h_index: number;
  period_start: number | null;
  period_end: number | null;
  last_openalex_sync: string | null;
  leiden_snapshot_year: number | null;
  leiden_decile: number | null;
  leiden_decile_label: string | null;
}

export interface SynthesisCounts {
  field: string;
  core_only: boolean;
  source: "openalex" | "leiden";
  publications: number | null;
  citations: number | null;
}

export interface Indicator {
  value: number | null;
  percentile: number | null;
  source: string;
  description: string;
}

export interface HeadlineImpactIndicator extends Indicator {
  value_lb: number | null;
  value_ub: number | null;
  leiden_column: "pp_top_10" | "pp_10_cits";
  non_equivalent_across_toggle: true;
}

export interface MncsIndicator extends Indicator {
  value_lb: number | null;
  value_ub: number | null;
}

export interface ImpactIndicators {
  field: string;
  core_only: boolean;
  snapshot_year: number | null;
  period_start: number | null;
  period_end: number | null;
  peer_group_size: number;
  indicators: {
    // Toggle-dependent: pp_top_10 (core_only=true) or pp_10_cits (core_only=false).
    // These are NOT equivalent indicators — see leiden_column + description.
    impact_normalise_leiden: HeadlineImpactIndicator;
    mncs: MncsIndicator;
    citations_brutes_moyennes: Indicator;
    h_index_core: Indicator;
    oa_pct: Indicator;
    collab_intl_pct: Indicator;
  };
}

export interface HerfindahlIndex {
  value: number;
  label: string;
  explanation: string;
  description: string;
}

export interface SignatureTopic {
  topic_id: string;
  topic_name: string;
  own_publication_count: number;
  own_share_permille: number;
  peer_avg_share_permille: number;
  ratio: number;
}

/** Domain > Field > Subfield > Topic node — `children` is absent on leaves (Topics). */
export interface TopicTreeNode {
  id: string;
  name: string;
  value: number;
  children?: TopicTreeNode[];
}

export interface SpecificityIndicators {
  thematic_profile: TopicTreeNode[];
  herfindahl: HerfindahlIndex;
  topics_signature: {
    items: SignatureTopic[];
    threshold: number;
    peer_cache_populated: boolean;
    description: string;
  };
  total_works_analysed: number;
  peer_group_size: number;
}

export interface PeerGroupSummary {
  id: number;
  name: string;
  type: "geographic" | "size_bracket" | "custom";
  member_count: number;
  generated_at: string | null;
  params: Record<string, unknown>;
}

export interface PeerMemberInfo {
  ror_id: string;
  university_name: string | null;
  country_code: string | null;
  p: number | null;
}

export interface WeightProfileResponse {
  id: number;
  name: string;
  axis_weights: Record<string, number>;
  sub_indicator_weights: Record<string, Record<string, number>>;
  is_default: boolean;
  created_at: string;
}

export interface SyncJob {
  id: number;
  job_name: string;
  status: "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  records_processed: number;
  error_message: string | null;
}

export interface LeidenSummary {
  snapshot_year: number;
  period: string | null;
  row_count: number;
  institution_count: number;
  imported_at: string | null;
}

export interface PeerComparisonRow {
  quality_coefficient: number | null;
  quality_axis_score: number | null;
  ror_id: string;
  name: string | null;
  country_code: string | null;
  is_own: boolean;
  p_total: number | null;
  headline_value: number | null;
  headline_percentile: number | null;
  mncs: number | null;
  oa_pct: number | null;
  collab_pct: number | null;
  herfindahl_simplified: number | null;
  impact_axis_score: number;
  specificity_axis_score: number;
  composite_score: number;
}

export interface PeerComparisonTable {
  rows: PeerComparisonRow[];
  snapshot_year: number | null;
  core_only: boolean;
  field: string;
  headline_column: "pp_top_10" | "pp_10_cits";
  specificity_note: string;
}

export interface CompositeScore {
  weight_profile_id: number;
  peer_group_id: number;
  composite_score: number;
  axis_scores: Record<string, number>;
  axis_weights: Record<string, number>;
  sub_weights: Record<string, Record<string, number>>;
}

export interface QualityCriterion {
  id: string;
  parent_id: string | null;
  category: string;
  subcategory: string;
  label: string;
  type: string;
  role: "points" | "coefficient" | "modulateur" | "aucun";
  active_answer: string;
  yes: number;
  no: number;
  undetermined: number;
  share_yes: number | null;
  coverage: number | null;
}

export interface QualityHistogramBin {
  start: number;
  end: number;
  count: number;
  open_ended: boolean;
}

export interface QualityCoefficientSummary {
  mean: number;
  median: number;
  p10: number;
  p90: number;
  min: number;
  max: number;
  histogram: QualityHistogramBin[];
}

export interface QualitySummary {
  available: boolean;
  running: boolean;
  core_only: boolean;
  n_corpus: number;
  computed_at?: string;
  run_date?: string;
  n_works?: number;
  n_scored?: number;
  n_errors?: number;
  coefficient?: QualityCoefficientSummary | null;
  grid_file?: string;
  n_criteria_grid?: number;
  n_criteria_reached?: number;
  sources?: {
    crossref_records: number;
    hal_deposits: number;
    pubmed_records: number;
    doaj_dump_date: string | null;
    retraction_watch_dump_date: string | null;
    llm_journals: number;
    llm_model: string | null;
  };
  categories?: {
    name: string;
    subcategories: { name: string; criteria: QualityCriterion[] }[];
  }[];
}

export interface QualityWorkRow {
  id: string;
  title: string | null;
  publication_year: number | null;
  doi: string | null;
  coefficient: number;
}

export interface QualityWorksPage {
  total: number;
  works: QualityWorkRow[];
}

export type QualityVerdict = "Oui" | "Non" | "Indéterminé";

export interface QualityWorkCriterion
  extends Omit<QualityCriterion, "yes" | "no" | "undetermined" | "share_yes" | "coverage"> {
  verdict: QualityVerdict;
  confidence: "haute" | "heuristique";
  evidence: string;
}

export interface QualityWorkDetail {
  id: string;
  title: string | null;
  doi: string | null;
  publication_year: number | null;
  type: string | null;
  source: string | null;
  score: { score_base: number | null; coefficient: number | null; score_final: number | null; error: string | null };
  contributions: { kind: string; id: string; value: number }[];
  criteria: QualityWorkCriterion[];
}

export interface GridParameter {
  name: string;
  value: number;
  default: number;
  unit: string;
}

export interface GridCriterion {
  id: string;
  parent_id: string | null;
  category: string;
  subcategory: string;
  label: string;
  type: string;
  role: "points" | "coefficient" | "modulateur" | "aucun";
  active_answer: string;
  modulates: string | null;
  weight: number | null;
  default_weight: number | null;
  parameters: GridParameter[];
  automated: boolean;
  comparable: boolean;
}

export interface GridCalibration {
  has_overrides: boolean;
  updated_at: string | null;
  running: boolean;
  default_grid_file: string;
  criteria: GridCriterion[];
}

export interface QualityBenchmark {
  available: boolean;
  group_size: number;
  institutions_with_data: number;
  n_criteria: number;
  estimates: Record<string, number> | null;
  percentiles: Record<string, number> | null;
  global_percentile: number | null;
}

export interface LlmStatus {
  enabled: boolean;
  reachable: boolean;
  model: string | null;
  models: string[];
  model_available?: boolean;
  error?: string;
}
