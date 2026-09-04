"""
Suite de tests automatisés du data warehouse.

Lancer avec : pytest tests/ -v

Chaque test repart d'une base temporaire propre (fixture `fresh_db`) pour
rester indépendant des autres tests et reproductible.
"""
import shutil
import duckdb
import pandas as pd
import pytest

from dw.paths import DB_PATH, DATA_WAREHOUSE_DIR
from dw import schema_generator, warehouse, seed, transform, quality


@pytest.fixture
def fresh_db():
    """Reconstruit une base vide et peuplée des dimensions avant chaque test."""
    schema_generator.run()
    warehouse.init(reset=True)
    seed.run()
    yield DB_PATH
    if DB_PATH.exists():
        DB_PATH.unlink()


def test_schema_generation_produces_all_tables(fresh_db):
    con = duckdb.connect(str(fresh_db), read_only=True)
    tables = {r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables"
    ).fetchall()}
    con.close()
    expected = {"dim_source_dataset", "dim_platform", "dim_model", "dim_user",
                "fact_social_post", "fact_sentiment_prediction",
                "model_run", "model_metric", "dq_checks"}
    assert expected.issubset(tables)


def test_foreign_key_constraint_is_enforced(fresh_db):
    con = duckdb.connect(str(fresh_db))
    with pytest.raises(Exception):
        con.execute(
            "INSERT INTO fact_social_post (post_id, source_id, platform_id, external_post_id) "
            "VALUES (1, 9999, 1, 'x')"
        )
    con.close()


def test_seed_dimensions_are_idempotent(fresh_db):
    """Relancer seed deux fois ne doit pas dupliquer les lignes de référence."""
    seed.run()  # deuxième appel
    con = duckdb.connect(str(fresh_db), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM dim_source_dataset").fetchone()[0]
    con.close()
    assert count == len(seed.SOURCE_DATASETS)


def test_transform_new_rows_are_inserted(fresh_db, tmp_path):
    df = pd.DataFrame({
        "comment_id": ["a1", "a2"],
        "subreddit": ["tech", "news"],
        "text": ["premier commentaire", "deuxième commentaire"],
        "score": [5, 2],
        "created_at": ["2024-01-01", "2024-01-02"],
    })
    con = duckdb.connect(str(fresh_db))
    con.register("df_view", df)
    con.execute("INSERT INTO raw_reddit (comment_id, subreddit, text, score, created_at) SELECT * FROM df_view")
    con.close()

    from dw.transform import load_mapping
    cfg = load_mapping()["raw_reddit"]
    result = transform.transform_source("raw_reddit", cfg)

    assert result["new"] == 2
    assert result["updated"] == 0

    con = duckdb.connect(str(fresh_db), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM fact_social_post WHERE is_current").fetchone()[0]
    con.close()
    assert n == 2


def test_transform_detects_change_and_applies_scd2(fresh_db):
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_reddit (comment_id, text, score, ingested_at) "
                "VALUES ('b1', 'texte initial', 1, TIMESTAMP '2024-01-01 00:00:00')")
    con.close()

    from dw.transform import load_mapping
    cfg = load_mapping()["raw_reddit"]
    transform.transform_source("raw_reddit", cfg)

    # Rechargement avec une valeur modifiée, ingéré plus tard
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_reddit (comment_id, text, score, ingested_at) "
                "VALUES ('b1', 'texte modifié', 99, TIMESTAMP '2024-01-02 00:00:00')")
    con.close()

    result = transform.transform_source("raw_reddit", cfg)
    assert result["updated"] == 1
    assert result["new"] == 0

    con = duckdb.connect(str(fresh_db), read_only=True)
    versions = con.execute(
        "SELECT is_current, expiration_date FROM fact_social_post "
        "WHERE external_post_id = 'b1' ORDER BY post_id"
    ).fetchall()
    con.close()

    assert len(versions) == 2, "b1 doit avoir 2 versions après modification"
    assert versions[0][0] is False and versions[0][1] is not None, "l'ancienne version doit être expirée"
    assert versions[1][0] is True, "la nouvelle version doit être active"


