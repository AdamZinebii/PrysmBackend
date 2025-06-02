import sys


# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

from firebase_admin import firestore

from datetime import datetime
from modules.content.topics import convert_old_topic_to_gnews, find_parent_topic_for_subtopic, find_subtopic_in_catalog

def save_user_preferences_to_db(user_id, preferences_data):
    """
    Save user preferences to Firestore Database.
    
    Args:
        user_id (str): User ID
        preferences_data (dict): Preferences data with nested structure
                                New format v3.0:
                                {
                                    'preferences': {
                                        'business': {
                                            'Finance': {'subreddits': [...], 'queries': [...]}
                                        },
                                        'technology': {
                                            'AI': {'subreddits': [...], 'queries': [...]},
                                            'Gadgets': {'subreddits': [...], 'queries': [...]}
                                        }
                                    },
                                    'detail_level': 'Medium',
                                    'language': 'en',
                                    'format_version': '3.0'
                                }
    
    Returns:
        dict: Success status and any error
    """
    try:
        # Use Firestore instead of Realtime Database
        db_client = firestore.client()
        
        # Prepare data structure for new nested format
        format_version = preferences_data.get('format_version', '3.0')
        
        if format_version == '3.0':
            # New nested format
            data = {
                'preferences': preferences_data.get('preferences', {}),
                'detail_level': preferences_data.get('detail_level', 'Medium'),
                'language': preferences_data.get('language', 'en'),
                'format_version': '3.0',
                'updated_at': datetime.now().isoformat()
            }
            
            # Validate the new nested format
            if not isinstance(data['preferences'], dict):
                logger.error(f"Invalid preferences format for user {user_id}: expected dict, got {type(data['preferences'])}")
                return {"success": False, "error": "Invalid preferences format"}
            
            # Validate nested structure
            for topic_name, topic_subtopics in data['preferences'].items():
                if not isinstance(topic_subtopics, dict):
                    logger.error(f"Invalid topic structure for {topic_name}: expected dict, got {type(topic_subtopics)}")
                    return {"success": False, "error": f"Invalid topic structure for {topic_name}"}
                
                for subtopic_name, subtopic_data in topic_subtopics.items():
                    if not isinstance(subtopic_data, dict):
                        logger.error(f"Invalid subtopic data for {subtopic_name}: expected dict, got {type(subtopic_data)}")
                        return {"success": False, "error": f"Invalid subtopic data for {subtopic_name}"}
                    
                    if 'subreddits' not in subtopic_data or 'queries' not in subtopic_data:
                        logger.error(f"Missing required fields in subtopic {subtopic_name}")
                        return {"success": False, "error": f"Missing required fields in subtopic {subtopic_name}"}
                    
                    if not isinstance(subtopic_data['subreddits'], list) or not isinstance(subtopic_data['queries'], list):
                        logger.error(f"Invalid subreddits/queries format in subtopic {subtopic_name}")
                        return {"success": False, "error": f"Invalid subreddits/queries format in subtopic {subtopic_name}"}
            
            # Count topics and subtopics for logging
            topics_count = len(data['preferences'])
            subtopics_count = sum(len(topic_subtopics) for topic_subtopics in data['preferences'].values())
            
            logger.info(f"Preferences saved for user {user_id} in nested format v{data['format_version']}")
            logger.info(f"  - Topics: {topics_count} items")
            logger.info(f"  - Subtopics: {subtopics_count} items")
            
        else:
            # Legacy format (v2.0 or v1.0) - keep for backward compatibility
            data = {
                'topics': preferences_data.get('topics', []),
                'subtopics': preferences_data.get('subtopics', {}),
                'specific_subjects': preferences_data.get('specific_subjects', []),
                'detail_level': preferences_data.get('detail_level', 'Medium'),
                'language': preferences_data.get('language', 'en'),
                'format_version': preferences_data.get('format_version', '2.0'),
                'updated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Preferences saved for user {user_id} in legacy format v{data['format_version']}")
        
        # Save to Firestore
        doc_ref = db_client.collection('preferences').document(user_id)
        doc_ref.set(data)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error saving preferences to database: {e}")
        return {"success": False, "error": str(e)}

def update_specific_subjects_in_db(user_id, new_specific_subjects):
    """
    Update specific subjects in Firestore Database.
    
    Args:
        user_id (str): User ID
        new_specific_subjects (list): List of new specific subjects to add
    
    Returns:
        dict: Success status and any error
    """
    try:
        # Use Firestore instead of Realtime Database
        db_client = firestore.client()
        doc_ref = db_client.collection('preferences').document(user_id)
        
        # Get current preferences
        doc = doc_ref.get()
        current_data = doc.to_dict() if doc.exists else {}
        
        # Get existing specific subjects
        existing_subjects = current_data.get('specific_subjects', [])
        
        # Add new subjects (avoid duplicates)
        for subject in new_specific_subjects:
            if subject not in existing_subjects:
                existing_subjects.append(subject)
        
        # Update Firestore - use set with merge to handle non-existing documents
        doc_ref.set({
            'specific_subjects': existing_subjects,
            'updated_at': datetime.now().isoformat()
        }, merge=True)
        
        logger.info(f"Updated specific subjects for user {user_id}: {new_specific_subjects}")
        
        return {"success": True, "updated_subjects": existing_subjects}

    except Exception as e:
        logger.error(f"Error updating specific subjects: {e}")
        return {"success": False, "error": str(e)}

def get_user_preferences_from_db(user_id):
    """
    Get user preferences from Firestore Database.
    Handles v3.0 (nested), v2.0 (flat), and v1.0 (legacy) formats for backward compatibility.
    
    Args:
        user_id (str): User ID
    
    Returns:
        dict: User preferences or empty dict if not found
              New format v3.0:
              {
                  'preferences': {
                      'business': {
                          'Finance': {'subreddits': [...], 'queries': [...]}
                      },
                      'technology': {
                          'AI': {'subreddits': [...], 'queries': [...]},
                          'Gadgets': {'subreddits': [...], 'queries': [...]}
                      }
                  },
                  'detail_level': 'Medium',
                  'language': 'en',
                  'format_version': '3.0'
              }
    """
    try:
        # Use Firestore instead of Realtime Database
        db_client = firestore.client()
        doc_ref = db_client.collection('preferences').document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            format_version = data.get('format_version', '1.0')
            
            logger.info(f"Retrieved preferences for user {user_id} in format v{format_version}")
            
            # Handle new nested format (v3.0)
            if format_version == '3.0':
                # Validate new nested format structure
                if 'preferences' in data and isinstance(data['preferences'], dict):
                    topics_count = len(data['preferences'])
                    subtopics_count = sum(len(topic_subtopics) for topic_subtopics in data['preferences'].values())
                    logger.info(f"  - Topics: {topics_count} items")
                    logger.info(f"  - Subtopics: {subtopics_count} items")
                    return data
                else:
                    logger.warning(f"Invalid v3.0 format structure for user {user_id}, converting from legacy")
                    format_version = '2.0'  # Fall back to conversion
            
            # Handle v2.0 format or convert from v1.0
            if format_version == '2.0' or 'topics' in data or 'subtopics' in data:
                logger.info(f"Converting v2.0/legacy preferences for user {user_id} to v3.0 nested format")
                
                # Get old format data
                old_topics = data.get('topics', [])
                old_subtopics = data.get('subtopics', {})
                
                # Convert old topics (if they were localized) to GNews format
                converted_topics = []
                if isinstance(old_topics, list):
                    for topic in old_topics:
                        gnews_topic = convert_old_topic_to_gnews(topic)
                        if gnews_topic not in converted_topics:
                            converted_topics.append(gnews_topic)
                
                # Convert old flat subtopics to new nested format
                nested_preferences = {}
                
                # Initialize topics in nested structure
                for topic in converted_topics:
                    nested_preferences[topic] = {}
                
                # Distribute subtopics under their parent topics
                if isinstance(old_subtopics, dict):
                    for subtopic_name, subtopic_data in old_subtopics.items():
                        # Find which topic this subtopic belongs to
                        parent_topic = find_parent_topic_for_subtopic(subtopic_name)
                        
                        if parent_topic and parent_topic in nested_preferences:
                            # Convert subtopic data format if needed
                            if isinstance(subtopic_data, dict) and 'subreddits' in subtopic_data and 'queries' in subtopic_data:
                                nested_preferences[parent_topic][subtopic_name] = subtopic_data
                            else:
                                # Create basic structure for legacy data
                                subtopic_meta = find_subtopic_in_catalog(subtopic_name)
                                nested_preferences[parent_topic][subtopic_name] = {
                                    'subreddits': subtopic_meta.get('subreddits', []) if subtopic_meta else [],
                                    'queries': [subtopic_meta.get('query', subtopic_name)] if subtopic_meta else [subtopic_name]
                                }
                        else:
                            # If we can't find a parent topic, put it under 'general'
                            if 'general' not in nested_preferences:
                                nested_preferences['general'] = {}
                            
                            subtopic_meta = find_subtopic_in_catalog(subtopic_name)
                            nested_preferences['general'][subtopic_name] = {
                                'subreddits': subtopic_meta.get('subreddits', []) if subtopic_meta else [],
                                'queries': [subtopic_meta.get('query', subtopic_name)] if subtopic_meta else [subtopic_name]
                            }
                
                # Create new v3.0 format structure
                converted_data = {
                    'preferences': nested_preferences,
                    'detail_level': data.get('detail_level', 'Medium'),
                    'language': data.get('language', 'en'),
                    'format_version': '3.0',
                    'updated_at': data.get('updated_at', datetime.now().isoformat()),
                    'converted_from': format_version
                }
                
                topics_count = len(nested_preferences)
                subtopics_count = sum(len(topic_subtopics) for topic_subtopics in nested_preferences.values())
                logger.info(f"Converted preferences for user {user_id}:")
                logger.info(f"  - Topics: {topics_count} items")
                logger.info(f"  - Subtopics: {subtopics_count} items")
                
                # Optionally save the converted format back to database
                try:
                    doc_ref.set(converted_data)
                    logger.info(f"Saved converted v3.0 preferences for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to save converted preferences for user {user_id}: {e}")
                
                return converted_data
            
            # If we get here, it's an unknown format - return as is
            logger.warning(f"Unknown format version {format_version} for user {user_id}")
            return data
        else:
            logger.info(f"No preferences found for user {user_id}")
            return {}
            
    except Exception as e:
        logger.error(f"Error retrieving preferences: {e}")
        return {}


def get_user_articles_from_db(user_id):
    """
    Get stored articles for a user from the database.
    
    Args:
        user_id (str): User ID
    
    Returns:
        dict: Stored articles data or None if not found
    """
    try:
        db_client = firestore.client()
        doc_ref = db_client.collection('articles').document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            logger.info(f"Retrieved stored articles for user {user_id}")
            return data
        else:
            logger.info(f"No stored articles found for user {user_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving articles for user {user_id}: {e}")
        return None