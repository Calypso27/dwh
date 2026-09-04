# saint_jean_dw — Data warehouse générique pour l'analyse de communautés sociales

Projet de mémoire M2 — plateforme générique d'analyse de réseaux sociaux et
de recommandation, validée d'abord sur des datasets publics (phase de
généralisation), puis appliquée à l'Institut Universitaire Saint Jean.

## Structure du projet

```
saint_jean_dw/
├── manage.py              ← point d'entrée unique, toutes les commandes passent par ici
├── requirements.txt
├── config/
│   └── schema.yaml        ← source de vérité : décrit toutes les tables
├── dw/                    ← code du package
│   ├── schema_generator.py
│   ├── warehouse.py
│   ├── seed.py
│   ├── loader.py
│   └── quality.py
├── sql/                   ← généré automatiquement, ne pas éditer à la main
├── docs/
│   └── data_dictionary.md ← généré automatiquement, réutilisable dans le mémoire
├── data/
│   ├── raw/                ← dépose ici tes fichiers CSV/Excel téléchargés
│   └── warehouse/          ← contient le fichier .duckdb (créé automatiquement)
└── tests/
```

## Installation (une seule fois)

```bash
pip install -r requirements.txt
```

## Mise en route rapide

```bash
python manage.py setup
```
Cette seule commande : génère le SQL depuis `config/schema.yaml`, crée la
base `data/warehouse/social_analytics_dw.duckdb`, et peuple les dimensions
de référence (sources, plateformes, modèles déjà identifiés).

## Utilisation courante

**Ajouter un nouveau dataset**
1. Ajoute un bloc `raw_xxx` dans `config/schema.yaml` (copie un bloc existant).
2. `python manage.py generate-schema`
3. `python manage.py init` (les nouvelles tables sont ajoutées, les
   existantes ne sont pas touchées)

**Charger un fichier**
```bash
# Dépose le fichier dans data/raw/, puis :
python manage.py load --file mon_fichier.csv --table raw_sentiment140
```

**Contrôler la qualité d'une table**
```bash
python manage.py check --table raw_sentiment140
```

**Voir l'état de la base en un coup d'œil**
```bash
python manage.py status
```

## Explorer la base directement en SQL

```bash
python3 -c "import duckdb; duckdb.connect('data/warehouse/social_analytics_dw.duckdb').sql('SELECT * FROM dq_checks').show()"
```
Ou installe le CLI DuckDB et lance `duckdb data/warehouse/social_analytics_dw.duckdb`.

## API REST

Lancer l'API (après `python manage.py setup`) :
```bash
uvicorn api.main:app --reload
```
Documentation interactive auto-générée : http://localhost:8000/docs

### Endpoints disponibles

| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET | `/health` | Vérifie que l'API répond | non |
| POST | `/auth/login` | Récupère un token JWT (form `username`/`password`) | non |
| GET | `/auth/me` | Infos de l'utilisateur connecté | oui |
| GET | `/posts` | Liste les publications (filtres `source_id`, `platform_id`, pagination) | non |
| GET | `/posts/{id}` | Détail d'une publication | non |
| GET | `/posts/scoped/me` | Liste restreinte selon le rôle (démo des 2 niveaux d'admin) | oui |
| GET | `/model-runs` | Liste les essais de modèles ML | non |
| GET | `/model-runs/{id}/metrics` | Métriques d'un essai (F1, PR-AUC...) | non |
| GET | `/dq-checks` | Journal des contrôles qualité | non |

### Comptes de démonstration (MVP — à remplacer par une vraie table `users`)

| Utilisateur | Mot de passe | Rôle | Portée |
|---|---|---|---|
| `admin_global` | `admin123` | `institution_admin` | Voit toutes les sources |
| `admin_sji` | `sji123` | `scoped_admin` | Voit uniquement `source_id = 2` |

### Tester rapidement avec curl

```bash
# Se connecter
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin_global&password=admin123"

# Utiliser le token reçu
curl http://localhost:8000/posts/scoped/me \
  -H "Authorization: Bearer <TOKEN>"
```

## Frontend Angular

Dans `frontend/` — application Angular 18 (composants standalone), testée
avec compilation réelle (`ng build`) et démarrage réel du serveur de dev
en parallèle de l'API, requêtes HTTP vérifiées de bout en bout.

```bash
cd frontend
npm install
ng serve
```
Puis ouvre http://localhost:4200 (l'API doit tourner en parallèle sur le
port 8000 — voir section API REST ci-dessus).

