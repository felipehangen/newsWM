#!/usr/bin/env python3
"""
Robust scraper that automatically handles crashes and restarts
Use this instead of main.py for large scraping jobs
"""

import argparse
import sys
import time
import logging
import os
from datetime import datetime, timedelta
from crhoy_scraper import get_crhoy_articles, get_crhoy_articles_range
from db_writer import DatabaseWriter
import traceback

def setup_logging():
    """Setup comprehensive logging system with session organization."""
    
    # Create LOGS directory if it doesn't exist
    logs_dir = "LOGS"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create session timestamp
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create session directory
    session_dir = os.path.join(logs_dir, f"session_{session_timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Define log files
    main_log = os.path.join(session_dir, "scraper_main.log")
    stats_log = os.path.join(session_dir, "session_stats.log")
    errors_log = os.path.join(session_dir, "errors.log")
    
    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Setup main logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(main_log, encoding='utf-8'),
            logging.StreamHandler()  # Console output
        ]
    )
    
    # Setup stats logger (for session statistics)
    stats_logger = logging.getLogger('session_stats')
    stats_handler = logging.FileHandler(stats_log, encoding='utf-8')
    stats_formatter = logging.Formatter('%(asctime)s - %(message)s')
    stats_handler.setFormatter(stats_formatter)
    stats_logger.addHandler(stats_handler)
    stats_logger.setLevel(logging.INFO)
    stats_logger.propagate = False  # Don't duplicate to main logger
    
    # Setup error logger (for detailed errors)
    error_logger = logging.getLogger('errors_only')
    error_handler = logging.FileHandler(errors_log, encoding='utf-8')
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False  # Don't duplicate to main logger
    
    return session_dir, stats_logger, error_logger

class SessionStats:
    """Track detailed statistics for the scraping session."""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.dates_attempted = 0
        self.dates_successful = 0
        self.dates_failed = 0
        self.total_articles_found = 0
        self.total_articles_scraped = 0
        self.total_articles_saved = 0
        self.total_articles_failed = 0
        self.total_duplicates = 0
        self.errors = []
        self.date_details = {}  # Per-date breakdown
    
    def add_date_result(self, date_str: str, found: int, scraped: int, saved: int, failed: int, duplicates: int = 0, success: bool = True):
        """Add results for a specific date."""
        self.dates_attempted += 1
        if success:
            self.dates_successful += 1
        else:
            self.dates_failed += 1
        
        self.total_articles_found += found
        self.total_articles_scraped += scraped
        self.total_articles_saved += saved
        self.total_articles_failed += failed
        self.total_duplicates += duplicates
        
        self.date_details[date_str] = {
            'found': found,
            'scraped': scraped,
            'saved': saved,
            'failed': failed,
            'duplicates': duplicates,
            'success': success,
            'timestamp': datetime.now()
        }
    
    def add_error(self, error_type: str, error_msg: str, context: str = ""):
        """Add an error to the tracking."""
        self.errors.append({
            'timestamp': datetime.now(),
            'type': error_type,
            'message': error_msg,
            'context': context
        })
    
    def get_summary(self) -> str:
        """Generate a comprehensive session summary."""
        duration = datetime.now() - self.session_start
        
        summary = f"""
{'='*80}
SCRAPING SESSION SUMMARY
{'='*80}
Session Duration: {duration}
Session Start: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
Session End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DATES PROCESSED:
  • Dates Attempted: {self.dates_attempted}
  • Dates Successful: {self.dates_successful}
  • Dates Failed: {self.dates_failed}
  • Success Rate: {(self.dates_successful/max(self.dates_attempted, 1)*100):.1f}%

ARTICLES OVERVIEW:
  • Total Articles Found: {self.total_articles_found}
  • Total Articles Scraped: {self.total_articles_scraped}
  • Total Articles Saved to DB: {self.total_articles_saved}
  • Total Articles Failed: {self.total_articles_failed}
  • Total Duplicates Skipped: {self.total_duplicates}

PERFORMANCE METRICS:
  • Scraping Success Rate: {(self.total_articles_scraped/max(self.total_articles_found, 1)*100):.1f}%
  • Database Save Rate: {(self.total_articles_saved/max(self.total_articles_scraped, 1)*100):.1f}%
  • Articles per Hour: {(self.total_articles_scraped/max(duration.total_seconds()/3600, 1)):.1f}
  • Total Errors: {len(self.errors)}

{'='*80}
PER-DATE BREAKDOWN:
{'='*80}"""
        
        for date_str, details in self.date_details.items():
            status = "✅ SUCCESS" if details['success'] else "❌ FAILED"
            summary += f"""
{date_str} - {status}
  Found: {details['found']} | Scraped: {details['scraped']} | Saved: {details['saved']} | Failed: {details['failed']} | Duplicates: {details['duplicates']}"""
        
        if self.errors:
            summary += f"""

{'='*80}
ERROR SUMMARY:
{'='*80}"""
            error_types = {}
            for error in self.errors:
                error_type = error['type']
                if error_type in error_types:
                    error_types[error_type] += 1
                else:
                    error_types[error_type] = 1
            
            for error_type, count in error_types.items():
                summary += f"\n  • {error_type}: {count} occurrences"
        
        summary += f"\n{'='*80}\n"
        return summary

