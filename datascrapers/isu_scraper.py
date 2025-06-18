import csv
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# Regex die veelvoorkomende mojibake detecteert (zoals "Ã¶", "Ã¤", etc.)
MOJIBAKE_PATTERN = re.compile(r"[Ã][^\s]{1,2}")

def fix_encoding(text):
    """Detects and fixes common mojibake artifacts by re-decoding Latin-1-encoded UTF-8 text."""
    if isinstance(text, str):
        try:
            if MOJIBAKE_PATTERN.search(text):
                # Double-encoded UTF-8 (interpreted as Latin-1)
                fixed = text.encode("latin-1").decode("utf-8")
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


# Thread-safe session with connection pooling
session = requests.Session()
session.mount('https://', requests.adapters.HTTPAdapter(
    pool_connections=20,
    pool_maxsize=100,
    max_retries=3
))

def safe_get_json(url, retries=3, delay=0.1, timeout=10, params=None):
    for attempt in range(retries):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                # Ensure proper UTF-8 encoding
                response.encoding = 'utf-8'
                return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                print(f"[ERROR] All attempts failed for {url}: {e}")
        time.sleep(delay)
    return None


def fetch_events_page(page):
    data = safe_get_json("https://api.isuresults.eu/events/", params={"page": page})
    if data:
        events = data.get("results", data) if isinstance(data, dict) else data
        return events if events else []
    return []

def fetch_all_events_parallel():
    print("Fetching events in parallel...")
    first_page_events = fetch_events_page(1)
    if not first_page_events:
        print("[WARNING] No data found on first page of events")
        return []
    all_events = first_page_events[:]
    max_pages = 50
    max_workers = 10

    def fetch_page_with_number(page_num):
        events = fetch_events_page(page_num)
        return page_num, events

    batch_size = max_workers
    for start_page in range(2, max_pages + 1, batch_size):
        end_page = min(start_page + batch_size - 1, max_pages)
        pages_to_fetch = list(range(start_page, end_page + 1))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {executor.submit(fetch_page_with_number, page): page for page in pages_to_fetch}

            batch_has_data = False
            for future in as_completed(future_to_page):
                page_num, events = future.result()
                if events:
                    all_events.extend(events)
                    batch_has_data = True

            print(f"Fetched pages {start_page}-{end_page}, found {len(all_events)} total events")

            if not batch_has_data:
                break

    return all_events

latitude=""
longitude=""

def process_single_event(event_id):
    base_event_url = f"https://api.isuresults.eu/events/{event_id}"
    competitions_url = f"{base_event_url}/competitions"

    track_data = safe_get_json(base_event_url)
    if not track_data:
        print(f"[WARNING] No track data found for event {event_id}")
        return [], []

    latitude = track_data.get("track", {}).get("latitude")
    longitude = track_data.get("track", {}).get("longitude")
    city = fix_encoding(track_data.get("track", {}).get("city", ""))
    stadium = fix_encoding(track_data.get("track", {}).get("name", ""))
    event_name = fix_encoding(track_data.get("name", ""))

    competitions = safe_get_json(competitions_url)
    if not competitions:
        print(f"[WARNING] No competitions found for event {event_id}")
        return [], []

    valid_competitions = []
    for comp in competitions:
        schedule_number = comp.get("scheduleNumber")
        title = comp.get("title", "").lower()
        if any(skip in title for skip in ["team", "mass", "mixed"]):
            continue
        if not schedule_number:
            continue
        valid_competitions.append((schedule_number, fix_encoding(comp.get("title", f"Competition {schedule_number}"))))

    if not valid_competitions:
        print(f"[INFO] No valid competitions found for event {event_id}")
        return [], []

    def fetch_competition_data(comp_info):
        schedule_number, race_name = comp_info
        conditions_url = f"{base_event_url}/competitions/{schedule_number}/"
        result_url = f"{base_event_url}/competitions/{schedule_number}/results/?inSeconds=0"

        with ThreadPoolExecutor(max_workers=2) as executor:
            conditions_future = executor.submit(safe_get_json, conditions_url)
            results_future = executor.submit(safe_get_json, result_url)

            conditions_data_comp = conditions_future.result()
            results_comp = results_future.result()

        return schedule_number, race_name, conditions_data_comp, results_comp

    event_results = []
    event_conditions = []
    batch_size = 5
    for i in range(0, len(valid_competitions), batch_size):
        batch = valid_competitions[i:i+batch_size]

        with ThreadPoolExecutor(max_workers=min(batch_size, 5)) as executor:
            batch_results = list(executor.map(fetch_competition_data, batch))

        for schedule_number, race_name, conditions_data_comp, results_comp in batch_results:
            if not conditions_data_comp:
                print(f"[WARNING] No conditions data found for competition {schedule_number} in event {event_id} - skipping results")
                continue
            elif not results_comp:
                print(f"[WARNING] No results data found for competition {schedule_number} in event {event_id}")
                continue

            conditions = conditions_data_comp.get('conditions', [])
            distance = conditions_data_comp.get("distance",{}).get("distance")
            if not conditions:
                print(f"[INFO] No conditions available for competition {schedule_number} in event {event_id} - skipping results")
                continue

            for condition in conditions:
                timestamp = condition.get("timeStamp")
                if not timestamp:
                    continue

                try:
                    time_only = datetime.fromisoformat(timestamp.replace("Z", "")).time().isoformat()
                    date = datetime.fromisoformat(timestamp.replace("Z", "")).strftime("%Y-%m-%d")
                except Exception:
                    time_only = ""
                    date = ""

                airTemp = condition.get("airTemperature")
                iceTemp = condition.get("iceTemperature")
                humidity = condition.get("humidity")
                if airTemp is None or iceTemp is None or humidity is None:
                    print(f"[WARNING] Missing condition data for competition {schedule_number} in event {event_id} - skipping results")
                    continue

                event_conditions.append({
                    'Stadium': fix_encoding(stadium).replace(" ", "_"),
                    'Location': city.replace(" ", "_") if city else '',
                    'Latitude': latitude,
                    'Longitude': longitude,
                    'Date': date,
                    'Event': event_name.replace(" ", "_"),
                    'Race': race_name.replace(" ", "_"),
                    'Country': fix_encoding(track_data.get("track", {}).get("country", "")),
                    'Distance': distance,
                    'Occasion': fix_encoding(condition.get('occasion', '')),
                    'Time': time_only,
                    'TempIndoors': airTemp,
                    'IceTemperature': iceTemp,
                    'Humidity': humidity,
                })

            results = results_comp if isinstance(results_comp, list) else [results_comp]
            valid_results = []
            for r in results:
                time_val = r.get("time")
                if not time_val:
                    continue
                competitor = r.get("competitor")
                if not competitor or "skater" not in competitor:
                    continue
                valid_results.append(r)

            if not valid_results:
                print(f"[INFO] No valid results found for competition {schedule_number} in event {event_id}")

            for r in valid_results:
                competitor = r["competitor"]
                skater = competitor["skater"]
                first_name = fix_encoding(skater.get("firstName", ""))
                last_name = fix_encoding(skater.get("lastName", "")).replace(" ", "_")
                full_name = f"{first_name}_{last_name}"

                country = fix_encoding(skater.get("country", ""))

                gender = skater.get("gender", "")
                if gender == "F":
                    gender = "Women"
                elif gender == "M":
                    gender = "Men"
                
                event_results.append([
                    fix_encoding(stadium).replace(" ", "_"),
                    date,
                    event_name.replace(" ", "_"),
                    race_name.replace(" ", "_"),
                    r.get("rank", ""),
                    competitor.get("number", ""),
                    full_name,
                    country,
                    r.get("startNumber", ""),
                    r.get("startLane", ""),
                    r.get("time"),
                    r.get("timeBehind", ""),
                    gender
                ])

    return event_results, event_conditions

  
