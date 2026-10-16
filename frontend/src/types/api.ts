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
  min_publications: number;
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

/** Leiden Ranking indicators of one university ("Monde entier" tab). Proportions in %. */
export interface WorldRow {
  ror_id: string;
  name: string | null;
  country_code: string | null;
  is_own: boolean;
  /** P ≥ the instance's minimum publication count: ranked. */
  compared: boolean;
  p: number | null;
  [indicator: string]: string | number | boolean | null;
}

export interface WorldOwnIndicator {
  value: number | null;
  rank: number | null;
  percentile: number | null;
  n: number;
}

export interface WorldRanking {
  field: string;
  core_only: boolean;
  snapshot_year: number | null;
  period: string | null;
  min_publications: number;
  /** Indicator columns available for this toggle (besides P). */
  indicators: string[];
  rows: WorldRow[];
  own: { compared: boolean; n_compared: number; indicators: Record<string, WorldOwnIndicator> } | null;
}

/** Domain > Field > Subfield > Topic node — `children` is absent on leaves (Topics). */
export interface TopicTreeNode {
  id: string;
  name: string;
  value: number;
  children?: TopicTreeNode[];
}

export interface ThematicProfile {
  thematic_profile: TopicTreeNode[];
  total_works_analysed: number;
}

export interface SignatureTopic {
  topic_id: string;
  topic_name: string;
  subfield_name: string | null;
  field_name: string | null;
  own_publications: number;
  own_share_permille: number;
  own_top10_pct: number;
  own_oa_pct: number;
  own_intl_pct: number;
  own_score: number;
  runner_up_score: number | null;
  runner_up_name: string | null;
  margin: number | null;
  n_compared: number;
}

export interface TopicsSignature {
  min_publications: number;
  period_start: number | null;
  period_end: number | null;
  group_size: number;
  institutions_with_data: number;
  own_cache_populated: boolean;
  peer_cache_populated: boolean;
  axis_weights: Record<string, number>;
  items: SignatureTopic[];
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

export interface ScoreComponent {
  key: string;
  value: number | null;
  unit: string;
  percentile: number | null;
  weight: number;
  /** Weight actually applied after renormalization; null if left out (no data or zero weight). */
  applied_weight: number | null;
}

export interface ScoreAxis {
  axis: "impact_scientifique" | "specificite_disciplinaire" | "qualite";
  applicable: boolean;
  score: number | null;
  weight: number;
  applied_weight: number | null;
  contribution: number | null;
  components: ScoreComponent[];
}

/** Leiden-like quality indicators: P / PP in the top 50 / 25 / 10 % in quality. */
export type QualityTop = Record<"50" | "25" | "10", { share: number; count: number }>;

export type QualityCategoryWeights = Record<"qualite_ex_ante" | "qualite_intrinseque" | "qualite_ex_post", number>;

export interface InstitutionQuality {
  estimates: Record<string, number>;
  /** null for a category without any non-neutral criterion (excluded from the axis). */
  percentiles: Record<string, number | null>;
  axis_score: number | null;
  top: QualityTop;
}

export interface GroupBenchmarkRow {
  ror_id: string;
  name: string | null;
  country_code: string | null;
  is_own: boolean;
  /** Counts cached for this institution (peer cache filled). */
  has_data: boolean;
  /** P ≥ the instance's minimum publication count on the scope: percentiles, rank and score. */
  compared: boolean;
  p: number | null;
  impact: Record<string, number | null>;
  impact_percentiles: Record<string, number | null>;
  specialization_rate: number | null;
  specialization_percentile: number | null;
  quality: InstitutionQuality | null;
  composite_score: number | null;
  rank: number | null;
  breakdown: ScoreAxis[];
}

export interface GroupBenchmark {
  domain: string | null;
  period_start: number | null;
  period_end: number | null;
  min_publications: number;
  group_size: number;
  institutions_with_data: number;
  institutions_compared: number;
  specialization_applicable: boolean;
  axis_weights: Record<string, number>;
  sub_weights: Record<string, Record<string, number>>;
  category_weights: QualityCategoryWeights;
  quality_active_categories: string[];
  rows: GroupBenchmarkRow[];
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
  /** Counted for every group institution and reported as an impact indicator. */
  benchmark_impact: boolean;
}

export interface GridCalibration {
  has_overrides: boolean;
  updated_at: string | null;
  running: boolean;
  default_grid_file: string;
  criteria: GridCriterion[];
}

export interface QualityCategoryWeightsResponse {
  weights: QualityCategoryWeights;
  is_default: boolean;
  /** Categories without any valid criterion outside the impact ones: effective weight 0. */
  inactive: string[];
}

export interface LlmStatus {
  enabled: boolean;
  reachable: boolean;
  model: string | null;
  models: string[];
  model_available?: boolean;
  error?: string;
}
