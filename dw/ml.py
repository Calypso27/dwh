"""Benchmarks reproductibles des modeles engagement et viralite."""
import json
from pathlib import Path

import duckdb
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    average_precision_score,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split

from dw.paths import DB_PATH, DOC_DIR


FEATURES = [
    "followers", "account_age_days", "verified", "content_length",
    "num_hashtags", "sentiment_positive", "sentiment_negative",
    "sentiment_neutral", "hours_since_post", "platform", "topic",
    "language", "media_type",
]
NUMERIC_FEATURES = [feature for feature in FEATURES if feature not in {
    "platform", "topic", "language", "media_type"
}]
CATEGORICAL_FEATURES = ["platform", "topic", "language", "media_type"]


def _preprocessor() -> ColumnTransformer:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])


def _load_data() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    frame = con.execute("""
        SELECT *
        FROM raw_multi_platform_posts
        ORDER BY timestamp
    """).fetchdf()
    con.close()
    return frame


def _store_run(con, model_id: int, task: str, train_rows: int, test_rows: int,
               metrics: dict[str, float], hyperparameters: dict) -> None:
    run_id = con.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM model_run").fetchone()[0]
    con.execute("""
        INSERT INTO model_run
            (run_id, model_id, source_id, task_type, hyperparameters,
             train_rows, test_rows, split_seed)
        VALUES (?, ?, 8, ?, ?, ?, ?, 42)
    """, [run_id, model_id, task, json.dumps(hyperparameters), train_rows, test_rows])
    next_metric = con.execute("SELECT COALESCE(MAX(metric_id), 0) + 1 FROM model_metric").fetchone()[0]
    for offset, (name, value) in enumerate(metrics.items()):
        con.execute("""
            INSERT INTO model_metric (metric_id, run_id, metric_name, metric_value)
            VALUES (?, ?, ?, ?)
        """, [next_metric + offset, run_id, name, float(value)])


def benchmark() -> dict[str, int]:
    frame = _load_data()
    if len(frame) < 100:
        raise ValueError("Le corpus principal est trop petit pour un benchmark fiable.")
    split = int(len(frame) * 0.8)
    train = frame.iloc[:split]
    test = frame.iloc[split:]
    x_train, x_test = train[FEATURES], test[FEATURES]
    preprocessor = _preprocessor()
    con = duckdb.connect(str(DB_PATH))
    con.execute("DELETE FROM model_metric WHERE run_id IN (SELECT run_id FROM model_run WHERE source_id = 8)")
    con.execute("DELETE FROM model_run WHERE source_id = 8")
    results = []

    target = "log_engagement"
    y_train = train["total_engagement"].clip(lower=0).apply(lambda value: __import__("math").log1p(value))
    y_test = test["total_engagement"].clip(lower=0).apply(lambda value: __import__("math").log1p(value))
    regressors = [
        (10, "dummy", DummyRegressor(strategy="median")),
        (8, "ridge", Ridge(alpha=1.0)),
        (9, "random_forest", RandomForestRegressor(n_estimators=80, random_state=42, n_jobs=-1, max_depth=16)),
    ]
    for model_id, name, estimator in regressors:
        pipeline = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
        pipeline.fit(x_train, y_train)
        prediction = pipeline.predict(x_test)
        metrics = {
            "mae": mean_absolute_error(y_test, prediction),
            "rmse": mean_squared_error(y_test, prediction) ** 0.5,
            "r2": r2_score(y_test, prediction),
        }
        _store_run(con, model_id, "engagement", len(train), len(test), metrics, {"model": name, "target": target})
        results.append(("engagement", name, metrics))

    train_thresholds = train.groupby("platform")["viral_coefficient"].quantile(0.90)
    threshold = frame["platform"].map(train_thresholds)
    frame["viral"] = (frame["viral_coefficient"] >= threshold).astype(int)
    train = frame.iloc[:split]
    test = frame.iloc[split:]
    classifiers = [
        (1, "dummy", DummyClassifier(strategy="prior", random_state=42)),
        (2, "logistic_regression", LogisticRegression(max_iter=500, class_weight="balanced")),
        (3, "random_forest", RandomForestClassifier(n_estimators=80, random_state=42, n_jobs=-1, max_depth=16, class_weight="balanced")),
    ]
    for model_id, name, estimator in classifiers:
        pipeline = Pipeline([("preprocessor", _preprocessor()), ("model", estimator)])
        pipeline.fit(train[FEATURES], train["viral"])
        prediction = pipeline.predict(test[FEATURES])
        probabilities = pipeline.predict_proba(test[FEATURES])[:, 1]
        metrics = {
            "f1_viral": f1_score(test["viral"], prediction, zero_division=0),
            "balanced_accuracy": balanced_accuracy_score(test["viral"], prediction),
            "precision_viral": precision_score(test["viral"], prediction, zero_division=0),
            "recall_viral": recall_score(test["viral"], prediction, zero_division=0),
            "pr_auc": average_precision_score(test["viral"], probabilities),
        }
        _store_run(con, model_id, "virality", len(train), len(test), metrics, {"model": name, "threshold": "p90_platform"})
        results.append(("virality", name, metrics))
    con.close()
    _write_report(results, len(train), len(test))
    print(f"Benchmark termine : {len(results)} runs, train={len(train):,}, test={len(test):,}")
    return {"runs": len(results), "train": len(train), "test": len(test)}


