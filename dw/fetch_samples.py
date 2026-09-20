"""
Échantillonnage par streaming depuis Hugging Face — récupère un sous-ensemble
d'un dataset SANS le télécharger en entier, puis l'enregistre au format CSV
avec les colonnes déjà alignées sur config/mapping.yaml.

IMPORTANT — statut de vérification des configurations ci-dessous :
Les noms de dataset et de champs ont été vérifiés par recherche web (pages
"Dataset card" Hugging Face, septembre 2026) — pas par un appel réseau réel
depuis cet environnement de développement (accès à huggingface.co non
disponible ici). Vérifie que rien n'a changé côté Hugging Face avant un
vrai run à grande échelle, et commence toujours par un petit `--n 100`.

Usage :
    python manage.py fetch-sample --source raw_allocine --n 20000
    python manage.py fetch-sample --source raw_amazon_reviews --n 20000
    python manage.py fetch-sample --source raw_reddit --n 20000
"""
import pandas as pd
from datetime import datetime, timezone
from dw.paths import DATA_RAW_DIR


def _to_iso_datetime(value):
    """
    Convertit une valeur de date en ISO string, quel que soit son format
    d'origine. Nécessaire car la librairie `datasets` ne retourne pas
    toujours le même type pour une colonne de date selon le dataset : parfois
    un epoch (int/float, secondes depuis 1970), parfois déjà un objet
    datetime.datetime (si le parquet source stocke un vrai type timestamp).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    return str(value)  # déjà une chaîne, ou type inattendu : on la laisse telle quelle

# Chaque entrée : quel dataset HF streamer, quel split, comment renommer ses
# colonnes vers notre schéma, et quels champs manquants synthétiser.
SAMPLE_CONFIGS = {
    "raw_allocine": {
        "hf_dataset": "tblard/allocine",
        "config_name": None,
        "split": "train",
        "field_map": {"review": "text"},
        "synthesize": {
            "review_id": lambda row, idx: f"al_{idx}",
            "rating": lambda row, idx: 5.0 if row.get("label") == 1 else 1.0,  # label binaire -> échelle approximative
            "review_date": lambda row, idx: None,  # absent du dataset source
        },
        "output_file": "allocine_hf_sample.csv",
    },
    "raw_amazon_reviews": {
        # Vérifié par recherche web (09/2026) : dépôt renommé fancyzhx/amazon_polarity
        # (l'ancien nom "amazon_polarity" reste utilisable en alias). Champs réels
        # confirmés : 'title', 'content', 'label' (0=négatif, 1=positif).
        "hf_dataset": "fancyzhx/amazon_polarity",
        "config_name": None,
        "split": "train",
        "field_map": {"content": "text"},
        "synthesize": {
            "review_id": lambda row, idx: f"az_{idx}",
            "product_id": lambda row, idx: None,       # absent de cette version du dataset
            "star_rating": lambda row, idx: 5 if row.get("label") == 1 else 1,
            "review_date": lambda row, idx: None,       # absent de cette version du dataset
            "verified_purchase": lambda row, idx: None,  # absent de cette version du dataset
        },
        "output_file": "amazon_reviews_hf_sample.csv",
    },
    "raw_reddit": {
        # Vérifié par recherche web (09/2026) : les posts et les commentaires sont
        # dans deux CONFIGURATIONS séparées de ce dataset ('posts' / 'comments'),
        # pas dans le même split. On cible 'comments' car ça correspond à notre
        # cas d'usage (analyse de commentaires). Champs réels confirmés pour les
        # commentaires : 'id', 'subreddit.name', 'body', 'score', 'created_utc'
        # (timestamp UTC en secondes, pas une date lisible -> converti ci-dessous).
        "hf_dataset": "SocialGrep/the-reddit-dataset-dataset",
        "config_name": "comments",
        "split": "train",
        "field_map": {"id": "comment_id", "subreddit.name": "subreddit", "body": "text", "score": "score"},
        "synthesize": {
            "created_at": lambda row, idx: _to_iso_datetime(row.get("created_utc")),
        },
        "output_file": "reddit_hf_sample.csv",
    },
}


def fetch_sample(source_key: str, n: int = 20000, shuffle_buffer: int = None, seed: int = 42,
                  _load_dataset_fn=None) -> str:
    """
    Streame `n` lignes depuis Hugging Face et les enregistre en CSV dans data/raw/.
    `_load_dataset_fn` permet d'injecter une fonction de remplacement pour les tests
    (sans réseau) — ne pas fournir en usage normal.

    `shuffle_buffer` : par défaut, adapté automatiquement à `n` (environ 10x, plafonné
    à 10 000) plutôt que fixé à une grande valeur constante. Un gros buffer force la
    librairie à précharger beaucoup plus de données que nécessaire même pour un petit
    échantillon de test — ce qui peut provoquer des coupures réseau évitables sur une
    connexion instable. Augmente `shuffle_buffer` toi-même si tu veux un mélange plus
    aléatoire sur un run à grande échelle, une fois la connexion confirmée stable.
    """
    if source_key not in SAMPLE_CONFIGS:
        raise ValueError(f"Source inconnue : {source_key}. Options : {list(SAMPLE_CONFIGS)}")

    if shuffle_buffer is None:
        shuffle_buffer = min(max(n * 10, 200), 10_000)

    cfg = SAMPLE_CONFIGS[source_key]

    if _load_dataset_fn is None:
        from datasets import load_dataset
        _load_dataset_fn = load_dataset

    print(f"→ Connexion en streaming à '{cfg['hf_dataset']}'"
          f"{' (config: ' + cfg['config_name'] + ')' if cfg.get('config_name') else ''} "
          f"(aucun téléchargement complet)...")
    ds = _load_dataset_fn(cfg["hf_dataset"], name=cfg.get("config_name"), split=cfg["split"], streaming=True)
    ds = ds.shuffle(seed=seed, buffer_size=shuffle_buffer)

    rows = []
    for idx, row in enumerate(ds.take(n)):
        mapped = {}
        for hf_field, our_field in cfg["field_map"].items():
            mapped[our_field] = row.get(hf_field)
        for our_field, synth_fn in cfg["synthesize"].items():
            mapped[our_field] = synth_fn(row, idx)
        rows.append(mapped)

    df = pd.DataFrame(rows)
    DATA_RAW_DIR.mkdir(exist_ok=True, parents=True)
    out_path = DATA_RAW_DIR / cfg["output_file"]
    df.to_csv(out_path, index=False)

    print(f"✓ {len(df):,} lignes échantillonnées → {out_path}")
    print(f"✓ Prochaine étape : python manage.py load --file {cfg['output_file']} --table {source_key}")
    return str(out_path)


def run(source: str, n: int = 20000):
    fetch_sample(source, n=n)
