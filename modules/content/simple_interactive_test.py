import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import uuid

from firebase_admin import firestore, storage
from modules.ai.client import get_openai_client
from modules.audio.cartesia import generate_text_to_speech

logger = logging.getLogger(__name__)

# Sample 300-word news text for testing
SAMPLE_PODCAST_TEXT = """
Hello and welcome to your personalized news briefing! I'm Alex, and today we have some fascinating developments in technology and business.

Starting with artificial intelligence, OpenAI has just announced major updates to their GPT models, focusing on improved reasoning capabilities and reduced hallucinations. The company claims these improvements will make AI assistants more reliable for complex tasks like data analysis and scientific research. Industry experts are calling this a significant step forward in making AI more trustworthy for enterprise applications.

In business news, European startups are seeing record funding levels this quarter, with fintech and climate tech leading the charge. Notable deals include a 50 million euro Series B for Berlin-based renewable energy platform GreenTech Solutions, and a 30 million euro Series A for Paris-based AI trading firm QuantumTrade. Investors are particularly excited about the intersection of AI and sustainable technology.

Meanwhile, the cryptocurrency market is experiencing renewed volatility as regulatory frameworks continue to evolve. Bitcoin has stabilized around forty-two thousand dollars, while Ethereum is showing strong momentum due to upcoming network upgrades. Regulatory clarity in the European Union is expected to provide more certainty for crypto businesses operating in the region.

Looking at social media trends, there's growing discussion about digital privacy rights and data protection. Users are increasingly concerned about how their personal information is being used by tech platforms, leading to calls for stronger privacy legislation.

That's your briefing for today! Remember, you can interrupt me anytime to ask for more details, sources, or to explore any topic deeper. What would you like to know more about?
"""

