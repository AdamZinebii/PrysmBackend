import sys
sys.stdout.write("--- main.py PYTHON SCRIPT STARTED (STDOUT) ---\n")
sys.stderr.write("--- main.py PYTHON SCRIPT STARTED (STDERR) ---\n")
print("--- main.py PYTHON SCRIPT STARTED (PRINT) ---")

# Configure logging AS EARLY AS POSSIBLE
import logging
logging.basicConfig(stream=sys.stderr, level=logging.INFO, force=True, format='%(levelname)s:%(name)s:%(asctime)s:%(message)s')
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

from firebase_functions import https_fn, scheduler_fn, options
from firebase_admin import initialize_app, firestore, messaging, storage, db
import openai
import feedparser
import urllib.parse
import json
import os
from datetime import datetime, timedelta
import serpapi
import re
from pathlib import Path
import uuid
import requests
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from elevenlabs import ElevenLabs
from modules.ai.client import analyze_and_update_specific_subjects, analyze_conversation_for_specific_subjects, build_system_prompt, generate_ai_response
from modules.audio.cartesia import generate_text_to_speech_cartesia
from modules.config import get_elevenlabs_key
from modules.content.generation import get_complete_topic_report, get_pickup_line, get_reddit_world_summary, get_topic_summary
from modules.content.podcast import generate_complete_user_media_twin_script, generate_media_twin_script, generate_simple_podcast, generate_user_media_twin_script
from modules.content.topics import extract_trending_subtopics, get_trending_topics_for_subtopic
from modules.database.operations import get_user_articles_from_db, get_user_preferences_from_db, save_user_preferences_to_db, update_specific_subjects_in_db
from modules.news.news_helper import get_articles_subtopics_user
from modules.news.serpapi import format_gnews_articles_for_prysm, gnews_search, gnews_top_headlines
from modules.notifications.push import send_push_notification
from modules.scheduling.tasks import get_aifeed_reports, get_complete_report, refresh_articles, should_trigger_update_for_user, trigger_user_update_async, update
from modules.content.simple_interactive_test import interactive_test
logger.info("--- main.py: Logging configured ---")

# Initialize Firebase app
# Using Firestore (no need for database URL)
initialize_app()

# --- GNews API Test Endpoint ---
@https_fn.on_request(timeout_sec=120)
def test_gnews_api(req: https_fn.Request) -> https_fn.Response:
    """Test endpoint for GNews API functionality."""
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
        
    if req.method not in ['GET', 'POST']:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use GET or POST.', headers=headers, status=405)
    
    try:
        # Get parameters from query string (GET) or JSON body (POST)
        if req.method == 'GET':
            endpoint = req.args.get('endpoint', 'search')
            query = req.args.get('query', 'technology')
            category = req.args.get('category', 'general')
            lang = req.args.get('lang', 'en')
            country = req.args.get('country', 'us')
            max_articles = int(req.args.get('max', '10'))
        else:  # POST
            data = req.get_json() or {}
            endpoint = data.get('endpoint', 'search')
            query = data.get('query', 'technology')
            category = data.get('category', 'general')
            lang = data.get('lang', 'en')
            country = data.get('country', 'us')
            max_articles = int(data.get('max', '10'))
        
        logger.info(f"Testing GNews API - Endpoint: {endpoint}, Query: {query}, Category: {category}")
        
        # Call appropriate GNews function
        if endpoint == 'search':
            gnews_response = gnews_search(
                query=query,
                lang=lang,
                country=country,
                max_articles=max_articles
            )
        elif endpoint == 'top-headlines':
            gnews_response = gnews_top_headlines(
                category=category,
                lang=lang,
                country=country,
                max_articles=max_articles,
                query=query if query != 'technology' else None  # Only add query if it's not the default
            )
        else:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Invalid endpoint. Use 'search' or 'top-headlines'"}),
                headers=headers,
                status=400
            )
        
        # Format articles for Prysm if successful
        formatted_articles = []
        if gnews_response.get("success"):
            formatted_articles = format_gnews_articles_for_prysm(gnews_response)
        
        # Prepare response
        response_data = {
            "endpoint": endpoint,
            "gnews_response": gnews_response,
            "formatted_articles": formatted_articles,
            "article_count": len(formatted_articles),
            "timestamp": datetime.now().isoformat()
        }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Error in test_gnews_api: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "error": str(e),
            "message": "An error occurred while testing GNews API",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

@https_fn.on_request(timeout_sec=120)
def fetch_news_with_gnews(req: https_fn.Request) -> https_fn.Response:
    """Fetch news articles using GNews API for a specific topic/query."""
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
        
    if req.method not in ['GET', 'POST']:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use GET or POST.', headers=headers, status=405)
    
    try:
        # Get parameters
        if req.method == 'GET':
            query = req.args.get('query')
            lang = req.args.get('lang', 'en')
            country = req.args.get('country', 'us')
            max_articles = int(req.args.get('max', '10'))
            use_headlines = req.args.get('use_headlines', 'false').lower() == 'true'
            category = req.args.get('category', 'general')
        else:  # POST
            data = req.get_json() or {}
            query = data.get('query')
            lang = data.get('lang', 'en')
            country = data.get('country', 'us')
            max_articles = int(data.get('max', '10'))
            use_headlines = data.get('use_headlines', False)
            category = data.get('category', 'general')
        
        if not query:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Missing 'query' parameter"}),
                headers=headers,
                status=400
            )
        
        logger.info(f"Fetching news for query: '{query}', lang: {lang}, country: {country}")
        
        # Choose endpoint based on use_headlines parameter
        if use_headlines:
            gnews_response = gnews_top_headlines(
                category=category,
                lang=lang,
                country=country,
                max_articles=max_articles,
                query=query
            )
        else:
            gnews_response = gnews_search(
                query=query,
                lang=lang,
                country=country,
                max_articles=max_articles
            )
        
        # Format articles for Prysm
        formatted_articles = format_gnews_articles_for_prysm(gnews_response)
        
        # Prepare response
        response_data = {
            "query": query,
            "success": gnews_response.get("success", False),
            "total_articles": gnews_response.get("totalArticles", 0),
            "returned_articles": len(formatted_articles),
            "articles": formatted_articles,
            "endpoint_used": "top-headlines" if use_headlines else "search",
            "error": gnews_response.get("error"),
            "timestamp": datetime.now().isoformat()
        }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Error in fetch_news_with_gnews: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "error": str(e),
            "message": "An error occurred while fetching news",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

# --- Conversation System ---


# --- New Firebase Functions ---

