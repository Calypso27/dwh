# Dictionnaire de données — social_analytics_dw

Généré automatiquement depuis `config/schema.yaml` le 2026-09-20 09:31. Ne pas éditer à la main.


## Couche staging


### `raw_youtube_comments`
Export brut du dataset YouTube (texte réel + scores de sentiment déjà calculés)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| comment_id | VARCHAR | — |  |
| video_id | VARCHAR | — |  |
| channel_id | VARCHAR | — |  |
| text | VARCHAR | — |  |
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

### `raw_facebook_comments`
Commentaires Facebook enrichis avec le contexte de leur publication

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| plateforme | VARCHAR | — |  |
| id_commentaire | VARCHAR | — |  |
| id_publication | VARCHAR | — |  |
| pseudo_auteur | VARCHAR | — |  |
| texte | VARCHAR | — |  |
| date_commentaire | TIMESTAMP | — |  |
| langue | VARCHAR | — |  |
| texte_publication | VARCHAR | — |  |
| date_publication | TIMESTAMP | — |  |
| type_contenu | VARCHAR | — |  |
| ecole | VARCHAR | — |  |
| likes | INTEGER | — |  |
| partages | INTEGER | — |  |
| vues | INTEGER | — |  |
| nb_commentaires | INTEGER | — |  |
| ingested_at *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de réception en zone de staging |
| source_file *(technique, auto-injectée)* | VARCHAR | — | Nom du fichier ou export source d'origine |

### `raw_multi_platform_posts`
Corpus principal de 150 000 publications multi-plateformes

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| post_id | VARCHAR | — |  |
| platform | VARCHAR | — |  |
| timestamp | TIMESTAMP | — |  |
| date | DATE | — |  |
| hour_of_day | INTEGER | — |  |
| day_of_week | VARCHAR | — |  |
| is_weekend | BOOLEAN | — |  |
| user_id | VARCHAR | — |  |
| followers | BIGINT | — |  |
| account_age_days | INTEGER | — |  |
| verified | BOOLEAN | — |  |
| topic | VARCHAR | — |  |
| language | VARCHAR | — |  |
| content_length | INTEGER | — |  |
| media_type | VARCHAR | — |  |
| num_hashtags | INTEGER | — |  |
| sentiment_category | VARCHAR | — |  |
| sentiment_positive | DOUBLE | — |  |
| sentiment_negative | DOUBLE | — |  |
| sentiment_neutral | DOUBLE | — |  |
| likes | BIGINT | — |  |
| shares | BIGINT | — |  |
| comments | BIGINT | — |  |
| views | BIGINT | — |  |
| total_engagement | BIGINT | — |  |
| engagement_rate_per_1k_followers | DOUBLE | — |  |
| hours_since_post | DOUBLE | — |  |
| viral_coefficient | DOUBLE | — |  |
| cross_platform_spread | DOUBLE | — |  |
| toxicity_score | DOUBLE | — |  |
| location | VARCHAR | — |  |
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

### `fact_post_analytics`
Mesures analytiques conservees au grain publication

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| analytics_id | BIGINT | PK |  |
| source_id | INTEGER | FK → dim_source_dataset.source_id |  |
| external_post_id | VARCHAR | — |  |
| platform_name | VARCHAR | — |  |
| published_at | TIMESTAMP | — |  |
| followers | BIGINT | — |  |
| topic | VARCHAR | — |  |
| language | VARCHAR | — |  |
| media_type | VARCHAR | — |  |
| num_hashtags | INTEGER | — |  |
| sentiment_category | VARCHAR | — |  |
| sentiment_positive | DOUBLE | — |  |
| sentiment_negative | DOUBLE | — |  |
| sentiment_neutral | DOUBLE | — |  |
| likes | BIGINT | — |  |
| shares | BIGINT | — |  |
| comments | BIGINT | — |  |
| views | BIGINT | — |  |
| total_engagement | BIGINT | — |  |
| engagement_rate_per_1k_followers | DOUBLE | — |  |
| viral_coefficient | DOUBLE | — |  |
| cross_platform_spread | DOUBLE | — |  |
| toxicity_score | DOUBLE | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `agg_platform_kpis`
KPI descriptifs agreges par plateforme

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| platform_name | VARCHAR | PK |  |
| post_count | BIGINT | — |  |
| median_engagement | DOUBLE | — |  |
| average_engagement | DOUBLE | — |  |
| average_engagement_rate | DOUBLE | — |  |
| viral_post_count | BIGINT | — |  |
| average_toxicity | DOUBLE | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `agg_daily_kpis`
KPI descriptifs agreges par jour

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| activity_date | DATE | PK |  |
| post_count | BIGINT | — |  |
| total_engagement | BIGINT | — |  |
| average_viral_coefficient | DOUBLE | — |  |
| average_toxicity | DOUBLE | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `agg_segment_kpis`
KPI descriptifs par theme, media, langue, sentiment et classe de hashtags

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| segment_id | BIGINT | PK |  |
| dimension_name | VARCHAR | — |  |
| dimension_value | VARCHAR | — |  |
| post_count | BIGINT | — |  |
| median_engagement | DOUBLE | — |  |
| average_engagement | DOUBLE | — |  |
| average_engagement_rate | DOUBLE | — |  |
| viral_post_count | BIGINT | — |  |
| average_toxicity | DOUBLE | — |  |
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

