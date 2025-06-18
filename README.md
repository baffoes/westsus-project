# ISU Data Pipeline

This project is a complete, fully automated ETL (Extract, Transform, Load) pipeline designed to collect, enrich, and store speed skating data. It pulls data from the official ISU (International Skating Union) API, enriches it with historical weather from the Open-Meteo API, calculates key metrics, and loads everything into a clean, analysis-ready SQLite database.

## Workflow

The entire pipeline is executed by a single master script, `run_workflow.py`, which calls all other scripts in the correct sequence. The process is designed to be robust and idempotent, meaning it can be run multiple times with the same predictable outcome.

To run the entire workflow, execute the following command in your terminal:
```bash
python run_workflow.py
```

All output, progress, and errors are logged to `logs/workflow.log`.

---

## Script Descriptions

### 1. `run_workflow.py` - Workflow Orchestrator
- **Purpose:** This is the main script that orchestrates the entire ETL pipeline.
- **Function:** It executes each Python script as a separate process and logs its output, start time, end time, and success or failure status. If any step fails, the workflow stops to prevent data corruption.
- **Output:** A detailed log file at `logs/workflow.log`.

### 2. `isu_scraper.py` - Step 1: Extract (E)
- **Purpose:** To scrape all raw competition data from the ISU Results API.
- **Function:**
    - Uses a multi-threaded approach to fetch data for all historical events in parallel, handling API pagination dynamically to ensure all past and future data is collected.
    - Filters out non-individual events (like Team Sprint, Mass Start).
    - Parses the JSON responses to extract results and measurement conditions. Crucially, it captures the **event's city, latitude, and longitude** directly from the API for maximum accuracy.
- **Output:**
    - `isu_results.csv`: Contains the results for every individual skater in every race.
    - `isu_conditions.csv`: Contains the ice/air conditions for each competition, including the precise `Location`, `Latitude`, and `Longitude`.

### 3. `add_weather_to_conditions_with_location.py` - Step 2: Transform (T)
- **Purpose:** To add historical, hourly weather data to each competition.
- **Function:**
    - Reads `isu_conditions.csv`.
    - It uses the **latitude and longitude** from the file to query the Open-Meteo API, making the script independent of hardcoded locations.
    - To avoid being blocked by the API (rate-limiting), it uses an ultra-safe, sequential, year-by-year approach with a patient retry mechanism.
    - After successfully fetching weather data, it **removes the `Location`, `Latitude`, and `Longitude` columns** from the final CSV to keep the dataset clean.
- **Input:** `isu_conditions.csv`.
- **Output:** An updated `isu_conditions.csv` enriched with `TempOutdoors`, `AirpressureSurface`, and `AirpressureSealevel`.

### 4. `calculate_estimated_tfm.py` - Step 3: Transform (T)
- **Purpose:** To calculate the "Estimated Time From Mopping" (TFM), a key metric for analysis.
- **Function:**
    - Reads `isu_results.csv`.
    - It calculates `EstimatedTFM` and `EstimatedTFMBuffer` based on the race distance and the skater's pair number.
    - Includes special logic for 10,000m races, where an ice-resurfacing break is assumed to occur halfway through.
- **Input:** `isu_results.csv`
- **Output:** An updated `isu_results.csv` with `EstimatedTFM` and `EstimatedTFMBuffer` columns added.

### 5. `load_to_database.py` - Step 4: Load (L)
- **Purpose:** To load the final, clean data into a structured database.
- **Function:**
    - Creates or connects to a SQLite database file named `isu_data.db`.
    - It drops any existing tables to ensure a clean slate on every run.
    - It loads all data from the final `isu_results.csv` and `isu_conditions.csv` files into two new tables: `results` and `conditions`.
- **Input:** `isu_results.csv` and `isu_conditions.csv`.
- **Output:** The final `isu_data.db` database file, ready for analysis.

---

## Automation and Future-Proofing

The pipeline is designed to be fully automated and requires no code changes for future updates:

- **New Venues:** If the ISU adds events at a new venue, the scraper will automatically extract the new location's name and coordinates from the API. The weather script will then use these new coordinates without any manual intervention.
- **Future Seasons:** The scraper does not have a hardcoded end date. It dynamically fetches all available pages of events from the API. When data for the 2026 season (and beyond) is released, it will be automatically included in the next pipeline run.

The only manual step is initiating the `run_workflow.py` script. This can be scheduled to run automatically using **Task Scheduler** (Windows) or **cron** (macOS/Linux).