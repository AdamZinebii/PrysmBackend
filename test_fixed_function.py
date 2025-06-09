#!/usr/bin/env python3
"""
Quick test of the fixed combine_wav_chunks function.
"""
import glob
from datetime import datetime
from modules.interaction.chunked_podcast import combine_wav_chunks

def test_fixed_function():
    print("🧪 Testing fixed combine_wav_chunks function...")
    
    # Get latest chunk files
    chunk_files = glob.glob("chunk_*20250606_112556.wav")
    chunk_files.sort()
    
    if len(chunk_files) != 5:
        print(f"❌ Expected 5 chunks, found {len(chunk_files)}")
        return
    
    print(f"✅ Found {len(chunk_files)} chunk files from latest generation")
    
    # Read chunk files into bytes
    audio_chunks = []
    for chunk_file in chunk_files:
        with open(chunk_file, 'rb') as f:
            audio_chunks.append(f.read())
        print(f"📁 Loaded {chunk_file}")
    
    # Test our fixed function
    print("\n🔧 Testing fixed combine_wav_chunks function...")
    combined_audio = combine_wav_chunks(audio_chunks)
    
    if not combined_audio:
        print("❌ Function returned empty audio!")
        return
    
    # Save result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"fixed_function_test_{timestamp}.wav"
    
    with open(output_file, 'wb') as f:
        f.write(combined_audio)
    
    file_size_mb = len(combined_audio) / (1024 * 1024)
    
    print(f"✅ Fixed function test complete!")
    print(f"📊 Result: {output_file}")
    print(f"   Size: {file_size_mb:.1f} MB")
    
    print(f"\n🎵 To test quality:")
    print(f"   afplay {output_file}")

if __name__ == "__main__":
    test_fixed_function() 