# main.py

import argparse
from crhoy_scraper import get_crhoy_articles, get_crhoy_articles_range
from db_writer import save_article_to_supabase

def main():
    parser = argparse.ArgumentParser(
        description="Scrape CRHoy and save articles to Supabase"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date",       help="Single date YYYY-MM-DD")
    group.add_argument("--start-date", help="Start of date range YYYY-MM-DD")
    parser.add_argument(
        "--end-date",
        help="End of date range YYYY-MM-DD (with --start-date)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max articles per day (<=0 = unlimited)"
    )

    args = parser.parse_args()
    # treat <=0 as “no limit”
    limit = None if args.limit <= 0 else args.limit

    if args.date:
        articles = get_crhoy_articles(args.date, limit=limit)
    else:
        if not args.end_date:
            parser.error("--start-date requires --end-date")
        articles = get_crhoy_articles_range(
            args.start_date, args.end_date, limit_per_day=limit
        )

    for article in articles:
        save_article_to_supabase(article)

if __name__ == "__main__":
    main()