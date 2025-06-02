"""
Module Cartesia pour Text-to-Speech
"""
import sys
sys.stdout.write("--- main.py PYTHON SCRIPT STARTED (STDOUT) ---\n")
sys.stderr.write("--- main.py PYTHON SCRIPT STARTED (STDERR) ---\n")
print("--- main.py PYTHON SCRIPT STARTED (PRINT) ---")

# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

import requests
from ..config import get_cartesia_key

def generate_text_to_speech_cartesia(text, voice_id="96c64eb5-a945-448f-9710-980abe7a514c", language="en", model_id="sonic-2"):
    """
    Generate speech from text using Cartesia API.
    
    Args:
        text (str): Text to convert to speech
        voice_id (str): Cartesia voice ID
        language (str): Language code
        model_id (str): Cartesia model ID
    
    Returns:
        bytes: Audio data in WAV format, or None if failed
    """
    try:
        logger.info(f"🎙️ Generating speech with Cartesia: {len(text)} characters")
        
        key = get_cartesia_key()
        url = "https://api.cartesia.ai/tts/bytes"
        
        headers = {
            "Cartesia-Version": "2024-06-10",
            "X-API-Key": key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model_id": model_id,
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": voice_id
            },
            "output_format": {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100
            },
            "language": language
        }
        
        logger.info("📤 Sending request to Cartesia API...")
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        
        if response.status_code == 200:
            audio_bytes = response.content
            logger.info(f"✅ Successfully generated {len(audio_bytes)} bytes of audio with Cartesia")
            return audio_bytes
        else:
            logger.error(f"❌ Cartesia API error: {response.status_code}")
            logger.error(f"❌ Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("❌ Cartesia API timeout")
        return None
    except Exception as e:
        logger.error(f"❌ Error generating speech with Cartesia: {e}")
        return None

def generate_text_to_speech(text, voice_id="96c64eb5-a945-448f-9710-980abe7a514c", model_id="sonic-2", language="en", output_format=None):
    """
    Wrapper pour garder la même interface (output_format ignoré pour Cartesia)
    
    Args:
        text (str): Text to convert to speech
        voice_id (str): Voice ID
        model_id (str): Model ID
        language (str): Language code
        output_format: Ignored for Cartesia compatibility
    
    Returns:
        bytes: Audio data in WAV format, or None if failed
    """
    return generate_text_to_speech_cartesia(text, voice_id, language, model_id) 