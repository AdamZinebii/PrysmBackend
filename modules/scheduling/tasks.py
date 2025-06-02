import sys

# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

from firebase_admin import firestore
from datetime import datetime, timedelta

import time

from modules.utils.country import get_user_country_from_db


from modules.content.generation import get_complete_topic_report, get_topic_posts
from modules.database.operations import get_user_articles_from_db, get_user_preferences_from_db
from modules.notifications.push import send_push_notification
logger.info("--- main.py: Logging configured ---")


def update(user_id, presenter_name="Alex", language="en", voice_id="cmudN4ihcI42n48urXgc"):
    """
    Complete user update pipeline that chains three operations:
    1. Refresh articles for the user
    2. Generate complete report
    3. Generate simple podcast
    4. Send push notification
    
    Args:
        user_id (str): User ID to update
        presenter_name (str): Name of the presenter for podcast
        language (str): Language for the content ('en', 'fr', etc.)
        voice_id (str): ElevenLabs voice ID for TTS
    
    Returns:
        dict: Complete result with all operation results
    """
    try:
        logger.info(f"🚀 Starting complete update pipeline for user: {user_id}")
        
        # Step 1: Refresh articles
        logger.info(f"📰 Step 1/4: Refreshing articles for user {user_id}")
        refresh_result = refresh_articles(user_id)
        
        if not refresh_result.get("success"):
            raise Exception(f"Failed to refresh articles: {refresh_result.get('error', 'Unknown error')}")
        
        logger.info(f"✅ Articles refreshed: {refresh_result.get('total_articles_saved', 0)} articles")
        
        # Step 2: Generate complete report
        logger.info(f"📊 Step 2/4: Generating complete report for user {user_id}")
        report_result = get_complete_report(user_id)
        
        if not report_result.get("success"):
            raise Exception(f"Failed to generate complete report: {report_result.get('error', 'Unknown error')}")
        
        logger.info(f"✅ Complete report generated")
        
        # Step 3: Generate simple podcast
        logger.info(f"🎙️ Step 3/4: Generating podcast for user {user_id}")
        # Lazy import to avoid circular dependency
        from ..content.podcast import generate_simple_podcast
        
        podcast_result = generate_simple_podcast(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language,
            voice_id=voice_id
        )
        
        if not podcast_result.get("success"):
            raise Exception(f"Failed to generate podcast: {podcast_result.get('error', 'Unknown error')}")
        
        logger.info(f"✅ Podcast generated: {podcast_result.get('audio_url', 'No URL')}")
        
        # Step 4: Send push notification
        logger.info(f"📱 Step 4/4: Sending push notification to user {user_id}")
        notification_result = send_push_notification(
            user_id=user_id,
            title="Your updates are available",
            body="Fresh news articles and podcast are ready!"
        )
        
        if notification_result.get("success"):
            logger.info(f"✅ Push notification sent successfully")
        else:
            logger.warning(f"⚠️ Push notification failed: {notification_result.get('error', 'Unknown error')}")
        
        # Prepare complete result
        result = {
            "success": True,
            "user_id": user_id,
            "pipeline_completed": True,
            "refresh_result": {
                "success": refresh_result.get("success"),
                "total_articles": refresh_result.get("total_articles_saved", 0),
                "timestamp": refresh_result.get("timestamp")
            },
            "report_result": {
                "success": report_result.get("success"),
                "reports_count": len(report_result.get("reports", [])),
                "timestamp": report_result.get("timestamp")
            },
            "podcast_result": {
                "success": podcast_result.get("success"),
                "audio_url": podcast_result.get("audio_url"),
                "script_storage_url": podcast_result.get("script_storage_url"),
                "metadata": podcast_result.get("metadata", {})
            },
            "notification_result": {
                "success": notification_result.get("success"),
                "message_id": notification_result.get("message_id"),
                "error": notification_result.get("error") if not notification_result.get("success") else None
            },
            "pipeline_timestamp": datetime.now().isoformat(),
            "total_duration_estimate": "Complete pipeline execution"
        }
        
        logger.info(f"🎉 Complete update pipeline successful for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in update pipeline for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "pipeline_completed": False,
            "error": str(e),
            "message": "Failed to complete update pipeline",
            "timestamp": datetime.now().isoformat()
        }

