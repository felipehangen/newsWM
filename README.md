Scraping news.

main.py




# How to Use the Crash-Resistant Version:
# For Normal Scraping:
bash# Use the robust version for large jobs
python robust_scraper.py --date 2024-05-25 --limit 10

# For date ranges  
python robust_scraper.py --start-date 2024-05-10 --end-date 2024-05-11 --limit 3

# For Heavy Scraping (100+ articles):
bash# Lower limits with automatic retries
python robust_scraper.py --start-date 2024-05-01 --end-date 2024-05-31 --limit 3 --max-retries 5

# Emergency Mode (if crashes persist):
bash# Very conservative settings
python robust_scraper.py --date 2024-05-25 --limit 1 --max-retries 1