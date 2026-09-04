"""Initialisation et connexion au data warehouse physique (DuckDB)."""
import duckdb
from dw.paths import SQL_DIR, DB_PATH, DATA_WAREHOUSE_DIR


def get_connection():
    DATA_WAREHOUSE_DIR.mkdir(exist_ok=True, parents=True)
    return duckdb.connect(str(DB_PATH))


def init(reset: bool = False):
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"⚠ Base existante supprimée : {DB_PATH}")

    con = get_connection()
    for sql_file in ["01_staging.sql", "02_warehouse.sql"]:
        sql_path = SQL_DIR / sql_file
        if not sql_path.exists():
            raise FileNotFoundError(
                f"{sql_path} n'existe pas — lance d'abord : python manage.py generate-schema"
            )
        con.execute(sql_path.read_text(encoding="utf-8"))
        print(f"✓ Exécuté : {sql_file}")

    tables = con.execute("SELECT table_name FROM information_schema.tables ORDER BY table_name").fetchall()
    print(f"\n✓ Base initialisée : {DB_PATH}")
    print(f"✓ {len(tables)} tables prêtes : {', '.join(t[0] for t in tables)}")
    con.close()


def status():
    con = get_connection()
    tables = con.execute("SELECT table_name FROM information_schema.tables ORDER BY table_name").fetchall()
    if not tables:
        print("Base vide ou non initialisée. Lance : python manage.py init")
        return
    print(f"{'Table':<35} {'Lignes':>10}")
    print("-" * 47)
    for (table_name,) in tables:
        count = con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        print(f"{table_name:<35} {count:>10,}")
    con.close()
