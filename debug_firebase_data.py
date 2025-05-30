#!/usr/bin/env python3

import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    """Initialize Firebase if not already done."""
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()

def debug_user_data():
    print("🔍 DEBUGGING Firebase Data Structure")
    print("=" * 60)
    
    user_id = "GDofaXAIvnPp5jjSF2D1FHuPfly1"
    print(f"👤 User ID: {user_id}")
    print()
    
    try:
        # Get raw data from Firebase
        db = initialize_firebase()
        user_doc_ref = db.collection('articles').document(user_id)
        user_doc = user_doc_ref.get()
        
        if user_doc.exists:
            data = user_doc.to_dict()
            print("✅ Document exists!")
            print(f"📊 Document has {len(data)} top-level keys:")
            
            for key in data.keys():
                value = data[key]
                print(f"  🔑 {key}: {type(value).__name__}")
                if isinstance(value, dict):
                    print(f"      📁 Dict with {len(value)} keys")
                    if key == "topics_data" and len(value) <= 3:  # Show details if small
                        for subkey in value.keys():
                            print(f"        📂 {subkey}")
                elif isinstance(value, list):
                    print(f"      📃 List with {len(value)} items")
                else:
                    print(f"      📄 Value: {str(value)[:100]}...")
            
            print()
            print("🔍 EXAMINING topics_data structure:")
            topics_data = data.get("topics_data", {})
            if topics_data:
                print(f"Found {len(topics_data)} topics:")
                for topic_name, topic_content in topics_data.items():
                    print(f"  📁 Topic: {topic_name}")
                    if isinstance(topic_content, dict):
                        print(f"      📊 Structure: {list(topic_content.keys())}")
                        
                        # Look for actual articles/data
                        if "data" in topic_content:
                            data_content = topic_content["data"]
                            if isinstance(data_content, dict):
                                print(f"      📰 Data keys: {list(data_content.keys())}")
                                
                                # Check for headlines
                                if "topic_headlines" in data_content:
                                    headlines = data_content["topic_headlines"]
                                    print(f"      📰 Headlines: {len(headlines)} articles")
                                
                                # Check for subtopics
                                if "subtopics" in data_content:
                                    subtopics = data_content["subtopics"]
                                    print(f"      📂 Subtopics: {len(subtopics)} subtopics")
                                    for sub_name in subtopics.keys():
                                        print(f"          🔸 {sub_name}")
            else:
                print("❌ No topics_data found!")
            
            print()
            print("🔍 RAW JSON SAMPLE (first 1000 chars):")
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            print(json_str[:1000] + "..." if len(json_str) > 1000 else json_str)
            
        else:
            print("❌ Document does not exist!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_user_data() 