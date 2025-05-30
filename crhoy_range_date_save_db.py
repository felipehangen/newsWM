#!/usr/bin/env python3
"""
crhoy_range_date_save_db.py

Fetches articles for a date range using crhoy_range_date_scraper.py and saves them to Supabase 'articles' table.
Logs operations and any errors in LOG/crhoy_range_date_save_db_log.
Usage:
    python crhoy_range_date_save_db.py <start_date> <end_date>
"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from supabase import create_client

# Spanish to English month mapping for parsing
SPANISH_TO_ENGLISH = {
    'Enero': 'January', 'Febrero': 'February', 'Marzo': 'March', 'Abril': 'April',
    'Mayo': 'May', 'Junio': 'June', 'Julio': 'July', 'Agosto': 'August',
    'Septiembre': 'September', 'Octubre': 'October', 'Noviembre': 'November', 'Diciembre': 'December'
}

# Load environment variables
dotenv_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_KEY in environment")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Logging setup
LOG_DIR = os.path.join(os.getcwd(), 'LOG')
LOG_FILE = os.path.join(LOG_DIR, 'crhoy_range_date_save_db_log')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def normalize_date(spanish_date, url=None):
    """
    Convert a Spanish-formatted date like "Mayo 21, 2025 11:37 pm"
    into an ISO8601 UTC timestamp string.
    """
    pd = spanish_date.replace('\u2003', ' ')
    for sp, en in SPANISH_TO_ENGLISH.items():
        if sp in pd:
            pd = pd.replace(sp, en)
            break
    try:
        dt_local = datetime.strptime(pd, '%B %d, %Y %I:%M %p')
        dt_utc = dt_local + timedelta(hours=6)
        return dt_utc.replace(tzinfo=timezone.utc).isoformat()
    except Exception as e:
        logging.error(f"Date parse error for {url or pd}: {e}")
        return None


def main():
    if len(sys.argv) != 3:
        print("Usage: python crhoy_range_date_save_db.py <start_date> <end_date>")
        sys.exit(1)
    start_date, end_date = sys.argv[1], sys.argv[2]
    logging.info(f"Starting save for date range {start_date} to {end_date}")
    print(f"Fetching articles for range {start_date} to {end_date}...")

    try:
        result = subprocess.run(
            ['python3', 'crhoy_range_date_scraper.py', start_date, end_date],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or e.stdout).strip()
        logging.error(f"Error running scraper: {error_msg}")
        print(f"Error fetching articles: {error_msg}")
        sys.exit(1)

    try:
        articles = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        print(f"Error decoding JSON output: {e}")
        sys.exit(1)

    total = len(articles)
    logging.info(f"Fetched {total} articles for saving")
    print(f"Fetched {total} articles. Normalizing dates and beginning save...")

    for article in articles:
        if 'published_date' in article and article['published_date']:
            iso_date = normalize_date(article['published_date'], article.get('url'))
            if iso_date:
                article['published_date'] = iso_date

    success_count = 0
    errors = []
    for idx, article in enumerate(articles, start=1):
        url = article.get('url', 'unknown URL')
        print(f"Saving article {idx}/{total}: {url}")
        try:
            resp = supabase.table('articles').insert(article).execute()
            # Handle HTTP errors for PostgrestResponse
            status = getattr(resp, 'status_code', None)
            if status is not None and not (200 <= status < 300):
                msg = getattr(resp, 'data', resp)
                raise Exception(f"HTTP {status}: {msg}")
            success_count += 1
            logging.info(f"Saved article: {url}")
        except Exception as e:
            err_str = str(e)
            errors.append((url, err_str))
            logging.error(f"Error saving {url}: {err_str}")
            print(f"Error saving {url}: {err_str}")

    print(f"Save complete: {success_count}/{total} articles saved.")
    logging.info(f"Save complete: {success_count}/{total} saved with {len(errors)} errors.")

    if errors:
        logging.info("Encountered the following errors:")
        for url, err in errors:
            logging.info(f"{url}: {err}")


if __name__ == "__main__":
    main()