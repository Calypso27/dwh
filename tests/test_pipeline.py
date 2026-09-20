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


@pytest.fixture(autouse=True)
def _isolate_load_profiles(monkeypatch, tmp_path_factory):
    """
    Isole TOUS les tests du vrai config/load_profiles.yaml par défaut. Sans
    ça, un profil pensé pour un vrai fichier Kaggle sans en-tête (ex:
    raw_sentiment140 -> column_names sans en-tête) s'appliquerait aussi aux
    fixtures de test qui simulent des fichiers AVEC en-tête standard, cassant
    des tests sans rapport avec les profils. Le test qui veut vraiment tester
    un profil définit son propre monkeypatch après celui-ci (donc prioritaire).
    """
    from dw import load_profiles
    empty_profiles = tmp_path_factory.mktemp("no_profiles") / "load_profiles.yaml"
    monkeypatch.setattr(load_profiles, "PROFILES_FILE", empty_profiles)


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


def test_quality_check_does_not_flag_negative_reddit_score(fresh_db):
    """
    Faux positif corrigé : sur Reddit, 'score' = votes positifs - votes
    négatifs, un score net légitimement négatif ne doit PAS être signalé
    comme une anomalie (contrairement à likes/comments/shares/views).
    """
    con = duckdb.connect(str(DB_PATH))
    con.execute("INSERT INTO raw_reddit (comment_id, text, score) VALUES ('r1', 'impopulaire', -15)")
    con.close()

    quality.run("raw_reddit")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    check = con.execute(
        "SELECT check_name FROM dq_checks WHERE check_name LIKE 'type_consistency_score%'"
    ).fetchall()
    con.close()
    assert len(check) == 0, "'score' négatif sur Reddit ne doit déclencher aucun contrôle de non-négativité"


def test_quality_check_flags_negative_engagement_values(fresh_db):
    """Un compteur comme 'likes' doit rester signalé s'il est négatif (contrairement à 'score')."""
    con = duckdb.connect(str(fresh_db))
    con.execute("INSERT INTO raw_youtube_comments (comment_id, likes) VALUES ('e1', -5)")
    con.close()

    quality.run("raw_youtube_comments")

    con = duckdb.connect(str(fresh_db), read_only=True)
    check = con.execute(
        "SELECT check_result, rows_failed FROM dq_checks "
        "WHERE check_name = 'type_consistency_likes_non_negative' ORDER BY check_id DESC LIMIT 1"
    ).fetchone()
    con.close()
    assert check[0] == "WARN"
    assert check[1] == 1


def test_quality_check_validates_principal_metrics(fresh_db):
    con = duckdb.connect(str(fresh_db))
    con.execute("""
        INSERT INTO raw_multi_platform_posts
            (post_id, sentiment_positive, toxicity_score, likes, shares, comments, total_engagement)
        VALUES ('q1', 1.2, 0.4, 10, 2, 3, 15),
               ('q2', 0.4, 101.4, 10, 2, 3, 99)
    """)
    con.close()

    quality.run("raw_multi_platform_posts")

    con = duckdb.connect(str(fresh_db), read_only=True)
    checks = dict(con.execute(
        "SELECT check_name, check_result FROM dq_checks "
        "WHERE table_name = 'raw_multi_platform_posts'"
    ).fetchall())
    con.close()
    assert checks["range_sentiment_positive"] == "WARN"
    assert checks["range_toxicity_score"] == "WARN"
    assert checks["engagement_total_consistent"] == "WARN"


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


def test_load_blocks_duplicate_file_by_default(fresh_db, tmp_path):
    """
    Incident réel reproduit : recharger le même fichier deux fois (french_tweets.csv
    x3) a pollué raw_twitter_fr. Un second chargement du même fichier doit
    maintenant être bloqué par défaut, détecté par hash de contenu.
    """
    from dw.loader import load

    csv_path = tmp_path / "same_file.csv"
    pd.DataFrame({"comment_id": ["a1"], "text": ["contenu"], "score": [5]}).to_csv(csv_path, index=False)

    load(str(csv_path), "raw_reddit")
    load(str(csv_path), "raw_reddit")  # même fichier, même table -> doit être bloqué

    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    log_statuses = con.execute("SELECT status FROM ingestion_log ORDER BY log_id").fetchall()
    con.close()

    assert count == 1, "le second chargement du même fichier ne doit rien insérer"
    assert [s[0] for s in log_statuses] == ["LOADED", "SKIPPED_DUPLICATE"]


