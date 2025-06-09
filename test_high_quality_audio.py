#!/usr/bin/env python3
"""
High Quality Audio Timeline Test
Generates premium quality audio with optimized settings.
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

def check_audio_dependencies():
    """Check if audio quality dependencies are available"""
    try:
        from pydub import AudioSegment
        print("✅ pydub available - high quality audio concatenation enabled")
        return True
    except ImportError:
        print("⚠️  pydub not available - installing...")
        os.system("pip install pydub")
        try:
            from pydub import AudioSegment
            print("✅ pydub installed successfully")
            return True
        except ImportError:
            print("❌ Could not install pydub - audio quality will be poor")
            return False

def load_test_script():
    """Load the test script content"""
    try:
        with open('modules/interaction/test_script.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("❌ Test script file not found")
        return None

def save_high_quality_audio(audio_bytes, filename_base="high_quality_podcast"):
    """Save audio with high quality settings"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_base}_{timestamp}.wav"
        
        # Save raw audio first
        with open(filename, 'wb') as f:
            f.write(audio_bytes)
        
        print(f"💾 High quality audio saved: {filename}")
        print(f"📊 Audio info:")
        print(f"   Size: {len(audio_bytes) / 1024 / 1024:.1f} MB")
        
        # Try to get audio info with pydub
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(filename)
            print(f"   Duration: {len(audio) / 1000:.1f} seconds")
            print(f"   Sample Rate: {audio.frame_rate} Hz")
            print(f"   Channels: {audio.channels}")
            print(f"   Sample Width: {audio.sample_width} bytes")
        except ImportError:
            print("   (Install pydub for detailed audio info)")
        
        return filename
    except Exception as e:
        print(f"❌ Error saving audio: {e}")
        return None

def analyze_audio_quality(timeline, audio_filename):
    """Analyze the audio quality and timing accuracy"""
    print("\n🔬 AUDIO QUALITY ANALYSIS")
    print("="*60)
    
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(audio_filename)
        
        total_duration = len(audio) / 1000  # Convert to seconds
        timeline_duration = max([info["end_seconds"] for info in timeline.values()])
        
        print(f"📊 Duration Analysis:")
        print(f"   Timeline duration: {timeline_duration:.1f}s")
        print(f"   Actual audio duration: {total_duration:.1f}s")
        print(f"   Difference: {abs(total_duration - timeline_duration):.1f}s")
        
        accuracy_percentage = (1 - abs(total_duration - timeline_duration) / timeline_duration) * 100
        print(f"   Timing accuracy: {accuracy_percentage:.1f}%")
        
        # Audio quality metrics
        print(f"\n🎵 Audio Quality:")
        print(f"   Sample rate: {audio.frame_rate} Hz {'✅' if audio.frame_rate >= 44100 else '⚠️'}")
        print(f"   Bit depth: {audio.sample_width * 8} bit {'✅' if audio.sample_width >= 4 else '⚠️'}")
        print(f"   Channels: {audio.channels} {'✅' if audio.channels == 1 else '⚠️'}")
        
        # Analyze each section boundary for quality
        print(f"\n🔍 Section Boundary Analysis:")
        for time_range, info in timeline.items():
            start_ms = int(info["start_seconds"] * 1000)
            end_ms = int(info["end_seconds"] * 1000)
            
            # Extract section audio
            try:
                section_audio = audio[start_ms:end_ms]
                max_volume = section_audio.max_dBFS
                
                status = "✅" if max_volume > -20 else "⚠️" if max_volume > -40 else "❌"
                print(f"   {status} {info['section_name']}: {max_volume:.1f} dBFS")
            except Exception as e:
                print(f"   ❌ {info['section_name']}: Analysis failed")
        
    except ImportError:
        print("⚠️  Install pydub for detailed audio analysis")
    except Exception as e:
        print(f"❌ Audio analysis failed: {e}")

def test_timestamp_precision(timeline, audio_filename):
    """Test the precision of timestamp detection"""
    print("\n🎯 TIMESTAMP PRECISION TEST")
    print("="*60)
    
    # Test timestamps at section boundaries
    boundary_tests = []
    
    for time_range, info in timeline.items():
        start_time = info["start_seconds"]
        end_time = info["end_seconds"]
        mid_time = (start_time + end_time) / 2
        
        # Test start, middle, and just before end
        test_points = [
            (start_time + 0.1, "start"),
            (mid_time, "middle"), 
            (end_time - 0.1, "end")
        ]
        
        for test_time, position in test_points:
            found_article = find_article_at_timestamp(timeline, test_time)
            expected_section = info["section_name"]
            
            if found_article and found_article["section_name"] == expected_section:
                status = "✅"
            else:
                status = "❌"
                
            boundary_tests.append({
                "timestamp": test_time,
                "position": position,
                "expected": expected_section,
                "found": found_article["section_name"] if found_article else "None",
                "status": status
            })
    
    # Show results
    correct_tests = sum(1 for test in boundary_tests if test["status"] == "✅")
    total_tests = len(boundary_tests)
    accuracy = (correct_tests / total_tests) * 100
    
    print(f"📈 Precision Results:")
    print(f"   Correct detections: {correct_tests}/{total_tests}")
    print(f"   Precision accuracy: {accuracy:.1f}%")
    
    if accuracy < 95:
        print(f"\n⚠️  Low precision detected:")
        failed_tests = [test for test in boundary_tests if test["status"] == "❌"]
        for test in failed_tests[:5]:  # Show first 5 failures
            print(f"   ❌ {format_timestamp_for_display(test['timestamp'])}: Expected {test['expected']}, got {test['found']}")

