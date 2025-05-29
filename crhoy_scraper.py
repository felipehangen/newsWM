# crhoy_scraper.py

import requests
import time
import random
import locale
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

Article = Dict[str, Any]

def _parse_spanish_date(date_text: str) -> Optional[str]:
    """Parse Spanish date formats commonly used by CRHoy."""
    if not date_text:
        return None
        
    # Clean the date text
    date_text = date_text.strip().replace('\u2003', ' ').replace('\n', ' ')
    
    # Spanish month names
    spanish_months = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    # Try different Spanish date patterns
    patterns = [
        # "Mayo 24, 2024   11:10 pm"
        r'(\w+)\s+(\d{1,2}),\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*(am|pm)',
        # "24 de Mayo de 2024, 11:10 pm"
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*(am|pm)',
        # "Mayo 24, 2024"
        r'(\w+)\s+(\d{1,2}),\s+(\d{4})',
        # "24 de Mayo de 2024"
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        # Standard ISO format
        r'(\d{4})-(\d{2})-(\d{2})',
        # "24/05/2024"
        r'(\d{1,2})/(\d{1,2})/(\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_text.lower())
        if match:
            try:
                groups = match.groups()
                
                if 'de' in pattern:  # Spanish format: "24 de Mayo de 2024"
                    day, month_name, year = groups[:3]
                    month = spanish_months.get(month_name.lower())
                    if month:
                        if len(groups) > 3:  # Has time
                            hour, minute, ampm = groups[3:6]
                            hour = int(hour)
                            if ampm == 'pm' and hour != 12:
                                hour += 12
                            elif ampm == 'am' and hour == 12:
                                hour = 0
                            dt = datetime(int(year), month, int(day), hour, int(minute))
                        else:
                            dt = datetime(int(year), month, int(day))
                        return dt.isoformat()
                        
                elif groups[0].isalpha():  # English format: "Mayo 24, 2024"
                    month_name, day, year = groups[:3]
                    month = spanish_months.get(month_name.lower())
                    if month:
                        if len(groups) > 3:  # Has time
                            hour, minute, ampm = groups[3:6]
                            hour = int(hour)
                            if ampm == 'pm' and hour != 12:
                                hour += 12
                            elif ampm == 'am' and hour == 12:
                                hour = 0
                            dt = datetime(int(year), month, int(day), hour, int(minute))
                        else:
                            dt = datetime(int(year), month, int(day))
                        return dt.isoformat()
                        
                elif '-' in pattern:  # ISO format
                    year, month, day = groups
                    dt = datetime(int(year), int(month), int(day))
                    return dt.isoformat()
                    
                elif '/' in pattern:  # DD/MM/YYYY
                    day, month, year = groups
                    dt = datetime(int(year), int(month), int(day))
                    return dt.isoformat()
                    
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse date pattern {pattern}: {e}")
                continue
    
    logger.warning(f"Could not parse date: {date_text}")
    return None

def _setup_chrome_driver() -> webdriver.Chrome:
    """Setup Chrome driver with crash prevention measures."""
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1920,1080")
    
    # Memory and stability improvements
    chrome_opts.add_argument("--memory-pressure-off")
    chrome_opts.add_argument("--max_old_space_size=4096")
    chrome_opts.add_argument("--disable-background-timer-throttling")
    chrome_opts.add_argument("--disable-renderer-backgrounding")
    chrome_opts.add_argument("--disable-backgrounding-occluded-windows")
    chrome_opts.add_argument("--disable-ipc-flooding-protection")
    
    # Prevent crashes from heavy content
    chrome_opts.add_argument("--disable-extensions")
    chrome_opts.add_argument("--disable-plugins")
    chrome_opts.add_argument("--disable-images")  # Save memory by not loading images
    chrome_opts.add_argument("--disable-javascript")  # Disable JS if not needed
    chrome_opts.add_argument("--disable-css")
    
    # Resource limits
    chrome_opts.add_argument("--aggressive-cache-discard")
    chrome_opts.add_argument("--memory-pressure-off")
    
    # Anti-detection measures
    chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
    chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_opts.add_experimental_option('useAutomationExtension', False)
    
    # Rotate User-Agent strings to appear more natural
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    selected_ua = random.choice(user_agents)
    chrome_opts.add_argument(f"--user-agent={selected_ua}")
    
    # Additional stability options
    chrome_opts.add_argument("--disable-features=VizDisplayCompositor")
    chrome_opts.add_argument("--disable-web-security")
    chrome_opts.add_argument("--allow-running-insecure-content")
    
    try:
        driver = webdriver.Chrome(options=chrome_opts)
        
        # Execute stealth scripts to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'es']})")
        
        # Set timeouts
        driver.set_page_load_timeout(20)  # Reduced from 30
        driver.implicitly_wait(3)         # Reduced from 5
        
        logger.info(f"Chrome driver initialized successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise

def _is_driver_alive(driver) -> bool:
    """Check if WebDriver is still alive and responsive."""
    try:
        driver.current_url
        return True
    except Exception:
        return False

def _cleanup_driver_memory(driver):
    """Clean up driver memory to prevent crashes."""
    try:
        # Clear browser data
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        
        # Close any extra windows/tabs
        while len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            driver.close()
        
        # Switch back to main window
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
            
        # Force garbage collection
        driver.execute_script("if (window.gc) { window.gc(); }")
        
    except Exception as e:
        logger.debug(f"Memory cleanup failed (non-critical): {e}")

def _is_blocked_response(response) -> bool:
    """Check if the response indicates we're being blocked."""
    if not response:
        return True
        
    # Check status codes
    if response.status_code in [403, 429, 503]:
        return True
    
    # Check for common blocking indicators in content
    content = response.text.lower()
    blocking_indicators = [
        'captcha',
        'blocked',
        'access denied',
        'too many requests',
        'rate limit',
        'cloudflare',
        'security check',
        'unusual traffic',
        'bot detection'
    ]
    
    for indicator in blocking_indicators:
        if indicator in content:
            logger.warning(f"Blocking indicator found: {indicator}")
            return True
    
    # Check content length (very short responses might be blocks)
    if len(response.text.strip()) < 100:
        logger.warning("Suspiciously short response, might be blocked")
        return True
    
    return False

def _handle_potential_blocking(driver, url: str) -> bool:
    """Check if we're being blocked and handle accordingly."""
    try:
        # Check for common blocking elements
        blocking_selectors = [
            '[id*="captcha"]',
            '[class*="captcha"]', 
            '[id*="challenge"]',
            '[class*="challenge"]',
            '.cf-browser-verification',
            '#cf-wrapper'
        ]
        
        for selector in blocking_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    logger.error(f"Blocking element detected: {selector} on {url}")
                    return True
            except:
                continue
        
        # Check page title for blocking indicators
        try:
            title = driver.title.lower()
            if any(word in title for word in ['blocked', 'captcha', 'security', 'challenge']):
                logger.error(f"Blocking detected in page title: {title}")
                return True
        except:
            pass
            
        return False
        
    except Exception as e:
        logger.warning(f"Error checking for blocking: {e}")
        return False

def _safe_scrape_single_article(driver, url: str) -> Optional[Article]:
    """Safely scrape a single article with error handling."""
    try:
        driver.get(url)
        
        # Check if we're being blocked before proceeding
        if _handle_potential_blocking(driver, url):
            logger.error(f"Blocking detected for {url}, skipping...")
            time.sleep(random.uniform(30, 60))
            return None
        
        # Wait for page to load with shorter timeout
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except:
            logger.warning(f"Page load timeout for {url}, trying anyway...")
        
        # Extract headline
        try:
            h1 = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            logger.warning(f"Could not find title for {url}")
            return None
        
        # Extract body paragraphs
        try:
            body_div = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "contenido"))
            )
            paras = [p.text.strip() for p in body_div.find_elements(By.TAG_NAME, "p") if p.text.strip()]
            content = "\n\n".join(paras)
        except:
            logger.warning(f"Could not find content for {url}")
            return None

        # Extract subtitle
        try:
            subtitle = driver.find_element(By.TAG_NAME, "h2").text.strip()
        except:
            subtitle = ""

        # Extract author & email with multiple strategies
        author = ""
        author_email = ""
        
        # Strategy 1: Try the original selector
        try:
            nota = driver.find_element(By.CLASS_NAME, "autor-nota")
            author_link = nota.find_element(By.TAG_NAME, "a")
            author = author_link.get_attribute("title") or author_link.text.strip()
        except:
            pass
        
        # Strategy 2: Try alternative author selectors
        if not author:
            author_selectors = ['.author-name', '.byline a', '[rel="author"]', '.post-author', 
                             '.article-author', 'span.autor-nota a', '.autor a', 'p.autor a']
            
            for selector in author_selectors:
                try:
                    author_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip() or author_elem.get_attribute("title")
                    if author:
                        break
                except:
                    continue
        
        # Extract author email
        email_selectors = ['span.autor-nota a[href^="mailto:"]', '.autor-nota a[href*="@"]', 
                          'a[href^="mailto:"]', '.author-email']
        
        for selector in email_selectors:
            try:
                mail_el = driver.find_element(By.CSS_SELECTOR, selector)
                href = mail_el.get_attribute("href")
                if href and "mailto:" in href:
                    author_email = href.replace("mailto:", "").strip()
                    break
            except:
                continue

        # Extract tags
        tags = []
        tag_selectors = ["div.etiquetas a", ".tags a", ".post-tags a", ".article-tags a", 
                        ".categoria a", ".etiqueta"]
        
        for selector in tag_selectors:
            try:
                tag_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if tag_elements:
                    tags = [t.text.strip() for t in tag_elements if t.text.strip()]
                    if tags:
                        break
            except:
                continue

        # Extract timestamp
        published_date = None
        
        try:
            raw_ts = driver.find_element(By.CLASS_NAME, "fecha-nota").text.strip().replace("\u2003", " ")
            published_date = _parse_spanish_date(raw_ts)
        except:
            pass
        
        if not published_date:
            date_selectors = ['.fecha-nota', '.date', '.post-date', 'time', '.fecha']
            
            for selector in date_selectors:
                try:
                    date_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    date_text = date_elem.text.strip().replace("\u2003", " ")
                    
                    datetime_attr = date_elem.get_attribute('datetime')
                    if datetime_attr:
                        try:
                            published_date = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')).isoformat()
                            break
                        except:
                            pass
                    
                    if date_text:
                        published_date = _parse_spanish_date(date_text)
                        if published_date:
                            break
                except:
                    continue
        
        if not published_date:
            published_date = datetime.utcnow().isoformat()

        # Extract summary
        try:
            meta_desc = driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
            summary = meta_desc.get_attribute("content")
        except:
            summary = content[:200] + "..." if len(content) > 200 else content

        # Extract featured image
        image_url = ""
        img_selectors = ['.featured-image img', '.post-image img', 'article img', '#contenido img']
        
        for selector in img_selectors:
            try:
                img_element = driver.find_element(By.CSS_SELECTOR, selector)
                image_url = img_element.get_attribute("src")
                if image_url:
                    break
            except:
                continue

        # Extract category
        category = "General"
        parsed_url = urlparse(url)
        path_parts = [part for part in parsed_url.path.split('/') if part]
        
        if len(path_parts) > 0:
            potential_category = path_parts[0].lower()
            category_mapping = {
                'nacionales': 'Nacionales', 'economia': 'Economía', 'mundo': 'Mundo',
                'deportes': 'Deportes', 'tecnologia': 'Tecnología', 'entretenimiento': 'Entretenimiento',
                'salud': 'Salud', 'opinion': 'Opinión', 'la-foto-del-dia': 'La Foto del Día'
            }
            category = category_mapping.get(potential_category, potential_category.title())

        # Validate article
        if not h1 or not content or len(content.split()) < 20:
            logger.warning(f"Article missing essential content or too short: {url}")
            return None

        article: Article = {
            "title": h1,
            "subtitle": subtitle,
            "content": content,
            "author": author,
            "author_email": author_email,
            "tags": tags,
            "published_date": published_date,
            "url": url,
            "source": parsed_url.netloc,
            "summary": summary,
            "image_url": image_url,
            "category": category
        }
        
        return article
        
    except Exception as e:
        logger.error(f"Error in _safe_scrape_single_article for {url}: {e}")
        return None

