import logging
import nltk
import time
from typing import Dict, Optional, List
from urllib.parse import urlparse
from newspaper import Article
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentExtractor:
    """
    A robust content extractor using newspaper3k for extracting article content from URLs.
    """
    
    def __init__(self):
        """Initialize the content extractor with proper configuration."""
        self.session = self._create_robust_session()
        self._download_nltk_data()
    
    def _create_robust_session(self) -> requests.Session:
        """Create a requests session with retry strategy and timeout."""
        session = requests.Session()
        
        # Define retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set user agent to avoid blocking
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return session
    
    def _download_nltk_data(self):
        """Download required NLTK data for NLP processing."""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            nltk.download('stopwords', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
    
    def _validate_url(self, url: str) -> bool:
        """Validate if the URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def fetch_content(self, url: str, language: str = 'en') -> Dict[str, Optional[str]]:
        """
        Extract article content from a given URL.
        
        Args:
            url (str): The article URL to extract content from
            language (str): Language code for the article (default: 'en')
            
        Returns:
            Dict containing extracted content with keys:
            - title: Article title
            - text: Full article text
            - summary: AI-generated summary (if NLP is successful)
            - authors: List of authors
            - publish_date: Publication date
            - top_image: Featured image URL
            - keywords: Extracted keywords
            - url: Original URL
            - success: Boolean indicating extraction success
            - error: Error message if extraction failed
        """
        
        # Initialize result structure
        result = {
            'title': None,
            'text': None,
            'summary': None,
            'authors': [],
            'publish_date': None,
            'top_image': None,
            'keywords': [],
            'url': url,
            'success': False,
            'error': None
        }
        
        try:
            # Validate URL
            if not self._validate_url(url):
                result['error'] = 'Invalid URL format'
                return result
            
            logger.info(f"Extracting content from: {url}")
            
            # Create Article object with language specification
            article = Article(url, language=language)
            
            # Download the article with custom session
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Pass the HTML content to newspaper3k
                article.download(input_html=response.text)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download article: {e}")
                # Fallback to newspaper3k's built-in download
                article.download()
            
            # Parse the article
            article.parse()
            
            # Extract basic content
            result['title'] = article.title
            result['text'] = article.text
            result['authors'] = article.authors
            result['publish_date'] = article.publish_date.isoformat() if article.publish_date else None
            result['top_image'] = article.top_image
            
            # Perform NLP analysis (optional - can be expensive)
            try:
                article.nlp()
                result['summary'] = article.summary
                result['keywords'] = article.keywords
            except Exception as nlp_error:
                logger.warning(f"NLP processing failed: {nlp_error}")
                # NLP failure doesn't mean the extraction failed
            
            # Check if we got meaningful content
            if result['title'] and result['text'] and len(result['text']) > 100:
                result['success'] = True
                logger.info(f"Successfully extracted {len(result['text'])} characters from {url}")
            else:
                result['error'] = 'Insufficient content extracted'
                logger.warning(f"Insufficient content extracted from {url}")
                
        except Exception as e:
            result['error'] = f'Content extraction failed: {str(e)}'
            logger.error(f"Content extraction failed for {url}: {e}")
        
        return result
    
    def fetch_multiple_contents(self, urls: List[str], language: str = 'en', delay: float = 1.0) -> List[Dict]:
        """
        Extract content from multiple URLs with rate limiting.
        
        Args:
            urls (List[str]): List of URLs to extract content from
            language (str): Language code for articles
            delay (float): Delay between requests in seconds
            
        Returns:
            List of extraction results
        """
        results = []
        
        for i, url in enumerate(urls):
            logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
            
            result = self.fetch_content(url, language)
            results.append(result)
            
            # Rate limiting - be respectful to websites
            if i < len(urls) - 1:  # Don't sleep after the last URL
                time.sleep(delay)
        
        return results


# Convenience function for Firebase Cloud Functions
def fetch_content(url: str, language: str = 'en') -> Dict[str, Optional[str]]:
    """
    Convenience function to extract content from a single URL.
    
    Args:
        url (str): The article URL to extract content from
        language (str): Language code for the article (default: 'en')
        
    Returns:
        Dict containing extracted content
    """
    extractor = ContentExtractor()
    return extractor.fetch_content(url, language)


# Example usage
if __name__ == "__main__":
    # Test the content extractor
    test_urls = [
        "https://www.reuters.com/world/middle-east/dubai-real-estate-prices-likely-face-double-digit-fall-after-years-boom-fitch-2025-05-29/",
        "https://www.tcpalm.com/story/marketplace/real-estate/2025/05/30/florida-real-estate-condo-townhome-listings-surge-on-treasure-coast-condominium-analysis-market/83624424007/",
        "https://www.realestatenews.com/2025/03/13/the-housing-market-is-improving-but-buyers-are-anxious",
        "https://www.newsweek.com/recession-housing-market-mortgage-rates-price-trump-tariffs-2043195",

    ]
    
    extractor = ContentExtractor()
    
    # Test single URL
    result = extractor.fetch_content("https://www.bbc.com/news")
    print("Single URL Result:", result['success'])
    
    # Test multiple URLs
    results = extractor.fetch_multiple_contents(test_urls)
    print(f"Processed {len(results)} URLs")
    for i, result in enumerate(results):
        print(f"URL {i+1}: {'Success' if result['success'] else 'Failed'}") 
        print(result['summary'])