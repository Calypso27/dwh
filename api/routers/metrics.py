from typing import List

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas import ModelRun, ModelMetric, DQCheck, SentimentPrediction, SourceDataset, Platform

router = APIRouter(tags=["metrics"])


@router.get("/sources", response_model=List[SourceDataset])
def list_sources(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute(
        "SELECT source_id, source_name, provenance, language FROM dim_source_dataset ORDER BY source_id"
    ).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/platforms", response_model=List[Platform])
def list_platforms(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute(
        "SELECT platform_id, platform_name, content_type FROM dim_platform ORDER BY platform_id"
    ).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/posts/{post_id}/sentiment", response_model=List[SentimentPrediction])
def get_post_sentiment(post_id: int, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute(
        "SELECT prediction_id, post_id, model_id, sentiment_label, positive_probability, "
        "negative_probability, neutral_probability, confidence "
        "FROM fact_sentiment_prediction WHERE post_id = ?",
        [post_id],
    ).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/sentiment-summary")
def sentiment_summary(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Répartition globale des sentiments — utilisé pour le graphique du dashboard."""
    rows = db.execute("""
        SELECT sentiment_label, COUNT(*) as count
        FROM fact_sentiment_prediction
        GROUP BY sentiment_label
        ORDER BY sentiment_label
    """).fetchall()
    return [{"sentiment_label": r[0], "count": r[1]} for r in rows]


@router.get("/kpis/platform")
def platform_kpis(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute("""
        SELECT platform_name, post_count, median_engagement,
               average_engagement, average_engagement_rate,
               viral_post_count, average_toxicity
        FROM agg_platform_kpis
        ORDER BY average_engagement DESC
    """).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/kpis/daily")
def daily_kpis(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute("""
        SELECT activity_date, post_count, total_engagement,
               average_viral_coefficient, average_toxicity
        FROM agg_daily_kpis
        ORDER BY activity_date
    """).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/model-runs", response_model=List[ModelRun])
def list_model_runs(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute("""
        SELECT r.run_id, m.model_name, s.source_name, r.task_type, r.train_rows, r.test_rows, r.run_at
        FROM model_run r
        JOIN dim_model m ON r.model_id = m.model_id
        JOIN dim_source_dataset s ON r.source_id = s.source_id
        ORDER BY r.run_id
    """).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/model-runs/{run_id}/metrics", response_model=List[ModelMetric])
def get_run_metrics(run_id: int, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    exists = db.execute("SELECT 1 FROM model_run WHERE run_id = ?", [run_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Run introuvable")
    rows = db.execute(
        "SELECT metric_id, run_id, metric_name, metric_value, class_label FROM model_metric WHERE run_id = ?",
        [run_id],
    ).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/dq-checks", response_model=List[DQCheck])
def list_dq_checks(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute(
        "SELECT check_id, table_name, check_name, check_result, rows_checked, rows_failed, checked_at "
        "FROM dq_checks ORDER BY check_id DESC"
    ).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/recommendations")
def list_recommendations(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute("""
        SELECT recommendation_id, platform_name, recommendation_type,
               recommendation_text, evidence, score, generated_at
        FROM recommendation
        ORDER BY score DESC, recommendation_id
    """).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/alerts")
def list_alerts(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    rows = db.execute("""
        SELECT alert_id, platform_name, alert_type, alert_text,
               severity, evidence, generated_at
        FROM alert
        ORDER BY generated_at DESC, alert_id
    """).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]
