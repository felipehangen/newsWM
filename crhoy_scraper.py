# crhoy_scraper.py

import requests
import time
import random
import locale
from datetime import datetime
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_crhoy_articles(date_str):
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
        response = requests.get(sitemap_url, headers=headers)
        response.raise_for_status()
        urls = response.text.strip().splitlines()
    except Exception as e:
        print(f"❌ Error fetching sitemap: {e}")
        return []

    print(f"\n🔎 Found {len(urls)} URLs for {date_str}. Limiting to first 5.\n")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=" + headers["User-Agent"])
    driver = webdriver.Chrome(options=chrome_options)

    articles = []

    for i, url in enumerate(urls[:5]):
        print(f"🔗 Processing {i+1}/5: {url}")
        try:
            driver.get(url)

            headline_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            body_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "contenido"))
            )
            paragraphs = body_div.find_elements(By.TAG_NAME, "p")
            headline = headline_elem.text.strip()
            body = "\n\n".join([p.text.strip() for p in paragraphs if p.text.strip()])

            try:
                subtitle = driver.find_element(By.TAG_NAME, "h2").text.strip()
            except:
                subtitle = ""

            try:
                autor_nota = driver.find_element(By.CLASS_NAME, "autor-nota")
                author = autor_nota.find_element(By.TAG_NAME, "a").get_attribute("title")
            except:
                author = None

            try:
                email_link = driver.find_element(By.CSS_SELECTOR, 'span.autor-nota a[href^="mailto:"]')
                author_email = email_link.get_attribute("href").replace("mailto:", "").strip()
            except:
                author_email = None

            try:
                tag_links = driver.find_elements(By.CSS_SELECTOR, "div.etiquetas a")
                tags = [t.text.strip() for t in tag_links if t.text.strip()]
            except:
                tags = []

            try:
                timestamp_raw = driver.find_element(By.CLASS_NAME, "fecha-nota").text.strip().replace("\u2003", " ")
                timestamp = datetime.strptime(timestamp_raw, "%B %d, %Y %I:%M %p").isoformat()
            except Exception as e:
                print("⚠️ Failed to parse timestamp:", e)
                timestamp = datetime.utcnow().isoformat()

            article = {
                "title": headline or "",
                "subtitle": subtitle or "",
                "body": body or "",
                "author": author or None,
                "author_email": author_email or None,
                "tags": tags,
                "timestamp": timestamp,
                "url": url,
                "domain": urlparse(url).netloc
            }
            articles.append(article)
        except Exception as e:
            print(f"❌ Error on article: {e}")
        time.sleep(random.uniform(1.5, 3.0))

    driver.quit()
    return articles


if __name__ == "__main__":
    raw_input = input("📅 Enter the date (YYYY-MM-DD): ").strip()
    try:
        datetime.strptime(raw_input, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format.")
        exit()

    articles = get_crhoy_articles(raw_input)
    print(f"\n📦 Collected {len(articles)} articles.")
