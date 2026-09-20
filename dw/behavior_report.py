"""Génère le rapport d'analyse comportementale depuis la couche behavior.

Le rapport est régénéré à partir de la base, jamais rédigé à la main : tout
chiffre qui y figure est reproductible en relançant la commande.
"""
from pathlib import Path

from dw.paths import DOC_DIR
from dw.warehouse import get_connection

OUTPUT_FILE = "behavioral_analysis_report.md"

# Avertissement méthodologique non négociable : le corpus décrit l'audience de
# deux pages de presse (BBC, CNN) en juillet 2017, pas celle de l'Institut.
# Il sert à valider la chaîne de traitement, pas à conclure sur l'école. Sans
# ce rappel en tête de rapport, les chiffres peuvent être cités hors contexte.
AVERTISSEMENT = """> **Portée de ce rapport.** Les données analysées proviennent des pages
> Facebook **BBC et CNN** (6-14 juillet 2017, 99,3 % anglophone). Elles ne
> décrivent **pas** l'audience de l'Institut Saint-Jean. Ce corpus sert de
> **substitut méthodologique** : il a exactement la structure attendue
> (commentaires rattachés à leur publication), ce qui permet de construire et
> d'éprouver la chaîne d'analyse. Aucun chiffre ci-dessous ne doit être cité
> comme un résultat portant sur l'école."""


def _fetch(con, query: str):
    return con.execute(query).fetchall()


