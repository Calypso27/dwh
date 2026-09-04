export interface SocialPost {
  post_id: number;
  source_id: number;
  platform_id: number;
  external_post_id: string | null;
  text_content: string | null;
  published_at: string | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  views: number | null;
}

export interface ModelRun {
  run_id: number;
  model_name: string;
  source_name: string;
  task_type: string | null;
  train_rows: number | null;
  test_rows: number | null;
  run_at: string | null;
}

export interface ModelMetric {
  metric_id: number;
  run_id: number;
  metric_name: string;
  metric_value: number;
  class_label: string | null;
}

export interface DQCheck {
  check_id: number;
  table_name: string;
  check_name: string;
  check_result: 'PASS' | 'WARN' | 'FAIL';
  rows_checked: number | null;
  rows_failed: number | null;
  checked_at: string | null;
}

export interface SentimentPrediction {
  prediction_id: number;
  post_id: number;
  model_id: number;
  sentiment_label: string;
  positive_probability: number;
  negative_probability: number;
  neutral_probability: number;
  confidence: number;
}

export interface SentimentSummary {
  sentiment_label: string;
  count: number;
}

export interface SourceDataset {
  source_id: number;
  source_name: string;
  provenance: string | null;
  language: string | null;
}

export interface Platform {
  platform_id: number;
  platform_name: string;
  content_type: string | null;
}

export interface CurrentUser {
  username: string;
  role: string;
  scope_source_id: number | null;
}
