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
  description: string;
}

export interface SignatureTopic {
  topic_id: string;
  own_share: number;
  peer_avg_share: number;
  ratio: number;
}

export interface SpecificityIndicators {
  thematic_profile: Array<{
    name: string;
    children: Array<{ name: string; value: number }>;
    total: number;
  }>;
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

export interface CompositeScore {
  weight_profile_id: number;
  peer_group_id: number;
  composite_score: number;
  axis_scores: Record<string, number>;
  axis_weights: Record<string, number>;
  sub_weights: Record<string, Record<string, number>>;
}
