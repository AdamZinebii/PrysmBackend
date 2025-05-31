#!/usr/bin/env python3

from gnews_api_function import search_gnews
import json

def test_gnews_api():
    """Test the GNews API function with different parameter combinations."""
    
    print("=" * 60)
    print("Testing GNews API Function")
    print("=" * 60)
    
    # Test 1: Basic search
    print("\n1. Basic search test:")
    print("   Query: 'artificial intelligence'")
    result1 = search_gnews("artificial intelligence")
    print(f"   Status: {result1.get('status', 'success' if 'articles' in result1 else 'unknown')}")
    if 'error' in result1:
        print(f"   Error: {result1['error']}")
    elif 'totalArticles' in result1:
        print(f"   Total articles found: {result1['totalArticles']}")
        print(f"   Articles returned: {len(result1.get('articles', []))}")
    
    # Test 2: Search with specific country and language
    print("\n2. Country/language specific search:")
    print("   Query: 'technology', Country: 'gb', Language: 'en', Max: 5")
    result2 = search_gnews("technology", gl="gb", hl="en", max_articles=5)
    print(f"   Status: {result2.get('status', 'success' if 'articles' in result2 else 'unknown')}")
    if 'error' in result2:
        print(f"   Error: {result2['error']}")
    elif 'totalArticles' in result2:
        print(f"   Total articles found: {result2['totalArticles']}")
        print(f"   Articles returned: {len(result2.get('articles', []))}")
    
    # Test 3: Search with time period
    print("\n3. Time period search:")
    print("   Query: 'climate change', Time period: '7d', Max: 3")
    result3 = search_gnews("climate change", time_period="7d", max_articles=3)
    print(f"   Status: {result3.get('status', 'success' if 'articles' in result3 else 'unknown')}")
    if 'error' in result3:
        print(f"   Error: {result3['error']}")
    elif 'totalArticles' in result3:
        print(f"   Total articles found: {result3['totalArticles']}")
        print(f"   Articles returned: {len(result3.get('articles', []))}")
    
    # Test 4: Search with all parameters
    print("\n4. Full parameter search:")
    print("   Query: 'renewable energy', Country: 'de', Language: 'de', Max: 2, Period: '1m'")
    result4 = search_gnews("renewable energy", gl="de", hl="de", max_articles=2, time_period="1m")
    print(f"   Status: {result4.get('status', 'success' if 'articles' in result4 else 'unknown')}")
    if 'error' in result4:
        print(f"   Error: {result4['error']}")
    elif 'totalArticles' in result4:
        print(f"   Total articles found: {result4['totalArticles']}")
        print(f"   Articles returned: {len(result4.get('articles', []))}")
    
    # Display sample article if any successful response
    sample_result = None
    for result in [result1, result2, result3, result4]:
        if 'articles' in result and result['articles']:
            sample_result = result
            break
    
    if sample_result and sample_result['articles']:
        print("\n" + "=" * 60)
        print("Sample Article Data:")
        print("=" * 60)
        article = sample_result['articles'][0]
        print(f"Title: {article.get('title', 'N/A')}")
        print(f"Description: {article.get('description', 'N/A')[:100]}...")
        print(f"URL: {article.get('url', 'N/A')}")
        print(f"Published: {article.get('publishedAt', 'N/A')}")
        print(f"Source: {article.get('source', {}).get('name', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    # Note about API key
    if any('error' in result for result in [result1, result2, result3, result4]):
        print("\nNOTE: If you're seeing errors, make sure to:")
        print("1. Replace 'YOUR_API_KEY' in gnews_api_function.py with a valid GNews API key")
        print("2. Get your API key from: https://gnews.io")
        print("3. Check your internet connection")

if __name__ == "__main__":
    test_gnews_api() 