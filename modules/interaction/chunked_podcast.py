#!/usr/bin/env python3
"""
Chunked Podcast Generation Module
Generates podcasts section by section for precise timestamp mapping.
"""

import logging
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Tuple
import io

# Audio processing imports
try:
    import wave
    import struct
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

from modules.audio.cartesia import generate_text_to_speech

logger = logging.getLogger(__name__)

def parse_script_sections(script_content: str) -> Dict[str, str]:
    """
    Parse podcast script to extract sections based on markers.
    
    Args:
        script_content (str): Full podcast script with <<articlelink>> markers
        
    Returns:
        Dict[str, str]: Dictionary mapping section names to content
    """
    try:
        sections = {}
        
        # Split script by sections using regex
        # Look for patterns like "INTRO:", "<<articlelink1>>:", "CONCLUSION:"
        section_pattern = r'^(INTRO:|<<[^>]+>>:|CONCLUSION:)\s*\n'
        
        # Split the script at section headers
        parts = re.split(section_pattern, script_content, flags=re.MULTILINE)
        
        # Process parts (every odd index is a header, every even index is content)
        current_section = "INTRO"
        for i in range(len(parts)):
            if i == 0:
                # First part might be content before any header
                if parts[i].strip():
                    sections["INTRO"] = parts[i].strip()
            elif i % 2 == 1:
                # This is a section header
                header = parts[i].strip().rstrip(':')
                current_section = header
            elif i % 2 == 0:
                # This is section content
                if current_section and parts[i].strip():
                    sections[current_section] = parts[i].strip()
        
        # If no sections found, treat entire script as one section
        if not sections:
            sections["FULL_SCRIPT"] = script_content
            
        logger.info(f"✅ Parsed {len(sections)} sections from script")
        return sections
        
    except Exception as e:
        logger.error(f"Error parsing script sections: {e}")
        return {"FULL_SCRIPT": script_content}

def estimate_word_duration(text: str, words_per_minute: int = 150) -> float:
    """
    Estimate duration of text in seconds based on word count.
    
    Args:
        text (str): Text to estimate
        words_per_minute (int): Speaking rate
        
    Returns:
        float: Estimated duration in seconds
    """
    word_count = len(text.split())
    duration_minutes = word_count / words_per_minute
    return duration_minutes * 60  # Convert to seconds

def get_wav_duration_from_bytes(audio_bytes: bytes) -> float:
    """
    Get duration of WAV audio from bytes by parsing WAV header.
    
    Args:
        audio_bytes (bytes): WAV audio data
        
    Returns:
        float: Duration in seconds
    """
    try:
        # Parse WAV header manually for precise duration
        if len(audio_bytes) < 44:
            logger.error("WAV file too small")
            return 1.0
        
        # WAV header structure:
        # Bytes 0-3: "RIFF"
        # Bytes 4-7: File size - 8
        # Bytes 8-11: "WAVE"
        # Bytes 12-15: "fmt "
        # Bytes 16-19: Format chunk size
        # Bytes 20-21: Audio format
        # Bytes 22-23: Number of channels
        # Bytes 24-27: Sample rate
        # Bytes 28-31: Byte rate
        # Bytes 32-33: Block align
        # Bytes 34-35: Bits per sample
        
        # Check if it's a valid WAV file
        if audio_bytes[:4] != b'RIFF' or audio_bytes[8:12] != b'WAVE':
            logger.error("Not a valid WAV file")
            return estimate_duration_by_size(audio_bytes)
        
        # Extract sample rate (bytes 24-27, little endian)
        sample_rate = int.from_bytes(audio_bytes[24:28], 'little')
        
        # Extract number of channels (bytes 22-23, little endian)
        channels = int.from_bytes(audio_bytes[22:24], 'little')
        
        # Extract bits per sample (bytes 34-35, little endian)
        bits_per_sample = int.from_bytes(audio_bytes[34:36], 'little')
        
        # Find data chunk
        data_chunk_start = None
        pos = 12  # Start after "WAVE"
        
        while pos < len(audio_bytes) - 8:
            chunk_id = audio_bytes[pos:pos+4]
            chunk_size = int.from_bytes(audio_bytes[pos+4:pos+8], 'little')
            
            if chunk_id == b'data':
                data_chunk_start = pos + 8
                data_size = chunk_size
                break
            
            pos += 8 + chunk_size
        
        if data_chunk_start is None:
            logger.error("No data chunk found in WAV")
            return estimate_duration_by_size(audio_bytes)
        
        # Calculate duration: data_size / (sample_rate * channels * (bits_per_sample / 8))
        bytes_per_sample = bits_per_sample // 8
        bytes_per_second = sample_rate * channels * bytes_per_sample
        
        if bytes_per_second > 0:
            duration = data_size / bytes_per_second
            logger.info(f"📊 WAV duration calculated: {duration:.2f}s (size={data_size}, rate={sample_rate})")
            return duration
        else:
            return estimate_duration_by_size(audio_bytes)
            
    except Exception as e:
        logger.error(f"Error parsing WAV duration: {e}")
        return estimate_duration_by_size(audio_bytes)

