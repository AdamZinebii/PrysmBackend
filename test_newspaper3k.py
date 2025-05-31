#!/usr/bin/env python3

def test_newspaper3k():
    """Test newspaper3k extraction with a sample URL."""
    print("Testing newspaper3k extraction...")
    
    try:
        from newspaper import Article
        
        # Test URL
        url = "https://www.techspot.com/news/108118-nvidia-jensen-huang-applauds-us-trade-moves-warns.html"
        
        print(f"Testing URL: {url}")
        
        # Create article object
        article = Article(url)
        article.config.request_timeout = 10
        article.config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        # Download and parse
        print("Downloading article...")
        article.download()
        
        print("Parsing article...")
        article.parse()
        
        print(f"✅ Title: {article.title}")
        print(f"✅ Summary length: {len(article.summary) if article.summary else 0}")
        print(f"✅ Text length: {len(article.text) if article.text else 0}")
        
        if article.summary:
            print(f"✅ Summary: {article.summary[:100]}...")
        elif article.text:
            print(f"✅ Text excerpt: {article.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_newspaper3k() 