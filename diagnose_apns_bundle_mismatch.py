#!/usr/bin/env python3
"""
Diagnose APNs Bundle ID and environment mismatches
"""
import sys
import os
import json

# Add main to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firebase_admin import firestore, messaging
import firebase_admin

def init_firebase():
    """Initialize Firebase Admin if not already done"""
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()

def test_apns_with_different_configs(user_id):
    """
    Test different APNs configurations to identify the mismatch
    """
    print(f"🔍 APNS BUNDLE ID & ENVIRONMENT DIAGNOSIS")
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
        
        if not fcm_token:
            print(f"❌ No FCM token found")
            return False
        
        print(f"📱 FCM Token: {fcm_token[:15]}...{fcm_token[-15:]}")
        
        # Test 1: Basic message without APNs config
        print(f"\n🧪 TEST 1: Basic message (no APNs-specific config)")
        print("-" * 50)
        
        try:
            basic_message = messaging.Message(
                notification=messaging.Notification(
                    title="Basic Test",
                    body="Testing without APNs config"
                ),
                token=fcm_token
            )
            
            response = messaging.send(basic_message)
            print(f"✅ Basic message SUCCESS: {response}")
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ Basic message FAILED: {error_str}")
            
            if "Auth error from APNS" in error_str:
                print("🚨 BUNDLE ID OR ENVIRONMENT MISMATCH DETECTED!")
                print("Your APNs key configuration doesn't match this token's environment")
                
                # Check for specific error details
                if "Sender ID mismatch" in error_str:
                    print("💡 Cause: Token belongs to different Firebase project")
                elif "Requested entity was not found" in error_str:
                    print("💡 Cause: Token environment doesn't match APNs key environment")
                else:
                    print("💡 Cause: Bundle ID or environment mismatch")
                    
                return False
            elif "Requested entity was not found" in error_str:
                print("✅ APNs auth OK - Token might be expired/invalid")
                return True
            else:
                print(f"⚠️ Unexpected error: {error_str}")
                return False
        
        # Test 2: Explicit production environment
        print(f"\n🧪 TEST 2: Explicit production environment")
        print("-" * 50)
        
        try:
            prod_message = messaging.Message(
                notification=messaging.Notification(
                    title="Production Test",
                    body="Testing production environment"
                ),
                token=fcm_token,
                apns=messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'alert',
                        'apns-topic': 'com.zinebi.PrysmApp'  # Your bundle ID
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title="Production Test",
                                body="Testing production environment"
                            ),
                            sound='default',
                            badge=1
                        )
                    )
                )
            )
            
            response = messaging.send(prod_message)
            print(f"✅ Production message SUCCESS: {response}")
            return True
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ Production message FAILED: {error_str}")
            
            if "Auth error from APNS" in error_str:
                print("🚨 PRODUCTION ENVIRONMENT MISMATCH!")
                print("Your FCM token was generated in development, but APNs key is for production")
                print("💡 SOLUTION: User needs to regenerate FCM token in TestFlight environment")
                return False
        
        # Test 3: Try different bundle ID format
        print(f"\n🧪 TEST 3: Testing bundle ID variations")
        print("-" * 50)
        
        bundle_variations = [
            'com.zinebi.PrysmApp',
            'com.zinebi.Prysm',
            'Adam.PrysmIOS',  # Your Firebase app name
        ]
        
        for bundle_id in bundle_variations:
            try:
                bundle_message = messaging.Message(
                    notification=messaging.Notification(
                        title=f"Bundle Test: {bundle_id}",
                        body="Testing bundle ID"
                    ),
                    token=fcm_token,
                    apns=messaging.APNSConfig(
                        headers={
                            'apns-topic': bundle_id
                        }
                    )
                )
                
                response = messaging.send(bundle_message)
                print(f"✅ Bundle ID {bundle_id} SUCCESS: {response}")
                return True
                
            except Exception as e:
                print(f"❌ Bundle ID {bundle_id} failed: {str(e)[:100]}...")
        
        return False
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        return False

def analyze_environment_mismatch():
    """
    Provide analysis of common environment mismatch issues
    """
    print(f"\n📋 ENVIRONMENT MISMATCH ANALYSIS")
    print("=" * 40)
    
    print("🔍 Common TestFlight notification issues:")
    print("1. ❌ FCM token generated in Xcode (development)")
    print("   📱 TestFlight uses production environment")
    print("   💡 Solution: Regenerate token in TestFlight build")
    
    print("2. ❌ APNs key configured for wrong Bundle ID")
    print("   📱 Key Bundle ID ≠ App Bundle ID")
    print("   💡 Solution: Check Apple Developer Console key configuration")
    
    print("3. ❌ APNs key restricted to specific app")
    print("   📱 Key doesn't include your app's Bundle ID")
    print("   💡 Solution: Generate new key or update existing key")
    
    print(f"\n🎯 RECOMMENDED ACTIONS:")
    print("1. Have user open TestFlight app and get fresh FCM token")
    print("2. Verify Bundle ID in Apple Developer Console matches your app")
    print("3. Check APNs key permissions cover your Bundle ID")

def main():
    """
    Main diagnosis function
    """
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        success = test_apns_with_different_configs(user_id)
        analyze_environment_mismatch()
        
        if not success:
            print(f"\n🚨 CONCLUSION: Environment/Bundle ID mismatch detected")
            print(f"Your APNs configuration is correct, but doesn't match the FCM token environment")
    else:
        print("Usage: python3 diagnose_apns_bundle_mismatch.py <user_id>")

if __name__ == "__main__":
    main() 