@https_fn.on_request(timeout_sec=60)
def save_initial_preferences(req: https_fn.Request) -> https_fn.Response:
    """
    Save initial user preferences to Firestore Database.
    
    Expected JSON payload (NEW NESTED FORMAT):
    {
        "user_id": "user123",
        "preferences": {
            "business": {
                "Finance": {
                    "subreddits": ["personalfinance", "stocks", "cryptocurrency"],
                    "queries": ["stock market", "bitcoin", "interest rates"]
                }
            },
            "technology": {
                "AI": {
                    "subreddits": ["MachineLearning", "ArtificialInteligence", "singularity"],
                    "queries": ["openai", "chatgpt", "large language models"]
                },
                "Gadgets": {
                    "subreddits": ["gadgets", "Android", "apple"],
                    "queries": ["smartphones", "wearables", "iPhone 15"]
                }
            }
        },
        "detail_level": "Medium",
        "language": "en"
    }
    """
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use POST.', headers=headers, status=405)
    
    try:
        # Parse request data
        data = req.get_json() or {}
        
        user_id = data.get('user_id')
        preferences = data.get('preferences', {})  # New nested structure
        detail_level = data.get('detail_level', 'Medium')
        language = data.get('language', 'en')
        
        # Validate required fields
        if not user_id:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Missing 'user_id' field"}),
                headers=headers,
                status=400
            )
        
        # Validate preferences format (nested structure)
        if not isinstance(preferences, dict):
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "'preferences' must be an object with nested topic structure"}),
                headers=headers,
                status=400
            )
        
        # Validate nested structure: topics -> subtopics -> {subreddits, queries}
        for topic_name, topic_subtopics in preferences.items():
            if not isinstance(topic_subtopics, dict):
                headers = {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                }
                return https_fn.Response(
                    json.dumps({"error": f"Topic '{topic_name}' must contain subtopics as an object"}),
                    headers=headers,
                    status=400
                )
            
            for subtopic_name, subtopic_data in topic_subtopics.items():
                if not isinstance(subtopic_data, dict):
                    headers = {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    }
                    return https_fn.Response(
                        json.dumps({"error": f"Subtopic '{subtopic_name}' in topic '{topic_name}' must have an object with 'subreddits' and 'queries'"}),
                        headers=headers,
                        status=400
                    )
                
                if 'subreddits' not in subtopic_data or 'queries' not in subtopic_data:
                    headers = {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    }
                    return https_fn.Response(
                        json.dumps({"error": f"Subtopic '{subtopic_name}' must have 'subreddits' and 'queries' fields"}),
                        headers=headers,
                        status=400
                    )
                
                if not isinstance(subtopic_data['subreddits'], list) or not isinstance(subtopic_data['queries'], list):
                    headers = {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    }
                    return https_fn.Response(
                        json.dumps({"error": f"Subtopic '{subtopic_name}' subreddits and queries must be arrays"}),
                        headers=headers,
                        status=400
                    )
        
        # Prepare preferences data in new nested format
        preferences_data = {
            'preferences': preferences,  # New nested structure
            'detail_level': detail_level,
            'language': language,
            'format_version': '3.0'  # Version marker for the new nested format
        }
        
        # Count topics and subtopics for logging
        topics_count = len(preferences)
        subtopics_count = sum(len(topic_subtopics) for topic_subtopics in preferences.values())
        
        logger.info(f"Saving preferences for user {user_id} in new nested format v3.0")
        logger.info(f"Topics: {list(preferences.keys())}")
        logger.info(f"Topics count: {topics_count}")
        logger.info(f"Subtopics count: {subtopics_count}")
        
        # Save to database
        result = save_user_preferences_to_db(user_id, preferences_data)
        
        if result["success"]:
            response_data = {
                "success": True,
                "message": "Initial preferences saved successfully in new nested format",
                "user_id": user_id,
                "format_version": "3.0",
                "topics_count": topics_count,
                "subtopics_count": subtopics_count,
                "timestamp": datetime.now().isoformat()
            }
        else:
            response_data = {
                "success": False,
                "error": result.get("error", "Failed to save preferences"),
                "timestamp": datetime.now().isoformat()
            }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Error in save_initial_preferences: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while saving preferences",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

@https_fn.on_request(timeout_sec=60)
def update_specific_subjects(req: https_fn.Request) -> https_fn.Response:
    """
    Update specific subjects for a user based on conversation analysis.
    This function is called in parallel after each user message.
    
    Expected JSON payload:
    {
        "user_id": "user123",
        "conversation_history": [...],
        "user_message": "I'm interested in Tesla and SpaceX",
        "language": "en"
    }
    """
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use POST.', headers=headers, status=405)
    
    try:
        # Parse request data
        data = req.get_json() or {}
        
        user_id = data.get('user_id')
        action = data.get('action', 'analyze')  # 'analyze' or 'get'
        conversation_history = data.get('conversation_history', [])
        user_message = data.get('user_message', '')
        language = data.get('language', 'en')
        
        # Validate required fields
        if not user_id:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Missing 'user_id' field"}),
                headers=headers,
                status=400
            )
        
        # Handle 'get' action - just return existing specific subjects
        if action == 'get':
            try:
                existing_preferences = get_user_preferences_from_db(user_id)
                specific_subjects = existing_preferences.get('specific_subjects', []) if existing_preferences else []
                response_data = {
                    "success": True,
                    "specific_subjects": specific_subjects,
                    "total_subjects": len(specific_subjects),
                    "timestamp": datetime.now().isoformat()
                }
                headers = {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                }
                return https_fn.Response(json.dumps(response_data), headers=headers)
            except Exception as e:
                logger.error(f"Error getting specific subjects: {e}")
                response_data = {
                    "success": True,
                    "specific_subjects": [],
                    "total_subjects": 0,
                    "timestamp": datetime.now().isoformat()
                }
                headers = {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                }
                return https_fn.Response(json.dumps(response_data), headers=headers)
        
        # For 'analyze' action, we need user_message
        if not user_message:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Missing 'user_message' field for analyze action"}),
                headers=headers,
                status=400
            )
        
        logger.info(f"Analyzing conversation for user {user_id}")
        
        # Analyze conversation for specific subjects
        analysis_result = analyze_conversation_for_specific_subjects(
            conversation_history, user_message, language
        )
        
        if analysis_result["success"] and analysis_result.get("specific_subjects"):
            # Update database with new specific subjects
            update_result = update_specific_subjects_in_db(
                user_id, analysis_result["specific_subjects"]
            )
            
            response_data = {
                "success": True,
                "new_subjects_found": analysis_result["specific_subjects"],
                "total_subjects": update_result.get("updated_subjects", []),
                "analysis_usage": analysis_result.get("usage", {}),
                "timestamp": datetime.now().isoformat()
            }
        else:
            response_data = {
                "success": True,
                "new_subjects_found": [],
                "message": "No new specific subjects found in this message",
                "timestamp": datetime.now().isoformat()
            }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Error in update_specific_subjects: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while updating specific subjects",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

