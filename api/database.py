"""
Connexion à la base pour l'API.

Ouverte en lecture seule (read_only=True) : l'API ne fait que consulter
les données déjà produites par le pipeline `dw` (manage.py). Ça évite
tout conflit de verrou avec le pipeline qui, lui, écrit dans la base.

En production, cette couche basculera vers PostgreSQL (accès concurrent
natif) — c'est pour ça que toutes les requêtes ci-dessous et dans les
routers restent du SQL standard, sans fonction propre à DuckDB, afin
d'être portables sans réécriture.
"""
import duckdb
from dw.paths import DB_PATH


def get_db():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        yield con
    finally:
        con.close()
