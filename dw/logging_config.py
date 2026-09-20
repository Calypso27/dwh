"""Logging fichier — indispensable pour une tâche planifiée : personne ne
regarde une console à 3h du matin. Chaque exécution laisse une trace dans
logs/pipeline.log, en plus de la table pipeline_runs en base."""
import logging
from dw.paths import ROOT

LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"


def get_logger() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    logger = logging.getLogger("dw.pipeline")
    if logger.handlers:
        return logger  # déjà configuré, éviter les doublons de handlers

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