def estimate_duration_by_size(audio_bytes: bytes) -> float:
    """
    Fallback: estimate duration based on file size for WAV.
    WAV at 44.1kHz, 32-bit float, mono ≈ 176,400 bytes/second
    """
    estimated_duration = len(audio_bytes) / 176400
    return max(1.0, estimated_duration)



def generate_chunked_podcast_audio(
    sections: Dict[str, str], 
    voice_id: str = "96c64eb5-a945-448f-9710-980abe7a514c",
    language: str = "en",
    save_chunks: bool = True
) -> Tuple[bytes, Dict[str, Dict]]:
    """
    Generate audio for each section and create precise timeline mapping.
    
    Args:
        sections (Dict[str, str]): Script sections from parse_script_sections
        voice_id (str): Cartesia voice ID
        language (str): Language code
        save_chunks (bool): Whether to save individual chunks for quality analysis
        
    Returns:
        Tuple[bytes, Dict]: (combined_audio_bytes, timeline_mapping)
    """
    try:
        logger.info(f"🔊 Starting chunked audio generation for {len(sections)} sections")
        
        timeline = {}
        audio_chunks = []
        chunk_files = []
        current_timestamp = 0.0
        
        # Create timestamp for unique file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, (section_name, content) in enumerate(sections.items()):
            logger.info(f"🎙️ Generating audio for section {i+1}/{len(sections)}: {section_name}")
            
            # Generate audio for this section (Cartesia returns WAV)
            section_audio = generate_text_to_speech(
                text=content,
                voice_id=voice_id,
                language=language,
                model_id="sonic-2"
            )
            
            if not section_audio:
                logger.error(f"❌ Failed to generate audio for section: {section_name}")
                continue
            
            # Save individual chunk for quality analysis
            if save_chunks:
                safe_section_name = section_name.replace('<<', '').replace('>>', '').replace(':', '')
                chunk_filename = f"chunk_{i+1:02d}_{safe_section_name}_{timestamp}.wav"
                chunk_path = os.path.join(os.getcwd(), chunk_filename)
                
                with open(chunk_path, 'wb') as f:
                    f.write(section_audio)
                chunk_files.append(chunk_path)
                logger.info(f"💾 Saved individual chunk: {chunk_filename}")
            
            # Get precise duration of this WAV audio chunk
            section_duration = get_wav_duration_from_bytes(section_audio)
            
            # Calculate end timestamp
            end_timestamp = current_timestamp + section_duration
            
            # Create timeline entry
            timeline_key = f"{current_timestamp:.1f}-{end_timestamp:.1f}"
            timeline[timeline_key] = {
                "section_name": section_name,
                "article_id": section_name if section_name.startswith("<<") else None,
                "start_seconds": current_timestamp,
                "end_seconds": end_timestamp,
                "duration_seconds": section_duration,
                "word_count": len(content.split()),
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "chunk_file": chunk_files[-1] if save_chunks and chunk_files else None
            }
            
            # Store audio chunk
            audio_chunks.append(section_audio)
            
            # Update current timestamp
            current_timestamp = end_timestamp
            
            logger.info(f"✅ Section '{section_name}': {section_duration:.1f}s ({timeline_key})")
        
        # Combine all audio chunks
        logger.info("🔧 Combining WAV audio chunks...")
        combined_audio = combine_wav_chunks(audio_chunks)
        
        total_duration = current_timestamp
        logger.info(f"🎉 Chunked podcast generated: {total_duration:.1f}s total, {len(timeline)} sections")
        
        if save_chunks:
            logger.info(f"💾 Individual chunks saved: {len(chunk_files)} files")
            for chunk_file in chunk_files:
                logger.info(f"   📁 {os.path.basename(chunk_file)}")
        
        return combined_audio, timeline
        
    except Exception as e:
        logger.error(f"Error in chunked podcast generation: {e}")
        return b"", {}

