#!/usr/bin/env python3
"""
Loads the final transformed CSV files ('isu_results.csv', 'isu_conditions.csv')
into a SQLite database. This script constitutes the 'Load' phase of the ETL pipeline,
creating a clean, analysis-ready database file.
"""

import csv
import sqlite3
import sys
import logging
import os
import re

# --- Configuration ---
DATABASE_FILE = "isu_data.db"
# Mapping of table names to their source CSV files
TABLE_MAPPINGS = {
    'results': 'isu_results.csv',
    'conditions': 'isu_conditions.csv'
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

def load_csv_to_table(conn, table_name, csv_filepath):
    """
    Creates a new table from a CSV file, dropping the table if it already exists.
    Column names are sanitized, and all data is loaded as TEXT.
    """
    if not os.path.exists(csv_filepath):
        logging.error(f"CSV file not found at '{csv_filepath}'. Cannot create table '{table_name}'.")
        return

    try:
        with open(csv_filepath, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile, delimiter=';')
            header = next(reader)
            
            # Sanitize column names for SQL compatibility
            safe_header = [re.sub(r'[^A-Z0-9_]', '', h.strip().upper().replace(' ', '_')) for h in header]
            
            cursor = conn.cursor()
            
            logging.info(f"Preparing to load data into table '{table_name}'...")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            create_sql = f"CREATE TABLE {table_name} ({', '.join([f'{col} TEXT' for col in safe_header])})"
            cursor.execute(create_sql)
            
            insert_sql = f"INSERT INTO {table_name} VALUES ({', '.join(['?'] * len(safe_header))})"
            
            rows = list(reader)
            cursor.executemany(insert_sql, rows)
            
            conn.commit()
            logging.info(f"Table '{table_name}' created and loaded with {len(rows)} rows.")
            
    except (sqlite3.Error, csv.Error, FileNotFoundError) as e:
        logging.error(f"Failed to create or load table '{table_name}': {e}")
        conn.rollback()

def main():
    """Main function to orchestrate loading all CSVs into the database."""
    logging.info(f"Starting database load process -> '{DATABASE_FILE}'")
    
    conn = create_connection(DATABASE_FILE)
    if not conn:
        sys.exit(1)

    for table_name, csv_file in TABLE_MAPPINGS.items():
        logging.info(f"Processing '{csv_file}' -> table '{table_name}'.")
        load_csv_to_table(conn, table_name, csv_file)
        
    conn.close()
    logging.info(f"Database load process complete. '{DATABASE_FILE}' is ready for analysis.")

if __name__ == "__main__":
    main() 