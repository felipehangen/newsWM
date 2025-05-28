import requests
import time
import random
from datetime import datetime
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from openai import OpenAI

from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env

# 🔑 OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Replace with your actual key

# Ask for the date
raw_input = input("📅 Enter the date (YYYY-MM-DD): ").strip()
try:
    target_date = datetime.strptime(raw_input, "%Y-%m-%d")
    date_str = target_date.strftime("%Y-%m-%d")
    sitemap_suffix = target_date.strftime("%Y%m")
except ValueError:
    print("❌ Invalid date format.")
    exit()

# Load the sitemap
sitemap_url = f"https://www.diarioextra.com/sitemap-posttype-portada.{sitemap_suffix}.xml"
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

try:
    response = requests.get(sitemap_url, headers=headers)
    response.raise_for_status()
    tree = ET.fromstring(response.content)
except Exception as e:
    print(f"❌ Error loading sitemap: {e}")
    exit()

# Filter articles
ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls = []
timestamp_map = {}
for url_entry in tree.findall("ns:url", ns):
    loc = url_entry.find("ns:loc", ns).text
    lastmod = url_entry.find("ns:lastmod", ns).text
    if lastmod.startswith(date_str):
        urls.append(loc)
        timestamp_map[loc] = lastmod

print(f"🔎 Found {len(urls)} articles for {date_str}. Limiting to first 5.\n")

# Setup Selenium
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=" + headers["User-Agent"])
driver = webdriver.Chrome(options=chrome_options)

# Process articles
results = []

for i, url in enumerate(urls[:5]):
    print(f"🔗 Processing {i+1}/5: {url}")
    try:
        driver.get(url)

        # Wait for <noscript> block
        noscript_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "noscript.noscript"))
        )
        noscript_html = noscript_elem.get_attribute("innerHTML")
        soup = BeautifulSoup(noscript_html, "html.parser")

        # Headline and subtitle
        headline = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        subtitle = soup.find("h2").get_text(strip=True) if soup.find("h2") else ""

        # Body from noscript HTML
        body = ""
        start_tag = '<div class="noscript__content">'
        start_index = noscript_html.find(start_tag)
        if start_index != -1:
            end_index = noscript_html.find("</div>", start_index)
            if end_index != -1:
                body_html = noscript_html[start_index:end_index + 6]
                body_soup = BeautifulSoup(body_html, "html.parser")
                body = " ".join(body_soup.stripped_strings)

        if not body:
            print("⚠️ Body not found — preview:")
            print(noscript_html[:500])

        # Extract author and email from live DOM
        try:
            author = driver.find_element(By.CSS_SELECTOR, "span.single-layout__meta-name").text.strip()
        except NoSuchElementException:
            author = None

        try:
            author_email = driver.find_element(By.CSS_SELECTOR, "span.single-layout__meta-email").text.strip()
        except NoSuchElementException:
            author_email = None

        # Extract tags from <x-swiper class="tag-layout">
        tags = []
        try:
            tag_container = driver.find_element(By.CSS_SELECTOR, "x-swiper.tag-layout")
            tag_titles = tag_container.find_elements(By.CLASS_NAME, "swiper-slide__title")
            tags = [t.text.strip() for t in tag_titles]
        except NoSuchElementException:
            tags = []

        # Bias detection
        prompt = f"""
Given the following Costa Rican news article, determine if it is written in a neutral tone or if it seems biased or emotionally charged.

Respond ONLY with one word: Neutral or Biased.

Title: {headline}

Body:
{body}
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        verdict = response.choices[0].message.content.strip().split()[0]

        results.append({
            "title": headline,
            "subtitle": subtitle,
            "body": body,
            "author": author,
            "author_email": author_email,
            "tags": tags,
            "timestamp": timestamp_map[url],
            "url": url,
            "domain": urlparse(url).netloc,
            "bias": verdict
        })

    except Exception as e:
        print(f"❌ Error on {url}: {e}")

    time.sleep(random.uniform(1.5, 3.0))

driver.quit()

# Output HTML
html_file = "diarioextra_stories.html"
with open(html_file, "w", encoding="utf-8") as f:
    f.write("<html><head><meta charset='UTF-8'><title>Diario Extra Stories</title>")
    f.write("<style>body{font-family:sans-serif;max-width:800px;margin:auto;} h2{color:#800000;} .bias{font-weight:bold;padding:4px 8px;border-radius:4px;} .Neutral{color:green;} .Biased{color:red;} h3{color:#444;} small{color:#555;display:block;margin-bottom:10px;}</style>")
    f.write("</head><body>")
    f.write(f"<h1>Diario Extra Stories for {date_str}</h1><hr>")

    for story in results:
        f.write(f"<h2>{story['title']}</h2>")
        if story['subtitle']:
            f.write(f"<h3>{story['subtitle']}</h3>")
        f.write(f"<small><strong>Author:</strong> {story['author'] or 'N/A'}<br>")
        f.write(f"<strong>Email:</strong> {story['author_email'] or 'N/A'}<br>")
        f.write(f"<strong>Tags:</strong> {', '.join(story['tags']) or 'N/A'}<br>")
        f.write(f"<strong>Timestamp:</strong> {story['timestamp']}<br>")
        f.write(f"<strong>Domain:</strong> {story['domain']}<br></small>")
        f.write(f"<p class='bias {story['bias']}'><strong>Bias:</strong> {story['bias']}</p>")
        f.write(f"<p>{story['body']}</p>")
        f.write(f"<a href='{story['url']}' target='_blank'>Leer en diarioextra.com</a>")
        f.write("<hr>")

    f.write("</body></html>")

print(f"\n✅ Done! Output written to: {html_file}")