def combine_wav_chunks(audio_chunks: List[bytes]) -> bytes:
    """
    HIGH-QUALITY concatenation using ffmpeg with stream copy (zero recompression).
    
    Args:
        audio_chunks (List[bytes]): List of WAV audio byte arrays
        
    Returns:
        bytes: Combined WAV audio
    """
    try:
        if not audio_chunks:
            return b""
        
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        
        logger.info(f"🎯 FFMPEG STREAM-COPY concatenation for {len(audio_chunks)} chunks")
        
        import subprocess
        import tempfile
        
        # Create temporary directory for chunk files
        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_files = []
            
            # Write each chunk to a temporary file
            for i, chunk in enumerate(audio_chunks):
                chunk_file = os.path.join(temp_dir, f"chunk_{i:03d}.wav")
                with open(chunk_file, 'wb') as f:
                    f.write(chunk)
                chunk_files.append(chunk_file)
                logger.info(f"📁 Created temp chunk: {os.path.basename(chunk_file)}")
            
            # Create ffmpeg concat list file
            concat_list_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_file, 'w') as f:
                for chunk_file in chunk_files:
                    f.write(f"file '{chunk_file}'\n")
            
            # Output file
            output_file = os.path.join(temp_dir, "combined.wav")
            
            # Run ffmpeg with stream copy (preserves quality)
            cmd = [
                "ffmpeg",
                "-f", "concat",              # Use concat demuxer
                "-safe", "0",                # Allow unsafe paths
                "-i", concat_list_file,      # Input concat file
                "-c", "copy",                # Stream copy - NO recompression
                "-y",                        # Overwrite output
                output_file
            ]
            
            logger.info("🔧 Running ffmpeg stream-copy concatenation...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ FFmpeg failed: {result.stderr}")
                # Fallback to manual concatenation
                return manual_wav_concat(audio_chunks)
            
            # Read the combined result
            with open(output_file, 'rb') as f:
                combined_audio = f.read()
            
            logger.info(f"✅ FFMPEG concatenation complete: {len(combined_audio)} bytes")
            return combined_audio
        
    except Exception as e:
        logger.error(f"Error in ffmpeg concatenation: {e}")
        logger.info("🔄 Falling back to manual concatenation...")
        return manual_wav_concat(audio_chunks)

