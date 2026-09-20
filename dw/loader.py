"""Chargeur générique : envoie un fichier CSV/Excel/TSV vers sa table de staging."""
import re
import hashlib
import pandas as pd
from pathlib import Path
from dw.warehouse import get_connection
from dw.paths import DATA_RAW_DIR
from dw.load_profiles import get_profile

ENCODING_FALLBACKS = ["utf-8", "latin-1", "cp1252"]
_TZ_ABBREV_PATTERN = re.compile(r"\s+(PST|PDT|MST|MDT|CST|CDT|EST|EDT|UTC|GMT)\s+(\d{4})$")


def _strip_known_tz_abbreviations(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(_TZ_ABBREV_PATTERN, r" \2", regex=True)


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


def read_any(file_path: Path, column_names: list = None, sep: str = ",") -> pd.DataFrame:
    suffix = file_path.suffix.lower()
    extra_kwargs = {}
    if column_names:
        extra_kwargs = {"header": None, "names": column_names}

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(file_path, **extra_kwargs)
    elif suffix == ".csv":
        return _read_with_encoding_fallback(pd.read_csv, file_path, sep=sep, **extra_kwargs)
    elif suffix == ".tsv":
        return _read_with_encoding_fallback(pd.read_csv, file_path, sep="\t", **extra_kwargs)
    raise ValueError(f"Format non supporté : {suffix}")


def _coerce_timestamp_columns(df: pd.DataFrame, timestamp_columns: set) -> pd.DataFrame:
    for col in df.columns:
        if col not in timestamp_columns:
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        original_non_null = df[col].notna().sum()
        cleaned = _strip_known_tz_abbreviations(df[col])
        parsed = pd.to_datetime(cleaned, errors="coerce")
        newly_failed = original_non_null - parsed.notna().sum()
        if newly_failed > 0:
            print(f"⚠ {newly_failed:,} valeurs de la colonne '{col}' n'ont pas pu être converties "
                  f"en date et sont devenues NULL (format non reconnu)")
        df[col] = parsed
    return df


def _generate_stable_id(df: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """
    Génère un identifiant STABLE basé sur le hash du contenu de la ligne
    (pas juste sa position). Propriété importante : recharger exactement le
    même fichier reproduit les mêmes identifiants -> le transform SCD2 les
    reconnaît comme 'inchangés' plutôt que de créer de faux doublons.
    Ne jamais utiliser pour un vrai identifiant métier : c'est un pis-aller
    pour les fichiers qui n'en fournissent aucun.
    """
    content_cols = [c for c in df.columns if c != id_column]
    combined = df[content_cols].astype(str).agg("|".join, axis=1)
    df[id_column] = combined.apply(
        lambda s: int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % (2**62)
    )
    return df


def _compute_file_hash(file_path: Path) -> str:
    """Hash SHA-256 du contenu brut du fichier — sert à détecter un rechargement du même fichier."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _check_prior_ingestion(con, file_hash: str, table: str):
    return con.execute(
        "SELECT log_id, file_name, loaded_at, row_count FROM ingestion_log "
        "WHERE file_hash = ? AND table_name = ? AND status IN ('LOADED', 'FORCED_RELOAD') "
        "ORDER BY loaded_at DESC LIMIT 1",
        [file_hash, table]
    ).fetchone()


def _log_ingestion(con, file_hash, file_name, table, row_count, status):
    next_id = con.execute("SELECT COALESCE(MAX(log_id), 0) + 1 FROM ingestion_log").fetchone()[0]
    con.execute(
        "INSERT INTO ingestion_log (log_id, file_hash, file_name, table_name, row_count, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [next_id, file_hash, file_name, table, row_count, status]
    )


def load(file: str, table: str, column_names: list = None,
         rename_columns: dict = None, generate_id: list = None, force: bool = False,
         sep: str = None):
    file_path = Path(file)
    if not file_path.is_absolute() and not file_path.exists():
        candidate = DATA_RAW_DIR / file_path
        if candidate.exists():
            file_path = candidate

    # Applique automatiquement le profil déclaratif de la source si un existe
    # (config/load_profiles.yaml), sans écraser ce que l'utilisateur a explicitement fourni.
    profile = get_profile(table)
    if profile:
        if column_names is None and "column_names" in profile:
            column_names = profile["column_names"]
            print(f"ℹ Profil de chargement appliqué pour '{table}' : column_names={column_names}")
        if rename_columns is None and "rename_columns" in profile:
            rename_columns = profile["rename_columns"]
            print(f"ℹ Profil de chargement appliqué pour '{table}' : rename_columns={rename_columns}")
        if generate_id is None and "generate_id" in profile:
            generate_id = profile["generate_id"]
            print(f"ℹ Profil de chargement appliqué pour '{table}' : generate_id={generate_id}")
        if sep is None and "sep" in profile:
            sep = profile["sep"]
            print(f"ℹ Profil de chargement appliqué pour '{table}' : sep='{sep}'")

    file_hash = _compute_file_hash(file_path)
    con = get_connection()

    prior = _check_prior_ingestion(con, file_hash, table)
    if prior and not force:
        prior_log_id, prior_file_name, prior_loaded_at, prior_row_count = prior
        print(f"⚠⚠ CE FICHIER A DÉJÀ ÉTÉ CHARGÉ dans '{table}' : {prior_file_name} le {prior_loaded_at} "
              f"({prior_row_count:,} lignes). Chargement ANNULÉ pour éviter un doublon.")
        print(f"   Si c'est volontaire (ex: le fichier source a changé côté disque sans renommage), "
              f"relance avec --force.")
        _log_ingestion(con, file_hash, file_path.name, table, 0, "SKIPPED_DUPLICATE")
        con.close()
        return "SKIPPED_DUPLICATE"

    df = read_any(file_path, column_names=column_names, sep=sep or ",")

    if rename_columns:
        df = df.rename(columns=rename_columns)
        print(f"✓ Colonnes renommées : {rename_columns}")

    if generate_id:
        for id_col in generate_id:
            df = _generate_stable_id(df, id_col)
            print(f"✓ Identifiant '{id_col}' généré à partir d'un hash stable du contenu "
                  f"(le fichier source n'en fournissait pas)")

    df["source_file"] = file_path.name

    schema_columns = con.execute(
        f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'"
    ).fetchall()
    target_columns = [r[0] for r in schema_columns if r[0] != "ingested_at"]
    timestamp_columns = {r[0] for r in schema_columns if r[1] == "TIMESTAMP"}

    if not target_columns:
        con.close()
        raise ValueError(f"Table '{table}' introuvable — vérifie qu'elle est déclarée dans config/schema.yaml")

    all_target_columns = [c for c in target_columns if c != "source_file"]
    absent_from_file = set(all_target_columns) - set(df.columns)
    if absent_from_file:
        print(f"⚠⚠ ATTENTION : ces colonnes attendues par le schéma sont ABSENTES de ton fichier : {absent_from_file}")
        print("   Elles resteront NULL pour toutes les lignes chargées — vérifie les noms de colonnes de ton "
              "fichier source avec : python manage.py inspect --table " + table)

    missing = set(df.columns) - set(target_columns)
    if missing:
        print(f"⚠ Colonnes ignorées (absentes du schéma déclaré) : {missing}")
        df = df[[c for c in df.columns if c not in missing]]

    df = _coerce_timestamp_columns(df, timestamp_columns)

    con.register("df_view", df)
    cols = ", ".join(df.columns)
    con.execute(f'INSERT INTO "{table}" ({cols}) SELECT {cols} FROM df_view')

    total = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    print(f"✓ {len(df):,} lignes chargées depuis {file_path.name} → {table}")
    print(f"✓ Total actuel dans {table} : {total:,} lignes")

    status = "FORCED_RELOAD" if prior else "LOADED"
    _log_ingestion(con, file_hash, file_path.name, table, len(df), status)
    con.close()
    return status


def load_all(force: bool = False) -> dict:
    """
    Recharge TOUTES les sources déclarées dans config/load_profiles.yaml
    avec un `file`, en une seule commande — sans avoir à retaper --file/--table
    pour chaque source à la main.

    Une source dont le fichier est absent de data/raw/ est simplement
    signalée et ignorée (pas d'erreur bloquante : c'est normal de ne pas
    encore avoir toutes les sources en local).
    Une source déjà chargée à l'identique est protégée par la même logique
    anti-doublon que `load` (voir --force).

    Retourne un résumé {table: statut} pour permettre d'automatiser des
    vérifications si besoin (ex: dans un test).
    """
    from dw.load_profiles import all_profiles

    profiles = all_profiles()
    tables_with_file = {table: p for table, p in profiles.items() if p.get("file")}

    if not tables_with_file:
        print("⚠ Aucune source avec un champ 'file' déclaré dans config/load_profiles.yaml — rien à charger.")
        return {}

    summary = {}
    for table, profile in tables_with_file.items():
        file_name = profile["file"]
        file_path = DATA_RAW_DIR / file_name
        print(f"\n--- {table} ({file_name}) ---")
        if not file_path.exists():
            print(f"⚠ Fichier introuvable : {file_path} — source ignorée. "
                  f"Dépose le fichier dans data/raw/ pour l'inclure.")
            summary[table] = "MISSING_FILE"
            continue
        try:
            summary[table] = load(file_name, table, force=force)  # LOADED / FORCED_RELOAD / SKIPPED_DUPLICATE
        except Exception as e:
            print(f"✗ Échec du chargement de '{table}' : {type(e).__name__}: {e}")
            summary[table] = "FAILED"

    n_loaded = sum(1 for s in summary.values() if s in ("LOADED", "FORCED_RELOAD"))
    n_skipped = sum(1 for s in summary.values() if s == "SKIPPED_DUPLICATE")
    n_missing = sum(1 for s in summary.values() if s == "MISSING_FILE")
    n_failed = sum(1 for s in summary.values() if s == "FAILED")
    print(f"\n✓ load-all terminé : {n_loaded} chargée(s), {n_skipped} ignorée(s) (déjà chargées, "
          f"utilise --force pour les recharger), {n_missing} fichier(s) manquant(s), {n_failed} échec(s).")
    return summary
