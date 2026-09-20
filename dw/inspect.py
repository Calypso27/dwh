"""
Outil de diagnostic : inspecte une table (staging ou warehouse) pour repérer
rapidement les colonnes anormalement vides — le genre de problème qui ne
saute pas aux yeux dans `status` (qui ne montre que le nombre de lignes,
pas leur contenu).

Usage :
    python manage.py inspect --table raw_sentiment140
"""
from dw.warehouse import get_connection


def run(table: str):
    con = get_connection()

    columns = con.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position"
    ).fetchall()
    if not columns:
        print(f"✗ Table '{table}' introuvable. Vérifie le nom avec : python manage.py status")
        con.close()
        return

    total = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    print(f"Table '{table}' — {total:,} lignes\n")

    if total == 0:
        print("(table vide, rien à inspecter)")
        con.close()
        return

    print(f"{'Colonne':<25} {'% NULL':>8}  {'Valeurs distinctes':>18}  Exemple")
    print("-" * 90)
    for (col,) in columns:
        null_count = con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" IS NULL').fetchone()[0]
        null_pct = null_count / total * 100
        distinct = con.execute(f'SELECT COUNT(DISTINCT "{col}") FROM "{table}"').fetchone()[0]
        sample = con.execute(f'SELECT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL LIMIT 1').fetchone()
        sample_val = str(sample[0])[:40] if sample else "—"
        flag = " ⚠" if null_pct == 100 else (" ⚠" if null_pct > 50 else "")
        print(f"{col:<25} {null_pct:>7.1f}%  {distinct:>18,}  {sample_val}{flag}")

    print()
    non_technical_cols = [c[0] for c in columns if c[0] not in ("ingested_at", "source_file")]
    all_null_cols = [c for c in non_technical_cols if
                      con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{c}" IS NOT NULL').fetchone()[0] == 0]

    if all_null_cols:
        # Une seule colonne vide parmi plusieurs bien remplies : probablement une donnée
        # réellement absente du fichier source, pas une erreur de nommage de colonne.
        if len(all_null_cols) == 1 and len(all_null_cols) < len(non_technical_cols) / 2:
            print(f"ℹ Colonne vide : {all_null_cols} — probablement une donnée absente du fichier "
                  f"source (pas forcément une erreur), puisque les autres colonnes sont bien peuplées.")
        else:
            print(f"⚠⚠ Colonnes ENTIÈREMENT vides : {all_null_cols}")
            print("   Cause la plus probable : le fichier source n'a pas ces noms de colonnes exacts.")
            print("   Vérifie l'en-tête réel de ton fichier CSV (première ligne) et compare-le à "
                  "config/schema.yaml.")

    con.close()
