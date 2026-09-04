"""
Générateur de schéma — lit config/schema.yaml (source de vérité unique) et produit :
  1. Le SQL de création pour la couche staging
  2. Le SQL de création pour la couche warehouse (dimensions, faits, ML tracking, qualité)
  3. Un dictionnaire de données en Markdown (documentation auto-générée pour le mémoire)
"""

import yaml
from datetime import datetime
from dw.paths import SCHEMA_FILE, SQL_DIR, DOC_DIR

# Différences de typage entre moteurs. DuckDB accepte DOUBLE tel quel ;
# PostgreSQL exige DOUBLE PRECISION. On ajoute ici toute future différence
# de dialecte plutôt que de la découvrir en production.
TYPE_OVERRIDES = {
    "postgres": {"DOUBLE": "DOUBLE PRECISION"},
}


def load_schema() -> dict:
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_type(sql_type: str, target_engine: str) -> str:
    return TYPE_OVERRIDES.get(target_engine, {}).get(sql_type, sql_type)


def build_columns(table_def: dict, conventions: dict, apply_staging: bool, apply_scd2: bool) -> list:
    columns = list(table_def.get("columns", []))
    if apply_staging:
        columns += conventions["staging_columns"]
    if apply_scd2:
        columns += conventions["scd2_columns"]
    return columns


def render_column_sql(col: dict, target_engine: str = "duckdb") -> str:
    resolved_type = resolve_type(col["type"], target_engine)
    parts = [f'"{col["name"]}"', resolved_type]
    if not col.get("nullable", True) and not col.get("pk", False):
        parts.append("NOT NULL")
    if col.get("pk"):
        parts.append("PRIMARY KEY")
    if "default" in col and col["default"] is not None:
        default_val = col["default"]
        if default_val == "CURRENT_TIMESTAMP":
            parts.append("DEFAULT CURRENT_TIMESTAMP")
        elif isinstance(default_val, bool):
            parts.append(f"DEFAULT {str(default_val).upper()}")
        else:
            parts.append(f"DEFAULT {default_val}")
    return " ".join(parts)


def render_table_sql(table_name: str, table_def: dict, columns: list, target_engine: str = "duckdb") -> str:
    lines = [f"-- {table_def.get('description', '')}", f'CREATE TABLE IF NOT EXISTS "{table_name}" (']
    col_lines = [f"    {render_column_sql(c, target_engine)}" for c in columns]
    fk_lines = []
    for c in table_def.get("columns", []):
        if "fk" in c:
            ref_table, ref_col = c["fk"].split(".")
            fk_lines.append(f'    FOREIGN KEY ("{c["name"]}") REFERENCES "{ref_table}"("{ref_col}")')
    lines.append(",\n".join(col_lines + fk_lines))
    lines.append(");\n")
    return "\n".join(lines)


def generate_staging_sql(schema: dict, target_engine: str = None) -> str:
    target_engine = target_engine or schema.get("target_engine", "duckdb")
    conventions = schema["conventions"]
    staging = schema["staging"]
    apply_staging = staging.get("apply_staging_columns", True)
    apply_scd2 = staging.get("apply_scd2", False)

    header = [
        "-- =========================================================",
        f"-- COUCHE STAGING ({target_engine}) — généré automatiquement, ne pas éditer à la main",
        f"-- Source : config/schema.yaml — généré le {datetime.now().isoformat(timespec='seconds')}",
        "-- =========================================================\n",
    ]
    body = []
    for table_name, table_def in staging["tables"].items():
        cols = build_columns(table_def, conventions, apply_staging, apply_scd2)
        body.append(render_table_sql(table_name, table_def, cols, target_engine))
    return "\n".join(header + body)


