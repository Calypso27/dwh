-- =========================================================
-- COUCHE STAGING (duckdb) — généré automatiquement, ne pas éditer à la main
-- Source : config/schema.yaml — généré le 2026-09-20T10:42:53
-- =========================================================

-- Export brut du dataset YouTube (texte réel + scores de sentiment déjà calculés)
CREATE TABLE IF NOT EXISTS "raw_youtube_comments" (
    "comment_id" VARCHAR,
    "video_id" VARCHAR,
    "channel_id" VARCHAR,
    "text" VARCHAR,
    "sentiment_category" VARCHAR,
    "sentiment_score" DOUBLE,
    "likes" INTEGER,
    "published_at" TIMESTAMP,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- 1.6M tweets réels annotés positif/négatif (Sentiment140)
CREATE TABLE IF NOT EXISTS "raw_sentiment140" (
    "tweet_id" BIGINT,
    "text" VARCHAR,
    "polarity" INTEGER,
    "tweet_date" TIMESTAMP,
    "user_handle" VARCHAR,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- 1.5M tweets réels en français avec sentiment
CREATE TABLE IF NOT EXISTS "raw_twitter_fr" (
    "tweet_id" BIGINT,
    "text" VARCHAR,
    "sentiment" VARCHAR,
    "tweet_date" TIMESTAMP,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- Critiques réelles Allociné (texte long, notation)
CREATE TABLE IF NOT EXISTS "raw_allocine" (
    "review_id" VARCHAR,
    "text" VARCHAR,
    "rating" DOUBLE,
    "review_date" TIMESTAMP,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- Commentaires réels Reddit, diversité de communautés/sujets
CREATE TABLE IF NOT EXISTS "raw_reddit" (
    "comment_id" VARCHAR,
    "subreddit" VARCHAR,
    "text" VARCHAR,
    "score" INTEGER,
    "created_at" TIMESTAMP,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- Nouveau dataset ajouté après coup — avis produits réels avec note et texte
CREATE TABLE IF NOT EXISTS "raw_amazon_reviews" (
    "review_id" VARCHAR,
    "product_id" VARCHAR,
    "text" VARCHAR,
    "star_rating" INTEGER,
    "review_date" TIMESTAMP,
    "verified_purchase" BOOLEAN,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- Commentaires Facebook enrichis avec le contexte de leur publication
CREATE TABLE IF NOT EXISTS "raw_facebook_comments" (
    "plateforme" VARCHAR,
    "id_commentaire" VARCHAR,
    "id_publication" VARCHAR,
    "pseudo_auteur" VARCHAR,
    "texte" VARCHAR,
    "date_commentaire" TIMESTAMP,
    "langue" VARCHAR,
    "texte_publication" VARCHAR,
    "date_publication" TIMESTAMP,
    "type_contenu" VARCHAR,
    "ecole" VARCHAR,
    "likes" INTEGER,
    "partages" INTEGER,
    "vues" INTEGER,
    "nb_commentaires" INTEGER,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);

-- Corpus principal de 150 000 publications multi-plateformes
CREATE TABLE IF NOT EXISTS "raw_multi_platform_posts" (
    "post_id" VARCHAR,
    "platform" VARCHAR,
    "timestamp" TIMESTAMP,
    "date" DATE,
    "hour_of_day" INTEGER,
    "day_of_week" VARCHAR,
    "is_weekend" BOOLEAN,
    "user_id" VARCHAR,
    "followers" BIGINT,
    "account_age_days" INTEGER,
    "verified" BOOLEAN,
    "topic" VARCHAR,
    "language" VARCHAR,
    "content_length" INTEGER,
    "media_type" VARCHAR,
    "num_hashtags" INTEGER,
    "sentiment_category" VARCHAR,
    "sentiment_positive" DOUBLE,
    "sentiment_negative" DOUBLE,
    "sentiment_neutral" DOUBLE,
    "likes" BIGINT,
    "shares" BIGINT,
    "comments" BIGINT,
    "views" BIGINT,
    "total_engagement" BIGINT,
    "engagement_rate_per_1k_followers" DOUBLE,
    "hours_since_post" DOUBLE,
    "viral_coefficient" DOUBLE,
    "cross_platform_spread" DOUBLE,
    "toxicity_score" DOUBLE,
    "location" VARCHAR,
    "ingested_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "source_file" VARCHAR
);
