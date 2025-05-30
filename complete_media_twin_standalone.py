#!/usr/bin/env python3

import json
import logging
import os
import re
import uuid
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
from generate_complete_media_twin import generate_complete_media_twin_script
from elevenlabs import ElevenLabs

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase if not already done."""
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()

def get_elevenlabs_key():
    """Retrieve ElevenLabs API key from environment or fallback to hardcoded value."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    logger.warning("ELEVENLABS_API_KEY not found in env, using fallback key")
    return "sk_332f27cd984ed4fb2eb9a18bd6eb202b45fe290873db787f"

def generate_text_to_speech(text, voice_id="cmudN4ihcI42n48urXgc", model_id="eleven_multilingual_v2", output_format="mp3_44100_128"):
    """
    Generate speech from text using ElevenLabs API.
    
    Args:
        text (str): The text to convert to speech
        voice_id (str): ElevenLabs voice ID to use
        model_id (str): ElevenLabs model ID to use
        output_format (str): Audio output format
    
    Returns:
        bytes: Audio data as bytes, or None if error
    """
    try:
        logger.info(f"🔊 Converting text to speech: '{text[:50]}...' using voice {voice_id}")
        
        # Initialize ElevenLabs client
        api_key = get_elevenlabs_key()
        elevenlabs = ElevenLabs(api_key=api_key)
        
        # Convert text to speech
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
        )
        
        # Convert the audio generator to bytes
        audio_bytes = b''.join(audio)
        
        logger.info(f"✅ Successfully generated {len(audio_bytes)} bytes of audio")
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Error generating text-to-speech: {e}")
        return None

def clean_script_for_audio(script_text):
    """
    Clean script text for optimal text-to-speech conversion.
    Removes emojis, formatting symbols, and adjusts for natural speech.
    
    Args:
        script_text (str): Raw script text with formatting
    
    Returns:
        str: Cleaned text optimized for TTS
    """
    try:
        # Remove emoji and special symbols
        emoji_pattern = re.compile("["
                                 u"\U0001F600-\U0001F64F"  # emoticons
                                 u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                 u"\U0001F680-\U0001F6FF"  # transport & map
                                 u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                 u"\U00002702-\U000027B0"
                                 u"\U000024C2-\U0001F251"
                                 "]+", flags=re.UNICODE)
        clean_text = emoji_pattern.sub('', script_text)
        
        # Remove special formatting
        clean_text = re.sub(r'🎙️|🎬|🎯|📰|🔍|💬|🔄|📊|====+', '', clean_text)
        clean_text = re.sub(r'#{1,6}\s*', '', clean_text)  # Remove markdown headers
        clean_text = re.sub(r'\*{1,3}', '', clean_text)    # Remove bold/italic
        clean_text = re.sub(r'`{1,3}[^`]*`{1,3}', '', clean_text)  # Remove code blocks
        clean_text = re.sub(r'[-]{3,}', '', clean_text)    # Remove separator lines
        clean_text = re.sub(r'•', '-', clean_text)         # Replace bullet points
        
        # Clean up specific patterns
        clean_text = re.sub(r'SCRIPT MÉDIA TWIN.*?\n', '', clean_text)
        clean_text = re.sub(r'INTRO \(\d+.*?\)', 'Introduction.', clean_text)
        clean_text = re.sub(r'SEGMENT \d+:.*?\)', '', clean_text)
        clean_text = re.sub(r'CONCLUSION \(\d+.*?\)', 'Conclusion.', clean_text)
        clean_text = re.sub(r'ACCROCHE:', 'Voici les actualités.', clean_text)
        clean_text = re.sub(r'LE BRIEFING:', '', clean_text)
        clean_text = re.sub(r'LES POINTS CLÉS:', 'Voici les points importants.', clean_text)
        clean_text = re.sub(r'INFORMATIONS DU BRIEFING:', 'Informations sur ce briefing.', clean_text)
        
        # Clean up time references
        clean_text = re.sub(r'\(\d+\s*secondes?\)', '', clean_text)
        clean_text = re.sub(r'\(\d+s\)', '', clean_text)
        
        # Normalize whitespace
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)  # Max 2 consecutive newlines
        clean_text = re.sub(r' {2,}', ' ', clean_text)      # Multiple spaces to single
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)  # Clean paragraph breaks
        
        # Add natural pauses for TTS
        clean_text = clean_text.replace('\n\n', '. ... ')   # Paragraph breaks become pauses
        clean_text = clean_text.replace('\n', '. ')         # Line breaks become sentence breaks
        
        # Final cleanup
        clean_text = clean_text.strip()
        clean_text = re.sub(r'\.{2,}', '...', clean_text)   # Normalize ellipses
        clean_text = re.sub(r'\s+', ' ', clean_text)        # Final space normalization
        
        logger.info(f"Script cleaned for TTS: {len(script_text)} → {len(clean_text)} characters")
        return clean_text
        
    except Exception as e:
        logger.error(f"Error cleaning script for audio: {e}")
        # Return basic cleaned version as fallback
        return re.sub(r'[^\w\s\.,;:!?àâäéèêëïîôöùûüÿçÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÇ-]', '', script_text)

