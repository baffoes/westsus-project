# West-Sussex Speedskating Data Project

## Project Goal

This project aims to create a comprehensive and enriched dataset for speedskating performance analysis. By systematically scraping, cleaning, enriching, and storing data, it provides a robust foundation for building analytical models, generating insights, and creating dashboards. The primary goal is to understand the factors that influence race outcomes, including environmental conditions, rink characteristics, and individual skater performance metrics.

## Features

-   **Automated Data Pipeline**: A fully automated workflow to handle data scraping, processing, and database loading.
-   **Data Enrichment**: Augments raw data with valuable metrics such as unique skater IDs, historical seasonal bests, and local weather conditions.
-   **Error Handling & Logging**: Robust logging to monitor the workflow's progress and identify any issues.
-   **Modular Design**: Each step in the workflow is a separate script, making it easy to maintain, debug, and extend.
-   **SQLite Integration**: Stores the final, cleaned data in a portable and easy-to-use SQLite database.

## Prerequisites

Before you begin, ensure you have the following installed:

-   Python 3.8 or higher
-   `pip` for package management

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/westsus-project.git
    cd westsus-project
    ```

2.  **Install the required Python packages:**
    *It is recommended to use a virtual environment to avoid conflicts with other projects.*
    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

    # Install dependencies (assuming a requirements.txt file exists)
    pip install -r requirements.txt 
    ```
    *Note: If a `requirements.txt` file is not available, you may need to install packages like `requests` manually.*

## Usage

To run the entire data processing pipeline, execute the main workflow script from the project's root directory:

```bash
python datascraper/run_workflow.py
```

The script will run all the necessary steps in sequence, and you can monitor its progress in the console and review the detailed logs in the `logs/workflow.log` file.

## Workflow & File Descriptions

The data processing workflow is managed by `datascraper/run_workflow.py` and executes the following scripts in order:

1.  **`isu_scraper.py`**: Scrapes competition results and environmental conditions from the ISU results archive. This forms the foundational dataset.
2.  **`skaterid_scraper.py`**: Enriches the results data by querying an external API to find and add a unique ID for each skater based on their name and country. This is crucial for tracking individual athlete performance over time.
3.  **`seasonalbest_scraper.py`**: For each skater in a race, this script fetches their best time for that distance from the *previous* season. This provides a baseline performance metric.
4.  **`add_weather_to_conditions_with_location.py`**: Adds historical weather data (temperature and air pressure) to the conditions file. It uses the location of the event to fetch accurate meteorological data for the race date.
5.  **`calculate_estimated_tfm.py`**: Calculates the estimated time from mopping (TFM) for each pair of skaters in a race. This is based on the distance.
6.  **`load_to_database.py`**: Loads the final, processed, and enriched data from the CSV files into a SQLite database (`isu_data.db`). This makes the data accessible for querying and analysis.