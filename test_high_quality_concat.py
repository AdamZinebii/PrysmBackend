#!/usr/bin/env python3
"""
High quality concatenation that preserves the exact format.
"""
import glob
from datetime import datetime
from pydub import AudioSegment

def high_quality_concat():
    print("🎯 HIGH QUALITY CONCATENATION - Preserving 32-bit float format")
    
    # Get latest chunk files
    chunk_files = glob.glob("chunk_*20250606_112556.wav")
    chunk_files.sort()
    
    print(f"✅ Found {len(chunk_files)} chunk files")
    
    combined = None
    for i, chunk_file in enumerate(chunk_files):
        print(f"📎 Adding {chunk_file} ({i+1}/{len(chunk_files)})")
        
        # Load with specific format preservation
        audio_segment = AudioSegment.from_wav(chunk_file)
        
        # Log original format
        print(f"   Format: {audio_segment.sample_width} bytes/sample, {audio_segment.frame_rate}Hz, {audio_segment.channels}ch")
        
        if combined is None:
            combined = audio_segment
        else:
            combined = combined + audio_segment
    
    # Save with explicit 32-bit float format
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"hq_float32_{timestamp}.wav"
    
    print(f"💾 Exporting with 32-bit float format...")
    
    # Export with explicit float32 format
    combined.export(
        output_file, 
        format="wav",
        codec="pcm_f32le",  # Force 32-bit float little-endian
        parameters=[
            "-acodec", "pcm_f32le",  # 32-bit float codec
            "-ar", str(combined.frame_rate),  # Preserve sample rate
            "-ac", str(combined.channels)     # Preserve channels
        ]
    )
    
    file_size_mb = len(combined.raw_data) / (1024 * 1024)
    duration_seconds = len(combined) / 1000
    
    print(f"✅ High quality export complete!")
    print(f"📊 Result: {output_file}")
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"   Duration: {duration_seconds:.1f} seconds")
    
    print(f"\n🎵 Test quality:")
    print(f"   afplay {output_file}")
    
    print(f"\n🔍 Verify format:")
    print(f"   ffprobe -v quiet -show_streams {output_file} | grep codec_name")

if __name__ == "__main__":
    high_quality_concat() 