def main():
    print("Starting optimized ISU data collection...")
    start_time = time.time()

    all_events = fetch_all_events_parallel()
    if not all_events:
        print("[ERROR] No events found. Exiting.")
        return

    isu_ids = [event.get("isuId", "") for event in all_events if event.get("isuId")]
    if not isu_ids:
        print("[ERROR] No valid ISU IDs found in events. Exiting.")
        return

    print(f"Found {len(isu_ids)} events")

    # Ensure UTF-8 encoding when writing CSV files
    with open("isu_results.csv", "w", newline='', encoding="utf-8") as result_file:
        result_writer = csv.writer(result_file, delimiter=';')
        result_writer.writerow(["Stadium","Date","Event","Race","Rank", "Nr", "Name", "Country", "Pair", "Lane", "Time", "Behind","Gender"])

    condition_fieldnames = ['Stadium', 'Location', 'Latitude', 'Longitude', 'Date','Event','Race','Country','Distance','Occasion', 'Time', 'TempIndoors', 'IceTemperature', 'Humidity', 'AirpressureSurface', 'AirpressureSealevel']
    with open("isu_conditions.csv", mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=condition_fieldnames, delimiter=';')
        writer.writeheader()

    max_workers = 6
    def process_event_with_progress(event_id):
        results, conditions = process_single_event(event_id)
        return len(results), len(conditions), results, conditions

    batch_size = 15
    total_results = 0
    total_conditions = 0

    for i in range(0, len(isu_ids), batch_size):
        batch = isu_ids[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(isu_ids)-1)//batch_size + 1} ({len(batch)} events)")

        batch_results = []
        batch_conditions = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_event_with_progress, event_id) for event_id in batch]

            for future in as_completed(futures):
                try:
                    result_count, condition_count, results, conditions = future.result()
                    batch_results.extend(results)
                    batch_conditions.extend(conditions)
                    total_results += result_count
                    total_conditions += condition_count
                except Exception as e:
                    print(f"[ERROR] Error processing event: {e}")

        if batch_results:
            print(f"Writing {len(batch_results)} results from batch {i//batch_size + 1}...")
            with open("isu_results.csv", "a", newline='', encoding="utf-8") as result_file:
                result_writer = csv.writer(result_file, delimiter=';')
                result_writer.writerows(batch_results)

        if batch_conditions:
            print(f"Writing {len(batch_conditions)} conditions from batch {i//batch_size + 1}...")
            with open("isu_conditions.csv", mode='a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=condition_fieldnames, delimiter=';')
                writer.writerows(batch_conditions)

        print(f"Batch {i//batch_size + 1} completed and written to CSV. Total so far: {total_results} results, {total_conditions} conditions")
        time.sleep(0.3)

    end_time = time.time()
    print(f"\nCompleted in {end_time - start_time:.2f} seconds")
    print(f"Total results: {total_results}")
    print(f"Total conditions: {total_conditions}")

    if total_results > 0 or total_conditions > 0:
        print("CSV files have been created and updated with all batches successfully.")
    else:
        print("[WARNING] No data was collected. CSV files contain only headers.")

if __name__ == "__main__":
    main()