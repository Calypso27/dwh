"""
Tests de la couche comportementale : étiquetage thématique et analyse des
réactions.

Lancer avec : pytest tests/test_behavior.py -v

Les tests d'étiquetage utilisent une taxonomie jetable plutôt que le vrai
config/taxonomy.yaml : celui-ci est destiné à évoluer (on y ajoute des
mots-clés au fil des corpus), et des tests qui en dépendraient casseraient à
chaque enrichissement, pour de mauvaises raisons.

Toutes les connexions de vérification sont ouvertes en lecture-écriture, sans
`read_only=True` : sur Windows, une connexion read-only encore référencée par
le test précédent empêche le suivant d'ouvrir le même fichier en écriture
(« le fichier est utilisé par un autre processus »).
"""
import duckdb
import pytest
import yaml

from dw import behavior, labeling, schema_generator, seed, warehouse
from dw.paths import DB_PATH


@pytest.fixture
def fresh_db():
    """Base vide, dimensions peuplées, supprimée en fin de test."""
    schema_generator.run()
    warehouse.init(reset=True)
    seed.run()
    yield DB_PATH
    if DB_PATH.exists():
        DB_PATH.unlink()


@pytest.fixture
def taxonomie(tmp_path):
    """Taxonomie minimale et contrôlée, écrite sur disque puis chargée."""
    contenu = {
        "min_occurrences": 1,
        "fallback": "non_classe",
        "themes": {
            # Déclaré en premier : doit gagner les égalités.
            "evenement": {"description": "x", "mots_cles": ["gala", "ceremonie"]},
            "politique": {"description": "x", "mots_cles": ["vote", "war", "senat"]},
        },
    }
    chemin = tmp_path / "taxonomy.yaml"
    chemin.write_text(yaml.safe_dump(contenu, allow_unicode=True), encoding="utf-8")
    return labeling.load_taxonomy(chemin)


def _insert_comment(con, comment_id, post_id, author, text, published, commented,
                    page="BBC", media="texte", likes=100, shares=10):
    con.execute(
        """INSERT INTO raw_facebook_comments
           (plateforme, id_commentaire, id_publication, pseudo_auteur, texte,
            date_commentaire, langue, texte_publication, date_publication,
            type_contenu, ecole, likes, partages, vues, nb_commentaires)
           VALUES ('facebook', ?, ?, ?, ?, ?, 'en', ?, ?, ?, ?, ?, ?, 0, 1)""",
        [comment_id, post_id, author, text, commented,
         f"Publication {post_id}", published, media, page, likes, shares],
    )


# --------------------------------------------------------------------------
# Étiquetage
# --------------------------------------------------------------------------

def test_classify_retient_le_theme_ayant_le_plus_de_mots_cles(taxonomie):
    theme, hits, count = labeling.classify("Le vote au senat", taxonomie)
    assert theme == "politique"
    assert count == 2
    assert set(hits) == {"vote", "senat"}


def test_classify_respecte_les_bornes_de_mots(taxonomie):
    """« war » ne doit se déclencher ni sur « warm » ni sur « award »."""
    theme, hits, count = labeling.classify("A warm award today", taxonomie)
    assert count == 0
    assert hits == []
    assert theme == "non_classe"


def test_classify_ne_matche_pas_un_mot_inclus_dans_un_autre(taxonomie):
    theme, hits, _ = labeling.classify("The weather is warm today", taxonomie)
    assert theme == "non_classe"
    assert hits == []


def test_classify_egalite_tranchee_par_ordre_de_declaration(taxonomie):
    """Un mot de chaque thème : le thème déclaré en premier l'emporte."""
    theme, _, count = labeling.classify("Le gala avant le vote", taxonomie)
    assert count == 1
    assert theme == "evenement", "l'ordre du YAML est une priorité assumée"


def test_classify_texte_vide_retourne_le_fallback(taxonomie):
    assert labeling.classify("", taxonomie)[0] == "non_classe"
    assert labeling.classify(None, taxonomie)[0] == "non_classe"


def test_classify_respecte_min_occurrences(tmp_path):
    contenu = {
        "min_occurrences": 2,
        "fallback": "non_classe",
        "themes": {"politique": {"description": "x", "mots_cles": ["vote", "senat"]}},
    }
    chemin = tmp_path / "t.yaml"
    chemin.write_text(yaml.safe_dump(contenu), encoding="utf-8")
    taxo = labeling.load_taxonomy(chemin)

    assert labeling.classify("un vote", taxo)[0] == "non_classe"
    assert labeling.classify("un vote au senat", taxo)[0] == "politique"


# --------------------------------------------------------------------------
# Couche comportementale
# --------------------------------------------------------------------------

