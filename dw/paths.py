"""Chemins centralisés du projet — modifier ici, jamais dans les autres modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SCHEMA_FILE = CONFIG_DIR / "schema.yaml"
SQL_DIR = ROOT / "sql"
DOC_DIR = ROOT / "docs"
DATA_RAW_DIR = ROOT / "data" / "raw"
DATA_WAREHOUSE_DIR = ROOT / "data" / "warehouse"
DB_PATH = DATA_WAREHOUSE_DIR / "social_analytics_dw.duckdb"
