#!/usr/bin/env python3
"""
Simple script to concatenate existing chunk files.
"""
import os
import glob
from datetime import datetime
from pydub import AudioSegment

def concatenate_existing_chunks():
    """
    Find existing chunk files and concatenate them simply.
    """
    print("🔍 Looking for existing chunk files...")
    
    # Find all chunk files
    chunk_files = glob.glob("chunk_*.wav")
    chunk_files.sort()  # Sort by filename
    
    if not chunk_files:
        print("❌ No chunk files found!")
        return
    
    print(f"✅ Found {len(chunk_files)} chunk files:")
    for chunk_file in chunk_files:
        size_mb = os.path.getsize(chunk_file) / (1024 * 1024)
        print(f"   📁 {chunk_file} ({size_mb:.1f} MB)")
    
    print("\n🔧 Concatenating with pydub (SIMPLE method)...")
    
    # Load and concatenate
    combined = None
    for i, chunk_file in enumerate(chunk_files):
        print(f"📎 Adding {chunk_file} ({i+1}/{len(chunk_files)})")
        
        chunk_audio = AudioSegment.from_wav(chunk_file)
        
        if combined is None:
            combined = chunk_audio
        else:
            # Simple concatenation - no fancy stuff
            combined = combined + chunk_audio
    
    # Save result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"simple_concatenated_{timestamp}.wav"
    
    print(f"💾 Saving to {output_file}...")
    combined.export(output_file, format="wav")
    
    # Check result
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    duration_seconds = len(combined) / 1000
    
    print(f"✅ Concatenation complete!")
    print(f"📊 Result: {output_file}")
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"   Duration: {duration_seconds:.1f} seconds")
    
    # Test playback
    print(f"\n🎵 To test playback:")
    print(f"   afplay {output_file}")
    
    return output_file

if __name__ == "__main__":
    concatenate_existing_chunks() 