@https_fn.on_request(timeout_sec=120)
def answer(req: https_fn.Request) -> https_fn.Response:
    """
    Handle conversation with AI assistant based on user preferences.
    
    Expected JSON payload:
    {
        "user_id": "user123",  # Optional - for saving specific subjects
        "user_preferences": {
            "subjects": ["technology", "sports"],
            "subtopics": ["AI", "Tennis"],
            "detail_level": "Medium",
            "language": "en"
        },
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you?"}
        ],
        "user_message": "I want to know about tech news"
    }
    """
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use POST.', headers=headers, status=405)
    
    try:
        # Parse request data
        data = req.get_json() or {}
        
        user_id = data.get('user_id')  # Optional for specific subjects tracking
        user_preferences = data.get('user_preferences', {})
        conversation_history = data.get('conversation_history', [])
        user_message = data.get('user_message', '')
        
        # Validate required fields
        if not user_message:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Missing 'user_message' field"}),
                headers=headers,
                status=400
            )
        
        logger.info(f"Processing conversation - User ID: {user_id}")
        logger.info(f"User message: {user_message}")
        logger.info(f"Using current local preferences: {user_preferences}")
        
        # Always use the preferences sent in the request (current local preferences)
        # These are the user's current choices, not what's saved in database
        
        # Build system prompt based on current user preferences
        system_prompt = build_system_prompt(user_preferences)
        
        # Check if user wants to end conversation
        end_conversation_keywords = {
            'en': ['yes', 'sure', 'ok', 'okay', 'start reading', 'read news', 'go ahead', 'let\'s go'],
            'fr': ['oui', 'bien sûr', 'd\'accord', 'ok', 'commencer', 'lire', 'allons-y', 'c\'est parti'],
            'es': ['sí', 'claro', 'de acuerdo', 'ok', 'empezar', 'leer', 'vamos', 'adelante'],
            'ar': ['نعم', 'موافق', 'حسناً', 'ابدأ', 'اقرأ', 'هيا']
        }
        
        user_language = user_preferences.get('language', 'en')
        user_msg_lower = user_message.lower().strip()
        
        # Check if this might be a conversation ending response
        is_ending_response = False
        if user_language in end_conversation_keywords:
            keywords = end_conversation_keywords[user_language]
            is_ending_response = any(keyword in user_msg_lower for keyword in keywords)
        
        # Generate AI response
        ai_response = generate_ai_response(system_prompt, conversation_history, user_message)
        
        # If user_id is provided, analyze for specific subjects synchronously
        # This ensures the analysis happens but may add slight delay
        if user_id and user_message.strip():
            try:
                # Run analysis synchronously to ensure it completes
                analyze_and_update_specific_subjects(
                    user_id,
                    conversation_history,
                    user_message,
                    user_preferences.get('language', 'en')
                )
                logger.info(f"Completed analysis for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to analyze specific subjects: {e}")
                # Don't fail the main response if analysis fails
        
        if not ai_response["success"]:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({
                    "error": "Failed to generate AI response",
                    "details": ai_response.get("error")
                }),
                headers=headers,
                status=500
            )
        
        # Check if AI suggests ending the conversation
        ai_message = ai_response["message"].lower()
        ai_suggests_ending = any(phrase in ai_message for phrase in [
            'personalized news feed is ready', 'flux d\'actualités personnalisé est prêt', 
            'feed de noticias personalizado está listo', 'تدفق الأخبار المخصص لك جاهز',
            'start reading', 'commencer à lire', 'empezar a leer', 'البدء في قراءة'
        ])
        
        # Prepare response
        response_data = {
            "success": True,
            "ai_message": ai_response["message"],
            "conversation_id": str(uuid.uuid4()),  # Generate conversation ID for tracking
            "timestamp": datetime.now().isoformat(),
            "usage": ai_response.get("usage", {}),
            "user_preferences": user_preferences,
            "conversation_ending": is_ending_response or ai_suggests_ending,
            "ready_for_news": ai_suggests_ending
        }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"AI response generated successfully: {len(ai_response['message'])} characters")
        
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Error in answer function: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while processing the conversation",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

# --- Trending Subtopics Analysis ---

@https_fn.on_request(timeout_sec=120)
def get_trending_for_subtopic(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to get trending topics for a specific subtopic.
    
    Expected request body:
    {
        "subtopic_title": "Artificial Intelligence",
        "subtopic_query": "artificial intelligence OR AI",
        "subreddits": ["MachineLearning", "Artificial", "singularity"],
        "lang": "en",
        "country": "us",
        "max_articles": 10
    }
    """
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use POST.', headers=headers, status=405)
    
    try:
        request_data = req.get_json()
        if not request_data:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"success": False, "error": "No JSON data provided"}),
                headers=headers,
                status=400
            )
        
        # Extract parameters
        subtopic_title = request_data.get('subtopic_title')
        subtopic_query = request_data.get('subtopic_query')
        subreddits = request_data.get('subreddits', [])
        
        if not subtopic_title or not subtopic_query:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"success": False, "error": "subtopic_title and subtopic_query are required"}),
                headers=headers,
                status=400
            )
        
        lang = request_data.get('lang', 'en')
        country = request_data.get('country', 'us')
        max_articles = request_data.get('max_articles', 10)
        
        logger.info(f"Getting trending topics for subtopic: {subtopic_title}")
        
        # Call the analysis function
        result = get_trending_topics_for_subtopic(
            subtopic_title=subtopic_title,
            subtopic_query=subtopic_query,
            subreddits=subreddits,
            lang=lang,
            country=country,
            max_articles=max_articles
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_trending_for_subtopic endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e), "trending_topics": []}),
            headers=headers,
            status=500
        )

@https_fn.on_request(timeout_sec=120)
def get_trending_subtopics(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to get trending subtopics for a given topic.
    
    Expected request body:
    {
        "topic": "technology",
        "lang": "en",
        "country": "us",
        "max_articles": 10
    }
    
    Returns:
    {
        "success": true,
        "topic": "technology",
        "articles_analyzed": 10,
        "subtopics": ["AI regulation", "ChatGPT updates", "tech layoffs", ...]
    }
    """
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use POST.', headers=headers, status=405)
    
    try:
        # Parse request body
        request_data = req.get_json()
        if not request_data:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"success": False, "error": "No JSON data provided"}),
                headers=headers,
                status=400
            )
        
        # Extract parameters
        topic = request_data.get('topic')
        if not topic:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"success": False, "error": "Topic is required"}),
                headers=headers,
                status=400
            )
        
        lang = request_data.get('lang', 'en')
        country = request_data.get('country', 'us')
        max_articles = request_data.get('max_articles', 10)
        
        # Validate max_articles
        max_articles = min(max(1, max_articles), 20)  # Between 1 and 20
        
        logger.info(f"Getting trending subtopics for topic: {topic}, lang: {lang}, country: {country}")
        
        # Call the analysis function
        result = extract_trending_subtopics(
            topic=topic,
            lang=lang,
            country=country,
            max_articles=max_articles
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_trending_subtopics endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e), "subtopics": []}),
            headers=headers,
            status=500
        )