def combine_with_wave_library(audio_chunks: List[bytes]) -> bytes:
    """
    Fallback combination using only wave library (lower quality).
    """
    try:
        if not AUDIO_AVAILABLE:
            logger.warning("Audio libraries not available, using manual concat")
            return manual_wav_concat(audio_chunks)
        
        combined_frames = []
        sample_rate = None
        sample_width = None
        channels = None
        
        for chunk in audio_chunks:
            chunk_io = io.BytesIO(chunk)
            
            with wave.open(chunk_io, 'rb') as wav:
                # Get audio parameters from first chunk
                if sample_rate is None:
                    sample_rate = wav.getframerate()
                    sample_width = wav.getsampwidth()
                    channels = wav.getnchannels()
                
                # Read all frames from this chunk
                frames = wav.readframes(wav.getnframes())
                combined_frames.append(frames)
        
        # Create combined WAV
        output_io = io.BytesIO()
        
        with wave.open(output_io, 'wb') as combined_wav:
            combined_wav.setnchannels(channels)
            combined_wav.setsampwidth(sample_width)
            combined_wav.setframerate(sample_rate)
            
            # Write all frames
            for frames in combined_frames:
                combined_wav.writeframes(frames)
        
        return output_io.getvalue()
        
    except Exception as e:
        logger.error(f"Error combining audio chunks with wave library: {e}")
        return manual_wav_concat(audio_chunks)



def manual_wav_concat(audio_chunks: List[bytes]) -> bytes:
    """
    Manual WAV concatenation by combining audio data sections.
    
    Args:
        audio_chunks (List[bytes]): List of WAV chunks
        
    Returns:
        bytes: Concatenated WAV
    """
    try:
        if not audio_chunks:
            return b""
        
        # Use first chunk as template for header
        first_chunk = audio_chunks[0]
        if len(first_chunk) < 44:
            return first_chunk
        
        # Extract header info from first chunk
        header = first_chunk[:44]  # Standard WAV header is 44 bytes
        
        # Find data section start in first chunk
        data_start = 44
        pos = 12
        while pos < len(first_chunk) - 8:
            chunk_id = first_chunk[pos:pos+4]
            chunk_size = int.from_bytes(first_chunk[pos+4:pos+8], 'little')
            
            if chunk_id == b'data':
                data_start = pos + 8
                break
            pos += 8 + chunk_size
        
        # Collect all audio data
        combined_data = b""
        
        for chunk in audio_chunks:
            # Find data section in this chunk
            chunk_data_start = 44
            pos = 12
            while pos < len(chunk) - 8:
                chunk_id = chunk[pos:pos+4]
                chunk_size = int.from_bytes(chunk[pos+4:pos+8], 'little')
                
                if chunk_id == b'data':
                    chunk_data_start = pos + 8
                    data_size = chunk_size
                    # Extract audio data
                    audio_data = chunk[chunk_data_start:chunk_data_start + data_size]
                    combined_data += audio_data
                    break
                pos += 8 + chunk_size
        
        # Create new WAV with combined data
        new_data_size = len(combined_data)
        new_file_size = 36 + new_data_size  # 44 - 8 + data_size
        
        # Update header with new sizes
        new_header = bytearray(header)
        # Update file size (bytes 4-7)
        new_header[4:8] = (new_file_size).to_bytes(4, 'little')
        
        # Create data chunk header
        data_chunk_header = b'data' + new_data_size.to_bytes(4, 'little')
        
        # Combine: RIFF header + format chunk + data chunk header + audio data
        result = bytes(new_header[:data_start-8]) + data_chunk_header + combined_data
        
        return result
        
    except Exception as e:
        logger.error(f"Error in manual WAV concat: {e}")
        return audio_chunks[0] if audio_chunks else b""