def generate_complete_media_twin_with_audio(user_id, presenter_name="Alex", language="fr", voice_id="cmudN4ihcI42n48urXgc"):
    """
    Orchestrate complete media twin generation: script + audio + storage.
    
    1. Generate complete AI script using user's real articles
    2. Convert script to audio using ElevenLabs TTS
    3. Store audio in Firebase Storage
    4. Return complete result with URLs and metadata
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter
        language (str): Language for the script ('fr' or 'en')
        voice_id (str): ElevenLabs voice ID for TTS
    
    Returns:
        dict: Complete result with script, audio URL, and metadata
    """
    try:
        logger.info(f"🎬 Starting complete media twin generation for user {user_id}")
        
        # STEP 1: Generate the complete AI script
        logger.info("📝 Step 1: Generating complete AI script...")
        script_text = generate_complete_media_twin_script(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language
        )
        
        if not script_text or "Désolé" in script_text:
            raise Exception(f"Script generation failed: {script_text}")
        
        logger.info(f"✅ Script generated: {len(script_text.split())} words")
        
        # Create metadata
        script_metadata = {
            "word_count": len(script_text.split()),
            "total_duration_estimate": f"{max(4, len(script_text.split()) // 150)} minutes",
            "presenter_name": presenter_name,
            "language": language,
            "user_id": user_id
        }
        
        # STEP 2: Convert script to audio using ElevenLabs
        logger.info("🔊 Step 2: Converting script to audio...")
        
        # Clean script for TTS (remove emojis and formatting)
        clean_script_for_tts = clean_script_for_audio(script_text)
        
        # Generate audio using ElevenLabs
        audio_bytes = generate_text_to_speech(
            text=clean_script_for_tts,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        if not audio_bytes:
            raise Exception("Audio generation failed")
        
        logger.info(f"✅ Audio generated: {len(audio_bytes)} bytes")
        
        # STEP 3: Store audio in Firebase Storage
        logger.info("💾 Step 3: Storing audio in Firebase Storage...")
        
        # Generate unique filename
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4()).split('-')[0]
        audio_filename = f"media_twin_{user_id}_{timestamp_str}_{short_uuid}.mp3"
        
        # Upload to Firebase Storage
        bucket_name = "prysmios.firebasestorage.app"
        bucket = storage.bucket(name=bucket_name)
        storage_path = f"user_media_twins/{user_id}/{audio_filename}"
        blob = bucket.blob(storage_path)
        
        # Upload audio bytes
        blob.upload_from_string(audio_bytes, content_type='audio/mpeg')
        
        # Make publicly accessible
        blob.make_public()
        audio_url = blob.public_url
        
        logger.info(f"✅ Audio stored at: {storage_path}")
        logger.info(f"🌐 Public URL: {audio_url}")
        
        # STEP 4: Store metadata in Firestore
        logger.info("📊 Step 4: Storing metadata in Firestore...")
        
        db_client = initialize_firebase()
        media_twin_doc = {
            "user_id": user_id,
            "presenter_name": presenter_name,
            "language": language,
            "voice_id": voice_id,
            "script_text": script_text,
            "clean_script": clean_script_for_tts,
            "audio_url": audio_url,
            "storage_path": storage_path,
            "script_metadata": script_metadata,
            "audio_size_bytes": len(audio_bytes),
            "generated_at": firestore.SERVER_TIMESTAMP,
            "status": "completed"
        }
        
        # Store in user's media twins collection
        media_twin_ref = db_client.collection('user_media_twins').document(user_id).collection('twins').document()
        media_twin_ref.set(media_twin_doc)
        
        # Also update user's latest media twin
        user_ref = db_client.collection('users').document(user_id)
        user_ref.set({
            "latest_media_twin": {
                "twin_id": media_twin_ref.id,
                "audio_url": audio_url,
                "generated_at": firestore.SERVER_TIMESTAMP,
                "presenter_name": presenter_name,
                "language": language,
                "duration_estimate": script_metadata.get("total_duration_estimate", "Unknown")
            }
        }, merge=True)
        
        logger.info(f"✅ Metadata stored with twin ID: {media_twin_ref.id}")
        
        # STEP 5: Return complete result
        result = {
            "success": True,
            "twin_id": media_twin_ref.id,
            "script": script_text,
            "clean_script": clean_script_for_tts,
            "audio_url": audio_url,
            "storage_path": storage_path,
            "metadata": {
                **script_metadata,
                "audio_size_bytes": len(audio_bytes),
                "voice_id": voice_id,
                "twin_id": media_twin_ref.id,
                "storage_bucket": bucket_name,
                "generation_complete": True
            },
            "generation_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🎉 Complete media twin generation successful for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in complete media twin generation for user {user_id}: {e}")
        
        # Store error in Firestore for debugging
        try:
            db_client = initialize_firebase()
            error_doc = {
                "user_id": user_id,
                "error": str(e),
                "error_timestamp": firestore.SERVER_TIMESTAMP,
                "presenter_name": presenter_name,
                "language": language,
                "voice_id": voice_id,
                "status": "failed"
            }
            db_client.collection('user_media_twins').document(user_id).collection('errors').add(error_doc)
        except:
            pass  # Don't fail on error logging
        
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

