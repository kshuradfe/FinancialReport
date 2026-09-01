export interface Market {
  region: string;
  name_en: string;
  name_zh: string;
  flag: string;
  group: string;
  currency: string;
  suffixes: string[];
  exchanges: string[];
  available: boolean;
}

export interface FieldGroup {
  key: string;
  label_zh: string;
  label_en: string;
}

export interface FieldDef {
  key: string;
  label_zh: string;
  label_en: string;
  group: string;
  source: string;
  fmt: 'text' | 'money' | 'number' | 'percent' | 'ratio';
  default: boolean;
  mandatory: boolean;
}

export interface Meta {
  markets: Market[];
  group_order: string[];
  fields: { groups: FieldGroup[]; fields: FieldDef[]; mandatory: string[] };
  sectors: string[];
  sort_options: { key: string; label_zh: string; label_en: string }[];
  period_modes: { key: string; label_zh: string; label_en: string }[];
  max_universe: number;
}

export interface UniverseItem {
  symbol: string;
  name: string;
  exchange: string;
  region: string;
  quote_currency: string | null;
  market_cap: number | null;
  trailing_pe: number | null;
  price: number | null;
}

export interface SearchItem {
  symbol: string;
  name: string;
  exchange: string;
  region: string | null;
  market: string;
}

export interface JobConfig {
  source: 'screener' | 'custom';
  regions: string[];
  limit_per_market: number;
  offset: number;
  min_market_cap: number | null;
  max_market_cap: number | null;
  sectors: string[] | null;
  domestic_only: boolean;
  local_currency_only: boolean;
  sort_by: string;
  sort_asc: boolean;
  custom_symbols: string;
  fields: string[];
  period_mode: 'auto' | 'quarterly' | 'annual';
  periods: number;
  date_from: string | null;
  date_to: string | null;
  concurrency: number;
  request_delay: number;
}

export type JobStatus =
  | 'queued'
  | 'discovering'
  | 'running'
  | 'done'
  | 'cancelled'
  | 'error';

export interface JobSummary {
  id: string;
  status: JobStatus;
  created_at: string;
  finished_at: string | null;
  total: number;
  completed: number;
  succeeded: number;
  failed: number;
  row_count: number;
  message: string;
  config: Partial<JobConfig>;
}

export interface LogEntry {
  t: string;
  level: 'info' | 'ok' | 'warn' | 'error';
  text: string;
}

export interface Progress {
  status: JobStatus;
  total: number;
  completed: number;
  succeeded: number;
  failed: number;
  rows: number;
  message: string;
}

export type Row = Record<string, string | number | null>;

export interface RowsPage {
  columns: string[];
  rows: Row[];
  total: number;
  offset: number;
}