def generate_warehouse_sql(schema: dict, target_engine: str = None) -> str:
    target_engine = target_engine or schema.get("target_engine", "duckdb")
    conventions = schema["conventions"]
    warehouse = schema["warehouse"]

    header = [
        "-- =========================================================",
        f"-- COUCHE WAREHOUSE ({target_engine}) — généré automatiquement, ne pas éditer à la main",
        f"-- Source : config/schema.yaml — généré le {datetime.now().isoformat(timespec='seconds')}",
        "-- =========================================================\n",
    ]
    body = []
    for group_name in ["dimensions", "facts", "ml_tracking", "data_quality"]:
        group = warehouse[group_name]
        apply_staging = group.get("apply_staging_columns", False)
        apply_scd2 = group.get("apply_scd2", False)
        body.append(f"-- --- groupe : {group_name} ---\n")
        for table_name, table_def in group["tables"].items():
            cols = build_columns(table_def, conventions, apply_staging, apply_scd2)
            body.append(render_table_sql(table_name, table_def, cols, target_engine))
    return "\n".join(header + body)


def generate_data_dictionary(schema: dict) -> str:
    lines = [f"# Dictionnaire de données — {schema['database']}",
             f"\nGénéré automatiquement depuis `config/schema.yaml` le "
             f"{datetime.now().strftime('%Y-%m-%d %H:%M')}. Ne pas éditer à la main.\n"]

    def document_group(title, tables, conventions, apply_staging, apply_scd2):
        lines.append(f"\n## {title}\n")
        for table_name, table_def in tables.items():
            lines.append(f"\n### `{table_name}`")
            lines.append(f"{table_def.get('description', '')}\n")
            lines.append("| Colonne | Type | Contraintes | Description |")
            lines.append("|---|---|---|---|")
            cols = build_columns(table_def, conventions, apply_staging, apply_scd2)
            declared = {c["name"] for c in table_def.get("columns", [])}
            for c in cols:
                constraints = []
                if c.get("pk"):
                    constraints.append("PK")
                if "fk" in c:
                    constraints.append(f"FK → {c['fk']}")
                if not c.get("nullable", True):
                    constraints.append("NOT NULL")
                tag = "" if c["name"] in declared else " *(technique, auto-injectée)*"
                lines.append(f"| {c['name']}{tag} | {c['type']} | {', '.join(constraints) or '—'} | {c.get('description', '')} |")

    conventions = schema["conventions"]
    document_group("Couche staging", schema["staging"]["tables"], conventions,
                    schema["staging"].get("apply_staging_columns", True),
                    schema["staging"].get("apply_scd2", False))
    for group_name, group_title in [
        ("dimensions", "Warehouse — Dimensions"),
        ("facts", "Warehouse — Faits"),
        ("ml_tracking", "Warehouse — Suivi d'expériences ML"),
        ("data_quality", "Warehouse — Contrôle qualité"),
    ]:
        group = schema["warehouse"][group_name]
        document_group(group_title, group["tables"], conventions,
                        group.get("apply_staging_columns", False),
                        group.get("apply_scd2", False))
    return "\n".join(lines)


def run():
    schema = load_schema()
    SQL_DIR.mkdir(exist_ok=True, parents=True)
    DOC_DIR.mkdir(exist_ok=True, parents=True)

    # SQL pour DuckDB (utilisé par manage.py init au quotidien)
    (SQL_DIR / "01_staging.sql").write_text(generate_staging_sql(schema, "duckdb"), encoding="utf-8")
    (SQL_DIR / "02_warehouse.sql").write_text(generate_warehouse_sql(schema, "duckdb"), encoding="utf-8")

    # SQL pour PostgreSQL (couche applicative en production, voir README)
    postgres_dir = SQL_DIR / "postgres"
    postgres_dir.mkdir(exist_ok=True)
    (postgres_dir / "01_staging.sql").write_text(generate_staging_sql(schema, "postgres"), encoding="utf-8")
    (postgres_dir / "02_warehouse.sql").write_text(generate_warehouse_sql(schema, "postgres"), encoding="utf-8")

    data_dict = generate_data_dictionary(schema)
    (DOC_DIR / "data_dictionary.md").write_text(data_dict, encoding="utf-8")

    n_staging = len(schema["staging"]["tables"])
    n_wh = sum(len(schema["warehouse"][g]["tables"]) for g in ["dimensions", "facts", "ml_tracking", "data_quality"])
    print(f"✓ {n_staging} tables staging générées (DuckDB + PostgreSQL) → sql/ et sql/postgres/")
    print(f"✓ {n_wh} tables warehouse générées (DuckDB + PostgreSQL) → sql/ et sql/postgres/")
    print("✓ Dictionnaire de données → docs/data_dictionary.md")
