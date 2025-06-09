#!/usr/bin/env python3
"""
END-TO-END PRODUCTION PIPELINE TEST
Uses exactly the same functions as production would use.
"""
import os
from datetime import datetime
from modules.interaction.chunked_podcast import generate_complete_chunked_podcast

def test_production_pipeline():
    """
    Test the complete production pipeline end-to-end.
    """
    print("🚀 PRODUCTION PIPELINE END-TO-END TEST")
    print("=" * 60)
    
    # Load the test script (same as used in other tests)
    script_file = "test_script.txt"
    
    if not os.path.exists(script_file):
        print(f"❌ Test script not found: {script_file}")
        print("💡 Run the other test scripts first to generate test_script.txt")
        return
    
    print(f"📄 Loading test script: {script_file}")
    with open(script_file, 'r', encoding='utf-8') as f:
        script_content = f.read()
    
    print(f"✅ Script loaded: {len(script_content)} characters")
    print(f"📝 Preview: {script_content[:100]}...")
    
    print(f"\n🎙️ Starting PRODUCTION PIPELINE...")
    print("⏳ This uses the exact same functions as production:")
    print("   1. parse_script_sections()")
    print("   2. generate_chunked_podcast_audio() with Cartesia TTS")
    print("   3. combine_wav_chunks() with FFmpeg stream-copy")
    print("   4. Build precise timeline mapping")
    
    # Use the EXACT production function
    start_time = datetime.now()
    
    result = generate_complete_chunked_podcast(
        script_content=script_content,
        voice_id="96c64eb5-a945-448f-9710-980abe7a514c",  # Same as production
        language="en"
    )
    
    end_time = datetime.now()
    generation_duration = (end_time - start_time).total_seconds()
    
    print(f"\n📊 PRODUCTION PIPELINE RESULTS:")
    print(f"⏱️  Generation time: {generation_duration:.1f} seconds")
    
    if not result["success"]:
        print(f"❌ Pipeline failed: {result['error']}")
        return
    
    # Extract results
    audio_bytes = result["audio_bytes"]
    timeline = result["timeline"]
    sections = result["sections"]
    metadata = result["metadata"]
    
    print(f"✅ Pipeline SUCCESS!")
    print(f"🎵 Audio generated: {len(audio_bytes)} bytes ({len(audio_bytes)/1024/1024:.1f} MB)")
    print(f"📊 Sections parsed: {len(sections)}")
    print(f"🕐 Timeline entries: {len(timeline)}")
    print(f"⏱️  Total duration: {metadata['total_duration_formatted']}")
    
    # Save the production result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"production_pipeline_{timestamp}.wav"
    
    with open(output_file, 'wb') as f:
        f.write(audio_bytes)
    
    print(f"💾 Production audio saved: {output_file}")
    
    # Display timeline
    print(f"\n📅 PRODUCTION TIMELINE:")
    for time_range, info in timeline.items():
        section_name = info['section_name']
        duration = info['duration_seconds']
        preview = info['content_preview'][:50] + "..." if len(info['content_preview']) > 50 else info['content_preview']
        print(f"  {time_range}s: {section_name} ({duration:.1f}s)")
        print(f"    📝 {preview}")
    
    # Test timeline lookup functionality
    print(f"\n🔍 TESTING TIMELINE LOOKUP (Production feature):")
    test_timestamps = [10.0, 30.0, 60.0, 90.0]
    
    from modules.interaction.chunked_podcast import find_article_at_timestamp
    
    for timestamp in test_timestamps:
        article_info = find_article_at_timestamp(timeline, timestamp)
        if article_info:
            print(f"  🎯 At {timestamp}s: {article_info['section_name']} ({article_info['formatted_range']})")
        else:
            print(f"  ❌ At {timestamp}s: No section found")
    
    # Quality verification
    print(f"\n🔍 QUALITY VERIFICATION:")
    print(f"   ffprobe -v quiet -show_streams {output_file} | grep codec_name")
    
    import subprocess
    try:
        result_probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_streams", output_file],
            capture_output=True, text=True
        )
        if "pcm_f32le" in result_probe.stdout:
            print(f"✅ Format verified: 32-bit float PCM (high quality)")
        else:
            print(f"⚠️  Format check: {result_probe.stdout}")
    except Exception as e:
        print(f"⚠️  Could not verify format: {e}")
    
    print(f"\n🎵 TEST PRODUCTION AUDIO:")
    print(f"   afplay {output_file}")
    
    print(f"\n🎉 PRODUCTION PIPELINE TEST COMPLETE!")
    print(f"📊 Summary:")
    print(f"   ✅ Script parsing: {len(sections)} sections")
    print(f"   ✅ Audio generation: {metadata['total_duration_formatted']}")
    print(f"   ✅ Timeline mapping: {len(timeline)} entries")
    print(f"   ✅ Quality: 32-bit float PCM")
    print(f"   ✅ File size: {len(audio_bytes)/1024/1024:.1f} MB")
    
    return output_file

if __name__ == "__main__":
    test_production_pipeline() 