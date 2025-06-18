import csv
import requests
import re
from difflib import SequenceMatcher
from functools import lru_cache
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict
import queue

# Compiled regex for maximum performance
NAME_PATTERN = re.compile(r'[^a-z]')

# Connection pool with keep-alive
session = requests.Session()
session.headers.update({
    'Connection': 'keep-alive',
    'Keep-Alive': 'timeout=30, max=100'
})

# Thread-safe rate limiter
class RateLimiter:
    def __init__(self, calls_per_second=15):  # Conservative for 54k rows
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_called = 0
        self.lock = threading.Lock()
    
    def wait(self):
        with self.lock:
            elapsed = time.time() - self.last_called
            sleep_time = self.min_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.last_called = time.time()

rate_limiter = RateLimiter(15)  # 15 calls per second max

@lru_cache(maxsize=2048)
def normalize_name(name):
    """Ultra-fast name normalization."""
    return NAME_PATTERN.sub('', name.lower())

@lru_cache(maxsize=4096)
def similar(a, b):
    """Optimized similarity with early exits."""
    if not a or not b:
        return 0.0
    len_diff = abs(len(a) - len(b))
    if len_diff > max(len(a), len(b)) * 0.2:  # 20% length difference threshold
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

@lru_cache(maxsize=512)  # Smaller cache for API calls
def search_skater_cached(givenname, familyname, country, use_partial_family=False):
    """Cached API search with aggressive optimizations."""
    query_familyname = familyname[:4] if use_partial_family else familyname
    id_url = f"https://speedskatingresults.com/api/json/skater_lookup?familyname={query_familyname}&country={country.upper()}"

    rate_limiter.wait()  # Rate limiting
    
    try:
        response = session.get(id_url, timeout=3)  # Very short timeout for speed
        if response.status_code == 200:
            data = response.json()
            skaters = data.get("skaters", [])
            
            if not skaters:
                return None
                
            normalized_given = normalize_name(givenname)
            normalized_family = normalize_name(familyname)

            # Process only first 10 results for speed
            for skater in skaters[:10]:
                skater_given = normalize_name(skater.get("givenname", ""))
                skater_family = normalize_name(skater.get("familyname", ""))

                if (similar(skater_given, normalized_given) > 0.9 and
                    (skater_family.startswith(normalized_family) or
                     (use_partial_family and len(normalized_family) >= 4 and 
                      skater_family.startswith(normalized_family[:4])))):
                    return skater.get("id")
    except:
        pass
    
    return None

def process_single_row(name_country_tuple):
    """Process a single row efficiently."""
    full_name, country = name_country_tuple
    
    if not full_name or not country:
        return ''
    
    # Parse name
    if '_' in full_name:
        givenname, familyname = full_name.split('_', 1)
    else:
        givenname = full_name
        familyname = ''
    
    # Try full match first
    skater_id = search_skater_cached(givenname, familyname, country, False)
    
    # Try partial match only if needed and familyname is long enough
    if not skater_id and len(familyname) >= 4:
        skater_id = search_skater_cached(givenname, familyname, country, True)
    
    return skater_id if skater_id else ""

def deduplicate_requests(rows):
    """Group identical requests to minimize API calls."""
    request_groups = defaultdict(list)
    
    for i, row in enumerate(rows):
        full_name = row.get('Name', '').strip()
        country = row.get('Country', '').strip()
        key = (full_name, country)
        request_groups[key].append(i)
    
    return request_groups

def parse_and_enrich_csv_massive(input_file, output_file, max_workers=8):
    """Optimized for massive datasets like 54k rows."""
    
    start_time = time.time()
    
    # Read all data
    with open(input_file, newline='', encoding='utf-8') as csvfile_in:
        reader = csv.DictReader(csvfile_in, delimiter=';')
        fieldnames = list(reader.fieldnames) + ['SkaterID']
        rows = list(reader)
    
    print(f"Loaded {len(rows)} rows in {time.time() - start_time:.1f}s")
    
    if not rows:
        return
    
    # Deduplicate requests
    dedup_start = time.time()
    request_groups = deduplicate_requests(rows)
    unique_requests = list(request_groups.keys())
    
    print(f"Deduplicated to {len(unique_requests)} unique requests ({time.time() - dedup_start:.1f}s)")
    
    # Process unique requests in parallel
    process_start = time.time()
    results = {}
    
    # Use more workers for large datasets
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all unique requests
        future_to_request = {
            executor.submit(process_single_row, request): request 
            for request in unique_requests
        }
        
        completed = 0
        for future in as_completed(future_to_request):
            request = future_to_request[future]
            try:
                result = future.result()
                results[request] = result
                completed += 1
                
                # Progress update every 1000 completions
                if completed % 1000 == 0:
                    elapsed = time.time() - process_start
                    rate = completed / elapsed
                    eta = (len(unique_requests) - completed) / rate
                    print(f"Processed {completed}/{len(unique_requests)} unique requests "
                          f"({rate:.1f}/s, ETA: {eta:.0f}s)")
                    
            except Exception as e:
                results[request] = 'Error'
    
    print(f"API processing completed in {time.time() - process_start:.1f}s")
    
    # Map results back to all rows
    write_start = time.time()
    skater_ids = []
    for row in rows:
        full_name = row.get('Name', '').strip()
        country = row.get('Country', '').strip()
        key = (full_name, country)
        skater_ids.append(results[key])
    
    # Write results in chunks for memory efficiency
    chunk_size = 1000
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile_out:
        writer = csv.DictWriter(csvfile_out, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        
        for i in range(0, len(rows), chunk_size):
            chunk_rows = rows[i:i + chunk_size]
            chunk_ids = skater_ids[i:i + chunk_size]
            
            for row, skater_id in zip(chunk_rows, chunk_ids):
                row['SkaterID'] = skater_id
                writer.writerow(row)
    
    print(f"File written in {time.time() - write_start:.1f}s")
    print(f"Total execution time: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    print("Starting processing...")
    
    start_time = time.time()
    
    # For 54k rows - use 8 workers but be conservative with rate limiting
    parse_and_enrich_csv_massive('datascraper/data/isu_results.csv', 'datascraper/data/isu_results.csv', max_workers=8)
    end_time = time.time()
    total_minutes = (end_time - start_time) / 60
    print(f"\nFinal execution time: {total_minutes:.1f} minutes")

