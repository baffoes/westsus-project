import csv
import requests
import re
from functools import lru_cache
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Connection pool with keep-alive
session = requests.Session()
session.headers.update({
    'Connection': 'keep-alive',
    'Keep-Alive': 'timeout=30, max=100'
})

class RateLimiter:
    def __init__(self, calls_per_second=20):  # Adjust to API limits
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.lock = threading.Lock()
        self.last_called = 0

    def wait(self):
        with self.lock:
            elapsed = time.time() - self.last_called
            sleep_time = self.min_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.last_called = time.time()

rate_limiter = RateLimiter(20)

def time_to_seconds(time_str):
    """Convert API time format to seconds with 2 decimals"""
    if not time_str or time_str.strip() == '':
        return None
    try:
        time_str = time_str.strip()
        # Examples: "36,07" => 36.07, "1.11,55" => 71.55, "4:00.393" => 240.393
        if '.' in time_str and ',' in time_str:
            # M.SS,ss format like 1.11,55
            minutes = int(time_str.split('.')[0])
            seconds = float(time_str.split('.')[1].replace(',', '.'))
            return round(minutes * 60 + seconds, 2)
        elif ',' in time_str:
            # SS,ss format like 36,07
            return round(float(time_str.replace(',', '.')), 2)
        elif ':' in time_str:
            # MM:SS.sss format like 4:00.393
            minutes, seconds = time_str.split(':')
            return round(int(minutes) * 60 + float(seconds), 2)
        else:
            # Simple float seconds
            return round(float(time_str), 2)
    except Exception as e:
        print(f"Failed to parse time '{time_str}': {e}")
        return None

season_cache = {}
cache_lock = threading.Lock()

def fetch_previous_season_data(skater_id, current_season_year, max_retries=3):
    previous_season_year = current_season_year - 1
    cache_key = (skater_id, previous_season_year)

    with cache_lock:
        if cache_key in season_cache:
            return season_cache[cache_key]

    if not skater_id or not skater_id.isdigit():
        with cache_lock:
            season_cache[cache_key] = {}
        return {}

    url = f"https://speedskatingresults.com/api/json/season_bests?skater={skater_id}&start={previous_season_year}&end={previous_season_year}"

    delay = 1
    for attempt in range(max_retries):
        rate_limiter.wait()
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                seasons = data.get("seasons", [])
                distance_times = {}
                for season in seasons:
                    if season.get('start') == previous_season_year:
                        for record in season.get("records", []):
                            dist = record.get("distance")
                            time_str = record.get("time", "")
                            secs = time_to_seconds(time_str)
                            if dist and secs is not None:
                                distance_times[dist] = secs
                        break
                with cache_lock:
                    season_cache[cache_key] = distance_times
                return distance_times
            else:
                print(f"API error {response.status_code} for skater {skater_id} season {previous_season_year}")
        except Exception as e:
            print(f"Exception fetching data for skater {skater_id} season {previous_season_year}: {e}")
        time.sleep(delay)
        delay *= 2  # exponential backoff

    with cache_lock:
        season_cache[cache_key] = {}
    return {}

# Extract numeric distance from event string like '3000m_Women
def extract_distance(event):

    if not event:
        return None
    match = re.search(r"(\d+)", event)
    if match:
        return int(match.group(1))
    return None

# Process a single CSV row, fetch previous season best seconds for skater & distance
def process_row(row_idx, row):
    skater_id = row.get("SkaterID", "").strip()
    date_str = row.get("Date", "").strip()
    event = row.get("Event", "").strip()

    season_best = ""

    if not (skater_id and date_str and event):
        row['SeasonalBest'] = season_best
        return (row_idx, row)

    try:
        # Your input dates seem like '2025-03-13', parse accordingly
        race_date = datetime.strptime(date_str, "%Y-%m-%d")
        current_season_year = race_date.year
    except Exception as e:
        print(f"Error parsing date '{date_str}' in row {row_idx}: {e}")
        row['SeasonalBest'] = season_best
        return (row_idx, row)

    distance = extract_distance(event)
    if distance is None:
        row['SeasonalBest'] = season_best
        return (row_idx, row)

    previous_season_data = fetch_previous_season_data(skater_id, current_season_year)

    if distance in previous_season_data:
        season_best = f"{previous_season_data[distance]:.2f}"

    row['SeasonalBest'] = season_best
    return (row_idx, row)

def add_seasonalbests(input_file, output_file, max_workers=20, batch_size=1000):
    print("Loading input CSV...")
    with open(input_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        rows = list(reader)

    if not rows:
        print("No rows found in input CSV.")
        return

    fieldnames = list(rows[0].keys()) + ['SeasonalBest']

    print(f"Processing {len(rows)} rows with {max_workers} workers...")

    processed_rows = [None] * len(rows)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_row, idx, row): idx for idx, row in enumerate(rows)}

        for i, future in enumerate(as_completed(futures), 1):
            idx = futures[future]
            try:
                row_idx, processed_row = future.result()
                processed_rows[row_idx] = processed_row
            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                processed_rows[idx] = rows[idx]  # fallback original row

            if i % 1000 == 0 or i == len(rows):
                print(f"Processed {i}/{len(rows)} rows")

    #delete row skater_id
    for row in processed_rows:
        if 'SkaterID' in row:
            del row['SkaterID']
    
    # Remove SkaterID from column headers
    if 'SkaterID' in fieldnames:
     fieldnames.remove('SkaterID')

    print("Writing output CSV...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(processed_rows)

    print(f"Done! Output saved to {output_file}")

if __name__ == "__main__":
    start = time.time()
    add_seasonalbests("datascraper/data/isu_results.csv", "datascraper/data/isu_results.csv")
    print(f"Completed in {time.time() - start:.2f} seconds")