**Ce qui est câblé et testé :**
- Page de connexion (`/login`) → appelle `POST /auth/login`, stocke le token JWT
- Intercepteur HTTP → attache automatiquement le token à chaque requête sortante
- Dashboard (`/dashboard`) → affiche `GET /posts/scoped/me` (liste qui change
  selon le rôle connecté) et `GET /model-runs`
- CORS déjà configuré côté API pour accepter `http://localhost:4200`

## Échantillonnage sans téléchargement complet (gros datasets)

Pour les datasets trop volumineux à télécharger entièrement (Allociné,
Amazon Reviews, Reddit), un échantillon peut être streamé directement
depuis Hugging Face — seules les lignes prélevées transitent, jamais le
fichier complet :

```bash
python manage.py fetch-sample --source raw_allocine --n 20000
python manage.py load --file allocine_hf_sample.csv --table raw_allocine
```

⚠️ **Statut de vérification** : les 3 configurations (`raw_allocine`,
`raw_amazon_reviews`, `raw_reddit`) ont été vérifiées par recherche web
(pages "Dataset card" Hugging Face, septembre 2026) — noms de dataset et de
champs confirmés à cette date. L'appel réseau réel n'a pas pu être testé
dans cet environnement de développement (accès à huggingface.co non
disponible ici) : commence toujours par `--n 100` avant un run à grande
échelle, au cas où quelque chose aurait changé côté Hugging Face depuis.

Point notable sur Reddit : le dataset sépare posts et commentaires dans
des **configurations distinctes** (`comments` vs `posts`) — déjà pris en
compte dans `dw/fetch_samples.py` (`config_name: "comments"`).

## Transformation staging → warehouse (SCD2)

```bash
python manage.py transform --source raw_reddit   # une seule source
python manage.py transform                        # toutes les sources déclarées
```

Implémente une vraie historisation SCD2 : une ligne staging jamais vue crée
une nouvelle version ; une ligne dont le contenu a changé (texte, likes...)
expire l'ancienne version et en insère une nouvelle ; une ligne identique
est ignorée (relancer plusieurs fois est sans danger). Le mapping
staging → `fact_social_post` par source est déclaré dans `config/mapping.yaml`.

## Tests automatisés

```bash
pytest tests/ -v
```
10 tests couvrant : génération de schéma, contraintes FK, idempotence du
seed, insertion/mise à jour/no-op du transform SCD2, détection des
problèmes de qualité (nulls, valeurs négatives), et hashage des mots de
passe.

## Support PostgreSQL

Le générateur produit aussi le SQL pour PostgreSQL (`sql/postgres/`), testé
contre une instance réelle (contraintes FK comprises). Bascule prévue pour
la couche applicative en production, DuckDB restant l'environnement
d'expérimentation/sandbox.

```bash
psql -U <user> -d <db> -f sql/postgres/01_staging.sql
psql -U <user> -d <db> -f sql/postgres/02_warehouse.sql
```

## Ce qui reste (limites assumées, à mentionner dans le mémoire)

- **Couche analytique** (agrégats/KPIs matérialisés) — identifiée dans la
  vue d'architecture globale, pas encore construite.
- **Vraies données publiques chargées** — le circuit est prouvé avec des
  données de test ; les 5 datasets publics identifiés doivent être
  téléchargés (Kaggle/Hugging Face) et chargés via `manage.py load`.
- **Orchestration** — toutes les commandes s'exécutent manuellement, pas de
  planification automatique (acceptable pour un mémoire, à noter comme
  perspective d'industrialisation).
- **Gestion des utilisateurs** — création/modification de comptes toujours
  via script (`dw/seed.py`), pas d'endpoint API dédié à l'administration
  des comptes.

## Principe de conception

Un seul schéma générique (`config/schema.yaml`), instancié deux fois dans
le temps : une fois maintenant pour valider l'approche sur des données
publiques (phase de généralisation), une fois plus tard pour Saint Jean
(étude de cas), sans modification du générateur — seulement de nouvelles
lignes de configuration et une nouvelle exécution de `setup`.
