import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseWriter:
    def __init__(self):
        """Initialize the database writer with Supabase client."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set.\n"
                "Create a .env file or export these variables:\n"
                "export SUPABASE_URL='your_supabase_project_url'\n"
                "export SUPABASE_KEY='your_supabase_anon_key'"
            )
        
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    def generate_article_hash(self, article: Dict[str, Any]) -> str:
        """Generate a unique hash for an article based on its URL or content."""
        identifier = article.get('url', '') or f"{article.get('title', '')}{article.get('content', '')[:100]}"
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def validate_article(self, article: Dict[str, Any]) -> bool:
        """Validate article has required fields."""
        required_fields = ['title', 'content', 'url']
        
        for field in required_fields:
            if not article.get(field):
                logger.warning(f"Article missing required field '{field}': {article.get('title', 'Unknown')}")
                return False
        
        # Check minimum content length
        if len(article.get('content', '').split()) < 10:
            logger.warning(f"Article content too short: {article.get('title', 'Unknown')}")
            return False
            
        return True
    
    def get_table_schema(self) -> List[str]:
        """Get the available columns from the articles table."""
        try:
            # Try to get table info by doing a select with limit 0
            result = self.supabase.table('articles').select("*").limit(0).execute()
            
            # If we can get some data, try to infer columns from an existing record
            test_result = self.supabase.table('articles').select("*").limit(1).execute()
            if test_result.data and len(test_result.data) > 0:
                return list(test_result.data[0].keys())
            
            # Fallback to basic columns that should always exist
            return ['title', 'content', 'url', 'created_at']
            
        except Exception as e:
            logger.warning(f"Could not determine table schema: {e}")
            # Return basic required columns
            return ['title', 'content', 'url', 'created_at']

    def save_article_to_supabase(self, article: Dict[str, Any]) -> bool:
        """
        Save an article to Supabase database.
        
        Args:
            article: Dictionary containing article data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate article first
            if not self.validate_article(article):
                return False
            
            # Check if article already exists using URL as unique identifier
            article_url = article.get('url', '')
            if article_url:
                existing = self.supabase.table('articles').select("id").eq('url', article_url).execute()
                
                if existing.data and len(existing.data) > 0:
                    logger.info(f"Article already exists: {article.get('title', 'Unknown')[:50]}...")
                    return True
            
            # Get available table columns
            available_columns = self.get_table_schema()
            
            # Prepare article data with all possible fields
            all_article_data = {
                'title': article.get('title', ''),
                'content': article.get('content', ''),
                'url': article.get('url', ''),
                'source': article.get('source', 'CRHoy.com'),
                'author': article.get('author', ''),
                'published_date': self._normalize_date(article.get('published_date')),
                'category': article.get('category', 'General'),
                'summary': article.get('summary', ''),
                'image_url': article.get('image_url', ''),
                'created_at': datetime.utcnow().isoformat(),
                'subtitle': article.get('subtitle', ''),
                'author_email': article.get('author_email', ''),
                'tags': self._format_tags(article.get('tags', []))
            }
            
            # Only include fields that exist in the database schema
            article_data = {}
            for key, value in all_article_data.items():
                if key in available_columns and value is not None and value != '':
                    article_data[key] = value
            
            # Ensure we have at least the required fields
            required_fields = ['title', 'content', 'url']
            for field in required_fields:
                if field not in article_data:
                    article_data[field] = all_article_data.get(field, '')
            
            logger.debug(f"Saving article with fields: {list(article_data.keys())}")
            
            # Insert the article
            result = self.supabase.table('articles').insert(article_data).execute()
            
            # Check if insertion was successful
            if result.data and len(result.data) > 0:
                logger.info(f"Successfully saved article: {article.get('title', 'Unknown')[:50]}...")
                return True
            else:
                logger.error(f"Failed to save article (no data returned): {article.get('title', 'Unknown')}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a column not found error
            if "could not find" in error_msg.lower() and "column" in error_msg.lower():
                logger.warning(f"Database schema mismatch: {error_msg}")
                logger.info("Retrying with basic fields only...")
                
                # Retry with only basic fields
                return self._save_article_basic_fields(article)
            else:
                logger.error(f"Error saving article to database: {error_msg}")
                logger.error(f"Article title: {article.get('title', 'Unknown')}")
                return False

    def _format_tags(self, tags) -> str:
        """Format tags for database storage."""
        if not tags:
            return ''
        if isinstance(tags, list):
            return ', '.join(str(tag) for tag in tags if tag)
        return str(tags)

    def _save_article_basic_fields(self, article: Dict[str, Any]) -> bool:
        """Save article with only the most basic fields."""
        try:
            # Use only the most basic fields that should exist in any articles table
            basic_data = {
                'title': article.get('title', ''),
                'content': article.get('content', ''),
                'url': article.get('url', ''),
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Add author if the field might exist
            if article.get('author'):
                basic_data['author'] = article.get('author', '')
            
            # Add source if the field might exist  
            if article.get('source'):
                basic_data['source'] = article.get('source', 'CRHoy.com')
                
            result = self.supabase.table('articles').insert(basic_data).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Successfully saved article (basic fields): {article.get('title', 'Unknown')[:50]}...")
                return True
            else:
                logger.error(f"Failed to save article even with basic fields: {article.get('title', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving article with basic fields: {str(e)}")
            return False
    
    def _normalize_date(self, date_value: Any) -> Optional[str]:
        """Normalize date to ISO format string."""
        if not date_value:
            return None
            
        if isinstance(date_value, str):
            try:
                # Try to parse and reformat to ensure consistency
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return dt.isoformat()
            except:
                return date_value  # Return as-is if can't parse
        elif isinstance(date_value, datetime):
            return date_value.isoformat()
        
        return str(date_value)
    
    def save_articles_batch(self, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Save multiple articles in batch with improved error handling.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dict with success, failed, and duplicate counts
        """
        results = {'success': 0, 'failed': 0, 'duplicates': 0, 'invalid': 0}
        
        if not articles:
            logger.warning("No articles provided to save")
            return results
        
        logger.info(f"Starting batch save of {len(articles)} articles")
        
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"Processing article {i}/{len(articles)}: {article.get('title', 'Unknown')[:50]}...")
                
                # Check if already exists first
                article_url = article.get('url', '')
                if article_url:
                    existing = self.supabase.table('articles').select("id").eq('url', article_url).execute()
                    if existing.data and len(existing.data) > 0:
                        results['duplicates'] += 1
                        continue
                
                if self.save_article_to_supabase(article):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Error in batch save for article {i}: {str(e)}")
                results['failed'] += 1
        
        logger.info(f"Batch save complete: {results}")
        return results
    
    def get_article_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an article by its URL.
        
        Args:
            url: The article URL
            
        Returns:
            Article data if found, None otherwise
        """
        try:
            result = self.supabase.table('articles').select("*").eq('url', url).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving article by URL: {str(e)}")
            return None
    
    def get_recent_articles(self, limit: int = 10, category: str = None) -> List[Dict[str, Any]]:
        """
        Get the most recently scraped articles.
        
        Args:
            limit: Number of articles to retrieve
            category: Optional category filter
            
        Returns:
            List of recent articles
        """
        try:
            query = self.supabase.table('articles').select("*")
            
            if category:
                query = query.eq('category', category)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving recent articles: {str(e)}")
            return []
    
    def get_articles_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get articles published on a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of articles from that date
        """
        try:
            # Query for articles where published_date starts with the date
            result = self.supabase.table('articles').select("*").like('published_date', f'{date_str}%').execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving articles by date: {str(e)}")
            return []
    
    def update_article_content(self, article_id: int, new_content: str) -> bool:
        """
        Update an existing article's content.
        
        Args:
            article_id: The article ID
            new_content: Updated content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.supabase.table('articles').update({
                'content': new_content,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', article_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated article ID: {article_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating article: {str(e)}")
            return False
    
    def delete_old_articles(self, days_old: int = 30) -> int:
        """
        Delete articles older than specified days.
        
        Args:
            days_old: Number of days threshold for deletion
            
        Returns:
            Number of articles deleted
        """
        try:
            from datetime import timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
            
            result = self.supabase.table('articles').delete().lt('created_at', cutoff_date).execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Deleted {deleted_count} old articles")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old articles: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            # Total articles
            total_result = self.supabase.table('articles').select("id", count='exact').execute()
            total_count = total_result.count if hasattr(total_result, 'count') else len(total_result.data or [])
            
            # Articles by category
            categories_result = self.supabase.table('articles').select("category", count='exact').execute()
            
            # Recent activity (last 7 days)
            from datetime import timedelta
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            recent_result = self.supabase.table('articles').select("id", count='exact').gte('created_at', week_ago).execute()
            recent_count = recent_result.count if hasattr(recent_result, 'count') else len(recent_result.data or [])
            
            return {
                'total_articles': total_count,
                'recent_articles_7_days': recent_count,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}


# Convenience function for backward compatibility
def save_article_to_supabase(article: Dict[str, Any]) -> bool:
    """
    Convenience function to save a single article.
    
    Args:
        article: Dictionary containing article data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        writer = DatabaseWriter()
        return writer.save_article_to_supabase(article)
    except Exception as e:
        logger.error(f"Error in convenience function: {str(e)}")
        return False


# Example usage and testing
if __name__ == "__main__":
    # Test the database writer
    sample_article = {
        'title': 'Test Article - ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'content': 'This is a test article content with enough words to pass validation. It contains multiple sentences and sufficient length to be considered a valid article for testing purposes.',
        'url': f'https://example.com/test-article-{int(datetime.now().timestamp())}',
        'source': 'CRHoy.com',
        'author': 'Test Author',
        'published_date': datetime.utcnow().isoformat(),
        'category': 'Technology',
        'tags': ['test', 'example'],
        'summary': 'This is a test summary for validation purposes.',
        'image_url': 'https://example.com/image.jpg'
    }
    
    try:
        # Initialize database writer
        db_writer = DatabaseWriter()
        
        # Test saving an article
        print("Testing single article save...")
        success = db_writer.save_article_to_supabase(sample_article)
        print(f"Article save result: {success}")
        
        # Test batch save
        print("\nTesting batch save...")
        batch_articles = [sample_article]  # In real use, this would be multiple articles
        batch_results = db_writer.save_articles_batch(batch_articles)
        print(f"Batch save results: {batch_results}")
        
        # Test retrieving recent articles
        print("\nTesting recent articles retrieval...")
        recent = db_writer.get_recent_articles(5)
        print(f"Retrieved {len(recent)} recent articles")
        
        # Test getting stats
        print("\nDatabase statistics:")
        stats = db_writer.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Error testing database writer: {str(e)}")
        print("Make sure SUPABASE_URL and SUPABASE_KEY environment variables are set")

        