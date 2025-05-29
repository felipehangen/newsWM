# main.py

import argparse
import sys
import logging
from datetime import datetime
from crhoy_scraper import get_crhoy_articles, get_crhoy_articles_range
from db_writer import DatabaseWriter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_date_format(date_string: str) -> bool:
    """Validate date string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Scrape CRHoy news articles and save to Supabase database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --date 2024-05-29                    # Scrape articles from specific date
  python main.py --date 2024-05-29 --limit 10        # Limit to 10 articles
  python main.py --start-date 2024-05-25 --end-date 2024-05-29  # Date range
  python main.py --date 2024-05-29 --limit 0         # No limit (scrape all)
        """
    )
    
    # Mutually exclusive group for date options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--date", 
        help="Single date to scrape (YYYY-MM-DD format)"
    )
    group.add_argument(
        "--start-date", 
        help="Start of date range (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--end-date",
        help="End of date range (YYYY-MM-DD format, required with --start-date)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum articles per day (default: 5, use 0 for unlimited)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape articles but don't save to database (for testing)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    try:
        # Validate date formats
        if args.date:
            if not validate_date_format(args.date):
                parser.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
        
        if args.start_date:
            if not args.end_date:
                parser.error("--start-date requires --end-date")
            
            if not validate_date_format(args.start_date):
                parser.error(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD")
            
            if not validate_date_format(args.end_date):
                parser.error(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD")
            
            # Check date order
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(args.end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                parser.error("Start date must be before or equal to end date")

        # Treat <=0 as "no limit"
        limit = None if args.limit <= 0 else args.limit
        
        # Log configuration
        logger.info("=== CRHoy News Scraper Started ===")
        if args.date:
            logger.info(f"Scraping date: {args.date}")
        else:
            logger.info(f"Scraping date range: {args.start_date} to {args.end_date}")
        
        logger.info(f"Articles per day limit: {'unlimited' if limit is None else limit}")
        logger.info(f"Dry run mode: {'enabled' if args.dry_run else 'disabled'}")

        # Initialize database writer (unless dry run)
        db_writer = None
        if not args.dry_run:
            try:
                db_writer = DatabaseWriter()
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                logger.error("Make sure SUPABASE_URL and SUPABASE_KEY environment variables are set")
                return 1

        # Scrape articles
        logger.info("Starting article scraping...")
        start_time = datetime.now()
        
        if args.date:
            articles = get_crhoy_articles(args.date, limit=limit)
        else:
            articles = get_crhoy_articles_range(
                args.start_date, args.end_date, limit_per_day=limit
            )

        scraping_time = datetime.now() - start_time
        logger.info(f"Scraping completed in {scraping_time}")
        logger.info(f"Total articles scraped: {len(articles)}")

        if not articles:
            logger.warning("No articles were scraped")
            return 0

        # Save to database (unless dry run)
        if args.dry_run:
            logger.info("DRY RUN - Articles not saved to database")
            
            # Show sample of scraped articles
            logger.info("Sample of scraped articles:")
            for i, article in enumerate(articles[:3], 1):
                logger.info(f"  {i}. {article['title'][:60]}...")
                logger.info(f"     URL: {article['url']}")
                logger.info(f"     Category: {article['category']}")
                logger.info(f"     Content length: {len(article['content'])} chars")
        else:
            logger.info("Saving articles to database...")
            save_start_time = datetime.now()
            
            results = db_writer.save_articles_batch(articles)
            
            save_time = datetime.now() - save_start_time
            logger.info(f"Database save completed in {save_time}")
            
            # Log results
            logger.info("=== SAVE RESULTS ===")
            logger.info(f"Successfully saved: {results['success']}")
            logger.info(f"Failed to save: {results['failed']}")
            logger.info(f"Duplicates skipped: {results['duplicates']}")
            logger.info(f"Invalid articles: {results.get('invalid', 0)}")
            
            if results['failed'] > 0:
                logger.warning(f"{results['failed']} articles failed to save - check logs above")

        total_time = datetime.now() - start_time
        logger.info(f"=== TOTAL EXECUTION TIME: {total_time} ===")
        
        return 0

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        return 130  # Standard exit code for Ctrl+C
    
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {e}")
        logger.exception("Full traceback:")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)