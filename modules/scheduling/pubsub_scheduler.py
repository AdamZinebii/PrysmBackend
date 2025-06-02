import json
import logging
from datetime import datetime
from google.cloud import pubsub_v1
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class PubSubScheduler:
    """
    Pub/Sub-based scheduler for scalable user updates.
    Used by companies like Uber, Airbnb, Google for horizontal scaling.
    """
    
    def __init__(self, project_id: str, topic_name: str = "user-updates"):
        self.project_id = project_id
        self.topic_name = topic_name
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)
    
    def schedule_user_updates(self) -> dict:
        """
        Fast scheduler that publishes user update messages to Pub/Sub.
        Each message triggers a separate Cloud Function worker.
        """
        try:
            logger.info("⏰ Starting Pub/Sub user scheduling...")
            
            current_time = datetime.now()
            db = firestore.client()
            
            # Read all scheduling preferences (fast operation)
            scheduling_ref = db.collection('scheduling_preferences')
            all_schedules = scheduling_ref.stream()
            
            messages_published = 0
            total_users_checked = 0
            
            for doc in all_schedules:
                total_users_checked += 1
                user_id = doc.id
                scheduling_prefs = doc.to_dict()
                
                # Quick check if user needs update
                if self._should_trigger_update(user_id, scheduling_prefs, current_time):
                    # Create message payload
                    message_data = {
                        "user_id": user_id,
                        "presenter_name": scheduling_prefs.get("presenter_name", "Alex"),
                        "language": scheduling_prefs.get("language", "en"),
                        "voice_id": scheduling_prefs.get("voice_id", "96c64eb5-a945-448f-9710-980abe7a514c"),
                        "scheduled_time": current_time.isoformat(),
                        "priority": scheduling_prefs.get("priority", "normal")
                    }
                    
                    # Publish message to Pub/Sub
                    message_json = json.dumps(message_data)
                    future = self.publisher.publish(
                        self.topic_path, 
                        message_json.encode('utf-8'),
                        user_id=user_id,  # Message attributes for filtering
                        timestamp=current_time.isoformat()
                    )
                    
                    # Don't wait for publish to complete (async)
                    messages_published += 1
                    logger.info(f"📨 Published message for user {user_id}")
            
            summary = {
                "success": True,
                "timestamp": current_time.isoformat(),
                "total_users_checked": total_users_checked,
                "messages_published": messages_published,
                "processing_time_seconds": (datetime.now() - current_time).total_seconds()
            }
            
            logger.info(f"✅ Pub/Sub scheduling complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error in Pub/Sub scheduling: {e}")
            return {"success": False, "error": str(e)}
    
    def _should_trigger_update(self, user_id: str, prefs: dict, current_time: datetime) -> bool:
        """Check if user needs update based on their preferences"""
        # Import here to avoid circular imports
        from modules.scheduling.tasks import should_trigger_update_for_user
        return should_trigger_update_for_user(user_id, prefs, current_time)

# Cloud Function to handle Pub/Sub messages
def process_user_update_pubsub(cloud_event):
    """
    Cloud Function triggered by Pub/Sub messages.
    This allows unlimited parallel processing.
    
    Deploy with:
    gcloud functions deploy process_user_update_pubsub \
        --runtime python39 \
        --trigger-topic user-updates \
        --timeout 900s \
        --memory 1GB
    """
    import base64
    from modules.scheduling.tasks import update
    
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data['message']['data']).decode('utf-8')
        message_data = json.loads(pubsub_message)
        
        user_id = message_data.get('user_id')
        presenter_name = message_data.get('presenter_name', 'Alex')
        language = message_data.get('language', 'en')
        voice_id = message_data.get('voice_id', '96c64eb5-a945-448f-9710-980abe7a514c')
        scheduled_time = message_data.get('scheduled_time')
        
        logger.info(f"🔄 Processing Pub/Sub update for user {user_id} (scheduled: {scheduled_time})")
        
        # Call the existing update function
        result = update(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language,
            voice_id=voice_id
        )
        
        if result.get("success"):
            logger.info(f"✅ Successfully processed user {user_id} via Pub/Sub")
        else:
            logger.error(f"❌ Failed to process user {user_id}: {result.get('error')}")
            # In production, you might want to publish to a dead letter queue
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing Pub/Sub message: {e}")
        # In production, throw exception to trigger retry
        raise e 