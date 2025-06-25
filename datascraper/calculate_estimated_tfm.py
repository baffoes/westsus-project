#!/usr/bin/env python3
import pandas as pd
import logging

# --- Configuratie ---
INPUT_FILE = 'datascraper/data/isu_results.csv'
OUTPUT_FILE = 'datascraper/data/isu_results.csv'
TFM_COLUMN = 'EstimatedTFM'
TFM_BUFFER_COLUMN = 'EstimatedTFMBuffer'
TFM_BUFFER_SECONDS = 60

# Standaard intervallen (in seconden).
STANDARD_INTERVALS = {
    500: 135,
    1000: 165,
    1500: 200,
    3000: 330,
    5000: 480,
    10000: 900,
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def apply_10000m_reset_logic(df):
    """Past TFM reset logica toe voor 10,000m races."""
    logging.info("Toepassen van speciale 10,000m TFM reset logica...")
    df_10k = df[df['Distance'] == 10000].copy()
    if df_10k.empty:
        return df

    for _, group in df_10k.groupby(['Stadium', 'Date', 'Event']):
        unique_pairs = sorted(group['Pair'].unique())
        num_pairs = len(unique_pairs)
        if num_pairs <= 6:  # Geen dweilpauze bij kleine races
            continue

        halfway_point = (num_pairs + 1) // 2
        first_pair_after_break = unique_pairs[halfway_point]
        
        for idx, row in group.iterrows():
            if row['Pair'] >= first_pair_after_break:
                pairs_since_break = sorted(unique_pairs).index(row['Pair']) - halfway_point
                new_tfm = pairs_since_break * STANDARD_INTERVALS[10000]
                df.loc[idx, TFM_COLUMN] = new_tfm
    return df

def main():
    """Berekent TFM op basis van standaard-schattingen."""
    logging.info(f"Starten van Estimated TFM calculatie voor '{INPUT_FILE}'...")
    try:
        df = pd.read_csv(INPUT_FILE, delimiter=';', low_memory=False)
        df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
        df['Pair'] = pd.to_numeric(df['Pair'], errors='coerce')
    except (FileNotFoundError, KeyError) as e:
        logging.error(f"FATALE FOUT bij lezen '{INPUT_FILE}': {e}", exc_info=True)
        return

    # Map standaard intervallen naar de Distance kolom
    df['Interval'] = df['Distance'].map(STANDARD_INTERVALS)
    
    # Bereken de TFM op basis van schattingen
    df[TFM_COLUMN] = (df['Pair'] - 1) * df['Interval']
    
    # Pas 10k logica toe
    df = apply_10000m_reset_logic(df)
    
    # Voeg buffer toe
    df[TFM_BUFFER_COLUMN] = df[TFM_COLUMN] + TFM_BUFFER_SECONDS

    # Ruim op
    df = df.drop(columns=['Interval'])
    df[TFM_COLUMN] = df[TFM_COLUMN].round().astype('Int64')
    df[TFM_BUFFER_COLUMN] = df[TFM_BUFFER_COLUMN].round().astype('Int64')

    logging.info(f"Succesvol '{TFM_COLUMN}' berekend. Opslaan naar '{OUTPUT_FILE}'...")
    df.to_csv(OUTPUT_FILE, sep=';', index=False)
    logging.info("Klaar.")

if __name__ == "__main__":
    main() 