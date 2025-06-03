"""
Module pour les notifications push Firebase
"""
import sys
sys.stdout.write("--- main.py PYTHON SCRIPT STARTED (STDOUT) ---\n")
sys.stderr.write("--- main.py PYTHON SCRIPT STARTED (STDERR) ---\n")
print("--- main.py PYTHON SCRIPT STARTED (PRINT) ---")

# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

from firebase_admin import  firestore, messaging

def send_push_notification(user_id, title, body):
    """
    Send a push notification to a user using their FCM token.
    Enhanced for TestFlight compatibility.
    
    Args:
        user_id (str): User ID to send notification to
        title (str): Notification title
        body (str): Notification body
    
    Returns:
        dict: Result of the notification send
    """
    try:
        logger.info(f"📱 Sending push notification to user: {user_id}")
        
        # Get user's FCM token from Firestore
        db = firestore.client()
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            logger.warning(f"⚠️ User document not found for user_id: {user_id}")
            return {
                "success": False,
                "error": "User document not found",
                "user_id": user_id
            }
        
        user_data = user_doc.to_dict()
        fcm_token = user_data.get('fcmToken')
        
        if not fcm_token:
            logger.warning(f"⚠️ No FCM token found for user: {user_id}")
            return {
                "success": False,
                "error": "No FCM token found for user",
                "user_id": user_id
            }
        
        # Create FCM message with enhanced APNS configuration for TestFlight compatibility
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    click_action='FLUTTER_NOTIFICATION_CLICK'
                )
            ),
            apns=messaging.APNSConfig(
                headers={
                    # Use production environment for TestFlight
                    # Firebase automatically detects environment based on certificate/key
                    'apns-priority': '10',
                    'apns-push-type': 'alert'
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body
                        ),
                        sound='default',
                        badge=1,
                        # Ensure content is available for both foreground and background
                        content_available=True
                    )
                )
            )
        )
        
        # Send the message
        response = messaging.send(message)
        logger.info(f"✅ Push notification sent successfully: {response}")
        
        return {
            "success": True,
            "message_id": response,
            "user_id": user_id,
            "title": title,
            "body": body,
            "token_used": fcm_token[:10] + "..." + fcm_token[-10:] if len(fcm_token) > 20 else fcm_token
        }
        
    except messaging.UnregisteredError:
        logger.error(f"❌ FCM token is unregistered/invalid for user {user_id} - likely TestFlight token mismatch")
        return {
            "success": False,
            "error": "FCM token is unregistered or invalid (TestFlight environment mismatch possible)",
            "error_type": "UNREGISTERED_TOKEN",
            "user_id": user_id,
            "suggestion": "User needs to refresh FCM token in TestFlight environment"
        }
    except messaging.SenderIdMismatchError:
        logger.error(f"❌ Sender ID mismatch for user {user_id} - token belongs to different project")
        return {
            "success": False,
            "error": "Sender ID mismatch - token belongs to different Firebase project",
            "error_type": "SENDER_ID_MISMATCH",
            "user_id": user_id
        }
    except messaging.InvalidArgumentError as e:
        logger.error(f"❌ Invalid argument for user {user_id}: {e}")
        return {
            "success": False,
            "error": f"Invalid notification argument: {str(e)}",
            "error_type": "INVALID_ARGUMENT",
            "user_id": user_id
        }
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error sending push notification to user {user_id}: {error_str}")
        
        # Enhanced error analysis for TestFlight issues
        error_type = "UNKNOWN"
        suggestion = None
        
        if "Requested entity was not found" in error_str:
            error_type = "TOKEN_NOT_FOUND"
            suggestion = "FCM token expired or invalid - regenerate in TestFlight"
        elif "The registration token is not a valid FCM registration token" in error_str:
            error_type = "INVALID_TOKEN_FORMAT"
            suggestion = "Token format invalid - check iOS FCM implementation"
        elif "Sender ID mismatch" in error_str:
            error_type = "SENDER_MISMATCH"
            suggestion = "Token belongs to different Firebase project"
        elif "service unavailable" in error_str.lower():
            error_type = "SERVICE_UNAVAILABLE"
            suggestion = "Firebase/APNS service temporarily unavailable"
        
        return {
            "success": False,
            "error": error_str,
            "error_type": error_type,
            "user_id": user_id,
            "suggestion": suggestion
        }

def validate_fcm_token(fcm_token):
    """
    Validate FCM token format and basic structure.
    
    Args:
        fcm_token (str): FCM token to validate
    
    Returns:
        dict: Validation result
    """
    try:
        if not fcm_token:
            return {"valid": False, "error": "Token is empty"}
        
        if not isinstance(fcm_token, str):
            return {"valid": False, "error": "Token must be a string"}
        
        # Basic FCM token format validation
        token = fcm_token.strip()
        
        # FCM tokens are typically 163+ characters and contain specific patterns
        if len(token) < 100:
            return {"valid": False, "error": "Token too short for valid FCM token"}
        
        # Check for valid base64-like characters (FCM tokens use specific charset)
        import re
        if not re.match(r'^[A-Za-z0-9_:-]+$', token):
            return {"valid": False, "error": "Token contains invalid characters"}
        
        return {"valid": True, "token_length": len(token)}
        
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"} 