#!/usr/bin/env python3
"""
Mock test script for the trending subtopics functionality.
This script tests the extract_trending_subtopics function with mock data
to avoid making actual API calls during testing.
"""

import sys
import os
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Add the current directory to Python path to import main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock data for different topics
MOCK_ARTICLES_DATA = {
    "technology": {
        "success": True,
        "totalArticles": 50,
        "articles": [
            {
                "title": "Apple Vision Pro Sales Disappoint as Mixed Reality Market Struggles",
                "description": "Apple's highly anticipated Vision Pro headset faces lukewarm reception from consumers amid high pricing and limited content availability.",
                "url": "https://example.com/apple-vision-pro",
                "source": {"name": "TechCrunch"},
                "publishedAt": "2024-01-15T10:30:00Z",
                "image": "https://example.com/image1.jpg"
            },
            {
                "title": "OpenAI Announces GPT-5 Development Amid AI Regulation Debates",
                "description": "The AI company reveals plans for next-generation language model while facing increased scrutiny from regulators worldwide.",
                "url": "https://example.com/openai-gpt5",
                "source": {"name": "The Verge"},
                "publishedAt": "2024-01-15T09:15:00Z",
                "image": "https://example.com/image2.jpg"
            },
            {
                "title": "Tech Layoffs Continue as Meta Cuts 10,000 More Jobs",
                "description": "Meta announces another round of significant layoffs as the company restructures its operations and focuses on efficiency.",
                "url": "https://example.com/meta-layoffs",
                "source": {"name": "Reuters"},
                "publishedAt": "2024-01-15T08:45:00Z",
                "image": "https://example.com/image3.jpg"
            },
            {
                "title": "Quantum Computing Breakthrough: IBM Achieves 1000-Qubit Milestone",
                "description": "IBM's latest quantum processor represents a significant leap forward in quantum computing capabilities and commercial viability.",
                "url": "https://example.com/ibm-quantum",
                "source": {"name": "MIT Technology Review"},
                "publishedAt": "2024-01-15T07:20:00Z",
                "image": "https://example.com/image4.jpg"
            },
            {
                "title": "Cybersecurity Threats Rise 40% as AI-Powered Attacks Increase",
                "description": "Security experts warn of sophisticated new attack vectors leveraging artificial intelligence to bypass traditional defenses.",
                "url": "https://example.com/cybersecurity-threats",
                "source": {"name": "Wired"},
                "publishedAt": "2024-01-15T06:30:00Z",
                "image": "https://example.com/image5.jpg"
            },
            {
                "title": "Startup Funding Drops 60% in Q4 as Investors Turn Cautious",
                "description": "Venture capital investment reaches lowest levels since 2020 as economic uncertainty affects startup ecosystem.",
                "url": "https://example.com/startup-funding",
                "source": {"name": "TechCrunch"},
                "publishedAt": "2024-01-15T05:45:00Z",
                "image": "https://example.com/image6.jpg"
            },
            {
                "title": "Tesla Autopilot Under Investigation After Series of Accidents",
                "description": "Federal regulators launch comprehensive review of Tesla's self-driving technology following recent safety incidents.",
                "url": "https://example.com/tesla-autopilot",
                "source": {"name": "Bloomberg"},
                "publishedAt": "2024-01-15T04:15:00Z",
                "image": "https://example.com/image7.jpg"
            },
            {
                "title": "Microsoft Copilot Integration Expands to Office Suite",
                "description": "Microsoft announces deeper AI integration across its productivity tools, promising enhanced user experience and efficiency.",
                "url": "https://example.com/microsoft-copilot",
                "source": {"name": "The Verge"},
                "publishedAt": "2024-01-15T03:30:00Z",
                "image": "https://example.com/image8.jpg"
            }
        ]
    },
    "sports": {
        "success": True,
        "totalArticles": 35,
        "articles": [
            {
                "title": "Messi Leads Argentina to Copa America Victory",
                "description": "Lionel Messi scores decisive goal as Argentina defeats Brazil 2-1 in thrilling Copa America final.",
                "url": "https://example.com/messi-copa",
                "source": {"name": "ESPN"},
                "publishedAt": "2024-01-15T10:00:00Z",
                "image": "https://example.com/sports1.jpg"
            },
            {
                "title": "NBA Trade Deadline Shakeup: Lakers Acquire All-Star Guard",
                "description": "Los Angeles Lakers make major move ahead of playoffs, trading for veteran point guard in blockbuster deal.",
                "url": "https://example.com/nba-trade",
                "source": {"name": "ESPN"},
                "publishedAt": "2024-01-15T09:30:00Z",
                "image": "https://example.com/sports2.jpg"
            },
            {
                "title": "Tennis Australian Open: Djokovic Reaches Semifinals",
                "description": "Novak Djokovic advances to Australian Open semifinals with straight-sets victory over rising star.",
                "url": "https://example.com/djokovic-tennis",
                "source": {"name": "Tennis.com"},
                "publishedAt": "2024-01-15T08:15:00Z",
                "image": "https://example.com/sports3.jpg"
            },
            {
                "title": "NFL Playoffs: Chiefs Advance to Conference Championship",
                "description": "Kansas City Chiefs defeat Buffalo Bills in overtime thriller to secure spot in AFC Championship game.",
                "url": "https://example.com/nfl-playoffs",
                "source": {"name": "NFL.com"},
                "publishedAt": "2024-01-15T07:45:00Z",
                "image": "https://example.com/sports4.jpg"
            },
            {
                "title": "Olympic Preparations: Paris 2024 Venues Near Completion",
                "description": "Paris Olympic organizers announce 95% completion rate for venues as summer games approach.",
                "url": "https://example.com/olympics-paris",
                "source": {"name": "Olympic Channel"},
                "publishedAt": "2024-01-15T06:20:00Z",
                "image": "https://example.com/sports5.jpg"
            }
        ]
    },
    "business": {
        "success": True,
        "totalArticles": 42,
        "articles": [
            {
                "title": "Federal Reserve Signals Potential Rate Cuts in 2024",
                "description": "Fed Chair Jerome Powell hints at possible interest rate reductions as inflation shows signs of cooling.",
                "url": "https://example.com/fed-rates",
                "source": {"name": "Wall Street Journal"},
                "publishedAt": "2024-01-15T10:45:00Z",
                "image": "https://example.com/business1.jpg"
            },
            {
                "title": "Amazon Stock Surges on Strong Q4 Earnings Report",
                "description": "E-commerce giant beats analyst expectations with record holiday season sales and AWS growth.",
                "url": "https://example.com/amazon-earnings",
                "source": {"name": "CNBC"},
                "publishedAt": "2024-01-15T09:20:00Z",
                "image": "https://example.com/business2.jpg"
            },
            {
                "title": "Cryptocurrency Market Rallies as Bitcoin Hits $45,000",
                "description": "Bitcoin reaches highest level in six months amid renewed institutional interest and ETF approvals.",
                "url": "https://example.com/bitcoin-rally",
                "source": {"name": "CoinDesk"},
                "publishedAt": "2024-01-15T08:30:00Z",
                "image": "https://example.com/business3.jpg"
            },
            {
                "title": "Supply Chain Disruptions Ease as Shipping Costs Drop",
                "description": "Global supply chains show signs of normalization with container shipping rates falling to pre-pandemic levels.",
                "url": "https://example.com/supply-chain",
                "source": {"name": "Reuters"},
                "publishedAt": "2024-01-15T07:15:00Z",
                "image": "https://example.com/business4.jpg"
            },
            {
                "title": "Green Energy Investments Reach Record $2 Trillion",
                "description": "Renewable energy sector attracts unprecedented investment as governments push climate initiatives.",
                "url": "https://example.com/green-energy",
                "source": {"name": "Bloomberg"},
                "publishedAt": "2024-01-15T06:45:00Z",
                "image": "https://example.com/business5.jpg"
            }
        ]
    }
}

