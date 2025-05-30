#!/usr/bin/env python3
# diarioextra_range_date_scraper.py
#
# Usage:
#   python diarioextra_range_date_scraper.py <start_date YYYY-MM-DD> <end_date YYYY-MM-DD>
#
# Dependencies:
#   pip install selenium webdriver-manager beautifulsoup4 python-dateutil requests

import sys
import os
import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, date
from dateutil import parser as dateparser

from diarioextra_scraper import get_page_source, parse_article

LOG_DIR = "LOG"
LOG_FILE = os.path.join(LOG_DIR, "diarioextra_range_date_scraper_log")

def month_range(start_date, end_date):
    # Yield each (year, month) tuple from start_date to end_date inclusive
    current = date(start_date.year, start_date.month, 1)
    end_month = date(end_date.year, end_date.month, 1)
    while current <= end_month:
        yield current.year, current.month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def main():
    if len(sys.argv) != 3:
        print(json.dumps({"error": "Usage: python diarioextra_range_date_scraper.py <start_date YYYY-MM-DD> <end_date YYYY-MM-DD>"}), file=sys.stderr)
        sys.exit(1)
    start_str, end_str = sys.argv[1], sys.argv[2]
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")
    except Exception as e:
        print(json.dumps({"error": f"Invalid date: {e}"}), file=sys.stderr)
        sys.exit(1)

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        article_urls = []
        # Fetch sitemaps for each month in range
        for year, month in month_range(start_date, end_date):
            sitemap_url = f"https://www.diarioextra.com/sitemap-posttype-portada.{year}{month:02}.xml"
            log.write(f"Fetching sitemap: {sitemap_url}\n")
            try:
                resp = requests.get(sitemap_url)
                resp.raise_for_status()
                xml_root = ET.fromstring(resp.content)
                for url_elem in xml_root.findall(".//{*}url"):
                    loc = url_elem.find("{*}loc")
                    lastmod = url_elem.find("{*}lastmod")
                    if loc is None or lastmod is None:
                        continue
                    url = loc.text.strip()
                    lastmod_text = lastmod.text.strip()
                    try:
                        mod_dt = dateparser.parse(lastmod_text).date()
                    except Exception as e:
                        log.write(f"ERROR parsing lastmod '{lastmod_text}' for URL {url}: {e}\n")
                        continue
                    if start_date <= mod_dt <= end_date:
                        article_urls.append(url)
                        log.write(f"FOUND URL: {url} lastmod {mod_dt}\n")
            except Exception as e:
                log.write(f"ERROR fetching sitemap {sitemap_url}: {e}\n")

        # Deduplicate URLs while preserving order
        article_urls = list(dict.fromkeys(article_urls))

        # Process each article URL
        for url in article_urls:
            log.write(f"Processing URL: {url}\n")
            try:
                html = get_page_source(url)
                article = parse_article(html, url)
                print(json.dumps(article, ensure_ascii=False))
            except Exception as e:
                log.write(f"ERROR processing {url}: {e}\n")

if __name__ == "__main__":
    main()
