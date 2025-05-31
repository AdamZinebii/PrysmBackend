#!/usr/bin/env python3

import json
from unittest.mock import patch, Mock
from gnews_api_function import search_gnews

# Mock response data that simulates a real GNews API response
MOCK_RESPONSE = {
    "totalArticles": 54904,
    "articles": [
        {
            "title": "AI Revolution: How Artificial Intelligence is Transforming Industries",
            "description": "Artificial intelligence is rapidly changing the way businesses operate across various sectors...",
            "content": "The artificial intelligence revolution is reshaping industries at an unprecedented pace...",
            "url": "https://example.com/ai-revolution-article",
            "image": "https://example.com/images/ai-revolution.jpg",
            "publishedAt": "2024-01-15T10:30:00Z",
            "source": {
                "name": "Tech News Today",
                "url": "https://example.com"
            }
        },
        {
            "title": "Machine Learning Breakthrough in Healthcare",
            "description": "Researchers develop new ML algorithms that can detect diseases earlier than traditional methods...",
            "content": "A groundbreaking study published today reveals how machine learning algorithms...",
            "url": "https://example.com/ml-healthcare-breakthrough",
            "image": "https://example.com/images/ml-healthcare.jpg",
            "publishedAt": "2024-01-15T08:15:00Z",
            "source": {
                "name": "Medical AI Journal",
                "url": "https://example.com"
            }
        }
    ]
}

def mock_urlopen(url):
    """Mock urllib.request.urlopen to return our mock response"""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(MOCK_RESPONSE).encode('utf-8')
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=None)
    return mock_response

def test_gnews_api_with_mock():
    """Test the GNews API function with mocked successful responses."""
    
    print("=" * 60)
    print("Testing GNews API Function (MOCKED RESPONSES)")
    print("=" * 60)
    
    # Patch urllib.request.urlopen to return our mock response
    with patch('urllib.request.urlopen', side_effect=mock_urlopen):
        
        # Test 1: Basic search
        print("\n1. Basic search test:")
        print("   Query: 'artificial intelligence'")
        result1 = search_gnews("artificial intelligence")
        print(f"   Status: success")
        print(f"   Total articles found: {result1['totalArticles']}")
        print(f"   Articles returned: {len(result1['articles'])}")
        
        # Test 2: Search with specific country and language
        print("\n2. Country/language specific search:")
        print("   Query: 'technology', Country: 'gb', Language: 'en', Max: 5")
        result2 = search_gnews("technology", gl="gb", hl="en", max_articles=5)
        print(f"   Status: success")
        print(f"   Total articles found: {result2['totalArticles']}")
        print(f"   Articles returned: {len(result2['articles'])}")
        
        # Test 3: Search with time period
        print("\n3. Time period search:")
        print("   Query: 'climate change', Time period: '7d', Max: 3")
        result3 = search_gnews("climate change", time_period="7d", max_articles=3)
        print(f"   Status: success")
        print(f"   Total articles found: {result3['totalArticles']}")
        print(f"   Articles returned: {len(result3['articles'])}")
        
        # Test 4: Search with all parameters
        print("\n4. Full parameter search:")
        print("   Query: 'renewable energy', Country: 'de', Language: 'de', Max: 2, Period: '1m'")
        result4 = search_gnews("renewable energy", gl="de", hl="de", max_articles=2, time_period="1m")
        print(f"   Status: success")
        print(f"   Total articles found: {result4['totalArticles']}")
        print(f"   Articles returned: {len(result4['articles'])}")
        
        # Display sample articles
        print("\n" + "=" * 60)
        print("Sample Articles Data:")
        print("=" * 60)
        
        for i, article in enumerate(result1['articles'], 1):
            print(f"\nArticle {i}:")
            print(f"  Title: {article['title']}")
            print(f"  Description: {article['description'][:80]}...")
            print(f"  URL: {article['url']}")
            print(f"  Published: {article['publishedAt']}")
            print(f"  Source: {article['source']['name']}")
    
    print("\n" + "=" * 60)
    print("Mock test completed successfully!")
    print("=" * 60)
    print("\nThis demonstrates what the function returns with a valid API key.")
    print("The actual GNews API would return similar structured data.")

if __name__ == "__main__":
    test_gnews_api_with_mock() 