#!/usr/bin/env python3
"""
Fix timeline using existing audio files with correct durations
"""

import json
import subprocess
import os
import sys
from typing import Dict, Any

def get_audio_duration_ffprobe(filepath: str) -> float:
    """Get audio duration using ffprobe"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', 
            '-show_entries', 'format=duration', 
            '-of', 'csv=p=0', 
            filepath
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            print(f"❌ ffprobe failed for {filepath}")
            return 0.0
    except Exception as e:
        print(f"❌ Error getting duration for {filepath}: {e}")
        return 0.0

def rebuild_timeline():
    """Rebuild timeline with correct durations"""
    
    # Find existing chunks (latest timestamp)
    chunk_files = [f for f in os.listdir('.') if f.startswith('chunk_') and f.endswith('.wav')]
    
    if not chunk_files:
        print("❌ No chunk files found")
        return
    
    # Group by timestamp
    timestamps = {}
    for f in chunk_files:
        parts = f.split('_')
        if len(parts) >= 4:
            timestamp = '_'.join(parts[-2:]).replace('.wav', '')
            if timestamp not in timestamps:
                timestamps[timestamp] = []
            timestamps[timestamp].append(f)
    
    # Use latest timestamp
    latest_timestamp = sorted(timestamps.keys())[-1]
    latest_chunks = timestamps[latest_timestamp]
    
    print(f"🎯 Using chunks from: {latest_timestamp}")
    print(f"   Found {len(latest_chunks)} chunks")
    
    # Sort chunks by number
    latest_chunks.sort(key=lambda x: int(x.split('_')[1]))
    
    # Load original timeline to get section info
    timeline_files = [f for f in os.listdir('.') if f.startswith('timeline_') and f.endswith('.json')]
    if not timeline_files:
        print("❌ No timeline file found")
        return
        
    with open(sorted(timeline_files)[-1], 'r') as f:
        old_timeline = json.load(f)
    
    # Extract section info from old timeline (preserving order)
    sections_info = []
    for key in sorted(old_timeline.keys(), key=lambda x: float(x.split('-')[0])):
        sections_info.append(old_timeline[key])
    
    # Build new timeline with correct durations
    new_timeline = {}
    current_time = 0.0
    
    for i, chunk_file in enumerate(latest_chunks):
        print(f"📊 Processing {chunk_file}...")
        
        # Get real duration
        duration = get_audio_duration_ffprobe(chunk_file)
        end_time = current_time + duration
        
        # Get section info (match by index)
        if i < len(sections_info):
            section_info = sections_info[i].copy()
        else:
            section_info = {
                "section_name": f"Section_{i+1}",
                "article_id": None,
                "content_preview": "Unknown section",
                "word_count": 0
            }
        
        # Update with correct times
        section_info.update({
            "start_seconds": current_time, 
            "end_seconds": end_time,
            "duration_seconds": duration,
            "chunk_file": chunk_file
        })
        
        # Create timeline key
        timeline_key = f"{current_time:.1f}-{end_time:.1f}"
        new_timeline[timeline_key] = section_info
        
        print(f"   ✅ {section_info['section_name']}: {duration:.1f}s ({timeline_key})")
        
        current_time = end_time
    
    # Save corrected timeline
    corrected_filename = f"corrected_timeline_{latest_timestamp}.json"
    with open(corrected_filename, 'w') as f:
        json.dump(new_timeline, f, indent=2)
    
    print(f"\n🎉 Timeline corrigé sauvegardé: {corrected_filename}")
    print(f"   Durée totale: {current_time:.1f}s ({current_time/60:.1f}min)")
    print(f"   Sections: {len(new_timeline)}")
    
    return new_timeline, corrected_filename

def test_corrected_timeline(timeline: Dict[str, Any]):
    """Test the corrected timeline"""
    print(f"\n🧪 TEST DU TIMELINE CORRIGÉ")
    print("-" * 60)
    
    # Add modules to path for testing
    sys.path.append('modules')
    from modules.interaction.chunked_podcast import find_article_at_timestamp
    
    total_duration = max([info['end_seconds'] for info in timeline.values()])
    
    # Test some timestamps
    test_timestamps = [0, 5, 15, 30, 50, 70, total_duration - 5]
    
    for ts in test_timestamps:
        if ts <= total_duration:
            result = find_article_at_timestamp(timeline, ts)
            if result:
                print(f"{ts:5.1f}s -> {result['section_name']:<15} ({result['formatted_range']})")
            else:
                print(f"{ts:5.1f}s -> ❌ Not found")
                
    print(f"\n✅ Test terminé. Total: {total_duration:.1f}s")

def main():
    print("🔧 CORRECTION DU TIMELINE AVEC FICHIERS EXISTANTS")
    print("=" * 55)
    
    timeline, filename = rebuild_timeline()
    if timeline:
        test_corrected_timeline(timeline)
        print(f"\n💡 Pour tester interactivement:")
        print(f"   python -c \"exec(open('test_corrected_timeline.py').read())\"")

if __name__ == "__main__":
    main() 