import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
import uuid

from firebase_admin import firestore, storage
from modules.ai.client import get_openai_client
from modules.audio.cartesia import generate_text_to_speech
from modules.database.operations import get_user_articles_from_db, get_user_preferences_from_db

logger = logging.getLogger(__name__)

class InteractivePodcastManager:
    """
    Manages interactive podcast sessions with real-time voice interruptions.
    Handles the complete pipeline: STT → Context Analysis → LLM → TTS
    """
    
    def __init__(self):
        self.active_sessions = {}  # session_id -> session_data
        self.openai_client = get_openai_client()
        
    async def start_interactive_session(self, user_id: str, podcast_data: Dict) -> Dict:
        """
        Initialize an interactive podcast session with pre-loaded context.
        
        Args:
            user_id: User identifier
            podcast_data: Original podcast content and metadata
            
        Returns:
            Session information with session_id
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Pre-load user context for fast responses
            user_context = await self._load_user_context(user_id)
            
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "podcast_data": podcast_data,
                "user_context": user_context,
                "current_position": 0,  # Where user is in the podcast
                "conversation_history": [],
                "status": "active"
            }
            
            self.active_sessions[session_id] = session_data
            
            logger.info(f"🎙️ Interactive session started: {session_id} for user {user_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "message": "Interactive session ready. You can interrupt anytime with questions!",
                "available_commands": [
                    "Give me more details on [topic]",
                    "Explain this better",
                    "Tomorrow bring updates on [field]",
                    "Skip to [topic]",
                    "Pause/Resume",
                    "What sources support this?"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error starting interactive session: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_user_interruption(self, session_id: str, user_audio_text: str) -> AsyncGenerator[Dict, None]:
        """
        Handle user interruption with streaming response generation.
        
        Args:
            session_id: Active session identifier
            user_audio_text: Transcribed user question/command
            
        Yields:
            Streaming response chunks for real-time playback
        """
        try:
            if session_id not in self.active_sessions:
                yield {"error": "Session not found", "success": False}
                return
                
            session = self.active_sessions[session_id]
            user_id = session["user_id"]
            
            logger.info(f"🎤 User interruption in session {session_id}: '{user_audio_text}'")
            
            # Step 1: Analyze user intent (fast classification)
            intent_analysis = await self._analyze_user_intent(user_audio_text, session)
            
            yield {
                "type": "intent_detected",
                "intent": intent_analysis["intent"],
                "confidence": intent_analysis["confidence"],
                "processing": True
            }
            
            # Step 2: Generate streaming response based on intent
            async for response_chunk in self._generate_streaming_response(user_audio_text, intent_analysis, session):
                yield response_chunk
                
            # Step 3: Update conversation history
            session["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "user_input": user_audio_text,
                "intent": intent_analysis["intent"],
                "response_generated": True
            })
            
        except Exception as e:
            logger.error(f"Error handling interruption: {e}")
            yield {"error": str(e), "success": False}
    
    async def _analyze_user_intent(self, user_input: str, session: Dict) -> Dict:
        """
        Fast intent classification to determine response strategy.
        """
        try:
            # Define intent patterns
            intent_patterns = {
                "more_details": ["more details", "explain", "elaborate", "tell me more"],
                "source_request": ["source", "where did you get", "reference"],
                "topic_jump": ["skip to", "go to", "talk about", "tell me about"],
                "future_updates": ["tomorrow", "next time", "bring updates", "follow up"],
                "clarification": ["what do you mean", "clarify", "I don't understand"],
                "pause_control": ["pause", "stop", "resume", "continue"],
                "summary_request": ["summarize", "sum up", "key points"]
            }
            
            user_lower = user_input.lower()
            detected_intent = "general_question"
            confidence = 0.5
            
            # Simple pattern matching for fast classification
            for intent, patterns in intent_patterns.items():
                for pattern in patterns:
                    if pattern in user_lower:
                        detected_intent = intent
                        confidence = 0.8
                        break
                if confidence > 0.7:
                    break
            
            return {
                "intent": detected_intent,
                "confidence": confidence,
                "original_text": user_input
            }
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return {"intent": "general_question", "confidence": 0.3, "original_text": user_input}
    
    async def _generate_streaming_response(self, user_input: str, intent_analysis: Dict, session: Dict) -> AsyncGenerator[Dict, None]:
        """
        Generate streaming AI response based on user intent and session context.
        """
        try:
            intent = intent_analysis["intent"]
            podcast_data = session["podcast_data"]
            user_context = session["user_context"]
            
            # Build context-aware prompt based on intent
            if intent == "more_details":
                prompt = self._build_details_prompt(user_input, podcast_data, user_context)
            elif intent == "future_updates":
                prompt = self._build_future_updates_prompt(user_input, user_context)
            elif intent == "source_request":
                prompt = self._build_source_prompt(user_input, podcast_data)
            elif intent == "topic_jump":
                prompt = self._build_topic_jump_prompt(user_input, podcast_data)
            else:
                prompt = self._build_general_prompt(user_input, podcast_data, user_context)
            
            # Stream response from OpenAI
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ]
            
            response_chunks = []
            
            # Using OpenAI streaming
            stream = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500,  # Keep responses concise for voice
                temperature=0.7,
                stream=True
            )
            
            current_response = ""
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    current_response += content
                    response_chunks.append(content)
                    
                    # Yield chunk for streaming TTS
                    yield {
                        "type": "text_chunk",
                        "content": content,
                        "full_response_so_far": current_response,
                        "is_final": False
                    }
            
            # Final response
            yield {
                "type": "response_complete",
                "full_response": current_response,
                "intent_handled": intent,
                "is_final": True,
                "ready_for_tts": True
            }
            
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            yield {
                "type": "error",
                "message": "Sorry, I had trouble processing that. Can you try again?",
                "error": str(e)
            }
    
    def _build_details_prompt(self, user_input: str, podcast_data: Dict, user_context: Dict) -> str:
        """Build prompt for detailed explanations."""
        return f"""You are an AI assistant providing detailed explanations during an interactive news podcast.

