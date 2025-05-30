#!/usr/bin/env python3
"""
Test script for the new trending subtopics functionality.
This script tests the extract_trending_subtopics function locally.
"""

import sys
import os
import json

# Add the current directory to Python path to import main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the function from main.py
try:
    from main import extract_trending_subtopics, get_openai_client, get_gnews_key
    print("✅ Successfully imported functions from main.py")
except ImportError as e:
    print(f"❌ Failed to import functions: {e}")
    sys.exit(1)

def test_trending_subtopics():
    """Test the extract_trending_subtopics function with different topics."""
    
    print("\n🔥 Testing Trending Subtopics Extraction")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "topic": "technology",
            "lang": "en",
            "country": "us",
            "max_articles": 5
        },
        {
            "topic": "sports", 
            "lang": "en",
            "country": "us",
            "max_articles": 3
        },
        {
            "topic": "business",
            "lang": "en", 
            "country": "us",
            "max_articles": 5
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['topic'].upper()}")
        print("-" * 30)
        
        try:
            result = extract_trending_subtopics(
                topic=test_case["topic"],
                lang=test_case["lang"],
                country=test_case["country"],
                max_articles=test_case["max_articles"]
            )
            
            if result.get("success"):
                print(f"✅ Success!")
                print(f"📊 Articles analyzed: {result.get('articles_analyzed', 0)}")
                print(f"🔥 Trending subtopics ({len(result.get('subtopics', []))}):")
                
                for j, subtopic in enumerate(result.get('subtopics', []), 1):
                    print(f"   {j}. {subtopic}")
                
                if 'usage' in result:
                    usage = result['usage']
                    print(f"💰 Token usage: {usage.get('total_tokens', 0)} tokens")
                    
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Testing completed!")

def check_dependencies():
    """Check if required dependencies are available."""
    
    print("🔍 Checking Dependencies")
    print("=" * 30)
    
    # Check OpenAI client
    try:
        client = get_openai_client()
        if client:
            print("✅ OpenAI client: Available")
        else:
            print("❌ OpenAI client: Not available")
            return False
    except Exception as e:
        print(f"❌ OpenAI client error: {e}")
        return False
    
    # Check GNews API key
    try:
        gnews_key = get_gnews_key()
        if gnews_key and gnews_key != "your-gnews-api-key-here":
            print("✅ GNews API key: Available")
        else:
            print("❌ GNews API key: Not configured")
            return False
    except Exception as e:
        print(f"❌ GNews API key error: {e}")
        return False
    
    print("✅ All dependencies are available!")
    return True

if __name__ == "__main__":
    print("🚀 Trending Subtopics Test Script")
    print("=" * 40)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependencies not available. Please check your configuration.")
        sys.exit(1)
    
    # Run tests
    test_trending_subtopics() 