# --- Scheduled User Updates ---

def should_trigger_update_for_user(user_id, scheduling_prefs, current_time):
    """
    Check if a user should receive an update based on their scheduling preferences.
    
    Args:
        user_id (str): User ID
        scheduling_prefs (dict): User's scheduling preferences
        current_time (datetime): Current datetime
    
    Returns:
        bool: True if update should be triggered
    """
    try:
        if not scheduling_prefs:
            logger.info(f"⏭️ No scheduling preferences for user {user_id}")
            return False
        
        pref_type = scheduling_prefs.get('type')
        pref_hour = scheduling_prefs.get('hour', 9)
        pref_minute = scheduling_prefs.get('minute', 0)
        pref_day = scheduling_prefs.get('day')  # Only for weekly
        
        # Create target time for today
        target_time = current_time.replace(hour=pref_hour, minute=pref_minute, second=0, microsecond=0)
        
        # Check if we're within the last 15 minutes of the target time
        time_diff = current_time - target_time
        
        # For daily scheduling
        if pref_type == 'daily':
            # Check if target time was within the last 15 minutes
            if timedelta(minutes=0) <= time_diff <= timedelta(minutes=15):
                logger.info(f"✅ Daily update trigger for user {user_id}: target was {target_time}, current is {current_time}")
                return True
        
        # For weekly scheduling
        elif pref_type == 'weekly' and pref_day:
            current_day = current_time.strftime('%A').lower()
            
            # Check if it's the right day and within the time window
            if current_day == pref_day.lower():
                if timedelta(minutes=0) <= time_diff <= timedelta(minutes=15):
                    logger.info(f"✅ Weekly update trigger for user {user_id}: target was {pref_day} {target_time}, current is {current_day} {current_time}")
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking update trigger for user {user_id}: {e}")
        return False

def trigger_user_update_async(user_id, presenter_name="Alex", language="en", voice_id="cmudN4ihcI42n48urXgc"):
    """
    Trigger user update asynchronously without blocking.
    
    Args:
        user_id (str): User ID to update
        presenter_name (str): Presenter name for podcast
        language (str): Content language
        voice_id (str): Voice ID for TTS
    """
    try:
        logger.info(f"🚀 Starting async update for user: {user_id}")
        
        # Create a thread to run the update without blocking
        def run_update():
            try:
                result = update(
                    user_id=user_id,
                    presenter_name=presenter_name,
                    language=language,
                    voice_id=voice_id
                )
                if result.get("success"):
                    logger.info(f"✅ Async update completed successfully for user {user_id}")
                else:
                    logger.error(f"❌ Async update failed for user {user_id}: {result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Exception in async update for user {user_id}: {e}")
        
        # Start the update in a separate thread
        import threading
        thread = threading.Thread(target=run_update, daemon=True)
        thread.start()
        
        logger.info(f"🔄 Async update thread started for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error starting async update for user {user_id}: {e}")

