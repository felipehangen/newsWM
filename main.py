from crhoy_scraper import get_crhoy_articles
from db_writer import save_article_to_supabase

def main():
    date_input = input("📅 Enter the date (YYYY-MM-DD): ").strip()
    articles = get_crhoy_articles(date_input)

    for i, article in enumerate(articles, 1):
        print(f"\n📄 Saving article {i}/{len(articles)}: {article['title'][:60]}...")
        save_article_to_supabase(article)

    print("\n✅ All done!")

if __name__ == "__main__":
    main()