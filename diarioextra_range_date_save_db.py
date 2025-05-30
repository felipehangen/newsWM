#!/usr/bin/env python3
"""
diarioextra_range_date_save_db.py

Usage:
  python diarioextra_range_date_save_db.py <start_date YYYY-MM-DD> <end_date YYYY-MM-DD>

This script uses diarioextra_range_date_scraper.py to fetch articles in JSON format
for a given date range, then writes each article to the "articles" table in Supabase.
It logs the total found, how many were saved successfully, and any errors.
"""
import sys
import os
import json
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from .env
load_dotenv()

# Constants for logging
LOG_DIR = "LOG"
LOG_FILE = os.path.join(LOG_DIR, "diarioextra_range_date_save_db_log")

# Supabase configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def fetch_articles(start_date: str, end_date: str):
    """
    Calls diarioextra_range_date_scraper.py and captures JSON output lines.
    Returns a list of article dicts.
    """
    cmd = [sys.executable, "diarioextra_range_date_scraper.py", start_date, end_date]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stderr:
        logging.error(f"Errors from scraper:\n{result.stderr}")
    articles = []
    for line in result.stdout.splitlines():
        try:
            articles.append(json.loads(line))
        except json.JSONDecodeError:
            logging.warning(f"Skipping non-JSON output: {line}")
    return articles

def save_to_supabase(articles):
    """
    Inserts each article dict into Supabase 'articles' table.
    Returns (count_success, errors_list)
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.error("SUPABASE_URL or SUPABASE_KEY not set in environment.")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    success = 0
    errors = []
    for article in articles:
        url = article.get("url")
        try:
            resp = client.table("articles").insert(article).execute()
            # Supabase response may include 'error' key
            if hasattr(resp, 'error') and resp.error:
                raise Exception(resp.error)
            success += 1
            logging.info(f"Saved article: {url}")
        except Exception as e:
            logging.error(f"ERROR saving {url}: {e}")
            errors.append((url, str(e)))
    return success, errors


def main():
    if len(sys.argv) != 3:
        print("Usage: python diarioextra_range_date_save_db.py <start_date YYYY-MM-DD> <end_date YYYY-MM-DD>")
        sys.exit(1)
    start_date, end_date = sys.argv[1], sys.argv[2]

    setup_logging()
    logging.info(f"Fetching articles from {start_date} to {end_date}")
    articles = fetch_articles(start_date, end_date)
    total = len(articles)
    logging.info(f"Found {total} articles")

    success, errors = save_to_supabase(articles)
    logging.info(f"Successfully saved {success} articles out of {total}")
    if errors:
        logging.info("Errors encountered during save:")
        for url, err in errors:
            logging.info(f" - {url}: {err}")

if __name__ == "__main__":
    main()
