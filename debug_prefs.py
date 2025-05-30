#!/usr/bin/env python3

import requests
import json
import uuid

# Configuration
BASE_URL = "https://us-central1-prysmios.cloudfunctions.net"

def debug_preferences_flow():
    """Debug exact preferences flow."""
    
    print("🔍 DEBUG: Preferences Flow")
    print("=" * 50)
    
    user_id = str(uuid.uuid4())
    
    # Nouvelles préférences exactes
    new_preferences = {
        "subjects": ["Health", "Business"],
        "subtopics": ["Mental Health", "Startups"], 
        "detail_level": "Detailed",
        "language": "fr"
    }
    
    print(f"📤 SENDING preferences: {json.dumps(new_preferences, indent=2)}")
    
    payload = {
        "user_id": user_id,
        "user_preferences": new_preferences,
        "conversation_history": [],
        "user_message": "Bonjour, commençons la conversation"
    }
    
    print(f"📦 FULL PAYLOAD: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/answer",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received")
            print(f"📥 RETURNED preferences: {json.dumps(data.get('user_preferences', {}), indent=2)}")
            
            # Comparer ce qui a été envoyé vs ce qui est retourné
            sent_prefs = new_preferences
            returned_prefs = data.get('user_preferences', {})
            
            print("\n🔍 COMPARISON:")
            for key in ['subjects', 'subtopics', 'detail_level', 'language']:
                sent_val = sent_prefs.get(key, 'MISSING')
                returned_val = returned_prefs.get(key, 'MISSING')
                
                if sent_val == returned_val:
                    print(f"✅ {key}: {sent_val} == {returned_val}")
                else:
                    print(f"❌ {key}: SENT={sent_val} != RETURNED={returned_val}")
            
            print(f"\n🤖 AI Message: {data.get('ai_message', 'NO MESSAGE')[:200]}...")
            
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    debug_preferences_flow() 