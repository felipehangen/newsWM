# scraper_config.py
"""
Configuration settings for CRHoy scraper anti-detection measures
Adjust these values based on your needs and server responses
"""

# Rate limiting settings
RATE_LIMITS = {
    'min_delay': 2.5,           # Minimum seconds between requests
    'max_delay': 5.0,           # Maximum seconds between requests
    'batch_break_every': 10,    # Take extended break every N articles
    'batch_break_min': 10,      # Minimum extended break time (seconds)
    'batch_break_max': 20,      # Maximum extended break time (seconds)
    'daily_break_every': 50,    # Take long break every N articles
    'daily_break_min': 60,      # Minimum daily break time (seconds)
    'daily_break_max': 120      # Maximum daily break time (seconds)
}

# Retry settings
RETRY_SETTINGS = {
    'max_retries': 3,
    'backoff_multiplier': 2,
    'base_delay': 2,
    'max_delay': 60
}

# User agents (rotated randomly)
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Browser window sizes (rotated randomly)
WINDOW_SIZES = [
    "1920,1080",
    "1366,768", 
    "1440,900",
    "1536,864",
    "1280,720"
]

# Blocking detection keywords
BLOCKING_INDICATORS = [
    'captcha',
    'blocked',
    'access denied',
    'too many requests',
    'rate limit',
    'cloudflare',
    'security check',
    'unusual traffic',
    'bot detection',
    'please verify',
    'human verification'
]

# Respectful scraping settings
POLITENESS_SETTINGS = {
    'respect_robots_txt': True,
    'max_concurrent_requests': 1,  # Never make parallel requests
    'session_timeout': 30,
    'page_load_timeout': 30,
    'implicit_wait': 5
}

# Emergency settings (when detection is high)
EMERGENCY_MODE = {
    'min_delay': 10,            # Much slower requests
    'max_delay': 20,
    'emergency_break': 300,     # 5 minute break
    'max_articles_per_run': 5   # Limit articles per run
}

def get_rate_limit_config(emergency_mode: bool = False):
    """Get rate limiting configuration."""
    if emergency_mode:
        return EMERGENCY_MODE
    return RATE_LIMITS

def should_enable_emergency_mode(failed_requests: int, total_requests: int) -> bool:
    """Determine if we should switch to emergency mode."""
    if total_requests < 10:
        return False
    
    failure_rate = failed_requests / total_requests
    return failure_rate > 0.3  # If more than 30% of requests fail

# Headers that make requests look more natural
NATURAL_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"'
}