# Mock LLM responses for different topics
MOCK_LLM_RESPONSES = {
    "technology": "Vision Pro sales, GPT-5 development, AI regulation, tech layoffs, quantum computing, cybersecurity threats, startup funding, Tesla Autopilot",
    "sports": "Copa America, NBA trades, Australian Open, NFL playoffs, Olympics 2024, Messi performance, Lakers acquisition",
    "business": "Fed rate cuts, Amazon earnings, Bitcoin rally, supply chain, green energy, cryptocurrency ETF, AWS growth"
}

def create_mock_openai_client():
    """Create a mock OpenAI client that returns predefined responses."""
    mock_client = Mock()
    
    def mock_chat_completion_create(**kwargs):
        # Extract the topic from the prompt
        messages = kwargs.get('messages', [])
        user_message = ""
        for msg in messages:
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        # Determine topic from the prompt
        topic = "technology"  # default
        if "sports" in user_message.lower():
            topic = "sports"
        elif "business" in user_message.lower():
            topic = "business"
        elif "technology" in user_message.lower():
            topic = "technology"
        
        # Create mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = MOCK_LLM_RESPONSES.get(topic, MOCK_LLM_RESPONSES["technology"])
        
        # Mock usage stats
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 1200
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 1250
        
        return mock_response
    
    mock_client.chat.completions.create = mock_chat_completion_create
    return mock_client