def _load_sentiment_corpora(max_rows: int) -> pd.DataFrame:
    """Charge les corpus français et anglais avec des labels communs."""
    french = pd.read_csv(
        Path("data/raw/french_tweets.csv"), usecols=["label", "text"]
    ).dropna()
    french["language"] = "fr"
    french["label"] = french["label"].astype(str).map({"0": "negative", "1": "positive"})

    english = pd.read_csv(
        Path("data/raw/Sentiment140.csv"),
        encoding="latin-1",
        header=None,
        names=["polarity", "tweet_id", "tweet_date", "flag", "user_handle", "text"],
        usecols=["polarity", "text"],
    ).dropna()
    english["language"] = "en"
    english["label"] = english["polarity"].astype(str).map({"0": "negative", "4": "positive"})
    english = english.drop(columns=["polarity"])

    frames = []
    for corpus in (french, english):
        corpus = corpus.dropna(subset=["label", "text"])
        if len(corpus) > max_rows:
            corpus, _ = train_test_split(
                corpus, train_size=max_rows, random_state=42, stratify=corpus["label"]
            )
        frames.append(corpus[["text", "label", "language"]])
    return pd.concat(frames, ignore_index=True)


def benchmark_sentiment(max_rows: int = 100_000) -> dict[str, int]:
    """Compare deux modèles NLP sur des corpus français et anglais."""
    frame = _load_sentiment_corpora(max_rows)
    if frame["label"].nunique() < 2:
        raise ValueError("Le corpus sentiment doit contenir au moins deux classes.")
    train, test = train_test_split(
        frame, test_size=0.2, random_state=42, stratify=frame["label"]
    )
    vectorizer = TfidfVectorizer(
        max_features=80_000,
        ngram_range=(1, 2),
        min_df=3,
        sublinear_tf=True,
    )
    x_train = vectorizer.fit_transform(train["text"])
    x_test = vectorizer.transform(test["text"])
    con = duckdb.connect(str(DB_PATH))
    con.execute("DELETE FROM model_metric WHERE run_id IN (SELECT run_id FROM model_run WHERE source_id = 3 AND task_type = 'sentiment')")
    con.execute("DELETE FROM model_run WHERE source_id = 3 AND task_type = 'sentiment'")
    results = []
    models = [
        (11, "tfidf_logistic", LogisticRegression(max_iter=300, class_weight="balanced")),
        (12, "tfidf_linear_svm", LinearSVC(class_weight="balanced")),
    ]
    for model_id, name, estimator in models:
        estimator.fit(x_train, train["label"])
        prediction = estimator.predict(x_test)
        metrics = {
            "f1_macro": f1_score(test["label"], prediction, average="macro"),
            "balanced_accuracy": balanced_accuracy_score(test["label"], prediction),
            "precision_macro": precision_score(test["label"], prediction, average="macro", zero_division=0),
            "recall_macro": recall_score(test["label"], prediction, average="macro", zero_division=0),
        }
        for language in ("fr", "en"):
            mask = test["language"].to_numpy() == language
            if mask.any():
                metrics[f"f1_macro_{language}"] = f1_score(
                    test.loc[mask, "label"], prediction[mask], average="macro"
                )
                metrics[f"balanced_accuracy_{language}"] = balanced_accuracy_score(
                    test.loc[mask, "label"], prediction[mask]
                )
        _store_run_for_source(
            con, model_id, 3, "sentiment", len(train), len(test), metrics,
            {
                "model": name,
                "vectorizer": "tfidf",
                "max_features": 80_000,
                "languages": ["fr", "en"],
            },
        )
        results.append((name, metrics))
        if model_id == 11:
            model_path = DOC_DIR.parent / "data" / "models" / "sentiment_tfidf_logistic.joblib"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {"vectorizer": vectorizer, "classifier": estimator, "labels": sorted(frame["label"].unique())},
                model_path,
            )
            matrix = confusion_matrix(test["label"], prediction, labels=sorted(frame["label"].unique()))
            confusion_path = DOC_DIR / "sentiment_confusion_matrix.csv"
            pd.DataFrame(matrix, index=sorted(frame["label"].unique()),
                         columns=sorted(frame["label"].unique())).to_csv(confusion_path)
    con.close()
    output = DOC_DIR / "sentiment_benchmark_report.md"
    lines = [
        "# Benchmark sentiment",
        "",
        f"Echantillon stratifie : {len(frame):,} lignes; train={len(train):,}; test={len(test):,}.",
        "",
        "| Langue | Lignes |",
        "|---|---:|",
        *[
            f"| {language} | {count:,} |"
            for language, count in frame["language"].value_counts().sort_index().items()
        ],
        "",
        "| Modele | Metriques |",
        "|---|---|",
    ]
    for name, metrics in results:
        lines.append(f"| {name} | " + "; ".join(f"{k}={v:.4f}" for k, v in metrics.items()) + " |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Benchmark sentiment termine : {len(results)} runs, {len(frame):,} lignes")
    prediction_count = predict_sentiment_corpus()
    return {"runs": len(results), "rows": len(frame), "predictions": prediction_count}