def main():
    print("🎬 GÉNÉRATION MÉDIA TWIN COMPLET AVEC AUDIO")
    print("=" * 70)
    
    user_id = "GDofaXAIvnPp5jjSF2D1FHuPfly1"
    presenter_name = "Alex"
    language = "fr"
    voice_id = "cmudN4ihcI42n48urXgc"  # ElevenLabs voice
    
    print(f"👤 User ID: {user_id}")
    print(f"🎭 Présentateur: {presenter_name}")
    print(f"🌍 Langue: {language}")
    print(f"🔊 Voice ID: {voice_id}")
    print()
    
    print("🔄 Génération complète: script + audio + stockage...")
    print("   (Cela peut prendre plusieurs minutes)")
    print()
    
    try:
        result = generate_complete_media_twin_with_audio(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language,
            voice_id=voice_id
        )
        
        if result.get("success"):
            print("✅ SUCCÈS ! Média twin complet généré")
            print("=" * 70)
            print()
            print(f"🆔 Twin ID: {result['twin_id']}")
            print(f"🔊 Audio URL: {result['audio_url']}")
            print(f"📊 Script: {result['metadata']['word_count']} mots")
            print(f"🎵 Audio: {result['metadata']['audio_size_bytes']:,} bytes")
            print(f"⏱️ Durée estimée: {result['metadata']['total_duration_estimate']}")
            print()
            print("🎬 Script généré (extrait):")
            print("-" * 50)
            print(result['script'][:500] + "...")
        else:
            print(f"❌ ERREUR: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 