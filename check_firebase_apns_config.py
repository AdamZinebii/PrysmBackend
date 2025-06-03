#!/usr/bin/env python3
"""
Script to check Firebase APNs configuration
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

def check_apns_configuration():
    """
    Check Firebase project APNs configuration status
    """
    print(f"🔍 FIREBASE APNs CONFIGURATION CHECK")
    print("=" * 50)
    
    try:
        init_firebase()
        
        # Test if we can create a basic message (this will reveal APNs auth issues)
        print("📋 Testing Firebase APNs Authentication...")
        
        # Create a test message to a fake token to see the error response
        fake_token = "fake_token_for_testing_apns_auth_" + "x" * 100
        
        test_message = messaging.Message(
            notification=messaging.Notification(
                title="APNs Test",
                body="Testing APNs configuration"
            ),
            token=fake_token,
            apns=messaging.APNSConfig(
                headers={
                    'apns-priority': '10',
                    'apns-push-type': 'alert'
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title="APNs Test",
                            body="Testing APNs configuration"
                        ),
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        try:
            response = messaging.send(test_message)
            print(f"✅ APNs appears to be configured (got response: {response})")
            return True
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ APNs Configuration Issue: {error_str}")
            
            # Analyze the specific error
            if "Auth error from APNS or Web Push Service" in error_str:
                print("\n🚨 APNS AUTHENTICATION PROBLEM DETECTED!")
                print("Possible causes:")
                print("1. ❌ No APNs Authentication Key (.p8) uploaded to Firebase")
                print("2. ❌ No APNs Certificates (.p12) uploaded to Firebase") 
                print("3. ❌ Wrong Apple Team ID in Firebase configuration")
                print("4. ❌ APNs key doesn't match your app's Bundle ID")
                print("5. ❌ APNs key expired or revoked")
                print("6. ❌ Development APNs config but TestFlight needs Production")
                
                print(f"\n💡 NEXT STEPS:")
                print(f"1. Check Firebase Console: https://console.firebase.google.com/project/prysmios/settings/cloudmessaging/")
                print(f"2. Verify iOS app configuration section")
                print(f"3. Ensure APNs Authentication Key or Certificates are uploaded")
                print(f"4. Verify Apple Team ID is correct")
                
                return False
                
            elif "The registration token is not a valid FCM registration token" in error_str:
                print("✅ APNs authentication appears OK (invalid token error expected)")
                print("💡 The fake token error confirms APNs is configured")
                return True
                
            else:
                print(f"⚠️ Unexpected error: {error_str}")
                return False
        
    except Exception as e:
        print(f"❌ Failed to check APNs configuration: {e}")
        return False

def check_project_info():
    """
    Check basic Firebase project information
    """
    print(f"\n📱 FIREBASE PROJECT INFO")
    print("-" * 30)
    
    try:
        # Get Firebase app info if available
        app = firebase_admin.get_app()
        print(f"✅ Firebase app initialized: {app.name}")
        
        # We can't directly query APNs config via Admin SDK
        # but we can check if the project has iOS apps configured
        print(f"📋 Firebase project appears to be configured")
        print(f"🔗 Check full config at: https://console.firebase.google.com/project/prysmios/settings/cloudmessaging/")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking project info: {e}")
        return False

def main():
    """
    Main function to run all checks
    """
    print("🧪 FIREBASE APNS DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Check basic project info
    project_ok = check_project_info()
    
    # Check APNs configuration
    apns_ok = check_apns_configuration()
    
    print(f"\n📊 SUMMARY")
    print("=" * 20)
    print(f"Project configured: {'✅ Yes' if project_ok else '❌ No'}")
    print(f"APNs authentication: {'✅ Working' if apns_ok else '❌ Problem detected'}")
    
    if not apns_ok:
        print(f"\n🎯 RECOMMENDED ACTION:")
        print(f"Visit Firebase Console and configure APNs authentication:")
        print(f"https://console.firebase.google.com/project/prysmios/settings/cloudmessaging/")

if __name__ == "__main__":
    main() 