@https_fn.on_request(timeout_sec=30)
def get_user_preferences(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP function to get user preferences for updating.
    
    Expected request:
    {
        "user_id": "user123"
    }
    
    Returns:
    {
        "success": true,
        "preferences": {
            "topics": ["world", "business"],
            "subtopics": {
                "AI": {"subreddits": [...], "queries": [...]},
                "Finance": {"subreddits": [...], "queries": [...]}
            },
            "detail_level": "Medium",
            "language": "en",
            "format_version": "2.0"
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        if not user_id:
            raise ValueError("Missing user_id")
        
        logger.info(f"Getting preferences for user: {user_id}")
        
        # Get preferences from database
        preferences = get_user_preferences_from_db(user_id)
        
        if preferences:
            # Remove internal fields that shouldn't be sent to client
            if preferences.get('format_version') == '3.0':
                # New nested format
                client_preferences = {
                    'preferences': preferences.get('preferences', {}),
                    'detail_level': preferences.get('detail_level', 'Medium'),
                    'language': preferences.get('language', 'en'),
                    'format_version': '3.0'
                }
                
                topics_count = len(client_preferences['preferences'])
                subtopics_count = sum(len(topic_subtopics) for topic_subtopics in client_preferences['preferences'].values())
                
                logger.info(f"Successfully retrieved v3.0 preferences for user {user_id}")
                logger.info(f"  - Topics: {topics_count} items")
                logger.info(f"  - Subtopics: {subtopics_count} items")
                
            else:
                # Legacy format (v2.0 or older) - convert for backward compatibility
                client_preferences = {
                    'topics': preferences.get('topics', []),
                    'subtopics': preferences.get('subtopics', {}),
                    'detail_level': preferences.get('detail_level', 'Medium'),
                    'language': preferences.get('language', 'en'),
                    'format_version': preferences.get('format_version', '2.0'),
                    'specific_subjects': preferences.get('specific_subjects', [])  # Include for backward compatibility
                }
                
                logger.info(f"Successfully retrieved legacy preferences for user {user_id}")
                logger.info(f"  - Topics: {len(client_preferences['topics'])} items")
                logger.info(f"  - Subtopics: {len(client_preferences['subtopics'])} items")
            
            response_data = {
                "success": True,
                "preferences": client_preferences,
                "message": "Preferences retrieved successfully",
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            # No preferences found - return empty structure in new format
            response_data = {
                "success": True,
                "preferences": {
                    'preferences': {},
                    'detail_level': 'Medium',
                    'language': 'en',
                    'format_version': '3.0'
                },
                "message": "No existing preferences found",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"No preferences found for user {user_id}, returning empty v3.0 structure")
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Error in get_user_preferences: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while retrieving preferences",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

@https_fn.on_request(timeout_sec=120)
def get_articles_subtopics_user_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to fetch articles and Reddit posts for a user's subtopic.
    
    Expected request (POST):
    {
        "subtopic_name": "Finance",
        "subtopic_data": {
            "subreddits": ["personalfinance", "stocks", "cryptocurrency"],
            "queries": ["stock market", "bitcoin", "interest rates"]
        },
        "lang": "en",
        "country": "us",
        "include_comments": false,  // Optional: whether to fetch top comments for Reddit posts
        "max_comments": 3          // Optional: max number of comments per post (default: 3)
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "Finance": [top2_articles],
            "subreddits": {
                "personalfinance": [
                    {
                        "title": "Post title",
                        "score": 123,
                        "url": "https://reddit.com/...",
                        "subreddit": "personalfinance",
                        "created_utc": 1716883200.0,
                        "num_comments": 45,
                        "author": "username",
                        "selftext": "Full post text...",
                        "comments": [  // Only if include_comments=true
                            {
                                "body": "Comment text",
                                "author": "commenter",
                                "score": 67,
                                "created_utc": 1716883300.0,
                                "replies_count": 3,
                                "is_submitter": false,
                                "distinguished": null,
                                "stickied": false
                            }
                        ]
                    }
                ]
            },
            "queries": {
                "stock market": [top2_articles],
                "bitcoin": [top2_articles],
                "interest rates": [top2_articles]
            }
        },
        "summary": {
            "subtopic_articles": 2,
            "query_articles": 6,
            "reddit_posts": 6,
            "total_queries": 3,
            "total_subreddits": 3
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        subtopic_name = data.get('subtopic_name')
        subtopic_data = data.get('subtopic_data')
        lang = data.get('lang', 'en')
        country = data.get('country', 'us')
        include_comments = data.get('include_comments', False)
        max_comments = data.get('max_comments', 3)
        
        # Validate required parameters
        if not subtopic_name:
            raise ValueError("Missing subtopic_name")
        
        if not subtopic_data:
            raise ValueError("Missing subtopic_data")
        
        if not isinstance(subtopic_data, dict):
            raise ValueError("subtopic_data must be an object")
        
        if 'subreddits' not in subtopic_data or 'queries' not in subtopic_data:
            raise ValueError("subtopic_data must contain 'subreddits' and 'queries' fields")
        
        if not isinstance(subtopic_data['subreddits'], list) or not isinstance(subtopic_data['queries'], list):
            raise ValueError("subreddits and queries must be arrays")
        
        logger.info(f"Fetching content for subtopic: {subtopic_name}")
        logger.info(f"  - Subreddits: {subtopic_data['subreddits']}")
        logger.info(f"  - Queries: {subtopic_data['queries']}")
        logger.info(f"  - Language: {lang}, Country: {country}")
        
        # Call the main function
        result = get_articles_subtopics_user(
            subtopic_name=subtopic_name,
            subtopic_data=subtopic_data,
            lang=lang,
            country=country,
            include_comments=include_comments,
            max_comments=max_comments
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_articles_subtopics_user_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while fetching subtopic content",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=180)
def get_topic_posts_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to fetch articles and Reddit posts for a complete user topic.
    
    Expected request (POST):
    {
        "topic_name": "business",
        "topic_data": {
            "Finance": {
                "subreddits": ["personalfinance", "stocks", "cryptocurrency"],
                "queries": ["stock market", "bitcoin", "interest rates"]
            },
            "Economy": {
                "subreddits": ["economics", "investing"],
                "queries": ["inflation", "GDP", "economic policy"]
            }
        },
        "lang": "en",
        "country": "us"
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "topic_headlines": [top2_headlines_for_topic],
            "subtopics": {
                "Finance": {
                    "Finance": [top2_articles],
                    "subreddits": {...},
                    "queries": {...}
                },
                "Economy": {
                    "Economy": [top2_articles],
                    "subreddits": {...},
                    "queries": {...}
                }
            }
        },
        "summary": {
            "topic_headlines": 2,
            "subtopics_processed": 2,
            "total_subtopic_articles": 4,
            "total_query_articles": 12,
            "total_reddit_posts": 12
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        topic_name = data.get('topic_name')
        topic_data = data.get('topic_data')
        lang = data.get('lang', 'en')
        country = data.get('country', 'us')
        
        # Validate required parameters
        if not topic_name:
            raise ValueError("Missing topic_name")
        
        if not topic_data:
            raise ValueError("Missing topic_data")
        
        if not isinstance(topic_data, dict):
            raise ValueError("topic_data must be an object")
        
        # Validate topic_data structure
        for subtopic_name, subtopic_data in topic_data.items():
            if not isinstance(subtopic_data, dict):
                raise ValueError(f"Subtopic '{subtopic_name}' must be an object")
            
            if 'subreddits' not in subtopic_data or 'queries' not in subtopic_data:
                raise ValueError(f"Subtopic '{subtopic_name}' must have 'subreddits' and 'queries' fields")
            
            if not isinstance(subtopic_data['subreddits'], list) or not isinstance(subtopic_data['queries'], list):
                raise ValueError(f"Subtopic '{subtopic_name}' subreddits and queries must be arrays")
        
        logger.info(f"Processing topic: {topic_name} with {len(topic_data)} subtopics")
        logger.info(f"  - Subtopics: {list(topic_data.keys())}")
        logger.info(f"  - Language: {lang}, Country: {country}")
        
        # Call the main function
        result = get_topic_posts(
            topic_name=topic_name,
            topic_data=topic_data,
            lang=lang,
            country=country
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_topic_posts_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while fetching topic content",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)



@https_fn.on_request(timeout_sec=60)
def get_pickup_line_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to generate pickup lines for topics.
    
    Expected request (POST):
    {
        "topic_name": "Business",
        "topic_content_data": {
            "success": true,
            "data": {
                "topic_headlines": [...],
                "subtopics": {...}
            }
        }
    }
    
    Returns:
    {
        "success": true,
        "pickup_line": "One engaging sentence...",
        "topic_name": "Business",
        "content_summary": {
            "total_articles": 15,
            "subtopics_count": 3,
            "trending_keywords": ["AI", "stocks", "inflation"]
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        topic_name = data.get('topic_name')
        topic_content_data = data.get('topic_content_data')
        
        # Validate required parameters
        if not topic_name:
            raise ValueError("Missing topic_name")
        
        if not topic_content_data:
            raise ValueError("Missing topic_content_data")
        
        if not isinstance(topic_content_data, dict):
            raise ValueError("topic_content_data must be an object")
        
        logger.info(f"Generating pickup line for topic: {topic_name}")
        
        # Call the main function
        result = get_pickup_line(
            topic_name=topic_name,
            topic_content_data=topic_content_data
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_pickup_line_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating pickup line",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=90)
def get_topic_summary_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to generate comprehensive topic summaries.
    
    Expected request (POST):
    {
        "topic_name": "Business",
        "topic_content_data": {
            "success": true,
            "data": {
                "topic_headlines": [...],
                "subtopics": {...}
            }
        }
    }
    
    Returns:
    {
        "success": true,
        "topic_summary": "Comprehensive formatted summary...",
        "topic_name": "Business",
        "content_stats": {
            "total_articles": 15,
            "total_posts": 8,
            "subtopics_analyzed": 3
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        topic_name = data.get('topic_name')
        topic_content_data = data.get('topic_content_data')
        
        # Validate required parameters
        if not topic_name:
            raise ValueError("Missing topic_name")
        
        if not topic_content_data:
            raise ValueError("Missing topic_content_data")
        
        if not isinstance(topic_content_data, dict):
            raise ValueError("topic_content_data must be an object")
        
        logger.info(f"Generating comprehensive summary for topic: {topic_name}")
        
        # Call the main function
        result = get_topic_summary(
            topic_name=topic_name,
            topic_content_data=topic_content_data
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_topic_summary_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating topic summary",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=60)
def get_reddit_world_summary_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to generate executive world summaries from Reddit posts.
    
    Expected request (POST):
    {
        "reddit_posts": [
            {
                "title": "Post title",
                "score": 123,
                "url": "https://reddit.com/...",
                "subreddit": "worldnews",
                "selftext": "Post content...",
                "comments": [
                    {
                        "body": "Comment text",
                        "author": "username",
                        "score": 67
                    }
                ]
            }
        ]
    }
    
    Returns:
    {
        "success": true,
        "world_summary": "Executive summary of world events...",
        "posts_analyzed": 15,
        "relevant_posts": 8,
        "key_topics": ["Trump", "AI", "China"]
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        reddit_posts = data.get('reddit_posts', [])
        
        # Validate required parameters
        if not isinstance(reddit_posts, list):
            raise ValueError("reddit_posts must be an array")
        
        logger.info(f"Generating world summary from {len(reddit_posts)} Reddit posts")
        
        # Call the main function
        result = get_reddit_world_summary(reddit_posts_data=reddit_posts)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_reddit_world_summary_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating Reddit world summary",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=300)
def get_complete_topic_report_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to generate complete topic reports.
    
    Expected request (POST):
    {
        "topic_name": "Business",
        "topic_posts_data": {
            "success": true,
            "data": {
                "topic_headlines": [...],
                "subtopics": {...}
            }
        }
    }
    
    Returns:
    {
        "success": true,
        "topic_name": "Business",
        "pickup_line": "Engaging 3-sentence hook...",
        "topic_summary": "Comprehensive topic overview...",
        "subtopics": {
            "Finance": {
                "subtopic_summary": "Summary of Finance articles...",
                "reddit_summary": "Executive brief of Finance Reddit discussions..."
            }
        },
        "generation_stats": {
            "pickup_line_generated": true,
            "topic_summary_generated": true,
            "subtopics_processed": 2,
            "total_subtopics": 2
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        topic_name = data.get('topic_name')
        topic_posts_data = data.get('topic_posts_data')
        
        # Validate required parameters
        if not topic_name:
            raise ValueError("Missing topic_name")
        
        if not topic_posts_data:
            raise ValueError("Missing topic_posts_data")
        
        if not isinstance(topic_posts_data, dict):
            raise ValueError("topic_posts_data must be an object")
        
        logger.info(f"Generating complete topic report for: {topic_name}")
        
        # Call the main function
        result = get_complete_topic_report(
            topic_name=topic_name,
            topic_posts_data=topic_posts_data
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in get_complete_topic_report_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating complete topic report",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=600)
def refresh_articles_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to refresh articles for a user.
    
    Expected request (POST):
    {
        "user_id": "user123"
    }
    
    Returns:
    {
        "success": true,
        "user_id": "user123",
        "topics_processed": 3,
        "total_articles": 45,
        "total_posts": 28,
        "refresh_timestamp": "2025-05-28T21:30:00Z",
        "database_stored": true,
        "topics": {
            "business": {
                "success": true,
                "articles_count": 15,
                "posts_count": 10,
                "subtopics_count": 2
            },
            "technology": {
                "success": true,
                "articles_count": 20,
                "posts_count": 12,
                "subtopics_count": 3
            }
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        
        # Validate required parameters
        if not user_id:
            raise ValueError("Missing user_id")
        
        logger.info(f"Starting article refresh for user: {user_id}")
        
        # Call the main function
        result = refresh_articles(user_id=user_id)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in refresh_articles_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while refreshing articles",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)



@https_fn.on_request(timeout_sec=30)
def get_user_articles_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to get stored articles for a user.
    
    Expected request (POST):
    {
        "user_id": "user123"
    }
    
    Returns stored articles data or 404 if not found.
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        
        if not user_id:
            raise ValueError("Missing user_id")
        
        # Get articles from database
        articles_data = get_user_articles_from_db(user_id)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        if articles_data:
            return https_fn.Response(
                json.dumps({
                    "success": True,
                    "found": True,
                    "data": articles_data
                }),
                headers=headers
            )
        else:
            return https_fn.Response(
                json.dumps({
                    "success": True,
                    "found": False,
                    "message": "No articles found for this user"
                }),
                headers=headers,
                status=404
            )
        
    except Exception as e:
        logger.error(f"Error in get_user_articles_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while retrieving articles",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=600)
def get_complete_report_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to generate complete reports for all user topics.
    
    Expected request (POST):
    {
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02"
    }
    
    Returns:
    {
        "success": true,
        "user_id": "user123",
        "reports": {
            "business": {
                "pickup_line": "...",
                "topic_summary": "...",
                "subtopics": {...}
            }
        },
        "generation_stats": {...}
    }
    """
    # Enable CORS
    if req.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return https_fn.Response("", status=204, headers=headers)

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }

    try:
        # Parse request
        request_json = req.get_json(silent=True)
        if not request_json:
            return https_fn.Response(
                json.dumps({"success": False, "error": "No JSON data provided"}),
                status=400,
                headers=headers
            )

        user_id = request_json.get("user_id")
        if not user_id:
            return https_fn.Response(
                json.dumps({"success": False, "error": "user_id is required"}),
                status=400,
                headers=headers
            )

        logger.info(f"Complete report request for user: {user_id}")

        # Generate complete report
        result = get_complete_report(user_id)

        if result.get("success"):
            logger.info(f"Complete report generated successfully for user {user_id}")
            return https_fn.Response(
                json.dumps(result),
                status=200,
                headers=headers
            )
        else:
            logger.error(f"Complete report generation failed for user {user_id}: {result.get('error')}")
            return https_fn.Response(
                json.dumps(result),
                status=500,
                headers=headers
            )

    except Exception as e:
        logger.error(f"Error in get_complete_report_endpoint: {e}")
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            headers=headers
        )



@https_fn.on_request(timeout_sec=30)
def get_aifeed_reports_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to get AI feed reports for a user.
    
    Expected request (POST):
    {
        "user_id": "user123"
    }
    
    Returns AI feed reports data or 404 if not found.
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        
        if not user_id:
            raise ValueError("Missing user_id")
        
        # Get AI feed reports from database
        result = get_aifeed_reports(user_id)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        if result.get("success"):
            if result.get("found"):
                return https_fn.Response(
                    json.dumps(result),
                    headers=headers
                )
            else:
                return https_fn.Response(
                    json.dumps(result),
                    headers=headers,
                    status=404
                )
        else:
            return https_fn.Response(
                json.dumps(result),
                headers=headers,
                status=500
            )
        
    except Exception as e:
        logger.error(f"Error in get_aifeed_reports_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while retrieving AI feed reports",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


# --- Text to Speech Endpoint using ElevenLabs ---
@https_fn.on_request(timeout_sec=120)
def text_to_speech(req: https_fn.Request) -> https_fn.Response:
    """Convert text to speech using ElevenLabs API."""
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
        
    if req.method not in ['GET', 'POST']:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use GET or POST.', headers=headers, status=405)
    
    try:
        # Get parameters from query string (GET) or JSON body (POST)
        if req.method == 'GET':
            text = req.args.get('text')
            voice_id = req.args.get('voice_id', 'cmudN4ihcI42n48urXgc')
            model_id = req.args.get('model_id', 'eleven_multilingual_v2')
            output_format = req.args.get('output_format', 'mp3_44100_128')
        else:  # POST
            data = req.get_json() or {}
            text = data.get('text')
            voice_id = data.get('voice_id', 'cmudN4ihcI42n48urXgc')
            model_id = data.get('model_id', 'eleven_multilingual_v2')
            output_format = data.get('output_format', 'mp3_44100_128')
        
        if not text:
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
            return https_fn.Response(
                json.dumps({"error": "Missing 'text' parameter"}),
                headers=headers,
                status=400
            )
        
        logger.info(f"🔊 Converting text to speech: '{text[:50]}...' using voice {voice_id}")
        
        # Initialize ElevenLabs client
        audio_bytes = generate_text_to_speech_cartesia(
            text=text,
                voice_id=voice_id,  # Utilise model_id pour Cartesia
                language="en",  # NOUVEAU paramètre à ajouter à ton endpoint
                model_id=model_id
            )
        
        # Return the audio file directly
        headers = {
            'Access-Control-Allow-Origin': '*',
                'Content-Type': 'audio/wav',  # WAV au lieu de MP3
                'Content-Disposition': 'attachment; filename="speech.wav"',  # WAV
            'Content-Length': str(len(audio_bytes))
        }
        
        logger.info(f"✅ Successfully generated {len(audio_bytes)} bytes of audio")
        return https_fn.Response(audio_bytes, headers=headers)
        
    except Exception as e:
        logger.error(f"Error in text_to_speech: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "error": str(e),
            "message": "An error occurred while converting text to speech",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=300)
def generate_media_twin_script_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint pour générer un script de media twin.
    
    Expected request (POST):
    {
        "topic_name": "Business",
        "topic_posts_data": { ... },
        "presenter_name": "Alex",
        "language": "fr"
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        topic_name = data.get('topic_name')
        topic_posts_data = data.get('topic_posts_data')
        presenter_name = data.get('presenter_name', 'Alex')
        language = data.get('language', 'fr')
        
        # Validate required parameters
        if not topic_name:
            raise ValueError("Missing topic_name")
        if not topic_posts_data:
            raise ValueError("Missing topic_posts_data")
        
        logger.info(f"Generating media twin script for: {topic_name} ({language})")
        
        # Call the main function
        result = generate_media_twin_script(
            topic_name=topic_name,
            topic_posts_data=topic_posts_data,
            presenter_name=presenter_name,
            language=language
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in generate_media_twin_script_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating media twin script",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)


@https_fn.on_request(timeout_sec=600)
def generate_user_media_twin_script_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint pour générer un script de media twin basé sur tous les articles d'un utilisateur.
    
    Expected request (POST):
    {
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "presenter_name": "Alex",
        "language": "fr"
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        presenter_name = data.get('presenter_name', 'Alex')
        language = data.get('language', 'fr')
        
        # Validate required parameters
        if not user_id:
            raise ValueError("Missing user_id")
        
        logger.info(f"Generating user media twin script for user: {user_id} ({language})")
        
        # Call the main function
        result = generate_user_media_twin_script(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in generate_user_media_twin_script_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating user media twin script",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)



@https_fn.on_request(timeout_sec=600)
def generate_complete_user_media_twin_script_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint pour générer un script de media twin complet avec IA basé sur tous les articles d'un utilisateur.
    
    Expected request (POST):
    {
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "presenter_name": "Alex",
        "language": "fr"
    }
    
    Returns:
    {
        "success": true,
        "script": "Complete AI-generated script...",
        "metadata": {
            "user_id": "...",
            "word_count": 1250,
            "total_duration_estimate": "8 minutes",
            "topics_covered": 2,
            "articles_analyzed": 4,
            "reddit_discussions": 10,
            "ai_generated": true
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        presenter_name = data.get('presenter_name', 'Alex')
        language = data.get('language', 'fr')
        
        # Validate required parameters
        if not user_id:
            raise ValueError("Missing user_id")
        
        logger.info(f"Generating complete AI media twin script for user: {user_id} ({language})")
        
        # Call the main function
        result = generate_complete_user_media_twin_script(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in generate_complete_user_media_twin_script_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while generating complete AI media twin script",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500) 



@https_fn.on_request(timeout_sec=300, memory=options.MemoryOption.MB_512)  # Increased memory
def generate_simple_podcast_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to generate a complete podcast (script + audio).
    
    Expected request (POST):
    {
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "presenter_name": "Alex",
        "language": "en",
        "voice_id": "cmudN4ihcI42n48urXgc"
    }
    
    Returns:
    {
        "success": true,
        "script": "Generated script...",
        "script_storage_url": "https://storage.googleapis.com/...",
        "audio_url": "https://storage.googleapis.com/...",
        "metadata": {
            "word_count": 800,
            "estimated_duration": "5 minutes",
            "audio_size_bytes": 1234567
        }
    }
    """
    try:
        # Parse request
        request_json = req.get_json(silent=True)
        if not request_json:
            return https_fn.Response(
                json.dumps({"success": False, "error": "No JSON data provided"}),
                status=400,
                headers={"Content-Type": "application/json"}
            )
        
        user_id = request_json.get("user_id")
        if not user_id:
            return https_fn.Response(
                json.dumps({"success": False, "error": "user_id is required"}),
                status=400,
                headers={"Content-Type": "application/json"}
            )
        
        presenter_name = request_json.get("presenter_name", "Alex")
        language = request_json.get("language", "en")
        voice_id = request_json.get("voice_id", "96c64eb5-a945-448f-9710-980abe7a514c")
        
        # Generate complete podcast
        result = generate_simple_podcast(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language,
            voice_id=voice_id
        )
        
        if result.get("success"):
            return https_fn.Response(
                json.dumps(result),
                status=200,
                headers={"Content-Type": "application/json"}
            )
        else:
            return https_fn.Response(
                json.dumps(result),
                status=500,
                headers={"Content-Type": "application/json"}
            )
        
    except Exception as e:
        logger.error(f"Error in generate_simple_podcast_endpoint: {e}")
        return https_fn.Response(
            json.dumps({
                "success": False,
                "error": str(e),
                "message": "Failed to generate complete podcast"
            }),
            status=500,
            headers={"Content-Type": "application/json"}
        )

# --- Complete User Update Pipeline ---


@https_fn.on_request(timeout_sec=60)
def send_push_notification_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to send push notification to a user.
    
    Expected request (POST):
    {
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "title": "Your updates are available",
        "body": "Fresh news articles and podcast are ready!"
    }
    
    Returns:
    {
        "success": true,
        "message_id": "projects/prysmios/messages/...",
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "title": "Your updates are available",
        "body": "Fresh news articles and podcast are ready!"
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        title = data.get('title', 'Notification')
        body = data.get('body', 'You have a new update')
        
        # Validate required parameters
        if not user_id:
            raise ValueError("Missing user_id")
        
        logger.info(f"📱 Push notification request for user: {user_id}")
        
        # Call the main function
        result = send_push_notification(
            user_id=user_id,
            title=title,
            body=body
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in send_push_notification_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while sending push notification",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

@scheduler_fn.on_schedule(schedule="*/15 * * * *", timeout_sec=540, memory=options.MemoryOption.MB_512)  
def scheduled_user_updates_parallel(req):
    """
    READY-TO-DEPLOY parallel scheduler that processes multiple users concurrently.
    This replaces the original sequential scheduler with parallel processing.
    NO ADDITIONAL SETUP REQUIRED - WORKS IMMEDIATELY!
    """
    try:
        logger.info("⏰ Starting parallel user updates (READY TO DEPLOY VERSION)")
        
        current_time = datetime.now()
        db = firestore.client()
        
        # Get all users who need updates
        users_to_update = []
        scheduling_ref = db.collection('scheduling_preferences')
        all_schedules = scheduling_ref.stream()
        total_users_checked = 0
        
        for doc in all_schedules:
            total_users_checked += 1
            user_id = doc.id
            scheduling_prefs = doc.to_dict()
            
            logger.info(f"🔍 Checking user {user_id}: {scheduling_prefs}")
            
            # Check if this user should get an update
            if should_trigger_update_for_user(user_id, scheduling_prefs, current_time):
                users_to_update.append({
                    'user_id': user_id,
                    'preferences': scheduling_prefs
                })
                logger.info(f"📋 Added user {user_id} to parallel update queue")
        
        if not users_to_update:
            summary = {
                "success": True,
                "timestamp": current_time.isoformat(),
                "total_users_checked": total_users_checked,
                "users_triggered": 0,
                "message": "No users need updates"
            }
            logger.info(f"✅ No updates needed: {summary}")
            return summary
        
        logger.info(f"📊 Found {len(users_to_update)} users needing updates - processing in parallel")
        
        # Process users in parallel using ThreadPoolExecutor
        max_concurrent = min(5, len(users_to_update))  # Max 5 concurrent to avoid overwhelming
        successful_updates = 0
        failed_updates = 0
        
        def process_single_user(user_info):
            """Process a single user update"""
            try:
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
                    return {"success": True, "user_id": user_id}
                else:
                    logger.error(f"❌ Failed to process user {user_id}: {result.get('error')}")
                    return {"success": False, "user_id": user_id, "error": result.get('error')}
                    
            except Exception as e:
                logger.error(f"❌ Error processing user {user_info.get('user_id')}: {e}")
                return {"success": False, "user_id": user_info.get('user_id'), "error": str(e)}
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all user updates
            futures = []
            for user_info in users_to_update:
                future = executor.submit(process_single_user, user_info)
                futures.append(future)
            
            # Collect results as they complete
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=480)  # 8 min timeout per user (within scheduler limit)
                    if result.get("success"):
                        successful_updates += 1
                    else:
                        failed_updates += 1
                    
                    logger.info(f"📊 Completed {i+1}/{len(futures)} users: {result.get('user_id')}")
                    
                except Exception as e:
                    logger.error(f"❌ User update {i+1} failed with exception: {e}")
                    failed_updates += 1
        
        # Return summary
        summary = {
            "success": True,
            "timestamp": current_time.isoformat(),
            "total_users_checked": total_users_checked,
            "users_triggered": len(users_to_update),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "max_concurrent": max_concurrent,
            "processing_time_seconds": (datetime.now() - current_time).total_seconds(),
            "triggered_user_ids": [u['user_id'] for u in users_to_update]
        }
        
        logger.info(f"✅ Parallel updates complete: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error in parallel user updates: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@https_fn.on_request(timeout_sec=900, memory=options.MemoryOption.MB_512)
def process_user_update(req: https_fn.Request) -> https_fn.Response:
    """
    Worker function that processes individual user updates from the Cloud Tasks queue.
    This allows parallel processing of multiple users.
    """
    try:
        data = req.get_json()
        if not data:
            return https_fn.Response("No data provided", status=400)
        
        user_id = data.get('user_id')
        presenter_name = data.get('presenter_name', 'Alex')
        language = data.get('language', 'en')
        voice_id = data.get('voice_id', '96c64eb5-a945-448f-9710-980abe7a514c')
        scheduled_time = data.get('scheduled_time')
        
        logger.info(f"🔄 Processing queued update for user {user_id} (scheduled: {scheduled_time})")
        
        # Call the existing update function
        result = update(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language,
            voice_id=voice_id
        )
        
        if result.get("success"):
            logger.info(f"✅ Successfully processed user {user_id}")
        else:
            logger.error(f"❌ Failed to process user {user_id}: {result.get('error')}")
        
        return https_fn.Response(
            json.dumps(result),
            status=200 if result.get("success") else 500,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing user update: {e}")
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e)}),
            status=500,
            headers={"Content-Type": "application/json"}
        )
    
@https_fn.on_request(timeout_sec=900, memory=options.MemoryOption.MB_512)  # 15 minutes timeout, increased memory
def update_endpoint(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP endpoint to run complete user update pipeline.
    
    Expected request (POST):
    {
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "presenter_name": "Alex",
        "language": "en",
        "voice_id": "cmudN4ihcI42n48urXgc"
    }
    
    Returns:
    {
        "success": true,
        "user_id": "6YV8wgIEBrev7e2Ep7fm0InByq02",
        "pipeline_completed": true,
        "refresh_result": {
            "success": true,
            "total_articles": 45
        },
        "report_result": {
            "success": true,
            "reports_count": 3
        },
        "podcast_result": {
            "success": true,
            "audio_url": "https://storage.googleapis.com/...",
            "script_storage_url": "https://storage.googleapis.com/..."
        }
    }
    """
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        # Parse request data
        data = req.get_json()
        if not data:
            raise ValueError("No JSON data provided")
        
        user_id = data.get('user_id')
        presenter_name = data.get('presenter_name', 'Alex')
        language = data.get('language', 'en')
        voice_id = data.get('voice_id', '96c64eb5-a945-448f-9710-980abe7a514c')
        
        # Validate required parameters
        if not user_id:
            raise ValueError("Missing user_id")
        
        logger.info(f"Starting complete update pipeline for user: {user_id}")
        
        # Call the main function
        result = update(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language,
            voice_id=voice_id
        )
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(
            json.dumps(result),
            headers=headers,
            status=200 if result.get("success") else 500
        )
        
    except Exception as e:
        logger.error(f"Error in update_endpoint: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "success": False,
            "error": str(e),
            "message": "An error occurred while running update pipeline",
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

@https_fn.on_request(timeout_sec=60)
def start_interactive_test(req: https_fn.Request) -> https_fn.Response:
    """
    Start a simple interactive podcast test session.
    
    Expected request (POST):
    {
        "user_id": "test_user"  // Optional
    }
    
    Returns:
    {
        "success": true,
        "session_id": "uuid",
        "message": "Test session ready!",
        "sample_questions": [...]
    }
    """
    # Handle CORS
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        data = req.get_json() or {}
        user_id = data.get('user_id', 'test_user')
        
        logger.info(f"🧪 Starting interactive test for user: {user_id}")
        
        result = interactive_test.create_test_session(user_id)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(json.dumps(result), headers=headers)
        
    except Exception as e:
        logger.error(f"Error starting interactive test: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e)}),
            headers=headers,
            status=500
        )

@https_fn.on_request(timeout_sec=120)
def generate_test_audio(req: https_fn.Request) -> https_fn.Response:
    """
    Generate audio for the test podcast.
    
    Expected request (POST):
    {
        "session_id": "uuid",
        "voice_id": "voice_id"  // Optional
    }
    
    Returns:
    {
        "success": true,
        "audio_url": "https://storage.googleapis.com/...",
        "message": "Audio ready for testing!"
    }
    """
    # Handle CORS
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        data = req.get_json() or {}
        session_id = data.get('session_id')
        voice_id = data.get('voice_id', '96c64eb5-a945-448f-9710-980abe7a514c')
        
        if not session_id:
            raise ValueError("Missing session_id")
        
        logger.info(f"🔊 Generating test audio for session: {session_id}")
        
        result = interactive_test.generate_podcast_audio(session_id, voice_id)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(json.dumps(result), headers=headers)
        
    except Exception as e:
        logger.error(f"Error generating test audio: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e)}),
            headers=headers,
            status=500
        )

@https_fn.on_request(timeout_sec=90)
def handle_test_interruption(req: https_fn.Request) -> https_fn.Response:
    """
    Handle user interruption during test podcast.
    
    Expected request (POST):
    {
        "session_id": "uuid",
        "user_question": "Tell me more about OpenAI updates"
    }
    
    Returns:
    {
        "success": true,
        "response": "AI response text",
        "audio_url": "https://storage.googleapis.com/...",
        "message": "Response ready!"
    }
    """
    # Handle CORS
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers)
    
    if req.method != 'POST':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": "Method not allowed. Use POST."}),
            headers=headers,
            status=405
        )
    
    try:
        data = req.get_json() or {}
        session_id = data.get('session_id')
        user_question = data.get('user_question')
        
        if not session_id or not user_question:
            raise ValueError("Missing session_id or user_question")
        
        logger.info(f"🎤 Handling test interruption: {session_id} - '{user_question}'")
        
        result = interactive_test.handle_interruption(session_id, user_question)
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        return https_fn.Response(json.dumps(result), headers=headers)
        
    except Exception as e:
        logger.error(f"Error handling test interruption: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(
            json.dumps({"success": False, "error": str(e)}),
            headers=headers,
            status=500
        )

