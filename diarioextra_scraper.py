#!/usr/bin/env python3
# diarioextra_scraper.py
#
# Usage:
#   python diarioextra_scraper.py <article_url>
#
# Dependencies:
#   pip install selenium webdriver-manager beautifulsoup4 python-dateutil

import sys
import json
import re
from urllib.parse import urlparse
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil import parser as dateparser

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_page_source(url, headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")  # truly headless mode
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--log-level=3")

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
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        data["title"] = og_title["content"].strip()
    else:
        h1 = soup.find("h1")
        data["title"] = h1.get_text(strip=True) if h1 else None

    # Subtitle
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        data["subtitle"] = desc["content"].strip()
    else:
        h2 = soup.find("h2")
        data["subtitle"] = h2.get_text(strip=True) if h2 else None

    # Body
    content = (
        soup.find("div", class_="single-layout__article")
        or soup.find("div", class_="entry-content")
        or soup.find("article")
    )
    if content:
        paras = content.find_all(["p", "blockquote"])
        data["body"] = "\n\n".join(p.get_text(strip=False).strip() for p in paras)
    else:
        data["body"] = None

    # URL & domain
    data["url"] = url
    data["domain"] = urlparse(url).netloc

    # Author
    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author and meta_author.get("content"):
        data["author"] = meta_author["content"].strip()
    else:
        span = soup.find("span", class_="single-layout__meta-name")
        data["author"] = span.get_text(strip=True) if span else None

    # Author email
    email_span = soup.find("span", class_="single-layout__meta-email")
    data["author_email"] = email_span.get_text(strip=True) if email_span else None

    # Published date: convert to UTC
    # Try ISO meta first
    pub_meta = soup.find("meta", property="article:published_time")
    if pub_meta and pub_meta.get("content"):
        dt = dateparser.parse(pub_meta["content"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("America/Costa_Rica"))
        dt_utc = dt.astimezone(ZoneInfo("UTC"))
        data["published_date"] = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        span_date = soup.find("span", class_="single-layout__meta-date")
        if span_date:
            date_text = span_date.get_text(strip=True)  # e.g. 29/05/2025 - 16:02
            try:
                dt_local = datetime.strptime(date_text, "%d/%m/%Y - %H:%M")
                dt_local = dt_local.replace(tzinfo=ZoneInfo("America/Costa_Rica"))
                dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
                data["published_date"] = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                data["published_date"] = None
        else:
            data["published_date"] = None

    # Category: from feed__heading div
    cat_div = soup.find("div", class_="feed__heading")
    if cat_div:
        data["category"] = cat_div.get_text(strip=True)
    else:
        # fallback to section meta or breadcrumb
        sec_meta = soup.find("meta", property="article:section")
        if sec_meta and sec_meta.get("content"):
            data["category"] = sec_meta["content"].strip()
        else:
            cat_link = soup.find("a", class_="single-layout__meta-category")
            if not cat_link:
                crumbs = soup.select("ul.breadcrumb li a")
                if len(crumbs) >= 2:
                    cat_link = crumbs[-2]
            data["category"] = cat_link.get_text(strip=True) if cat_link else None

    # Tags
    tags = [m["content"].strip() for m in soup.find_all("meta", property="article:tag") if m.get("content")]
    if not tags:
        swiper = soup.find("x-swiper", class_="tag-layout")
        if swiper:
            links = swiper.find_all("a")
            tags = [a.get_text(strip=True).lstrip("#") for a in links]
    data["tags"] = tags

    return data


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python diarioextra_scraper.py <article_url>"}), file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    html = get_page_source(url)
    article = parse_article(html, url)
    print(json.dumps(article, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