def interactive_quality_test(timeline, audio_filename):
    """Interactive testing with quality feedback"""
    print("\n🎮 INTERACTIVE QUALITY TEST")
    print("="*60)
    print("Commands:")
    print("  - Enter timestamp (e.g., 1:30, 45, 2:15.5)")
    print("  - 'timeline' - show timeline")
    print("  - 'quality' - run quality analysis")
    print("  - 'precision' - test precision")
    print("  - 'quit' - exit")
    print()
    
    while True:
        try:
            user_input = input("🎯 Enter command or timestamp: ").strip().lower()
            
            if user_input in ['quit', 'exit', 'q']:
                break
            elif user_input == 'timeline':
                display_timeline_compact(timeline)
                continue
            elif user_input == 'quality':
                analyze_audio_quality(timeline, audio_filename)
                continue
            elif user_input == 'precision':
                test_timestamp_precision(timeline, audio_filename)
                continue
            
            # Parse timestamp
            timestamp_seconds = parse_timestamp(user_input)
            if timestamp_seconds is None:
                continue
            
            # Find article at timestamp
            article_info = find_article_at_timestamp(timeline, timestamp_seconds)
            
            print(f"\n🔍 Results for {format_timestamp_for_display(timestamp_seconds)}:")
            print("-" * 50)
            
            if article_info:
                print(f"📍 Section: {article_info['section_name']}")
                print(f"🎵 Time Range: {article_info['formatted_range']}")
                print(f"🆔 Article ID: {article_info['article_id']}")
                print(f"📝 Content Preview:")
                print(f"   {article_info['content_preview']}")
                
                # Show quality info for this section
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_wav(audio_filename)
                    start_ms = int(article_info['start_seconds'] * 1000)
                    end_ms = int(article_info['end_seconds'] * 1000)
                    section_audio = audio[start_ms:end_ms]
                    
                    print(f"🎵 Section Quality:")
                    print(f"   Volume: {section_audio.max_dBFS:.1f} dBFS")
                    print(f"   Duration: {len(section_audio) / 1000:.1f}s")
                except ImportError:
                    print("🎵 (Install pydub for quality metrics)")
                
            else:
                print("❌ No article found at this timestamp")
                total_duration = max([info["end_seconds"] for info in timeline.values()])
                print(f"   Audio duration: {format_timestamp_for_display(total_duration)}")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def display_timeline_compact(timeline):
    """Display timeline in compact format"""
    print("\n📈 AUDIO TIMELINE:")
    for time_range, info in timeline.items():
        start_time = format_timestamp_for_display(info['start_seconds'])
        end_time = format_timestamp_for_display(info['end_seconds'])
        section_name = info['section_name']
        
        icon = "🎬" if section_name == "INTRO" else "🎭" if section_name == "CONCLUSION" else "📰"
        print(f"   {icon} {start_time}-{end_time}: {section_name}")

def parse_timestamp(timestamp_str):
    """Parse timestamp string to seconds"""
    try:
        if timestamp_str.replace('.', '').isdigit():
            return float(timestamp_str)
        
        if ':' in timestamp_str:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
        
        print(f"❌ Invalid format. Use: 30, 1:30, 2:45.5")
        return None
        
    except ValueError:
        print(f"❌ Invalid timestamp: {timestamp_str}")
        return None

def main():
    """Main high quality audio test"""
    print("🎙️ HIGH QUALITY AUDIO TIMELINE TEST")
    print("="*60)
    
    # Check dependencies
    if not check_audio_dependencies():
        print("⚠️  Proceeding with lower quality audio...")
    
    # Load test script
    print("\n📄 Loading test script...")
    script_content = load_test_script()
    if not script_content:
        return
    
    print(f"✅ Script loaded: {len(script_content)} characters")
    
    # Generate high quality audio
    print("\n🔊 Generating HIGH QUALITY chunked audio...")
    print("⏳ This will take 2-3 minutes for premium quality...")
    
    start_time = time.time()
    result = generate_complete_chunked_podcast(script_content)
    generation_time = time.time() - start_time
    
    if not result["success"]:
        print(f"❌ Audio generation failed: {result.get('error')}")
        return
    
    print(f"✅ High quality audio generated in {generation_time:.1f} seconds!")
    
    # Extract results
    audio_bytes = result["audio_bytes"]
    timeline = result["timeline"]
    metadata = result["metadata"]
    
    # Save high quality audio
    audio_filename = save_high_quality_audio(audio_bytes)
    if not audio_filename:
        return
    
    # Display results
    print(f"\n📊 GENERATION RESULTS:")
    print(f"   Total sections: {metadata['total_sections']}")
    print(f"   Total duration: {metadata['total_duration_formatted']}")
    print(f"   Audio size: {metadata['audio_size_bytes'] / 1024 / 1024:.1f} MB")
    print(f"   Method: {metadata['generation_method']}")
    
    # Quality analysis
    analyze_audio_quality(timeline, audio_filename)
    
    # Precision test
    test_timestamp_precision(timeline, audio_filename)
    
    # Interactive testing
    interactive_quality_test(timeline, audio_filename)
    
    print(f"\n🎉 High quality testing completed!")
    print(f"📁 Audio file: {audio_filename}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Script interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc() 