#!/usr/bin/env python3
"""
Test file for PrysmIOS backend functions with mock data.
Run this file to test all functions without making real API requests.
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

# Add the current directory to Python path to import main functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import functions from main.py
from main import (
    build_system_prompt,
    format_conversation_history,
    format_gnews_articles_for_prysm,
    gnews_search,
    gnews_top_headlines
)

# Mock data for testing
MOCK_USER_PREFERENCES = {
    "en": {
        "subjects": ["technology", "sports"],
        "detail_level": "Medium",
        "language": "en"
    },
    "fr": {
        "subjects": ["sport", "technologie"],
        "detail_level": "Detailed",
        "language": "fr"
    },
    "es": {
        "subjects": ["deportes", "negocios"],
        "detail_level": "Light",
        "language": "es"
    },
    "ar": {
        "subjects": ["رياضة", "تكنولوجيا"],
        "detail_level": "Medium",
        "language": "ar"
    }
}

MOCK_CONVERSATION_HISTORY = [
    {"role": "user", "content": "Hello, I'm interested in tech news"},
    {"role": "assistant", "content": "Hi! I'd be happy to help you with technology news. What specific areas interest you?"},
    {"role": "user", "content": "I like AI and smartphones"},
    {"role": "chatbot", "content": "Great! Are you interested in specific companies like Apple, Google, or OpenAI?"}
]

MOCK_GNEWS_RESPONSE = {
    "success": True,
    "totalArticles": 150,
    "articles": [
        {
            "title": "Apple Unveils New iPhone 16 with Advanced AI Features",
            "description": "Apple's latest iPhone includes groundbreaking AI capabilities that revolutionize mobile computing.",
            "content": "Apple today announced the iPhone 16, featuring the most advanced AI processor ever built into a smartphone...",
            "url": "https://example.com/apple-iphone-16-ai",
            "image": "https://example.com/images/iphone16.jpg",
            "publishedAt": "2025-05-26T10:30:00Z",
            "source": {
                "name": "TechCrunch",
                "url": "https://techcrunch.com"
            }
        },
        {
            "title": "OpenAI Releases GPT-5 with Unprecedented Capabilities",
            "description": "The new language model shows remarkable improvements in reasoning and multimodal understanding.",
            "content": "OpenAI's GPT-5 represents a significant leap forward in artificial intelligence capabilities...",
            "url": "https://example.com/openai-gpt5-release",
            "image": "https://example.com/images/gpt5.jpg",
            "publishedAt": "2025-05-26T08:15:00Z",
            "source": {
                "name": "The Verge",
                "url": "https://theverge.com"
            }
        },
        {
            "title": "Tesla's New Autopilot Update Improves Safety by 40%",
            "description": "Latest software update brings significant improvements to Tesla's self-driving capabilities.",
            "content": "Tesla has rolled out a major update to its Autopilot system, showing dramatic safety improvements...",
            "url": "https://example.com/tesla-autopilot-update",
            "image": "https://example.com/images/tesla.jpg",
            "publishedAt": "2025-05-26T06:45:00Z",
            "source": {
                "name": "Electrek",
                "url": "https://electrek.co"
            }
        }
    ],
    "query": "technology AI",
    "params": {
        "q": "technology AI",
        "lang": "en",
        "country": "us",
        "max": 10
    }
}

MOCK_GNEWS_ERROR_RESPONSE = {
    "success": False,
    "error": "Daily quota reached",
    "articles": []
}

def print_separator(title):
    """Print a formatted separator for test sections."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_test_result(test_name, success, details=None):
    """Print formatted test results."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   Details: {details}")

def test_build_system_prompt():
    """Test the build_system_prompt function with different languages."""
    print_separator("Testing build_system_prompt Function")
    
    for lang_code, preferences in MOCK_USER_PREFERENCES.items():
        try:
            prompt = build_system_prompt(preferences)
            
            # Check if prompt contains expected elements
            has_role = any(word in prompt.lower() for word in ["assistant", "مساعد", "asistente"])
            has_subjects = any(subject.lower() in prompt.lower() for subject in preferences["subjects"])
            has_detail_level = preferences["detail_level"].lower() in prompt.lower()
            
            success = has_role and len(prompt) > 100  # Basic validation
            details = f"Language: {lang_code}, Length: {len(prompt)} chars"
            
            print_test_result(f"System prompt generation ({lang_code})", success, details)
            
            if lang_code == "en":  # Print one example
                print(f"\nExample prompt (first 200 chars):\n{prompt[:200]}...\n")
                
        except Exception as e:
            print_test_result(f"System prompt generation ({lang_code})", False, f"Error: {e}")

def test_format_conversation_history():
    """Test the format_conversation_history function."""
    print_separator("Testing format_conversation_history Function")
    
    try:
        formatted = format_conversation_history(MOCK_CONVERSATION_HISTORY)
        
        # Check if all messages are properly formatted
        expected_roles = ["user", "assistant", "user", "assistant"]
        actual_roles = [msg["role"] for msg in formatted]
        
        success = (
            len(formatted) == len(MOCK_CONVERSATION_HISTORY) and
            actual_roles == expected_roles and
            all("content" in msg for msg in formatted)
        )
        
        details = f"Input: {len(MOCK_CONVERSATION_HISTORY)} messages, Output: {len(formatted)} messages"
        print_test_result("Conversation history formatting", success, details)
        
        print("\nFormatted conversation:")
        for i, msg in enumerate(formatted):
            print(f"  {i+1}. {msg['role']}: {msg['content'][:50]}...")
            
    except Exception as e:
        print_test_result("Conversation history formatting", False, f"Error: {e}")

def test_format_gnews_articles():
    """Test the format_gnews_articles_for_prysm function."""
    print_separator("Testing format_gnews_articles_for_prysm Function")
    
    try:
        # Test with successful response
        formatted_articles = format_gnews_articles_for_prysm(MOCK_GNEWS_RESPONSE)
        
        success = (
            len(formatted_articles) == 3 and
            all("title" in article for article in formatted_articles) and
            all("link" in article for article in formatted_articles) and
            all("source" in article for article in formatted_articles)
        )
        
        details = f"Converted {len(MOCK_GNEWS_RESPONSE['articles'])} articles to {len(formatted_articles)} formatted articles"
        print_test_result("GNews articles formatting (success)", success, details)
        
        # Test with error response
        formatted_error = format_gnews_articles_for_prysm(MOCK_GNEWS_ERROR_RESPONSE)
        error_success = len(formatted_error) == 0
        
        print_test_result("GNews articles formatting (error)", error_success, "Empty list returned for error response")
        
        # Print example formatted article
        if formatted_articles:
            print(f"\nExample formatted article:")
            example = formatted_articles[0]
            for key, value in example.items():
                print(f"  {key}: {str(value)[:60]}{'...' if len(str(value)) > 60 else ''}")
                
    except Exception as e:
        print_test_result("GNews articles formatting", False, f"Error: {e}")

def test_gnews_functions_with_mock():
    """Test GNews functions with mocked API responses."""
    print_separator("Testing GNews Functions with Mock Data")
    
    # Mock the requests.get function
    with patch('main.requests.get') as mock_get:
        # Test successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalArticles": 150,
            "articles": MOCK_GNEWS_RESPONSE["articles"]
        }
        mock_get.return_value = mock_response
        
        # Mock the API key function
        with patch('main.get_gnews_key', return_value='mock-api-key'):
            try:
                # Test gnews_search
                search_result = gnews_search("technology", lang="en", country="us", max_articles=5)
                search_success = search_result.get("success", False) and len(search_result.get("articles", [])) > 0
                print_test_result("GNews search function", search_success, f"Returned {len(search_result.get('articles', []))} articles")
                
                # Test gnews_top_headlines
                headlines_result = gnews_top_headlines("technology", lang="en", country="us", max_articles=5)
                headlines_success = headlines_result.get("success", False) and len(headlines_result.get("articles", [])) > 0
                print_test_result("GNews top headlines function", headlines_success, f"Returned {len(headlines_result.get('articles', []))} articles")
                
            except Exception as e:
                print_test_result("GNews functions", False, f"Error: {e}")
        
        # Test error response
        mock_response.status_code = 403
        mock_response.text = "Daily quota reached"
        
        with patch('main.get_gnews_key', return_value='mock-api-key'):
            try:
                error_result = gnews_search("technology")
                error_success = "error" in error_result and not error_result.get("success", True)
                print_test_result("GNews error handling", error_success, f"Error: {error_result.get('error', 'Unknown')}")
                
            except Exception as e:
                print_test_result("GNews error handling", False, f"Exception: {e}")

def test_openai_mock():
    """Test OpenAI integration with mock data."""
    print_separator("Testing OpenAI Integration with Mock Data")
    
    # Mock OpenAI response
    mock_openai_response = Mock()
    mock_openai_response.choices = [Mock()]
    mock_openai_response.choices[0].message.content = "Hello! I'd be happy to help you with technology news. Are you particularly interested in AI developments, smartphone innovations, or specific tech companies like Apple or Google?"
    mock_openai_response.usage.prompt_tokens = 150
    mock_openai_response.usage.completion_tokens = 35
    mock_openai_response.usage.total_tokens = 185
    
    # Mock OpenAI client
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    
    with patch('main.get_openai_client', return_value=mock_client):
        try:
            from main import generate_ai_response
            
            system_prompt = build_system_prompt(MOCK_USER_PREFERENCES["en"])
            user_message = "I'm interested in technology news"
            
            ai_response = generate_ai_response(system_prompt, [], user_message)
            
            success = (
                ai_response.get("success", False) and
                "message" in ai_response and
                "usage" in ai_response
            )
            
            details = f"Generated {len(ai_response.get('message', ''))} characters, Used {ai_response.get('usage', {}).get('total_tokens', 0)} tokens"
            print_test_result("OpenAI response generation", success, details)
            
            if success:
                print(f"\nExample AI response:\n{ai_response['message'][:200]}...\n")
                
        except Exception as e:
            print_test_result("OpenAI response generation", False, f"Error: {e}")

def run_all_tests():
    """Run all test functions."""
    print("🧪 PrysmIOS Backend Functions Test Suite")
    print(f"📅 Test run: {datetime.now().isoformat()}")
    
    test_build_system_prompt()
    test_format_conversation_history()
    test_format_gnews_articles()
    test_gnews_functions_with_mock()
    test_openai_mock()
    
    print_separator("Test Suite Complete")
    print("✅ All tests completed! Check results above.")
    print("\n💡 To test with real APIs:")
    print("   1. Set your OPENAI_API_KEY environment variable")
    print("   2. Set your GNEWS_API_KEY environment variable")
    print("   3. Deploy to Firebase and test the endpoints")

if __name__ == "__main__":
    run_all_tests() 