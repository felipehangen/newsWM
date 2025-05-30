#!/usr/bin/env python3
# crhoy_scraper.py
#
# Usage:
#   python crhoy_scraper.py <article_url>
#
# Dependencies:
#   pip install selenium webdriver-manager beautifulsoup4 python-dateutil

import sys
import json
from urllib.parse import urlparse
from dateutil import parser as dateparser

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_page_source(url):
    opts = Options()
    opts.headless = True
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.get(url)
    html = driver.page_source
    driver.quit()
    return html


def parse_article(html, url):
    soup = BeautifulSoup(html, "lxml")
    data = {}

    # Title
    title_tag = soup.find("h1", class_="text-left titulo")
    data["title"] = title_tag.get_text(strip=True) if title_tag else None

    # Subtitle
    subtitle_tag = soup.find("h3", class_="text-uppercase pre-titulo border-deportes")
    data["subtitle"] = subtitle_tag.get_text(strip=True) if subtitle_tag else None

    # Body
    body_div = soup.find("div", id="contenido")
    if body_div:
        paragraphs = body_div.find_all(["p", "blockquote"])
        texts = [p.get_text(strip=False).strip() for p in paragraphs]
        data["body"] = "\n\n".join(texts)
    else:
        data["body"] = None

    # URL & domain
    data["url"] = url
    data["domain"] = urlparse(url).netloc

    # Author
    author_tag = soup.find("span", class_="autor-nota")
    data["author"] = author_tag.get_text(strip=True) if author_tag else None

    # Author email
    email_span = soup.find("span", attrs={"ng-show": "displayMail"})
    data["author_email"] = email_span.get_text(strip=True) if email_span else None

    # Published date (UTC)
    date_tag = soup.find("span", class_="fecha-nota")
    if date_tag:
        # parse and convert to ISO UTC
        dt = dateparser.parse(date_tag.get_text(strip=True))
        data["published_date"] = dt.astimezone(dateparser.tz.UTC).isoformat()
    else:
        data["published_date"] = None

    # Category
    cat_tag = soup.find("div", class_="categoria-desktop")
    data["category"] = cat_tag.get_text(strip=True) if cat_tag else None

    # Tags
    tags = []
    tag_div = soup.find("div", class_="etiquetas")
    if tag_div:
        links = tag_div.find_all("a")
        if links:
            tags = [a.get_text(strip=True) for a in links]
        else:
            raw = tag_div.get_text(separator=",", strip=True)
            tags = [t.strip() for t in raw.split(",") if t.strip()]
    data["tags"] = tags

    return data


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python crhoy_scraper.py <article_url>"}), file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    html = get_page_source(url)
    article = parse_article(html, url)
    print(json.dumps(article, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()