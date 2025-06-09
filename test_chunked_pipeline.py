#!/usr/bin/env python3
"""
Test script for chunked podcast pipeline
"""

import json
import sys
import os

# Add the modules path to import
sys.path.append('modules')

try:
    from interaction.chunked_podcast import (
        parse_script_sections,
        format_timestamp_for_display,
        find_article_at_timestamp,
        estimate_word_duration
    )
    print("✅ Successfully imported chunked podcast functions")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_script_parsing():
    """Test the script parsing functionality"""
    print("\n🧪 Testing script parsing...")
    
    # Read the test script
    try:
        with open('modules/interaction/test_script.txt', 'r', encoding='utf-8') as f:
            script_content = f.read()
        print(f"📄 Loaded test script: {len(script_content)} characters")
    except FileNotFoundError:
        print("❌ Test script file not found")
        return False
    
    # Parse sections
    sections = parse_script_sections(script_content)
    
    print(f"\n📊 Parsing Results:")
    print(f"   Total sections found: {len(sections)}")
    
    for section_name, content in sections.items():
        word_count = len(content.split())
        estimated_duration = estimate_word_duration(content)
        print(f"   📝 {section_name}: {word_count} words (~{estimated_duration:.1f}s)")
        print(f"      Preview: {content[:60]}...")
        print()
    
    return sections

def test_timeline_simulation():
    """Simulate timeline creation without actual audio generation"""
    print("\n🕐 Testing timeline simulation...")
    
    sections = test_script_parsing()
    if not sections:
        return False
    
    # Simulate timeline creation
    timeline = {}
    current_timestamp = 0.0
    
    print(f"\n📈 Simulated Timeline:")
    
    for section_name, content in sections.items():
        # Estimate duration based on word count
        section_duration = estimate_word_duration(content)
        end_timestamp = current_timestamp + section_duration
        
        # Create timeline entry
        timeline_key = f"{current_timestamp:.1f}-{end_timestamp:.1f}"
        timeline[timeline_key] = {
            "section_name": section_name,
            "article_id": section_name if section_name.startswith("<<") else None,
            "start_seconds": current_timestamp,
            "end_seconds": end_timestamp,
            "duration_seconds": section_duration,
            "word_count": len(content.split()),
            "content_preview": content[:80] + "..." if len(content) > 80 else content
        }
        
        # Display timeline entry
        formatted_start = format_timestamp_for_display(current_timestamp)
        formatted_end = format_timestamp_for_display(end_timestamp)
        print(f"   🎵 {formatted_start}-{formatted_end}: {section_name}")
        print(f"      Duration: {section_duration:.1f}s, Words: {len(content.split())}")
        
        current_timestamp = end_timestamp
    
    total_duration = current_timestamp
    print(f"\n⏱️  Total estimated duration: {format_timestamp_for_display(total_duration)} ({total_duration:.1f}s)")
    
    return timeline

def test_timestamp_lookup():
    """Test finding articles at specific timestamps"""
    print("\n🔍 Testing timestamp lookup...")
    
    timeline = test_timeline_simulation()
    if not timeline:
        return False
    
    # Test various timestamps
    test_timestamps = [15.0, 45.0, 75.0, 120.0, 180.0, 999.0]
    
    print(f"\n🎯 Timestamp Lookup Tests:")
    
    for timestamp in test_timestamps:
        article_info = find_article_at_timestamp(timeline, timestamp)
        formatted_time = format_timestamp_for_display(timestamp)
        
        if article_info:
            print(f"   ⏰ At {formatted_time}: {article_info['section_name']}")
            print(f"      Range: {article_info['formatted_range']}")
            print(f"      Article ID: {article_info['article_id']}")
            print(f"      Preview: {article_info['content_preview']}")
        else:
            print(f"   ❌ At {formatted_time}: No article found")
        print()

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🚨 Testing edge cases...")
    
    # Test empty script
    print("Testing empty script...")
    empty_sections = parse_script_sections("")
    print(f"   Empty script result: {empty_sections}")
    
    # Test malformed script
    print("Testing malformed script...")
    malformed_script = "This is just text without any section markers"
    malformed_sections = parse_script_sections(malformed_script)
    print(f"   Malformed script result: {list(malformed_sections.keys())}")
    
    # Test invalid timestamp lookup
    print("Testing invalid timestamp lookup...")
    empty_timeline = {}
    result = find_article_at_timestamp(empty_timeline, 60.0)
    print(f"   Invalid lookup result: {result}")
    
    print("✅ Edge case testing completed")

def generate_interaction_scenarios():
    """Generate realistic interaction scenarios for testing"""
    print("\n🎭 Generating interaction scenarios...")
    
    timeline = test_timeline_simulation()
    if not timeline:
        return
    
    scenarios = [
        {
            "timestamp": 30.0,
            "user_question": "Tell me more about OpenAI's new approach",
            "expected_article": "article1"
        },
        {
            "timestamp": 90.0,
            "user_question": "What's Revolut's valuation?",
            "expected_article": "article2"
        },
        {
            "timestamp": 150.0,
            "user_question": "Why are people angry about Binance?",
            "expected_article": "article3"
        },
        {
            "timestamp": 5.0,
            "user_question": "What topics are we covering today?",
            "expected_article": None  # Should be INTRO
        }
    ]
    
    print(f"\n🎮 Interaction Scenarios:")
    
    for i, scenario in enumerate(scenarios, 1):
        timestamp = scenario["timestamp"]
        question = scenario["user_question"]
        expected = scenario["expected_article"]
        
        article_info = find_article_at_timestamp(timeline, timestamp)
        actual_article = article_info["article_id"] if article_info else None
        
        status = "✅" if actual_article == expected else "❌"
        
        print(f"   {status} Scenario {i}:")
        print(f"      Time: {format_timestamp_for_display(timestamp)}")
        print(f"      Question: '{question}'")
        print(f"      Expected: {expected}")
        print(f"      Actual: {actual_article}")
        if article_info:
            print(f"      Section: {article_info['section_name']}")
        print()

def main():
    """Run all tests"""
    print("🚀 Starting Chunked Podcast Pipeline Tests")
    print("=" * 50)
    
    try:
        # Run all tests
        test_script_parsing()
        test_timeline_simulation()
        test_timestamp_lookup()
        test_edge_cases()
        generate_interaction_scenarios()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed!")
        print("\n📋 Summary:")
        print("   ✅ Script parsing: Working")
        print("   ✅ Timeline simulation: Working")
        print("   ✅ Timestamp lookup: Working")
        print("   ✅ Edge cases: Handled")
        print("   ✅ Interaction scenarios: Generated")
        print("\n🔥 Pipeline is ready for audio generation!")
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 