#!/usr/bin/env python3
"""
Adds historical weather data to 'isu_conditions.csv' using the Open-Meteo API.
It fetches temperature and air pressure based on location and date/time,
then enriches the original CSV file with this data.
"""

import csv
import requests
import time
import logging
import os
import sys
import random
from datetime import datetime
from collections import defaultdict

# --- Configuration ---
INPUT_FILE = 'isu_conditions.csv'
WEATHER_COLUMNS = ['TempOutdoors', 'AirpressureSurface', 'AirpressureSealevel']
API_TIMEOUT = 30
# Delay between each YEARLY request to be respectful to the API.
REQUEST_DELAY = 1

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_weather_for_location(location_name, lat, lon, dates, max_retries=4):
    """
    Fetches weather data for a set of dates for a single location.
    Includes a very patient retry mechanism with exponential backoff for rate limiting (429 errors).
    """
    if not dates:
        return {}

    min_date_str = min(d[0] for d in dates)
    max_date_str = max(d[0] for d in dates)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        'latitude': lat, 'longitude': lon,
        'start_date': min_date_str, 'end_date': max_date_str,
        'hourly': 'temperature_2m,surface_pressure,pressure_msl',
        'timezone': 'UTC'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json().get('hourly', {})
            
            if not data.get('time'):
                logging.warning(f"No hourly data returned for {location_name}.")
                return {}

            time_to_index = {time_str: i for i, time_str in enumerate(data['time'])}
            weather_results = {}
            for date_str, hour in dates:
                target_time = f"{date_str}T{hour:02d}:00"
                if target_time in time_to_index:
                    idx = time_to_index[target_time]
                    weather_results[(date_str, hour)] = {
                        'TempOutdoors': data['temperature_2m'][idx],
                        'AirpressureSurface': data['surface_pressure'][idx],
                        'AirpressureSealevel': data['pressure_msl'][idx]
                    }
            logging.info(f"Successfully retrieved {len(weather_results)} weather records for {location_name}.")
            return weather_results

        except requests.exceptions.HTTPError as e:
            # If rate-limited, wait with a patient exponential backoff before retrying.
            if e.response.status_code == 429 and attempt < max_retries - 1:
                # Exponential backoff: 4s, 8s, 16s
                wait_time = 2 ** (attempt + 2)
                logging.warning(
                    f"Rate limited for {location_name}. Retrying in {wait_time} seconds... "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                continue
            logging.error(f"API request failed for {location_name}: {e}")
            break  # For other HTTP errors, don't retry.
        except requests.RequestException as e:
            logging.error(f"Network error for {location_name}: {e}")
            break  # For network errors, don't retry.
        except (KeyError, IndexError) as e:
            logging.error(f"Error parsing weather data for {location_name}: {e}")
            break  # For data parsing errors, don't retry.
            
    return {}

def parse_time_to_hour(time_str):
    """Safely parse a time string to an integer hour."""
    if isinstance(time_str, str) and ':' in time_str:
        try:
            return int(time_str.split(':')[0])
        except (ValueError, IndexError):
            pass
    return None

def read_and_prepare_requests(filepath):
    """Reads CSV and groups rows by location coordinates for batch API requests."""
    if not os.path.exists(filepath):
        logging.error(f"Input file not found: {filepath}")
        return None, None, None

    with open(filepath, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile, delimiter=';')
        data = list(reader)
        original_fieldnames = reader.fieldnames
    
    if not data:
        logging.warning(f"Input file '{filepath}' is empty.")
        return data, original_fieldnames, defaultdict(set)

    location_requests = defaultdict(set)
    for row in data:
        loc_name = row.get('Location')
        lat = row.get('Latitude')
        lon = row.get('Longitude')
        date_str = row.get('Date')
        hour = parse_time_to_hour(row.get('Time'))
        
        if lat and lon and date_str and hour is not None:
            try:
                # Use a tuple of coordinates as the key for batching requests.
                # Include location name for logging purposes.
                key = (lat, lon, loc_name)
                # The date format from the scraper is now YYYY-MM-DD
                datetime.strptime(date_str, "%Y-%m-%d") # Validate date format
                location_requests[key].add((date_str, hour))
            except (ValueError, TypeError):
                logging.warning(f"Skipping row with invalid lat/lon or date format: {lat}, {lon}, {date_str}")
    
    return data, original_fieldnames, location_requests

def fetch_all_weather(location_requests):
    """
    Fetches weather data sequentially, year-by-year for each location,
    to avoid large API requests that can be rate-limited. This is the safest, most reliable method.
    """
    all_weather_data = {}
    total_locations = len(location_requests)
    logging.info(f"Fetching weather data for {total_locations} unique locations sequentially (ultra-safe, year-by-year mode)...")

    for i, ((lat, lon, loc_name), dates) in enumerate(location_requests.items()):
        logging.info(f"Processing location {i + 1}/{total_locations}: {loc_name} ({lat}, {lon})")

        # Group all date requests for this location by year
        dates_by_year = defaultdict(list)
        for date_str, hour in dates:
            year = date_str.split('-')[0]
            dates_by_year[year].append((date_str, hour))

        location_weather = {}
        # For each year, make a separate, smaller API request
        for year_index, (year, year_dates) in enumerate(sorted(dates_by_year.items())):
            logging.info(f"  Fetching data for {loc_name} for the year {year}...")

            # get_weather_for_location is called with a much smaller, single-year date range
            weather_chunk = get_weather_for_location(loc_name, lat, lon, year_dates)

            if weather_chunk:
                location_weather.update(weather_chunk)

            # Wait between each yearly request to be extra safe
            if year_index < len(dates_by_year) - 1:
                logging.info(f"Waiting for {REQUEST_DELAY} second(s) before next yearly request...")
                time.sleep(REQUEST_DELAY)

        if location_weather:
            # Key the results by a lat/lon tuple for easy lookup later
            all_weather_data[(lat, lon)] = location_weather
        else:
            logging.warning(f"Could not retrieve any weather data for {loc_name} across all years.")

        logging.info(f"Finished processing all years for {loc_name}.")
        # Also wait between locations
        if i < total_locations - 1:
            time.sleep(REQUEST_DELAY)

    return all_weather_data

def update_data_with_weather(data, all_weather_data):
    """Updates the dataset with the fetched weather information."""
    rows_updated = 0
    for row in data:
        lat = row.get('Latitude')
        lon = row.get('Longitude')
        date_str = row.get('Date')
        hour = parse_time_to_hour(row.get('Time'))
        
        # Look up weather data using lat/lon coordinates
        key = (lat, lon)
        if key in all_weather_data and date_str and hour is not None:
            try:
                # The date format from the scraper is already YYYY-MM-DD
                weather = all_weather_data[key].get((date_str, hour))
                if weather:
                    row.update(weather)
                    rows_updated += 1
            except (ValueError, KeyError):
                continue
    return data, rows_updated

def write_updated_data(filepath, data, original_fieldnames):
    """Writes the enriched data back to the CSV file, removing temporary columns."""
    # Add new weather columns to the header
    final_fieldnames = original_fieldnames[:]
    for col in WEATHER_COLUMNS:
        if col not in final_fieldnames:
            final_fieldnames.append(col)

    # Define and remove the columns that are no longer needed
    columns_to_remove = ['Location', 'Latitude', 'Longitude']
    logging.info(f"Removing temporary columns before writing to file: {', '.join(columns_to_remove)}")
    final_fieldnames = [field for field in final_fieldnames if field not in columns_to_remove]

    # Also remove the data from the rows themselves
    for row in data:
        for col in columns_to_remove:
            row.pop(col, None) # Use pop to avoid errors if a column is missing
    
    with open(filepath, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=final_fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(data)

def main():
    """Main function to orchestrate adding weather data."""
    logging.info(f"Starting to add weather data to '{INPUT_FILE}'.")
    
    data, original_fieldnames, location_requests = read_and_prepare_requests(INPUT_FILE)
    if data is None:
        sys.exit(1)
    
    if not location_requests:
        logging.info("No locations found needing weather data. Exiting.")
        return

    logging.info(f"Found {len(location_requests)} locations that need weather data.")
    
    all_weather_data = fetch_all_weather(location_requests)
    
    updated_data, rows_updated = update_data_with_weather(data, all_weather_data)
    
    write_updated_data(INPUT_FILE, updated_data, original_fieldnames)
    
    logging.info(f"Successfully enriched and saved '{INPUT_FILE}': updated {rows_updated:,} of {len(data):,} rows.")

if __name__ == "__main__":
    main()