def main():
    # Setup logging first
    session_dir, stats_logger, error_logger = setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize session statistics
    stats = SessionStats()
    
    parser = argparse.ArgumentParser(
        description="Robust CRHoy scraper with comprehensive logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python robust_scraper.py --date 2024-05-29 --limit 10
  python robust_scraper.py --start-date 2024-05-25 --end-date 2024-05-29 --limit 5
  python robust_scraper.py --date 2024-05-29 --limit 0  # No limit

Logs are saved to: LOGS/session_YYYYMMDD_HHMMSS/
  - scraper_main.log: Complete scraping log
  - session_stats.log: Statistics and summaries
  - errors.log: Detailed error information
  - SESSION_SUMMARY.txt: Final session report
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Single date (YYYY-MM-DD)")
    group.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD, required with --start-date)")
    parser.add_argument("--limit", type=int, default=10, help="Max articles per day (0 = unlimited)")
    
    args = parser.parse_args()
    
    if args.start_date and not args.end_date:
        parser.error("--start-date requires --end-date")
    
    limit = None if args.limit <= 0 else args.limit
    
    # Log session start
    logger.info("🚀 ROBUST CRHOY SCRAPER STARTED")
    logger.info(f"📁 Session Directory: {session_dir}")
    logger.info(f"📅 Date(s): {args.date or f'{args.start_date} to {args.end_date}'}")
    logger.info(f"🎯 Limit per day: {'unlimited' if limit is None else limit}")
    
    # Log to stats file
    stats_logger.info("="*80)
    stats_logger.info("SESSION CONFIGURATION")
    stats_logger.info("="*80)
    stats_logger.info(f"Target Date(s): {args.date or f'{args.start_date} to {args.end_date}'}")
    stats_logger.info(f"Articles per Day: {limit or 'UNLIMITED'}")
    stats_logger.info(f"Session ID: {os.path.basename(session_dir)}")
    stats_logger.info("="*80)
    
    try:
        # Initialize database
        db_writer = DatabaseWriter()
        logger.info("✅ Database connection established")
        stats_logger.info("✅ Database connection established successfully")
        
        if args.date:
            # Single date
            logger.info(f"🎯 Mode: Single Date Scraping")
            stats_logger.info(f"🎯 Mode: Single Date Scraping")
            stats_logger.info(f"📅 Processing date: {args.date}")
            
            articles = get_crhoy_articles(args.date, limit=limit)
            articles_found = len(articles) if articles else 0
            
            if articles:
                logger.info(f"✅ Scraped {len(articles)} articles from {args.date}")
                stats_logger.info(f"✅ Found and scraped {len(articles)} articles from {args.date}")
                
                # Save to database
                results = db_writer.save_articles_batch(articles)
                saved = results.get('success', 0)
                failed = results.get('failed', 0)
                duplicates = results.get('duplicates', 0)
                
                logger.info(f"💾 Database Results: Saved={saved}, Failed={failed}, Duplicates={duplicates}")
                stats_logger.info(f"💾 Database Results: Saved={saved}, Failed={failed}, Duplicates={duplicates}")
                
                # Record stats
                stats.add_date_result(args.date, articles_found, len(articles), saved, failed, duplicates, True)
            else:
                logger.info(f"⚠️ No articles found for {args.date}")
                stats_logger.info(f"⚠️ No articles found for {args.date}")
                stats.add_date_result(args.date, 0, 0, 0, 0, 0, True)
                
        else:
            # Date range
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            total_days = (end_date - start_date).days + 1
            
            logger.info(f"🎯 Mode: Date Range Scraping ({total_days} days)")
            stats_logger.info(f"🎯 Mode: Date Range Scraping")
            stats_logger.info(f"📅 Date Range: {args.start_date} to {args.end_date} ({total_days} days)")
            
            current_date = start_date
            day_count = 0
            
            while current_date <= end_date:
                day_count += 1
                date_str = current_date.strftime("%Y-%m-%d")
                
                logger.info(f"📅 Processing day {day_count}/{total_days}: {date_str}")
                stats_logger.info(f"📅 Processing day {day_count}/{total_days}: {date_str}")
                
                try:
                    articles = get_crhoy_articles(date_str, limit=limit)
                    articles_found = len(articles) if articles else 0
                    
                    if articles:
                        logger.info(f"✅ Scraped {len(articles)} articles from {date_str}")
                        stats_logger.info(f"✅ Found and scraped {len(articles)} articles from {date_str}")
                        
                        # Save to database
                        results = db_writer.save_articles_batch(articles)
                        saved = results.get('success', 0)
                        failed = results.get('failed', 0)
                        duplicates = results.get('duplicates', 0)
                        
                        logger.info(f"💾 Database Results: Saved={saved}, Failed={failed}, Duplicates={duplicates}")
                        stats_logger.info(f"💾 Database Results for {date_str}: Saved={saved}, Failed={failed}, Duplicates={duplicates}")
                        
                        # Record stats
                        stats.add_date_result(date_str, articles_found, len(articles), saved, failed, duplicates, True)
                    else:
                        logger.info(f"⚠️ No articles found for {date_str}")
                        stats_logger.info(f"⚠️ No articles found for {date_str}")
                        stats.add_date_result(date_str, 0, 0, 0, 0, 0, True)
                
                except Exception as e:
                    error_msg = f"❌ Error processing {date_str}: {e}"
                    logger.error(error_msg)
                    error_logger.error(error_msg)
                    error_logger.error(f"Full traceback: {traceback.format_exc()}")
                    stats.add_error("DATE_PROCESSING_ERROR", str(e), date_str)
                    stats.add_date_result(date_str, 0, 0, 0, 0, 0, False)
                
                current_date += timedelta(days=1)
                
                # Brief pause between dates
                if current_date <= end_date:
                    time.sleep(2)
        
        logger.info("✅ Scraping completed successfully")
        stats_logger.info("✅ Scraping session completed successfully")
        
        # Generate final summary
        summary = stats.get_summary()
        
        # Save summary to file
        summary_file = os.path.join(session_dir, "SESSION_SUMMARY.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        # Log summary to stats
        stats_logger.info(summary)
        
        # Print key metrics to console
        print(f"\n{'='*60}")
        print(f"📊 SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"📁 Logs saved to: {session_dir}")
        print(f"📅 Dates processed: {stats.dates_successful}/{stats.dates_attempted}")
        print(f"📈 Articles found: {stats.total_articles_found}")
        print(f"✅ Articles scraped: {stats.total_articles_scraped}")
        print(f"💾 Articles saved: {stats.total_articles_saved}")
        print(f"❌ Errors: {len(stats.errors)}")
        print(f"{'='*60}")
        
        return 0
        
    except Exception as e:
        error_msg = f"❌ Critical error: {e}"
        logger.error(error_msg)
        error_logger.error(error_msg)
        error_logger.error(f"Full traceback: {traceback.format_exc()}")
        stats.add_error("CRITICAL_ERROR", str(e), "Main execution")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)