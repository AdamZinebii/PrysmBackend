#!/usr/bin/env python3
"""
Interactive Timestamp Testing Script

This script generates a chunked podcast from the test script and provides
an interactive interface to test timestamp accuracy and section mapping.
"""

import os
import sys
import time
import datetime
from typing import List, Dict, Any, Optional

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from modules.interaction.chunked_podcast import (
    generate_complete_chunked_podcast,
    find_article_at_timestamp,
    format_timestamp_for_display
)

class InteractiveTimestampTester:
    def __init__(self, script_file: str = "test_script.txt"):
        self.script_file = script_file
        self.result = None
        self.timeline = {}
        self.total_duration = 0
        
    def load_and_generate(self):
        """Load script and generate chunked audio"""
        print("🎙️  Interactive Timestamp Tester")
        print("=" * 50)
        
        # Load script
        script_path = os.path.join(os.path.dirname(__file__), self.script_file)
        print(f"📄 Loading script: {script_path}")
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Generate complete chunked podcast
        print("\n🎵 Generating chunked podcast...")
        print("   This may take a few minutes...")
        
        start_time = time.time()
        self.result = generate_complete_chunked_podcast(content)
        generation_time = time.time() - start_time
        
        if not self.result["success"]:
            print(f"❌ Generation failed: {self.result['error']}")
            return False
        
        self.timeline = self.result["timeline"]
        self.total_duration = self.result["metadata"]["total_duration_seconds"]
        
        print(f"✅ Audio generated in {generation_time:.1f}s")
        print(f"   Duration: {self.total_duration:.2f}s ({self.total_duration/60:.1f}m)")
        print(f"   Sections: {self.result['metadata']['total_sections']}")
        print(f"   Audio size: {self.result['metadata']['audio_size_bytes']} bytes")
        
        # Save audio file for reference
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"interactive_test_{timestamp}.wav"
        with open(audio_filename, 'wb') as f:
            f.write(self.result["audio_bytes"])
        print(f"   Saved: {audio_filename}")
        
        # Show timeline
        self.show_timeline()
        return True
        
    def show_timeline(self):
        """Display the complete timeline"""
        print("\n📊 TIMELINE")
        print("-" * 80)
        print(f"{'Time Range':<15} {'Duration':<8} {'Section':<20} {'Preview'}")
        print("-" * 80)
        
        for time_range, section_info in self.timeline.items():
            start_time = section_info["start_seconds"]
            end_time = section_info["end_seconds"]
            duration = end_time - start_time
            
            formatted_range = f"{format_timestamp_for_display(start_time)}-{format_timestamp_for_display(end_time)}"
            section_name = section_info["section_name"]
            preview = section_info["content_preview"][:40] + "..." if len(section_info["content_preview"]) > 40 else section_info["content_preview"]
            
            print(f"{formatted_range:<15} {duration:>7.1f}s {section_name:<20} {preview}")
        
        print("-" * 80)
        print(f"Total Duration: {format_timestamp_for_display(self.total_duration)}")
    
    def test_timestamp(self, timestamp: float):
        """Test a specific timestamp"""
        if timestamp < 0 or timestamp > self.total_duration:
            print(f"❌ Timestamp {timestamp:.1f}s is out of range (0-{self.total_duration:.1f}s)")
            return
            
        # Get section at timestamp
        section_info = find_article_at_timestamp(self.timeline, timestamp)
        
        if section_info:
            print(f"\n🎯 TIMESTAMP: {timestamp:.1f}s ({format_timestamp_for_display(timestamp)})")
            print(f"📍 Section: {section_info['section_name']}")
            print(f"⏰ Section Range: {section_info['formatted_range']}")
            print(f"📝 Content Preview: {section_info['content_preview']}")
            print(f"🔗 Article ID: {section_info['article_id']}")
            print(f"📏 Time Range: {section_info['time_range']}")
        else:
            print(f"❌ No section found at timestamp {timestamp:.1f}s")
    
    def run_interactive_mode(self):
        """Run interactive testing mode"""
        if not self.result or not self.result["success"]:
            print("❌ No audio generated yet or generation failed.")
            return
            
        print("\n🎮 INTERACTIVE MODE")
        print("Commands:")
        print("  <number>     - Test timestamp (e.g., 45.5)")
        print("  timeline     - Show timeline again")
        print("  random       - Test random timestamps")
        print("  sections     - Test section boundaries")
        print("  info         - Show generation info")
        print("  quit         - Exit")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n> ").strip().lower()
                
                if user_input in ['quit', 'exit', 'q']:
                    break
                elif user_input == 'timeline':
                    self.show_timeline()
                elif user_input == 'random':
                    self.test_random_timestamps()
                elif user_input == 'sections':
                    self.test_section_boundaries()
                elif user_input == 'info':
                    self.show_generation_info()
                else:
                    # Try to parse as timestamp
                    try:
                        timestamp = float(user_input)
                        self.test_timestamp(timestamp)
                    except ValueError:
                        print("❌ Invalid command. Enter a number (timestamp) or a command.")
                        
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                break
    
    def test_random_timestamps(self, count: int = 5):
        """Test random timestamps"""
        import random
        
        print(f"\n🎲 Testing {count} random timestamps:")
        for i in range(count):
            timestamp = random.uniform(0, self.total_duration)
            print(f"\n--- Random Test {i+1} ---")
            self.test_timestamp(timestamp)
    
    def test_section_boundaries(self):
        """Test timestamps at section boundaries"""
        print("\n🔍 Testing section boundaries:")
        
        for i, (time_range, section_info) in enumerate(self.timeline.items()):
            start_time = section_info["start_seconds"]
            end_time = section_info["end_seconds"]
            
            print(f"\n--- Section {i+1}: {section_info['section_name']} ---")
            
            # Test start of section
            print(f"🟢 Start ({start_time:.1f}s):")
            self.test_timestamp(start_time)
            
            # Test middle of section
            mid_time = (start_time + end_time) / 2
            print(f"🟡 Middle ({mid_time:.1f}s):")
            self.test_timestamp(mid_time)
            
            # Test just before end
            end_test = max(start_time, end_time - 0.1)
            print(f"🟠 Near End ({end_test:.1f}s):")
            self.test_timestamp(end_test)
    
    def show_generation_info(self):
        """Show detailed generation information"""
        if not self.result:
            print("❌ No generation data available")
            return
            
        metadata = self.result["metadata"]
        print("\n📊 GENERATION INFO")
        print("-" * 40)
        print(f"Total Sections: {metadata['total_sections']}")
        print(f"Total Duration: {metadata['total_duration_formatted']} ({metadata['total_duration_seconds']:.2f}s)")
        print(f"Voice ID: {metadata['voice_id']}")
        print(f"Language: {metadata['language']}")
        print(f"Audio Size: {metadata['audio_size_bytes']:,} bytes")
        print(f"Method: {metadata['generation_method']}")
        print(f"Generated: {self.result['generation_timestamp']}")

def main():
    """Main function to run the interactive tester"""
    tester = InteractiveTimestampTester()
    
    print("Starting Interactive Timestamp Tester...")
    print("This will generate audio and test timestamp accuracy.\n")
    
    # Generate audio
    if tester.load_and_generate():
        # Start interactive mode
        tester.run_interactive_mode()
    else:
        print("❌ Failed to generate audio. Exiting.")

if __name__ == "__main__":
    main() 