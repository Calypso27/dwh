"""Analyse comportementale : comment le public réagit aux publications.

Principe directeur, imposé par le besoin métier : un commentaire n'est jamais
analysé seul. Chaque ligne produite ici porte le contexte de la publication
qui l'a provoqué (thème, format, page, date), ce qui permet de répondre à
« les gens réagissent-ils différemment selon le sujet du post ? » plutôt qu'au
seul « que disent les gens ? ».

Trois grains, trois tables :
  - fact_comment_context : un commentaire replacé dans son contexte
  - agg_author_behavior  : un auteur et son profil d'usage
  - agg_theme_reaction   : un thème x une page, et la réaction qu'il suscite
"""
from dw.warehouse import get_connection

# Bornes de segmentation des auteurs. Elles ne sont pas arbitraires : la
# distribution observée est très concentrée (81 % des auteurs ne commentent
# qu'une fois, 0,6 % dépassent 10 commentaires), et ces paliers isolent la
# minorité active qui produit l'essentiel du volume.
SEGMENTS = [
    (1, 1, "ponctuel"),
    (2, 2, "occasionnel"),
    (3, 4, "regulier"),
    (5, 9, "engage"),
    (10, None, "hyperactif"),
]


def _segment_case_sql(column: str = "comment_count") -> str:
    """Construit le CASE SQL de segmentation depuis SEGMENTS (source unique)."""
    clauses = []
    for low, high, label in SEGMENTS:
        condition = f"{column} >= {low}" if high is None else f"{column} BETWEEN {low} AND {high}"
        clauses.append(f"WHEN {condition} THEN '{label}'")
    return "CASE " + " ".join(clauses) + " END"


def build_comment_context() -> int:
    """Construit le fait 'commentaire en contexte' (idempotent)."""
    con = get_connection()
    con.execute("DELETE FROM fact_comment_context")
    con.execute("""
        INSERT INTO fact_comment_context (
            comment_id, external_post_id, author_pseudo, page_name, theme,
            media_type, language, commented_at, published_at,
            reaction_delay_hours, comment_hour, is_weekend, comment_length
        )
        SELECT
            f.id_commentaire,
            f.id_publication,
            f.pseudo_auteur,
            f.ecole,
            COALESCE(t.theme, 'non_classe'),
            f.type_contenu,
            f.langue,
            f.date_commentaire,
            f.date_publication,
            date_diff('second', f.date_publication, f.date_commentaire) / 3600.0,
            EXTRACT(hour FROM f.date_commentaire),
            EXTRACT(dow FROM f.date_commentaire) IN (0, 6),
            LENGTH(COALESCE(f.texte, ''))
        FROM raw_facebook_comments f
        LEFT JOIN dim_post_theme t ON t.external_post_id = f.id_publication
        WHERE f.texte IS NOT NULL AND TRIM(f.texte) <> ''
    """)

    count, negative = con.execute("""
        SELECT COUNT(*), COUNT(*) FILTER (WHERE reaction_delay_hours < 0)
        FROM fact_comment_context
    """).fetchone()
    con.close()

    print(f"✓ fact_comment_context : {count:,} commentaires replacés dans leur contexte")
    if negative:
        # Un commentaire antérieur à sa publication est impossible : c'est un
        # signe de dates corrompues à la source, pas un comportement à analyser.
        print(f"⚠ {negative:,} commentaires ont un délai NÉGATIF (dates incohérentes) — à exclure des moyennes")
    return count


def build_author_behavior() -> int:
    """Construit le profil comportemental par auteur (idempotent)."""
    con = get_connection()
    con.execute("DELETE FROM agg_author_behavior")
    con.execute(f"""
        INSERT INTO agg_author_behavior (
            author_pseudo, comment_count, segment, distinct_posts, distinct_themes,
            distinct_pages, median_delay_hours, avg_comment_length,
            first_seen_at, last_seen_at, active_days
        )
        WITH par_auteur AS (
            SELECT
                author_pseudo,
                COUNT(*) AS comment_count,
                COUNT(DISTINCT external_post_id) AS distinct_posts,
                COUNT(DISTINCT theme) AS distinct_themes,
                COUNT(DISTINCT page_name) AS distinct_pages,
                MEDIAN(reaction_delay_hours) AS median_delay_hours,
                AVG(comment_length) AS avg_comment_length,
                MIN(commented_at) AS first_seen_at,
                MAX(commented_at) AS last_seen_at,
                COUNT(DISTINCT CAST(commented_at AS DATE)) AS active_days
            FROM fact_comment_context
            WHERE reaction_delay_hours >= 0
            GROUP BY author_pseudo
        )
        SELECT
            author_pseudo, comment_count, {_segment_case_sql()},
            distinct_posts, distinct_themes, distinct_pages, median_delay_hours,
            avg_comment_length, first_seen_at, last_seen_at, active_days
        FROM par_auteur
    """)

    rows = con.execute("""
        SELECT segment, COUNT(*), SUM(comment_count)
        FROM agg_author_behavior GROUP BY segment
    """).fetchall()
    total_authors = sum(r[1] for r in rows)
    total_comments = sum(r[2] for r in rows)
    con.close()

    order = {label: i for i, (_, _, label) in enumerate(SEGMENTS)}
    print(f"✓ agg_author_behavior : {total_authors:,} auteurs profilés")
    for segment, authors, comments in sorted(rows, key=lambda r: order.get(r[0], 99)):
        print(f"    {segment:<13} {authors:>6} auteurs ({100 * authors / total_authors:>5.1f} %) "
              f"→ {comments:>6} commentaires ({100 * comments / total_comments:>5.1f} %)")
    return total_authors


def build_theme_reaction() -> int:
    """Agrège la réaction du public par thème et par page (idempotent)."""
    con = get_connection()
    con.execute("DELETE FROM agg_theme_reaction")
    con.execute("""
        INSERT INTO agg_theme_reaction (
            theme, page_name, post_count, comment_count, comments_per_post,
            distinct_authors, median_delay_hours, avg_comment_length, median_post_likes
        )
        SELECT
            c.theme,
            c.page_name,
            COUNT(DISTINCT c.external_post_id) AS post_count,
            COUNT(*) AS comment_count,
            COUNT(*) * 1.0 / COUNT(DISTINCT c.external_post_id) AS comments_per_post,
            COUNT(DISTINCT c.author_pseudo) AS distinct_authors,
            MEDIAN(c.reaction_delay_hours) AS median_delay_hours,
            AVG(c.comment_length) AS avg_comment_length,
            MEDIAN(t.post_likes) AS median_post_likes
        FROM fact_comment_context c
        LEFT JOIN dim_post_theme t ON t.external_post_id = c.external_post_id
        WHERE c.reaction_delay_hours >= 0
        GROUP BY c.theme, c.page_name
    """)
    count = con.execute("SELECT COUNT(*) FROM agg_theme_reaction").fetchone()[0]
    con.close()
    print(f"✓ agg_theme_reaction : {count} couples thème x page")
    return count


def build_all() -> None:
    """Chaîne complète — à lancer après l'étiquetage des publications."""
    build_comment_context()
    build_author_behavior()
    build_theme_reaction()