def format_timestamp_for_display(seconds: float) -> str:
    """
    Convert seconds to MM:SS format for display.
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: Formatted timestamp (e.g., "2:30")
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def find_article_at_timestamp(timeline: Dict[str, Dict], timestamp_seconds: float) -> Dict:
    """
    Find which article section is playing at a given timestamp.
    
    Args:
        timeline (Dict): Timeline mapping from generate_chunked_podcast_audio
        timestamp_seconds (float): Timestamp to query
        
    Returns:
        Dict: Section info at that timestamp, or None if not found
    """
    try:
        for time_range, section_info in timeline.items():
            start_time = section_info["start_seconds"]
            end_time = section_info["end_seconds"]
            
            if start_time <= timestamp_seconds <= end_time:
                return {
                    "time_range": time_range,
                    "section_name": section_info["section_name"],
                    "article_id": section_info["article_id"],
                    "content_preview": section_info["content_preview"],
                    "formatted_range": f"{format_timestamp_for_display(start_time)}-{format_timestamp_for_display(end_time)}"
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding article at timestamp: {e}")
        return None

def generate_complete_chunked_podcast(
    script_content: str,
    voice_id: str = "96c64eb5-a945-448f-9710-980abe7a514c",
    language: str = "en"
) -> Dict:
    """
    Complete pipeline: Parse script → Generate chunked audio → Create timeline.
    
    Args:
        script_content (str): Full podcast script with section markers
        voice_id (str): Cartesia voice ID
        language (str): Language code
        
    Returns:
        Dict: Complete result with audio, timeline, and metadata
    """
    try:
        logger.info("🚀 Starting complete chunked podcast generation")
        
        # Step 1: Parse script into sections
        sections = parse_script_sections(script_content)
        
        if not sections:
            raise Exception("No sections found in script")
        
        # Step 2: Generate chunked audio with precise timeline
        combined_audio, timeline = generate_chunked_podcast_audio(
            sections=sections,
            voice_id=voice_id,
            language=language
        )
        
        if not combined_audio:
            raise Exception("Audio generation failed")
        
        # Step 3: Create result
        total_duration = max([info["end_seconds"] for info in timeline.values()]) if timeline else 0
        
        result = {
            "success": True,
            "audio_bytes": combined_audio,
            "timeline": timeline,
            "sections": sections,
            "metadata": {
                "total_sections": len(sections),
                "total_duration_seconds": total_duration,
                "total_duration_formatted": format_timestamp_for_display(total_duration),
                "voice_id": voice_id,
                "language": language,
                "audio_size_bytes": len(combined_audio),
                "generation_method": "chunked_tts"
            },
            "generation_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Complete chunked podcast generated: {total_duration:.1f}s, {len(sections)} sections")
        return result
        
    except Exception as e:
        logger.error(f"Error in complete chunked podcast generation: {e}")
        return {
            "success": False,
            "error": str(e),
            "audio_bytes": b"",
            "timeline": {},
            "sections": {},
            "metadata": {}
        }

# Example usage functions
def demo_chunked_podcast():
    """Demo function showing how to use the chunked podcast system."""
    
    sample_script = """
INTRO:
Welcome to your personalized news briefing! Today we're covering some exciting developments in technology and business.

<<article1>>:
Speaking of artificial intelligence, OpenAI just announced major updates to their GPT models. The company claims these improvements will make AI more reliable for complex tasks.

<<article2>>:
Oh, and here's something interesting from the startup world. European fintech companies are seeing record funding this quarter.

<<article3>>:
You know what caught my eye? Bitcoin has stabilized around forty-two thousand dollars while regulatory frameworks continue to evolve.

CONCLUSION:
That's your briefing for today! Thanks for listening, and we'll catch you next time with more updates.
"""
    
    print("🎙️ Demo: Generating chunked podcast...")
    result = generate_complete_chunked_podcast(sample_script)
    
    if result["success"]:
        print(f"✅ Success! Generated {result['metadata']['total_duration_formatted']} of audio")
        print(f"📊 Timeline:")
        for time_range, info in result["timeline"].items():
            print(f"  {time_range}: {info['section_name']}")
        
        # Demo: Find article at specific timestamp
        test_timestamp = 45.0  # 45 seconds
        article_info = find_article_at_timestamp(result["timeline"], test_timestamp)
        if article_info:
            print(f"\n🔍 At {format_timestamp_for_display(test_timestamp)}: {article_info['section_name']}")
    else:
        print(f"❌ Failed: {result['error']}")

if __name__ == "__main__":
    demo_chunked_podcast() 