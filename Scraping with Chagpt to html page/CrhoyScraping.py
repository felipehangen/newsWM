#
# Este código saca 5 noticias de Crhoy.com y analiza sin son biased o neutral con ChatGPT
# Ahora incluye author, author_email, tags, timestamp, url, domain

import requests
import time
import random
from datetime import datetime
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI

from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env

# 🔑 OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Replace with your actual key

raw_input = input("📅 Enter the date (YYYY-MM-DD): ").strip()
try:
    target_date_obj = datetime.strptime(raw_input, "%Y-%m-%d")
    target_date = target_date_obj.strftime("%Y-%m-%d")
except ValueError:
    print("❌ Invalid date format.")
    exit()

sitemap_url = f"https://www.crhoy.com/site/dist/sitemap/{target_date}.txt"
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

try:
    response = requests.get(sitemap_url, headers=headers)
    response.raise_for_status()
    urls = response.text.strip().splitlines()
except Exception as e:
    print(f"❌ Error fetching sitemap: {e}")
    exit()

print(f"\n🔎 Found {len(urls)} URLs for {target_date}. Limiting to first 5.\n")

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=" + headers["User-Agent"])
driver = webdriver.Chrome(options=chrome_options)

results = []

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
            timestamp = driver.find_element(By.CLASS_NAME, "fecha-nota").text.strip()
        except:
            timestamp = target_date

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
            "timestamp": timestamp,
            "url": url,
            "domain": urlparse(url).netloc,
            "bias": verdict
        })

    except Exception as e:
        print(f"❌ Error on article: {e}")
    time.sleep(random.uniform(1.5, 3.0))

driver.quit()

with open("crhoy_stories.html", "w", encoding="utf-8") as f:
    f.write("<html><head><meta charset='UTF-8'><title>CRHoy Stories</title>")
    f.write("<style>body{font-family:sans-serif;max-width:800px;margin:auto;} h2{color:#003366;} .bias{font-weight:bold;padding:4px 8px;border-radius:4px;} .Neutral{color:green;} .Biased{color:red;} h3{color:#444;} small{color:#555;display:block;margin-bottom:10px;}</style>")
    f.write("</head><body>")
    f.write(f"<h1>CRHoy Stories for {target_date}</h1><hr>")

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
        for paragraph in story["body"].split("\n\n"):
            f.write(f"<p>{paragraph}</p>")
        f.write(f"<a href='{story['url']}' target='_blank'>Leer en crhoy.com</a><hr>")

    f.write("</body></html>")

print(f"\n✅ Done! Output written to: crhoy_stories.html")
