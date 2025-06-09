#!/usr/bin/env python3
"""
Simple script to concatenate LATEST chunk files from one generation.
"""
import os
import glob
from datetime import datetime
from pydub import AudioSegment

def get_latest_chunk_set():
    """
    Find the latest set of chunks (from same timestamp).
    """
    print("🔍 Looking for chunk files...")
    
    # Find all chunk files
    chunk_files = glob.glob("chunk_*.wav")
    
    if not chunk_files:
        print("❌ No chunk files found!")
        return []
    
    # Group by timestamp (extract timestamp from filename)
    timestamp_groups = {}
    for chunk_file in chunk_files:
        # Extract timestamp from filename like "chunk_01_INTRO_20250606_111911.wav"
        parts = chunk_file.split('_')
        if len(parts) >= 4:
            timestamp = parts[-2] + '_' + parts[-1].replace('.wav', '')
            if timestamp not in timestamp_groups:
                timestamp_groups[timestamp] = []
            timestamp_groups[timestamp].append(chunk_file)
    
    # Find the latest timestamp
    latest_timestamp = max(timestamp_groups.keys())
    latest_chunks = timestamp_groups[latest_timestamp]
    latest_chunks.sort()  # Sort by chunk number
    
    print(f"✅ Latest chunk set (timestamp: {latest_timestamp}):")
    for chunk_file in latest_chunks:
        size_mb = os.path.getsize(chunk_file) / (1024 * 1024)
        print(f"   📁 {chunk_file} ({size_mb:.1f} MB)")
    
    return latest_chunks

def concatenate_chunks(chunk_files):
    """
    Concatenate chunk files with pydub.
    """
    if not chunk_files:
        return None
    
    print(f"\n🔧 Concatenating {len(chunk_files)} chunks with pydub (SIMPLE method)...")
    
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
    
    return combined

def main():
    # Get latest chunk set
    chunk_files = get_latest_chunk_set()
    if not chunk_files:
        return
    
    # Concatenate
    combined = concatenate_chunks(chunk_files)
    if not combined:
        print("❌ Failed to concatenate!")
        return
    
    # Save result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"latest_concatenated_{timestamp}.wav"
    
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
    print(f"\n🎵 To test quality:")
    print(f"   afplay {output_file}")
    
    return output_file

if __name__ == "__main__":
    main() 