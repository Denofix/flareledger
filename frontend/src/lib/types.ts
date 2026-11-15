export type UnknownRecord = Record<string, unknown>;
export interface Entity extends UnknownRecord {
  id: string;
}
export interface Investigation extends Entity {
  acronym: string;
  title: string;
  title_en: string;
  summary_en: string;
  fuel_phase: string;
  gravity_regime: string;
  gravity_regime_basis: string;
  facility_as_reported: string | null;
  flight_platform_as_reported: string | null;
  doi: string;
  version: number;
  availability: string;
  tags: string[];
  source_ids: string[];
}
export interface Source extends Entity {
  title: string;
  url?: string;
  doi?: string;
  citation?: string;
  publisher?: string;
  license_identifier?: string;
  document_type?: string;
  version?: string | number;
}
export interface Issue extends Entity {
  description_en?: string;
  action?: string;
}
export interface Evidence extends Entity {
  source_id?: string;
  locator?: UnknownRecord;
  independent_human_review?: boolean;
}
export interface Detail<T extends Entity = Entity> {
  item: T;
  sources: Source[];
  evidence: Evidence[];
  quality_issues: Issue[];
}
export interface Page<T extends Entity = Entity> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface Axis {
  name: string;
  label_en: string;
  unit: string | null;
  zero_event?: string;
}
export type Point = [number | null, number | null];
export interface Series extends Entity {
  investigation_id: string;
  original_trial_label: string;
  x: Axis;
  y: Axis;
  point_count: number;
  points?: Point[];
  uncertainty: unknown;
  source_ids: string[];
  quality_note_en?: string;
  synthetic: boolean;
  measurement_origin: string;
}
export interface ResearchRecord extends Entity {
  investigation_id: string;
  record_type: string;
  original_test_id?: string | null;
  material?: string | null;
  fuel_phase?: string | null;
  gravity_regime?: string | null;
  oxygen_percent?: number | null;
  pressure_kpa?: number | null;
  airflow_cm_s?: number | null;
}
export interface Meta {
  corpus_version: string;
  seed_sha256: string;
  language: string;
  live_generation_available: boolean;
  statistics: {
    investigations: number;
    normalized_table_records_including_non_trials: number;
    record_types: Record<string, number>;
    numerical_time_series: number;
    time_series_points: number;
    source_records: number;
  };
}
export interface SearchItem {
  kind: string;
  id: string;
  investigation_id: string | null;
  title: string;
  excerpt: string;
  source_ids: string[];
  evidence_ids: string[];
  sources: Source[];
}
export interface SearchResult {
  query: string;
  method: string;
  items: SearchItem[];
}
export interface AskResult {
  status?:
    "generated" | "insufficient_evidence" | "rate_limited" | "unavailable";
  error?: { code: string; message: string };
  answer: string | null;
  retrieved_evidence: SearchItem[];
  retrieval_method: string;
  live_generation_available: boolean;
  model?: string;
  provider?: string;
  corpus_version?: string;
  notice?: string;
  limitations?: string[];
  retry_after_seconds?: number;
  citations?: { context_id: string; source_id: string; quote: string }[];
}
export interface Comparison {
  series: Detail<Series>[];
  transformations: unknown[];
  limitations: string[];
}
