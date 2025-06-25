#!/usr/bin/env python3
"""
Workflow script to run the entire ISU data processing pipeline:
1. Scrape data using isu_scraper.py
2. Add locations using add_location_to_conditions.py
3. Add weather data using add_weather_to_conditions_with_location.py
4. Calculate EstimatedTFM using calculate_estimated_tfm.py
5. Load data into a SQLite database using load_to_database.py
"""

import subprocess
import time
import sys
import os
import logging

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "workflow.log")

def setup_logging():
    """Set up logging to file and console."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_command(command, description):
    """Run a command and log its output"""
    logging.info(f"{'='*80}")
    logging.info(f"Running: {description} ({command})")
    logging.info(f"{'='*80}")
    
    start_time = time.time()
    
    python_exe = sys.executable
    full_command = f'"{python_exe}" {command}'
    
    try:
        result = subprocess.run(
            full_command,
            shell=True,
            text=True,
            check=True,
            capture_output=True,
            encoding='utf-8' # Add encoding for consistency
        )
        
        if result.stdout:
            logging.info("Output:\n" + result.stdout)
        if result.stderr:
            logging.error("Errors:\n" + result.stderr)
            
        end_time = time.time()
        logging.info(f"Completed '{description}' successfully in {end_time - start_time:.2f} seconds")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed '{description}' with return code {e.returncode}")
        logging.error("Error output:\n" + e.stderr)
        raise Exception(f"Command failed: {command}")
    
    return result

def main():
    """Main function to run the ETL workflow."""
    setup_logging()
    
    logging.info("Starting ISU data processing workflow...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    STEPS = {
        # Step 1: Scrape ISU Results
        "Scraping ISU Results": "isu_scraper.py",

        # Step 2: Enrich with SkaterIDs
        "Enriching with SkaterIDs": "skaterid_scraper.py",

        # Step 3: Enrich with Seasonal Bests
        "Enriching with Seasonal Bests": "seasonalbest_scraper.py",

        # Step 4: Add Weather Data
        "Adding Weather Data": "add_weather_to_conditions_with_location.py",

        # Step 5: Calculate Estimated TFM (Time From Mopping)
        # "Parsing PDF Schedules for Accurate TFM": "pdf_schedule_parser.py",
        "Calculating Estimated TFM": "calculate_estimated_tfm.py",

        # Step 6: Load to Database
        "Loading to SQLite Database": "load_to_database.py"
    }
    
    for description, script_name in STEPS.items():
        script_path = os.path.join(current_dir, script_name)
        run_command(script_path, description)
    
    logging.info("\n" + "="*80)
    logging.info("ETL WORKFLOW COMPLETED SUCCESSFULLY")
    logging.info("="*80)

if __name__ == "__main__":
    main()