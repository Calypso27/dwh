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

export interface PlatformKpi {
  platform_name: string;
  post_count: number;
  median_engagement: number;
  average_engagement: number;
  average_engagement_rate: number;
  viral_post_count: number;
  average_toxicity: number;
}

export interface Recommendation {
  recommendation_id: number;
  platform_name: string;
  recommendation_type: string;
  recommendation_text: string;
  evidence: string;
  score: number;
  generated_at: string;
}

export interface Alert {
  alert_id: number;
  platform_name: string;
  alert_type: string;
  alert_text: string;
  severity: string;
  evidence: string;
  generated_at: string;
}

export interface CurrentUser {
  username: string;
  role: string;
  scope_source_id: number | null;
}

// ---------------------------------------------------------------------------
// Couche comportementale
// ---------------------------------------------------------------------------

export interface BehaviorOverview {
  comment_count: number;
  post_count: number;
  author_count: number;
  theme_count: number;
  median_delay_hours: number;
  pct_within_1h: number;
  pct_within_6h: number;
  p90_delay_hours: number;
  period_start: string | null;
  period_end: string | null;
}

export interface AuthorSegment {
  segment: string;
  author_count: number;
  author_share: number;
  comment_count: number;
  comment_share: number;
  median_delay_hours: number | null;
  avg_comment_length: number | null;
  avg_distinct_themes: number | null;
}

export interface ThemeReaction {
  theme: string;
  post_count: number;
  comment_count: number;
  comments_per_post: number;
  distinct_authors: number;
  median_delay_hours: number | null;
  avg_comment_length: number | null;
}

export interface PageComparison {
  page_name: string;
  post_count: number;
  comment_count: number;
  author_count: number;
  median_delay_hours: number | null;
  avg_comment_length: number | null;
}

export interface HourlyActivity {
  hour: number;
  comment_count: number;
}
