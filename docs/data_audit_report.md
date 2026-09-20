# Audit des datasets

Audit genere automatiquement depuis `data/raw/`.

| Fichier | Statut | Lignes | Colonnes | Role analytique |
|---|---:|---:|---:|---|
| `multi_platform_social_sentiment_evolution.csv` | OK | 150,000 | 31 | principal: engagement, viralite, sentiment fourni, toxicite |
| `Sentiment140.csv` | OK | 1,600,000 | 6 | NLP: tweets anglais etiquetes |
| `french_tweets.csv` | OK | 1,526,724 | 2 | NLP: tweets francais etiquetes |
| `youtube-comments-sentiment.csv` | OK | 1,032,225 | 12 | NLP: commentaires YouTube etiquetes |
| `allocine_hf_sample.csv` | OK | 20,000 | 4 | NLP: critiques francaises |
| `amazon_reviews_hf_sample.csv` | OK | 20,000 | 6 | NLP: avis produits |
| `reddit_hf_sample.csv` | OK | 20,000 | 5 | NLP: commentaires Reddit |
| `dataset_publications.csv` | OK | 500 | 11 | social: publications Facebook |
| `dataset_commentaires.csv` | OK | 48,713 | 8 | social: commentaires Facebook |
| `dataset_facebook_joint.csv` | OK | 48,713 | 17 | social: commentaires Facebook enrichis |

## Regle d'utilisation

- Le corpus principal sert aux modeles d'engagement et de viralite.
- Les corpus textuels servent principalement a l'entrainement et a la validation NLP.
- Les analyses combinees doivent conserver la provenance et ne comparer que des metriques compatibles.