def test_transform_unchanged_rows_are_not_duplicated(fresh_db):
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_reddit (comment_id, text, score) VALUES ('c1', 'stable', 5)")
    con.close()

    from dw.transform import load_mapping
    cfg = load_mapping()["raw_reddit"]
    transform.transform_source("raw_reddit", cfg)

    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_reddit (comment_id, text, score) VALUES ('c1', 'stable', 5)")
    con.close()

    result = transform.transform_source("raw_reddit", cfg)
    assert result["new"] == 0
    assert result["updated"] == 0

    con = duckdb.connect(str(fresh_db), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM fact_social_post WHERE external_post_id = 'c1'").fetchone()[0]
    con.close()
    assert n == 1, "aucune nouvelle version ne doit être créée si rien n'a changé"


def test_quality_check_detects_null_rate(fresh_db):
    con = duckdb.connect(str(fresh_db))
    con.execute("""
        INSERT INTO raw_reddit (comment_id, text, score) VALUES
        ('d1', 'ok', 1), ('d2', NULL, 2), ('d3', NULL, 3), ('d4', 'ok', 4)
    """)
    con.close()

    quality.run("raw_reddit")

    con = duckdb.connect(str(fresh_db), read_only=True)
    check = con.execute(
        "SELECT check_result FROM dq_checks WHERE check_name = 'null_rate_text' ORDER BY check_id DESC LIMIT 1"
    ).fetchone()
    con.close()
    assert check[0] == "WARN", "50% de nuls sur une colonne clé doit déclencher un WARN"


def test_quality_check_flags_negative_engagement_values(fresh_db):
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_reddit (comment_id, text, score) VALUES ('e1', 'ok', -5)")
    con.close()

    quality.run("raw_reddit")

    con = duckdb.connect(str(fresh_db), read_only=True)
    check = con.execute(
        "SELECT check_result, rows_failed FROM dq_checks "
        "WHERE check_name = 'type_consistency_score_non_negative' ORDER BY check_id DESC LIMIT 1"
    ).fetchone()
    con.close()
    assert check[0] == "WARN"
    assert check[1] == 1


def test_transform_handles_numeric_natural_key(fresh_db):
    """
    Cas limite qui a révélé un vrai bug : un dataset dont l'identifiant
    naturel est numérique (BIGINT, ex: Sentiment140) doit être casté en
    VARCHAR pour rester compatible avec external_post_id (VARCHAR).
    """
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_sentiment140 (tweet_id, text, polarity) VALUES (12345, 'test', 4)")
    con.close()

    from dw.transform import load_mapping
    cfg = load_mapping()["raw_sentiment140"]
    result = transform.transform_source("raw_sentiment140", cfg)
    assert result["new"] == 1

    # Recharger le même identifiant numérique doit être détecté comme inchangé, pas planter
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_sentiment140 (tweet_id, text, polarity) VALUES (12345, 'test', 4)")
    con.close()
    result2 = transform.transform_source("raw_sentiment140", cfg)
    assert result2["new"] == 0
    assert result2["updated"] == 0


def test_transform_on_empty_staging_table_does_not_crash(fresh_db):
    """Cas limite qui a révélé un vrai bug pendant le développement — gardé comme non-régression."""
    from dw.transform import load_mapping
    cfg = load_mapping()["raw_reddit"]
    result = transform.transform_source("raw_reddit", cfg)
    assert result["new"] == 0
    assert result["updated"] == 0
    assert result["staging_rows_raw"] == 0


def test_fetch_sample_maps_and_synthesizes_columns(tmp_path, monkeypatch):
    """
    Vérifie la logique de mapping/synthèse de colonnes de fetch_samples,
    sans appel réseau réel (fonction load_dataset injectée).
    """
    from dw import fetch_samples

    class FakeStreamingDataset:
        def __init__(self, rows):
            self._rows = rows

        def shuffle(self, seed, buffer_size):
            return self

        def take(self, n):
            return iter(self._rows[:n])

    def make_fake_loader(rows):
        def fake_load_dataset(path, name=None, split=None, streaming=None, **kwargs):
            return FakeStreamingDataset(rows)
        return fake_load_dataset

    monkeypatch.setattr(fetch_samples, "DATA_RAW_DIR", tmp_path)

    # --- Allociné ---
    rows = [{"review": f"critique {i}", "label": i % 2} for i in range(20)]
    out_path = fetch_samples.fetch_sample("raw_allocine", n=5, _load_dataset_fn=make_fake_loader(rows))
    df = pd.read_csv(out_path)
    assert len(df) == 5
    assert set(df.columns) == {"text", "review_id", "rating", "review_date"}
    assert df["review_id"].tolist() == ["al_0", "al_1", "al_2", "al_3", "al_4"]

    # --- Amazon Reviews ---
    rows = [{"title": f"t{i}", "content": f"contenu {i}", "label": i % 2} for i in range(20)]
    out_path = fetch_samples.fetch_sample("raw_amazon_reviews", n=5, _load_dataset_fn=make_fake_loader(rows))
    df = pd.read_csv(out_path)
    assert len(df) == 5
    assert "text" in df.columns and "star_rating" in df.columns

    # --- Reddit (avec conversion de timestamp epoch -> date lisible) ---
    rows = [{"id": f"c{i}", "subreddit.name": "test", "body": f"commentaire {i}",
             "score": i, "created_utc": 1700000000 + i} for i in range(20)]
    out_path = fetch_samples.fetch_sample("raw_reddit", n=5, _load_dataset_fn=make_fake_loader(rows))
    df = pd.read_csv(out_path)
    assert len(df) == 5
    assert set(df.columns) == {"comment_id", "subreddit", "text", "score", "created_at"}
    assert df["comment_id"].tolist() == ["c0", "c1", "c2", "c3", "c4"]
    assert df["created_at"].iloc[0].startswith("2023")  # epoch converti en date lisible


def test_users_are_stored_hashed_not_plaintext(fresh_db):
    con = duckdb.connect(str(fresh_db), read_only=True)
    row = con.execute("SELECT hashed_password FROM dim_user WHERE username = 'admin_global'").fetchone()
    con.close()
    assert row is not None
    assert row[0] != "admin123", "le mot de passe ne doit jamais être stocké en clair"
    assert row[0].startswith("$2b$"), "doit être un hash bcrypt"
