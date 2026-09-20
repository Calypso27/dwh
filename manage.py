#!/usr/bin/env python3
"""
Point d'entrée unique du projet — toutes les opérations passent par ici.

    python manage.py generate-schema
    python manage.py init [--reset]
    python manage.py seed
    python manage.py load --file data/raw/sentiment140.csv --table raw_sentiment140
    python manage.py check --table raw_sentiment140
    python manage.py status
    python manage.py setup            (raccourci : generate-schema + init + seed)
"""
import argparse
import sys

# La console Windows utilise cp1252 par défaut, qui ne sait pas encoder les
# symboles ✓ / ⚠ / ✗ employés dans tous les messages du projet : sans cette
# ligne, la CLI plante sur un UnicodeEncodeError au premier print, avant même
# d'avoir affiché le moindre résultat (constaté sur un poste Windows vierge).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

from dw import schema_generator, warehouse, seed, loader, quality, transform, fetch_samples, combine_datasets, audit, analytics, ml, recommendations, labeling, behavior, behavior_report, inspect as dw_inspect, pipeline as dw_pipeline, migrate as dw_migrate


def main():
    parser = argparse.ArgumentParser(prog="manage.py", description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate-schema", help="Régénère le SQL depuis config/schema.yaml")

    p_init = sub.add_parser("init", help="Crée/ouvre la base et exécute le SQL")
    p_init.add_argument("--reset", action="store_true", help="Repart de zéro (supprime la base existante)")

    sub.add_parser("seed", help="Peuple les dimensions de référence")

    p_load = sub.add_parser("load", help="Charge un fichier CSV/Excel dans une table de staging")
    p_load.add_argument("--file", required=True)
    p_load.add_argument("--table", required=True)
    p_load.add_argument("--column-names", default=None,
                         help="Noms de colonnes séparés par des virgules, pour un fichier SANS en-tête "
                              "(ex: polarity,tweet_id,tweet_date,flag,user_handle,text)")
    p_load.add_argument("--rename-columns", default=None,
                         help="Renommer des colonnes existantes, format ancien:nouveau séparés par des virgules "
                              "(ex: label:sentiment)")
    p_load.add_argument("--generate-id", default=None,
                         help="Colonnes d'identifiant à générer si absentes du fichier (hash stable du contenu), "
                              "séparées par des virgules (ex: tweet_id)")
    p_load.add_argument("--force", action="store_true",
                         help="Recharger même si ce fichier a déjà été ingéré dans cette table")

    p_load_all = sub.add_parser(
        "load-all",
        help="Charge TOUTES les sources déclarées dans config/load_profiles.yaml en une seule commande "
             "(celles dont le fichier est présent dans data/raw/ ; les autres sont juste signalées)"
    )
    p_load_all.add_argument("--force", action="store_true",
                             help="Recharger même les fichiers déjà ingérés (voir 'load --force')")
    p_load_all.add_argument("--pipeline", action="store_true",
                             help="Enchaîne automatiquement 'pipeline' juste après (transform + check sur tout)")

    sub.add_parser(
        "combine-social",
        help="Joint dataset_commentaires et dataset_publications avant load-all",
    )
    sub.add_parser("audit-data", help="Audite les datasets presents dans data/raw")
    sub.add_parser("build-analytics", help="Construit les tables analytiques du corpus principal")

    sub.add_parser("label-posts",
                    help="Étiquette thématiquement les publications selon config/taxonomy.yaml")
    p_behavior = sub.add_parser(
        "build-behavior",
        help="Construit la couche comportementale (commentaires en contexte, profils d'auteurs, "
             "réaction par thème) — ré-étiquette les publications au passage"
    )
    p_behavior.add_argument("--skip-labeling", action="store_true",
                             help="Ne pas ré-étiqueter les publications (réutilise dim_post_theme tel quel)")
    sub.add_parser("report-behavior",
                    help="Génère docs/behavioral_analysis_report.md depuis la couche comportementale")
    sub.add_parser("benchmark-ml", help="Benchmark engagement et viralite")
    sub.add_parser("benchmark-sentiment", help="Benchmark sentiment TF-IDF")
    p_predict = sub.add_parser("predict-sentiment", help="Applique le modele sentiment sauvegarde")
    sub.add_parser("build-recommendations", help="Construit recommandations et alertes explicables")
    p_predict.add_argument("--max-rows", type=int, default=100000)
    p_predict.add_argument("--batch-size", type=int, default=5000,
                           help="Nombre de textes traités et validés par lot")
    p_predict.add_argument("--no-resume", action="store_true",
                           help="Recalcule toutes les prédictions du modèle (efface les précédentes)")
    p_predict.add_argument("--input", help="Corpus structuré CSV/JSON/JSONL/Parquet à prédire")
    p_predict.add_argument("--output", help="Fichier de sortie du corpus structuré")
    p_predict.add_argument("--text-column", default="text",
                           help="Colonne texte du corpus structuré")

    p_check = sub.add_parser("check", help="Lance les contrôles qualité sur une table")
    p_check.add_argument("--table", required=True)

    p_transform = sub.add_parser("transform", help="Transforme staging -> fact_social_post (SCD2)")
    p_transform.add_argument("--source", help="Une seule table staging (sinon : toutes)")

    p_fetch = sub.add_parser("fetch-sample",
                              help="Streame un échantillon depuis Hugging Face sans tout télécharger")
    p_fetch.add_argument("--source", required=True, choices=list(fetch_samples.SAMPLE_CONFIGS))
    p_fetch.add_argument("--n", type=int, default=20000, help="Nombre de lignes à échantillonner")

    sub.add_parser("status", help="Affiche le nombre de lignes par table")

    p_inspect = sub.add_parser("inspect", help="Diagnostique une table (colonnes vides, valeurs suspectes)")
    p_inspect.add_argument("--table", required=True)

    p_truncate = sub.add_parser(
        "truncate",
        help="Vide UNE SEULE table sans toucher au reste (à préférer à 'init --reset' pour corriger une source)"
    )
    p_truncate.add_argument("--table", required=True)
    p_truncate.add_argument("--confirm", action="store_true", help="Confirme la suppression (obligatoire)")

    p_pipeline = sub.add_parser(
        "pipeline",
        help="Enchaîne transform + check sur toutes les tables staging déjà chargées (raccourci)"
    )
    p_pipeline.add_argument("--trigger", default="manual", choices=["manual", "scheduled", "api"],
                             help="Origine de l'exécution, tracée dans pipeline_runs")

    p_history = sub.add_parser("history", help="Affiche l'historique des exécutions du pipeline")
    p_history.add_argument("--limit", type=int, default=10)

    p_migrate = sub.add_parser(
        "migrate",
        help="Ajoute les tables/colonnes manquantes depuis schema.yaml, SANS perte de données (préférer à init --reset)"
    )
    p_migrate.add_argument("--dry-run", action="store_true", help="Affiche ce qui serait fait, sans l'appliquer")

    sub.add_parser("setup", help="Raccourci : generate-schema + init + seed en une commande")

    p_test = sub.add_parser("test", help="Lance la suite de tests automatisés (raccourci pour pytest tests/ -v)")
    p_test.add_argument("-k", default=None, help="Ne lancer que les tests dont le nom contient ce filtre")

    args = parser.parse_args()

    if args.command == "generate-schema":
        schema_generator.run()
    elif args.command == "init":
        warehouse.init(reset=args.reset)
    elif args.command == "seed":
        seed.run()
    elif args.command == "load":
        col_names = args.column_names.split(",") if args.column_names else None
        rename_map = None
        if args.rename_columns:
            rename_map = dict(pair.split(":") for pair in args.rename_columns.split(","))
        gen_ids = args.generate_id.split(",") if args.generate_id else None
        loader.load(args.file, args.table, column_names=col_names,
                    rename_columns=rename_map, generate_id=gen_ids, force=args.force)
    elif args.command == "load-all":
        loader.load_all(force=args.force)
        if args.pipeline:
            print("\n== Enchaînement automatique : pipeline ==")
            dw_pipeline.run(trigger="manual")
    elif args.command == "combine-social":
        combine_datasets.combine()
    elif args.command == "audit-data":
        audit.run()
    elif args.command == "build-analytics":
        analytics.build_principal_posts()
        analytics.build_descriptive_kpis()
    elif args.command == "label-posts":
        labeling.build_post_themes()
    elif args.command == "build-behavior":
        # L'étiquetage conditionne toute l'analyse par thème : on le rejoue
        # systématiquement, sauf demande explicite du contraire. Oublier de le
        # relancer après avoir modifié taxonomy.yaml produirait une analyse
        # muette, calculée sur les anciennes étiquettes.
        if not args.skip_labeling:
            labeling.build_post_themes(warn_cascade=False)
        behavior.build_all()
    elif args.command == "report-behavior":
        behavior_report.generate()
    elif args.command == "benchmark-ml":
        ml.benchmark()
    elif args.command == "benchmark-sentiment":
        ml.benchmark_sentiment()
    elif args.command == "predict-sentiment":
        if args.input:
            if not args.output:
                parser.error("--output est obligatoire avec --input")
            ml.predict_structured_corpus(
                args.input, args.output, text_column=args.text_column,
                batch_size=args.batch_size,
            )
        else:
            ml.predict_sentiment_corpus(
                max_rows=args.max_rows,
                batch_size=args.batch_size,
                resume=not args.no_resume,
            )
    elif args.command == "build-recommendations":
        recommendations.build()
    elif args.command == "check":
        quality.run(args.table)
    elif args.command == "transform":
        transform.run(args.source)
    elif args.command == "fetch-sample":
        fetch_samples.run(args.source, n=args.n)
    elif args.command == "status":
        warehouse.status()
    elif args.command == "inspect":
        dw_inspect.run(args.table)
    elif args.command == "truncate":
        warehouse.truncate(args.table, confirm=args.confirm)
    elif args.command == "pipeline":
        dw_pipeline.run(trigger=args.trigger)
    elif args.command == "history":
        dw_pipeline.history(limit=args.limit)
    elif args.command == "migrate":
        dw_migrate.run(dry_run=args.dry_run)
    elif args.command == "setup":
        print("== 1/3 generate-schema ==")
        schema_generator.run()
        print("\n== 2/3 init ==")
        warehouse.init(reset=False)
        print("\n== 3/3 seed ==")
        seed.run()
        print("\n✓ Projet prêt. Dépose tes fichiers dans data/raw/ puis utilise : python manage.py load ...")
    elif args.command == "test":
        import pytest as _pytest
        pytest_args = ["tests/", "-v"]
        if args.k:
            pytest_args += ["-k", args.k]
        sys.exit(_pytest.main(pytest_args))


if __name__ == "__main__":
    sys.exit(main())