def get_crhoy_articles_with_driver(date_str: str, driver: webdriver.Chrome, limit: Optional[int] = 5) -> List[Article]:
    """
    Scrape CRHoy articles for a single date using provided driver with crash protection.
    """
    # Set Spanish locale for timestamp parsing
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES')
        except:
            logger.warning("Could not set Spanish locale. Timestamp parsing may fail.")

    sitemap_url = f"https://www.crhoy.com/site/dist/sitemap/{date_str}.txt"
    
    # More respectful headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        resp = requests.get(sitemap_url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        # Check for blocking indicators
        if _is_blocked_response(resp):
            logger.error(f"Detected blocking/captcha for sitemap {sitemap_url}")
            return []
            
        urls = resp.text.strip().splitlines()
    except Exception as e:
        logger.error(f"Error fetching sitemap for {date_str}: {e}")
        return []

    total = len(urls)
    logger.info(f"Found {total} URLs for {date_str}")
    
    if limit is not None:
        logger.info(f"Limiting to first {limit}")
        urls_to_fetch = urls[:limit]
    else:
        logger.info("No limit, fetching all URLs")
        urls_to_fetch = urls

    articles: List[Article] = []
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    for idx, url in enumerate(urls_to_fetch, start=1):
        logger.info(f"Processing {idx}/{len(urls_to_fetch)}: {url}")
        
        try:
            # Clean up memory every 15 articles to prevent crashes
            if idx % 15 == 0:
                logger.info("Performing memory cleanup...")
                _cleanup_driver_memory(driver)
                time.sleep(2)
            
            # Check driver health every 20 articles or after failures
            if idx % 20 == 0 or consecutive_failures > 0:
                if not _is_driver_alive(driver):
                    logger.warning("Driver not responsive, recreating...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = _setup_chrome_driver()
                    time.sleep(3)  # Give driver time to stabilize
            
            # Use safe driver operation
            article_data = _safe_scrape_single_article(driver, url)
            
            if article_data:
                articles.append(article_data)
                logger.info(f"Successfully scraped: {article_data['title'][:50]}...")
                consecutive_failures = 0  # Reset failure counter
            else:
                logger.warning(f"Failed to scrape article: {url}")
                consecutive_failures += 1
            
            # If too many consecutive failures, take a longer break
            if consecutive_failures >= max_consecutive_failures:
                logger.warning(f"Too many consecutive failures ({consecutive_failures}), taking longer break...")
                time.sleep(random.uniform(30, 60))
                consecutive_failures = 0
            
        except Exception as err:
            logger.error(f"Error scraping {url}: {err}")
            consecutive_failures += 1
            
            # Force driver recreation after certain types of errors
            error_msg = str(err).lower()
            if any(keyword in error_msg for keyword in ['chrome', 'driver', 'session', 'connection']):
                logger.warning("Driver-related error detected, recreating driver...")
                try:
                    driver.quit()
                except:
                    pass
                driver = _setup_chrome_driver()
                time.sleep(5)  # Give more time after crashes
        
        # Polite pause with exponential backoff on errors
        base_delay = random.uniform(2.5, 5.0)
        if consecutive_failures > 0:
            base_delay *= (1 + consecutive_failures * 0.5)  # Increase delay with failures
        
        time.sleep(base_delay)
        
        # Add extra delay every 10 articles to be extra polite
        if idx % 10 == 0:
            extra_delay = random.uniform(10, 20)
            logger.info(f"Taking extended break ({extra_delay:.1f}s) after {idx} articles...")
            time.sleep(extra_delay)

    logger.info(f"Successfully scraped {len(articles)} articles for {date_str}")
    return articles

def get_crhoy_articles(date_str: str, limit: Optional[int] = 5) -> List[Article]:
    """
    Scrape CRHoy articles for a single date.
    :param date_str: YYYY-MM-DD
    :param limit: max articles to fetch (None => no limit)
    :return: list of article dicts
    """
    driver = _setup_chrome_driver()
    try:
        return get_crhoy_articles_with_driver(date_str, driver, limit)
    finally:
        driver.quit()

def get_crhoy_articles_range(
    start_date_str: str,
    end_date_str: str,
    limit_per_day: Optional[int] = None
) -> List[Article]:
    """
    Scrape CRHoy for every date in [start_date, end_date] with crash protection.
    """
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    if start > end:
        logger.error("Start date must be before or equal to end date")
        return []
    
    # Create driver once for entire range with better error handling
    driver = None
    all_articles: List[Article] = []
    
    try:
        driver = _setup_chrome_driver()
        current = start
        day_count = 0
        
        while current <= end:
            day = current.strftime("%Y-%m-%d")
            day_count += 1
            logger.info(f"\n→ Scraping {day} (Day {day_count})")
            
            try:
                # Recreate driver every 3 days to prevent memory issues
                if day_count % 3 == 0 and day_count > 1:
                    logger.info("Recreating driver for stability (every 3 days)...")
                    try:
                        driver.quit()
                    except:
                        pass
                    time.sleep(5)
                    driver = _setup_chrome_driver()
                
                day_articles = get_crhoy_articles_with_driver(day, driver, limit=limit_per_day)
                all_articles.extend(day_articles)
                
                logger.info(f"Scraped {len(day_articles)} articles for {day}")
                
                # Pause between days (longer pause to be respectful)
                if current < end:  # Don't sleep after last day
                    day_break = random.uniform(5, 10)
                    logger.info(f"Taking break between dates ({day_break:.1f}s)...")
                    time.sleep(day_break)
                
            except Exception as e:
                logger.error(f"Error scraping day {day}: {e}")
                
                # Try to recreate driver if there was an error
                try:
                    driver.quit()
                except:
                    pass
                
                logger.info("Recreating driver after error...")
                driver = _setup_chrome_driver()
                time.sleep(10)  # Longer wait after errors
            
            current += timedelta(days=1)
        
        logger.info(f"Range scraping complete. Total articles: {len(all_articles)}")
        return all_articles
        
    except Exception as e:
        logger.error(f"Critical error in range scraping: {e}")
        return all_articles  # Return what we have so far
        
    finally:
        # Always clean up driver
        if driver:
            try:
                driver.quit()
                logger.info("Driver cleaned up successfully")
            except Exception as e:
                logger.warning(f"Error cleaning up driver: {e}")

if __name__ == "__main__":
    # Simple test harness
    import argparse
    from pprint import pprint

    p = argparse.ArgumentParser(description="Test CRHoy scraper")
    p.add_argument("--date", help="Single date YYYY-MM-DD")
    p.add_argument("--start-date", help="Range start YYYY-MM-DD")
    p.add_argument("--end-date", help="Range end YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=2,
                   help="Max per day (<=0 => unlimited)")
    args = p.parse_args()

    lim = None if args.limit <= 0 else args.limit
    
    try:
        if args.date:
            res = get_crhoy_articles(args.date, limit=lim)
        else:
            if not args.start_date or not args.end_date:
                p.error("Require either --date or both --start-date/--end-date")
            res = get_crhoy_articles_range(
                args.start_date, args.end_date, limit_per_day=lim
            )

        print(f"\nScraped {len(res)} articles:")
        for i, article in enumerate(res, 1):
            print(f"\n{i}. {article['title']}")
            print(f"   URL: {article['url']}")
            print(f"   Category: {article['category']}")
            print(f"   Content length: {len(article['content'])} chars")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        logger.error(f"Error in test: {e}")