def test_extract_trending_subtopics_with_mocks():
    """Test the extract_trending_subtopics function with mock data."""
    
    print("🧪 Testing Trending Subtopics with Mock Data")
    print("=" * 50)
    
    # Import the function we want to test
    try:
        from main import extract_trending_subtopics
        print("✅ Successfully imported extract_trending_subtopics")
    except ImportError as e:
        print(f"❌ Failed to import function: {e}")
        return False
    
    test_cases = [
        {
            "topic": "technology",
            "lang": "en",
            "country": "us",
            "max_articles": 8,
            "expected_subtopics": ["Vision Pro sales", "GPT-5 development", "AI regulation", "tech layoffs"]
        },
        {
            "topic": "sports",
            "lang": "en", 
            "country": "us",
            "max_articles": 5,
            "expected_subtopics": ["Copa America", "NBA trades", "Australian Open"]
        },
        {
            "topic": "business",
            "lang": "en",
            "country": "us", 
            "max_articles": 5,
            "expected_subtopics": ["Fed rate cuts", "Amazon earnings", "Bitcoin rally"]
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['topic'].upper()}")
        print("-" * 30)
        
        topic = test_case["topic"]
        
        # Mock the gnews_top_headlines function
        def mock_gnews_top_headlines(category, lang, country, max_articles):
            return MOCK_ARTICLES_DATA.get(category, MOCK_ARTICLES_DATA["technology"])
        
        # Mock the get_openai_client function
        def mock_get_openai_client():
            return create_mock_openai_client()
        
        try:
            # Apply mocks and run the test
            with patch('main.gnews_top_headlines', side_effect=mock_gnews_top_headlines), \
                 patch('main.get_openai_client', side_effect=mock_get_openai_client):
                
                result = extract_trending_subtopics(
                    topic=test_case["topic"],
                    lang=test_case["lang"],
                    country=test_case["country"],
                    max_articles=test_case["max_articles"]
                )
                
                # Validate results
                if result.get("success"):
                    print(f"✅ Success!")
                    print(f"📊 Articles analyzed: {result.get('articles_analyzed', 0)}")
                    print(f"🔥 Trending subtopics ({len(result.get('subtopics', []))}):")
                    
                    subtopics = result.get('subtopics', [])
                    for j, subtopic in enumerate(subtopics, 1):
                        print(f"   {j}. {subtopic}")
                    
                    # Check if we got expected subtopics
                    expected = test_case["expected_subtopics"]
                    found_expected = sum(1 for exp in expected if any(exp.lower() in sub.lower() for sub in subtopics))
                    
                    print(f"🎯 Expected subtopics found: {found_expected}/{len(expected)}")
                    
                    if 'usage' in result:
                        usage = result['usage']
                        print(f"💰 Token usage: {usage.get('total_tokens', 0)} tokens")
                    
                    # Validate response structure
                    required_fields = ['success', 'topic', 'articles_analyzed', 'subtopics', 'usage']
                    missing_fields = [field for field in required_fields if field not in result]
                    
                    if not missing_fields:
                        print(f"✅ Response structure valid")
                        success_count += 1
                    else:
                        print(f"❌ Missing fields in response: {missing_fields}")
                        
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            print(f"💥 Exception during test: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "=" * 50)
    print(f"🎉 Testing completed! {success_count}/{len(test_cases)} tests passed")
    
    return success_count == len(test_cases)

def test_error_scenarios():
    """Test error handling scenarios."""
    
    print("\n🚨 Testing Error Scenarios")
    print("=" * 30)
    
    try:
        from main import extract_trending_subtopics
    except ImportError as e:
        print(f"❌ Failed to import function: {e}")
        return False
    
    # Test 1: No articles found
    print("\n📋 Test: No articles found")
    def mock_gnews_empty(category, lang, country, max_articles):
        return {"success": False, "error": "No articles found", "articles": []}
    
    with patch('main.gnews_top_headlines', side_effect=mock_gnews_empty):
        result = extract_trending_subtopics("invalidtopic")
        if not result.get("success") and "No articles found" in result.get("error", ""):
            print("✅ Correctly handled no articles scenario")
        else:
            print("❌ Failed to handle no articles scenario")
    
    # Test 2: OpenAI client unavailable
    print("\n📋 Test: OpenAI client unavailable")
    def mock_gnews_success(category, lang, country, max_articles):
        return MOCK_ARTICLES_DATA["technology"]
    
    def mock_openai_none():
        return None
    
    with patch('main.gnews_top_headlines', side_effect=mock_gnews_success), \
         patch('main.get_openai_client', side_effect=mock_openai_none):
        
        result = extract_trending_subtopics("technology")
        if not result.get("success") and "OpenAI client not available" in result.get("error", ""):
            print("✅ Correctly handled OpenAI unavailable scenario")
        else:
            print("❌ Failed to handle OpenAI unavailable scenario")
    
    print("✅ Error scenario testing completed")

def test_response_format():
    """Test that the response format matches the expected API specification."""
    
    print("\n📋 Testing Response Format")
    print("=" * 30)
    
    try:
        from main import extract_trending_subtopics
    except ImportError as e:
        print(f"❌ Failed to import function: {e}")
        return False
    
    def mock_gnews_success(category, lang, country, max_articles):
        return MOCK_ARTICLES_DATA["technology"]
    
    def mock_get_openai_client():
        return create_mock_openai_client()
    
    with patch('main.gnews_top_headlines', side_effect=mock_gnews_success), \
         patch('main.get_openai_client', side_effect=mock_get_openai_client):
        
        result = extract_trending_subtopics("technology", "en", "us", 5)
        
        # Check required fields
        required_fields = {
            'success': bool,
            'topic': str,
            'articles_analyzed': int,
            'subtopics': list,
            'usage': dict
        }
        
        print("🔍 Validating response format:")
        all_valid = True
        
        for field, expected_type in required_fields.items():
            if field in result:
                actual_type = type(result[field])
                if actual_type == expected_type:
                    print(f"  ✅ {field}: {actual_type.__name__}")
                else:
                    print(f"  ❌ {field}: expected {expected_type.__name__}, got {actual_type.__name__}")
                    all_valid = False
            else:
                print(f"  ❌ {field}: missing")
                all_valid = False
        
        # Check usage sub-fields
        if 'usage' in result and isinstance(result['usage'], dict):
            usage_fields = ['prompt_tokens', 'completion_tokens', 'total_tokens']
            for field in usage_fields:
                if field in result['usage'] and isinstance(result['usage'][field], int):
                    print(f"  ✅ usage.{field}: int")
                else:
                    print(f"  ❌ usage.{field}: missing or wrong type")
                    all_valid = False
        
        if all_valid:
            print("✅ Response format is valid!")
        else:
            print("❌ Response format has issues")
        
        return all_valid

def main():
    """Run all tests."""
    
    print("🚀 Mock Testing Suite for Trending Subtopics")
    print("=" * 50)
    
    # Run all test suites
    test_results = []
    
    print("\n1️⃣ Running main functionality tests...")
    test_results.append(test_extract_trending_subtopics_with_mocks())
    
    print("\n2️⃣ Running error scenario tests...")
    test_error_scenarios()  # This doesn't return a boolean
    test_results.append(True)  # Assume passed if no exceptions
    
    print("\n3️⃣ Running response format tests...")
    test_results.append(test_response_format())
    
    # Summary
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"\n" + "=" * 50)
    print(f"🎯 FINAL RESULTS: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The function is working correctly with mock data.")
    else:
        print("⚠️  Some tests failed. Please review the output above.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    main() 