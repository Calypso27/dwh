"""Prépare le dataset Facebook joint (commentaires + publications)."""
from pathlib import Path

import pandas as pd

from dw.paths import DATA_RAW_DIR


COMMENTS_FILE = "dataset_commentaires.csv"
PUBLICATIONS_FILE = "dataset_publications.csv"
OUTPUT_FILE = "dataset_facebook_joint.csv"


def combine(
    comments_file: str = COMMENTS_FILE,
    publications_file: str = PUBLICATIONS_FILE,
    output_file: str = OUTPUT_FILE,
) -> Path:
    """Joint chaque commentaire à sa publication et écrit un CSV de staging."""
    comments_path = DATA_RAW_DIR / comments_file
    publications_path = DATA_RAW_DIR / publications_file
    output_path = DATA_RAW_DIR / output_file

    comments = pd.read_csv(comments_path, sep=";")
    publications = pd.read_csv(publications_path, sep=";")

    required_comments = {"plateforme", "id_publication", "id_commentaire", "texte"}
    required_publications = {"plateforme", "id_publication", "texte"}
    missing_comments = required_comments - set(comments.columns)
    missing_publications = required_publications - set(publications.columns)
    if missing_comments or missing_publications:
        raise ValueError(
            "Colonnes manquantes — commentaires: "
            f"{sorted(missing_comments)}, publications: {sorted(missing_publications)}"
        )

    # Une publication doit être unique sur (plateforme, id_publication).
    publications = publications.drop_duplicates(
        subset=["plateforme", "id_publication"], keep="last"
    )
    publication_columns = [
        column for column in publications.columns
        if column not in {"plateforme", "id_publication", "texte"}
    ]
    publication_context = publications[
        ["plateforme", "id_publication", "texte"] + publication_columns
    ].rename(columns={"texte": "texte_publication"})

    joined = comments.merge(
        publication_context,
        on=["plateforme", "id_publication"],
        how="left",
        validate="many_to_one",
    )
    joined.to_csv(output_path, sep=";", index=False)
    print(f"Dataset joint écrit : {output_path} ({len(joined):,} lignes)")
    return output_path
