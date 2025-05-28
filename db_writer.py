import os
from dotenv import load_dotenv
from supabase import create_client
from postgrest.exceptions import APIError

# Load environment variables from .env
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_article_to_supabase(article: dict):
    """
    Inserts an article into Supabase only if its URL isn't already present.
    """
    # Basic URL check
    url = article.get("url")
    if not url:
        print("❌ Missing URL—skipping article.")
        return

    # 1) Duplicate check
    try:
        resp = (
            supabase
            .table("articles")
            .select("url")
            .eq("url", url)
            .limit(1)
            .execute()
        )
    except APIError as e:
        print(f"❌ Duplicate-check error: {e}")
        return

    if resp.data:
        print(f"⚠️ Duplicate found—skipping URL: {url}")
        return

    # 2) Insert new article
    try:
        supabase.table("articles").insert(article).execute()
        print(f"✅ Inserted article: {url}")
    except APIError as e:
        print(f"❌ Insert error: {e}")