def test_load_force_overrides_duplicate_protection(fresh_db, tmp_path):
    """--force doit permettre de recharger explicitement un fichier déjà ingéré."""
    from dw.loader import load

    csv_path = tmp_path / "same_file.csv"
    pd.DataFrame({"comment_id": ["a1"], "text": ["contenu"], "score": [5]}).to_csv(csv_path, index=False)

    load(str(csv_path), "raw_reddit")
    load(str(csv_path), "raw_reddit", force=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    con.close()
    assert count == 2, "--force doit permettre le second chargement"


def test_load_profile_applied_automatically_without_any_flag(fresh_db, tmp_path, monkeypatch):
    """
    Incident réel : french_tweets.csv chargé SANS --generate-id/--rename-columns
    la première fois (le profil n'existait pas encore) a laissé tweet_id NULL.
    Avec le profil déclaratif, ce cas ne doit plus jamais se produire, même
    si l'utilisateur ne tape aucun flag.
    """
    from dw import load_profiles
    from dw.loader import load

    profiles_file = tmp_path / "load_profiles.yaml"
    profiles_file.write_text(
        "profiles:\n"
        "  raw_twitter_fr:\n"
        "    rename_columns: {label: sentiment}\n"
        "    generate_id: [tweet_id]\n"
    )
    monkeypatch.setattr(load_profiles, "PROFILES_FILE", profiles_file)

    csv_path = tmp_path / "french.csv"
    pd.DataFrame({"text": ["bon service"], "label": ["positive"]}).to_csv(csv_path, index=False)

    load(str(csv_path), "raw_twitter_fr")  # aucun flag fourni

    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute("SELECT tweet_id, sentiment FROM raw_twitter_fr").fetchone()
    con.close()

    assert row[0] is not None, "le profil doit générer tweet_id même sans --generate-id explicite"
    assert row[1] == "positive", "le profil doit renommer label -> sentiment même sans --rename-columns explicite"


def test_load_all_loads_present_files_and_skips_missing_ones(fresh_db, tmp_path, monkeypatch):
    """
    `load-all` doit charger toutes les sources dont le fichier existe dans
    data/raw/, appliquer leur profil automatiquement (comme `load` seul),
    et simplement signaler (sans planter) les sources dont le fichier est
    absent — c'est le scénario normal tant que toutes les sources n'ont pas
    encore été déposées localement.
    """
    from dw import load_profiles, loader

    profiles_file = tmp_path / "load_profiles.yaml"
    profiles_file.write_text(
        "profiles:\n"
        "  raw_reddit:\n"
        "    file: present.csv\n"
        "  raw_allocine:\n"
        "    file: absent.csv\n"
    )
    monkeypatch.setattr(load_profiles, "PROFILES_FILE", profiles_file)
    monkeypatch.setattr(loader, "DATA_RAW_DIR", tmp_path)

    (tmp_path / "present.csv").write_text(
        "comment_id,subreddit,text,score,created_at\nr1,tech,hello,5,2024-01-01\n"
    )
    # "absent.csv" n'est volontairement PAS créé.

    summary = loader.load_all()

    assert summary["raw_reddit"] == "LOADED"
    assert summary["raw_allocine"] == "MISSING_FILE"

    con = duckdb.connect(str(DB_PATH), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    con.close()
    assert n == 1


def test_load_all_respects_duplicate_protection_unless_forced(fresh_db, tmp_path, monkeypatch):
    """load-all doit bloquer un fichier déjà chargé, sauf si --force est passé."""
    from dw import load_profiles, loader

    profiles_file = tmp_path / "load_profiles.yaml"
    profiles_file.write_text("profiles:\n  raw_reddit:\n    file: present.csv\n")
    monkeypatch.setattr(load_profiles, "PROFILES_FILE", profiles_file)
    monkeypatch.setattr(loader, "DATA_RAW_DIR", tmp_path)

    (tmp_path / "present.csv").write_text(
        "comment_id,subreddit,text,score,created_at\nr1,tech,hello,5,2024-01-01\n"
    )

    loader.load_all()
    loader.load_all()  # 2e appel, sans --force : ne doit rien recharger

    con = duckdb.connect(str(DB_PATH), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    con.close()
    assert n == 1, "sans --force, un 2e load-all ne doit pas dupliquer les lignes déjà chargées"


def test_load_all_summary_distinguishes_skipped_from_actually_loaded(fresh_db, tmp_path, monkeypatch):
    """
    Incident réel : le résumé de `load-all` annonçait "6 chargée(s)" alors que
    les 6 sources avaient en fait été IGNORÉES par la protection anti-doublon
    (déjà chargées lors d'un run précédent). Le statut retourné par `load()`
    doit distinguer un vrai chargement d'un skip, pour que le résumé ne
    mente jamais sur ce qui s'est réellement passé.
    """
    from dw import load_profiles, loader

    profiles_file = tmp_path / "load_profiles.yaml"
    profiles_file.write_text("profiles:\n  raw_reddit:\n    file: present.csv\n")
    monkeypatch.setattr(load_profiles, "PROFILES_FILE", profiles_file)
    monkeypatch.setattr(loader, "DATA_RAW_DIR", tmp_path)

    (tmp_path / "present.csv").write_text(
        "comment_id,subreddit,text,score,created_at\nr1,tech,hello,5,2024-01-01\n"
    )

    first = loader.load_all()
    assert first["raw_reddit"] == "LOADED"

    second = loader.load_all()  # même fichier, pas de --force : doit être détecté comme SKIPPED
    assert second["raw_reddit"] == "SKIPPED_DUPLICATE", \
        "le statut doit refléter que le fichier a été ignoré, pas prétendre qu'il a été rechargé"


def test_loader_handles_non_utf8_encoding(tmp_path):
    """
    Cas réel rencontré en production : Sentiment140 (et d'autres datasets
    publics) sont encodés en latin-1, pas en UTF-8. Le chargeur doit
    basculer automatiquement au lieu de planter avec UnicodeDecodeError.
    """
    from dw.loader import read_any

    csv_path = tmp_path / "latin1_sample.csv"
    csv_content = "tweet_id,text\n1,café trop cher\n2,très déçu du service\n"
    csv_path.write_bytes(csv_content.encode("latin-1"))

    df = read_any(csv_path)
    assert len(df) == 2
    assert df["text"].tolist() == ["café trop cher", "très déçu du service"]


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

    # --- Reddit (epoch entier, ancien format supposé) ---
    rows = [{"id": f"c{i}", "subreddit.name": "test", "body": f"commentaire {i}",
             "score": i, "created_utc": 1700000000 + i} for i in range(20)]
    out_path = fetch_samples.fetch_sample("raw_reddit", n=5, _load_dataset_fn=make_fake_loader(rows))
    df = pd.read_csv(out_path)
    assert len(df) == 5
    assert set(df.columns) == {"comment_id", "subreddit", "text", "score", "created_at"}
    assert df["comment_id"].tolist() == ["c0", "c1", "c2", "c3", "c4"]
    assert df["created_at"].iloc[0].startswith("2023")  # epoch converti en date lisible

    # --- Reddit (bug réel rencontré : created_utc déjà en datetime.datetime, pas en epoch) ---
    from datetime import datetime as dt
    rows = [{"id": f"d{i}", "subreddit.name": "test", "body": f"commentaire {i}",
             "score": i, "created_utc": dt(2023, 6, 15, 10, 0, 0)} for i in range(5)]
    out_path = fetch_samples.fetch_sample("raw_reddit", n=3, _load_dataset_fn=make_fake_loader(rows))
    df = pd.read_csv(out_path)
    assert len(df) == 3
    assert df["created_at"].iloc[0].startswith("2023-06-15")


def test_loader_renames_and_generates_stable_id(fresh_db, tmp_path):
    """
    Bug réel : French Twitter Sentiment n'a que 'text' et 'label', aucun
    identifiant ni date. Le chargeur doit pouvoir renommer 'label' vers
    'sentiment' et générer un identifiant stable basé sur le contenu.
    """
    from dw.loader import load

    csv_path = tmp_path / "french.csv"
    pd.DataFrame({
        "text": ["service excellent", "tres decu"],
        "label": ["positive", "negative"],
    }).to_csv(csv_path, index=False)

    load(str(csv_path), "raw_twitter_fr", rename_columns={"label": "sentiment"}, generate_id=["tweet_id"])

    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute("SELECT tweet_id, text, sentiment FROM raw_twitter_fr ORDER BY text").fetchall()
    con.close()

    assert len(rows) == 2
    assert all(r[0] is not None for r in rows)  # identifiant bien généré, pas NULL
    assert rows[0][2] == "positive" and rows[1][2] == "negative"  # renommage appliqué ("service excellent" < "tres decu" alphabétiquement)


def test_generated_id_is_stable_across_reloads_preventing_duplicates(fresh_db, tmp_path):
    """
    Propriété critique du hash stable : recharger EXACTEMENT le même fichier
    doit reproduire les mêmes identifiants, pour que le transform SCD2 les
    reconnaisse comme 'inchangés' plutôt que de créer de faux doublons.
    """
    from dw.loader import load
    from dw.transform import load_mapping
    from dw import transform as transform_module

    csv_path = tmp_path / "french.csv"
    pd.DataFrame({"text": ["contenu stable"], "label": ["neutral"]}).to_csv(csv_path, index=False)

    cfg = load_mapping()["raw_twitter_fr"]

    load(str(csv_path), "raw_twitter_fr", rename_columns={"label": "sentiment"}, generate_id=["tweet_id"])
    transform_module.transform_source("raw_twitter_fr", cfg)

    # Rechargement du même fichier
    load(str(csv_path), "raw_twitter_fr", rename_columns={"label": "sentiment"}, generate_id=["tweet_id"])
    result = transform_module.transform_source("raw_twitter_fr", cfg)

    assert result["new"] == 0
    assert result["unchanged"] == 1

    con = duckdb.connect(str(DB_PATH), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM fact_social_post").fetchone()[0]
    con.close()
    assert n == 1, "aucun doublon ne doit être créé par un rechargement du même fichier"


def test_loader_handles_headerless_file_with_column_names(fresh_db, tmp_path):
    """
    Bug réel rencontré en production : le vrai fichier Sentiment140 Kaggle n'a
    pas de ligne d'en-tête. Sans --column-names, pandas prend la première
    ligne de données pour un en-tête, et TOUTES les vraies colonnes du schéma
    (tweet_id, text, polarity...) restent NULL pour l'intégralité du fichier.
    """
    from dw.loader import load

    csv_path = tmp_path / "headerless.csv"
    csv_path.write_text(
        "0,111,Mon Apr 06 22:19:45 PDT 2009,NO_QUERY,userA,mauvais service\n"
        "4,222,Mon Apr 06 22:19:49 PDT 2009,NO_QUERY,userB,super experience\n",
        encoding="utf-8",
    )

    load(str(csv_path), "raw_sentiment140",
         column_names=["polarity", "tweet_id", "tweet_date", "flag", "user_handle", "text"])

    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute("SELECT tweet_id, text, polarity FROM raw_sentiment140 LIMIT 1").fetchone()
    con.close()
    assert row == (111, "mauvais service", 0)


def test_loader_converts_non_iso_timestamp_with_tz_abbreviation(fresh_db, tmp_path):
    """
    Bug réel : le format de date Twitter classique ("Mon Apr 06 22:19:45 PDT
    2009") n'est pas reconnu tel quel par DuckDB (ni par %Z en Python), et
    plantait l'insertion. Le chargeur doit le convertir en vrai TIMESTAMP.
    """
    from dw.loader import load

    csv_path = tmp_path / "with_tz.csv"
    csv_path.write_text(
        "polarity,tweet_id,tweet_date,user_handle,text\n"
        "0,1,Mon Apr 06 22:19:45 PDT 2009,userA,test\n",
        encoding="utf-8",
    )

    load(str(csv_path), "raw_sentiment140")  # en-tête déjà correct ici, pas de column_names

    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute("SELECT tweet_date FROM raw_sentiment140 LIMIT 1").fetchone()
    con.close()
    assert row[0] is not None
    assert row[0].year == 2009 and row[0].month == 4 and row[0].day == 6


def test_loader_warns_when_expected_columns_are_missing(fresh_db, tmp_path, capsys):
    """
    Bug réel rencontré en production : un fichier Sentiment140 avec les vraies
    colonnes Kaggle (target, ids, date, flag, user, text) au lieu des colonnes
    attendues par le schéma (tweet_id, polarity, tweet_date, user_handle) a
    silencieusement rempli ces colonnes de NULL, faisant s'effondrer la
    déduplication SCD2 (tous les external_post_id NULL = 1 seul groupe).
    Le chargeur doit maintenant avertir clairement de ce cas.
    """
    from dw.loader import load

    csv_path = tmp_path / "mismatched.csv"
    pd.DataFrame({
        "target": [0, 4], "ids": [1, 2], "date": ["2024-01-01", "2024-01-02"],
        "flag": ["x", "x"], "user": ["a", "b"], "text": ["bad", "good"],
    }).to_csv(csv_path, index=False)

    load(str(csv_path), "raw_sentiment140")
    captured = capsys.readouterr()
    assert "ABSENTES de ton fichier" in captured.out
    assert "tweet_id" in captured.out


def test_inspect_distinguishes_missing_data_from_mapping_error(fresh_db, capsys):
    """
    Cas réel : sur le dataset YouTube, seule 'sentiment_score' est vide alors
    que toutes les autres colonnes sont bien peuplées — ce n'est pas une
    erreur de mapping, juste une donnée absente du fichier source. Le message
    doit être informatif (ℹ), pas alarmant (⚠⚠), dans ce cas précis.
    """
    from dw import inspect as dw_inspect

    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        INSERT INTO raw_youtube_comments (comment_id, video_id, channel_id, text, sentiment_category, likes, published_at)
        VALUES ('c1','v1','ch1','bon film','Positive',5,'2024-01-01')
    """)
    con.close()

    dw_inspect.run("raw_youtube_comments")
    captured = capsys.readouterr()
    assert "ℹ Colonne vide" in captured.out
    assert "⚠⚠ Colonnes ENTIÈREMENT vides" not in captured.out


def test_inspect_still_warns_strongly_on_real_mapping_error(fresh_db, capsys):
    """Cas inverse : si la majorité des colonnes sont vides, l'alerte forte doit rester déclenchée."""
    from dw import inspect as dw_inspect

    con = duckdb.connect(str(DB_PATH))
    con.execute("INSERT INTO raw_youtube_comments (source_file) VALUES ('mauvais_mapping.csv')")
    con.close()

    dw_inspect.run("raw_youtube_comments")
    captured = capsys.readouterr()
    assert "⚠⚠ Colonnes ENTIÈREMENT vides" in captured.out


def test_truncate_clears_only_target_table(fresh_db, tmp_path):
    """
    Répond à un vrai incident : `init --reset` efface TOUTE la base, causant
    une perte de données accidentelle sur d'autres sources pendant un
    débogage ciblé. `truncate` doit ne vider QUE la table demandée.
    """
    con = duckdb.connect(str(DB_PATH))
    con.execute("INSERT INTO raw_reddit (comment_id, text) VALUES ('r1', 'test')")
    con.execute("INSERT INTO raw_allocine (review_id, text) VALUES ('a1', 'test')")
    con.close()

    warehouse.truncate("raw_reddit", confirm=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    reddit_count = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    allocine_count = con.execute("SELECT COUNT(*) FROM raw_allocine").fetchone()[0]
    con.close()

    assert reddit_count == 0
    assert allocine_count == 1, "truncate ne doit jamais toucher aux autres tables"


def test_truncate_without_confirm_does_nothing(fresh_db):
    """Sans --confirm, aucune suppression ne doit avoir lieu (sécurité contre les fausses manœuvres)."""
    con = duckdb.connect(str(DB_PATH))
    con.execute("INSERT INTO raw_reddit (comment_id, text) VALUES ('r1', 'test')")
    con.close()

    warehouse.truncate("raw_reddit", confirm=False)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    con.close()
    assert count == 1, "sans --confirm, rien ne doit être supprimé"


def test_truncate_resets_ingestion_log_so_the_same_file_can_be_reloaded(fresh_db, tmp_path):
    """
    Incident découvert manuellement : après un `truncate`, recharger le MÊME
    fichier était bloqué par la protection anti-doublon (qui ne savait pas que
    la table avait été vidée), laissant la table silencieusement vide sans
    que rien ne le signale clairement. `truncate` doit réinitialiser
    l'historique de chargement de la table qu'il vide.
    """
    from dw import loader

    csv_path = tmp_path / "reddit.csv"
    csv_path.write_text("comment_id,subreddit,text,score,created_at\nr1,tech,hello,5,2024-01-01\n")

    loader.load(str(csv_path), "raw_reddit")
    warehouse.truncate("raw_reddit", confirm=True)
    loader.load(str(csv_path), "raw_reddit")  # sans --force : ne doit PAS être bloqué

    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM raw_reddit").fetchone()[0]
    con.close()
    assert count == 1, "après un truncate, recharger le même fichier doit fonctionner sans --force"


def test_migrate_creates_missing_tables_without_touching_existing_data(tmp_path, monkeypatch):
    """
    Incident réel : la base de l'utilisateur avait été créée avant l'ajout de
    dim_user/pipeline_runs/colonne text au schéma. `migrate` doit créer ce qui
    manque SANS jamais toucher aux tables/données déjà présentes.
    """
    import duckdb
    from dw import migrate, warehouse as dw_warehouse

    old_db = tmp_path / "old.duckdb"
    con = duckdb.connect(str(old_db))
    con.execute("CREATE TABLE dim_source_dataset (source_id INTEGER PRIMARY KEY, source_name VARCHAR)")
    con.execute("INSERT INTO dim_source_dataset VALUES (1, 'YouTube')")
    con.close()

    monkeypatch.setattr(dw_warehouse, "DB_PATH", old_db)
    migrate.run(dry_run=False)

    con = duckdb.connect(str(old_db), read_only=True)
    # La donnée pré-existante doit être intacte
    row = con.execute("SELECT source_id, source_name FROM dim_source_dataset").fetchone()
    assert row == (1, "YouTube")
    # La table manquante doit maintenant exister
    tables = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert "pipeline_runs" in tables
    assert "dim_user" in tables
    con.close()


def test_migrate_dry_run_does_not_modify_the_database(tmp_path, monkeypatch):
    """--dry-run doit uniquement afficher ce qui serait fait, sans rien appliquer."""
    import duckdb
    from dw import migrate, warehouse as dw_warehouse

    old_db = tmp_path / "old.duckdb"
    con = duckdb.connect(str(old_db))
    con.execute("CREATE TABLE dim_source_dataset (source_id INTEGER PRIMARY KEY)")
    con.close()

    monkeypatch.setattr(dw_warehouse, "DB_PATH", old_db)
    migrate.run(dry_run=True)

    con = duckdb.connect(str(old_db), read_only=True)
    tables = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    con.close()
    assert "pipeline_runs" not in tables, "dry-run ne doit rien créer réellement"


def test_pipeline_logs_successful_run(fresh_db, tmp_path):
    """Une exécution réussie du pipeline doit être journalisée avec status=SUCCESS."""
    from dw import pipeline as dw_pipeline

    dw_pipeline.run(trigger="scheduled")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute(
        "SELECT status, trigger_type, sources_processed FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    con.close()

    assert row[0] == "SUCCESS"
    assert row[1] == "scheduled"
    assert row[2] == 8  # les 8 sources déclarées dans mapping.yaml


def test_pipeline_logs_failure_and_reraises_for_nonzero_exit_code(fresh_db):
    """
    Propriété critique pour une tâche planifiée sans supervision : un échec
    doit être journalisé (status=FAILED, message d'erreur) ET l'exception
    doit être ré-émise, pour que le process se termine avec un code non-nul
    (sinon un scheduler comme cron/Task Scheduler croit que tout va bien).
    """
    from dw import pipeline as dw_pipeline

    con = duckdb.connect(str(DB_PATH))
    con.execute("DROP TABLE raw_reddit")
    con.close()

    with pytest.raises(Exception):
        dw_pipeline.run(trigger="scheduled")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute(
        "SELECT status, error_message FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    con.close()

    assert row[0] == "FAILED"
    assert row[1] is not None and "raw_reddit" in row[1]


def test_users_are_stored_hashed_not_plaintext(fresh_db):
    con = duckdb.connect(str(fresh_db), read_only=True)
    row = con.execute("SELECT hashed_password FROM dim_user WHERE username = 'admin_global'").fetchone()
    con.close()
    assert row is not None
    assert row[0] != "admin123", "le mot de passe ne doit jamais être stocké en clair"
    assert row[0].startswith("$2b$"), "doit être un hash bcrypt"