def test_le_delai_de_reaction_est_calcule_en_heures(fresh_db):
    con = duckdb.connect(str(fresh_db))
    _insert_comment(con, "c1", "p1", "alice", "bonjour",
                    "2017-07-06 10:00:00", "2017-07-06 12:30:00")
    con.close()

    labeling.build_post_themes(warn_cascade=False)
    behavior.build_comment_context()

    con = duckdb.connect(str(fresh_db))
    delai = con.execute(
        "SELECT reaction_delay_hours FROM fact_comment_context WHERE comment_id = 'c1'"
    ).fetchone()[0]
    con.close()
    assert delai == pytest.approx(2.5)


def test_les_commentaires_vides_sont_exclus(fresh_db):
    con = duckdb.connect(str(fresh_db))
    _insert_comment(con, "c1", "p1", "alice", "un vrai commentaire",
                    "2017-07-06 10:00:00", "2017-07-06 11:00:00")
    _insert_comment(con, "c2", "p1", "bob", "   ",
                    "2017-07-06 10:00:00", "2017-07-06 11:00:00")
    con.close()

    labeling.build_post_themes(warn_cascade=False)
    assert behavior.build_comment_context() == 1


def test_segmentation_des_auteurs_par_volume(fresh_db):
    """Un auteur à 1, 3 et 12 commentaires doit tomber dans 3 segments distincts."""
    con = duckdb.connect(str(fresh_db))
    n = 0
    for auteur, volume in [("solo", 1), ("moyen", 3), ("intense", 12)]:
        for i in range(volume):
            n += 1
            _insert_comment(con, f"c{n}", f"p{i}", auteur, f"texte {n}",
                            "2017-07-06 10:00:00", "2017-07-06 11:00:00")
    con.close()

    labeling.build_post_themes(warn_cascade=False)
    behavior.build_comment_context()
    behavior.build_author_behavior()

    con = duckdb.connect(str(fresh_db))
    segments = dict(con.execute(
        "SELECT author_pseudo, segment FROM agg_author_behavior"
    ).fetchall())
    con.close()
    assert segments == {"solo": "ponctuel", "moyen": "regulier", "intense": "hyperactif"}


def test_le_commentaire_porte_le_theme_de_sa_publication(fresh_db):
    """Le cœur du besoin métier : le commentaire hérite du contexte de son post."""
    con = duckdb.connect(str(fresh_db))
    con.execute(
        """INSERT INTO raw_facebook_comments
           (plateforme, id_commentaire, id_publication, pseudo_auteur, texte,
            date_commentaire, langue, texte_publication, date_publication,
            type_contenu, ecole, likes, partages, vues, nb_commentaires)
           VALUES ('facebook','c1','p1','alice','peu importe ce que dit le commentaire',
                   '2017-07-06 11:00:00','en',
                   'The president signed a new law', '2017-07-06 10:00:00',
                   'texte','CNN',100,10,0,1)"""
    )
    con.close()

    labeling.build_post_themes(warn_cascade=False)
    behavior.build_comment_context()

    con = duckdb.connect(str(fresh_db))
    theme = con.execute(
        "SELECT theme FROM fact_comment_context WHERE comment_id = 'c1'"
    ).fetchone()[0]
    con.close()
    # Le thème vient du TEXTE DE LA PUBLICATION, jamais de celui du commentaire.
    assert theme == "politique_gouvernement"


def test_reetiquetage_successif_ne_leve_pas_d_erreur_de_cle_etrangere(fresh_db):
    """Régression : le 2e passage échouait car fact_comment_context référence
    dim_post_theme, qu'on tentait de vider en premier."""
    con = duckdb.connect(str(fresh_db))
    _insert_comment(con, "c1", "p1", "alice", "bonjour",
                    "2017-07-06 10:00:00", "2017-07-06 11:00:00")
    con.close()

    labeling.build_post_themes(warn_cascade=False)
    behavior.build_all()
    labeling.build_post_themes(warn_cascade=False)  # doit passer sans exception
    behavior.build_all()

    con = duckdb.connect(str(fresh_db))
    assert con.execute("SELECT COUNT(*) FROM fact_comment_context").fetchone()[0] == 1
    con.close()


def test_agregation_par_theme_et_par_page(fresh_db):
    con = duckdb.connect(str(fresh_db))
    _insert_comment(con, "c1", "p1", "alice", "aa",
                    "2017-07-06 10:00:00", "2017-07-06 11:00:00", page="BBC")
    _insert_comment(con, "c2", "p2", "bob", "bb",
                    "2017-07-06 10:00:00", "2017-07-06 11:00:00", page="CNN")
    con.close()

    labeling.build_post_themes(warn_cascade=False)
    behavior.build_comment_context()
    assert behavior.build_theme_reaction() == 2  # un couple thème x page par page
