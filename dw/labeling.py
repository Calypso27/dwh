"""Étiquetage thématique des publications à partir de config/taxonomy.yaml.

Le besoin métier est explicite : « tu ne peux pas analyser un commentaire sans
le lier à un post — est-ce que le post est lié à un événement, à ceci, à cela ? »
La source ne porte que `type_contenu` (texte / photo / video), qui décrit le
FORMAT et non le SUJET. Ce module produit l'étiquette manquante.

Le choix d'un lexique explicite plutôt que d'un classifieur appris est
délibéré : chaque étiquette reste justifiable par les mots qui l'ont
déclenchée (colonne `matched_keywords`), ce qui se défend devant un jury et
se corrige à la main. Un modèle appris demanderait un corpus annoté qui
n'existe pas encore.
"""
import re

import yaml

from dw.paths import TAXONOMY_FILE
from dw.warehouse import get_connection


def load_taxonomy(path=None) -> dict:
    """Charge la taxonomie et pré-compile les motifs de recherche."""
    taxonomy = yaml.safe_load((path or TAXONOMY_FILE).read_text(encoding="utf-8"))

    for theme, definition in taxonomy["themes"].items():
        # Recherche sur mot entier : sans les bornes \b, « war » se déclenche
        # sur « warm » et « award », et « vote » sur « devote ». L'erreur est
        # silencieuse et fausse toutes les statistiques qui suivent.
        definition["_patterns"] = [
            (kw, re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE))
            for kw in definition["mots_cles"]
        ]
    return taxonomy


def classify(text: str, taxonomy: dict) -> tuple[str, list[str], int]:
    """Retourne (thème, mots-clés déclencheurs, nombre de correspondances).

    En cas d'égalité entre deux thèmes, le premier déclaré dans le YAML
    l'emporte — l'ordre du fichier est donc un ordre de priorité assumé, et
    non un détail d'implémentation.
    """
    if not text:
        return taxonomy["fallback"], [], 0

    best_theme, best_hits = taxonomy["fallback"], []
    for theme, definition in taxonomy["themes"].items():
        hits = [kw for kw, pattern in definition["_patterns"] if pattern.search(text)]
        if len(hits) > len(best_hits):
            best_theme, best_hits = theme, hits

    if len(best_hits) < taxonomy["min_occurrences"]:
        return taxonomy["fallback"], [], 0
    return best_theme, best_hits, len(best_hits)


def build_post_themes(warn_cascade: bool = True) -> dict[str, int]:
    """Étiquette les publications distinctes du corpus Facebook (idempotent).

    `warn_cascade` est mis à False quand l'appelant reconstruit lui-même
    fact_comment_context dans la foulée (cas de build-behavior) : l'avertir de
    relancer la commande qu'il est en train d'exécuter n'aurait aucun sens.
    """
    taxonomy = load_taxonomy()
    con = get_connection()

    # DISTINCT ON the post : la table source est au grain COMMENTAIRE, donc
    # chaque publication y apparaît autant de fois qu'elle a de commentaires.
    posts = con.execute("""
        SELECT id_publication, ANY_VALUE(ecole) AS ecole,
               ANY_VALUE(type_contenu) AS type_contenu,
               ANY_VALUE(texte_publication) AS texte_publication,
               ANY_VALUE(date_publication) AS date_publication,
               ANY_VALUE(likes) AS likes, ANY_VALUE(partages) AS partages
        FROM raw_facebook_comments
        GROUP BY id_publication
    """).fetchall()

    rows = []
    for post_id, page, media, text, published_at, likes, shares in posts:
        theme, hits, count = classify(text, taxonomy)
        rows.append((post_id, page, media, theme, ", ".join(hits), count,
                     published_at, likes, shares))

    # fact_comment_context référence dim_post_theme par clé étrangère : la table
    # enfant doit être vidée AVANT la table parent, sinon DuckDB refuse le DELETE
    # (constaté au second lancement — le premier passait, la base étant vide).
    # Ce n'est pas une perte : build-behavior reconstruit intégralement le fait
    # juste après, et l'avertissement ci-dessous couvre le cas d'un label-posts
    # lancé seul.
    dependent_rows = con.execute("SELECT COUNT(*) FROM fact_comment_context").fetchone()[0]
    if dependent_rows:
        con.execute("DELETE FROM fact_comment_context")

    con.execute("DELETE FROM dim_post_theme")
    con.executemany(
        """INSERT INTO dim_post_theme (external_post_id, page_name, media_type, theme,
                                       matched_keywords, match_count, published_at,
                                       post_likes, post_shares)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )

    distribution = dict(con.execute("""
        SELECT theme, COUNT(*) FROM dim_post_theme GROUP BY theme ORDER BY COUNT(*) DESC
    """).fetchall())
    con.close()

    total = sum(distribution.values())
    unclassified = distribution.get(taxonomy["fallback"], 0)
    coverage = 100 * (total - unclassified) / total if total else 0.0

    print(f"✓ {total:,} publications étiquetées — couverture {coverage:.1f} %")
    for theme, count in distribution.items():
        print(f"    {theme:<26} {count:>4}  ({100 * count / total:>5.1f} %)")
    if coverage < 70:
        print(f"⚠ Couverture faible : enrichis les mots-clés dans {TAXONOMY_FILE.name} "
              f"(inspecte les posts 'non_classe' pour voir ce qui manque).")
    if dependent_rows and warn_cascade:
        print(f"⚠ {dependent_rows:,} lignes de fact_comment_context ont été vidées "
              f"(dépendance de clé étrangère) — relance : python manage.py build-behavior")
    return distribution
