"""Audit reproductible des datasets presents dans data/raw."""
from pathlib import Path

import pandas as pd

from dw.paths import DATA_RAW_DIR, DOC_DIR


DATASETS = {
    "multi_platform_social_sentiment_evolution.csv": {
        "role": "principal: engagement, viralite, sentiment fourni, toxicite",
        "sep": ",",
        "date_columns": ["timestamp"],
    },
    "Sentiment140.csv": {
        "role": "NLP: tweets anglais etiquetes",
        "sep": ",",
        "encoding": "latin-1",
        "header": None,
        "names": ["polarity", "tweet_id", "tweet_date", "flag", "user_handle", "text"],
        "date_columns": ["tweet_date"],
    },
    "french_tweets.csv": {
        "role": "NLP: tweets francais etiquetes",
        "sep": ",",
    },
    "youtube-comments-sentiment.csv": {
        "role": "NLP: commentaires YouTube etiquetes",
        "sep": ",",
        "date_columns": ["PublishedAt"],
    },
    "allocine_hf_sample.csv": {
        "role": "NLP: critiques francaises",
        "sep": ",",
        "date_columns": ["review_date"],
    },
    "amazon_reviews_hf_sample.csv": {
        "role": "NLP: avis produits",
        "sep": ",",
        "date_columns": ["review_date"],
    },
    "reddit_hf_sample.csv": {
        "role": "NLP: commentaires Reddit",
        "sep": ",",
        "date_columns": ["created_at"],
    },
    "dataset_publications.csv": {
        "role": "social: publications Facebook",
        "sep": ";",
        "date_columns": ["date_publication"],
    },
    "dataset_commentaires.csv": {
        "role": "social: commentaires Facebook",
        "sep": ";",
        "date_columns": ["date_commentaire"],
    },
    "dataset_facebook_joint.csv": {
        "role": "social: commentaires Facebook enrichis",
        "sep": ";",
        "date_columns": ["date_commentaire", "date_publication"],
    },
}


def _read_chunks(path: Path, config: dict):
    kwargs = {
        "sep": config["sep"],
        "encoding": config.get("encoding", "utf-8"),
        "chunksize": 50_000,
    }
    if "header" in config and config["header"] is None:
        kwargs["header"] = None
        kwargs["names"] = config["names"]
    return pd.read_csv(path, **kwargs)


def audit() -> list[dict]:
    results = []
    for filename, config in DATASETS.items():
        path = DATA_RAW_DIR / filename
        if not path.exists():
            results.append({"file": filename, "status": "MISSING", "role": config["role"]})
            continue

        rows = 0
        missing = {}
        date_ranges = {}
        columns = None
        for chunk in _read_chunks(path, config):
            rows += len(chunk)
            columns = list(chunk.columns)
            for column in columns:
                missing[column] = missing.get(column, 0) + int(chunk[column].isna().sum())
            for column in config.get("date_columns", []):
                if column in chunk:
                    parsed = pd.to_datetime(chunk[column], errors="coerce", utc=True)
                    values = parsed.dropna()
                    if not values.empty:
                        current = date_ranges.get(column)
                        bounds = (values.min().isoformat(), values.max().isoformat())
                        date_ranges[column] = (
                            min(current[0], bounds[0]) if current else bounds[0],
                            max(current[1], bounds[1]) if current else bounds[1],
                        )

        results.append({
            "file": filename,
            "status": "OK",
            "role": config["role"],
            "rows": rows,
            "columns": len(columns or []),
            "column_names": columns or [],
            "missing": missing,
            "date_ranges": date_ranges,
        })
    return results


def write_report(results: list[dict]) -> Path:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    output = DOC_DIR / "data_audit_report.md"
    lines = [
        "# Audit des datasets",
        "",
        "Audit genere automatiquement depuis `data/raw/`.",
        "",
        "| Fichier | Statut | Lignes | Colonnes | Role analytique |",
        "|---|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result['file']}` | {result['status']} | "
            f"{result.get('rows', 0):,} | {result.get('columns', 0)} | {result['role']} |"
        )
    lines += [
        "",
        "## Regle d'utilisation",
        "",
        "- Le corpus principal sert aux modeles d'engagement et de viralite.",
        "- Les corpus textuels servent principalement a l'entrainement et a la validation NLP.",
        "- Les analyses combinees doivent conserver la provenance et ne comparer que des metriques compatibles.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def run() -> list[dict]:
    results = audit()
    output = write_report(results)
    for result in results:
        print(
            f"{result['file']}: {result['status']} "
            f"{result.get('rows', 0):,} lignes, role={result['role']}"
        )
    print(f"Rapport ecrit : {output}")
    return results
