#db_writer.py

import json
import os

from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime



load_dotenv()

# 🔑 Supabase config
SUPABASE_URL = "https://ezastdzwipwvtebvwrhx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_article_to_supabase(article):
    # Convert timestamp to UTC ISO format if it's not already
    try:
        dt = datetime.fromisoformat(article["timestamp"])
        article["timestamp"] = dt.astimezone().isoformat()
    except Exception as e:
        print(f"⚠️ Failed to convert timestamp to UTC: {e}")

    # Remove hashtags from tags
    article["tags"] = [tag.replace("#", "").strip() for tag in article.get("tags", []) if tag.strip()]

    try:
        json.dumps(article)
        print("📦 Inserting article to Supabase...")
        response = supabase.table("Articles").insert(article).execute()

        if hasattr(response, 'data'):
            print("✅ Inserted successfully!")
        else:
            print(f"❌ Insert failed! Full response: {response}")

    except Exception as e:
        if hasattr(e, 'message'):
            print(f"❌ Error inserting article: {e.message}")
        else:
            print(f"❌ Error inserting article: {e}")