PODCAST CONTEXT:
{json.dumps(podcast_data.get('metadata', {}), indent=2)}

USER PREFERENCES:
{json.dumps(user_context.get('preferences', {}), indent=2)}

USER QUESTION: {user_input}

INSTRUCTIONS:
- Provide detailed, conversational explanations
- Reference specific articles or sources when possible
- Keep response under 60 seconds when spoken (300-400 words max)
- Use a friendly, podcast-like tone
- If you don't have enough detail, offer to research it for next time

RESPONSE FORMAT: Natural speech, no markdown or formatting."""

    def _build_future_updates_prompt(self, user_input: str, user_context: Dict) -> str:
        """Build prompt for future update requests."""
        return f"""You are an AI assistant managing future update requests during an interactive podcast.

USER PREFERENCES:
{json.dumps(user_context.get('preferences', {}), indent=2)}

USER REQUEST: {user_input}

INSTRUCTIONS:
- Acknowledge the request for future updates
- Confirm what specific topic/field they want updates on
- Suggest how often they might want updates (daily, weekly)
- Offer to add it to their preferences
- Keep response brief and actionable (30 seconds max when spoken)

RESPONSE FORMAT: Natural speech confirming the request and next steps."""

    def _build_source_prompt(self, user_input: str, podcast_data: Dict) -> str:
        """Build prompt for source/reference requests."""
        article_sources = []
        if podcast_data.get('metadata', {}).get('articles_analyzed'):
            article_sources = ["Various news sources", "Reddit community discussions"]
            
        return f"""You are an AI assistant providing source information during an interactive podcast.

AVAILABLE SOURCES:
{json.dumps(article_sources, indent=2)}

USER QUESTION: {user_input}

INSTRUCTIONS:
- Provide information about sources used for the current topic
- Be transparent about data sources (news articles, Reddit, etc.)
- If specific sources aren't available, explain the general methodology
- Keep response brief (30-45 seconds when spoken)

RESPONSE FORMAT: Natural speech explaining sources clearly."""

    def _build_topic_jump_prompt(self, user_input: str, podcast_data: Dict) -> str:
        """Build prompt for topic navigation."""
        available_topics = list(podcast_data.get('topics_covered', {}).keys()) if podcast_data.get('topics_covered') else []
        
        return f"""You are an AI assistant helping users navigate podcast topics.

AVAILABLE TOPICS:
{json.dumps(available_topics, indent=2)}

USER REQUEST: {user_input}

INSTRUCTIONS:
- Help user navigate to requested topic
- If topic is available, confirm the jump and provide brief intro
- If topic isn't covered, suggest alternatives or offer to add for next time
- Keep response brief (20-30 seconds when spoken)

RESPONSE FORMAT: Natural speech confirming navigation or suggesting alternatives."""

    def _build_general_prompt(self, user_input: str, podcast_data: Dict, user_context: Dict) -> str:
        """Build prompt for general questions."""
        return f"""You are an AI assistant in an interactive news podcast session.

CURRENT PODCAST CONTEXT:
{json.dumps(podcast_data.get('metadata', {}), indent=2)}

USER PREFERENCES:
{json.dumps(user_context.get('preferences', {}), indent=2)}

USER QUESTION: {user_input}

INSTRUCTIONS:
- Answer the question conversationally
- Relate to current podcast content when possible
- If you don't know something, be honest and offer to research it
- Keep response concise for voice (45-60 seconds max when spoken)
- Maintain friendly, helpful podcast host tone

RESPONSE FORMAT: Natural speech, no formatting."""

    async def _load_user_context(self, user_id: str) -> Dict:
        """
        Pre-load user context for fast response generation.
        """
        try:
            # Get user preferences
            preferences = get_user_preferences_from_db(user_id)
            
            # Get recent articles
            articles = get_user_articles_from_db(user_id)
            
            return {
                "preferences": preferences,
                "recent_articles": articles,
                "loaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
            return {"preferences": {}, "recent_articles": {}}

    async def end_session(self, session_id: str) -> Dict:
        """End interactive session and cleanup."""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Save session summary to database for analytics
                await self._save_session_summary(session)
                
                del self.active_sessions[session_id]
                
                return {
                    "success": True,
                    "message": "Interactive session ended. Thanks for listening!",
                    "session_duration": "calculated",
                    "interactions": len(session.get("conversation_history", []))
                }
            else:
                return {"success": False, "error": "Session not found"}
                
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return {"success": False, "error": str(e)}
    
    async def _save_session_summary(self, session: Dict):
        """Save session analytics to database."""
        try:
            db = firestore.client()
            
            summary = {
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "created_at": session["created_at"],
                "ended_at": datetime.now().isoformat(),
                "total_interactions": len(session["conversation_history"]),
                "conversation_history": session["conversation_history"],
                "podcast_metadata": session["podcast_data"].get("metadata", {}),
                "session_type": "interactive_podcast"
            }
            
            db.collection('interactive_sessions').document(session["session_id"]).set(summary)
            
        except Exception as e:
            logger.error(f"Error saving session summary: {e}")

# Global instance
interactive_podcast_manager = InteractivePodcastManager() 