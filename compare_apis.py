#!/usr/bin/env python3

from gnews_api_function import search_gnews
import json

def compare_api_outputs():
    """Compare SerpAPI and GNews API response formats."""
    
    print("=" * 80)
    print("API OUTPUT COMPARISON: SerpAPI vs GNews")
    print("=" * 80)
    
    # Test our GNews function
    print("\n🔍 Testing GNews API...")
    gnews_result = search_gnews("artificial intelligence", max_articles=2)
    
    print("\n" + "="*50)
    print("1. GNEWS API OUTPUT STRUCTURE")
    print("="*50)
    
    if 'articles' in gnews_result:
        print(f"✅ Status: Success")
        print(f"📊 Total Articles: {gnews_result.get('totalArticles', 'N/A')}")
        print(f"📋 Articles Returned: {len(gnews_result['articles'])}")
        
        print(f"\n📄 Sample GNews Article Structure:")
        print("-" * 40)
        sample_article = gnews_result['articles'][0]
        for key, value in sample_article.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"{key}: {value[:100]}...")
            else:
                print(f"{key}: {value}")
                
        print(f"\n🔧 GNews Raw Response Keys:")
        print(f"- Root keys: {list(gnews_result.keys())}")
        print(f"- Article keys: {list(sample_article.keys())}")
        
    else:
        print(f"❌ GNews Error: {gnews_result.get('error', 'Unknown error')}")
    
    print("\n" + "="*50)
    print("2. SERPAPI OUTPUT STRUCTURE (From your main.py)")
    print("="*50)
    
    # Show SerpAPI structure based on your code
    serpapi_structure = {
        "success": True,
        "totalArticles": 15,
        "articles": [
            {
                "title": "AI News Article Title",
                "description": "",  # Often empty in SerpAPI
                "content": "",      # Often empty in SerpAPI  
                "url": "https://example.com/article",
                "image": "https://example.com/thumbnail.jpg",
                "publishedAt": "2024-01-15T10:30:00Z",
                "source": {
                    "name": "Tech Source",
                    "url": "https://example.com"  # Often icon URL
                }
            }
        ],
        "serpapi_data": {
            "related_topics": [],
            "menu_links": [],
            "topic_token": None
        }
    }
    
    print("📄 SerpAPI Structure (from your main.py):")
    print("-" * 40)
    print(json.dumps(serpapi_structure, indent=2))
    
    print("\n" + "="*50)
    print("3. KEY DIFFERENCES")
    print("="*50)
    
    differences = {
        "Data Source": {
            "SerpAPI": "Google News (scraped)",
            "GNews": "Direct Google News RSS Feed"
        },
        "Response Format": {
            "SerpAPI": "Custom wrapper with serpapi_data",
            "GNews": "Direct news data structure"
        },
        "Article Content": {
            "SerpAPI": "Usually empty description/content",
            "GNews": "Provides description and partial content"
        },
        "Success Indicator": {
            "SerpAPI": "success: true/false",
            "GNews": "Based on presence of 'articles' key"
        },
        "Additional Data": {
            "SerpAPI": "related_topics, menu_links, topic_token",
            "GNews": "Direct article focus"
        },
        "Source Info": {
            "SerpAPI": "source.url often contains icon URL",
            "GNews": "source.url contains actual website URL"
        },
        "Rate Limiting": {
            "SerpAPI": "Based on plan (100-100k/month)",
            "GNews": "Based on plan (100-100k/month)"
        },
        "Cost Structure": {
            "SerpAPI": "$50-$250/month for news searches",
            "GNews": "$9-$100/month"
        }
    }
    
    for category, details in differences.items():
        print(f"\n🔸 {category}:")
        for api, description in details.items():
            print(f"  {api}: {description}")
    
    print("\n" + "="*50)
    print("4. FORMATTED OUTPUT (Prysm Format)")
    print("="*50)
    
    if 'articles' in gnews_result and gnews_result['articles']:
        # Show how it would be formatted for Prysm (based on your format_gnews_articles_for_prysm function)
        formatted_article = {
            'title': gnews_result['articles'][0].get('title', '').strip(),
            'link': gnews_result['articles'][0].get('url', '#').strip(),
            'source': gnews_result['articles'][0].get('source', {}).get('name', 'Unknown Source'),
            'published': gnews_result['articles'][0].get('publishedAt', ''),
            'snippet': gnews_result['articles'][0].get('description', '').strip(),
            'thumbnail': gnews_result['articles'][0].get('image', ''),
            'content': gnews_result['articles'][0].get('content', '').strip()
        }
        
        print("📋 GNews → Prysm Format:")
        print("-" * 30)
        for key, value in formatted_article.items():
            if isinstance(value, str) and len(value) > 80:
                print(f"{key}: {value[:80]}...")
            else:
                print(f"{key}: {value}")
    
    print("\n" + "="*50)
    print("5. RECOMMENDATIONS")
    print("="*50)
    
    recommendations = [
        "✅ GNews API provides richer article content (description + partial content)",
        "✅ GNews API is more cost-effective ($9-100 vs $50-250)",
        "✅ GNews API has simpler response structure",
        "⚠️  SerpAPI provides additional context (related_topics, menu_links)",
        "⚠️  SerpAPI might have better rate limiting for high-volume apps",
        "💡 Consider using GNews for content-rich feeds",
        "💡 Consider SerpAPI for discovery/browsing features"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print("\n" + "="*80)
    print("COMPARISON COMPLETE")
    print("="*80)

if __name__ == "__main__":
    compare_api_outputs() 