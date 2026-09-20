"""
Orchestration du pipeline complet (transform + check sur toutes les
sources), avec journalisation systématique dans pipeline_runs.

Conçu pour tourner SANS SUPERVISION humaine (tâche planifiée / cron) :
- chaque exécution est enregistrée AVANT de démarrer (status=RUNNING),
  puis mise à jour à la fin (SUCCESS ou FAILED) — même en cas de crash,
  on garde une trace qu'une exécution a été tentée ;
- toute exception est capturée, journalisée (log fichier + base), puis
  ré-émise après coup, pour que le code de sortie du process reste non-nul
  (indispensable pour que le Planificateur de tâches Windows / cron sache
  que l'exécution a échoué et alerte, plutôt que de croire que tout va bien).

Usage :
    python manage.py pipeline --trigger scheduled
"""
from datetime import datetime, timezone
from dw.warehouse import get_connection
from dw import transform, quality, analytics, recommendations
from dw.logging_config import get_logger

logger = get_logger()


def run(trigger: str = "manual"):
    con = get_connection()
    run_id = con.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM pipeline_runs").fetchone()[0]
    started_at = datetime.now(timezone.utc)

    con.execute(
        "INSERT INTO pipeline_runs (run_id, trigger_type, started_at, status) VALUES (?, ?, ?, 'RUNNING')",
        [run_id, trigger, started_at]
    )
    con.close()

    logger.info(f"=== Démarrage pipeline run #{run_id} (trigger={trigger}) ===")

    total_new = 0
    total_updated = 0
    sources_processed = 0

    try:
        mapping = transform.load_mapping()
        con = get_connection()
        try:
            for table_name, cfg in mapping.items():
                result = transform.transform_source(table_name, cfg, con=con)
                logger.info(
                    f"{table_name}: staging_brut={result['staging_rows_raw']} "
                    f"nouveaux={result['new']} màj_scd2={result['updated']} inchangés={result['unchanged']}"
                )
                total_new += result["new"]
                total_updated += result["updated"]
                sources_processed += 1
        finally:
            con.close()  # toujours fermer, même si une source a fait planter la boucle

        staging_tables = list(mapping.keys())
        for t in staging_tables:
            quality.run(t)
        analytics.build_principal_posts()
        analytics.build_descriptive_kpis()
        recommendations.build()

        finished_at = datetime.now(timezone.utc)
        con = get_connection()
        con.execute(
            "UPDATE pipeline_runs SET finished_at = ?, status = 'SUCCESS', "
            "sources_processed = ?, total_new_rows = ?, total_updated_rows = ? WHERE run_id = ?",
            [finished_at, sources_processed, total_new, total_updated, run_id]
        )
        con.close()

        duration = (finished_at - started_at).total_seconds()
        logger.info(f"=== Pipeline run #{run_id} terminé avec SUCCÈS en {duration:.1f}s "
                    f"({sources_processed} sources, {total_new} nouveaux, {total_updated} màj SCD2) ===")

    except Exception as e:
        finished_at = datetime.now(timezone.utc)
        error_message = f"{type(e).__name__}: {e}"
        logger.error(f"=== Pipeline run #{run_id} ÉCHOUÉ : {error_message} ===", exc_info=True)

        con = get_connection()
        con.execute(
            "UPDATE pipeline_runs SET finished_at = ?, status = 'FAILED', error_message = ? WHERE run_id = ?",
            [finished_at, error_message, run_id]
        )
        con.close()
        raise  # code de sortie non-nul indispensable pour qu'un scheduler détecte l'échec


def history(limit: int = 10):
    con = get_connection()
    rows = con.execute(
        "SELECT run_id, trigger_type, started_at, finished_at, status, "
        "sources_processed, total_new_rows, total_updated_rows, error_message "
        "FROM pipeline_runs ORDER BY run_id DESC LIMIT ?", [limit]
    ).fetchall()
    con.close()

    if not rows:
        print("Aucune exécution enregistrée pour le moment.")
        return

    print(f"{'Run':<5} {'Trigger':<10} {'Statut':<10} {'Début':<20} {'Durée':<8} {'Nouv.':>6} {'MàJ':>6}")
    print("-" * 80)
    for r in rows:
        run_id, trigger_type, started_at, finished_at, status, n_sources, n_new, n_updated, err = r
        duration = f"{(finished_at - started_at).total_seconds():.0f}s" if finished_at else "—"
        print(f"{run_id:<5} {trigger_type:<10} {status:<10} {str(started_at)[:19]:<20} "
              f"{duration:<8} {n_new or 0:>6} {n_updated or 0:>6}")
        if err:
            print(f"      ↳ erreur : {err}")
