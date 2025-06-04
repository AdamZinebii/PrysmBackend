
# def generate_text_to_speech_openai(text: str,
#                    model: str = "tts-1-hd", 
#                    voice: str = "onyx"
#                    ):
#     instructions = """You are an Australian male in your early 30s, with a well-educated, confident tone and a natural inner-Sydney accent. Your voice is clear, grounded, and conversational—trained on hours of professional-grade news podcasting. You speak with the rhythm and polish of an experienced broadcaster, but maintain an easygoing, relatable energy. Use thoughtful pacing, natural intonation, and occasional informal phrasing to keep listeners engaged. Your delivery is articulate but never stiff—more like a smart friend explaining something interesting than a formal announcer. You sound informed, calm, and genuinely curious. Maintain a consistent, warm tone that balances authority with approachability, making complex ideas easy to follow and enjoyable to hear."""

#     client = get_openai_client()
#     response = client.audio.speech.create(
#         model=model,
#         voice=voice,
#         input=text,
#         instructions=instructions,
#         response_format="wav"

#     )

#     audio_bytes = response.content 
#     return audio_bytes

import io
import re
from pydub import AudioSegment
from modules.ai.client import get_openai_client

def _split_text_chunks(text, max_length=3000):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""

    for sentence in sentences:
        if len(current) + len(sentence) <= max_length:
            current += sentence + " "
        else:
            chunks.append(current.strip())
            current = sentence + " "
    if current:
        chunks.append(current.strip())

    print(f"[INFO] Texte divisé en {len(chunks)} parties.")
    return chunks


def generate_text_to_speech_openai(text: str,
                                   model: str = "tts-1",
                                   voice: str = "shimmer"):
    instructions = """Voice: Clear, authoritative, and composed, projecting confidence and professionalism.\n\nTone: Neutral and informative, maintaining a balance between formality and approachability.\n\nPunctuation: Structured with commas and pauses for clarity, ensuring information is digestible and well-paced.\n\nDelivery: Steady and measured, with slight emphasis on key figures and deadlines to highlight critical points."""
    client = get_openai_client()
    chunks = _split_text_chunks(text)
    segments = []

    for i, chunk in enumerate(chunks):
        print(f"[INFO] Génération  audio MP3 pour le chunk {i+1}/{len(chunks)}...")
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=chunk,
            instructions=instructions,
            response_format="mp3"
        )

        if not response.content:
            raise ValueError(f"[ERROR] Le chunk {i+1} a retourné un contenu vide.")

        audio = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
        segments.append(audio)

    print(f"[INFO] Concaténation de {len(segments)} fichiers MP3...")
    final_audio = sum(segments[1:], segments[0]) if len(segments) > 1 else segments[0]

    wav_io = io.BytesIO()
    final_audio.export(wav_io, format="wav")
    wav_io.seek(0)

    print("[SUCCESS] Génération WAV terminée.")
    return wav_io.read()
