"""Construction des tables analytiques a partir du staging."""
from pathlib import Path

from dw.warehouse import get_connection
from dw.paths import DOC_DIR


def build_principal_posts() -> int:
    """Construit le fait analytique du corpus principal, de facon idempotente."""
    con = get_connection()
    con.execute("DELETE FROM fact_post_analytics WHERE source_id = 8")
    con.execute("""
        INSERT INTO fact_post_analytics (
            analytics_id, source_id, external_post_id, platform_name, published_at,
            followers, topic, language, media_type, num_hashtags,
            sentiment_category, sentiment_positive, sentiment_negative,
            sentiment_neutral, likes, shares, comments, views, total_engagement,
            engagement_rate_per_1k_followers, viral_coefficient,
            cross_platform_spread, toxicity_score
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY post_id),
            8, post_id, platform, timestamp,
            followers, topic, language, media_type, num_hashtags,
            sentiment_category, sentiment_positive, sentiment_negative,
            sentiment_neutral, likes, shares, comments, views, total_engagement,
            engagement_rate_per_1k_followers, viral_coefficient,
            cross_platform_spread, toxicity_score
        FROM raw_multi_platform_posts
    """)
    count = con.execute(
        "SELECT COUNT(*) FROM fact_post_analytics WHERE source_id = 8"
    ).fetchone()[0]
    con.close()
    print(f"Fait analytique construit : {count:,} publications")
    return count


def build_descriptive_kpis() -> dict[str, int]:
    """Construit les agrégats descriptifs du corpus principal."""
    con = get_connection()
    con.execute("DELETE FROM agg_platform_kpis")
    con.execute("""
        INSERT INTO agg_platform_kpis (
            platform_name, post_count, median_engagement, average_engagement,
            average_engagement_rate, viral_post_count, average_toxicity
        )
        SELECT
            platform_name,
            COUNT(*) AS post_count,
            MEDIAN(total_engagement) AS median_engagement,
            AVG(total_engagement) AS average_engagement,
            AVG(engagement_rate_per_1k_followers) AS average_engagement_rate,
            COUNT(*) FILTER (WHERE viral_coefficient >= 1) AS viral_post_count,
            AVG(toxicity_score) AS average_toxicity
        FROM fact_post_analytics
        WHERE source_id = 8
        GROUP BY platform_name
    """)
    con.execute("DELETE FROM agg_daily_kpis")
    con.execute("""
        INSERT INTO agg_daily_kpis (
            activity_date, post_count, total_engagement,
            average_viral_coefficient, average_toxicity
        )
        SELECT
            CAST(published_at AS DATE) AS activity_date,
            COUNT(*) AS post_count,
            SUM(total_engagement) AS total_engagement,
            AVG(viral_coefficient) AS average_viral_coefficient,
            AVG(toxicity_score) AS average_toxicity
        FROM fact_post_analytics
        WHERE source_id = 8
        GROUP BY CAST(published_at AS DATE)
    """)
    con.execute("DELETE FROM agg_segment_kpis")
    con.execute("""
        INSERT INTO agg_segment_kpis (
            segment_id, dimension_name, dimension_value, post_count,
            median_engagement, average_engagement, average_engagement_rate,
            viral_post_count, average_toxicity
        )
        WITH segments AS (
            SELECT 'topic' AS dimension_name, COALESCE(topic, 'unknown') AS dimension_value,
                   total_engagement, engagement_rate_per_1k_followers,
                   viral_coefficient, toxicity_score
            FROM fact_post_analytics WHERE source_id = 8
            UNION ALL
            SELECT 'media_type', COALESCE(media_type, 'unknown'),
                   total_engagement, engagement_rate_per_1k_followers,
                   viral_coefficient, toxicity_score
            FROM fact_post_analytics WHERE source_id = 8
            UNION ALL
            SELECT 'language', COALESCE(language, 'unknown'),
                   total_engagement, engagement_rate_per_1k_followers,
                   viral_coefficient, toxicity_score
            FROM fact_post_analytics WHERE source_id = 8
            UNION ALL
            SELECT 'sentiment', COALESCE(sentiment_category, 'unknown'),
                   total_engagement, engagement_rate_per_1k_followers,
                   viral_coefficient, toxicity_score
            FROM fact_post_analytics WHERE source_id = 8
            UNION ALL
            SELECT 'hashtag_bucket',
                   CASE
                       WHEN num_hashtags = 0 THEN '0'
                       WHEN num_hashtags BETWEEN 1 AND 2 THEN '1-2'
                       WHEN num_hashtags BETWEEN 3 AND 5 THEN '3-5'
                       ELSE '6+'
                   END,
                   total_engagement, engagement_rate_per_1k_followers,
                   viral_coefficient, toxicity_score
            FROM raw_multi_platform_posts
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY dimension_name, dimension_value),
            dimension_name, dimension_value, COUNT(*),
            MEDIAN(total_engagement), AVG(total_engagement),
            AVG(engagement_rate_per_1k_followers),
            COUNT(*) FILTER (WHERE viral_coefficient >= 1),
            AVG(toxicity_score)
        FROM segments
        GROUP BY dimension_name, dimension_value
    """)
    platform_count = con.execute("SELECT COUNT(*) FROM agg_platform_kpis").fetchone()[0]
    daily_count = con.execute("SELECT COUNT(*) FROM agg_daily_kpis").fetchone()[0]
    segment_count = con.execute("SELECT COUNT(*) FROM agg_segment_kpis").fetchone()[0]
    report_rows = con.execute("""
        SELECT dimension_name, dimension_value, post_count,
               median_engagement, average_engagement_rate, average_toxicity
        FROM agg_segment_kpis
        ORDER BY dimension_name, post_count DESC
    """).fetchall()
    con.close()
    _write_descriptive_report(report_rows, platform_count, daily_count)
    print(f"KPI construits : {platform_count} plateformes, {daily_count} jours, {segment_count} segments")
    return {"platforms": platform_count, "days": daily_count, "segments": segment_count}


def _write_descriptive_report(rows, platform_count: int, daily_count: int) -> Path:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    output = DOC_DIR / "descriptive_analysis_report.md"
    lines = [
        "# Rapport d'analyse descriptive",
        "",
        "Rapport genere depuis `fact_post_analytics` et les tables KPI.",
        "",
        f"- Plateformes : {platform_count}",
        f"- Jours couverts : {daily_count}",
        "",
        "| Dimension | Valeur | Publications | Engagement median | Taux moyen / 1k | Toxicite moyenne |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for dimension, value, count, median, rate, toxicity in rows:
        lines.append(
            f"| {dimension} | {value} | {count:,} | "
            f"{median:.2f} | {rate:.2f} | {toxicity:.2f} |"
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
