"""Expose la couche comportementale : réactions replacées dans le contexte
de la publication qui les a provoquées.

Toutes les lectures excluent les délais négatifs (commentaire antérieur à sa
publication = date corrompue à la source, jamais un comportement réel).
"""
from typing import List

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas import (
    AuthorSegment,
    BehaviorOverview,
    HourlyActivity,
    PageComparison,
    ThemeReaction,
)

router = APIRouter(prefix="/behavior", tags=["behavior"])

# Ordre d'affichage des segments : croissant en intensité d'usage. Un tri
# alphabétique ("engage, hyperactif, occasionnel, ponctuel, regulier") casserait
# la lecture du gradient, qui est tout l'intérêt de la segmentation.
SEGMENT_ORDER = ["ponctuel", "occasionnel", "regulier", "engage", "hyperactif"]

_EMPTY = ("La couche comportementale est vide — lance : python manage.py build-behavior")


def _rows_to_dicts(db) -> list[dict]:
    return [dict(zip([d[0] for d in db.description], row)) for row in db.fetchall()]


@router.get("/overview", response_model=BehaviorOverview)
def overview(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    row = db.execute("""
        SELECT COUNT(*) AS comment_count,
               COUNT(DISTINCT external_post_id) AS post_count,
               COUNT(DISTINCT author_pseudo) AS author_count,
               COUNT(DISTINCT theme) AS theme_count,
               MEDIAN(reaction_delay_hours) AS median_delay_hours,
               100.0 * COUNT(*) FILTER (WHERE reaction_delay_hours < 1) / COUNT(*) AS pct_within_1h,
               100.0 * COUNT(*) FILTER (WHERE reaction_delay_hours < 6) / COUNT(*) AS pct_within_6h,
               QUANTILE_CONT(reaction_delay_hours, 0.9) AS p90_delay_hours,
               MIN(commented_at) AS period_start,
               MAX(commented_at) AS period_end
        FROM fact_comment_context
        WHERE reaction_delay_hours >= 0
    """).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail=_EMPTY)
    return dict(zip([d[0] for d in db.description], row))


@router.get("/segments", response_model=List[AuthorSegment])
def segments(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    db.execute("""
        WITH totaux AS (
            SELECT COUNT(*) AS auteurs, SUM(comment_count) AS commentaires
            FROM agg_author_behavior
        )
        SELECT a.segment,
               COUNT(*) AS author_count,
               100.0 * COUNT(*) / ANY_VALUE(t.auteurs) AS author_share,
               SUM(a.comment_count) AS comment_count,
               100.0 * SUM(a.comment_count) / ANY_VALUE(t.commentaires) AS comment_share,
               MEDIAN(a.median_delay_hours) AS median_delay_hours,
               AVG(a.avg_comment_length) AS avg_comment_length,
               AVG(a.distinct_themes) AS avg_distinct_themes
        FROM agg_author_behavior a CROSS JOIN totaux t
        GROUP BY a.segment
    """)
    rows = _rows_to_dicts(db)
    if not rows:
        raise HTTPException(status_code=404, detail=_EMPTY)
    rank = {segment: i for i, segment in enumerate(SEGMENT_ORDER)}
    return sorted(rows, key=lambda r: rank.get(r["segment"], 99))


@router.get("/themes", response_model=List[ThemeReaction])
def themes(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    # Tri par délai de réaction, PAS par commentaires/post : ce dernier est
    # plafonné par la collecte (100 commentaires max par publication) et ne
    # mesure donc pas l'intérêt suscité par un sujet.
    db.execute("""
        SELECT theme,
               SUM(post_count) AS post_count,
               SUM(comment_count) AS comment_count,
               SUM(comment_count) * 1.0 / SUM(post_count) AS comments_per_post,
               SUM(distinct_authors) AS distinct_authors,
               MEDIAN(median_delay_hours) AS median_delay_hours,
               AVG(avg_comment_length) AS avg_comment_length
        FROM agg_theme_reaction
        GROUP BY theme
        ORDER BY MEDIAN(median_delay_hours) ASC
    """)
    rows = _rows_to_dicts(db)
    if not rows:
        raise HTTPException(status_code=404, detail=_EMPTY)
    return rows


@router.get("/pages", response_model=List[PageComparison])
def pages(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    db.execute("""
        SELECT page_name,
               COUNT(DISTINCT external_post_id) AS post_count,
               COUNT(*) AS comment_count,
               COUNT(DISTINCT author_pseudo) AS author_count,
               MEDIAN(reaction_delay_hours) AS median_delay_hours,
               AVG(comment_length) AS avg_comment_length
        FROM fact_comment_context
        WHERE reaction_delay_hours >= 0
        GROUP BY page_name
        ORDER BY page_name
    """)
    rows = _rows_to_dicts(db)
    if not rows:
        raise HTTPException(status_code=404, detail=_EMPTY)
    return rows


@router.get("/hourly", response_model=List[HourlyActivity])
def hourly(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Volume de commentaires par heure — les 24 heures sont toujours
    renvoyées, y compris celles à zéro, pour que la courbe ne présente pas
    de trou trompeur là où il n'y a simplement pas eu d'activité."""
    observed = dict(db.execute("""
        SELECT comment_hour, COUNT(*) FROM fact_comment_context
        WHERE reaction_delay_hours >= 0 GROUP BY comment_hour
    """).fetchall())
    if not observed:
        raise HTTPException(status_code=404, detail=_EMPTY)
    return [{"hour": h, "comment_count": observed.get(h, 0)} for h in range(24)]
