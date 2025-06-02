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
        
        # Create FCM message
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
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
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
            "body": body
        }
        
    except Exception as e:
        logger.error(f"❌ Error sending push notification to user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        } 