def _score_predictions(artifact, texts):
    """Return labels and a stable positive/negative score mapping."""
    features = artifact["vectorizer"].transform(texts)
    classifier = artifact["classifier"]
    predictions = classifier.predict(features)
    probabilities = classifier.predict_proba(features)
    classes = list(classifier.classes_)
    result = []
    for label, probability in zip(predictions, probabilities):
        scores = {str(name): float(value) for name, value in zip(classes, probability)}
        result.append((str(label), scores, float(max(probability))))
    return result


def predict_sentiment_corpus(
    max_rows: int = 100_000,
    batch_size: int = 5_000,
    resume: bool = True,
    source_ids: tuple[int, ...] = (2, 3),
) -> int:
    """Prédit les corpus français et anglais avec le modèle commun.

    ``resume=True`` (par défaut) ne touche pas aux prédictions déjà présentes.
    Chaque lot est validé séparément : une interruption peut donc reprendre au
    lot suivant sans recalculer ni dupliquer les lots précédents.
    """
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro")
    model_path = DOC_DIR.parent / "data" / "models" / "sentiment_tfidf_logistic.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Modele sentiment absent : {model_path}")
    con = duckdb.connect(str(DB_PATH))
    if not resume:
        con.execute(
            "DELETE FROM fact_sentiment_prediction WHERE model_id = 11 "
            "AND post_id IN (SELECT post_id FROM fact_social_post WHERE source_id IN (?, ?))",
            list(source_ids),
        )
    rows = con.execute("""
        SELECT post_id, text_content
        FROM fact_social_post
        WHERE source_id IN (?, ?) AND text_content IS NOT NULL
          AND (? = false OR NOT EXISTS (
              SELECT 1 FROM fact_sentiment_prediction p
              WHERE p.post_id = fact_social_post.post_id AND p.model_id = 11
          ))
        ORDER BY post_id
        LIMIT ?
    """, [*source_ids, resume, max_rows * len(source_ids)]).fetchall()
    if not rows:
        con.close()
        print("Aucune publication française ou anglaise à prédire.")
        return 0
    artifact = joblib.load(model_path)
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        scored = _score_predictions(artifact, [row[1] for row in batch])
        next_id = con.execute(
            "SELECT COALESCE(MAX(prediction_id), 0) + 1 FROM fact_sentiment_prediction"
        ).fetchone()[0]
        values = []
        for offset, (row, (label, scores, confidence)) in enumerate(zip(batch, scored)):
            values.append((
                next_id + offset, row[0], 11, label,
                scores.get("1", 0.0), scores.get("0", 0.0), scores.get("neutral", 0.0),
                confidence, False,
            ))
        con.executemany("""
            INSERT INTO fact_sentiment_prediction
                (prediction_id, post_id, model_id, sentiment_label,
                 positive_probability, negative_probability, neutral_probability,
                 confidence, is_human_validated)
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM fact_sentiment_prediction
                WHERE post_id = ? AND model_id = ?
            )
        """, [value + (value[1], value[2]) for value in values])
        inserted += len(values)
    con.close()
    print(f"Predictions sentiment inserees : {inserted:,} (lots de {batch_size:,})")
    return inserted