def refresh_articles(user_id):
    """
    Refresh all articles for a user by fetching content for each topic in their preferences
    and storing the results in the database.
    
    Args:
        user_id (str): User ID to refresh articles for
    
    Returns:
        dict: Response with format:
            {
                "success": True,
                "user_id": "user123",
                "topics_processed": 3,
                "total_articles": 45,
                "total_posts": 28,
                "refresh_timestamp": "2025-05-28T21:30:00Z",
                "topics": {
                    "business": {
                        "success": True,
                        "articles_count": 15,
                        "posts_count": 10
                    }
                }
            }
    """
    try:
        logger.info(f"Starting article refresh for user: {user_id}")
        
        # Step 1: Get user preferences
        user_preferences = get_user_preferences_from_db(user_id)
        
        if not user_preferences:
            logger.warning(f"No preferences found for user {user_id}")
            return {
                "success": False,
                "error": "No user preferences found",
                "user_id": user_id,
                "topics_processed": 0
            }
        
        # Check if preferences are in new nested format (v3.0)
        format_version = user_preferences.get('format_version', '2.0')
        
        if format_version != '3.0' or 'preferences' not in user_preferences:
            logger.error(f"User {user_id} preferences are not in v3.0 nested format")
            return {
                "success": False,
                "error": "User preferences must be in v3.0 nested format",
                "user_id": user_id,
                "topics_processed": 0
            }
        
        nested_preferences = user_preferences['preferences']
        lang = user_preferences.get('language', 'en')
        country = get_user_country_from_db(user_id)
        if not country or country == "us":
            # Fallback to old logic if no country in database
            country = 'us' if lang == 'en' else 'fr' if lang == 'fr' else 'us'

        logger.info(f"User {user_id} using language: {lang}, country: {country}")
        
        logger.info(f"Found {len(nested_preferences)} topics for user {user_id}")
        
        # Step 2: Process each topic
        refresh_result = {
            "success": True,
            "user_id": user_id,
            "topics_processed": 0,
            "total_articles": 0,
            "total_posts": 0,
            "refresh_timestamp": datetime.now().isoformat(),
            "topics": {}
        }
        
        all_topics_data = {}
        
        for topic_name, topic_subtopics in nested_preferences.items():
            logger.info(f"Processing topic: {topic_name} with {len(topic_subtopics)} subtopics")
            
            try:
                # Call get_topic_posts for this topic
                topic_result = get_topic_posts(
                    topic_name=topic_name,
                    topic_data=topic_subtopics,
                    lang=lang,
                    country=country
                )
                
                if topic_result.get("success"):
                    # Count articles and posts
                    data = topic_result.get("data", {})
                    topic_headlines = len(data.get("topic_headlines", []))
                    
                    topic_articles = topic_headlines
                    topic_posts = 0
                    
                    subtopics = data.get("subtopics", {})
                    for subtopic_name, subtopic_data in subtopics.items():
                        topic_articles += len(subtopic_data.get(subtopic_name, []))
                        topic_articles += sum(len(articles) for articles in subtopic_data.get("queries", {}).values())
                        topic_posts += sum(len(posts) for posts in subtopic_data.get("subreddits", {}).values())
                    
                    refresh_result["topics"][topic_name] = {
                        "success": True,
                        "articles_count": topic_articles,
                        "posts_count": topic_posts,
                        "subtopics_count": len(subtopics)
                    }
                    
                    refresh_result["total_articles"] += topic_articles
                    refresh_result["total_posts"] += topic_posts
                    refresh_result["topics_processed"] += 1
                    
                    # Store the complete topic data
                    all_topics_data[topic_name] = topic_result
                    
                    logger.info(f"✅ Topic {topic_name}: {topic_articles} articles, {topic_posts} posts")
                    
                else:
                    refresh_result["topics"][topic_name] = {
                        "success": False,
                        "error": topic_result.get("error", "Unknown error"),
                        "articles_count": 0,
                        "posts_count": 0
                    }
                    logger.error(f"❌ Failed to fetch topic {topic_name}: {topic_result.get('error', 'Unknown error')}")
                
                # Add delay between topics to avoid overwhelming APIs
                time.sleep(2)
                
            except Exception as e:
                refresh_result["topics"][topic_name] = {
                    "success": False,
                    "error": str(e),
                    "articles_count": 0,
                    "posts_count": 0
                }
                logger.error(f"❌ Error processing topic {topic_name}: {e}")
        
        # Step 3: Store in database
        if all_topics_data:
            try:
                db_client = firestore.client()
                
                # Prepare document for articles collection
                articles_document = {
                    "user_id": user_id,
                    "refresh_timestamp": refresh_result["refresh_timestamp"],
                    "topics_data": all_topics_data,
                    "summary": {
                        "topics_processed": refresh_result["topics_processed"],
                        "total_articles": refresh_result["total_articles"],
                        "total_posts": refresh_result["total_posts"],
                        "language": lang,
                        "country": country
                    },
                    "format_version": "1.0"
                }
                
                # Store in articles collection with user_id as document ID
                doc_ref = db_client.collection('articles').document(user_id)
                doc_ref.set(articles_document)
                
                logger.info(f"✅ Stored articles for user {user_id} in database")
                refresh_result["database_stored"] = True
                
            except Exception as e:
                logger.error(f"❌ Failed to store articles in database: {e}")
                refresh_result["database_stored"] = False
                refresh_result["database_error"] = str(e)
        else:
            logger.warning(f"No topics data to store for user {user_id}")
            refresh_result["database_stored"] = False
            refresh_result["database_error"] = "No topics data available"
        
        # Final summary
        logger.info(f"Article refresh completed for user {user_id}:")
        logger.info(f"  - Topics processed: {refresh_result['topics_processed']}")
        logger.info(f"  - Total articles: {refresh_result['total_articles']}")
        logger.info(f"  - Total posts: {refresh_result['total_posts']}")
        logger.info(f"  - Database stored: {refresh_result.get('database_stored', False)}")
        
        return refresh_result
        
    except Exception as e:
        logger.error(f"Error refreshing articles for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id,
            "topics_processed": 0,
            "total_articles": 0,
            "total_posts": 0
        }
    
