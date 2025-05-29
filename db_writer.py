import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from supabase import create_client, Client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseWriter:
    def __init__(self):
        """Initialize the database writer with Supabase client."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    def generate_article_hash(self, article: Dict[str, Any]) -> str:
        """Generate a unique hash for an article based on its URL or content."""
        # Use URL as primary identifier, fallback to title + content
        identifier = article.get('url', '') or f"{article.get('title', '')}{article.get('content', '')[:100]}"
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def save_article_to_supabase(self, article: Dict[str, Any]) -> bool:
        """
        Save an article to Supabase database.
        
        Args:
            article: Dictionary containing article data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if article already exists using URL as unique identifier
            article_url = article.get('url', '')
            if article_url:
                existing = self.supabase.table('articles').select("id").eq('url', article_url).execute()
                
                # In newer Supabase versions, check data instead of error
                if existing.data and len(existing.data) > 0:
                    logger.info(f"Article already exists: {article.get('title', 'Unknown')}")
                    return True
            
            # Prepare article data for insertion (without hash column)
            article_data = {
                'title': article.get('title', ''),
                'content': article.get('content', ''),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'author': article.get('author', ''),
                'published_date': article.get('published_date'),
                'category': article.get('category', ''),
                'summary': article.get('summary', ''),
                'image_url': article.get('image_url', ''),
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Only include fields that have values (not None or empty string)
            article_data = {k: v for k, v in article_data.items() if v is not None and v != ''}
            
            # Insert the article
            result = self.supabase.table('articles').insert(article_data).execute()
            
            # Check if insertion was successful
            if result.data and len(result.data) > 0:
                logger.info(f"Successfully saved article: {article.get('title', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to save article: {article.get('title', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving article to database: {str(e)}")
            logger.error(f"Article data: {article.get('title', 'Unknown')}")
            return False
    
    def save_articles_batch(self, articles: list) -> Dict[str, int]:
        """
        Save multiple articles in batch.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dict with success and failure counts
        """
        results = {'success': 0, 'failed': 0, 'duplicates': 0}
        
        for article in articles:
            try:
                if self.save_article_to_supabase(article):
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f"Error in batch save: {str(e)}")
                results['failed'] += 1
        
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
    
    def get_recent_articles(self, limit: int = 10) -> list:
        """
        Get the most recently scraped articles.
        
        Args:
            limit: Number of articles to retrieve
            
        Returns:
            List of recent articles
        """
        try:
            result = self.supabase.table('articles').select("*").order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving recent articles: {str(e)}")
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
        'title': 'Test Article',
        'content': 'This is a test article content.',
        'url': 'https://example.com/test-article',
        'source': 'Test Source',
        'author': 'Test Author',
        'published_date': datetime.utcnow().isoformat(),
        'category': 'Technology',
        'tags': ['test', 'example'],
        'summary': 'This is a test summary.',
        'image_url': 'https://example.com/image.jpg'
    }
    
    # Initialize database writer
    try:
        db_writer = DatabaseWriter()
        
        # Test saving an article
        success = db_writer.save_article_to_supabase(sample_article)
        print(f"Article save result: {success}")
        
        # Test retrieving recent articles
        recent = db_writer.get_recent_articles(5)
        print(f"Retrieved {len(recent)} recent articles")
        
    except Exception as e:
        print(f"Error testing database writer: {str(e)}")