def predict_french_tweets(
    max_rows: int = 100_000,
    batch_size: int = 5_000,
    resume: bool = True,
    source_id: int = 3,
) -> int:
    """Compatibilité avec l'ancien point d'entrée français."""
    return predict_sentiment_corpus(max_rows, batch_size, resume, (source_id,))


def predict_structured_corpus(
    input_path, output_path, text_column: str = "text", batch_size: int = 5_000
) -> int:
    """Prédit un corpus CSV/JSON/JSONL/Parquet déjà structuré.

    Les colonnes originales sont conservées et les scores sont ajoutés dans
    ``output_path``. Cette voie ne dépend pas de la base et ne modifie pas le
    comportement historique du warehouse.
    """
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(input_path)
    elif input_path.suffix.lower() in {".json", ".jsonl"}:
        frame = pd.read_json(input_path, lines=input_path.suffix.lower() == ".jsonl")
    else:
        frame = pd.read_csv(input_path)
    if text_column not in frame.columns:
        raise ValueError(f"Colonne texte absente du corpus : {text_column}")
    model_path = DOC_DIR.parent / "data" / "models" / "sentiment_tfidf_logistic.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Modele sentiment absent : {model_path}")
    artifact = joblib.load(model_path)
    texts = frame[text_column].fillna("").astype(str).tolist()
    scored = []
    for start in range(0, len(texts), batch_size):
        scored.extend(_score_predictions(artifact, texts[start:start + batch_size]))
    frame["sentiment_label"] = [item[0] for item in scored]
    frame["positive_probability"] = [item[1].get("1", 0.0) for item in scored]
    frame["negative_probability"] = [item[1].get("0", 0.0) for item in scored]
    frame["confidence"] = [item[2] for item in scored]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".parquet":
        frame.to_parquet(output_path, index=False)
    elif output_path.suffix.lower() in {".json", ".jsonl"}:
        frame.to_json(output_path, orient="records", lines=output_path.suffix.lower() == ".jsonl", force_ascii=False)
    else:
        frame.to_csv(output_path, index=False)
    return len(frame)


def _store_run_for_source(con, model_id, source_id, task, train_rows, test_rows, metrics, hyperparameters):
    run_id = con.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM model_run").fetchone()[0]
    con.execute("""
        INSERT INTO model_run
            (run_id, model_id, source_id, task_type, hyperparameters, train_rows, test_rows, split_seed)
        VALUES (?, ?, ?, ?, ?, ?, ?, 42)
    """, [run_id, model_id, source_id, task, json.dumps(hyperparameters), train_rows, test_rows])
    next_metric = con.execute("SELECT COALESCE(MAX(metric_id), 0) + 1 FROM model_metric").fetchone()[0]
    for offset, (name, value) in enumerate(metrics.items()):
        con.execute(
            "INSERT INTO model_metric (metric_id, run_id, metric_name, metric_value) VALUES (?, ?, ?, ?)",
            [next_metric + offset, run_id, name, float(value)],
        )


def _write_report(results, train_rows: int, test_rows: int) -> Path:
    output = DOC_DIR / "ml_benchmark_report.md"
    lines = [
        "# Benchmark ML initial",
        "",
        f"Decoupage chronologique : {train_rows:,} train, {test_rows:,} test.",
        "",
        "| Tache | Modele | Metriques |",
        "|---|---|---|",
    ]
    for task, model, metrics in results:
        values = "; ".join(f"{key}={value:.4f}" for key, value in metrics.items())
        lines.append(f"| {task} | {model} | {values} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
