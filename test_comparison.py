#!/usr/bin/env python3
"""
Comparison test: Direct pydub vs Function-based approach
"""
import glob
import io
from datetime import datetime
from pydub import AudioSegment

def method_1_direct_from_files():
    """Method 1: Direct from files (like our working test script)"""
    print("🧪 METHOD 1: Direct from files (working method)")
    
    chunk_files = glob.glob("chunk_*20250606_112556.wav")
    chunk_files.sort()
    
    combined = None
    for i, chunk_file in enumerate(chunk_files):
        print(f"📎 Adding {chunk_file} ({i+1}/{len(chunk_files)})")
        
        # Load directly from file
        audio_segment = AudioSegment.from_wav(chunk_file)
        
        if combined is None:
            combined = audio_segment
        else:
            combined = combined + audio_segment
    
    # Save result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"method1_direct_{timestamp}.wav"
    combined.export(output_file, format="wav")
    
    file_size_mb = len(combined.raw_data) / (1024 * 1024)
    print(f"✅ Method 1 complete: {output_file} ({file_size_mb:.1f} MB)")
    
    return output_file, combined

def method_2_from_bytes():
    """Method 2: From bytes in memory (like our function)"""
    print("\n🧪 METHOD 2: From bytes in memory (function method)")
    
    chunk_files = glob.glob("chunk_*20250606_112556.wav")
    chunk_files.sort()
    
    # Load files into bytes first (like our function does)
    audio_chunks = []
    for chunk_file in chunk_files:
        with open(chunk_file, 'rb') as f:
            audio_chunks.append(f.read())
    
    combined = None
    for i, chunk_bytes in enumerate(audio_chunks):
        print(f"📎 Adding chunk {i+1}/{len(audio_chunks)} from bytes")
        
        # Load from bytes (like our function)
        chunk_io = io.BytesIO(chunk_bytes)
        audio_segment = AudioSegment.from_wav(chunk_io)
        
        if combined is None:
            combined = audio_segment
        else:
            combined = combined + audio_segment
    
    # Save result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"method2_bytes_{timestamp}.wav"
    combined.export(output_file, format="wav")
    
    file_size_mb = len(combined.raw_data) / (1024 * 1024)
    print(f"✅ Method 2 complete: {output_file} ({file_size_mb:.1f} MB)")
    
    return output_file, combined

def compare_methods():
    """Compare both methods"""
    print("🔍 COMPARING TWO METHODS\n")
    
    # Test both methods
    file1, combined1 = method_1_direct_from_files()
    file2, combined2 = method_2_from_bytes()
    
    # Compare properties
    print(f"\n📊 COMPARISON:")
    print(f"Method 1 (direct): {len(combined1)} ms, {combined1.frame_rate} Hz, {combined1.channels} ch")
    print(f"Method 2 (bytes):  {len(combined2)} ms, {combined2.frame_rate} Hz, {combined2.channels} ch")
    
    print(f"\n🎵 Test both files:")
    print(f"   afplay {file1}")
    print(f"   afplay {file2}")
    
    # Check if they're identical
    if combined1.raw_data == combined2.raw_data:
        print("✅ Raw audio data is IDENTICAL")
    else:
        print("❌ Raw audio data is DIFFERENT!")
        print(f"   Method 1 raw data: {len(combined1.raw_data)} bytes")
        print(f"   Method 2 raw data: {len(combined2.raw_data)} bytes")

if __name__ == "__main__":
    compare_methods() 