"""
Migration de schéma — compare config/schema.yaml à l'état RÉEL de la base
et applique uniquement les différences (tables manquantes créées, colonnes
manquantes ajoutées via ALTER TABLE), sans jamais supprimer ni modifier les
données existantes.

Contrairement à `init --reset` (qui recrée tout depuis zéro), `migrate` est
conçu pour être relancé à tout moment pendant le développement, chaque fois
que le schéma évolue, sans jamais perdre les données déjà chargées.

Limites assumées (cas volontairement non gérés, car dangereux à automatiser
sans intervention humaine) :
  - suppression de colonne : jamais fait automatiquement (perte de données)
  - changement de type d'une colonne existante : jamais fait automatiquement
  - renommage de colonne : indiscernable d'un ajout + une suppression,
    donc traité comme les deux (l'ancienne colonne reste, une nouvelle
    apparaît) — à corriger manuellement si c'est le cas.

Usage :
    python manage.py migrate
"""
from dw.schema_generator import load_schema, build_columns, render_column_sql
from dw.warehouse import get_connection


def _existing_tables(con) -> set:
    return {r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchall()}


def _existing_columns(con, table: str) -> set:
    return {r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
    ).fetchall()}


def run(dry_run: bool = False):
    schema = load_schema()
    conventions = schema["conventions"]
    con = get_connection()
    existing_tables = _existing_tables(con)

    all_table_groups = [(schema["staging"], "staging")]
    for group_name in ["dimensions", "facts", "ml_tracking", "data_quality"]:
        all_table_groups.append((schema["warehouse"][group_name], f"warehouse.{group_name}"))

    n_tables_created = 0
    n_columns_added = 0

    for group, group_label in all_table_groups:
        apply_staging = group.get("apply_staging_columns", False)
        apply_scd2 = group.get("apply_scd2", False)

        for table_name, table_def in group["tables"].items():
            all_columns = build_columns(table_def, conventions, apply_staging, apply_scd2)

            if table_name not in existing_tables:
                if dry_run:
                    print(f"[à créer] table '{table_name}' ({group_label}) — n'existe pas encore")
                    n_tables_created += 1
                    continue
                col_lines = ",\n    ".join(render_column_sql(c) for c in all_columns)
                con.execute(f'CREATE TABLE "{table_name}" (\n    {col_lines}\n)')
                print(f"✓ Table créée : {table_name}")
                n_tables_created += 1
                continue

            existing_cols = _existing_columns(con, table_name)
            for col in all_columns:
                if col["name"] in existing_cols:
                    continue
                if dry_run:
                    print(f"[à ajouter] colonne '{col['name']}' sur '{table_name}'")
                    n_columns_added += 1
                    continue
                # Une colonne ajoutée après coup sur une table déjà peuplée ne peut
                # pas porter de contrainte NOT NULL (les lignes existantes seraient
                # invalides) : on l'ajoute nullable, quitte à être plus permissif
                # que la déclaration d'origine.
                col_relaxed = dict(col)
                col_relaxed["nullable"] = True
                col_relaxed.pop("pk", None)
                col_relaxed.pop("default", None)
                con.execute(f'ALTER TABLE "{table_name}" ADD COLUMN {render_column_sql(col_relaxed)}')
                print(f"✓ Colonne ajoutée : {table_name}.{col['name']}")
                n_columns_added += 1

    con.close()

    if dry_run:
        print(f"\n(mode simulation) {n_tables_created} table(s) et {n_columns_added} colonne(s) seraient créées/ajoutées.")
    else:
        print(f"\n✓ Migration terminée : {n_tables_created} table(s) créée(s), {n_columns_added} colonne(s) ajoutée(s).")
        if n_tables_created == 0 and n_columns_added == 0:
            print("  (rien à faire, la base était déjà à jour)")
