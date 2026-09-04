"""
Moteur de transformation : fait passer les données de la couche staging
vers fact_social_post, en respectant le schéma commun défini dans
config/mapping.yaml.

Implémente une vraie logique SCD2 :
  - une ligne staging jamais vue -> nouvelle ligne fact (is_current = true)
  - une ligne staging dont le contenu a changé (texte, likes...) par rapport
    à la version actuelle -> l'ancienne version est expirée (is_current = false,
    expiration_date renseignée), une nouvelle version est insérée
  - une ligne staging identique à la version actuelle -> ignorée (idempotent :
    relancer plusieurs fois sans recharger de fichier ne duplique rien)

Tout est fait en SQL (pas de boucle Python ligne par ligne) pour rester
robuste sur de gros volumes.
"""
import yaml
from dw.paths import CONFIG_DIR
from dw.warehouse import get_connection

MAPPING_FILE = CONFIG_DIR / "mapping.yaml"

TRACKED_FIELDS = ["text_content", "likes", "comments", "shares", "views"]


def load_mapping() -> dict:
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["mappings"]


def _field_expr(field_value, cast_type: str | None = None) -> str:
    """Traduit une valeur de mapping ('nom_colonne' ou None) en expression SQL."""
    if field_value is None:
        return "NULL"
    expr = f'"{field_value}"'
    return f"CAST({expr} AS {cast_type})" if cast_type else expr


def transform_source(source_table: str, cfg: dict, con=None) -> dict:
    """Transforme une table staging vers fact_social_post. Retourne un résumé."""
    own_connection = con is None
    con = con or get_connection()

    fields = cfg["fields"]
    source_id = cfg["source_id"]
    platform_id = cfg["platform_id"]

    # Combien de lignes existent en staging pour cette source ?
    staging_count = con.execute(f'SELECT COUNT(*) FROM "{source_table}"').fetchone()[0]
    if staging_count == 0:
        if own_connection:
            con.close()
        return {"source": source_table, "staging_rows_raw": 0, "staging_rows_deduped": 0,
                "new": 0, "updated": 0, "unchanged": 0}

    # 1) Vue "staged" : staging reformaté au schéma commun, dédupliqué par clé
    #    naturelle (on garde la ligne la plus récemment ingérée en cas de doublon).
    select_fields = ", ".join(
        f"{_field_expr(fields[f], cast_type='VARCHAR' if f == 'external_post_id' else None)} AS {f}"
        for f in ["external_post_id", "text_content", "published_at", "likes", "comments", "shares", "views"]
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW staged AS
        SELECT {source_id} AS source_id, {platform_id} AS platform_id, {select_fields}
        FROM "{source_table}"
        QUALIFY ROW_NUMBER() OVER (PARTITION BY {_field_expr(fields['external_post_id'])}
                                    ORDER BY ingested_at DESC) = 1
    """)

    # 2) Versions actuelles déjà en warehouse pour cette source
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW current_facts AS
        SELECT * FROM fact_social_post WHERE source_id = {source_id} AND is_current = true
    """)

    # 3) Lignes nouvelles OU dont le contenu a changé par rapport à la version actuelle
    diff_clause = " OR ".join(
        f"COALESCE(s.{f}, '') != COALESCE(CAST(c.{f} AS VARCHAR), '')" for f in TRACKED_FIELDS
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW to_upsert AS
        SELECT s.*, (c.post_id IS NOT NULL) AS is_update
        FROM staged s
        LEFT JOIN current_facts c ON s.external_post_id = c.external_post_id
        WHERE c.post_id IS NULL OR ({diff_clause})
    """)

    n_new = con.execute("SELECT COUNT(*) FROM to_upsert WHERE NOT is_update").fetchone()[0]
    n_updated = con.execute("SELECT COUNT(*) FROM to_upsert WHERE is_update").fetchone()[0]
    staged_count = con.execute("SELECT COUNT(*) FROM staged").fetchone()[0]
    n_unchanged = staged_count - n_new - n_updated

    # 4) Expirer les anciennes versions concernées par un changement (SCD2)
    con.execute(f"""
        UPDATE fact_social_post
        SET is_current = false, expiration_date = CURRENT_TIMESTAMP
        WHERE source_id = {source_id} AND is_current = true
          AND external_post_id IN (SELECT external_post_id FROM to_upsert WHERE is_update)
    """)

    # 5) Insérer les nouvelles versions (nouvelles lignes + lignes modifiées)
    next_id = con.execute("SELECT COALESCE(MAX(post_id), 0) FROM fact_social_post").fetchone()[0]
    con.execute(f"""
        INSERT INTO fact_social_post
            (post_id, source_id, platform_id, external_post_id, text_content,
             published_at, likes, comments, shares, views,
             load_date, effective_date, expiration_date, is_current)
        SELECT
            {next_id} + ROW_NUMBER() OVER (),
            source_id, platform_id, external_post_id, text_content,
            published_at, likes, comments, shares, views,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, true
        FROM to_upsert
    """)

    if own_connection:
        con.close()

    return {"source": source_table, "staging_rows_raw": staging_count, "staging_rows_deduped": staged_count,
            "new": n_new, "updated": n_updated, "unchanged": n_unchanged}


def run(source: str | None = None):
    mapping = load_mapping()
    targets = {source: mapping[source]} if source else mapping

    con = get_connection()
    for table_name, cfg in targets.items():
        result = transform_source(table_name, cfg, con=con)
        print(f"✓ {result['source']:<28} staging_brut={result['staging_rows_raw']:>5}  "
              f"dédupliqué={result['staging_rows_deduped']:>5}  "
              f"nouveaux={result['new']:>4}  màj_scd2={result['updated']:>4}  "
              f"inchangés={result['unchanged']:>4}")
    con.close()
