#!/usr/bin/env python3

import requests
import json
import uuid

# Configuration
BASE_URL = "https://us-central1-prysmios.cloudfunctions.net"

def test_specific_subjects_flow():
    """Test le flux complet des specific subjects."""
    
    print("🧪 Testing Specific Subjects Flow")
    print("=" * 60)
    
    user_id = str(uuid.uuid4())
    print(f"👤 User ID: {user_id}")
    
    # 1. Test GET action (devrait retourner une liste vide au début)
    print("\n📥 1. Testing GET action (should be empty initially)")
    print("-" * 40)
    
    payload_get = {
        "user_id": user_id,
        "action": "get"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/update_specific_subjects",
            json=payload_get,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET Response: {json.dumps(data, indent=2)}")
            initial_subjects = data.get('specific_subjects', [])
            print(f"📊 Initial subjects count: {len(initial_subjects)}")
        else:
            print(f"❌ GET Error: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ GET Request failed: {e}")
        return
    
    # 2. Test ANALYZE action (simuler une conversation avec des entités)
    print("\n🔍 2. Testing ANALYZE action (simulate conversation)")
    print("-" * 40)
    
    payload_analyze = {
        "user_id": user_id,
        "action": "analyze",
        "conversation_history": [
            {"role": "assistant", "content": "Hello! What interests you?"},
            {"role": "user", "content": "I'm interested in technology"}
        ],
        "user_message": "I love Apple products and Tesla cars. I also follow SpaceX missions.",
        "language": "en"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/update_specific_subjects",
            json=payload_analyze,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ANALYZE Response: {json.dumps(data, indent=2)}")
            new_subjects = data.get('new_subjects_found', [])
            total_subjects = data.get('total_subjects', [])
            print(f"🆕 New subjects found: {new_subjects}")
            print(f"📊 Total subjects: {total_subjects}")
        else:
            print(f"❌ ANALYZE Error: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ ANALYZE Request failed: {e}")
        return
    
    # 3. Test GET action again (devrait maintenant retourner les sujets trouvés)
    print("\n📥 3. Testing GET action again (should now have subjects)")
    print("-" * 40)
    
    try:
        response = requests.post(
            f"{BASE_URL}/update_specific_subjects",
            json=payload_get,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET Response: {json.dumps(data, indent=2)}")
            final_subjects = data.get('specific_subjects', [])
            print(f"📊 Final subjects count: {len(final_subjects)}")
            print(f"🎯 Subjects: {final_subjects}")
            
            if len(final_subjects) > len(initial_subjects):
                print("🎉 SUCCESS: New subjects were added and retrieved!")
            else:
                print("⚠️  WARNING: No new subjects were added")
        else:
            print(f"❌ Final GET Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Final GET Request failed: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_specific_subjects_flow() 