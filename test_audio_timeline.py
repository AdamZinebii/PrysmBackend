#!/usr/bin/env python3
"""
Audio Timeline Test Script
Generates real audio using chunked podcast pipeline and allows timestamp testing.
"""

import sys
import os
import json
import time
from datetime import datetime

# Add modules path
sys.path.append('modules')

try:
    from interaction.chunked_podcast import (
        generate_complete_chunked_podcast,
        find_article_at_timestamp,
        format_timestamp_for_display
    )
    print("✅ Successfully imported chunked podcast functions")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def load_test_script():
    """Load the test script content"""
    try:
        with open('modules/interaction/test_script.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("❌ Test script file not found")
        return None

def save_audio_file(audio_bytes, filename="test_podcast.wav"):
    """Save audio bytes to file"""
    try:
        with open(filename, 'wb') as f:
            f.write(audio_bytes)
        print(f"💾 Audio saved to: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving audio: {e}")
        return None

def display_timeline(timeline):
    """Display the timeline in a nice format"""
    print("\n📈 AUDIO TIMELINE:")
    print("="*60)
    
    for time_range, info in timeline.items():
        start_time = format_timestamp_for_display(info['start_seconds'])
        end_time = format_timestamp_for_display(info['end_seconds'])
        section_name = info['section_name']
        word_count = info['word_count']
        
        # Color coding for different types
        if section_name == "INTRO":
            icon = "🎬"
        elif section_name == "CONCLUSION":
            icon = "🎭"
        elif section_name.startswith("<<"):
            icon = "📰"
        else:
            icon = "📝"
        
        print(f"{icon} {start_time}-{end_time}: {section_name}")
        print(f"   Duration: {info['duration_seconds']:.1f}s | Words: {word_count}")
        print(f"   Preview: {info['content_preview']}")
        print()

def interactive_timestamp_test(timeline):
    """Interactive timestamp testing"""
    print("\n🎯 INTERACTIVE TIMESTAMP TESTING")
    print("="*60)
    print("Enter timestamps to test (format: MM:SS or seconds)")
    print("Commands: 'quit' to exit, 'timeline' to see timeline again")
    print()
    
    while True:
        try:
            user_input = input("🕐 Enter timestamp: ").strip().lower()
            
            if user_input in ['quit', 'exit', 'q']:
                break
            elif user_input == 'timeline':
                display_timeline(timeline)
                continue
            
            # Parse timestamp
            timestamp_seconds = parse_timestamp(user_input)
            if timestamp_seconds is None:
                continue
            
            # Find article at timestamp
            article_info = find_article_at_timestamp(timeline, timestamp_seconds)
            
            print(f"\n🔍 Results for {format_timestamp_for_display(timestamp_seconds)}:")
            print("-" * 40)
            
            if article_info:
                print(f"📍 Section: {article_info['section_name']}")
                print(f"🎵 Time Range: {article_info['formatted_range']}")
                print(f"🆔 Article ID: {article_info['article_id']}")
                print(f"📝 Content Preview:")
                print(f"   {article_info['content_preview']}")
                
                # Suggest related questions
                suggest_questions(article_info['section_name'])
            else:
                print("❌ No article found at this timestamp")
                print("   Make sure the timestamp is within the audio duration")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def parse_timestamp(timestamp_str):
    """Parse timestamp string to seconds"""
    try:
        # If it's already seconds
        if timestamp_str.replace('.', '').isdigit():
            return float(timestamp_str)
        
        # If it's MM:SS format
        if ':' in timestamp_str:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        
        print(f"❌ Invalid timestamp format: {timestamp_str}")
        print("   Use formats like: 30, 1:30, 2:45.5")
        return None
        
    except ValueError:
        print(f"❌ Invalid timestamp: {timestamp_str}")
        return None

def suggest_questions(section_name):
    """Suggest relevant questions based on the section"""
    suggestions = {
        "INTRO": [
            "What topics are we covering today?",
            "How many articles did you analyze?",
            "What's the overall theme of today's briefing?"
        ],
        "<<article1>>": [
            "Tell me more about OpenAI's new approach",
            "How does iterative refinement work?",
            "What applications could benefit from this?"
        ],
        "<<article2>>": [
            "What's Revolut's current valuation?",
            "How many users does Revolut have?",
            "What's their expansion strategy?"
        ],
        "<<article3>>": [
            "Why are people angry about Binance fees?",
            "What's the new fee structure?",
            "Which competitors are people switching to?"
        ],
        "<<article4>>": [
            "How do Northvolt's batteries compare to Tesla's?",
            "When will the new gigafactories be ready?",
            "What's the deal value with BMW?"
        ],
        "<<article5>>": [
            "Why did Meta shut down Horizon Worlds?",
            "How much did Meta spend on the metaverse?",
            "What's their new strategy?"
        ],
        "<<article6>>": [
            "What's new in GitHub Copilot?",
            "How much faster is development now?",
            "What's the new pricing?"
        ],
        "<<article7>>": [
            "What can Pepper 3.0 do?",
            "How much does the robot cost?",
            "What's special about their language model?"
        ],
        "CONCLUSION": [
            "What was the main theme today?",
            "Which story was most interesting?",
            "When's the next briefing?"
        ]
    }
    
    if section_name in suggestions:
        print(f"\n💡 Suggested questions for this section:")
        for i, question in enumerate(suggestions[section_name], 1):
            print(f"   {i}. {question}")

def generate_audio_test():
    """Main function to generate audio and test timeline"""
    print("🎙️ AUDIO TIMELINE GENERATION TEST")
    print("="*60)
    
    # Load test script
    print("📄 Loading test script...")
    script_content = load_test_script()
    if not script_content:
        return
    
    print(f"✅ Script loaded: {len(script_content)} characters")
    
    # Generate chunked podcast with real audio
    print("\n🔊 Generating chunked audio (this may take 2-3 minutes)...")
    print("⏳ Please wait while we generate audio for each section...")
    
    start_time = time.time()
    result = generate_complete_chunked_podcast(script_content)
    generation_time = time.time() - start_time
    
    if not result["success"]:
        print(f"❌ Audio generation failed: {result.get('error')}")
        return
    
    print(f"✅ Audio generation completed in {generation_time:.1f} seconds!")
    
    # Extract results
    audio_bytes = result["audio_bytes"]
    timeline = result["timeline"]
    metadata = result["metadata"]
    
    # Display results
    print(f"\n📊 GENERATION RESULTS:")
    print(f"   Total sections: {metadata['total_sections']}")
    print(f"   Total duration: {metadata['total_duration_formatted']} ({metadata['total_duration_seconds']:.1f}s)")
    print(f"   Audio size: {metadata['audio_size_bytes'] / 1024 / 1024:.1f} MB")
    print(f"   Generation method: {metadata['generation_method']}")
    
    # Save audio file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"chunked_podcast_{timestamp}.wav"
    saved_file = save_audio_file(audio_bytes, audio_filename)
    
    if saved_file:
        print(f"🎵 You can play the audio file: {saved_file}")
    
    # Display timeline
    display_timeline(timeline)
    
    # Save timeline for reference
    timeline_filename = f"timeline_{timestamp}.json"
    try:
        with open(timeline_filename, 'w') as f:
            # Convert timeline to JSON-serializable format
            json_timeline = {}
            for time_range, info in timeline.items():
                json_timeline[time_range] = {
                    "section_name": info["section_name"],
                    "article_id": info["article_id"],
                    "start_seconds": info["start_seconds"],
                    "end_seconds": info["end_seconds"],
                    "duration_seconds": info["duration_seconds"],
                    "word_count": info["word_count"],
                    "content_preview": info["content_preview"]
                }
            
            json.dump(json_timeline, f, indent=2)
        print(f"💾 Timeline saved to: {timeline_filename}")
    except Exception as e:
        print(f"⚠️  Could not save timeline: {e}")
    
    # Start interactive testing
    interactive_timestamp_test(timeline)
    
    print("\n🎉 Testing completed!")
    print(f"📁 Files generated:")
    print(f"   Audio: {audio_filename}")
    print(f"   Timeline: {timeline_filename}")

if __name__ == "__main__":
    try:
        generate_audio_test()
    except KeyboardInterrupt:
        print("\n\n👋 Script interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc() 