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
from dw import schema_generator, warehouse, seed, loader, quality, transform, fetch_samples


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

    p_check = sub.add_parser("check", help="Lance les contrôles qualité sur une table")
    p_check.add_argument("--table", required=True)

    p_transform = sub.add_parser("transform", help="Transforme staging -> fact_social_post (SCD2)")
    p_transform.add_argument("--source", help="Une seule table staging (sinon : toutes)")

    p_fetch = sub.add_parser("fetch-sample",
                              help="Streame un échantillon depuis Hugging Face sans tout télécharger")
    p_fetch.add_argument("--source", required=True, choices=list(fetch_samples.SAMPLE_CONFIGS))
    p_fetch.add_argument("--n", type=int, default=20000, help="Nombre de lignes à échantillonner")

    sub.add_parser("status", help="Affiche le nombre de lignes par table")

    sub.add_parser("setup", help="Raccourci : generate-schema + init + seed en une commande")

    args = parser.parse_args()

    if args.command == "generate-schema":
        schema_generator.run()
    elif args.command == "init":
        warehouse.init(reset=args.reset)
    elif args.command == "seed":
        seed.run()
    elif args.command == "load":
        loader.load(args.file, args.table)
    elif args.command == "check":
        quality.run(args.table)
    elif args.command == "transform":
        transform.run(args.source)
    elif args.command == "fetch-sample":
        fetch_samples.run(args.source, n=args.n)
    elif args.command == "status":
        warehouse.status()
    elif args.command == "setup":
        print("== 1/3 generate-schema ==")
        schema_generator.run()
        print("\n== 2/3 init ==")
        warehouse.init(reset=False)
        print("\n== 3/3 seed ==")
        seed.run()
        print("\n✓ Projet prêt. Dépose tes fichiers dans data/raw/ puis utilise : python manage.py load ...")


if __name__ == "__main__":
    sys.exit(main())
