# crhoy_scraper.py

import requests
import time
import random
import locale
from datetime import datetime, timedelta
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Optional, Dict, Any

Article = Dict[str, Any]

def get_crhoy_articles(date_str: str, limit: Optional[int] = 5) -> List[Article]:
    """
    Scrape CRHoy articles for a single date.
    :param date_str: YYYY-MM-DD
    :param limit: max articles to fetch (None => no limit)
    :return: list of article dicts
    """
    # — set Spanish locale for timestamp parsing —
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES')
        except:
            print("⚠️ Could not set Spanish locale. Timestamp parsing may fail.")

    sitemap_url = f"https://www.crhoy.com/site/dist/sitemap/{date_str}.txt"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    try:
        resp = requests.get(sitemap_url, headers=headers)
        resp.raise_for_status()
        urls = resp.text.strip().splitlines()
    except Exception as e:
        print(f"❌ Error fetching sitemap for {date_str}: {e}")
        return []

    total = len(urls)
    print(f"\nFound {total} URLs for {date_str}.")
    if limit is not None:
        print(f"Limiting to first {limit}.\n")
        urls_to_fetch = urls[:limit]
    else:
        print("No limit, fetching all URLs.\n")
        urls_to_fetch = urls

    # — headless Chrome setup —
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--window-size=1920,1080")
    chrome_opts.add_argument("--user-agent=" + headers["User-Agent"])
    driver = webdriver.Chrome(options=chrome_opts)

    articles: List[Article] = []
    for idx, url in enumerate(urls_to_fetch, start=1):
        print(f" Processing {idx}/{len(urls_to_fetch)}: {url}")
        try:
            driver.get(url)
            # headline
            h1 = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            ).text.strip()
            # body paragraphs
            body_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "contenido"))
            )
            paras = [p.text.strip() for p in body_div.find_elements(By.TAG_NAME, "p") if p.text.strip()]
            body = "\n\n".join(paras)

            # subtitle
            try:
                subtitle = driver.find_element(By.TAG_NAME, "h2").text.strip()
            except:
                subtitle = ""

            # author & email
            try:
                nota = driver.find_element(By.CLASS_NAME, "autor-nota")
                author = nota.find_element(By.TAG_NAME, "a").get_attribute("title")
            except:
                author = None
            try:
                mail_el = driver.find_element(By.CSS_SELECTOR, 'span.autor-nota a[href^="mailto:"]')
                author_email = mail_el.get_attribute("href").replace("mailto:", "").strip()
            except:
                author_email = None

            # tags
            try:
                tag_elements = driver.find_elements(By.CSS_SELECTOR, "div.etiquetas a")
                tags = [t.text.strip() for t in tag_elements if t.text.strip()]
            except:
                tags = []

            # timestamp
            try:
                raw_ts = driver.find_element(By.CLASS_NAME, "fecha-nota") \
                    .text.strip().replace("\u2003", " ")
                timestamp = datetime.strptime(raw_ts, "%B %d, %Y %I:%M %p").isoformat()
            except Exception as e:
                print("⚠️ Timestamp parse failed:", e)
                timestamp = datetime.utcnow().isoformat()

            article: Article = {
                "title": h1,
                "subtitle": subtitle,
                "body": body,
                "author": author,
                "author_email": author_email,
                "tags": tags,
                "timestamp": timestamp,
                "url": url,
                "domain": urlparse(url).netloc
            }
            articles.append(article)
        except Exception as err:
            print(f"❌ Error scraping {url}: {err}")
        # polite pause
        time.sleep(random.uniform(1.5, 3.0))

    driver.quit()
    return articles


def get_crhoy_articles_range(
    start_date_str: str,
    end_date_str: str,
    limit_per_day: Optional[int] = None
) -> List[Article]:
    """
    Scrape CRHoy for every date in [start_date, end_date].
    :param start_date_str: YYYY-MM-DD
    :param end_date_str:   YYYY-MM-DD
    :param limit_per_day:  max per day (None => all)
    :return: combined list of article dicts
    """
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end   = datetime.strptime(end_date_str,   "%Y-%m-%d").date()
    delta = timedelta(days=1)

    all_articles: List[Article] = []
    current = start
    while current <= end:
        day = current.strftime("%Y-%m-%d")
        print(f"\n→ Scraping {day}")
        day_articles = get_crhoy_articles(day, limit=limit_per_day)
        all_articles.extend(day_articles)
        time.sleep(random.uniform(1, 3))
        current += delta

    return all_articles


if __name__ == "__main__":
    # simple test harness
    import argparse
    from pprint import pprint

    p = argparse.ArgumentParser(description="Test CRHoy scraper")
    p.add_argument("--date", help="Single date YYYY-MM-DD")
    p.add_argument("--start-date", help="Range start YYYY-MM-DD")
    p.add_argument("--end-date",   help="Range end YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=5,
                   help="Max per day (<=0 => unlimited)")
    args = p.parse_args()

    lim = None if args.limit <= 0 else args.limit
    if args.date:
        res = get_crhoy_articles(args.date, limit=lim)
    else:
        if not args.start_date or not args.end_date:
            p.error("Require either --date or both --start-date/--end-date")
        res = get_crhoy_articles_range(
            args.start_date, args.end_date, limit_per_day=lim
        )

    pprint(res)