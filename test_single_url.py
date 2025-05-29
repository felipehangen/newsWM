#!/usr/bin/env python3
"""
Test script to debug a single CRHoy article URL
This helps you see exactly what data is being extracted
"""

import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from crhoy_scraper import _setup_chrome_driver, _parse_spanish_date
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_single_url(url: str):
    """Test scraping a single URL and show all extracted data."""
    
    print(f"\n{'='*60}")
    print(f"TESTING URL: {url}")
    print(f"{'='*60}")
    
    driver = _setup_chrome_driver()
    
    try:
        driver.get(url)
        print("✅ Page loaded successfully")
        
        # Test each extraction method
        print(f"\n📰 TITLE EXTRACTION:")
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
            print(f"   ✅ Title: {title}")
        except Exception as e:
            print(f"   ❌ Title failed: {e}")
            title = ""
        
        print(f"\n📝 CONTENT EXTRACTION:")
        try:
            body_div = driver.find_element(By.ID, "contenido")
            paras = [p.text.strip() for p in body_div.find_elements(By.TAG_NAME, "p") if p.text.strip()]
            content = "\n\n".join(paras)
            print(f"   ✅ Content length: {len(content)} characters")
            print(f"   📖 First 200 chars: {content[:200]}...")
        except Exception as e:
            print(f"   ❌ Content failed: {e}")
            content = ""
        
        print(f"\n👤 AUTHOR EXTRACTION:")
        author_found = False
        
        # Test Strategy 1: Original selector
        try:
            nota = driver.find_element(By.CLASS_NAME, "autor-nota")
            author_link = nota.find_element(By.TAG_NAME, "a")
            author = author_link.get_attribute("title") or author_link.text.strip()
            if author:
                print(f"   ✅ Strategy 1 (autor-nota): {author}")
                author_found = True
        except Exception as e:
            print(f"   ❌ Strategy 1 failed: {e}")
        
        # Test alternative selectors
        if not author_found:
            author_selectors = [
                '.author-name', '.byline a', '[rel="author"]', '.post-author',
                '.article-author', 'span.autor-nota a', '.autor a', 'p.autor a'
            ]
            
            for i, selector in enumerate(author_selectors, 2):
                try:
                    author_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip() or author_elem.get_attribute("title")
                    if author:
                        print(f"   ✅ Strategy {i} ({selector}): {author}")
                        author_found = True
                        break
                except:
                    continue
        
        if not author_found:
            print("   ❌ No author found with any strategy")
        
        print(f"\n📧 AUTHOR EMAIL EXTRACTION:")
        email_found = False
        email_selectors = [
            'span.autor-nota a[href^="mailto:"]',
            '.autor-nota a[href*="@"]',
            'a[href^="mailto:"]',
            '.author-email'
        ]
        
        for i, selector in enumerate(email_selectors, 1):
            try:
                mail_el = driver.find_element(By.CSS_SELECTOR, selector)
                href = mail_el.get_attribute("href")
                if href and "mailto:" in href:
                    email = href.replace("mailto:", "").strip()
                    print(f"   ✅ Strategy {i} ({selector}): {email}")
                    email_found = True
                    break
            except:
                continue
        
        if not email_found:
            print("   ❌ No author email found")
        
        print(f"\n🏷️ TAGS EXTRACTION:")
        tags_found = False
        tag_selectors = [
            "div.etiquetas a", ".tags a", ".post-tags a", 
            ".article-tags a", ".categoria a", ".etiqueta"
        ]
        
        for i, selector in enumerate(tag_selectors, 1):
            try:
                tag_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if tag_elements:
                    tags = [t.text.strip() for t in tag_elements if t.text.strip()]
                    if tags:
                        print(f"   ✅ Strategy {i} ({selector}): {tags}")
                        tags_found = True
                        break
            except:
                continue
        
        if not tags_found:
            print("   ❌ No tags found")
        
        print(f"\n📅 DATE EXTRACTION:")
        date_found = False
        
        # Test original selector
        try:
            raw_ts = driver.find_element(By.CLASS_NAME, "fecha-nota").text.strip()
            print(f"   📝 Raw date text: '{raw_ts}'")
            parsed_date = _parse_spanish_date(raw_ts)
            if parsed_date:
                print(f"   ✅ Strategy 1 (fecha-nota): {parsed_date}")
                date_found = True
        except Exception as e:
            print(f"   ❌ Strategy 1 failed: {e}")
        
        # Test alternative selectors
        if not date_found:
            date_selectors = [
                '.date', '.post-date', '.article-date', 
                '.published-date', 'time', '.fecha'
            ]
            
            for i, selector in enumerate(date_selectors, 2):
                try:
                    date_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    date_text = date_elem.text.strip()
                    if date_text:
                        print(f"   📝 Raw date text ({selector}): '{date_text}'")
                        parsed_date = _parse_spanish_date(date_text)
                        if parsed_date:
                            print(f"   ✅ Strategy {i} ({selector}): {parsed_date}")
                            date_found = True
                            break
                except:
                    continue
        
        if not date_found:
            print("   ❌ No date found with any strategy")
        
        print(f"\n📂 CATEGORY EXTRACTION:")
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        path_parts = [part for part in parsed_url.path.split('/') if part]
        
        if path_parts:
            category_from_url = path_parts[0]
            print(f"   ✅ From URL: {category_from_url}")
        else:
            print("   ❌ Could not extract category from URL")
        
        print(f"\n🖼️ IMAGE EXTRACTION:")
        image_found = False
        image_selectors = [
            '.featured-image img', '.post-image img', 
            'article img', '#contenido img'
        ]
        
        for i, selector in enumerate(image_selectors, 1):
            try:
                img_elem = driver.find_element(By.CSS_SELECTOR, selector)
                img_url = img_elem.get_attribute("src")
                if img_url:
                    print(f"   ✅ Strategy {i} ({selector}): {img_url}")
                    image_found = True
                    break
            except:
                continue
        
        if not image_found:
            print("   ❌ No featured image found")
        
        # Show page source snippet for debugging
        print(f"\n🔍 HTML DEBUGGING:")
        try:
            # Look for author-related elements
            print("   Looking for author-related elements...")
            author_elements = driver.find_elements(By.CSS_SELECTOR, "*[class*='autor'], *[class*='author'], *[id*='autor'], *[id*='author']")
            for elem in author_elements[:5]:  # Show first 5
                print(f"     Found: <{elem.tag_name} class='{elem.get_attribute('class')}' id='{elem.get_attribute('id')}'>{elem.text[:50]}...")
        except:
            pass
        
        try:
            # Look for date-related elements
            print("   Looking for date-related elements...")
            date_elements = driver.find_elements(By.CSS_SELECTOR, "*[class*='fecha'], *[class*='date'], *[class*='tiempo'], time")
            for elem in date_elements[:5]:  # Show first 5
                print(f"     Found: <{elem.tag_name} class='{elem.get_attribute('class')}'>{elem.text[:50]}...")
        except:
            pass
        
    finally:
        driver.quit()
    
    print(f"\n{'='*60}")
    print("TESTING COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_single_url.py <URL>")
        print("Example: python test_single_url.py 'https://www.crhoy.com/entretenimiento/ave-maria-david-bisbal-se-entrego-hasta-la-ultima-gota-a-costa-rica/'")
        sys.exit(1)
    
    url = sys.argv[1]
    test_single_url(url)
    