class SimpleInteractiveTest:
    """Simple test class for interactive podcast functionality."""
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.current_sessions = {}
        
    def create_test_session(self, user_id: str = "test_user") -> Dict:
        """Create a simple test session."""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "podcast_text": SAMPLE_PODCAST_TEXT,
            "current_position": 0,
            "status": "ready",
            "created_at": datetime.now().isoformat(),
            "context": {
                "topics": ["AI", "European Startups", "Cryptocurrency", "Privacy"],
                "sources": ["OpenAI", "TechCrunch", "European Venture Report", "CoinDesk"],
                "key_facts": [
                    "OpenAI announced GPT model updates",
                    "European startups hit record funding",
                    "Bitcoin stable at $42k",
                    "Growing privacy concerns"
                ]
            }
        }
        
        self.current_sessions[session_id] = session_data
        
        logger.info(f"🎙️ Test session created: {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Interactive test session ready! The AI will start speaking shortly.",
            "sample_questions": [
                "Tell me more about the OpenAI updates",
                "What are the sources for this information?",
                "Give me details on European startup funding",
                "What's happening with Bitcoin?"
            ]
        }
    
    def generate_podcast_audio(self, session_id: str, voice_id: str = "96c64eb5-a945-448f-9710-980abe7a514c") -> Dict:
        """Generate audio for the podcast text."""
        try:
            if session_id not in self.current_sessions:
                return {"success": False, "error": "Session not found"}
            
            session = self.current_sessions[session_id]
            podcast_text = session["podcast_text"]
            
            logger.info(f"🔊 Generating audio for session {session_id}")
            
            # Generate audio using existing TTS
            audio_bytes = generate_text_to_speech(
                text=podcast_text,
                voice_id=voice_id,
                model_id="sonic-2",
                language="en"
            )
            
            if not audio_bytes:
                return {"success": False, "error": "Audio generation failed"}
            
            # Save to Firebase Storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interactive_tests/{session_id}/podcast_{timestamp}.wav"
            
            bucket = storage.bucket()
            blob = bucket.blob(filename)
            blob.upload_from_string(audio_bytes, content_type='audio/wav')
            blob.make_public()
            
            audio_url = blob.public_url
            
            # Update session
            session["audio_url"] = audio_url
            session["audio_generated_at"] = datetime.now().isoformat()
            session["status"] = "audio_ready"
            
            logger.info(f"✅ Audio generated: {filename}")
            
            return {
                "success": True,
                "audio_url": audio_url,
                "session_id": session_id,
                "message": "Audio is ready! Start playing and interrupt anytime with questions."
            }
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return {"success": False, "error": str(e)}
    
    def handle_interruption(self, session_id: str, user_question: str) -> Dict:
        """Handle user interruption with a simple question."""
        try:
            if session_id not in self.current_sessions:
                return {"success": False, "error": "Session not found"}
            
            session = self.current_sessions[session_id]
            context = session["context"]
            
            logger.info(f"🎤 User interruption in session {session_id}: '{user_question}'")
            
            # Simple intent detection
            question_lower = user_question.lower()
            
            # Pre-defined quick responses for common questions
            if any(word in question_lower for word in ["source", "where", "reference"]):
                response = f"The information comes from several reliable sources including {', '.join(context['sources'])}. These are all reputable tech and finance publications."
                
            elif "openai" in question_lower or "gpt" in question_lower:
                response = "OpenAI's latest updates focus on improved reasoning and reduced hallucinations. This means the AI will be more accurate and reliable for complex tasks like data analysis and research. The company hasn't released all technical details yet, but early tests show significant improvements."
                
            elif "startup" in question_lower or "funding" in question_lower or "european" in question_lower:
                response = "European startups are seeing record investments this quarter. Fintech and climate tech are leading with major deals like GreenTech Solutions raising 50 million euros. Investors are particularly interested in companies combining AI with sustainable technology."
                
            elif "bitcoin" in question_lower or "crypto" in question_lower:
                response = "Bitcoin is currently stable around forty-two thousand dollars. The cryptocurrency market is being influenced by evolving regulations, especially in the EU where new frameworks are providing more clarity for crypto businesses."
                
            elif "privacy" in question_lower or "data" in question_lower:
                response = "There's growing concern about how tech platforms use personal data. Users want more control over their information, and this is driving demand for stronger privacy laws similar to GDPR."
                
            else:
                # Use OpenAI for more complex questions
                response = self._generate_ai_response(user_question, context)
            
            # Generate audio response
            audio_response = self._generate_response_audio(response, session_id)
            
            # Update session history
            if "conversation_history" not in session:
                session["conversation_history"] = []
            
            session["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "user_question": user_question,
                "ai_response": response,
                "audio_url": audio_response.get("audio_url")
            })
            
            return {
                "success": True,
                "response": response,
                "audio_url": audio_response.get("audio_url"),
                "session_id": session_id,
                "message": "Here's my response! Continue listening or ask another question."
            }
            
        except Exception as e:
            logger.error(f"Error handling interruption: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_ai_response(self, question: str, context: Dict) -> str:
        """Generate AI response for complex questions."""
        try:
            prompt = f"""You're an AI news assistant. Answer the user's question based on this context:

TOPICS: {', '.join(context['topics'])}
KEY FACTS: {json.dumps(context['key_facts'], indent=2)}
SOURCES: {', '.join(context['sources'])}

USER QUESTION: {question}

INSTRUCTIONS:
- Keep response under 60 seconds when spoken (250-300 words max)
- Be conversational and friendly
- Reference the facts and sources available
- If you don't have specific info, say so and offer general insights

RESPONSE:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I'm having trouble processing that question right now. Could you try asking it differently?"
    
    def _generate_response_audio(self, response_text: str, session_id: str) -> Dict:
        """Generate audio for the AI response."""
        try:
            # Generate TTS audio
            audio_bytes = generate_text_to_speech(
                text=response_text,
                voice_id="96c64eb5-a945-448f-9710-980abe7a514c",
                model_id="sonic-2",
                language="en"
            )
            
            if not audio_bytes:
                return {"success": False, "error": "Response audio generation failed"}
            
            # Save to storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interactive_tests/{session_id}/response_{timestamp}.wav"
            
            bucket = storage.bucket()
            blob = bucket.blob(filename)
            blob.upload_from_string(audio_bytes, content_type='audio/wav')
            blob.make_public()
            
            return {
                "success": True,
                "audio_url": blob.public_url
            }
            
        except Exception as e:
            logger.error(f"Error generating response audio: {e}")
            return {"success": False, "error": str(e)}
    
    def get_session_info(self, session_id: str) -> Dict:
        """Get information about a test session."""
        if session_id not in self.current_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.current_sessions[session_id]
        
        return {
            "success": True,
            "session": session,
            "conversation_count": len(session.get("conversation_history", [])),
            "status": session["status"]
        }

# Global instance for testing
interactive_test = SimpleInteractiveTest() 