#!/usr/bin/env python3
"""
Database Schema Checker for CRHoy News Scraper
This utility helps you understand your current database schema
and provides SQL to add missing columns if needed.
"""

import os
from db_writer import DatabaseWriter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_schema():
    """Check current database schema and suggest improvements."""
    
    try:
        db_writer = DatabaseWriter()
        logger.info("✅ Successfully connected to Supabase")
        
        # Get current schema
        current_columns = db_writer.get_table_schema()
        logger.info(f"📋 Current table columns: {current_columns}")
        
        # Expected columns from our scraper
        expected_columns = {
            'id': 'Primary key (usually auto-generated)',
            'title': 'Article title (required)',
            'content': 'Article content/body (required)', 
            'url': 'Article URL (required, should be unique)',
            'source': 'News source (e.g., CRHoy.com)',
            'author': 'Article author name',
            'author_email': 'Author email address',
            'published_date': 'When article was published',
            'category': 'Article category (e.g., Nacionales, Economia)',
            'summary': 'Article summary/description',
            'subtitle': 'Article subtitle',
            'image_url': 'Featured image URL',
            'tags': 'Article tags (comma-separated)',
            'created_at': 'When record was created',
            'updated_at': 'When record was last updated'
        }
        
        # Check what's missing
        missing_columns = []
        existing_columns = []
        
        for col_name, description in expected_columns.items():
            if col_name in current_columns:
                existing_columns.append(col_name)
            else:
                missing_columns.append((col_name, description))
        
        print("\n" + "="*60)
        print("DATABASE SCHEMA ANALYSIS")
        print("="*60)
        
        print(f"\n✅ EXISTING COLUMNS ({len(existing_columns)}):")
        for col in existing_columns:
            print(f"   • {col} - {expected_columns.get(col, 'Unknown')}")
        
        if missing_columns:
            print(f"\n❌ MISSING COLUMNS ({len(missing_columns)}):")
            for col_name, description in missing_columns:
                print(f"   • {col_name} - {description}")
            
            print(f"\n📝 SQL TO ADD MISSING COLUMNS:")
            print("   Copy and paste this into your Supabase SQL Editor:")
            print("   " + "-"*50)
            
            sql_statements = []
            for col_name, _ in missing_columns:
                if col_name == 'id':
                    continue  # Skip ID, should already exist
                elif col_name in ['created_at', 'updated_at', 'published_date']:
                    sql_statements.append(f"ALTER TABLE articles ADD COLUMN {col_name} TIMESTAMPTZ;")
                elif col_name in ['title', 'content']:
                    sql_statements.append(f"ALTER TABLE articles ADD COLUMN {col_name} TEXT NOT NULL DEFAULT '';")
                elif col_name == 'url':
                    sql_statements.append(f"ALTER TABLE articles ADD COLUMN {col_name} TEXT UNIQUE;")
                else:
                    sql_statements.append(f"ALTER TABLE articles ADD COLUMN {col_name} TEXT;")
            
            for sql in sql_statements:
                print(f"   {sql}")
            
        else:
            print(f"\n🎉 ALL EXPECTED COLUMNS ARE PRESENT!")
        
        # Test with sample data
        print(f"\n🧪 TESTING DATABASE CONNECTION:")
        try:
            recent_articles = db_writer.get_recent_articles(1)
            print(f"   ✅ Successfully queried database")
            print(f"   📊 Recent articles found: {len(recent_articles)}")
            
            if recent_articles:
                sample_article = recent_articles[0]
                print(f"   📝 Sample article fields: {list(sample_article.keys())}")
        except Exception as e:
            print(f"   ❌ Error querying database: {e}")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("="*60)
        
        if missing_columns:
            print("1. Add the missing columns using the SQL statements above")
            print("2. Re-run this script to verify the changes")
            print("3. Then run your scraper again")
        else:
            print("✅ Your database schema looks good!")
            print("🚀 You can run the scraper without issues")
        
        print(f"\n💡 TIP: The scraper will now automatically adapt to your")
        print(f"   current schema and only use available columns.")
        
    except Exception as e:
        logger.error(f"❌ Error checking database schema: {e}")
        print(f"\n🔧 TROUBLESHOOTING:")
        print(f"   Make sure your environment variables are set:")
        print(f"   export SUPABASE_URL='your_project_url'")
        print(f"   export SUPABASE_KEY='your_anon_key'")

if __name__ == "__main__":
    check_database_schema()