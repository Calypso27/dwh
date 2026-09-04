"""Chargeur générique : envoie un fichier CSV/Excel/TSV vers sa table de staging."""
import pandas as pd
from pathlib import Path
from dw.warehouse import get_connection
from dw.paths import DATA_RAW_DIR

# Certains datasets publics largement utilisés (ex: Sentiment140) sont encodés
# en latin-1/cp1252, pas en UTF-8 — on essaie UTF-8 d'abord (le cas standard),
# puis on bascule automatiquement plutôt que de planter.
ENCODING_FALLBACKS = ["utf-8", "latin-1", "cp1252"]


def _read_with_encoding_fallback(read_fn, file_path: Path, **kwargs) -> pd.DataFrame:
    last_error = None
    for encoding in ENCODING_FALLBACKS:
        try:
            df = read_fn(file_path, encoding=encoding, **kwargs)
            if encoding != "utf-8":
                print(f"⚠ Fichier non-UTF-8 détecté, lu avec l'encodage '{encoding}'")
            return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = e
            continue
    raise ValueError(
        f"Impossible de lire {file_path.name} avec les encodages testés {ENCODING_FALLBACKS}"
    ) from last_error


def read_any(file_path: Path) -> pd.DataFrame:
    suffix = file_path.suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)  # les fichiers Excel n'ont pas ce problème d'encodage
    elif suffix == ".csv":
        return _read_with_encoding_fallback(pd.read_csv, file_path)
    elif suffix == ".tsv":
        return _read_with_encoding_fallback(pd.read_csv, file_path, sep="\t")
    raise ValueError(f"Format non supporté : {suffix}")


def load(file: str, table: str):
    file_path = Path(file)
    if not file_path.is_absolute() and not file_path.exists():
        candidate = DATA_RAW_DIR / file_path
        if candidate.exists():
            file_path = candidate

    df = read_any(file_path)
    df["source_file"] = file_path.name

    con = get_connection()
    target_columns = [r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table}' AND column_name != 'ingested_at'"
    ).fetchall()]

    if not target_columns:
        raise ValueError(f"Table '{table}' introuvable — vérifie qu'elle est déclarée dans config/schema.yaml")

    missing = set(df.columns) - set(target_columns)
    if missing:
        print(f"⚠ Colonnes ignorées (absentes du schéma déclaré) : {missing}")
        df = df[[c for c in df.columns if c not in missing]]

    con.register("df_view", df)
    cols = ", ".join(df.columns)
    con.execute(f'INSERT INTO "{table}" ({cols}) SELECT {cols} FROM df_view')

    total = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    print(f"✓ {len(df):,} lignes chargées depuis {file_path.name} → {table}")
    print(f"✓ Total actuel dans {table} : {total:,} lignes")
    con.close()