def generate() -> Path:
    con = get_connection()

    total, authors, posts, themes = _fetch(con, """
        SELECT COUNT(*), COUNT(DISTINCT author_pseudo),
               COUNT(DISTINCT external_post_id), COUNT(DISTINCT theme)
        FROM fact_comment_context
    """)[0]
    if not total:
        con.close()
        raise RuntimeError(
            "La couche comportementale est vide — lance d'abord : python manage.py build-behavior"
        )

    debut, fin, delai_median, delai_p90 = _fetch(con, """
        SELECT MIN(commented_at), MAX(commented_at),
               MEDIAN(reaction_delay_hours),
               QUANTILE_CONT(reaction_delay_hours, 0.9)
        FROM fact_comment_context WHERE reaction_delay_hours >= 0
    """)[0]

    rapide_1h, rapide_6h = _fetch(con, """
        SELECT 100.0 * COUNT(*) FILTER (WHERE reaction_delay_hours < 1) / COUNT(*),
               100.0 * COUNT(*) FILTER (WHERE reaction_delay_hours < 6) / COUNT(*)
        FROM fact_comment_context WHERE reaction_delay_hours >= 0
    """)[0]

    segments = _fetch(con, """
        SELECT segment, COUNT(*), SUM(comment_count), MEDIAN(median_delay_hours),
               AVG(avg_comment_length), AVG(distinct_themes)
        FROM agg_author_behavior GROUP BY segment
        ORDER BY SUM(comment_count) DESC
    """)
    total_auteurs = sum(r[1] for r in segments)
    total_comm_seg = sum(r[2] for r in segments)

    par_theme = _fetch(con, """
        SELECT theme, SUM(post_count), SUM(comment_count),
               SUM(comment_count) * 1.0 / SUM(post_count),
               MEDIAN(median_delay_hours), AVG(avg_comment_length)
        FROM agg_theme_reaction GROUP BY theme
        ORDER BY MEDIAN(median_delay_hours) ASC
    """)

    par_page = _fetch(con, """
        SELECT page_name, COUNT(DISTINCT external_post_id), COUNT(*),
               COUNT(DISTINCT author_pseudo), MEDIAN(reaction_delay_hours),
               AVG(comment_length)
        FROM fact_comment_context WHERE reaction_delay_hours >= 0
        GROUP BY page_name ORDER BY page_name
    """)

    partages = _fetch(con, """
        SELECT COUNT(*) FROM (
            SELECT author_pseudo FROM fact_comment_context
            GROUP BY author_pseudo HAVING COUNT(DISTINCT page_name) > 1)
    """)[0][0]

    par_format = _fetch(con, """
        SELECT media_type, COUNT(DISTINCT external_post_id), COUNT(*),
               COUNT(*) * 1.0 / COUNT(DISTINCT external_post_id),
               MEDIAN(reaction_delay_hours)
        FROM fact_comment_context WHERE reaction_delay_hours >= 0
        GROUP BY media_type ORDER BY COUNT(*) DESC
    """)

    heures = _fetch(con, """
        SELECT comment_hour, COUNT(*) FROM fact_comment_context
        GROUP BY comment_hour ORDER BY comment_hour
    """)
    con.close()

    pic = max(heures, key=lambda r: r[1])
    creux = min(heures, key=lambda r: r[1])

    L = [
        "# Rapport d'analyse comportementale",
        "",
        AVERTISSEMENT,
        "",
        "Rapport généré automatiquement par `python manage.py report-behavior`.",
        "Toute valeur est reproductible en relançant la commande.",
        "",
        "## 1. Périmètre",
        "",
        f"- Commentaires analysés : **{total:,}**, tous rattachés à leur publication",
        f"- Publications : **{posts}** | Auteurs distincts : **{authors:,}**",
        f"- Thèmes représentés : **{themes}**",
        f"- Période : du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}",
        "",
        "## 2. Réactivité : à quelle vitesse le public réagit",
        "",
        f"- Délai médian entre publication et commentaire : **{delai_median:.2f} h**",
        f"- 9 commentaires sur 10 arrivent en moins de **{delai_p90:.1f} h**",
        f"- **{rapide_1h:.1f} %** des réactions surviennent dans l'heure, **{rapide_6h:.1f} %** dans les six heures",
        "",
        "L'essentiel de la réaction se joue donc le jour même : une publication",
        "qui n'a pas suscité de commentaire dans les six heures n'en suscitera",
        "quasiment plus. C'est une contrainte directe sur le rythme de modération.",
        "",
        "## 3. Segmentation comportementale des auteurs",
        "",
        "| Segment | Auteurs | Part des auteurs | Commentaires | Part du volume | Délai médian | Longueur moy. | Thèmes/auteur |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for seg, n_auteurs, n_comm, delai, longueur, div in segments:
        L.append(f"| {seg} | {n_auteurs:,} | {100 * n_auteurs / total_auteurs:.1f} % | {n_comm:,} | "
                 f"{100 * n_comm / total_comm_seg:.1f} % | {delai:.2f} h | {longueur:.0f} car. | {div:.2f} |")

    minoritaires = sum(r[2] for r in segments if r[0] in ("engage", "hyperactif"))
    part_min_auteurs = sum(r[1] for r in segments if r[0] in ("engage", "hyperactif"))
    L += [
        "",
        f"**Lecture.** {100 * part_min_auteurs / total_auteurs:.1f} % des auteurs "
        f"(segments *engagé* et *hyperactif*) produisent "
        f"{100 * minoritaires / total_comm_seg:.1f} % des commentaires. Une poignée de voix "
        "pèse donc lourdement sur la tonalité perçue d'une page — ignorer cette "
        "concentration conduirait à confondre l'opinion d'une minorité active avec "
        "celle du public.",
        "",
        "## 4. Réaction selon le thème de la publication",
        "",
        "C'est la réponse directe à « il faut regarder les commentaires par rapport",
        "au post qui est associé ». Le thème provient de `config/taxonomy.yaml`.",
        "",
        "| Thème | Publications | Commentaires | Commentaires/post | Délai médian | Longueur moy. |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for theme, n_posts, n_comm, ratio, delai, longueur in par_theme:
        L.append(f"| {theme} | {n_posts} | {n_comm:,} | {ratio:.1f} | {delai:.2f} h | {longueur:.0f} car. |")

    classes = [r for r in par_theme if r[0] != "non_classe"]
    if classes:
        plus_rapide = min(classes, key=lambda r: r[4])
        plus_bavard = max(classes, key=lambda r: r[5])
        L += [
            "",
            f"**Lecture.** Le thème *{plus_rapide[0]}* déclenche les réactions les plus "
            f"rapides ({plus_rapide[4]:.2f} h de délai médian), tandis que *{plus_bavard[0]}* "
            f"suscite les commentaires les plus longs ({plus_bavard[5]:.0f} caractères en "
            "moyenne). Le sujet d'une publication ne change donc pas seulement le volume "
            "de réactions, mais leur nature.",
        ]

    L += [
        "",
        "## 5. Effet du format de la publication",
        "",
        "| Format | Publications | Commentaires | Commentaires/post | Délai médian |",
        "|---|---:|---:|---:|---:|",
    ]
    for fmt, n_posts, n_comm, ratio, delai in par_format:
        L.append(f"| {fmt} | {n_posts} | {n_comm:,} | {ratio:.1f} | {delai:.2f} h |")

    L += [
        "",
        "## 6. Comparaison des deux pages",
        "",
        "| Page | Publications | Commentaires | Auteurs | Délai médian | Longueur moy. |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for page, n_posts, n_comm, n_auth, delai, longueur in par_page:
        L.append(f"| {page} | {n_posts} | {n_comm:,} | {n_auth:,} | {delai:.2f} h | {longueur:.0f} car. |")

    L += [
        "",
        f"**{partages:,} auteurs commentent sur les deux pages** : les audiences se "
        "recouvrent partiellement. C'est le schéma d'analyse qui servira à comparer "
        "l'Institut à un établissement concurrent.",
        "",
        "## 7. Rythme d'usage sur la journée",
        "",
        f"- Pic d'activité à **{pic[0]} h** ({pic[1]:,} commentaires)",
        f"- Creux à **{creux[0]} h** ({creux[1]:,} commentaires)",
        f"- Amplitude pic/creux : **×{pic[1] / creux[1]:.1f}**",
        "",
        "## 8. Limites",
        "",
        "- **Fenêtre de 8 jours** : aucune analyse de tendance ou de saisonnalité "
        "n'est possible. Les variations de volume quotidien reflètent la collecte, "
        "pas le comportement.",
        "- **La colonne `commentaires/post` est plafonnée** : la source ne conserve "
        "au maximum que 100 commentaires par publication (médiane observée : 100). "
        "Tous les thèmes se retrouvent donc tassés entre 87 et 100, et cet "
        "indicateur ne mesure **pas** la popularité d'un sujet. Les comparaisons "
        "valides portent sur le **délai de réaction** et la **longueur des "
        "commentaires**, qui ne subissent pas ce plafond.",
        f"- **Couverture thématique partielle** : les publications sans mot-clé "
        "reconnu restent étiquetées `non_classe`. Beaucoup sont des accroches très "
        "courtes qui ne portent aucun sujet ; les classer de force fabriquerait du bruit.",
        "- **Aucune donnée alumni** : le corpus ne contient aucun attribut de profil, "
        "les auteurs étant des pseudonymes hachés. Cet axe reste ouvert.",
        "- **Corpus anglophone** : un modèle de sentiment entraîné ici ne se "
        "transposera pas tel quel au français.",
        "",
    ]

    DOC_DIR.mkdir(parents=True, exist_ok=True)
    output = DOC_DIR / OUTPUT_FILE
    output.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"✓ Rapport généré : {output}")
    return output
