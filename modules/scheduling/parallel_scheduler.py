import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from firebase_admin import firestore
from typing import List, Dict

logger = logging.getLogger(__name__)

class ParallelScheduler:
    """
    Rate-limited parallel scheduler for medium-scale applications.
    Processes multiple users concurrently with configurable limits.
    """
    
    def __init__(self, max_concurrent_users: int = 5, rate_limit_per_minute: int = 20):
        self.max_concurrent_users = max_concurrent_users
        self.rate_limit_per_minute = rate_limit_per_minute
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_users)
    
    def schedule_user_updates_parallel(self) -> dict:
        """
        Process user updates in parallel with rate limiting.
        Good compromise between simplicity and scalability.
        """
        try:
            logger.info(f"⏰ Starting parallel user scheduling (max {self.max_concurrent_users} concurrent)")
            
            current_time = datetime.now()
            db = firestore.client()
            
            # Get all users who need updates
            users_to_update = self._get_users_needing_updates(db, current_time)
            
            if not users_to_update:
                return {
                    "success": True,
                    "timestamp": current_time.isoformat(),
                    "total_users_checked": 0,
                    "users_processed": 0,
                    "message": "No users need updates"
                }
            
            logger.info(f"📋 Found {len(users_to_update)} users needing updates")
            
            # Process users in batches to respect rate limits
            batch_size = self.max_concurrent_users
            total_processed = 0
            successful_updates = 0
            failed_updates = 0
            
            for i in range(0, len(users_to_update), batch_size):
                batch = users_to_update[i:i + batch_size]
                
                # Process batch in parallel
                futures = []
                for user_info in batch:
                    future = self.executor.submit(self._process_single_user, user_info)
                    futures.append(future)
                
                # Wait for batch completion
                batch_results = []
                for future in futures:
                    try:
                        result = future.result(timeout=900)  # 15 min timeout per user
                        batch_results.append(result)
                        if result.get("success"):
                            successful_updates += 1
                        else:
                            failed_updates += 1
                    except Exception as e:
                        logger.error(f"❌ User update failed with exception: {e}")
                        failed_updates += 1
                
                total_processed += len(batch)
                logger.info(f"📊 Batch {i//batch_size + 1} complete: {len(batch)} users processed")
                
                # Rate limiting: wait between batches if needed
                if i + batch_size < len(users_to_update):
                    wait_time = 60 / (self.rate_limit_per_minute / batch_size)
                    if wait_time > 0:
                        logger.info(f"⏳ Rate limiting: waiting {wait_time:.1f}s before next batch")
                        asyncio.sleep(wait_time)
            
            summary = {
                "success": True,
                "timestamp": current_time.isoformat(),
                "total_users_checked": total_processed,
                "users_processed": total_processed,
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "processing_time_seconds": (datetime.now() - current_time).total_seconds(),
                "max_concurrent": self.max_concurrent_users
            }
            
            logger.info(f"✅ Parallel scheduling complete: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error in parallel scheduling: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_users_needing_updates(self, db, current_time: datetime) -> List[Dict]:
        """Get list of users who need updates"""
        users_to_update = []
        
        scheduling_ref = db.collection('scheduling_preferences')
        all_schedules = scheduling_ref.stream()
        
        for doc in all_schedules:
            user_id = doc.id
            scheduling_prefs = doc.to_dict()
            
            if self._should_trigger_update(user_id, scheduling_prefs, current_time):
                users_to_update.append({
                    'user_id': user_id,
                    'preferences': scheduling_prefs
                })
        
        return users_to_update
    
    def _process_single_user(self, user_info: Dict) -> Dict:
        """Process a single user update"""
        try:
            from modules.scheduling.tasks import update
            
            user_id = user_info['user_id']
            prefs = user_info['preferences']
            
            logger.info(f"🔄 Processing user {user_id} in parallel")
            
            # Call the existing update function
            result = update(
                user_id=user_id,
                presenter_name=prefs.get("presenter_name", "Alex"),
                language=prefs.get("language", "en"),
                voice_id=prefs.get("voice_id", "96c64eb5-a945-448f-9710-980abe7a514c")
            )
            
            if result.get("success"):
                logger.info(f"✅ Successfully processed user {user_id}")
            else:
                logger.error(f"❌ Failed to process user {user_id}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing user {user_info.get('user_id')}: {e}")
            return {"success": False, "error": str(e), "user_id": user_info.get('user_id')}
    
    def _should_trigger_update(self, user_id: str, prefs: dict, current_time: datetime) -> bool:
        """Check if user needs update based on their preferences"""
        from modules.scheduling.tasks import should_trigger_update_for_user
        return should_trigger_update_for_user(user_id, prefs, current_time)
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True) 