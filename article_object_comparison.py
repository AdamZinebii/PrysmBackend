#!/usr/bin/env python3

from gnews_api_function import search_gnews
import json

def compare_article_objects():
    """Compare the exact article object structure between SerpAPI and GNews."""
    
    print("=" * 80)
    print("ARTICLE OBJECT COMPARISON: SerpAPI vs GNews")
    print("=" * 80)
    
    # Get a real GNews article
    print("\n🔍 Fetching real GNews article...")
    gnews_result = search_gnews("technology", max_articles=1)
    
    if 'articles' in gnews_result and gnews_result['articles']:
        gnews_article = gnews_result['articles'][0]
        print("✅ GNews article fetched successfully")
    else:
        print("❌ Failed to fetch GNews article")
        return
    
    # Create a SerpAPI article object based on your _parse_serpapi_story function
    serpapi_article_raw = {
        "title": "Sample AI Technology News Article",
        "link": "https://example.com/ai-tech-news",
        "source": {
            "name": "TechCrunch",
            "icon": "https://encrypted-tbn0.gstatic.com/images?q=tbn:techcrunch-icon"
        },
        "date": "2024-01-15, 3 hours ago",
        "thumbnail": "https://example.com/thumbnail.jpg"
    }
    
    # Parse it using your SerpAPI parsing logic
    serpapi_article = {
        "title": serpapi_article_raw.get("title", ""),
        "description": "",  # SerpAPI doesn't always provide description
        "content": "",      # SerpAPI doesn't provide full content
        "url": serpapi_article_raw.get("link", ""),
        "image": serpapi_article_raw.get("thumbnail", ""),
        "publishedAt": serpapi_article_raw.get("date", ""),
        "source": {
            "name": serpapi_article_raw.get("source", {}).get("name", "Unknown"),
            "url": serpapi_article_raw.get("source", {}).get("icon", "")  # Using icon URL as source URL
        }
    }
    
    print("\n" + "="*50)
    print("GNEWS ARTICLE OBJECT")
    print("="*50)
    print("🔍 Structure and Content:")
    print("-" * 30)
    
    for key, value in gnews_article.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, str) and len(sub_value) > 70:
                    print(f"  {sub_key}: {sub_value[:70]}...")
                else:
                    print(f"  {sub_key}: {sub_value}")
        elif isinstance(value, str) and len(value) > 70:
            print(f"{key}: {value[:70]}...")
        else:
            print(f"{key}: {value}")
    
    print("\n" + "="*50)
    print("SERPAPI ARTICLE OBJECT")
    print("="*50)
    print("🔍 Structure and Content:")
    print("-" * 30)
    
    for key, value in serpapi_article.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")
    
    print("\n" + "="*50)
    print("FIELD-BY-FIELD COMPARISON")
    print("="*50)
    
    # Get all unique keys
    all_keys = set(gnews_article.keys()) | set(serpapi_article.keys())
    
    for key in sorted(all_keys):
        print(f"\n🔸 Field: '{key}'")
        print("-" * 25)
        
        gnews_value = gnews_article.get(key, "❌ NOT PRESENT")
        serpapi_value = serpapi_article.get(key, "❌ NOT PRESENT")
        
        if key == "source":
            # Special handling for source object
            print("  GNews:")
            if isinstance(gnews_value, dict):
                for sub_key, sub_val in gnews_value.items():
                    print(f"    {sub_key}: {sub_val}")
            else:
                print(f"    {gnews_value}")
                
            print("  SerpAPI:")
            if isinstance(serpapi_value, dict):
                for sub_key, sub_val in serpapi_value.items():
                    print(f"    {sub_key}: {sub_val}")
            else:
                print(f"    {serpapi_value}")
        else:
            # Regular field comparison
            if isinstance(gnews_value, str) and len(gnews_value) > 100:
                print(f"  GNews: {gnews_value[:100]}...")
            else:
                print(f"  GNews: {gnews_value}")
                
            if isinstance(serpapi_value, str) and len(serpapi_value) > 100:
                print(f"  SerpAPI: {serpapi_value[:100]}...")
            else:
                print(f"  SerpAPI: {serpapi_value}")
    
    print("\n" + "="*50)
    print("KEY DIFFERENCES SUMMARY")
    print("="*50)
    
    differences = [
        {
            "field": "title",
            "gnews": "✅ Full title provided",
            "serpapi": "✅ Full title provided",
            "winner": "🤝 Equal"
        },
        {
            "field": "description", 
            "gnews": "✅ Rich description (100-200 chars)",
            "serpapi": "❌ Usually empty string",
            "winner": "🥇 GNews"
        },
        {
            "field": "content",
            "gnews": "✅ Partial article content (500+ chars)",
            "serpapi": "❌ Always empty string", 
            "winner": "🥇 GNews"
        },
        {
            "field": "url",
            "gnews": "✅ Direct article URL",
            "serpapi": "✅ Direct article URL",
            "winner": "🤝 Equal"
        },
        {
            "field": "image",
            "gnews": "✅ High-quality article image URL",
            "serpapi": "✅ Thumbnail URL (may be lower quality)",
            "winner": "🥇 GNews"
        },
        {
            "field": "publishedAt",
            "gnews": "✅ ISO 8601 format (2024-01-15T10:30:00Z)",
            "serpapi": "⚠️ Relative format (3 hours ago)",
            "winner": "🥇 GNews"
        },
        {
            "field": "source.name",
            "gnews": "✅ Clean source name",
            "serpapi": "✅ Clean source name",
            "winner": "🤝 Equal"
        },
        {
            "field": "source.url",
            "gnews": "✅ Actual website URL",
            "serpapi": "⚠️ Often icon/image URL, not website",
            "winner": "🥇 GNews"
        }
    ]
    
    for diff in differences:
        print(f"\n📋 {diff['field']}:")
        print(f"  GNews:   {diff['gnews']}")
        print(f"  SerpAPI: {diff['serpapi']}")
        print(f"  Result:  {diff['winner']}")
    
    print("\n" + "="*50)
    print("JSON STRUCTURE COMPARISON")
    print("="*50)
    
    print("\n🔍 GNews Article Schema:")
    print("-" * 25)
    gnews_schema = {
        "title": "string (full title)",
        "description": "string (rich description)",
        "content": "string (partial content)",
        "url": "string (article URL)",
        "image": "string (image URL)", 
        "publishedAt": "string (ISO 8601)",
        "source": {
            "name": "string (source name)",
            "url": "string (website URL)"
        }
    }
    print(json.dumps(gnews_schema, indent=2))
    
    print("\n🔍 SerpAPI Article Schema:")
    print("-" * 25)
    serpapi_schema = {
        "title": "string (full title)",
        "description": "string (usually empty)",
        "content": "string (always empty)",
        "url": "string (article URL)",
        "image": "string (thumbnail URL)",
        "publishedAt": "string (relative format)",
        "source": {
            "name": "string (source name)",
            "url": "string (often icon URL)"
        }
    }
    print(json.dumps(serpapi_schema, indent=2))
    
    print("\n" + "="*50)
    print("CONTENT RICHNESS COMPARISON")
    print("="*50)
    
    # Calculate content richness
    gnews_content_score = 0
    serpapi_content_score = 0
    
    # Title (both have)
    gnews_content_score += 1
    serpapi_content_score += 1
    
    # Description 
    if gnews_article.get('description', '').strip():
        gnews_content_score += 2
    if serpapi_article.get('description', '').strip():
        serpapi_content_score += 2
    
    # Content
    if gnews_article.get('content', '').strip():
        gnews_content_score += 3
    if serpapi_article.get('content', '').strip():
        serpapi_content_score += 3
    
    # Image quality (assume GNews is better)
    if gnews_article.get('image', '').strip():
        gnews_content_score += 1
    if serpapi_article.get('image', '').strip():
        serpapi_content_score += 0.5  # Lower quality assumption
    
    # Date format standardization
    if 'T' in gnews_article.get('publishedAt', ''):  # ISO format
        gnews_content_score += 1
    if 'ago' in serpapi_article.get('publishedAt', ''):  # Relative format
        serpapi_content_score += 0.5
    
    print(f"📊 Content Richness Score:")
    print(f"  GNews:   {gnews_content_score}/8.0 ({gnews_content_score/8*100:.1f}%)")
    print(f"  SerpAPI: {serpapi_content_score}/8.0 ({serpapi_content_score/8*100:.1f}%)")
    
    if gnews_content_score > serpapi_content_score:
        print(f"  🏆 Winner: GNews (richer content)")
    elif serpapi_content_score > gnews_content_score:
        print(f"  🏆 Winner: SerpAPI (richer content)")
    else:
        print(f"  🤝 Tie: Equal content richness")
    
    print("\n" + "="*80)
    print("COMPARISON COMPLETE")
    print("="*80)

if __name__ == "__main__":
    compare_article_objects() 