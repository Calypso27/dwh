# Dictionnaire de données — social_analytics_dw

Généré automatiquement depuis `config/schema.yaml` le 2026-09-04 13:12. Ne pas éditer à la main.


## Couche staging


### `raw_youtube_comments`
Export brut du dataset YouTube (scores de sentiment déjà calculés)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| comment_id | VARCHAR | — |  |
| video_id | VARCHAR | — |  |
| channel_id | VARCHAR | — |  |
| sentiment_category | VARCHAR | — |  |
| sentiment_score | DOUBLE | — |  |
| likes | INTEGER | — |  |
| published_at | TIMESTAMP | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

### `raw_sentiment140`
1.6M tweets réels annotés positif/négatif (Sentiment140)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| tweet_id | BIGINT | — |  |
| text | VARCHAR | — |  |
| polarity | INTEGER | — |  |
| tweet_date | TIMESTAMP | — |  |
| user_handle | VARCHAR | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

### `raw_twitter_fr`
1.5M tweets réels en français avec sentiment

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| tweet_id | BIGINT | — |  |
| text | VARCHAR | — |  |
| sentiment | VARCHAR | — |  |
| tweet_date | TIMESTAMP | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

### `raw_allocine`
Critiques réelles Allociné (texte long, notation)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| review_id | VARCHAR | — |  |
| text | VARCHAR | — |  |
| rating | DOUBLE | — |  |
| review_date | TIMESTAMP | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

### `raw_reddit`
Commentaires réels Reddit, diversité de communautés/sujets

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| comment_id | VARCHAR | — |  |
| subreddit | VARCHAR | — |  |
| text | VARCHAR | — |  |
| score | INTEGER | — |  |
| created_at | TIMESTAMP | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

### `raw_amazon_reviews`
Nouveau dataset ajouté après coup — avis produits réels avec note et texte

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| review_id | VARCHAR | — |  |
| product_id | VARCHAR | — |  |
| text | VARCHAR | — |  |
| star_rating | INTEGER | — |  |
| review_date | TIMESTAMP | — |  |
| verified_purchase | BOOLEAN | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

## Warehouse — Dimensions


### `dim_source_dataset`
Provenance de chaque donnée : institution, entreprise, dataset public...

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| source_id | INTEGER | PK |  |
| source_name | VARCHAR | NOT NULL |  |
| provenance | VARCHAR | — | public_dataset | saint_jean | ... |
| language | VARCHAR | — |  |
| license | VARCHAR | — |  |
| is_synthetic | BOOLEAN | — | true si données générées, jamais utilisé pour validation |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `dim_platform`
Réseau social ou plateforme d'origine du contenu

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| platform_id | INTEGER | PK |  |
| platform_name | VARCHAR | NOT NULL |  |
| content_type | VARCHAR | — | texte | vidéo | image | mixte |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `dim_model`
Modèle ou algorithme utilisé pour une prédiction

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| model_id | INTEGER | PK |  |
| model_name | VARCHAR | NOT NULL |  |
| model_version | VARCHAR | — |  |
| model_family | VARCHAR | — | baseline | linear | tree_ensemble | transformer |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `dim_user`
Comptes d'accès à la plateforme, avec rôle et périmètre (gestion des accès du cahier des charges)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| user_id | INTEGER | PK |  |
| username | VARCHAR | NOT NULL |  |
| hashed_password | VARCHAR | NOT NULL |  |
| role | VARCHAR | NOT NULL | institution_admin | scoped_admin |
| scope_source_id | INTEGER | FK → dim_source_dataset.source_id | NULL si institution_admin |
| is_active | BOOLEAN | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

## Warehouse — Faits


### `fact_social_post`
Publication ou commentaire, une ligne par version (SCD2)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| post_id | BIGINT | PK |  |
| source_id | INTEGER | FK → dim_source_dataset.source_id |  |
| platform_id | INTEGER | FK → dim_platform.platform_id |  |
| external_post_id | VARCHAR | — | identifiant dans le dataset d'origine |
| text_content | VARCHAR | — |  |
| published_at | TIMESTAMP | — |  |
| likes | INTEGER | — |  |
| comments | INTEGER | — |  |
| shares | INTEGER | — |  |
| views | INTEGER | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `fact_sentiment_prediction`
Une prédiction de sentiment pour un post, par un modèle donné

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| prediction_id | BIGINT | PK |  |
| post_id | BIGINT | FK → fact_social_post.post_id |  |
| model_id | INTEGER | FK → dim_model.model_id |  |
| sentiment_label | VARCHAR | — |  |
| positive_probability | DOUBLE | — |  |
| negative_probability | DOUBLE | — |  |
| neutral_probability | DOUBLE | — |  |
| confidence | DOUBLE | — |  |
| is_human_validated | BOOLEAN | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

## Warehouse — Suivi d'expériences ML


### `model_run`
Un essai d'entraînement/évaluation : quel algo, sur quelles données, comment

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| run_id | BIGINT | PK |  |
| model_id | INTEGER | FK → dim_model.model_id |  |
| source_id | INTEGER | FK → dim_source_dataset.source_id |  |
| task_type | VARCHAR | — | sentiment | virality | engagement |
| hyperparameters | VARCHAR | — | JSON sérialisé des hyperparamètres |
| train_rows | INTEGER | — |  |
| test_rows | INTEGER | — |  |
| split_seed | INTEGER | — |  |
| run_at | TIMESTAMP | — |  |

### `model_metric`
Résultat mesuré pour un run donné (F1, precision, recall, PR-AUC...)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| metric_id | BIGINT | PK |  |
| run_id | BIGINT | FK → model_run.run_id |  |
| metric_name | VARCHAR | NOT NULL |  |
| metric_value | DOUBLE | NOT NULL |  |
| class_label | VARCHAR | — | classe concernée si métrique par classe, sinon NULL |

## Warehouse — Contrôle qualité


### `dq_checks`
Journal des contrôles qualité exécutés à chaque chargement

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| check_id | BIGINT | PK |  |
| table_name | VARCHAR | NOT NULL |  |
| check_name | VARCHAR | NOT NULL | not_null | unique | schema_match | duplicate_rate |
| check_result | VARCHAR | — | PASS | FAIL | WARN |
| rows_checked | INTEGER | — |  |
| rows_failed | INTEGER | — |  |
| checked_at | TIMESTAMP | — |  |