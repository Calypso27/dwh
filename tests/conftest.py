"""Configuration commune à toute la suite de tests.

Ce fichier est importé par pytest AVANT les modules de test : c'est le seul
endroit où l'on peut positionner la variable d'environnement à temps, puisque
`dw.paths` lit SJ_WAREHOUSE_DIR au moment de son import.
"""
import os
import tempfile
from pathlib import Path

# Sort la base de test du dossier OneDrive.
#
# Sans cette redirection, la suite échoue par intermittence sur
# « IO Error: le fichier est utilisé par un autre processus » : OneDrive ouvre
# le .duckdb pour le synchroniser pendant que le test suivant tente de le
# recréer. Le test qui tombe change à chaque exécution, ce qui fait perdre
# beaucoup de temps à chercher un bug dans le code applicatif — il n'y en a
# pas. Le dossier temporaire du système n'est jamais synchronisé.
_test_warehouse = Path(tempfile.gettempdir()) / "saint_jean_dw_tests"
_test_warehouse.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("SJ_WAREHOUSE_DIR", str(_test_warehouse))
