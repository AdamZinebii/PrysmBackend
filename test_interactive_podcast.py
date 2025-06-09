#!/usr/bin/env python3
"""
Simple Interactive Podcast Test with Real OpenAI
Run this script to test interactive podcast functionality with real AI responses.
"""

import json
import time
import uuid
import os
from datetime import datetime
from typing import Dict
from modules.config import get_openai_key

# Real OpenAI client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("⚠️  OpenAI library not installed. Run: pip install openai")
    OPENAI_AVAILABLE = False

class RealOpenAIClient:
    """Real OpenAI client for generating responses."""
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available")
            
        # Try to get API key from environment or user input
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            print("🔑 OpenAI API key not found in environment variables.")
            self.api_key = get_openai_key()
            
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.client = OpenAI(api_key=self.api_key)
        print("✅ OpenAI client initialized successfully!")
    
    def generate_response(self, question: str, context: Dict) -> str:
        """Generate AI response using OpenAI with context."""
        try:
            # Build context-aware prompt
            prompt = f"""You are an AI assistant in an interactive news podcast. A user just interrupted to ask a question.

PODCAST CONTEXT:
- Topics covered: {', '.join(context['topics'])}
- Key facts: {json.dumps(context['key_facts'], indent=2)}
- Sources: {', '.join(context['sources'])}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer the user's question conversationally and naturally
- Reference the specific facts and sources available when relevant
- Keep response under 60 seconds when spoken (250-300 words max)
- Be friendly and engaging like a podcast host
- If you don't have specific information, say so and offer general insights
- Don't mention that you're an AI - respond as "Alex" the podcast host

RESPONSE (speak naturally as Alex):"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I'm having trouble processing that question right now. Error: {str(e)}"

# Mock fallback for when OpenAI is not available
class MockOpenAIClient:
    def __init__(self):
        self.responses = {
            "openai": "OpenAI's latest updates focus on improved reasoning and reduced hallucinations. This makes AI more reliable for complex tasks like data analysis and research.",
            "startup": "European startups are seeing record investments this quarter. Fintech and climate tech are leading, with companies like GreenTech Solutions raising 50M euros.",
            "bitcoin": "Bitcoin is stable around $42,000. Cryptocurrency markets are influenced by evolving EU regulations providing more clarity for crypto businesses.",
            "privacy": "There's growing concern about tech platforms using personal data. Users want more control, driving demand for stronger privacy laws like GDPR.",
            "sources": "Information comes from reliable sources including OpenAI, TechCrunch, European Venture Report, and CoinDesk."
        }
    
    def generate_response(self, question: str, context: Dict) -> str:
        question_lower = question.lower()
        
        for keyword, response in self.responses.items():
            if keyword in question_lower:
                return response
        
        return f"That's an interesting question about '{question}'. Based on the available context, I can provide some general insights, but I'd need more specific information to give you a detailed answer."

# Sample 300-word podcast text
SAMPLE_PODCAST_TEXT = """
Hello and welcome to your personalized news briefing! I'm Alex, and today we have some fascinating developments in technology and business.

Starting with artificial intelligence, OpenAI has just announced major updates to their GPT models, focusing on improved reasoning capabilities and reduced hallucinations. The company claims these improvements will make AI assistants more reliable for complex tasks like data analysis and scientific research. Industry experts are calling this a significant step forward in making AI more trustworthy for enterprise applications.

In business news, European startups are seeing record funding levels this quarter, with fintech and climate tech leading the charge. Notable deals include a 50 million euro Series B for Berlin-based renewable energy platform GreenTech Solutions, and a 30 million euro Series A for Paris-based AI trading firm QuantumTrade. Investors are particularly excited about the intersection of AI and sustainable technology.

Meanwhile, the cryptocurrency market is experiencing renewed volatility as regulatory frameworks continue to evolve. Bitcoin has stabilized around forty-two thousand dollars, while Ethereum is showing strong momentum due to upcoming network upgrades. Regulatory clarity in the European Union is expected to provide more certainty for crypto businesses operating in the region.

