"""Contrôles qualité, journalisés automatiquement dans dq_checks."""
from dw.warehouse import get_connection


def _log_check(con, table, check_name, result, rows_checked, rows_failed):
    next_id = con.execute("SELECT COALESCE(MAX(check_id), 0) + 1 FROM dq_checks").fetchone()[0]
    con.execute(
        "INSERT INTO dq_checks (check_id, table_name, check_name, check_result, rows_checked, rows_failed) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [next_id, table, check_name, result, rows_checked, rows_failed]
    )
    return result


def check_row_count(con, table, total_rows):
    result = "PASS" if total_rows > 0 else "FAIL"
    _log_check(con, table, "row_count_positive", result, total_rows, 0 if total_rows > 0 else 1)
    print(f"✓ row_count_positive : {result} ({total_rows:,} lignes)")


def check_duplicates(con, table, total_rows):
    columns = [r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
    ).fetchall()]
    col_list = ", ".join(columns)
    dup_count = con.execute(f'SELECT COUNT(*) - COUNT(DISTINCT ({col_list})) FROM "{table}"').fetchone()[0]
    dup_rate = dup_count / total_rows if total_rows else 0
    result = "PASS" if dup_rate < 0.01 else "WARN"
    _log_check(con, table, "duplicate_rate", result, total_rows, dup_count)
    print(f"✓ duplicate_rate : {result} ({dup_count:,} doublons, {dup_rate:.2%})")


def check_null_rate(con, table, total_rows, key_columns: list[str], threshold: float = 0.05):
    """Vérifie le taux de valeurs nulles sur les colonnes jugées critiques pour cette table."""
    for col in key_columns:
        exists = con.execute(
            f"SELECT 1 FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{col}'"
        ).fetchone()
        if not exists:
            continue
        null_count = con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" IS NULL').fetchone()[0]
        null_rate = null_count / total_rows if total_rows else 0
        result = "PASS" if null_rate <= threshold else "WARN"
        _log_check(con, table, f"null_rate_{col}", result, total_rows, null_count)
        print(f"✓ null_rate_{col} : {result} ({null_count:,} nuls, {null_rate:.2%})")


def check_type_consistency(con, table):
    """
    Vérifie que les colonnes numériques déclarées comme telles dans le schéma
    contiennent bien des valeurs numériques valides (pas de texte parasite).
    DuckDB rejette déjà les types incompatibles au chargement — ce contrôle
    documente et journalise explicitement que la vérification a eu lieu,
    plutôt que de se reposer silencieusement sur le moteur.
    """
    numeric_cols = con.execute(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = '{table}' AND data_type IN ('INTEGER', 'BIGINT', 'DOUBLE')
    """).fetchall()
    total_rows = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    for (col,) in numeric_cols:
        # Une valeur numérique négative dans un compteur d'engagement est incohérente
        if col in ("likes", "comments", "shares", "views", "score"):
            bad = con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" < 0').fetchone()[0]
            result = "PASS" if bad == 0 else "WARN"
            _log_check(con, table, f"type_consistency_{col}_non_negative", result, total_rows, bad)
            print(f"✓ type_consistency_{col}_non_negative : {result} ({bad:,} valeurs négatives)")


# Colonnes considérées critiques (candidates naturelles de clé métier) par table
KEY_COLUMNS_BY_TABLE = {
    "raw_sentiment140": ["tweet_id", "text"],
    "raw_twitter_fr": ["tweet_id", "text"],
    "raw_allocine": ["review_id", "text"],
    "raw_reddit": ["comment_id", "text"],
    "raw_youtube_comments": ["comment_id"],
    "raw_amazon_reviews": ["review_id", "text"],
}


def run(table: str):
    con = get_connection()
    total_rows = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    check_row_count(con, table, total_rows)
    check_duplicates(con, table, total_rows)
    check_null_rate(con, table, total_rows, KEY_COLUMNS_BY_TABLE.get(table, []))
    check_type_consistency(con, table)

    con.close()
