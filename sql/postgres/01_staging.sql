-- =========================================================
-- COUCHE STAGING (postgres) — généré automatiquement, ne pas éditer à la main
-- Source : config/schema.yaml — généré le 2026-09-04T13:12:27
-- =========================================================

-- Export brut du dataset YouTube (scores de sentiment déjà calculés)
CREATE TABLE IF NOT EXISTS "raw_youtube_comments" (
    "comment_id" VARCHAR,
    "video_id" VARCHAR,
    "channel_id" VARCHAR,
    "sentiment_category" VARCHAR,
    "sentiment_score" DOUBLE PRECISION,
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
    "rating" DOUBLE PRECISION,
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
