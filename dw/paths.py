"""Chemins centralisés du projet — modifier ici, jamais dans les autres modules."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SCHEMA_FILE = CONFIG_DIR / "schema.yaml"
TAXONOMY_FILE = CONFIG_DIR / "taxonomy.yaml"
SQL_DIR = ROOT / "sql"
DOC_DIR = ROOT / "docs"
DATA_RAW_DIR = ROOT / "data" / "raw"

# L'emplacement de l'entrepôt est surchargeable par SJ_WAREHOUSE_DIR.
#
# Raison concrète : ce projet est stocké dans un dossier OneDrive. OneDrive
# ouvre les fichiers pour les synchroniser, ce qui pose un verrou bref mais
# bien réel sur le .duckdb. Les tests, qui créent et suppriment la base à
# chaque cas, tombent alors par intermittence sur « le fichier est utilisé par
# un autre processus » — et jamais sur le même test deux fois, ce qui rend le
# symptôme très trompeur. tests/conftest.py redirige donc la base vers un
# dossier temporaire hors synchronisation.
_warehouse_override = os.environ.get("SJ_WAREHOUSE_DIR")
DATA_WAREHOUSE_DIR = Path(_warehouse_override) if _warehouse_override else ROOT / "data" / "warehouse"
DB_PATH = DATA_WAREHOUSE_DIR / "social_analytics_dw.duckdb"
