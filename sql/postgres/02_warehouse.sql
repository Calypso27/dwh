-- =========================================================
-- COUCHE WAREHOUSE (postgres) — généré automatiquement, ne pas éditer à la main
-- Source : config/schema.yaml — généré le 2026-09-14T23:38:28
-- =========================================================

-- --- groupe : dimensions ---

-- Provenance de chaque donnée : institution, entreprise, dataset public...
CREATE TABLE IF NOT EXISTS "dim_source_dataset" (
    "source_id" INTEGER PRIMARY KEY,
    "source_name" VARCHAR NOT NULL,
    "provenance" VARCHAR,
    "language" VARCHAR,
    "license" VARCHAR,
    "is_synthetic" BOOLEAN DEFAULT FALSE,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE
);

-- Réseau social ou plateforme d'origine du contenu
CREATE TABLE IF NOT EXISTS "dim_platform" (
    "platform_id" INTEGER PRIMARY KEY,
    "platform_name" VARCHAR NOT NULL,
    "content_type" VARCHAR,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE
);

-- Modèle ou algorithme utilisé pour une prédiction
CREATE TABLE IF NOT EXISTS "dim_model" (
    "model_id" INTEGER PRIMARY KEY,
    "model_name" VARCHAR NOT NULL,
    "model_version" VARCHAR,
    "model_family" VARCHAR,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE
);

-- Comptes d'accès à la plateforme, avec rôle et périmètre (gestion des accès du cahier des charges)
CREATE TABLE IF NOT EXISTS "dim_user" (
    "user_id" INTEGER PRIMARY KEY,
    "username" VARCHAR NOT NULL,
    "hashed_password" VARCHAR NOT NULL,
    "role" VARCHAR NOT NULL,
    "scope_source_id" INTEGER,
    "is_active" BOOLEAN DEFAULT TRUE,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY ("scope_source_id") REFERENCES "dim_source_dataset"("source_id")
);

-- --- groupe : facts ---

-- Publication ou commentaire, une ligne par version (SCD2)
CREATE TABLE IF NOT EXISTS "fact_social_post" (
    "post_id" BIGINT PRIMARY KEY,
    "source_id" INTEGER,
    "platform_id" INTEGER,
    "external_post_id" VARCHAR,
    "text_content" VARCHAR,
    "published_at" TIMESTAMP,
    "likes" INTEGER,
    "comments" INTEGER,
    "shares" INTEGER,
    "views" INTEGER,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY ("source_id") REFERENCES "dim_source_dataset"("source_id"),
    FOREIGN KEY ("platform_id") REFERENCES "dim_platform"("platform_id")
);

-- Mesures analytiques conservees au grain publication
CREATE TABLE IF NOT EXISTS "fact_post_analytics" (
    "analytics_id" BIGINT PRIMARY KEY,
    "source_id" INTEGER,
    "external_post_id" VARCHAR,
    "platform_name" VARCHAR,
    "published_at" TIMESTAMP,
    "followers" BIGINT,
    "topic" VARCHAR,
    "language" VARCHAR,
    "media_type" VARCHAR,
    "num_hashtags" INTEGER,
    "sentiment_category" VARCHAR,
    "sentiment_positive" DOUBLE PRECISION,
    "sentiment_negative" DOUBLE PRECISION,
    "sentiment_neutral" DOUBLE PRECISION,
    "likes" BIGINT,
    "shares" BIGINT,
    "comments" BIGINT,
    "views" BIGINT,
    "total_engagement" BIGINT,
    "engagement_rate_per_1k_followers" DOUBLE PRECISION,
    "viral_coefficient" DOUBLE PRECISION,
    "cross_platform_spread" DOUBLE PRECISION,
    "toxicity_score" DOUBLE PRECISION,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY ("source_id") REFERENCES "dim_source_dataset"("source_id")
);

-- KPI descriptifs agreges par plateforme
CREATE TABLE IF NOT EXISTS "agg_platform_kpis" (
    "platform_name" VARCHAR PRIMARY KEY,
    "post_count" BIGINT,
    "median_engagement" DOUBLE PRECISION,
    "average_engagement" DOUBLE PRECISION,
    "average_engagement_rate" DOUBLE PRECISION,
    "viral_post_count" BIGINT,
    "average_toxicity" DOUBLE PRECISION,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE
);

-- KPI descriptifs agreges par jour
CREATE TABLE IF NOT EXISTS "agg_daily_kpis" (
    "activity_date" DATE PRIMARY KEY,
    "post_count" BIGINT,
    "total_engagement" BIGINT,
    "average_viral_coefficient" DOUBLE PRECISION,
    "average_toxicity" DOUBLE PRECISION,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE
);

