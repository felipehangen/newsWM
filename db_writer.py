# db_writer.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any

# 1) Load .env
load_dotenv()  # looks for a file named ".env" in the current working dir

# 2) Read in your Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# 3) Validate
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing Supabase credentials. "
        "Please create a .env file with SUPABASE_URL and SUPABASE_KEY."
    )

# 4) Create the client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_article_to_supabase(article: Dict[str, Any]) -> None:
    """
    Inserts an article into Supabase, skipping it if the URL already exists.
    Expects `article` to be a flat dict matching your Supabase table schema.
    """
    # 4.1) Check for duplicate URL
    existing = (
        supabase
        .table("articles")
        .select("id")
        .eq("url", article["url"])
        .maybe_single()
        .execute()
    )
    if existing.error:
        print(f"❌ Error checking duplicates: {existing.error}")
        return

    if existing.data is not None:
        print(f"🔁 Skipping duplicate: {article['url']}")
        return

    # 4.2) Insert new record
    result = supabase.table("articles").insert(article).execute()
    if result.error:
        print(f"❌ Error inserting article: {result.error}")
    else:
        print(f"✅ Saved: {article['url']}")