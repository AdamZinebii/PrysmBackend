#!/usr/bin/env python3
"""
Direct ffmpeg concatenation - zero recompression, pure stream copy.
"""
import glob
import subprocess
from datetime import datetime

def ffmpeg_concat():
    print("🎯 FFMPEG DIRECT CONCATENATION - Zero recompression")
    
    # Get latest chunk files
    chunk_files = glob.glob("chunk_*20250606_112556.wav")
    chunk_files.sort()
    
    if len(chunk_files) != 5:
        print(f"❌ Expected 5 chunks, found {len(chunk_files)}")
        return
    
    print(f"✅ Found {len(chunk_files)} chunk files")
    for chunk_file in chunk_files:
        print(f"   📁 {chunk_file}")
    
    # Create ffmpeg concat file list
    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        for chunk_file in chunk_files:
            f.write(f"file '{chunk_file}'\n")
    
    print(f"📝 Created concat list: {concat_file}")
    
    # Output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ffmpeg_concat_{timestamp}.wav"
    
    # Run ffmpeg with stream copy (no recompression)
    cmd = [
        "ffmpeg",
        "-f", "concat",              # Use concat demuxer
        "-safe", "0",                # Allow unsafe paths
        "-i", concat_file,           # Input concat file
        "-c", "copy",                # Stream copy - NO recompression
        "-y",                        # Overwrite output
        output_file
    ]
    
    print(f"🔧 Running ffmpeg command:")
    print(f"   {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ FFmpeg concatenation successful!")
            print(f"📊 Result: {output_file}")
            
            # Check file size
            import os
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"   Size: {file_size_mb:.1f} MB")
            
            print(f"\n🎵 Test quality:")
            print(f"   afplay {output_file}")
            
            print(f"\n🔍 Verify format (should be identical to chunks):")
            print(f"   ffprobe -v quiet -show_streams {output_file} | grep codec_name")
            
        else:
            print(f"❌ FFmpeg failed:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error running ffmpeg: {e}")
    
    # Cleanup
    try:
        import os
        os.remove(concat_file)
        print(f"🗑️  Cleaned up {concat_file}")
    except:
        pass

if __name__ == "__main__":
    ffmpeg_concat() 