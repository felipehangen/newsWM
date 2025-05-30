#!/usr/bin/env python3
# crhoy_range_date_scraper.py
#
# Usage:
#   python crhoy_range_date_scraper.py <start_date> <end_date>
#
# Fetches article URLs from CRHoy sitemaps for each date in the given range
# and uses crhoy_scraper.py to extract JSON for each article.

import sys
import json
import os
import logging
from datetime import datetime, timedelta

import requests
from crhoy_scraper import get_page_source, parse_article

# Log file configuration: use a relative 'LOG' directory
LOG_DIR = os.path.join(os.getcwd(), 'LOG')
LOG_FILE = os.path.join(LOG_DIR, 'crhoy_range_date_scraper.log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Use a session with a browser-like User-Agent to avoid 403 Forbidden
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
    'Accept': 'text/plain, */*; q=0.1',
    'Referer': 'https://www.crhoy.com/'
})

def daterange(start_date, end_date):
    """
    Yield dates from start_date to end_date inclusive.
    """
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)


def main():
    if len(sys.argv) != 3:
        msg = 'Usage: python crhoy_range_date_scraper.py <start_date> <end_date>'
        logging.error(msg)
        sys.stderr.write(json.dumps({'error': msg}) + '\n')
        sys.exit(1)

    # Parse input dates
    try:
        start_dt = datetime.fromisoformat(sys.argv[1]).date()
        end_dt = datetime.fromisoformat(sys.argv[2]).date()
    except ValueError:
        msg = 'Dates must be in YYYY-MM-DD format'
        logging.error(msg)
        sys.stderr.write(json.dumps({'error': msg}) + '\n')
        sys.exit(1)

    all_articles = []

    for single_date in daterange(start_dt, end_dt):
        sitemap_url = f"https://www.crhoy.com/site/dist/sitemap/{single_date}.txt"
        try:
            resp = session.get(sitemap_url, timeout=10)
            resp.raise_for_status()
            urls = [u.strip() for u in resp.text.splitlines() if u.strip()]
            logging.info(f"Found {len(urls)} URLs for {single_date}")
            for url in urls:
                logging.info(f"URL: {url}")
        except Exception as e:
            logging.error(f"Error fetching sitemap for {single_date}: {e}")
            sys.stderr.write(f"Error fetching sitemap for {single_date}: {e}\n")
            continue

        for url in urls:
            try:
                html = get_page_source(url)
                article = parse_article(html, url)
                all_articles.append(article)
            except Exception as e:
                logging.error(f"Error scraping {url}: {e}")
                sys.stderr.write(f"Error scraping {url}: {e}\n")

    # Output all extracted articles as JSON array
    print(json.dumps(all_articles, ensure_ascii=False, indent=2))
    logging.info(f"Scraping complete: {len(all_articles)} articles extracted.")


if __name__ == "__main__":
    main()
