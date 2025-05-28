import requests
import time
import random
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from supabase import create_client, Client

# Supabase keys
SUPABASE_URL = "https://ezastdzwipwvtebvwrhx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6YXN0ZHp3aXB3dnRlYnZ3cmh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgyOTUxODYsImV4cCI6MjA2Mzg3MTE4Nn0.kvCoTZhx8pPjboPrVEL1aQLK4lqiHH-qS66bDQKgymo"  # Keep private

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

        # Body
        body = ""
        start_tag = '<div class="noscript__content">'
        start_index = noscript_html.find(start_tag)
        if start_index != -1:
            end_index = noscript_html.find("</div>", start_index)
            if end_index != -1:
                body_html = noscript_html[start_index:end_index + 6]
                body_soup = BeautifulSoup(body_html, "html.parser")
                body = " ".join(body_soup.stripped_strings)

        # Author info
        try:
            author = driver.find_element(By.CSS_SELECTOR, "span.single-layout__meta-name").text.strip()
        except NoSuchElementException:
            author = None
        try:
            author_email = driver.find_element(By.CSS_SELECTOR, "span.single-layout__meta-email").text.strip()
        except NoSuchElementException:
            author_email = None

        # Tags
        tags = []
        try:
            tag_container = driver.find_element(By.CSS_SELECTOR, "x-swiper.tag-layout")
            tag_titles = tag_container.find_elements(By.CLASS_NAME, "swiper-slide__title")
            tags = [t.text.strip().lstrip("#") for t in tag_titles]
        except NoSuchElementException:
            tags = []

        # Timestamp conversion to UTC
        raw_timestamp = timestamp_map[url]
        try:
            local_dt = datetime.fromisoformat(raw_timestamp)
            utc_dt = local_dt.astimezone(timezone.utc)
            timestamp = utc_dt.isoformat()
        except Exception as e:
            print(f"⚠️ Failed to convert timestamp: {e}")
            timestamp = raw_timestamp  # fallback

        domain = urlparse(url).netloc

        # Check for duplicate
        existing = supabase.table("Articles").select("url").eq("url", url).execute()
        if existing.data and len(existing.data) > 0:
            print("⚠️ Article already exists in DB, skipping.\n")
            continue

        # Prepare and insert
        payload = {
            "title": headline,
            "subtitle": subtitle,
            "body": body,
            "author": author,
            "author_email": author_email,
            "tags": tags,
            "timestamp": timestamp,
            "url": url,
            "domain": domain
        }

        print("📦 Inserting article to Supabase...")
        response = supabase.table("Articles").insert(payload).execute()

        if response.status_code == 201:
            print("✅ Inserted successfully!\n")
        else:
            print(f"❌ Insert failed! Response code: {response.status_code}")
            print("Response:", response.json())

    except Exception as e:
        print(f"❌ Error on article: {e}")

    time.sleep(random.uniform(1.5, 3.0))

driver.quit()
print("\n🏁 Done.")