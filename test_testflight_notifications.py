#!/usr/bin/env python3
"""
Enhanced test script for TestFlight notification debugging
"""
import sys
import os
import json

# Add main to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firebase_admin import firestore, messaging
import firebase_admin
from modules.notifications.push import send_push_notification, validate_fcm_token

def init_firebase():
    """Initialize Firebase Admin if not already done"""
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()

def comprehensive_token_test(user_id):
    """
    Comprehensive test for TestFlight notification issues
    """
    print(f"🧪 COMPREHENSIVE TESTFLIGHT NOTIFICATION TEST")
    print(f"User ID: {user_id}")
    print("=" * 60)
    
    try:
        init_firebase()
        db = firestore.client()
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            print(f"❌ User document not found: {user_id}")
            return False
        
        user_data = user_doc.to_dict()
        fcm_token = user_data.get('fcmToken')
        
        # Test 1: Token Validation
        print("📋 TEST 1: FCM Token Validation")
        print("-" * 30)
        
        if not fcm_token:
            print("❌ No FCM token found")
            return False
        
        validation = validate_fcm_token(fcm_token)
        print(f"Token length: {len(fcm_token)}")
        print(f"Token preview: {fcm_token[:15]}...{fcm_token[-15:]}")
        print(f"Validation result: {validation}")
        
        if not validation.get("valid"):
            print(f"❌ Token validation failed: {validation.get('error')}")
            return False
        
        print("✅ Token format validation passed")
        
        # Test 2: Direct Firebase Messaging Test
        print("\n📤 TEST 2: Direct Firebase Messaging")
        print("-" * 30)
        
        try:
            # Simple test message
            test_message = messaging.Message(
                notification=messaging.Notification(
                    title="🧪 TestFlight Debug",
                    body="Direct Firebase test - basic message"
                ),
                token=fcm_token
            )
            
            response = messaging.send(test_message)
            print(f"✅ Direct message SUCCESS: {response}")
            
        except messaging.UnregisteredError:
            print("❌ UNREGISTERED TOKEN - This is the TestFlight issue!")
            print("💡 Cause: Token was generated in development, now in production environment")
            return False
        except messaging.SenderIdMismatchError:
            print("❌ SENDER ID MISMATCH - Token belongs to different Firebase project")
            return False
        except Exception as e:
            print(f"❌ Direct message failed: {e}")
            return False
        
        # Test 3: Enhanced APNS Configuration Test  
        print("\n📱 TEST 3: Enhanced APNS Configuration")
        print("-" * 30)
        
        try:
            # Enhanced message with proper APNS config for TestFlight
            enhanced_message = messaging.Message(
                notification=messaging.Notification(
                    title="🧪 TestFlight Enhanced",
                    body="Enhanced APNS config test"
                ),
                token=fcm_token,
                apns=messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'alert'
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title="🧪 TestFlight Enhanced",
                                body="Enhanced APNS config test"
                            ),
                            sound='default',
                            badge=1,
                            content_available=True
                        )
                    )
                )
            )
            
            response = messaging.send(enhanced_message)
            print(f"✅ Enhanced APNS message SUCCESS: {response}")
            
        except Exception as e:
            print(f"❌ Enhanced message failed: {e}")
            return False
        
        # Test 4: Our Custom Function Test
        print("\n🔧 TEST 4: Custom Push Function")
        print("-" * 30)
        
        result = send_push_notification(
            user_id=user_id,
            title="🧪 Custom Function Test",
            body="Testing our enhanced push notification function"
        )
        
        if result.get("success"):
            print(f"✅ Custom function SUCCESS: {result.get('message_id')}")
            print(f"Token used: {result.get('token_used')}")
        else:
            print(f"❌ Custom function FAILED: {result.get('error')}")
            print(f"Error type: {result.get('error_type')}")
            print(f"Suggestion: {result.get('suggestion')}")
            return False
        
        # Test 5: Token Environment Analysis
        print("\n🔍 TEST 5: Token Environment Analysis")
        print("-" * 30)
        
        # Analyze token characteristics that might indicate environment
        token_analysis = analyze_token_environment(fcm_token)
        print(f"Token analysis: {json.dumps(token_analysis, indent=2)}")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("Token appears to be valid for current environment")
        return True
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return False

def analyze_token_environment(token):
    """
    Analyze FCM token to understand its characteristics
    """
    try:
        import hashlib
        import base64
        
        analysis = {
            "length": len(token),
            "starts_with": token[:10],
            "ends_with": token[-10:],
            "contains_colon": ":" in token,
            "contains_underscore": "_" in token,
            "contains_dash": "-" in token,
            "hash_md5": hashlib.md5(token.encode()).hexdigest(),
            "estimated_type": "unknown"
        }
        
        # Try to determine token type based on characteristics
        if len(token) > 150 and ":" in token:
            analysis["estimated_type"] = "likely_valid_fcm"
        elif len(token) < 100:
            analysis["estimated_type"] = "likely_invalid_too_short"
        else:
            analysis["estimated_type"] = "uncertain"
        
        return analysis
        
    except Exception as e:
        return {"error": str(e)}

def test_multiple_environments():
    """
    Test multiple users to compare working vs non-working tokens
    """
    test_users = [
        {"id": "6wot9fy9YBgLrf9CWRq4W1aJj6O2", "status": "working"},
        {"id": "hWR0Z7AvhQU3EWB5jdm5eg2Tqzz1", "status": "not_working"}
    ]
    
    print("🔬 COMPARATIVE TESTFLIGHT ANALYSIS")
    print("=" * 50)
    
    results = {}
    
    for user in test_users:
        print(f"\n👤 Testing {user['status'].upper()} user: {user['id']}")
        print("-" * 40)
        
        success = comprehensive_token_test(user['id'])
        results[user['id']] = {
            "expected_status": user['status'],
            "test_result": "passed" if success else "failed"
        }
    
    print(f"\n📊 SUMMARY")
    print("=" * 20)
    for user_id, result in results.items():
        expected = result['expected_status']
        actual = result['test_result']
        match = "✅" if (expected == "working" and actual == "passed") or (expected == "not_working" and actual == "failed") else "❌"
        print(f"{match} {user_id}: Expected {expected}, Got {actual}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        comprehensive_token_test(user_id)
    else:
        test_multiple_environments() 