-- KPI descriptifs par theme, media, langue, sentiment et classe de hashtags
CREATE TABLE IF NOT EXISTS "agg_segment_kpis" (
    "segment_id" BIGINT PRIMARY KEY,
    "dimension_name" VARCHAR,
    "dimension_value" VARCHAR,
    "post_count" BIGINT,
    "median_engagement" DOUBLE PRECISION,
    "average_engagement" DOUBLE PRECISION,
    "average_engagement_rate" DOUBLE PRECISION,
    "viral_post_count" BIGINT,
    "average_toxicity" DOUBLE PRECISION,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE
);

-- Une prédiction de sentiment pour un post, par un modèle donné
CREATE TABLE IF NOT EXISTS "fact_sentiment_prediction" (
    "prediction_id" BIGINT PRIMARY KEY,
    "post_id" BIGINT,
    "model_id" INTEGER,
    "sentiment_label" VARCHAR,
    "positive_probability" DOUBLE PRECISION,
    "negative_probability" DOUBLE PRECISION,
    "neutral_probability" DOUBLE PRECISION,
    "confidence" DOUBLE PRECISION,
    "is_human_validated" BOOLEAN DEFAULT FALSE,
    "load_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "effective_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiration_date" TIMESTAMP,
    "is_current" BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY ("post_id") REFERENCES "fact_social_post"("post_id"),
    FOREIGN KEY ("model_id") REFERENCES "dim_model"("model_id")
);

-- --- groupe : ml_tracking ---

-- Un essai d'entraînement/évaluation : quel algo, sur quelles données, comment
CREATE TABLE IF NOT EXISTS "model_run" (
    "run_id" BIGINT PRIMARY KEY,
    "model_id" INTEGER,
    "source_id" INTEGER,
    "task_type" VARCHAR,
    "hyperparameters" VARCHAR,
    "train_rows" INTEGER,
    "test_rows" INTEGER,
    "split_seed" INTEGER,
    "run_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("model_id") REFERENCES "dim_model"("model_id"),
    FOREIGN KEY ("source_id") REFERENCES "dim_source_dataset"("source_id")
);

-- Résultat mesuré pour un run donné (F1, precision, recall, PR-AUC...)
CREATE TABLE IF NOT EXISTS "model_metric" (
    "metric_id" BIGINT PRIMARY KEY,
    "run_id" BIGINT,
    "metric_name" VARCHAR NOT NULL,
    "metric_value" DOUBLE PRECISION NOT NULL,
    "class_label" VARCHAR,
    FOREIGN KEY ("run_id") REFERENCES "model_run"("run_id")
);

-- Recommandation explicable generee a partir des KPI
CREATE TABLE IF NOT EXISTS "recommendation" (
    "recommendation_id" BIGINT PRIMARY KEY,
    "platform_name" VARCHAR,
    "recommendation_type" VARCHAR,
    "recommendation_text" VARCHAR,
    "evidence" VARCHAR,
    "score" DOUBLE PRECISION,
    "generated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerte explicable sur sentiment ou toxicite
CREATE TABLE IF NOT EXISTS "alert" (
    "alert_id" BIGINT PRIMARY KEY,
    "platform_name" VARCHAR,
    "alert_type" VARCHAR,
    "alert_text" VARCHAR,
    "severity" VARCHAR,
    "evidence" VARCHAR,
    "generated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --- groupe : data_quality ---

-- Journal des contrôles qualité exécutés à chaque chargement
CREATE TABLE IF NOT EXISTS "dq_checks" (
    "check_id" BIGINT PRIMARY KEY,
    "table_name" VARCHAR NOT NULL,
    "check_name" VARCHAR NOT NULL,
    "check_result" VARCHAR,
    "rows_checked" INTEGER,
    "rows_failed" INTEGER,
    "checked_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historique des exécutions planifiées du pipeline (cron) — succès, échecs, durée, volumes traités
CREATE TABLE IF NOT EXISTS "pipeline_runs" (
    "run_id" BIGINT PRIMARY KEY,
    "trigger_type" VARCHAR,
    "started_at" TIMESTAMP NOT NULL,
    "finished_at" TIMESTAMP,
    "status" VARCHAR,
    "sources_processed" INTEGER,
    "total_new_rows" INTEGER,
    "total_updated_rows" INTEGER,
    "error_message" VARCHAR
);

-- Registre des chargements (hash de fichier) — empêche de recharger deux fois le même fichier par erreur
CREATE TABLE IF NOT EXISTS "ingestion_log" (
    "log_id" BIGINT PRIMARY KEY,
    "file_hash" VARCHAR NOT NULL,
    "file_name" VARCHAR,
    "table_name" VARCHAR NOT NULL,
    "row_count" INTEGER,
    "status" VARCHAR,
    "loaded_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