### `dim_post_theme`
Étiquette thématique d'une publication, issue de config/taxonomy.yaml

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| external_post_id | VARCHAR | PK |  |
| page_name | VARCHAR | — | Page émettrice (colonne 'ecole' de la source) |
| media_type | VARCHAR | — | Format du média : texte | photo | video |
| theme | VARCHAR | — | Thème retenu, ou 'non_classe' si aucun mot-clé déclenché |
| matched_keywords | VARCHAR | — | Mots-clés ayant déclenché l'étiquette — rend la décision auditable |
| match_count | INTEGER | — | Nombre de mots-clés trouvés (proxy de confiance) |
| published_at | TIMESTAMP | — |  |
| post_likes | BIGINT | — |  |
| post_shares | BIGINT | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `fact_comment_context`
Un commentaire replacé dans le contexte de sa publication (grain : un commentaire)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| comment_id | VARCHAR | PK |  |
| external_post_id | VARCHAR | FK → dim_post_theme.external_post_id |  |
| author_pseudo | VARCHAR | — |  |
| page_name | VARCHAR | — |  |
| theme | VARCHAR | — |  |
| media_type | VARCHAR | — |  |
| language | VARCHAR | — |  |
| commented_at | TIMESTAMP | — |  |
| published_at | TIMESTAMP | — |  |
| reaction_delay_hours | DOUBLE | — | Heures écoulées entre la publication et le commentaire |
| comment_hour | INTEGER | — | Heure du jour (0-23) — rythme d'usage |
| is_weekend | BOOLEAN | — |  |
| comment_length | INTEGER | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `agg_author_behavior`
Profil comportemental d'un auteur (grain : un auteur)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| author_pseudo | VARCHAR | PK |  |
| comment_count | BIGINT | — |  |
| segment | VARCHAR | — | ponctuel | occasionnel | regulier | engage | hyperactif |
| distinct_posts | BIGINT | — |  |
| distinct_themes | BIGINT | — | Diversité thématique — un auteur mono-thème est un militant, un multi-thème un habitué |
| distinct_pages | BIGINT | — |  |
| median_delay_hours | DOUBLE | — | Réactivité médiane de l'auteur |
| avg_comment_length | DOUBLE | — |  |
| first_seen_at | TIMESTAMP | — |  |
| last_seen_at | TIMESTAMP | — |  |
| active_days | BIGINT | — |  |
| load_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de chargement dans l'entrepôt |
| effective_date *(technique, auto-injectée)* | TIMESTAMP | NOT NULL | Date de début de validité de cette version |
| expiration_date *(technique, auto-injectée)* | TIMESTAMP | — | Date de fin de validité (NULL = version courante) |
| is_current *(technique, auto-injectée)* | BOOLEAN | NOT NULL | Version actuellement active |

### `agg_theme_reaction`
Réaction du public par thème et par page (grain : thème x page)

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| theme | VARCHAR | — |  |
| page_name | VARCHAR | — |  |
| post_count | BIGINT | — |  |
| comment_count | BIGINT | — |  |
| comments_per_post | DOUBLE | — |  |
| distinct_authors | BIGINT | — |  |
| median_delay_hours | DOUBLE | — |  |
| avg_comment_length | DOUBLE | — |  |
| median_post_likes | DOUBLE | — |  |
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

### `recommendation`
Recommandation explicable generee a partir des KPI

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| recommendation_id | BIGINT | PK |  |
| platform_name | VARCHAR | — |  |
| recommendation_type | VARCHAR | — |  |
| recommendation_text | VARCHAR | — |  |
| evidence | VARCHAR | — |  |
| score | DOUBLE | — |  |
| generated_at | TIMESTAMP | — |  |

### `alert`
Alerte explicable sur sentiment ou toxicite

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| alert_id | BIGINT | PK |  |
| platform_name | VARCHAR | — |  |
| alert_type | VARCHAR | — |  |
| alert_text | VARCHAR | — |  |
| severity | VARCHAR | — |  |
| evidence | VARCHAR | — |  |
| generated_at | TIMESTAMP | — |  |

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

### `pipeline_runs`
Historique des exécutions planifiées du pipeline (cron) — succès, échecs, durée, volumes traités

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| run_id | BIGINT | PK |  |
| trigger_type | VARCHAR | — | scheduled | manual | api |
| started_at | TIMESTAMP | NOT NULL |  |
| finished_at | TIMESTAMP | — |  |
| status | VARCHAR | — | RUNNING | SUCCESS | FAILED |
| sources_processed | INTEGER | — |  |
| total_new_rows | INTEGER | — |  |
| total_updated_rows | INTEGER | — |  |
| error_message | VARCHAR | — |  |

### `ingestion_log`
Registre des chargements (hash de fichier) — empêche de recharger deux fois le même fichier par erreur

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| log_id | BIGINT | PK |  |
| file_hash | VARCHAR | NOT NULL | SHA-256 du contenu brut du fichier |
| file_name | VARCHAR | — |  |
| table_name | VARCHAR | NOT NULL |  |
| row_count | INTEGER | — |  |
| status | VARCHAR | — | LOADED | SKIPPED_DUPLICATE | FORCED_RELOAD |
| loaded_at | TIMESTAMP | — |  |