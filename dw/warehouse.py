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


def truncate(table: str, confirm: bool = False):
    """
    Vide UNE SEULE table, sans toucher au reste de la base — à utiliser à la
    place de `init --reset` quand seule une source a un problème de données.
    `init --reset` supprime TOUT le fichier .duckdb, y compris les autres
    sources déjà chargées avec succès (cause fréquente de perte de données
    accidentelle en cours de débogage).
    """
    con = get_connection()
    exists = con.execute(
        f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'"
    ).fetchone()
    if not exists:
        print(f"✗ Table '{table}' introuvable. Vérifie le nom avec : python manage.py status")
        con.close()
        return

    count_before = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    if not confirm:
        print(f"⚠ Ceci va supprimer {count_before:,} lignes de '{table}' UNIQUEMENT (le reste de la base est intact).")
        print(f"  Relance avec --confirm pour valider : python manage.py truncate --table {table} --confirm")
        con.close()
        return

    con.execute(f'DELETE FROM "{table}"')

    # La table est maintenant vide : son historique de chargement n'a plus lieu
    # d'être. Sans ce nettoyage, recharger le MÊME fichier après un truncate est
    # bloqué par la protection anti-doublon (`ingestion_log` se souvient encore
    # du fichier), et la table reste silencieusement vide sans `--force` — un
    # piège découvert lors d'un test manuel de bout en bout.
    ingestion_log_exists = con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'ingestion_log'"
    ).fetchone()
    if ingestion_log_exists:
        con.execute("DELETE FROM ingestion_log WHERE table_name = ?", [table])

    con.close()
    print(f"✓ Table '{table}' vidée ({count_before:,} lignes supprimées) — le reste de la base est intact.")
    print(f"  ✓ Historique de chargement de '{table}' réinitialisé (tu peux recharger les mêmes fichiers sans --force).")
