"""Lecture des profils de chargement déclaratifs (config/load_profiles.yaml)."""
import yaml
from dw.paths import CONFIG_DIR

PROFILES_FILE = CONFIG_DIR / "load_profiles.yaml"


def get_profile(table: str) -> dict:
    """Retourne le profil déclaré pour cette table, ou {} si aucun n'existe."""
    return all_profiles().get(table, {})


def all_profiles() -> dict:
    """Retourne {table: profil} pour TOUTES les tables ayant un profil déclaré."""
    if not PROFILES_FILE.exists():
        return {}
    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("profiles") or {}
