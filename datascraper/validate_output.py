import os
import sys
import pandas as pd
import sqlite3

# --- CONFIGURATIE ---
# Pas deze waarden aan op basis van je projectverwachtingen.
BASE_PATH = 'datascraper/data'
CSV_FILENAME = 'isu_results.csv' # Aangepast van 'isu_results.csv' voor duidelijkheid
DB_FILENAME = 'isu_data.db'
MINIMUM_ROWS = 40000  # Verwacht minimaal 1000 resultaten
MINIMUM_ID_FILL_RATE = 0.95  # Verwacht dat minstens 95% van de SkaterID's is ingevuld

# Volledige bestandspaden
CSV_OUTPUT = os.path.join(BASE_PATH, CSV_FILENAME)
DB_OUTPUT = os.path.join(BASE_PATH, DB_FILENAME)

def validate_output():
    """
    Voert een reeks validatietests uit op de output van de data pipeline.
    Geeft een exit code 0 bij succes en 1 bij een fout.
    """
    validation_issues = []
    csv_row_count = 0

    # --- Test 1: Bestandsvalidatie ---
    print("Stap 1: Bestandsvalidatie...")
    if not os.path.exists(CSV_OUTPUT):
        validation_issues.append(f"❌ [FOUT] CSV-bestand niet gevonden: {CSV_OUTPUT}")
    elif os.path.getsize(CSV_OUTPUT) == 0:
        validation_issues.append(f"❌ [FOUT] CSV-bestand is leeg: {CSV_OUTPUT}")

    if not os.path.exists(DB_OUTPUT):
        validation_issues.append(f"❌ [FOUT] Database-bestand niet gevonden: {DB_OUTPUT}")
    elif os.path.getsize(DB_OUTPUT) == 0:
        validation_issues.append(f"❌ [FOUT] Database-bestand is leeg: {DB_OUTPUT}")

    # Stop als de bestanden niet in orde zijn
    if validation_issues:
        return validation_issues, False

    print("✅ Bestanden bestaan en zijn niet leeg.")

    # --- Test 2: CSV Sanity Checks ---
    print("\nStap 2: CSV Sanity Checks...")
    try:
        df = pd.read_csv(CSV_OUTPUT, delimiter=';')
        csv_row_count = len(df)

        # Check 2a: Minimum aantal rijen
        if csv_row_count < MINIMUM_ROWS:
            validation_issues.append(f"⚠️ [WAARSCHUWING] CSV bevat {csv_row_count} rijen, wat minder is dan de drempel van {MINIMUM_ROWS}.")
        else:
            print(f"✅ CSV bevat {csv_row_count} rijen (voldoet aan drempel).")

        # Check 2b: Aanwezigheid van 'SkaterID' kolom (verwijderd op verzoek)
        # if 'SkaterID' not in df.columns:
        #     validation_issues.append("❌ [FOUT] Kolom 'SkaterID' ontbreekt in het CSV-bestand.")
        # else:
        #     print("✅ Kolom 'SkaterID' is aanwezig.")
        #     # Check 2c: Verrijkingsgraad
        #     id_fill_rate = df['SkaterID'].notna().sum() / csv_row_count
        #     if id_fill_rate < MINIMUM_ID_FILL_RATE:
        #         validation_issues.append(f"⚠️ [WAARSCHUWING] De SkaterID verrijkingsgraad is {id_fill_rate:.2%}, wat lager is dan de drempel van {MINIMUM_ID_FILL_RATE:.0%}.")
        #     else:
        #         print(f"✅ SkaterID verrijkingsgraad is {id_fill_rate:.2%} (voldoet aan drempel).")

    except Exception as e:
        validation_issues.append(f"❌ [FOUT] Kon CSV-bestand niet lezen of verwerken: {e}")

    if any("❌" in issue for issue in validation_issues):
        return validation_issues, False


    # --- Test 3: Database Sanity Checks ---
    print("\nStap 3: Database Sanity Checks...")
    try:
        conn = sqlite3.connect(DB_OUTPUT)
        cursor = conn.cursor()

        # Check 3a: Bestaan van de 'results' tabel
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='results';")
        if cursor.fetchone() is None:
            validation_issues.append("❌ [FOUT] Tabel 'results' niet gevonden in de database.")
        else:
            print("✅ Tabel 'results' is aanwezig in de database.")
            # Check 3b: Consistentie van aantal rijen
            db_row_count = cursor.execute("SELECT COUNT(*) FROM results;").fetchone()[0]
            if db_row_count != csv_row_count:
                validation_issues.append(f"❌ [FOUT] Inconsistentie in aantal rijen: CSV heeft {csv_row_count} rijen, maar de database heeft {db_row_count} rijen.")
            else:
                print(f"✅ Aantal rijen in database ({db_row_count}) komt overeen met CSV.")

        conn.close()
    except Exception as e:
        validation_issues.append(f"❌ [FOUT] Kon database niet lezen of verwerken: {e}")

    is_success = not any("❌" in issue for issue in validation_issues)
    return validation_issues, is_success


if __name__ == "__main__":
    print("--- Start Data Validatie ---")
    issues, success = validate_output()
    print("\n--- Validatierapport ---")

    if not issues:
        print("🎉 GEWELDIG! Alle validatietests zijn succesvol doorlopen.")
    else:
        for issue in issues:
            print(issue)

    if success:
        print("\nEindstatus: ✅ VALIDATIE GESLAAGD")
        sys.exit(0)
    else:
        print("\nEindstatus: ❌ VALIDATIE MISLUKT")
        sys.exit(1) 