def get_complete_report(user_id):
    """
    Generate complete reports for all topics for a user.
    Gets articles from database and calls get_complete_topic_report for each topic.
    
    Args:
        user_id (str): User ID to get articles for
    
    Returns:
        dict: Complete reports for all topics with format:
            {
                "success": True,
                "user_id": "user123",
                "reports": {
                    "business": {
                        "pickup_line": "...",
                        "topic_summary": "...",
                        "subtopics": {...}
                    },
                    "technology": {...}
                },
                "generation_stats": {
                    "topics_processed": 5,
                    "total_topics": 9,
                    "successful_reports": 5,
                    "failed_reports": 0
                }
            }
    """
    try:
        logger.info(f"Generating complete report for user: {user_id}")
        
        # Step 1: Get user articles from database
        articles_data = get_user_articles_from_db(user_id)
        
        if not articles_data:
            return {
                "success": False,
                "error": "No articles found for user",
                "user_id": user_id,
                "reports": {},
                "generation_stats": {
                    "topics_processed": 0,
                    "total_topics": 0,
                    "successful_reports": 0,
                    "failed_reports": 0
                }
            }
        
        topics = articles_data.get("topics_data", {})
        
        if not topics:
            return {
                "success": False,
                "error": "No topics found for user",
                "user_id": user_id,
                "reports": {},
                "generation_stats": {
                    "topics_processed": 0,
                    "total_topics": 0,
                    "successful_reports": 0,
                    "failed_reports": 0
                }
            }
        
        logger.info(f"Found {len(topics)} topics for user {user_id}")
        
        # Step 2: Initialize response
        complete_report = {
            "success": True,
            "user_id": user_id,
            "reports": {},
            "generation_stats": {
                "topics_processed": 0,
                "total_topics": len(topics),
                "successful_reports": 0,
                "failed_reports": 0
            },
            "refresh_timestamp": articles_data.get("refresh_timestamp"),
            "language": articles_data.get("summary", {}).get("language", "en")
        }
        
        # Step 3: Process each topic
        for topic_name, topic_data in topics.items():
            logger.info(f"Processing topic: {topic_name}")
            complete_report["generation_stats"]["topics_processed"] += 1
            
            try:
                # Call get_complete_topic_report for this topic
                topic_report = get_complete_topic_report(topic_name, topic_data)
                
                if topic_report.get("success"):
                    complete_report["reports"][topic_name] = {
                        "pickup_line": topic_report.get("pickup_line", ""),
                        "topic_summary": topic_report.get("topic_summary", ""),
                        "subtopics": topic_report.get("subtopics", {}),
                        "generation_stats": topic_report.get("generation_stats", {})
                    }
                    complete_report["generation_stats"]["successful_reports"] += 1
                    logger.info(f"✅ Successfully generated report for {topic_name}")
                else:
                    # Store failed report with fallback content
                    complete_report["reports"][topic_name] = {
                        "pickup_line": f"Discover the latest {topic_name} developments and trends.",
                        "topic_summary": f"# {topic_name}\n\nReport generation failed. Please try again.",
                        "subtopics": {},
                        "generation_stats": {"error": topic_report.get("error", "Unknown error")}
                    }
                    complete_report["generation_stats"]["failed_reports"] += 1
                    logger.warning(f"❌ Failed to generate report for {topic_name}: {topic_report.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error processing topic {topic_name}: {e}")
                complete_report["reports"][topic_name] = {
                    "pickup_line": f"Explore the latest {topic_name} news and insights.",
                    "topic_summary": f"# {topic_name}\n\nReport generation encountered an error.",
                    "subtopics": {},
                    "generation_stats": {"error": str(e)}
                }
                complete_report["generation_stats"]["failed_reports"] += 1
        
        # Step 4: Final statistics
        logger.info(f"Complete report generation finished for user {user_id}:")
        logger.info(f"  - Topics processed: {complete_report['generation_stats']['topics_processed']}")
        logger.info(f"  - Successful reports: {complete_report['generation_stats']['successful_reports']}")
        logger.info(f"  - Failed reports: {complete_report['generation_stats']['failed_reports']}")
        
        complete_report["generation_timestamp"] = datetime.now().isoformat()
        
        # Step 5: Save to aifeed collection

        
        try:
            logger.info(f"Saving complete report to aifeed collection for user {user_id}")
            db_client = firestore.client()
            aifeed_ref = db_client.collection('aifeed').document(user_id)
            
            # Prepare data for storage
            aifeed_data = {
                "user_id": user_id,
                "reports": complete_report["reports"],
                "generation_stats": complete_report["generation_stats"],
                "generation_timestamp": complete_report["generation_timestamp"],
                "refresh_timestamp": complete_report["refresh_timestamp"],
                "language": complete_report["language"],
                "format_version": "1.0"
            }
            
            # Save to database
            aifeed_ref.set(aifeed_data)
            logger.info(f"✅ Complete report saved to aifeed collection for user {user_id}")
            
            # Add database storage confirmation to response
            complete_report["database_stored"] = True
            complete_report["aifeed_collection"] = "aifeed"
            
        except Exception as e:
            logger.error(f"Error saving complete report to aifeed collection for user {user_id}: {e}")
            complete_report["database_stored"] = False
            complete_report["database_error"] = str(e)
        
        return complete_report
        
    except Exception as e:
        logger.error(f"Error generating complete report for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id,
            "reports": {},
            "generation_stats": {
                "topics_processed": 0,
                "total_topics": 0,
                "successful_reports": 0,
                "failed_reports": 0
            }
        }

def get_aifeed_reports(user_id):
    """
    Get AI feed reports for a user from the aifeed collection.
    
    Args:
        user_id (str): User ID
    
    Returns:
        dict: AI feed reports data or None if not found
    """
    try:
        db_client = firestore.client()
        doc_ref = db_client.collection('aifeed').document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            logger.info(f"Retrieved AI feed reports for user {user_id}")
            return {
                "success": True,
                "found": True,
                "data": data
            }
        else:
            logger.info(f"No AI feed reports found for user {user_id}")
            return {
                "success": True,
                "found": False,
                "message": "No AI feed reports found for this user"
            }
            
    except Exception as e:
        logger.error(f"Error retrieving AI feed reports for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }