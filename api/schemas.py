"""Schémas Pydantic — définissent exactement ce que l'API expose (contrat REST)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SocialPost(BaseModel):
    post_id: int
    source_id: int
    platform_id: int
    external_post_id: Optional[str] = None
    text_content: Optional[str] = None
    published_at: Optional[datetime] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    views: Optional[int] = None


class SentimentPrediction(BaseModel):
    prediction_id: int
    post_id: int
    model_id: int
    sentiment_label: Optional[str] = None
    positive_probability: Optional[float] = None
    negative_probability: Optional[float] = None
    neutral_probability: Optional[float] = None
    confidence: Optional[float] = None


class ModelRun(BaseModel):
    run_id: int
    model_name: str
    source_name: str
    task_type: Optional[str] = None
    train_rows: Optional[int] = None
    test_rows: Optional[int] = None
    run_at: Optional[datetime] = None


class ModelMetric(BaseModel):
    metric_id: int
    run_id: int
    metric_name: str
    metric_value: float
    class_label: Optional[str] = None


class DQCheck(BaseModel):
    check_id: int
    table_name: str
    check_name: str
    check_result: str
    rows_checked: Optional[int] = None
    rows_failed: Optional[int] = None
    checked_at: Optional[datetime] = None


class SourceDataset(BaseModel):
    source_id: int
    source_name: str
    provenance: Optional[str] = None
    language: Optional[str] = None


class Platform(BaseModel):
    platform_id: int
    platform_name: str
    content_type: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    username: str
    role: str
    scope_source_id: Optional[int] = None


# --------------------------------------------------------------------------
# Couche comportementale — analyse des réactions rapportées à leur publication
# --------------------------------------------------------------------------

class BehaviorOverview(BaseModel):
    """Chiffres d'en-tête du tableau de bord comportemental."""
    comment_count: int
    post_count: int
    author_count: int
    theme_count: int
    median_delay_hours: float
    pct_within_1h: float
    pct_within_6h: float
    p90_delay_hours: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class AuthorSegment(BaseModel):
    segment: str
    author_count: int
    author_share: float
    comment_count: int
    comment_share: float
    median_delay_hours: Optional[float] = None
    avg_comment_length: Optional[float] = None
    avg_distinct_themes: Optional[float] = None


class ThemeReaction(BaseModel):
    theme: str
    post_count: int
    comment_count: int
    comments_per_post: float
    distinct_authors: int
    median_delay_hours: Optional[float] = None
    avg_comment_length: Optional[float] = None


class PageComparison(BaseModel):
    page_name: str
    post_count: int
    comment_count: int
    author_count: int
    median_delay_hours: Optional[float] = None
    avg_comment_length: Optional[float] = None


class HourlyActivity(BaseModel):
    hour: int
    comment_count: int
