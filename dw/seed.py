"""Peuple les tables de dimension avec les valeurs de référence connues."""
from dw.warehouse import get_connection

SOURCE_DATASETS = [
    (1, "YouTube Comments Sentiment", "public_dataset", "en", "voir page Hugging Face", False),
    (2, "Sentiment140", "public_dataset", "en", "voir page Kaggle", False),
    (3, "French Twitter Sentiment", "public_dataset", "fr", "voir page Kaggle", False),
    (4, "Allociné Reviews", "public_dataset", "fr", "voir page Hugging Face", False),
    (5, "Reddit Comments", "public_dataset", "en", "voir page Hugging Face", False),
    (6, "Amazon Reviews", "public_dataset", "en", "voir page source", False),
    (7, "Facebook Comments + Publications", "public_dataset", "en", "dataset local", False),
    (8, "Multi-platform Social Sentiment Evolution", "public_dataset", "multi", "dataset local", False),
]

PLATFORMS = [
    (1, "YouTube", "vidéo"),
    (2, "Twitter/X", "texte"),
    (3, "Allociné", "texte"),
    (4, "Reddit", "texte"),
    (5, "Amazon", "texte"),
    (6, "Facebook", "mixte"),
    (7, "Instagram", "mixte"),
    (8, "LinkedIn", "texte"),
    (9, "Multi-platform", "mixte"),
]

MODELS = [
    (1, "DummyClassifier", "1.0", "baseline"),
    (2, "LogisticRegression", "1.0", "linear"),
    (3, "RandomForestClassifier", "1.0", "tree_ensemble"),
    (4, "HistGradientBoosting", "1.0", "tree_ensemble"),
    (5, "XGBoost", "1.0", "tree_ensemble"),
    (6, "cardiffnlp/twitter-xlm-roberta-base-sentiment", "1.0", "transformer"),
    (7, "DistilCamemBERT-sentiment", "1.0", "transformer"),
    (8, "Ridge", "1.0", "linear"),
    (9, "RandomForestRegressor", "1.0", "tree_ensemble"),
    (10, "DummyRegressor", "1.0", "baseline"),
    (11, "TFIDF-LogisticRegression", "1.0", "linear"),
    (12, "TFIDF-LinearSVM", "1.0", "linear"),
]


def _seed_users(con):
    """Comptes de démonstration — à remplacer par un vrai formulaire de création de compte."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    users = [
        (1, "admin_global", pwd_context.hash("admin123"), "institution_admin", None, True),
        (2, "admin_sji", pwd_context.hash("sji123"), "scoped_admin", 2, True),
    ]
    return _upsert(con, "dim_user",
                    ["user_id", "username", "hashed_password", "role", "scope_source_id", "is_active"],
                    users)


def _upsert(con, table, columns, rows):
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    inserted = 0
    for row in rows:
        exists = con.execute(f"SELECT 1 FROM {table} WHERE {columns[0]} = ?", [row[0]]).fetchone()
        if exists:
            continue
        con.execute(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})", row)
        inserted += 1
    return inserted


def run():
    con = get_connection()
    n1 = _upsert(con, "dim_source_dataset",
                 ["source_id", "source_name", "provenance", "language", "license", "is_synthetic"],
                 SOURCE_DATASETS)
    print(f"✓ dim_source_dataset : {n1} nouvelles lignes ({len(SOURCE_DATASETS)} au total déclarées)")

    n2 = _upsert(con, "dim_platform", ["platform_id", "platform_name", "content_type"], PLATFORMS)
    print(f"✓ dim_platform : {n2} nouvelles lignes ({len(PLATFORMS)} au total déclarées)")

    n3 = _upsert(con, "dim_model", ["model_id", "model_name", "model_version", "model_family"], MODELS)
    print(f"✓ dim_model : {n3} nouvelles lignes ({len(MODELS)} au total déclarées)")

    n4 = _seed_users(con)
    print(f"✓ dim_user : {n4} nouveaux comptes créés (mots de passe hashés en base)")
    con.close()
