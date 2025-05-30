#!/usr/bin/env python3
"""
Quick Test for Parallel Analysis Functionality
Tests the specific subjects extraction without full conversation interface.
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_parallel_analysis():
    """Test the parallel analysis functionality with sample data."""
    
    print("🧪 Testing Parallel Analysis for Specific Subjects")
    print("=" * 60)
    
    # Test data
    test_cases = [
        {
            "language": "en",
            "conversation_history": [
                {"role": "user", "content": "I'm interested in technology news"},
                {"role": "assistant", "content": "Great! What specific areas of technology interest you most?"}
            ],
            "user_message": "I really like following Tesla and SpaceX. Elon Musk is fascinating, and I also want to know about Apple's latest iPhone releases.",
            "expected_subjects": ["Tesla", "SpaceX", "Elon Musk", "Apple", "iPhone"]
        },
        {
            "language": "fr", 
            "conversation_history": [
                {"role": "user", "content": "Je m'intéresse aux actualités sportives"},
                {"role": "assistant", "content": "Parfait! Quels sports vous intéressent le plus?"}
            ],
            "user_message": "J'adore suivre le PSG et Kylian Mbappé. Je regarde aussi beaucoup de tennis, surtout Roland Garros et Novak Djokovic.",
            "expected_subjects": ["PSG", "Kylian Mbappé", "Roland Garros", "Novak Djokovic"]
        },
        {
            "language": "es",
            "conversation_history": [
                {"role": "user", "content": "Me interesan las noticias de negocios"},
                {"role": "assistant", "content": "¡Excelente! ¿Qué aspectos de los negocios te interesan más?"}
            ],
            "user_message": "Sigo mucho las acciones de Amazon y Microsoft. También me interesa Bitcoin y las noticias sobre Jeff Bezos.",
            "expected_subjects": ["Amazon", "Microsoft", "Bitcoin", "Jeff Bezos"]
        }
    ]
    
    # Import the analysis function
    try:
        from main import analyze_conversation_for_specific_subjects
        print("✅ Successfully imported analysis function from main.py")
    except ImportError as e:
        print(f"❌ Could not import analysis function: {e}")
        print("💡 Make sure main.py is available and contains analyze_conversation_for_specific_subjects")
        return False
    
    print()
    
    # Run tests
    total_tests = len(test_cases)
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 Test Case {i}/{total_tests} - Language: {test_case['language'].upper()}")
        print(f"📝 User Message: {test_case['user_message']}")
        print(f"🎯 Expected Subjects: {test_case['expected_subjects']}")
        
        try:
            # Run analysis
            result = analyze_conversation_for_specific_subjects(
                test_case["conversation_history"],
                test_case["user_message"], 
                test_case["language"]
            )
            
            if result["success"]:
                found_subjects = result.get("specific_subjects", [])
                usage = result.get("usage", {})
                
                print(f"✅ Analysis successful!")
                print(f"📊 Found Subjects: {found_subjects}")
                print(f"🔢 Token Usage: {usage.get('total_tokens', 'N/A')}")
                
                # Check if we found any expected subjects
                found_expected = [subj for subj in found_subjects if any(exp.lower() in subj.lower() or subj.lower() in exp.lower() for exp in test_case["expected_subjects"])]
                
                if found_expected:
                    print(f"🎉 Found expected subjects: {found_expected}")
                    passed_tests += 1
                else:
                    print(f"⚠️  No expected subjects found, but analysis worked")
                    print(f"💡 This might be due to different extraction patterns")
                
            else:
                print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
        
        print("-" * 60)
        print()
    
    # Summary
    print(f"📊 Test Summary:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Parallel analysis is working correctly.")
    elif passed_tests > 0:
        print("⚠️  Some tests passed. Analysis is working but may need tuning.")
    else:
        print("❌ No tests passed. Check the analysis function implementation.")
    
    return passed_tests > 0

def test_openai_connection():
    """Test if OpenAI connection is working."""
    print("\n🔍 Testing OpenAI Connection...")
    
    try:
        from main import get_openai_client
        client = get_openai_client()
        
        if client:
            print("✅ OpenAI client initialized successfully")
            
            # Try a simple test call
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "Say 'test successful'"}],
                    max_tokens=10
                )
                print("✅ OpenAI API call successful")
                print(f"📝 Response: {response.choices[0].message.content}")
                return True
            except Exception as e:
                print(f"❌ OpenAI API call failed: {e}")
                return False
        else:
            print("❌ OpenAI client not available")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import OpenAI functions: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Parallel Analysis Tests")
    print("=" * 60)
    
    # Test OpenAI connection first
    openai_works = test_openai_connection()
    
    if openai_works:
        print("\n" + "=" * 60)
        # Run parallel analysis tests
        analysis_works = test_parallel_analysis()
        
        if analysis_works:
            print("\n🎉 All systems working! You can now test the full conversation with parallel analysis.")
            print("💡 Run: python interactive_conversation_test.py")
        else:
            print("\n❌ Parallel analysis needs debugging.")
    else:
        print("\n❌ OpenAI connection failed. Set up your API key first.")
        print("💡 Export OPENAI_API_KEY='your-key-here'") 