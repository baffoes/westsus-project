#!/usr/bin/env python3
"""
Loads the final transformed CSV files ('isu_results.csv', 'isu_conditions.csv')
into a SQLite database. This script constitutes the 'Load' phase of the ETL pipeline,
creating a clean, analysis-ready database file with exact schema specifications.
"""

import csv
import sqlite3
import sys
import logging
import os
import pandas as pd
import numpy as np

# --- Configuration ---
DATABASE_FILE = "isu_data.db"
# Mapping of table names to their source CSV files
TABLE_MAPPINGS = {
    'results': 'datascraper/data/isu_results.csv',
    'conditions': 'datascraper/data/isu_conditions.csv'
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_connection(db_file):
    """Creates and returns a database connection."""
    try:
        conn = sqlite3.connect(db_file)
        logging.info(f"Successfully connected to database '{db_file}'.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        sys.exit(1)

def create_results_table(conn):
    """Create results table with exact schema specifications"""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS results")
    
    create_sql = '''
        CREATE TABLE results (
            Stadium TEXT,
            Date TEXT,
            Event TEXT,
            Race TEXT,
            Rank INTEGER,
            Nr INTEGER,
            Name TEXT,
            Country TEXT,
            Pair INTEGER,
            Lane TEXT,
            Time TEXT,
            Behind REAL,
            Gender TEXT,
            SkaterID INTEGER,
            SeasonalBest REAL,
            EstimatedTFM INTEGER,
            EstimatedTFMBuffer INTEGER
        )
    '''
    cursor.execute(create_sql)
    logging.info("Created results table with correct schema")

def create_conditions_table(conn):
    """Create conditions table with exact schema specifications"""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS conditions")
    
    create_sql = '''
        CREATE TABLE conditions (
            Stadium TEXT,
            Date TEXT,
            Event TEXT,
            Race TEXT,
            Country TEXT,
            Distance INTEGER,
            Occassion TEXT,
            Time TEXT,
            TempIndoors REAL,
            IceTemperature REAL,
            Humidity REAL,
            TempOutdoors REAL,
            AirpressureSurface REAL,
            AirpressureSealevel REAL
        )
    '''
    cursor.execute(create_sql)
    logging.info("Created conditions table with correct schema")

def safe_convert_to_int(series, default=0):
    """Safely convert series to integer, handling NaN values"""
    try:
        # Convert to numeric first, then fill NaN with default, then convert to int
        numeric_series = pd.to_numeric(series, errors='coerce')
        filled_series = numeric_series.fillna(default)
        return filled_series.astype(int)
    except:
        # If conversion fails, return series filled with default values
        return pd.Series([default] * len(series))

def safe_convert_to_float(series, default=0.0):
    """Safely convert series to float, handling NaN values"""
    try:
        numeric_series = pd.to_numeric(series, errors='coerce')
        return numeric_series.fillna(default)
    except:
        return pd.Series([default] * len(series))

def load_results_data(conn, csv_filepath):
    """Load results data with proper column mapping and data types"""
    if not os.path.exists(csv_filepath):
        logging.error(f"CSV file not found at '{csv_filepath}'.")
        return

    try:
        # Read CSV data
        df = pd.read_csv(csv_filepath, delimiter=';')
        logging.info(f"Loaded {len(df)} results records from CSV")
        
        # Map columns to match exact schema with proper type handling
        results_mapped = pd.DataFrame({
            'Stadium': df.get('Stadium', pd.Series([''] * len(df))).astype(str),
            'Date': df.get('Date', pd.Series([''] * len(df))).astype(str),
            'Event': df.get('Event', pd.Series([''] * len(df))).astype(str),
            'Race': df.get('Race', pd.Series([''] * len(df))).astype(str),
            'Rank': safe_convert_to_int(df.get('Rank', pd.Series([0] * len(df)))),
            'Nr': safe_convert_to_int(df.get('Nr', pd.Series([0] * len(df)))),
            'Name': df.get('Name', pd.Series([''] * len(df))).astype(str),
            'Country': df.get('Country', pd.Series([''] * len(df))).astype(str),
            'Pair': safe_convert_to_int(df.get('Pair', pd.Series([0] * len(df)))),
            'Lane': df.get('Lane', pd.Series([''] * len(df))).astype(str),
            'Time': df.get('Time', pd.Series([''] * len(df))).astype(str),
            'Behind': safe_convert_to_float(df.get('Behind', pd.Series([0.0] * len(df)))),
            'Gender': df.get('Gender', pd.Series([''] * len(df))).astype(str),
            'SkaterID': safe_convert_to_int(df.get('SkaterID', pd.Series([0] * len(df)))),
            'SeasonalBest': safe_convert_to_float(df.get('SeasonalBest', pd.Series([0.0] * len(df)))),
            'EstimatedTFM': safe_convert_to_int(df.get('EstimatedTFM', pd.Series([0] * len(df)))),
            'EstimatedTFMBuffer': safe_convert_to_int(df.get('EstimatedTFMBuffer', pd.Series([0] * len(df))))
        })
        
        # Insert data into database
        results_mapped.to_sql('results', conn, if_exists='append', index=False)
        logging.info(f"Successfully inserted {len(results_mapped)} results records")
        
    except Exception as e:
        logging.error(f"Failed to load results data: {e}")
        conn.rollback()

def load_conditions_data(conn, csv_filepath):
    """Load conditions data with proper column mapping and data types"""
    if not os.path.exists(csv_filepath):
        logging.error(f"CSV file not found at '{csv_filepath}'.")
        return
    
    try:
        # Read CSV data
        df = pd.read_csv(csv_filepath, delimiter=';')
        logging.info(f"Loaded {len(df)} conditions records from CSV")
        
        # Map columns to match exact schema (note: mapping 'Occasion' to 'Occassion' as per spec)
        conditions_mapped = pd.DataFrame({
            'Stadium': df.get('Stadium', pd.Series([''] * len(df))).astype(str),
            'Date': df.get('Date', pd.Series([''] * len(df))).astype(str),
            'Event': df.get('Event', pd.Series([''] * len(df))).astype(str),
            'Race': df.get('Race', pd.Series([''] * len(df))).astype(str),
            'Country': df.get('Country', pd.Series([''] * len(df))).astype(str),
            'Distance': safe_convert_to_int(df.get('Distance', pd.Series([0] * len(df)))),
            'Occassion': df.get('Occasion', pd.Series([''] * len(df))).astype(str),  # Note: CSV has 'Occasion', DB schema has 'Occassion'
            'Time': df.get('Time', pd.Series([''] * len(df))).astype(str),
            'TempIndoors': safe_convert_to_float(df.get('TempIndoors', pd.Series([0.0] * len(df)))),
            'IceTemperature': safe_convert_to_float(df.get('IceTemperature', pd.Series([0.0] * len(df)))),
            'Humidity': safe_convert_to_float(df.get('Humidity', pd.Series([0.0] * len(df)))),
            'TempOutdoors': safe_convert_to_float(df.get('TempOutdoors', pd.Series([0.0] * len(df)))),
            'AirpressureSurface': safe_convert_to_float(df.get('AirpressureSurface', pd.Series([0.0] * len(df)))),
            'AirpressureSealevel': safe_convert_to_float(df.get('AirpressureSealevel', pd.Series([0.0] * len(df))))
        })
        
        # Insert data into database
        conditions_mapped.to_sql('conditions', conn, if_exists='append', index=False)
        logging.info(f"Successfully inserted {len(conditions_mapped)} conditions records")
        
    except Exception as e:
        logging.error(f"Failed to load conditions data: {e}")
        conn.rollback()

def main():
    """Main function to orchestrate loading all CSVs into the database with correct schema."""
    logging.info(f"Starting database load process -> '{DATABASE_FILE}'")
    
    conn = create_connection(DATABASE_FILE)
    if not conn:
        sys.exit(1)

    try:
        # Create tables with exact schema
        create_results_table(conn)
        create_conditions_table(conn)
        
        # Load data with proper type conversion
        load_results_data(conn, TABLE_MAPPINGS['results'])
        load_conditions_data(conn, TABLE_MAPPINGS['conditions'])
        
        conn.commit()
        logging.info(f"Database load process complete. '{DATABASE_FILE}' is ready for analysis.")
        
    except Exception as e:
        logging.error(f"Database load failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main() 