#!/usr/bin/env python3
"""
Calculates Estimated Time From Mopping (TFM) for results in 'isu_results.csv'.
It applies a standard interval-based calculation and includes special logic
for 10,000m races, which often have a mid-session ice resurfacing break.
"""

import csv
import re
import logging
import sys
import os
from collections import defaultdict

# --- Configuration ---
INPUT_FILE = 'datascraper/data/isu_results.csv'
OUTPUT_COLUMNS = ['EstimatedTFM', 'EstimatedTFMBuffer']
TFM_BUFFER = 60  # Seconds to add for the TFM Buffer

# Standard intervals between pairs based on race distance (in seconds).
# These are based on typical competition schedules (e.g., Thialf).
INTERVAL_MAPPING = {
    '500': 135,
    '1000': 165,
    '1500': 200,
    '3000': 330,
    '5000': 480,
    '10000': 900,
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_distance_from_event(event_name):
    """Extracts the distance (e.g., '500') from an event name string."""
    if isinstance(event_name, str):
        match = re.search(r'(\d+)m', event_name)
        return match.group(1) if match else None
    return None

def read_data(filepath):
    """Reads the CSV data and returns it along with fieldnames."""
    if not os.path.exists(filepath):
        logging.error(f"Input file not found: {filepath}")
        return None, None
        
    with open(filepath, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile, delimiter=';')
        fieldnames = reader.fieldnames
        data = list(reader)
        
    if not data:
        logging.warning(f"Input file '{filepath}' is empty.")
    
    return data, fieldnames

def apply_standard_tfm(data):
    """Applies the standard TFM calculation to the dataset."""
    for row in data:
        try:
            pair = int(float(row.get('Pair', '')))
        except (ValueError, TypeError, AttributeError):
            pair = None

        distance = get_distance_from_event(row.get('Event'))
        
        if pair is not None and distance in INTERVAL_MAPPING:
            interval = INTERVAL_MAPPING[distance]
            tfm = (pair - 1) * interval
            row['EstimatedTFM'] = tfm
            row['EstimatedTFMBuffer'] = tfm + TFM_BUFFER
        else:
            row['EstimatedTFM'] = ''
            row['EstimatedTFMBuffer'] = ''
    return data

def apply_10000m_reset_logic(data):
    """
    Applies special TFM reset logic for 10,000m races.
    Assumes an ice resurfacing break occurs halfway through the competition,
    except for smaller races (e.g., with 4 or 6 pairs) where it's not needed.
    """
    races_10000m = defaultdict(list)
    for i, row in enumerate(data):
        if get_distance_from_event(row.get('Event')) == '10000':
            try:
                pair = int(float(row.get('Pair')))
                race_key = (row.get('Stadium'), row.get('Date'), row.get('Event'))
                races_10000m[race_key].append({'original_index': i, 'pair': pair})
            except (ValueError, TypeError, KeyError):
                continue

    for race_key, pairs_info in races_10000m.items():
        unique_pairs = sorted(list(set(p['pair'] for p in pairs_info)))
        num_unique_pairs = len(unique_pairs)

        # Skip reset for certain small race formats (e.g., 8 or 12 skaters total)
        if num_unique_pairs in [4, 6]:
            logging.info(f"Skipping 10000m TFM reset for race {race_key} with {num_unique_pairs} pairs.")
            continue
        
        # Determine the pair that starts after the mopping break
        halfway_point = (num_unique_pairs + 1) // 2
        first_pair_after_break = unique_pairs[halfway_point]
        
        # Reset TFM for all pairs skating after the break
        for skater_info in pairs_info:
            if skater_info['pair'] >= first_pair_after_break:
                # Calculate pairs elapsed since the break
                pairs_since_break = sorted(unique_pairs).index(skater_info['pair']) - halfway_point
                new_tfm = pairs_since_break * INTERVAL_MAPPING['10000']
                
                original_data_index = skater_info['original_index']
                data[original_data_index]['EstimatedTFM'] = new_tfm
                data[original_data_index]['EstimatedTFMBuffer'] = new_tfm + TFM_BUFFER
    return data

def write_data(filepath, data, fieldnames):
    """Writes the updated data back to the CSV file."""
    # Ensure output columns are in the header
    for col in OUTPUT_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)
            
    with open(filepath, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(data)

def main():
    """Main function to calculate and apply TFM values."""
    logging.info(f"Starting TFM calculation for '{INPUT_FILE}'.")

    data, fieldnames = read_data(INPUT_FILE)
    if data is None:
        sys.exit(1)
        
    if not data:
        logging.info("No data to process. Exiting.")
        return

    # Step 1: Apply the standard TFM calculation for all races
    data = apply_standard_tfm(data)
    logging.info("Applied standard TFM calculations.")

    # Step 2: Apply the special reset logic for 10,000m races
    data = apply_10000m_reset_logic(data)
    logging.info("Applied special 10,000m TFM reset logic.")

    # Step 3: Write the updated data back to the file
    write_data(INPUT_FILE, data, fieldnames)
    logging.info(f"Successfully updated '{INPUT_FILE}' with TFM calculations.")

if __name__ == "__main__":
    main() 