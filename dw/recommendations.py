"""Regles explicables de recommandation et d'alerte."""
import json

from dw.warehouse import get_connection


def build() -> dict[str, int]:
    con = get_connection()
    con.execute("DELETE FROM recommendation")
    con.execute("DELETE FROM alert")

    platform_rows = con.execute("""
        SELECT platform_name, post_count, median_engagement,
               average_engagement_rate, viral_post_count, average_toxicity
        FROM agg_platform_kpis
        ORDER BY platform_name
    """).fetchall()
    if not platform_rows:
        con.close()
        print("Recommandations : 0, alertes : 0 (aucun KPI disponible)")
        return {"recommendations": 0, "alerts": 0}

    recommendations = []
    alerts = []
    for row in platform_rows:
        platform, count, median, rate, viral_count, toxicity = row
        recommendations.append((
            platform,
            "format_engagement",
            f"Prioriser les contenus performants sur {platform}.",
            json.dumps({
                "post_count": count,
                "median_engagement": median,
                "average_engagement_rate": rate,
            }),
            float(rate),
        ))
        if toxicity >= 50:
            alerts.append((
                platform,
                "high_toxicity",
                f"Surveiller la toxicite moyenne sur {platform}.",
                "HIGH",
                json.dumps({"average_toxicity": toxicity}),
            ))

    next_recommendation = con.execute(
        "SELECT COALESCE(MAX(recommendation_id), 0) + 1 FROM recommendation"
    ).fetchone()[0]
    if recommendations:
        con.executemany("""
            INSERT INTO recommendation
                (recommendation_id, platform_name, recommendation_type,
                 recommendation_text, evidence, score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (next_recommendation + index, *recommendation)
            for index, recommendation in enumerate(recommendations)
        ])

    next_alert = con.execute(
        "SELECT COALESCE(MAX(alert_id), 0) + 1 FROM alert"
    ).fetchone()[0]
    if alerts:
        con.executemany("""
            INSERT INTO alert
                (alert_id, platform_name, alert_type, alert_text, severity, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (next_alert + index, *alert)
            for index, alert in enumerate(alerts)
        ])
    con.close()
    print(f"Recommandations : {len(recommendations)}, alertes : {len(alerts)}")
    return {"recommendations": len(recommendations), "alerts": len(alerts)}