Looking at social media trends, there's growing discussion about digital privacy rights and data protection. Users are increasingly concerned about how their personal information is being used by tech platforms, leading to calls for stronger privacy legislation.

That's your briefing for today! Remember, you can interrupt me anytime to ask for more details, sources, or to explore any topic deeper. What would you like to know more about?
"""

class InteractivePodcastTest:
    """Interactive podcast test with real OpenAI integration."""
    
    def __init__(self):
        # Try to initialize real OpenAI client, fallback to mock
        try:
            self.ai_client = RealOpenAIClient()
            self.using_real_ai = True
            print("🤖 Using REAL OpenAI for responses!")
        except Exception as e:
            print(f"⚠️  Falling back to mock responses: {e}")
            self.ai_client = MockOpenAIClient()
            self.using_real_ai = False
            
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        
        self.context = {
            "topics": ["AI", "European Startups", "Cryptocurrency", "Privacy"],
            "sources": ["OpenAI", "TechCrunch", "European Venture Report", "CoinDesk"],
            "key_facts": [
                "OpenAI announced GPT model updates with improved reasoning and reduced hallucinations",
                "European startups hit record funding this quarter, led by fintech and climate tech",
                "Bitcoin stable at $42k, crypto markets influenced by EU regulatory clarity",
                "Growing privacy concerns about tech platforms using personal data",
                "GreenTech Solutions raised 50M euro Series B",
                "QuantumTrade secured 30M euro Series A",
                "Ethereum showing momentum due to upcoming network upgrades"
            ]
        }
        
        print(f"🎙️ Interactive podcast session started: {self.session_id}")
    
    def simulate_podcast_playing(self):
        """Simulate the podcast starting to play."""
        print("\n" + "="*60)
        print("🔊 PODCAST STARTING - Alex is speaking:")
        print("="*60)
        
        # Split text into sentences for realistic simulation
        sentences = [s.strip() + "." for s in SAMPLE_PODCAST_TEXT.split('.') if s.strip()]
        
        for i, sentence in enumerate(sentences):
            print(f"\n[{i+1:2d}] {sentence}")
            
            # Simulate natural speaking pace (faster for testing)
            time.sleep(len(sentence) * 0.02)  # Faster timing for testing
            
            # Check for interruption every few sentences
            if i > 0 and i % 3 == 0:
                print(f"\n   💡 You can interrupt now! Type your question or press Enter to continue...")
                try:
                    # Non-blocking input with timeout simulation
                    import select
                    import sys
                    
                    print("   🎤 Your question (or Enter to continue): ", end='', flush=True)
                    
                    # Give user 5 seconds to type
                    if select.select([sys.stdin], [], [], 5.0)[0]:
                        user_input = input().strip()
                    else:
                        user_input = ""
                        print("(continuing...)")
                        
                except (ImportError, OSError):
                    # Fallback for Windows or systems without select
                    user_input = input("   🎤 Your question (or Enter to continue): ").strip()
                
                if user_input:
                    self.handle_interruption(user_input)
                    
                    # Ask if they want to continue
                    continue_choice = input("\n   ▶️  Continue podcast? (y/n): ").strip().lower()
                    if continue_choice == 'n':
                        print("\n   🛑 Podcast paused. Thanks for listening!")
                        return
                    else:
                        print("\n   ▶️  Resuming podcast...")
        
        print("\n" + "="*60)
        print("🎙️ PODCAST ENDED - Thanks for listening!")
        print("="*60)
    
    def handle_interruption(self, user_question: str):
        """Handle user interruption with real AI response."""
        print(f"\n🎤 USER INTERRUPTION: '{user_question}'")
        
        if self.using_real_ai:
            print("🤖 OpenAI is thinking... (this may take 2-5 seconds)")
        else:
            print("🤖 Mock AI is thinking...")
        
        # Time the response generation
        start_time = time.time()
        
        # Classify intent and generate response
        intent = self.classify_intent(user_question)
        
        # Use OpenAI for all responses (or fast pre-computed for basic ones)
        if intent == "source_request" and not self.using_real_ai:
            # Fast response for sources when using mock
            response = f"The information comes from several reliable sources including {', '.join(self.context['sources'])}. These are all reputable tech and finance publications that we monitor regularly."
        else:
            # Use AI (real or mock) for intelligent responses
            response = self.ai_client.generate_response(user_question, self.context)
        
        processing_time = time.time() - start_time
        
        print(f"   ⚡ Response generated in {processing_time:.2f} seconds")
        print(f"   🎯 Intent detected: {intent}")
        print(f"   🧠 Using: {'Real OpenAI' if self.using_real_ai else 'Mock AI'}")
        
        print("\n" + "-"*50)
        print("🤖 AI RESPONSE:")
        print("-"*50)
        print(f"{response}")
        print("-"*50)
        
        # Save to conversation history
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_question": user_question,
            "intent": intent,
            "ai_response": response,
            "processing_time": processing_time,
            "used_real_ai": self.using_real_ai
        })
    
    def classify_intent(self, question: str) -> str:
        """Fast intent classification."""
        question_lower = question.lower()
        
        intent_patterns = {
            "source_request": ["source", "where", "reference", "from where"],
            "more_details": ["more", "details", "explain", "elaborate", "tell me more"],
            "openai_topic": ["openai", "gpt", "ai update"],
            "startup_topic": ["startup", "funding", "european", "investment"],
            "crypto_topic": ["bitcoin", "crypto", "cryptocurrency", "ethereum"],
            "privacy_topic": ["privacy", "data", "personal information"],
            "comparison": ["compare", "difference", "versus", "vs"],
            "prediction": ["future", "predict", "will", "next", "tomorrow"],
            "general": ["what", "how", "why", "when"]
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in question_lower for pattern in patterns):
                return intent
        
        return "general_question"
    
    def show_session_summary(self):
        """Show summary of the interactive session."""
        print("\n" + "="*60)
        print("📊 SESSION SUMMARY")
        print("="*60)
        print(f"Session ID: {self.session_id}")
        print(f"Total interactions: {len(self.conversation_history)}")
        print(f"AI Type: {'Real OpenAI' if self.using_real_ai else 'Mock AI'}")
        
        if self.conversation_history:
            total_time = sum(interaction['processing_time'] for interaction in self.conversation_history)
            avg_time = total_time / len(self.conversation_history)
            print(f"Average response time: {avg_time:.2f} seconds")
            
            print(f"\nConversation History:")
            for i, interaction in enumerate(self.conversation_history, 1):
                print(f"\n{i}. [{interaction['timestamp'][:19]}]")
                print(f"   Q: {interaction['user_question']}")
                print(f"   Intent: {interaction['intent']}")
                print(f"   Response time: {interaction['processing_time']:.2f}s")
                print(f"   AI: {'Real' if interaction['used_real_ai'] else 'Mock'}")
                print(f"   A: {interaction['ai_response'][:100]}...")
        
        print("\n" + "="*60)

def main():
    """Main test function."""
    print("🎙️ Interactive Podcast Test with REAL OpenAI")
    print("="*60)
    print("This script simulates an interactive podcast where you can:")
    print("• Listen to a 300-word news briefing")
    print("• Interrupt to ask questions")
    print("• Get REAL AI responses from OpenAI GPT-4")
    print("\nSample questions you can try:")
    print("• 'What are the sources?'")
    print("• 'Tell me more about OpenAI updates'")
    print("• 'How will this affect small businesses?'")
    print("• 'Compare Bitcoin and Ethereum'")
    print("• 'What should investors focus on?'")
    print("="*60)
    
    if not OPENAI_AVAILABLE:
        print("\n⚠️  OpenAI library not installed. Install with: pip install openai")
        print("Continuing with mock responses for demo...")
    
    # Create test instance
    podcast_test = InteractivePodcastTest()
    
    # Start the interactive session
    input("\nPress Enter to start the podcast...")
    
    try:
        podcast_test.simulate_podcast_playing()
    except KeyboardInterrupt:
        print("\n\n🛑 Podcast interrupted by user (Ctrl+C)")
    
    # Show summary
    podcast_test.show_session_summary()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main() 