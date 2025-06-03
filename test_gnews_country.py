#!/usr/bin/env python3
"""
Test GNews API querying with and without country specification
"""
import sys
import os
import json
from datetime import datetime

# Add main to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.news.serpapi import gnews_search, gnews_top_headlines, format_gnews_articles_for_prysm

def test_gnews_search_with_country():
    """Test GNews search WITH country specified (US)"""
    print("🇺🇸 TEST GNEWS SEARCH WITH COUNTRY (US)")
    print("=" * 50)
    
    query = "artificial intelligence"
    lang = "en"
    country = "us"
    max_articles = 5
    
    print(f"🔍 Query: {query}")
    print(f"🌍 Country: {country}")
    print(f"🔤 Language: {lang}")
    print(f"📰 Max articles: {max_articles}")
    print()
    
    try:
        result = gnews_search(
            query=query,
            lang=lang,
            country=country,
            max_articles=max_articles
        )
        
        print("📊 RÉSULTATS:")
        print(f"✅ Success: {result.get('success')}")
        print(f"📈 Total articles: {result.get('totalArticles', 0)}")
        
        if result.get('success') and result.get('articles'):
            print(f"📋 Articles returned: {len(result['articles'])}")
            
            # Show first few articles
            for i, article in enumerate(result['articles'][:3]):
                print(f"\n📰 Article {i+1}:")
                print(f"   Title: {article.get('title', 'N/A')[:80]}...")
                print(f"   Source: {article.get('source', {}).get('name', 'N/A')}")
                print(f"   Published: {article.get('published_date', 'N/A')}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return {"success": False, "error": str(e)}

def test_gnews_search_without_country():
    """Test GNews search WITHOUT country specified"""
    print("\n🌍 TEST GNEWS SEARCH WITHOUT COUNTRY")
    print("=" * 50)
    
    query = "artificial intelligence"
    lang = "en"
    max_articles = 5
    
    print(f"🔍 Query: {query}")
    print(f"🌍 Country: None (global)")
    print(f"🔤 Language: {lang}")
    print(f"📰 Max articles: {max_articles}")
    print()
    
    try:
        result = gnews_search(
            query=query,
            lang=lang,
            max_articles=max_articles
        )
        
        print("📊 RÉSULTATS:")
        print(f"✅ Success: {result.get('success')}")
        print(f"📈 Total articles: {result.get('totalArticles', 0)}")
        
        if result.get('success') and result.get('articles'):
            print(f"📋 Articles returned: {len(result['articles'])}")
            
            # Show first few articles
            for i, article in enumerate(result['articles'][:3]):
                print(f"\n📰 Article {i+1}:")
                print(f"   Title: {article.get('title', 'N/A')[:80]}...")
                print(f"   Source: {article.get('source', {}).get('name', 'N/A')}")
                print(f"   Published: {article.get('published_date', 'N/A')}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return {"success": False, "error": str(e)}

def test_gnews_headlines_with_country():
    """Test GNews top headlines WITH country specified (US)"""
    print("\n🇺🇸 TEST GNEWS TOP HEADLINES WITH COUNTRY (US)")
    print("=" * 50)
    
    category = "technology"
    lang = "en"
    country = "us"
    max_articles = 5
    
    print(f"📂 Category: {category}")
    print(f"🌍 Country: {country}")
    print(f"🔤 Language: {lang}")
    print(f"📰 Max articles: {max_articles}")
    print()
    
    try:
        result = gnews_top_headlines(
            category=category,
            lang=lang,
            country=country,
            max_articles=max_articles
        )
        
        print("📊 RÉSULTATS:")
        print(f"✅ Success: {result.get('success')}")
        print(f"📈 Total articles: {result.get('totalArticles', 0)}")
        
        if result.get('success') and result.get('articles'):
            print(f"📋 Articles returned: {len(result['articles'])}")
            
            # Show first few articles
            for i, article in enumerate(result['articles'][:3]):
                print(f"\n📰 Article {i+1}:")
                print(f"   Title: {article.get('title', 'N/A')[:80]}...")
                print(f"   Source: {article.get('source', {}).get('name', 'N/A')}")
                print(f"   Published: {article.get('published_date', 'N/A')}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return {"success": False, "error": str(e)}

def test_gnews_headlines_without_country():
    """Test GNews top headlines WITHOUT country specified"""
    print("\n🌍 TEST GNEWS TOP HEADLINES WITHOUT COUNTRY")
    print("=" * 50)
    
    category = "technology"
    lang = "en"
    max_articles = 5
    
    print(f"📂 Category: {category}")
    print(f"🌍 Country: None (global)")
    print(f"🔤 Language: {lang}")
    print(f"📰 Max articles: {max_articles}")
    print()
    
    try:
        result = gnews_top_headlines(
            category=category,
            lang=lang,
            country=None,  # No country specified
            max_articles=max_articles
        )
        
        print("📊 RÉSULTATS:")
        print(f"✅ Success: {result.get('success')}")
        print(f"📈 Total articles: {result.get('totalArticles', 0)}")
        
        if result.get('success') and result.get('articles'):
            print(f"📋 Articles returned: {len(result['articles'])}")
            
            # Show first few articles
            for i, article in enumerate(result['articles'][:3]):
                print(f"\n📰 Article {i+1}:")
                print(f"   Title: {article.get('title', 'N/A')[:80]}...")
                print(f"   Source: {article.get('source', {}).get('name', 'N/A')}")
                print(f"   Published: {article.get('published_date', 'N/A')}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return {"success": False, "error": str(e)}

def compare_results(with_country, without_country, test_type):
    """Compare results from with/without country tests"""
    print(f"\n📊 COMPARISON: {test_type}")
    print("=" * 40)
    
    print(f"🇺🇸 WITH Country (US):")
    print(f"   Success: {with_country.get('success')}")
    print(f"   Total articles: {with_country.get('totalArticles', 0)}")
    print(f"   Returned: {len(with_country.get('articles', []))}")
    
    print(f"🌍 WITHOUT Country:")
    print(f"   Success: {without_country.get('success')}")
    print(f"   Total articles: {without_country.get('totalArticles', 0)}")
    print(f"   Returned: {len(without_country.get('articles', []))}")
    
    # Check for differences in sources
    if (with_country.get('success') and without_country.get('success') and 
        with_country.get('articles') and without_country.get('articles')):
        
        us_sources = set()
        global_sources = set()
        
        for article in with_country['articles']:
            source_name = article.get('source', {}).get('name', 'Unknown')
            us_sources.add(source_name)
            
        for article in without_country['articles']:
            source_name = article.get('source', {}).get('name', 'Unknown')
            global_sources.add(source_name)
        
        print(f"\n📰 Source Diversity:")
        print(f"   US sources: {len(us_sources)} unique")
        print(f"   Global sources: {len(global_sources)} unique")
        print(f"   Overlap: {len(us_sources.intersection(global_sources))} sources")

def main():
    """Run all GNews country tests"""
    print("🧪 GNEWS COUNTRY SPECIFICATION TEST SUITE")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().isoformat()}")
    print()
    
    # Test 1: Search with country
    search_with_country = test_gnews_search_with_country()
    
    # Test 2: Search without country  
    search_without_country = test_gnews_search_without_country()
    
    # Test 3: Headlines with country
    headlines_with_country = test_gnews_headlines_with_country()
    
    # Test 4: Headlines without country
    headlines_without_country = test_gnews_headlines_without_country()
    
    # Compare results
    compare_results(search_with_country, search_without_country, "SEARCH")
    compare_results(headlines_with_country, headlines_without_country, "TOP HEADLINES")
    
    print(f"\n🏁 FINAL SUMMARY")
    print("=" * 30)
    print(f"Search with US: {'✅' if search_with_country.get('success') else '❌'}")
    print(f"Search global: {'✅' if search_without_country.get('success') else '❌'}")
    print(f"Headlines with US: {'✅' if headlines_with_country.get('success') else '❌'}")
    print(f"Headlines global: {'✅' if headlines_without_country.get('success') else '❌'}")

if __name__ == "__main__":
    main() 