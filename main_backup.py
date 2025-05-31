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

logger.info("--- main.py: Logging configured ---")

# Initialize Firebase app
# Using Firestore (no need for database URL)
initialize_app()

# --- Constants ---
MAX_NEWS_SUBJECTS = 5
MAX_SPECIFIC_RESEARCH = 2
DETAIL_LEVELS = ["Light", "Medium", "Detailed"]
DETAIL_STARS = {
    "Light": "*",
    "Medium": "**", 
    "Detailed": "***"
}

SERPAPI_API_KEY_HARDCODED = "cc6fb3c2829269bca1fa87ecfeb3ff984e3313b5f2f80503ff1e55d8c6b9098c"

# GNews API Configuration
GNEWS_API_KEY = "75807d7923a12e3d80d64c971ff340da"  # GNews API key
GNEWS_BASE_URL = "https://gnews.io/api/v4"

# Function to get OpenAI API key
def get_openai_key():
    """Retrieve OpenAI API key from environment or fallback to hardcoded value."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    logger.warning("OPENAI_API_KEY not found in env, using fallback key")
    return "sk-HxFKqwvTI8JfWp0WbPRF75FsoEQokPS2IQHrKIKQwtT3BlbkFJwNHRfzhJb-_Xz39M9531MNdy35DGxMkTZ2s05X2sYA"  # Replace with actual key

# Function to get OpenAI client
def get_openai_client():
    """Get configured OpenAI client."""
    try:
        api_key = get_openai_key()
        client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None

# Function to get GNews API key
def get_gnews_key():
    """Legacy function that now returns SerpAPI key for backward compatibility."""
    return get_serpapi_key()

def sanitize_gnews_query(query):
    """
    Legacy function for GNews API query sanitization.
    SerpAPI handles query formatting automatically, so this just returns the original query.
    
    Args:
        query (str): The original search query
        
    Returns:
        str: The query (unchanged for SerpAPI)
    """
    return query

# --- GNews API Functions ---

def gnews_search(query, lang="en", country="us", max_articles=10, from_date=None, to_date=None, nullable=None):
    """
    Search for news articles using SerpAPI Google News API (updated from GNews).
    
    Args:
        query (str): Search keywords
        lang (str): Language code (e.g., 'en', 'fr', 'es')
        country (str): Country code (e.g., 'us', 'fr', 'gb')
        max_articles (int): Number of articles to return
        from_date (str): Not supported by SerpAPI Google News (legacy parameter)
        to_date (str): Not supported by SerpAPI Google News (legacy parameter)
        nullable (str): Not supported by SerpAPI Google News (legacy parameter)
    
    Returns:
        dict: API response with articles or error information
    """
    logger.info(f"🔍 Google News Search (SerpAPI): Query '{query}', Lang: {lang}, Country: {country}")
    
    # Convert parameters to SerpAPI format
    gl = country  # Google's gl parameter
    hl = lang     # Google's hl parameter
    
    # Determine time period based on from_date (approximate conversion)
    time_period = None
    if from_date:
        try:
            from datetime import datetime, timedelta
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            now = datetime.now(from_dt.tzinfo)
            diff = now - from_dt
            
            if diff <= timedelta(hours=1):
                time_period = "h"  # Last hour
            elif diff <= timedelta(days=1):
                time_period = "d"  # Last day
            elif diff <= timedelta(days=7):
                time_period = "w"  # Last week
            # If older than a week, don't set time_period (all time)
        except:
            logger.warning(f"⚠️ Could not parse from_date '{from_date}', using all time")
    
    # Call SerpAPI Google News
    result = serpapi_google_news_search(
        query=query,
        gl=gl,
        hl=hl,
        max_articles=max_articles,
        time_period=time_period
    )
    
    # If no articles found and we had a time filter, try without time filter as fallback
    if result.get('success') and result.get('totalArticles', 0) == 0 and time_period:
        logger.info(f"🔄 Google News Search: No articles found with time filter, trying without time filter")
        fallback_result = serpapi_google_news_search(
            query=query,
            gl=gl,
            hl=hl,
            max_articles=max_articles,
            time_period=None
        )
        
        if fallback_result.get('success') and fallback_result.get('totalArticles', 0) > 0:
            logger.info(f"✅ Google News Search: Fallback successful - found {fallback_result.get('totalArticles', 0)} articles")
            fallback_result['used_fallback'] = True
            fallback_result['original_time_period'] = time_period
            return fallback_result
    
    return result

def gnews_top_headlines(category="general", lang="en", country="us", max_articles=10, from_date=None, to_date=None, query=None, nullable=None):
    """
    Get top headlines using SerpAPI Google News API (updated from GNews).
    
    Args:
        category (str): News category (general, world, business, technology, entertainment, sports, science, health)
        lang (str): Language code (e.g., 'en', 'fr', 'es')
        country (str): Country code (e.g., 'us', 'fr', 'gb')
        max_articles (int): Number of articles to return
        from_date (str): Not supported by SerpAPI Google News (legacy parameter)
        to_date (str): Not supported by SerpAPI Google News (legacy parameter)
        query (str): Optional search query
        nullable (str): Not supported by SerpAPI Google News (legacy parameter)
    
    Returns:
        dict: API response with articles or error information
    """
    logger.info(f"🔍 Google News Top Headlines (SerpAPI): Category '{category}', Lang: {lang}, Country: {country}")
    
    # Convert parameters to SerpAPI format
    gl = country
    hl = lang
    
    # If we have a specific query, search for it
    if query:
        return gnews_search(query, lang, country, max_articles, from_date, to_date)
    
    # Map GNews categories to SerpAPI topic tokens
    # These tokens are for US English - different countries/languages may have different tokens
    category_topic_tokens = {
        "general": None,  # No topic token = general homepage
        "world": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YTJJZ0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # World
        "business": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Business
        "technology": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Technology
        "entertainment": "CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Entertainment
        "sports": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Sports
        "science": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Science (using tech token as fallback)
        "health": "CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3Q0ZGpVU0FTb0pFZ0EQAg"  # Health
    }
    
    # Get the topic token for the requested category
    topic_token = category_topic_tokens.get(category.lower())
    
    # Determine time period based on from_date (approximate conversion)
    time_period = None
    if from_date:
        try:
            from datetime import datetime, timedelta
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            now = datetime.now(from_dt.tzinfo)
            diff = now - from_dt
            
            if diff <= timedelta(hours=1):
                time_period = "h"  # Last hour
            elif diff <= timedelta(days=1):
                time_period = "d"  # Last day
            elif diff <= timedelta(days=7):
                time_period = "w"  # Last week
        except:
            logger.warning(f"⚠️ Could not parse from_date '{from_date}', using all time")
    
    if category.lower() == "general" or topic_token is None:
        # For general news, get the homepage headlines
        logger.info(f"📰 Fetching general homepage headlines")
        result = serpapi_google_news_search(
            query=None,
            gl=gl,
            hl=hl,
            max_articles=max_articles,
            time_period=time_period
        )
    else:
        # For specific categories, use the topic token
        logger.info(f"📰 Fetching {category} headlines using topic token: {topic_token}")
        result = serpapi_google_news_search(
            query=None,
            gl=gl,
            hl=hl,
            max_articles=max_articles,
            time_period=time_period,
            topic_token=topic_token
        )
    
    # Add category information to the response
    if result.get('success'):
        result['category'] = category
        result['topic_token_used'] = topic_token
    
    return result

def format_gnews_articles_for_prysm(gnews_response):
    """
    Convert GNews API response to Prysm-compatible format.
    
    Args:
        gnews_response (dict): Response from GNews API
    
    Returns:
        list: List of articles in Prysm format
    """
    if not gnews_response.get("success") or not gnews_response.get("articles"):
        return []
    
    formatted_articles = []
    
    for article in gnews_response["articles"]:
        formatted_article = {
            'title': article.get('title', '').strip(),
            'link': article.get('url', '#').strip(),
            'source': article.get('source', {}).get('name', 'Unknown Source'),
            'published': article.get('publishedAt', ''),
            'snippet': article.get('description', '').strip(),
            'thumbnail': article.get('image', ''),
            'content': article.get('content', '').strip()
        }
        
        # Clean empty fields
        formatted_article = {k: v for k, v in formatted_article.items() if v and v != 'No Title'}
        
        if formatted_article:  # Only add non-empty articles
            formatted_articles.append(formatted_article)
    
    logger.info(f"Formatted {len(formatted_articles)} articles for Prysm")
    return formatted_articles

# --- Basic Health Check Endpoint ---
@https_fn.on_request(timeout_sec=60)
def health_check(req: https_fn.Request) -> https_fn.Response:
    """Basic health check endpoint."""
    
    # Handle CORS preflight requests
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return https_fn.Response('', headers=headers, status=204)
        
    if req.method != 'GET':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response('Method not allowed. Use GET.', headers=headers, status=405)
    
    try:
        response_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "PrysmIOS Backend is running"
        }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        return https_fn.Response(json.dumps(response_data), headers=headers)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return https_fn.Response(json.dumps(error_response), headers=headers, status=500)

# --- Placeholder for future endpoints ---
# TODO: Add your new endpoints here

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

def build_system_prompt(user_preferences):
    """
    Build the system prompt based on user preferences.
    
    Args:
        user_preferences (dict): User preferences including subjects, subtopics, detail_level, language, specific_subjects, etc.
    
    Returns:
        str: Complete system prompt for the AI
    """
    subjects = user_preferences.get('subjects', [])
    subtopics = user_preferences.get('subtopics', [])
    specific_subjects = user_preferences.get('specific_subjects', [])
    detail_level = user_preferences.get('detail_level', 'Medium')
    language = user_preferences.get('language', 'en')
    
    # Language-specific prompts
    language_prompts = {
        'en': {
            'role': "You are a preferences discovery assistant for PrysmIOS app.",
            'task': "Your ONLY goal is to discover the user's specific news interests and preferences. DO NOT provide news articles or current events. Keep responses SHORT (max 3-4 sentences).",
            'guide': "Ask questions to understand what specific topics, companies, people, or events they want to follow. Be proactive in discovering their interests.",
            'subjects_intro': "User selected:",
            'subtopics_intro': "Subtopics:",
            'detail_intro': f"Detail level: {detail_level.lower()}.",
            'refinement_task': "Ask about specific entities they want to follow from their topics. Examples: 'Which tech companies interest you?' or 'Any specific sports teams you follow?'",
            'guidelines': "DISCOVER PREFERENCES, DON'T GIVE NEWS! Examples: Technology → Ask 'Which tech companies like Apple, Tesla, or OpenAI interest you?' Sports → Ask 'Do you follow specific teams like Lakers or players like Messi?'",
            'conversation_flow': "When you have enough specific interests, say: 'Perfect! I've learned about your interests. Your personalized news feed is ready!'"
        },
        'fr': {
            'role': "Tu es un assistant de découverte de préférences pour l'application PrysmIOS.",
            'task': "Ton SEUL objectif est de découvrir les intérêts et préférences spécifiques de l'utilisateur. NE DONNE PAS d'articles d'actualités ou d'événements actuels. Reste BREF (max 3-4 phrases).",
            'guide': "Pose des questions pour comprendre quels sujets spécifiques, entreprises, personnes ou événements ils veulent suivre. Sois proactif dans la découverte de leurs intérêts.",
            'subjects_intro': "Utilisateur a choisi :",
            'subtopics_intro': "Sous-sujets :",
            'detail_intro': f"Niveau de détail : {detail_level.lower()}.",
            'refinement_task': "Demande quelles entités spécifiques ils veulent suivre dans leurs sujets. Exemples : 'Quelles entreprises tech t'intéressent ?' ou 'Tu suis des équipes sportives particulières ?'",
            'guidelines': "DÉCOUVRE LES PRÉFÉRENCES, NE DONNE PAS D'ACTUALITÉS ! Exemples : Technologie → Demande 'Quelles entreprises comme Apple, Tesla ou OpenAI t'intéressent ?' Sport → Demande 'Tu suis des équipes comme le PSG ou des joueurs comme Mbappé ?'",
            'conversation_flow': "Quand tu as assez d'intérêts spécifiques, dis : 'Parfait ! J'ai appris tes intérêts. Ton flux d'actualités personnalisé est prêt !'"
        },
        'es': {
            'role': "Eres un asistente de descubrimiento de preferencias para la aplicación PrysmIOS.",
            'task': "Tu ÚNICO objetivo es descubrir los intereses y preferencias específicos del usuario. NO proporciones artículos de noticias o eventos actuales. Mantente BREVE (máx 3-4 frases).",
            'guide': "Haz preguntas para entender qué temas específicos, empresas, personas o eventos quieren seguir. Sé proactivo en descubrir sus intereses.",
            'subjects_intro': "Usuario eligió:",
            'subtopics_intro': "Subtemas:",
            'detail_intro': f"Nivel de detalle: {detail_level.lower()}.",
            'refinement_task': "Pregunta qué entidades específicas quieren seguir de sus temas. Ejemplos: '¿Qué empresas tecnológicas te interesan?' o '¿Sigues equipos deportivos específicos?'",
            'guidelines': "¡DESCUBRE PREFERENCIAS, NO DES NOTICIAS! Ejemplos: Tecnología → Pregunta '¿Qué empresas como Apple, Tesla u OpenAI te interesan?' Deportes → Pregunta '¿Sigues equipos como Real Madrid o jugadores como Messi?'",
            'conversation_flow': "Cuando tengas suficientes intereses específicos, di: '¡Perfecto! He aprendido sobre tus intereses. ¡Tu feed de noticias personalizado está listo!'"
        },
        'ar': {
            'role': "أنت مساعد اكتشاف التفضيلات لتطبيق PrysmIOS.",
            'task': "هدفك الوحيد هو اكتشاف اهتمامات وتفضيلات المستخدم المحددة. لا تقدم مقالات إخبارية أو أحداث جارية. كن مختصراً (حد أقصى 3-4 جمل).",
            'guide': "اطرح أسئلة لفهم المواضيع المحددة والشركات والأشخاص أو الأحداث التي يريدون متابعتها. كن استباقياً في اكتشاف اهتماماتهم.",
            'subjects_intro': "المستخدم اختار:",
            'subtopics_intro': "المواضيع الفرعية:",
            'detail_intro': f"مستوى التفصيل: {detail_level.lower()}.",
            'refinement_task': "اسأل عن الكيانات المحددة التي يريدون متابعتها من مواضيعهم. أمثلة: 'ما الشركات التقنية التي تهمك؟' أو 'هل تتابع فرق رياضية معينة؟'",
            'guidelines': "اكتشف التفضيلات، لا تعطِ أخباراً! أمثلة: التكنولوجيا → اسأل 'ما الشركات مثل آبل أو تسلا أو OpenAI التي تهمك؟' الرياضة → اسأل 'هل تتابع فرق مثل ريال مدريد أو لاعبين مثل ميسي؟'",
            'conversation_flow': "عندما تحصل على اهتمامات محددة كافية، قل: 'ممتاز! لقد تعلمت عن اهتماماتك. تدفق أخبارك الشخصي جاهز!'"
        }
    }
    
    prompt_data = language_prompts.get(language, language_prompts['en'])
    
    # Build the complete system prompt
    system_prompt = f"""IMPORTANT: You are NOT a news provider. You do NOT give news articles, headlines, or current events.

{prompt_data['role']}

{prompt_data['task']}

{prompt_data['guide']}

{prompt_data['subjects_intro']} {', '.join(subjects) if subjects else 'None specified'}

"""
    
    # Add subtopics if available
    if subtopics:
        system_prompt += f"{prompt_data['subtopics_intro']} {', '.join(subtopics)}\n\n"
    
    system_prompt += f"""{prompt_data['detail_intro']}

{prompt_data['refinement_task']}

{prompt_data['guidelines']}

{prompt_data['conversation_flow']}"""
    
    return system_prompt

def format_conversation_history(messages):
    """
    Format conversation history for OpenAI API.
    
    Args:
        messages (list): List of message objects with 'role' and 'content'
    
    Returns:
        list: Formatted messages for OpenAI API
    """
    formatted_messages = []
    
    for message in messages:
        role = message.get('role', '').lower()
        content = message.get('content', '')
        
        # Map roles to OpenAI format
        if role in ['user', 'human']:
            formatted_messages.append({"role": "user", "content": content})
        elif role in ['assistant', 'chatbot', 'ai']:
            formatted_messages.append({"role": "assistant", "content": content})
        elif role == 'system':
            formatted_messages.append({"role": "system", "content": content})
    
    return formatted_messages

def generate_ai_response(system_prompt, conversation_history, user_message):
    """
    Generate AI response using OpenAI API.
    
    Args:
        system_prompt (str): System prompt with user preferences
        conversation_history (list): Previous messages in conversation
        user_message (str): Current user message
    
    Returns:
        dict: Response with success status and AI message or error
    """
    try:
        client = get_openai_client()
        if not client:
            return {"success": False, "error": "OpenAI client not available"}
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        formatted_history = format_conversation_history(conversation_history)
        messages.extend(formatted_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Generate response - shorter limit for concise responses, use gpt-4o-mini model
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        
        ai_message = response.choices[0].message.content
        
        return {
            "success": True,
            "message": ai_message,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return {"success": False, "error": str(e)}

# --- Firebase Database Functions ---

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

def find_parent_topic_for_subtopic(subtopic_name):
    """Find which topic a subtopic belongs to"""
    # Map subtopics to their parent topics
    subtopic_to_topic = {
        # Technology subtopics
        'AI': 'technology',
        'Artificial Intelligence': 'technology',
        'Gadgets': 'technology',
        'Software': 'technology',
        'Hardware': 'technology',
        'Cybersecurity': 'technology',
        'Startups': 'technology',
        
        # Business subtopics
        'Finance': 'business',
        'Economy': 'business',
        'Markets': 'business',
        'Cryptocurrency': 'business',
        'Investment': 'business',
        'Banking': 'business',
        
        # Sports subtopics
        'Football': 'sports',
        'Basketball': 'sports',
        'Tennis': 'sports',
        'Soccer': 'sports',
        'Olympics': 'sports',
        'Baseball': 'sports',
        
        # Science subtopics
        'Space': 'science',
        'Research': 'science',
        'Climate': 'science',
        'Physics': 'science',
        'Chemistry': 'science',
        'Biology': 'science',
        
        # Health subtopics
        'Medicine': 'health',
        'Fitness': 'health',
        'Nutrition': 'health',
        'Mental Health': 'health',
        'Wellness': 'health',
        
        # Entertainment subtopics
        'Movies': 'entertainment',
        'Music': 'entertainment',
        'Gaming': 'entertainment',
        'TV Shows': 'entertainment',
        'Celebrities': 'entertainment',
        
        # World subtopics
        'Politics': 'world',
        'International': 'world',
        'Conflicts': 'world',
        'Diplomacy': 'world'
    }
    
    return subtopic_to_topic.get(subtopic_name, 'general')

def convert_old_topic_to_gnews(old_topic):
    """Convert old topic format to GNews format"""
    if isinstance(old_topic, str):
        lowercased = old_topic.lower()
        
        # Map common old topics to GNews format
        topic_mapping = {
            'technology': 'technology',
            'technologie': 'technology',
            'tecnología': 'technology',
            'تكنولوجيا': 'technology',
            'business': 'business',
            'affaires': 'business',
            'negocios': 'business',
            'أعمال': 'business',
            'sports': 'sports',
            'deportes': 'sports',
            'رياضة': 'sports',
            'science': 'science',
            'ciencia': 'science',
            'علوم': 'science',
            'health': 'health',
            'santé': 'health',
            'salud': 'health',
            'صحة': 'health',
            'entertainment': 'entertainment',
            'divertissement': 'entertainment',
            'entretenimiento': 'entertainment',
            'ترفيه': 'entertainment',
            'world': 'world',
            'monde': 'world',
            'mundo': 'world',
            'عالم': 'world',
            'general': 'general',
            'général': 'general'
        }
        
        return topic_mapping.get(lowercased, 'general')
    
    return 'general'

def find_subtopic_in_catalog(subtopic_name):
    """Find subtopic metadata in our predefined catalog"""
    # This would need to be implemented based on your SubtopicsCatalog
    # For now, return a basic structure
    
    # Common subtopic mappings with basic subreddit suggestions
    subtopic_catalog = {
        'Artificial Intelligence': {
            'subreddits': ['MachineLearning', 'artificial', 'singularity'],
            'query': 'artificial intelligence OR AI'
        },
        'AI': {
            'subreddits': ['MachineLearning', 'artificial', 'singularity'],
            'query': 'artificial intelligence OR AI'
        },
        'Finance': {
            'subreddits': ['personalfinance', 'stocks', 'cryptocurrency'],
            'query': 'finance OR stock market OR investment'
        },
        'Gadgets': {
            'subreddits': ['gadgets', 'Android', 'apple'],
            'query': 'gadgets OR smartphones OR technology devices'
        },
        'Sports': {
            'subreddits': ['sports', 'nfl', 'nba'],
            'query': 'sports OR games OR athletics'
        }
    }
    
    return subtopic_catalog.get(subtopic_name, None)

# --- Specific Subjects Analysis ---

def analyze_conversation_for_specific_subjects(conversation_history, user_message, language='en'):
    """
    Analyze conversation to extract specific subjects using a separate LLM call.
    
    Args:
        conversation_history (list): Previous conversation messages
        user_message (str): Current user message
        language (str): Language code for analysis
    
    Returns:
        dict: Analysis result with extracted subjects
    """
    try:
        client = get_openai_client()
        if not client:
            return {"success": False, "error": "OpenAI client not available"}
        
        # Build analysis prompt based on language
        analysis_prompts = {
            'en': """CRITICAL TASK: Extract ONLY specific entities that the USER explicitly mentions in their messages.

RULES:
1. Look ONLY at messages that start with "user:"
2. Extract ONLY what the user explicitly names or mentions
3. IGNORE everything the assistant says
4. Extract specific names, companies, people, products, events, AND specific technologies

What to extract (ONLY if user mentions them):
- Company names: "Tesla", "Apple", "Microsoft", "OpenAI", "Google"
- People names: "Elon Musk", "Tim Cook", "Biden", "Cristiano Ronaldo"
- Products: "iPhone", "ChatGPT", "PlayStation", "Rubik's Cube"
- Events: "Olympics 2024", "CES", "World Cup"
- Specific technologies: "LLMs", "GPT-4", "machine learning", "AI", "robotique", "robot"
- Specific topics: "robot qui a battu le record", "innovations en robotique"

What NOT to extract:
- Very general concepts like "technology", "sports" (without specifics)
- Things only the assistant mentioned
- Implied topics not explicitly mentioned

IMPORTANT: If user says "LLMs", "robot", "robotique", "machine learning", "AI" - these ARE specific enough to extract.

Return ONLY a JSON array of specific entities the USER explicitly mentioned: ["entity1", "entity2"]
If user mentioned no specific entities, return: []""",
            
            'fr': """TÂCHE CRITIQUE: Extraire SEULEMENT les entités spécifiques que l'UTILISATEUR mentionne explicitement dans ses messages.

RÈGLES:
1. Regarde SEULEMENT les messages qui commencent par "user:"
2. Extrait SEULEMENT ce que l'utilisateur nomme ou mentionne explicitement
3. IGNORE tout ce que l'assistant dit
4. Extrait les noms spécifiques, entreprises, personnes, produits, événements, ET technologies spécifiques

Quoi extraire (SEULEMENT si l'utilisateur les mentionne):
- Noms d'entreprises: "Tesla", "Apple", "Microsoft", "OpenAI", "Google"
- Noms de personnes: "Elon Musk", "Tim Cook", "Biden", "Cristiano Ronaldo"
- Produits: "iPhone", "ChatGPT", "PlayStation", "Rubik's Cube"
- Événements: "Jeux Olympiques 2024", "CES", "Coupe du Monde"
- Technologies spécifiques: "LLMs", "GPT-4", "apprentissage automatique", "IA", "robotique", "robot"
- Sujets spécifiques: "robot qui a battu le record", "innovations en robotique"

Quoi NE PAS extraire:
- Concepts très généraux comme "technologie", "sport" (sans spécificités)
- Choses mentionnées seulement par l'assistant
- Sujets impliqués ou suggérés

IMPORTANT: Si l'utilisateur dit "LLMs", "robot", "robotique", "apprentissage automatique", "IA" - ces termes SONT assez spécifiques pour être extraits.

Retourne SEULEMENT un array JSON d'entités spécifiques que l'UTILISATEUR a explicitement mentionnées: ["entité1", "entité2"]
Si l'utilisateur n'a mentionné aucune entité spécifique, retourne: []""",
            
            'es': """TAREA CRÍTICA: Extraer SOLO entidades específicas que el USUARIO menciona explícitamente en sus mensajes.

REGLAS:
1. Mira SOLO mensajes que empiecen con "user:"
2. Extrae SOLO lo que el usuario nombra o menciona explícitamente
3. IGNORA todo lo que dice el asistente
4. IGNORA temas generales como "IA", "tecnología", "deportes"
5. Extrae SOLO nombres específicos, empresas, personas, productos, eventos

Qué extraer (SOLO si el usuario los menciona):
- Nombres de empresas: "Tesla", "Apple", "Microsoft"
- Nombres de personas: "Elon Musk", "Tim Cook", "Biden"
- Productos: "iPhone", "ChatGPT", "PlayStation"
- Eventos: "Olimpiadas 2024", "CES", "Copa Mundial"
- Tecnologías específicas: "LLMs" (si el usuario lo dice), "GPT-4"

Qué NO extraer:
- Conceptos generales: "IA", "tecnología", "aprendizaje automático"
- Cosas mencionadas solo por el asistente
- Temas implícitos o sugeridos

Devuelve SOLO un array JSON de entidades específicas que el USUARIO mencionó explícitamente: ["entidad1", "entidad2"]
Si el usuario no mencionó entidades específicas, devuelve: []""",
            
            'ar': """مهمة حاسمة: استخراج فقط الكيانات المحددة التي يذكرها المستخدم صراحة في رسائله.

القواعد:
1. انظر فقط إلى الرسائل التي تبدأ بـ "user:"
2. استخرج فقط ما يسميه أو يذكره المستخدم صراحة
3. تجاهل كل ما يقوله المساعد
4. تجاهل المواضيع العامة مثل "الذكاء الاصطناعي"، "التكنولوجيا"، "الرياضة"
5. استخرج فقط الأسماء المحددة، الشركات، الأشخاص، المنتجات، الأحداث

ما يجب استخراجه (فقط إذا ذكرها المستخدم):
- أسماء الشركات: "تسلا"، "آبل"، "مايكروسوفت"
- أسماء الأشخاص: "إيلون ماسك"، "تيم كوك"، "بايدن"
- المنتجات: "آيفون"، "ChatGPT"، "بلايستيشن"
- الأحداث: "أولمبياد 2024"، "CES"، "كأس العالم"
- التقنيات المحددة: "LLMs" (إذا قالها المستخدم)، "GPT-4"

ما لا يجب استخراجه:
- المفاهيم العامة: "الذكاء الاصطناعي"، "التكنولوجيا"، "التعلم الآلي"
- الأشياء التي ذكرها المساعد فقط
- المواضيع الضمنية أو المقترحة

أرجع فقط مصفوفة JSON للكيانات المحددة التي ذكرها المستخدم صراحة: ["كيان1", "كيان2"]
إذا لم يذكر المستخدم أي كيانات محددة، أرجع: []"""
        }
        
        analysis_prompt = analysis_prompts.get(language, analysis_prompts['en'])
        
        # Build conversation context
        conversation_text = ""
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            role = msg.get('role', '')
            content = msg.get('content', '')
            conversation_text += f"{role}: {content}\n"
        
        conversation_text += f"user: {user_message}\n"
        
        # Create analysis messages
        messages = [
            {"role": "system", "content": analysis_prompt},
            {"role": "user", "content": f"Conversation to analyze:\n{conversation_text}"}
        ]
        
        # Generate analysis
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200,
            temperature=0.3
        )
        
        analysis_result = response.choices[0].message.content.strip()
        
        # Try to parse JSON
        try:
            specific_subjects = json.loads(analysis_result)
            if isinstance(specific_subjects, list):
                # Filter out empty strings and duplicates
                specific_subjects = list(set([s.strip() for s in specific_subjects if s.strip()]))
                
                return {
                    "success": True,
                    "specific_subjects": specific_subjects,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            else:
                return {"success": False, "error": "Invalid response format"}
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis result as JSON: {analysis_result}")
            return {"success": False, "error": "Failed to parse analysis result"}
            
    except Exception as e:
        logger.error(f"Error analyzing conversation for specific subjects: {e}")
        return {"success": False, "error": str(e)}

# --- Background Analysis Helper ---

def analyze_and_update_specific_subjects(user_id, conversation_history, user_message, language):
    """
    Background function to analyze conversation and update specific subjects.
    This runs in a separate thread to not block the main conversation response.
    """
    try:
        logger.info(f"Background analysis started for user {user_id}")
        
        # Analyze conversation for specific subjects
        analysis_result = analyze_conversation_for_specific_subjects(
            conversation_history, user_message, language
        )
        
        if analysis_result["success"] and analysis_result.get("specific_subjects"):
            # Update database with new specific subjects
            update_result = update_specific_subjects_in_db(
                user_id, analysis_result["specific_subjects"]
            )
            
            if update_result["success"]:
                logger.info(f"Background analysis completed for user {user_id}. New subjects: {analysis_result['specific_subjects']}")
        else:
            logger.info(f"Background analysis completed for user {user_id}. No new subjects found.")
            
    except Exception as e:
        logger.error(f"Error in background analysis for user {user_id}: {e}")

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

def get_trending_topics_for_subtopic(subtopic_title, subtopic_query, subreddits, lang="en", country="us", max_articles=10):
    """
    Get trending topics for a specific subtopic by combining GNews search + Reddit posts.
    
    Args:
        subtopic_title (str): Display name (e.g., "Artificial Intelligence")
        subtopic_query (str): Search query (e.g., "artificial intelligence OR AI")
        subreddits (list): Associated subreddits (e.g., ["MachineLearning", "Artificial", "singularity"])
        lang (str): Language code
        country (str): Country code
        max_articles (int): Max GNews articles to fetch
    
    Returns:
        dict: Response with trending topics list
    """
    try:
        logger.info(f"Getting trending topics for subtopic: {subtopic_title}")
        
        # Step 1: Fetch GNews articles using subtopic query
        gnews_response = gnews_search(
            query=subtopic_query,
            lang=lang,
            country=country,
            max_articles=max_articles
        )
        
        gnews_articles = gnews_response.get("articles", []) if gnews_response.get("success") else []
        
        # Step 2: Fetch Reddit posts from associated subreddits
        reddit_posts = []
        headers = {"User-Agent": "NewsXTrendingBot/1.0"}
        
        for subreddit in subreddits[:3]:  # Limit to top 3 subreddits
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if "data" in data and "children" in data["data"]:
                    posts = data["data"]["children"]
                    for post in posts:
                        post_data = post.get("data", {})
                        reddit_posts.append({
                            "title": post_data.get("title", ""),
                            "score": post_data.get("score", 0),
                            "subreddit": subreddit
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch from r/{subreddit}: {e}")
        
        # Step 3: Prepare content for LLM analysis
        content_text = f"SUBTOPIC: {subtopic_title}\n\n"
        
        # Add GNews articles
        content_text += "NEWS ARTICLES:\n"
        for i, article in enumerate(gnews_articles[:8], 1):
            title = article.get('title', '')
            description = article.get('description', '')
            content_text += f"{i}. {title}\n"
            if description:
                content_text += f"   {description}\n"
        
        # Add Reddit posts
        content_text += "\nREDDIT DISCUSSIONS:\n"
        for i, post in enumerate(reddit_posts[:10], 1):
            content_text += f"{i}. r/{post['subreddit']}: {post['title']} ({post['score']} points)\n"
        
        # Step 4: LLM prompt for trending topics extraction
        analysis_prompt = f"""You are a trending topics analyst. Based on the news articles and Reddit discussions below about "{subtopic_title}", extract 6-8 specific trending topics that are currently hot.

RULES:
1. Focus on SPECIFIC trending themes, events, companies, or technologies
2. Each topic should be 2-4 words maximum
3. Avoid generic terms - be specific about what's trending NOW
4. Look for patterns across both news and Reddit discussions
5. Prioritize topics mentioned in multiple sources
6. Return ONLY the trending topics, separated by commas
7. Topics should be suitable for news searches

CONTENT TO ANALYZE:
{content_text}

OUTPUT FORMAT: Return only the trending topics separated by commas, nothing else.
Example: "ChatGPT-4o launch, AI regulation EU, OpenAI funding round, LLM hallucination fix"
"""

        # Step 5: Get LLM analysis
        client = get_openai_client()
        if not client:
            return {
                "success": False,
                "error": "OpenAI client not available",
                "trending_topics": []
            }
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a trending topics analyst that extracts specific trending themes from news and social media content."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        # Step 6: Parse LLM response
        llm_response = response.choices[0].message.content.strip()
        logger.info(f"LLM response: {llm_response}")
        
        # Extract trending topics
        trending_topics = []
        if llm_response:
            raw_topics = [s.strip() for s in llm_response.split(',')]
            trending_topics = [t for t in raw_topics if t and len(t) > 2]
        
        logger.info(f"Extracted {len(trending_topics)} trending topics: {trending_topics}")
        
        return {
            "success": True,
            "subtopic": subtopic_title,
            "gnews_articles_count": len(gnews_articles),
            "reddit_posts_count": len(reddit_posts),
            "trending_topics": trending_topics,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting trending topics for subtopic: {e}")
        return {
            "success": False,
            "error": str(e),
            "trending_topics": []
        }

def extract_trending_subtopics(topic, lang="en", country="us", max_articles=10):
    """
    Extract trending subtopics from news articles for a given topic using LLM analysis.
    
    Args:
        topic (str): The main topic/category to analyze (e.g., "technology", "sports", "business")
        lang (str): Language code (e.g., 'en', 'fr', 'es')
        country (str): Country code (e.g., 'us', 'fr', 'gb')
        max_articles (int): Number of articles to analyze (default 10)
    
    Returns:
        dict: Response with success status and list of trending subtopic keywords
    """
    try:
        logger.info(f"Extracting trending subtopics for topic: {topic}")
        
        # Step 1: Fetch headlines using existing function
        gnews_response = gnews_top_headlines(
            category=topic.lower(),
            lang=lang,
            country=country,
            max_articles=max_articles
        )
        
        # Check if we got articles
        if not gnews_response.get("success") or not gnews_response.get("articles"):
            logger.warning(f"No articles found for topic: {topic}")
            return {
                "success": False,
                "error": f"No articles found for topic: {topic}",
                "subtopics": []
            }
        
        articles = gnews_response["articles"]
        logger.info(f"Fetched {len(articles)} articles for analysis")
        
        # Step 2: Prepare articles text for LLM analysis
        articles_text = ""
        for i, article in enumerate(articles[:10], 1):  # Limit to first 10 articles
            title = article.get('title', '')
            description = article.get('description', '')
            
            articles_text += f"Article {i}:\n"
            articles_text += f"Title: {title}\n"
            if description:
                articles_text += f"Description: {description}\n"
            articles_text += "\n"
        
        # Step 3: Create LLM prompt for subtopic extraction
        analysis_prompt = f"""You are a news analysis expert. Analyze the following {len(articles)} news articles about "{topic}" and extract the top trending subtopics.

TASK: Extract 5-8 specific trending subtopics as keywords from these articles.

RULES:
1. Focus on SPECIFIC trending themes, not general concepts
2. Extract keywords that represent current trends and hot topics
3. Avoid very general terms like "news" or "updates"
4. Prefer specific technologies, events, companies, or phenomena mentioned
5. Return ONLY the keywords, separated by commas
6. Each keyword should be 1-3 words maximum
7. Focus on what's currently trending or newsworthy
8. Don't be very specific, if you see that a theme will only appear once in one article, don't include it. The themes should be elligibe for a news feed.

ARTICLES TO ANALYZE:
{articles_text}

OUTPUT FORMAT: Return only the trending subtopic keywords separated by commas, nothing else.
Example: "AI regulation, ChatGPT updates, tech layoffs, startup funding, cybersecurity threats"
"""

        # Step 4: Get LLM analysis
        client = get_openai_client()
        if not client:
            return {
                "success": False,
                "error": "OpenAI client not available",
                "subtopics": []
            }
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a news analysis expert that extracts trending subtopics from news articles."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=200,
            temperature=0.3  # Lower temperature for more consistent results
        )
        
        # Step 5: Parse LLM response
        llm_response = response.choices[0].message.content.strip()
        logger.info(f"LLM response: {llm_response}")
        
        # Extract subtopics from response
        subtopics = []
        if llm_response:
            # Split by commas and clean up
            raw_subtopics = [s.strip() for s in llm_response.split(',')]
            subtopics = [s for s in raw_subtopics if s and len(s) > 2]  # Filter out empty or too short
        
        logger.info(f"Extracted {len(subtopics)} trending subtopics: {subtopics}")
        
        return {
            "success": True,
            "topic": topic,
            "articles_analyzed": len(articles),
            "subtopics": subtopics,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Error extracting trending subtopics: {e}")
        return {
            "success": False,
            "error": str(e),
            "subtopics": []
        }

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

def get_articles_subtopics_user(subtopic_name, subtopic_data, lang="en", country="us", include_comments=False, max_comments=3):
    """
    Fetch articles and Reddit posts for a user's subtopic.
    
    Args:
        subtopic_name (str): Name of the subtopic (e.g., "Finance")
        subtopic_data (dict): Subtopic data with format:
            {
                "subreddits": ["personalfinance", "stocks", "cryptocurrency"],
                "queries": ["stock market", "bitcoin", "interest rates"]
            }
        lang (str): Language code for GNews API
        country (str): Country code for GNews API
        include_comments (bool): Whether to include top comments for Reddit posts
        max_comments (int): Maximum number of top comments to fetch per post
    
    Returns:
        dict: Response with format:
            {
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
                            "comments": [  # Only if include_comments=True
                                {
                                    "body": "Comment text",
                                    "author": "commenter",
                                    "score": 67,
                                    "created_utc": 1716883300.0,
                                    "replies_count": 3,
                                    "is_submitter": false
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
            }
    """
    try:
        logger.info(f"Fetching articles and posts for subtopic: {subtopic_name}")
        
        result = {
            subtopic_name: [],
            "subreddits": {},
            "queries": {}
        }
        
        # Step 1: Fetch top 2 articles for the subtopic name itself
        logger.info(f"Fetching articles for subtopic name: {subtopic_name}")
        subtopic_response = gnews_search(
            query=subtopic_name,
            lang=lang,
            country=country,
            max_articles=2,
            from_date=(datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        
        # Check if quota is exceeded from the first request
        quota_exceeded = False
        if not subtopic_response.get("success"):
            error_msg = subtopic_response.get("error", "")
            if "quota" in error_msg.lower() or "forbidden" in error_msg.lower():
                quota_exceeded = True
                logger.warning(f"GNews quota exceeded for subtopic '{subtopic_name}'. Queries will return empty results.")
        
        if subtopic_response.get("success") and subtopic_response.get("articles"):
            result[subtopic_name] = format_gnews_articles_for_prysm(subtopic_response)[:2]
            logger.info(f"Found {len(result[subtopic_name])} articles for subtopic name")
        else:
            logger.warning(f"No articles found for subtopic name: {subtopic_name}")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        # Step 2: Fetch top 2 articles for each query
        queries = subtopic_data.get("queries", [])
        logger.info(f"🔍 SUBTOPIC DEBUG: Fetching articles for {len(queries)} queries: {queries}")
        
        for i, query in enumerate(queries):
            logger.info(f"🔍 SUBTOPIC DEBUG: Processing query {i+1}/{len(queries)}: '{query}'")
            
            # Skip if quota already exceeded
            if quota_exceeded:
                result["queries"][query] = []
                logger.warning(f"⚠️ SUBTOPIC DEBUG: Skipping query '{query}' due to quota limit")
                continue
            
            # Add delay between requests to avoid rate limiting
            if i > 0:
                time.sleep(1)
            
            query_response = gnews_search(
                query=query,
                lang=lang,
                country=country,
                max_articles=2,
                from_date=(datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            
            logger.info(f"📊 SUBTOPIC DEBUG: Query '{query}' response success: {query_response.get('success', False)}")
            logger.info(f"📊 SUBTOPIC DEBUG: Query '{query}' articles count: {len(query_response.get('articles', []))}")
            
            if query_response.get("success") and query_response.get("articles"):
                result["queries"][query] = format_gnews_articles_for_prysm(query_response)[:2]
                logger.info(f"✅ SUBTOPIC DEBUG: Found {len(result['queries'][query])} articles for query: {query}")
            else:
                result["queries"][query] = []
                error_msg = query_response.get("error", "")
                
                logger.warning(f"⚠️ SUBTOPIC DEBUG: No articles for query '{query}'. Error: {error_msg}")
                
                if "quota" in error_msg.lower() or "forbidden" in error_msg.lower():
                    quota_exceeded = True
                    logger.warning(f"🚫 SUBTOPIC DEBUG: Daily quota exceeded for query: {query}. Skipping remaining queries.")
                    # Fill remaining queries with empty arrays
                    for remaining_query in queries[i+1:]:
                        result["queries"][remaining_query] = []
                        logger.warning(f"⚠️ SUBTOPIC DEBUG: Skipped remaining query: {remaining_query}")
                    break
                elif "rate limit" in error_msg.lower() or "too many" in error_msg.lower():
                    logger.warning(f"🚫 SUBTOPIC DEBUG: Rate limit hit for query: {query}. Skipping remaining queries.")
                    # Fill remaining queries with empty arrays
                    for remaining_query in queries[i+1:]:
                        result["queries"][remaining_query] = []
                        logger.warning(f"⚠️ SUBTOPIC DEBUG: Skipped remaining query: {remaining_query}")
                    break
                else:
                    logger.warning(f"⚠️ SUBTOPIC DEBUG: No articles found for query: {query} (not a quota/rate limit issue)")
        
        # Log quota status
        if quota_exceeded:
            logger.warning("GNews daily quota has been exceeded. Some queries returned no results.")
        
        # Step 3: Fetch top 2 posts from each subreddit
        subreddits = subtopic_data.get("subreddits", [])
        logger.info(f"Fetching posts from {len(subreddits)} subreddits")
        
        headers = {"User-Agent": "NewsXTrendingBot/1.0"}
        
        for subreddit in subreddits:
            logger.info(f"Fetching posts from r/{subreddit}")
            try:
                # Use 'top' endpoint with time filter for last 24 hours
                url = f"https://www.reddit.com/r/{subreddit}/top.json?t=day&limit=2"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                posts = []
                if "data" in data and "children" in data["data"]:
                    for post in data["data"]["children"]:
                        post_data = post.get("data", {})
                        
                        # Check if post is from last 24 hours
                        created_utc = post_data.get("created_utc", 0)
                        post_time = datetime.fromtimestamp(created_utc)
                        time_diff = datetime.now() - post_time
                        
                        if time_diff.total_seconds() <= 86400:  # 24 hours
                            posts.append({
                                "title": post_data.get("title", ""),
                                "score": post_data.get("score", 0),
                                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                "subreddit": subreddit,
                                "created_utc": created_utc,
                                "num_comments": post_data.get("num_comments", 0),
                                "author": post_data.get("author", ""),
                                "selftext": post_data.get("selftext", "")  # Return full selftext
                            })
                
                result["subreddits"][subreddit] = posts[:2]  # Top 2 posts
                logger.info(f"Found {len(result['subreddits'][subreddit])} posts from r/{subreddit}")
                
            except Exception as e:
                result["subreddits"][subreddit] = []
                logger.warning(f"Failed to fetch from r/{subreddit}: {e}")
        
        # Step 4: Fetch top comments for Reddit posts if requested
        if include_comments:
            logger.info(f"Fetching top {max_comments} comments for each Reddit post")
            for subreddit, posts in result["subreddits"].items():
                for post in posts:
                    # Extract permalink from the full URL
                    permalink = post["url"].replace("https://reddit.com", "")
                    comments = get_reddit_post_comments(permalink, max_comments)
                    post["comments"] = comments
                    logger.info(f"Added {len(comments)} comments to post: {post['title'][:50]}...")
        
        # Log summary
        total_articles = len(result[subtopic_name]) + sum(len(articles) for articles in result["queries"].values())
        total_posts = sum(len(posts) for posts in result["subreddits"].values())
        
        logger.info(f"Successfully fetched content for {subtopic_name}:")
        logger.info(f"  - Subtopic articles: {len(result[subtopic_name])}")
        logger.info(f"  - Query articles: {total_articles - len(result[subtopic_name])}")
        logger.info(f"  - Reddit posts: {total_posts}")
        
        return {
            "success": True,
            "data": result,
            "summary": {
                "subtopic_articles": len(result[subtopic_name]),
                "query_articles": sum(len(articles) for articles in result["queries"].values()),
                "reddit_posts": total_posts,
                "total_queries": len(queries),
                "total_subreddits": len(subreddits)
            },
            "warnings": {
                "quota_exceeded": quota_exceeded,
                "message": "GNews daily quota exceeded - some queries returned no results" if quota_exceeded else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_articles_subtopics_user: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                subtopic_name: [],
                "subreddits": {},
                "queries": {}
            }
        }

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

def get_topic_posts(topic_name, topic_data, lang="en", country="us"):
    """
    Fetch articles and posts for a complete user topic with all its subtopics.
    
    Args:
        topic_name (str): Name of the topic (e.g., "business", "technology")
        topic_data (dict): Complete topic data from user preferences with format:
            {
                "Finance": {
                    "subreddits": ["personalfinance", "stocks", "cryptocurrency"],
                    "queries": ["stock market", "bitcoin", "interest rates"]
                },
                "Economy": {
                    "subreddits": ["economics", "investing"],
                    "queries": ["inflation", "GDP", "economic policy"]
                }
            }
        lang (str): Language code for GNews API
        country (str): Country code for GNews API
    
    Returns:
        dict: Response with format:
            {
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
            }
    """
    try:
        logger.info(f"Fetching posts for topic: {topic_name} with {len(topic_data)} subtopics")
        
        result = {
            "topic_headlines": [],
            "subtopics": {}
        }
        
        # Process each subtopic using get_articles_subtopics_user
        subtopic_names = list(topic_data.keys())
        logger.info(f"Processing {len(subtopic_names)} subtopics: {subtopic_names}")
        
        for i, (subtopic_name, subtopic_data) in enumerate(topic_data.items()):
            logger.info(f"Processing subtopic {i+1}/{len(subtopic_names)}: {subtopic_name}")
            
            # Add delay between subtopics to avoid overwhelming APIs
            if i > 0:
                time.sleep(2)
            
            # Call the existing function for this subtopic
            subtopic_result = get_articles_subtopics_user(
                subtopic_name=subtopic_name,
                subtopic_data=subtopic_data,
                lang=lang,
                country=country
            )
            
            if subtopic_result.get("success"):
                result["subtopics"][subtopic_name] = subtopic_result.get("data", {})
                summary = subtopic_result.get("summary", {})
                logger.info(f"Subtopic '{subtopic_name}' completed: {summary.get('subtopic_articles', 0)} articles, {summary.get('query_articles', 0)} query articles, {summary.get('reddit_posts', 0)} posts")
            else:
                result["subtopics"][subtopic_name] = {
                    subtopic_name: [],
                    "subreddits": {},
                    "queries": {}
                }
                logger.error(f"Failed to process subtopic '{subtopic_name}': {subtopic_result.get('error', 'Unknown error')}")
        
        # Calculate summary statistics
        total_subtopic_articles = sum(
            len(subtopic_data.get(subtopic_name, [])) 
            for subtopic_name, subtopic_data in result["subtopics"].items()
        )
        total_query_articles = sum(
            sum(len(articles) for articles in subtopic_data.get("queries", {}).values())
            for subtopic_data in result["subtopics"].values()
        )
        total_reddit_posts = sum(
            sum(len(posts) for posts in subtopic_data.get("subreddits", {}).values())
            for subtopic_data in result["subtopics"].values()
        )
        
        logger.info(f"Topic '{topic_name}' processing completed:")
        logger.info(f"  - Topic headlines: {len(result['topic_headlines'])}")
        logger.info(f"  - Subtopics processed: {len(result['subtopics'])}")
        logger.info(f"  - Total subtopic articles: {total_subtopic_articles}")
        logger.info(f"  - Total query articles: {total_query_articles}")
        logger.info(f"  - Total Reddit posts: {total_reddit_posts}")
        
        return {
            "success": True,
            "data": result,
            "summary": {
                "topic_headlines": len(result["topic_headlines"]),
                "subtopics_processed": len(result["subtopics"]),
                "total_subtopic_articles": total_subtopic_articles,
                "total_query_articles": total_query_articles,
                "total_reddit_posts": total_reddit_posts
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_topic_posts: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "topic_headlines": [],
                "subtopics": {}
            }
        }

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

def get_reddit_post_comments(post_permalink, max_comments=3):
    """
    Fetch top comments for a specific Reddit post.
    
    Args:
        post_permalink (str): Reddit post permalink (e.g., "/r/personalfinance/comments/abc123/post_title/")
        max_comments (int): Maximum number of top-level comments to fetch
    
    Returns:
        list: List of top comments with format:
            [
                {
                    "body": "Comment text",
                    "author": "username",
                    "score": 123,
                    "created_utc": 1716883200.0,
                    "replies_count": 5,
                    "is_submitter": false
                }
            ]
    """
    try:
        headers = {"User-Agent": "NewsXTrendingBot/1.0"}
        # Reddit comments API endpoint
        url = f"https://www.reddit.com{post_permalink}.json?limit={max_comments}&sort=top"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        comments = []
        
        # Reddit returns an array with 2 elements: [post_data, comments_data]
        if len(data) >= 2 and "data" in data[1] and "children" in data[1]["data"]:
            comments_data = data[1]["data"]["children"]
            
            for comment in comments_data[:max_comments]:
                if comment.get("kind") == "t1":  # t1 = comment type
                    comment_data = comment.get("data", {})
                    
                    # Skip deleted/removed comments
                    if comment_data.get("body") in ["[deleted]", "[removed]"]:
                        continue
                    
                    # Count replies
                    replies_count = 0
                    if "replies" in comment_data and comment_data["replies"]:
                        if isinstance(comment_data["replies"], dict):
                            replies_data = comment_data["replies"].get("data", {})
                            if "children" in replies_data:
                                replies_count = len([r for r in replies_data["children"] if r.get("kind") == "t1"])
                    
                    comments.append({
                        "body": comment_data.get("body", ""),
                        "author": comment_data.get("author", ""),
                        "score": comment_data.get("score", 0),
                        "created_utc": comment_data.get("created_utc", 0),
                        "replies_count": replies_count,
                        "is_submitter": comment_data.get("is_submitter", False),
                        "distinguished": comment_data.get("distinguished"),  # mod/admin comments
                        "stickied": comment_data.get("stickied", False)
                    })
        
        logger.info(f"Fetched {len(comments)} comments for post {post_permalink}")
        return comments
        
    except Exception as e:
        logger.warning(f"Failed to fetch comments for {post_permalink}: {e}")
        return []

def get_articles_subtopics_user_with_comments(subtopic_name, subtopic_data, lang="en", country="us", include_comments=False, max_comments=3):
    """
    Fetch articles and Reddit posts for a user's subtopic, including top comments for Reddit posts.
    
    Args:
        subtopic_name (str): Name of the subtopic (e.g., "Finance")
        subtopic_data (dict): Subtopic data with format:
            {
                "subreddits": ["personalfinance", "stocks", "cryptocurrency"],
                "queries": ["stock market", "bitcoin", "interest rates"]
            }
        lang (str): Language code for GNews API
        country (str): Country code for GNews API
        include_comments (bool): Whether to include top comments for Reddit posts
        max_comments (int): Maximum number of top comments to fetch
    
    Returns:
        dict: Response with format:
            {
                "Finance": [top2_articles],
                "subreddits": {
                    "personalfinance": [top2_posts],
                    "stocks": [top2_posts],
                    "cryptocurrency": [top2_posts]
                },
                "queries": {
                    "stock market": [top2_articles],
                    "bitcoin": [top2_articles], 
                    "interest rates": [top2_articles]
                },
                "comments": [top_comments]
            }
    """
    try:
        logger.info(f"Fetching articles and posts for subtopic: {subtopic_name}")
        
        result = {
            subtopic_name: [],
            "subreddits": {},
            "queries": {},
            "comments": []
        }
        
        # Step 1: Fetch top 2 articles for the subtopic name itself
        logger.info(f"Fetching articles for subtopic name: {subtopic_name}")
        subtopic_response = gnews_search(
            query=subtopic_name,
            lang=lang,
            country=country,
            max_articles=2,
            from_date=(datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        
        # Check if quota is exceeded from the first request
        quota_exceeded = False
        if not subtopic_response.get("success"):
            error_msg = subtopic_response.get("error", "")
            if "quota" in error_msg.lower() or "forbidden" in error_msg.lower():
                quota_exceeded = True
                logger.warning(f"GNews quota exceeded for subtopic '{subtopic_name}'. Queries will return empty results.")
        
        if subtopic_response.get("success") and subtopic_response.get("articles"):
            result[subtopic_name] = format_gnews_articles_for_prysm(subtopic_response)[:2]
            logger.info(f"Found {len(result[subtopic_name])} articles for subtopic name")
        else:
            logger.warning(f"No articles found for subtopic name: {subtopic_name}")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        # Step 2: Fetch top 2 articles for each query
        queries = subtopic_data.get("queries", [])
        logger.info(f"Fetching articles for {len(queries)} queries")
        
        for i, query in enumerate(queries):
            logger.info(f"Fetching articles for query: {query}")
            
            # Skip if quota already exceeded
            if quota_exceeded:
                result["queries"][query] = []
                logger.warning(f"Skipping query '{query}' due to quota limit")
                continue
            
            # Add delay between requests to avoid rate limiting
            if i > 0:
                time.sleep(1)
            
            query_response = gnews_search(
                query=query,
                lang=lang,
                country=country,
                max_articles=2,
                from_date=(datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            
            if query_response.get("success") and query_response.get("articles"):
                result["queries"][query] = format_gnews_articles_for_prysm(query_response)[:2]
                logger.info(f"Found {len(result['queries'][query])} articles for query: {query}")
            else:
                result["queries"][query] = []
                error_msg = query_response.get("error", "")
                
                if "quota" in error_msg.lower() or "forbidden" in error_msg.lower():
                    quota_exceeded = True
                    logger.warning(f"Daily quota exceeded for query: {query}. Skipping remaining queries.")
                    # Fill remaining queries with empty arrays
                    for remaining_query in queries[i+1:]:
                        result["queries"][remaining_query] = []
                    break
                elif "rate limit" in error_msg.lower() or "too many" in error_msg.lower():
                    logger.warning(f"Rate limit hit for query: {query}. Skipping remaining queries.")
                    # Fill remaining queries with empty arrays
                    for remaining_query in queries[i+1:]:
                        result["queries"][remaining_query] = []
                    break
                else:
                    logger.warning(f"No articles found for query: {query}")
        
        # Log quota status
        if quota_exceeded:
            logger.warning("GNews daily quota has been exceeded. Some queries returned no results.")
        
        # Step 3: Fetch top 2 posts from each subreddit
        subreddits = subtopic_data.get("subreddits", [])
        logger.info(f"Fetching posts from {len(subreddits)} subreddits")
        
        headers = {"User-Agent": "NewsXTrendingBot/1.0"}
        
        for subreddit in subreddits:
            logger.info(f"Fetching posts from r/{subreddit}")
            try:
                # Use 'top' endpoint with time filter for last 24 hours
                url = f"https://www.reddit.com/r/{subreddit}/top.json?t=day&limit=2"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                posts = []
                if "data" in data and "children" in data["data"]:
                    for post in data["data"]["children"]:
                        post_data = post.get("data", {})
                        
                        # Check if post is from last 24 hours
                        created_utc = post_data.get("created_utc", 0)
                        post_time = datetime.fromtimestamp(created_utc)
                        time_diff = datetime.now() - post_time
                        
                        if time_diff.total_seconds() <= 86400:  # 24 hours
                            posts.append({
                                "title": post_data.get("title", ""),
                                "score": post_data.get("score", 0),
                                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                "subreddit": subreddit,
                                "created_utc": created_utc,
                                "num_comments": post_data.get("num_comments", 0),
                                "author": post_data.get("author", ""),
                                "selftext": post_data.get("selftext", "")  # Return full selftext
                            })
                
                result["subreddits"][subreddit] = posts[:2]  # Top 2 posts
                logger.info(f"Found {len(result['subreddits'][subreddit])} posts from r/{subreddit}")
                
            except Exception as e:
                result["subreddits"][subreddit] = []
                logger.warning(f"Failed to fetch from r/{subreddit}: {e}")
        
        # Step 4: Fetch top comments for Reddit posts if requested
        if include_comments:
            logger.info(f"Fetching top {max_comments} comments for each Reddit post")
            for subreddit, posts in result["subreddits"].items():
                for post in posts:
                    # Extract permalink from the full URL
                    permalink = post["url"].replace("https://reddit.com", "")
                    comments = get_reddit_post_comments(permalink, max_comments)
                    post["comments"] = comments
                    logger.info(f"Added {len(comments)} comments to post: {post['title'][:50]}...")
        
        # Log summary
        total_articles = len(result[subtopic_name]) + sum(len(articles) for articles in result["queries"].values())
        total_posts = sum(len(posts) for posts in result["subreddits"].values())
        
        logger.info(f"Successfully fetched content for {subtopic_name}:")
        logger.info(f"  - Subtopic articles: {len(result[subtopic_name])}")
        logger.info(f"  - Query articles: {total_articles - len(result[subtopic_name])}")
        logger.info(f"  - Reddit posts: {total_posts}")
        
        return {
            "success": True,
            "data": result,
            "summary": {
                "subtopic_articles": len(result[subtopic_name]),
                "query_articles": sum(len(articles) for articles in result["queries"].values()),
                "reddit_posts": total_posts,
                "total_queries": len(queries),
                "total_subreddits": len(subreddits)
            },
            "warnings": {
                "quota_exceeded": quota_exceeded,
                "message": "GNews daily quota exceeded - some queries returned no results" if quota_exceeded else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_articles_subtopics_user_with_comments: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                subtopic_name: [],
                "subreddits": {},
                "queries": {},
                "comments": []
            }
        }

def get_pickup_line(topic_name, topic_content_data):
    """
    Generate an engaging 1-sentence pickup line for a topic based on retrieved content.
    
    Args:
        topic_name (str): Name of the topic (e.g., "Business", "Technology")
        topic_content_data (dict): Complete topic data from get_topic_posts() with format:
            {
                "success": True,
                "data": {
                    "topic_headlines": [articles],
                    "subtopics": {
                        "Finance": {
                            "Finance": [articles],
                            "subreddits": {"personalfinance": [posts]},
                            "queries": {"stock market": [articles]}
                        }
                    }
                }
            }
    
    Returns:
        dict: Response with format:
            {
                "success": True,
                "pickup_line": "One engaging sentence to entice user to click...",
                "topic_name": "Business",
                "content_summary": {
                    "total_articles": 15,
                    "subtopics_count": 3,
                    "trending_keywords": ["AI", "stocks", "inflation"]
                }
            }
    """
    try:
        logger.info(f"Generating pickup line for topic: {topic_name}")
        
        if not topic_content_data.get("success"):
            raise ValueError(f"Invalid topic content data: {topic_content_data.get('error', 'Unknown error')}")
        
        data = topic_content_data.get("data", {})
        
        # Extract and summarize all content (focus on articles only, not Reddit)
        content_summary = {
            "total_articles": 0,
            "subtopics_count": 0,
            "trending_keywords": [],
            "key_headlines": []
        }
        
        # Count topic headlines
        topic_headlines = data.get("topic_headlines", [])
        content_summary["total_articles"] += len(topic_headlines)
        
        # Extract key headlines from topic
        for article in topic_headlines[:3]:  # Top 3 headlines
            if article.get("title"):
                content_summary["key_headlines"].append(article["title"])
        
        # Process subtopics
        subtopics = data.get("subtopics", {})
        content_summary["subtopics_count"] = len(subtopics)
        
        for subtopic_name, subtopic_data in subtopics.items():
            # Count subtopic articles
            subtopic_articles = subtopic_data.get(subtopic_name, [])
            content_summary["total_articles"] += len(subtopic_articles)
            
            # Extract headlines from subtopic articles
            for article in subtopic_articles[:2]:  # Top 2 per subtopic
                if article.get("title"):
                    content_summary["key_headlines"].append(article["title"])
            
            # Count query articles and add queries as trending keywords
            queries = subtopic_data.get("queries", {})
            for query, articles in queries.items():
                content_summary["total_articles"] += len(articles)
                content_summary["trending_keywords"].append(query)
        
        # Limit arrays to prevent overwhelming the LLM
        content_summary["key_headlines"] = content_summary["key_headlines"][:6]
        content_summary["trending_keywords"] = list(set(content_summary["trending_keywords"]))[:5]
        
        # Create prompt for OpenAI
        prompt = f"""You are a professional news editor creating clean, concise topic titles. Your task is to create a short, professional title for the "{topic_name}" topic that summarizes the key development.

TOPIC CONTENT SUMMARY:
- Topic: {topic_name}
- Total Articles: {content_summary['total_articles']}
- Subtopics: {content_summary['subtopics_count']} ({', '.join(subtopics.keys()) if subtopics else 'None'})
- Trending Keywords: {', '.join(content_summary['trending_keywords']) if content_summary['trending_keywords'] else 'None'}

KEY HEADLINES:
{chr(10).join([f"• {headline}" for headline in content_summary['key_headlines'][:4]])}

INSTRUCTIONS:
1. Write a clean, professional title (exactly 3-5 words)
2. NO emojis, NO "BREAKING", NO dramatic language
3. Focus on the main trend or development
4. Use business/professional tone
5. Be specific and factual
6. Mention numbers, companies, or concrete developments when relevant

GOOD EXAMPLES:
- "AI Investment Reaches $50B"
- "Tesla Stock Drops 15%"
- "Federal Reserve Cuts Rates"
- "Tech Layoffs Continue Rising"
- "Oil Prices Hit $90"

Generate the clean title now:"""

        # Get OpenAI client and generate response
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional news editor. Always respond with clean, factual titles without emojis or dramatic language. Keep titles to 3-5 words maximum."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )

        pickup_line = response.choices[0].message.content.strip()
        
        logger.info(f"Generated pickup line for {topic_name}: {pickup_line[:100]}...")
        
        return {
            "success": True,
            "pickup_line": pickup_line,
            "topic_name": topic_name,
            "content_summary": content_summary,
            "generation_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating pickup line for {topic_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "topic_name": topic_name,
            "pickup_line": f"Discover what's trending in {topic_name} right now with breaking stories and latest developments.",
            "fallback": True
        }

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

def get_topic_summary(topic_name, topic_content_data):
    """
    Generate a comprehensive summary of all topic content with key facts from each article.
    
    Args:
        topic_name (str): Name of the topic (e.g., "Business", "Technology")
        topic_content_data (dict): Complete topic data from get_topic_posts() with format:
            {
                "success": True,
                "data": {
                    "topic_headlines": [articles],
                    "subtopics": {
                        "Finance": {
                            "Finance": [articles],
                            "subreddits": {"personalfinance": [posts]},
                            "queries": {"stock market": [articles]}
                        }
                    }
                }
            }
    
    Returns:
        dict: Response with format:
            {
                "success": True,
                "topic_summary": "Comprehensive formatted summary with key facts...",
                "topic_name": "Business",
                "content_stats": {
                    "total_articles": 15,
                    "total_posts": 8,
                    "subtopics_analyzed": 3
                }
            }
    """
    try:
        logger.info(f"Generating comprehensive summary for topic: {topic_name}")
        
        if not topic_content_data.get("success"):
            raise ValueError(f"Invalid topic content data: {topic_content_data.get('error', 'Unknown error')}")
        
        data = topic_content_data.get("data", {})
        
        # Collect all content for analysis
        all_content = {
            "topic_headlines": [],
            "subtopic_articles": {},
            "query_articles": {},
            "reddit_discussions": {}
        }
        
        content_stats = {
            "total_articles": 0,
            "total_posts": 0,
            "subtopics_analyzed": 0
        }
        
        # Collect topic headlines
        topic_headlines = data.get("topic_headlines", [])
        all_content["topic_headlines"] = topic_headlines
        content_stats["total_articles"] += len(topic_headlines)
        
        # Collect subtopic content
        subtopics = data.get("subtopics", {})
        content_stats["subtopics_analyzed"] = len(subtopics)
        
        for subtopic_name, subtopic_data in subtopics.items():
            # Collect subtopic articles
            subtopic_articles = subtopic_data.get(subtopic_name, [])
            if subtopic_articles:
                all_content["subtopic_articles"][subtopic_name] = subtopic_articles
                content_stats["total_articles"] += len(subtopic_articles)
            
            # Collect query articles
            queries = subtopic_data.get("queries", {})
            for query, articles in queries.items():
                if articles:
                    all_content["query_articles"][f"{subtopic_name} - {query}"] = articles
                    content_stats["total_articles"] += len(articles)
            
            # Collect Reddit discussions
            subreddits = subtopic_data.get("subreddits", {})
            for subreddit, posts in subreddits.items():
                if posts:
                    all_content["reddit_discussions"][f"{subtopic_name} - r/{subreddit}"] = posts
                    content_stats["total_posts"] += len(posts)
        
        # Prepare content for LLM analysis
        content_text = f"TOPIC: {topic_name}\n\n"
        
        # Add topic headlines
        if all_content["topic_headlines"]:
            content_text += "🔥 MAIN TOPIC HEADLINES:\n"
            for i, article in enumerate(all_content["topic_headlines"], 1):
                title = article.get('title', 'No title')
                snippet = article.get('snippet', article.get('description', ''))
                source = article.get('source', 'Unknown source')
                content_text += f"{i}. {title}\n"
                content_text += f"   Source: {source}\n"
                if snippet:
                    content_text += f"   Summary: {snippet}\n"
                content_text += "\n"
        
        # Add subtopic articles
        if all_content["subtopic_articles"]:
            content_text += "📊 SUBTOPIC ARTICLES:\n"
            for subtopic_name, articles in all_content["subtopic_articles"].items():
                content_text += f"\n{subtopic_name.upper()}:\n"
                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'No title')
                    snippet = article.get('snippet', article.get('description', ''))
                    source = article.get('source', 'Unknown source')
                    content_text += f"  {i}. {title}\n"
                    content_text += f"     Source: {source}\n"
                    if snippet:
                        content_text += f"     Summary: {snippet}\n"
                content_text += "\n"
        
        # Add query-based articles
        if all_content["query_articles"]:
            content_text += "🔍 QUERY-BASED ARTICLES:\n"
            for query_label, articles in all_content["query_articles"].items():
                content_text += f"\n{query_label.upper()}:\n"
                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'No title')
                    snippet = article.get('snippet', article.get('description', ''))
                    source = article.get('source', 'Unknown source')
                    content_text += f"  {i}. {title}\n"
                    content_text += f"     Source: {source}\n"
                    if snippet:
                        content_text += f"     Summary: {snippet}\n"
                content_text += "\n"
        
        # Add Reddit discussions
        if all_content["reddit_discussions"]:
            content_text += "💬 REDDIT DISCUSSIONS:\n"
            for subreddit_label, posts in all_content["reddit_discussions"].items():
                content_text += f"\n{subreddit_label.upper()}:\n"
                for i, post in enumerate(posts, 1):
                    title = post.get('title', 'No title')
                    score = post.get('score', 0)
                    selftext = post.get('selftext', '')
                    content_text += f"  {i}. {title} ({score} upvotes)\n"
                    if selftext and len(selftext) > 10:
                        content_text += f"     Content: {selftext[:200]}...\n"
                content_text += "\n"
        
        # Create LLM prompt for summary generation
        summary_prompt = f"""You are a professional news analyst creating clean, structured summaries. Create a concise summary of the {topic_name} topic based on the content below.

INSTRUCTIONS:
1. Write in a professional, factual tone
2. Use clean structure with clear sections
3. Keep the entire summary under 100 words
4. Use minimal formatting for better mobile readability
5. Focus on key facts and developments
6. No excessive emojis or dramatic language
7. Use simple bullet points and clear sections

FORMATTING RULES FOR iOS:
- Use double line breaks between sections
- Use "•" for bullet points (not dashes or asterisks)  
- Put each bullet point on its own line
- Avoid complex markdown - keep it simple
- Use **bold** only for section headers
- CREATE YOUR OWN SECTION TITLES based on the actual content - don't use generic templates

DYNAMIC FORMATTING INSTRUCTIONS:
- Analyze the content and create 2-3 relevant section titles that match what you're discussing
- Section titles should be specific to the content, not generic like "Key Developments" or "Market Impact"
- Examples of good dynamic titles: "AI Chip Shortage", "Federal Reserve Updates", "Tesla Production Changes", "European Energy Crisis", etc.
- Make titles descriptive and specific to what's actually happening

FORMAT STRUCTURE:
**{topic_name} Summary**

**[Your Dynamic Title 1 Based on Actual Content]**
• [Brief fact 1]
• [Brief fact 2]

**[Your Dynamic Title 2 Based on Actual Content]**
• [Relevant information]

**[Your Dynamic Title 3 Based on Actual Content]** (if needed)
• [Important trends or developments]

CONTENT TO ANALYZE:
{content_text}

Generate the clean, professional summary now (MAX 100 WORDS):"""

        # Get OpenAI client and generate response
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional news analyst who creates clean, factual summaries with DYNAMIC section titles. Analyze the content and create specific, relevant section headers rather than using generic templates like 'Key Developments' or 'Market Impact'. Make section titles descriptive and specific to what's actually happening in the news. Use simple formatting, avoid excessive emojis, and focus on key facts. Keep summaries concise and professional."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=150,
            temperature=0.4
        )
        
        topic_summary = response.choices[0].message.content.strip()
        
        logger.info(f"Generated comprehensive summary for {topic_name}: {len(topic_summary)} characters")
        
        return {
            "success": True,
            "topic_summary": topic_summary,
            "topic_name": topic_name,
            "content_stats": content_stats,
            "generation_timestamp": datetime.now().isoformat(),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating topic summary for {topic_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "topic_name": topic_name,
            "topic_summary": f"# {topic_name} Summary\n\nUnable to generate detailed summary at this time. Please try again later.",
            "fallback": True
        }

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

def get_reddit_world_summary(reddit_posts_data):
    """
    Generate a concise executive summary of Reddit posts and comments focused on world events.
    Filters out personal content and presents key trends/developments in a professional format.
    
    Args:
        reddit_posts_data (list): List of Reddit posts with comments in format:
            [
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
    
    Returns:
        dict: Response with format:
            {
                "success": True,
                "world_summary": "Executive summary of world events and trends...",
                "posts_analyzed": 15,
                "relevant_posts": 8,
                "key_topics": ["topic1", "topic2"]
            }
    """
    try:
        logger.info(f"Generating world summary from {len(reddit_posts_data)} Reddit posts")
        
        if not reddit_posts_data:
            return {
                "success": True,
                "world_summary": "No significant world events or trends detected in current Reddit discussions.",
                "posts_analyzed": 0,
                "relevant_posts": 0,
                "key_topics": []
            }
        
        # Filter and prepare content for analysis
        relevant_content = []
        personal_keywords = [
            "my", "i am", "i'm", "my wife", "my husband", "my job", "my boss", 
            "personal", "relationship", "dating", "family", "parents", "kids",
            "salary", "debt", "loan", "mortgage", "credit card", "budget"
        ]
        
        world_keywords = [
            "government", "politics", "economy", "market", "global", "international",
            "country", "nation", "war", "conflict", "trade", "policy", "election",
            "climate", "technology", "industry", "company", "stock", "inflation",
            "gdp", "unemployment", "regulation", "law", "court", "supreme court"
        ]
        
        relevant_posts = 0
        
        for post in reddit_posts_data:
            title = post.get('title', '').lower()
            selftext = post.get('selftext', '').lower()
            subreddit = post.get('subreddit', '').lower()
            score = post.get('score', 0)
            
            # Skip if too personal
            is_personal = any(keyword in title or keyword in selftext for keyword in personal_keywords)
            
            # Check if relevant to world events
            is_world_relevant = (
                any(keyword in title or keyword in selftext for keyword in world_keywords) or
                subreddit in ['worldnews', 'news', 'politics', 'economics', 'technology', 'business'] or
                score > 100  # High-scoring posts are often newsworthy
            )
            
            if is_world_relevant and not is_personal:
                relevant_posts += 1
                
                # Prepare post content
                post_content = f"SUBREDDIT: r/{post.get('subreddit', 'unknown')}\n"
                post_content += f"TITLE: {post.get('title', 'No title')} ({score} upvotes)\n"
                
                if selftext and len(selftext.strip()) > 20:
                    post_content += f"CONTENT: {selftext[:300]}...\n"
                
                # Add top comments (filter out personal ones)
                comments = post.get('comments', [])
                relevant_comments = []
                
                for comment in comments[:5]:  # Top 5 comments
                    comment_body = comment.get('body', '').lower()
                    comment_score = comment.get('score', 0)
                    
                    # Skip personal comments
                    if not any(keyword in comment_body for keyword in personal_keywords):
                        if comment_score > 10 or any(keyword in comment_body for keyword in world_keywords):
                            relevant_comments.append({
                                'body': comment.get('body', '')[:200],
                                'score': comment_score
                            })
                
                if relevant_comments:
                    post_content += "TOP COMMENTS:\n"
                    for i, comment in enumerate(relevant_comments[:3], 1):
                        post_content += f"  {i}. {comment['body']} ({comment['score']} upvotes)\n"
                
                relevant_content.append(post_content)
        
        if not relevant_content:
            return {
                "success": True,
                "world_summary": "No significant world events or trends detected in current Reddit discussions.",
                "posts_analyzed": len(reddit_posts_data),
                "relevant_posts": 0,
                "key_topics": []
            }
        
        # Create executive summary prompt
        content_text = "\n\n".join(relevant_content[:10])  # Limit to top 10 relevant posts
        
        summary_prompt = f"""You are an executive assistant briefing your boss on current world events and trends based on Reddit discussions.

INSTRUCTIONS:
1. Focus ONLY on world events, politics, economy, technology, and business trends
2. Ignore personal stories, relationship advice, or individual financial situations
3. Present information as if briefing a busy executive (concise, professional)
4. Highlight what's trending, what people are discussing, and key developments
5. MAXIMUM 150 words total (to match other summary lengths)
6. Use iOS-friendly formatting with proper line breaks and bullet points
7. Focus on actionable insights and trends

FORMATTING RULES FOR iOS:
- Use double line breaks (\\n\\n) between sections
- Use • for bullet points (not dashes or asterisks)
- Put each bullet point on its own line
- Use simple bold formatting: **text**
- Avoid complex markdown formatting
- Ensure proper spacing between elements

FORMAT:
**Key Developments:**

• [Major trend/event 1]

• [Major trend/event 2]

REDDIT DISCUSSIONS TO ANALYZE:
{content_text}

Generate the executive brief (MAX 150 words, iOS-FRIENDLY FORMATTING):"""

        # Get OpenAI client and generate response
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an executive assistant who creates concise, professional briefs on world events from social media discussions. Focus on trends, not personal stories. Keep summaries under 150 words and use iOS-friendly formatting with proper line breaks and bullet points (•)."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=200,
            temperature=0.6
        )
        
        world_summary = response.choices[0].message.content.strip()
        
        # Extract key topics mentioned
        key_topics = []
        topic_keywords = ["trump", "biden", "china", "russia", "ukraine", "ai", "crypto", "inflation", "recession", "election", "climate", "energy"]
        for keyword in topic_keywords:
            if keyword in content_text.lower():
                key_topics.append(keyword.title())
        
        logger.info(f"Generated world summary from {relevant_posts} relevant posts out of {len(reddit_posts_data)} total")
        
        return {
            "success": True,
            "world_summary": world_summary,
            "posts_analyzed": len(reddit_posts_data),
            "relevant_posts": relevant_posts,
            "key_topics": key_topics[:6],  # Top 6 topics
            "generation_timestamp": datetime.now().isoformat(),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating Reddit world summary: {e}")
        return {
            "success": False,
            "error": str(e),
            "world_summary": "Unable to generate world summary at this time.",
            "posts_analyzed": len(reddit_posts_data) if reddit_posts_data else 0,
            "relevant_posts": 0,
            "key_topics": []
        }

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

def get_complete_topic_report(topic_name, topic_posts_data):
    """
    Generate a complete topic report with pickup line, topic summary, and subtopic breakdowns.
    
    Args:
        topic_name (str): Name of the topic (e.g., "Business", "Technology")
        topic_posts_data (dict): Complete output from get_topic_posts() with format:
            {
                "success": True,
                "data": {
                    "topic_headlines": [articles],
                    "subtopics": {
                        "Finance": {
                            "Finance": [articles],
                            "subreddits": {"personalfinance": [posts]},
                            "queries": {"stock market": [articles]}
                        }
                    }
                }
            }
    
    Returns:
        dict: Complete report with format:
            {
                "success": True,
                "pickup_line": "Engaging 3-sentence hook...",
                "topic_summary": "Comprehensive topic overview...",
                "subtopics": {
                    "Finance": {
                        "subtopic_summary": "Summary of Finance articles...",
                        "reddit_summary": "Executive brief of Finance Reddit discussions..."
                    }
                }
            }
    """
    try:
        logger.info(f"Generating complete topic report for: {topic_name}")
        
        if not topic_posts_data.get("success"):
            raise ValueError(f"Invalid topic posts data: {topic_posts_data.get('error', 'Unknown error')}")
        
        report = {
            "success": True,
            "topic_name": topic_name,
            "pickup_line": "",
            "topic_summary": "",
            "subtopics": {},
            "generation_stats": {
                "pickup_line_generated": False,
                "topic_summary_generated": False,
                "subtopics_processed": 0,
                "total_subtopics": 0
            }
        }
        
        data = topic_posts_data.get("data", {})
        subtopics_data = data.get("subtopics", {})
        report["generation_stats"]["total_subtopics"] = len(subtopics_data)
        
        # Step 1: Generate pickup line for the entire topic
        logger.info(f"Step 1: Generating pickup line for {topic_name}")
        try:
            pickup_result = get_pickup_line(topic_name, topic_posts_data)
            if pickup_result.get("success"):
                report["pickup_line"] = pickup_result["pickup_line"]
                report["generation_stats"]["pickup_line_generated"] = True
                logger.info("✅ Pickup line generated successfully")
            else:
                report["pickup_line"] = f"Discover what's trending in {topic_name} right now with breaking stories and latest developments."
                logger.warning(f"Pickup line generation failed, using fallback")
        except Exception as e:
            logger.error(f"Error generating pickup line: {e}")
            report["pickup_line"] = f"Stay updated with the latest {topic_name} news and trends."
        
        # Step 2: Generate comprehensive topic summary
        logger.info(f"Step 2: Generating topic summary for {topic_name}")
        try:
            summary_result = get_topic_summary(topic_name, topic_posts_data)
            if summary_result.get("success"):
                report["topic_summary"] = summary_result["topic_summary"]
                report["generation_stats"]["topic_summary_generated"] = True
                logger.info("✅ Topic summary generated successfully")
            else:
                report["topic_summary"] = f"# {topic_name} Summary\n\nComprehensive overview of current {topic_name} developments and trends."
                logger.warning(f"Topic summary generation failed, using fallback")
        except Exception as e:
            logger.error(f"Error generating topic summary: {e}")
            report["topic_summary"] = f"Current {topic_name} overview and key developments."
        
        # Step 3: Process each subtopic
        logger.info(f"Step 3: Processing {len(subtopics_data)} subtopics")
        
        for subtopic_name, subtopic_data in subtopics_data.items():
            logger.info(f"Processing subtopic: {subtopic_name}")
            
            subtopic_report = {
                "subtopic_summary": "",
                "reddit_summary": ""
            }
            
            # 3a: Generate subtopic summary (articles + query articles)
            try:
                # Collect all articles for this subtopic
                subtopic_articles = subtopic_data.get(subtopic_name, [])
                query_articles = []
                
                queries_data = subtopic_data.get("queries", {})
                for query, articles in queries_data.items():
                    query_articles.extend(articles)
                
                all_subtopic_articles = subtopic_articles + query_articles
                
                if all_subtopic_articles:
                    # Create a mini topic summary for just this subtopic's articles
                    subtopic_content = {
                        "success": True,
                        "data": {
                            "topic_headlines": all_subtopic_articles,
                            "subtopics": {}
                        }
                    }
                    
                    summary_result = get_topic_summary(subtopic_name, subtopic_content)
                    if summary_result.get("success"):
                        subtopic_report["subtopic_summary"] = summary_result["topic_summary"]
                        logger.info(f"✅ Generated summary for {subtopic_name} ({len(all_subtopic_articles)} articles)")
                    else:
                        subtopic_report["subtopic_summary"] = f"**{subtopic_name} Overview**\n\nKey developments and trends in {subtopic_name}."
                        logger.warning(f"Subtopic summary failed for {subtopic_name}")
                else:
                    subtopic_report["subtopic_summary"] = f"**{subtopic_name}**\n\nNo recent articles available for this subtopic."
                    logger.info(f"No articles found for {subtopic_name}")
                    
            except Exception as e:
                logger.error(f"Error generating subtopic summary for {subtopic_name}: {e}")
                subtopic_report["subtopic_summary"] = f"**{subtopic_name}**\n\nSummary unavailable."
            
            # 3b: Generate Reddit world summary for this subtopic
            try:
                # Collect all Reddit posts for this subtopic
                all_reddit_posts = []
                subreddits_data = subtopic_data.get("subreddits", {})
                
                for subreddit, posts in subreddits_data.items():
                    all_reddit_posts.extend(posts)
                
                if all_reddit_posts:
                    reddit_result = get_reddit_world_summary(all_reddit_posts)
                    if reddit_result.get("success"):
                        subtopic_report["reddit_summary"] = reddit_result["world_summary"]
                        logger.info(f"✅ Generated Reddit summary for {subtopic_name} ({len(all_reddit_posts)} posts, {reddit_result.get('relevant_posts', 0)} relevant)")
                    else:
                        subtopic_report["reddit_summary"] = f"**{subtopic_name} Community Pulse**\n\nNo significant world events detected in current discussions."
                        logger.warning(f"Reddit summary failed for {subtopic_name}")
                else:
                    subtopic_report["reddit_summary"] = f"**{subtopic_name} Community Pulse**\n\nNo recent Reddit discussions available."
                    logger.info(f"No Reddit posts found for {subtopic_name}")
                    
            except Exception as e:
                logger.error(f"Error generating Reddit summary for {subtopic_name}: {e}")
                subtopic_report["reddit_summary"] = f"**{subtopic_name} Community Pulse**\n\nCommunity insights unavailable."
            
            report["subtopics"][subtopic_name] = subtopic_report
            report["generation_stats"]["subtopics_processed"] += 1
            
            logger.info(f"✅ Completed processing {subtopic_name}")
        
        # Final statistics
        logger.info(f"Complete topic report generated for {topic_name}:")
        logger.info(f"  - Pickup line: {'✅' if report['generation_stats']['pickup_line_generated'] else '❌'}")
        logger.info(f"  - Topic summary: {'✅' if report['generation_stats']['topic_summary_generated'] else '❌'}")
        logger.info(f"  - Subtopics processed: {report['generation_stats']['subtopics_processed']}/{report['generation_stats']['total_subtopics']}")
        
        report["generation_timestamp"] = datetime.now().isoformat()
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating complete topic report for {topic_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "topic_name": topic_name,
            "pickup_line": f"Explore the latest {topic_name} developments.",
            "topic_summary": f"# {topic_name}\n\nReport generation failed. Please try again.",
            "subtopics": {}
        }

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
        country = 'us' if lang == 'en' else 'fr' if lang == 'fr' else 'us'
        
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

# Function to get SerpAPI key
def get_serpapi_key():
    """Retrieve SerpAPI key from environment or fallback to hardcoded value."""
    key = os.environ.get("SERPAPI_KEY")
    if key:
        return key
    logger.warning("SERPAPI_KEY not found in env, using fallback key")
    return "244ee6479d320cc04fe56b47958dde125b98782e9a473411d1015605bdd3072c"

def serpapi_google_news_search(query, gl="us", hl="en", max_articles=10, time_period=None, topic_token=None):
    """
    Search Google News using SerpAPI.
    
    Args:
        query (str): Search query (can be None for homepage/category browsing)
        gl (str): Country code (e.g., 'us', 'fr', 'gb')
        hl (str): Language code (e.g., 'en', 'fr', 'es')
        max_articles (int): Maximum number of articles to return
        time_period (str): Time filter ('h' for hour, 'd' for day, 'w' for week)
        topic_token (str): Topic token for specific categories/sections
    
    Returns:
        dict: API response with articles or error information
    """
    api_key = get_serpapi_key()
    
    if query:
        logger.info(f"🔍 SerpAPI Google News Search: '{query}' | {gl}/{hl} | Max: {max_articles}")
    else:
        logger.info(f"🏠 SerpAPI Google News Browse: {gl}/{hl} | Max: {max_articles} | Topic: {topic_token or 'Homepage'}")
    
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_news",
        "api_key": api_key,
        "gl": gl,
        "hl": hl
    }
    
    # Add query if provided
    if query:
        params["q"] = query
    
    # Add time period filter if provided
    if time_period:
        params["when"] = time_period
        logger.info(f"🕒 Time filter: {time_period}")
    
    # Add topic token if provided (for category browsing)
    if topic_token:
        params["topic_token"] = topic_token
        logger.info(f"🏷️ Topic token: {topic_token}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            
            # Parse articles from different possible response structures
            news_results = data.get("news_results", [])
            stories = data.get("stories", [])
            
            # Handle news_results (from search queries)
            for item in news_results[:max_articles]:
                article = _parse_serpapi_story(item)
                if article:
                    articles.append(article)
            
            # Handle stories (from homepage/category browsing)  
            if not articles and stories:
                for story_section in stories:
                    section_stories = story_section.get("stories", [])
                    for story in section_stories:
                        if len(articles) >= max_articles:
                            break
                        article = _parse_serpapi_story(story)
                        if article:
                            articles.append(article)
                    if len(articles) >= max_articles:
                        break
            
            logger.info(f"✅ SerpAPI: Found {len(articles)} articles")
            
            return {
                "success": True,
                "totalArticles": len(articles),
                "articles": articles,
                "serpapi_data": {
                    "related_topics": data.get("related_topics", []),
                    "menu_links": data.get("menu_links", []),
                    "topic_token": topic_token
                }
            }
        
        elif response.status_code == 401:
            logger.error("❌ SerpAPI: Invalid API key")
            return {
                "success": False,
                "error": "Invalid SerpAPI key"
            }
        
        elif response.status_code == 429:
            logger.error("❌ SerpAPI: Rate limit exceeded")
            return {
                "success": False,
                "error": "SerpAPI rate limit exceeded"
            }
        
        else:
            logger.error(f"❌ SerpAPI: HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except requests.RequestException as e:
        logger.error(f"❌ SerpAPI: Request failed: {e}")
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }

def _parse_serpapi_story(story):
    """Parse a SerpAPI story into our standard article format."""
    try:
        # Extract basic information
        title = story.get("title", "")
        link = story.get("link", "")
        
        # Extract source information
        source_info = story.get("source", {})
        source = {
            "name": source_info.get("name", "Unknown"),
            "url": source_info.get("icon", "")  # Using icon URL as source URL
        }
        
        # Extract date/time
        published_at = story.get("date", "")
        
        # Extract thumbnail
        thumbnail = story.get("thumbnail", "")
        
        # Create article in our standard format
        article = {
            "title": title,
            "description": "",  # SerpAPI doesn't always provide description
            "content": "",      # SerpAPI doesn't provide full content
            "url": link,
            "image": thumbnail,
            "publishedAt": published_at,
            "source": source
        }
        
        return article
        
    except Exception as e:
        logger.error(f"❌ Error parsing SerpAPI story: {e}")
        return None

def gnews_search(query, lang="en", country="us", max_articles=10, from_date=None, to_date=None, nullable=None):
    """
    Search for news articles using SerpAPI Google News API (updated from GNews).
    
    Args:
        query (str): Search keywords
        lang (str): Language code (e.g., 'en', 'fr', 'es')
        country (str): Country code (e.g., 'us', 'fr', 'gb')
        max_articles (int): Number of articles to return
        from_date (str): Not supported by SerpAPI Google News (legacy parameter)
        to_date (str): Not supported by SerpAPI Google News (legacy parameter)
        nullable (str): Not supported by SerpAPI Google News (legacy parameter)
    
    Returns:
        dict: API response with articles or error information
    """
    logger.info(f"🔍 Google News Search (SerpAPI): Query '{query}', Lang: {lang}, Country: {country}")
    
    # Convert parameters to SerpAPI format
    gl = country  # Google's gl parameter
    hl = lang     # Google's hl parameter
    
    # Determine time period based on from_date (approximate conversion)
    time_period = None
    if from_date:
        try:
            from datetime import datetime, timedelta
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            now = datetime.now(from_dt.tzinfo)
            diff = now - from_dt
            
            if diff <= timedelta(hours=1):
                time_period = "h"  # Last hour
            elif diff <= timedelta(days=1):
                time_period = "d"  # Last day
            elif diff <= timedelta(days=7):
                time_period = "w"  # Last week
            # If older than a week, don't set time_period (all time)
        except:
            logger.warning(f"⚠️ Could not parse from_date '{from_date}', using all time")
    
    # Call SerpAPI Google News
    result = serpapi_google_news_search(
        query=query,
        gl=gl,
        hl=hl,
        max_articles=max_articles,
        time_period=time_period
    )
    
    # If no articles found and we had a time filter, try without time filter as fallback
    if result.get('success') and result.get('totalArticles', 0) == 0 and time_period:
        logger.info(f"🔄 Google News Search: No articles found with time filter, trying without time filter")
        fallback_result = serpapi_google_news_search(
            query=query,
            gl=gl,
            hl=hl,
            max_articles=max_articles,
            time_period=None
        )
        
        if fallback_result.get('success') and fallback_result.get('totalArticles', 0) > 0:
            logger.info(f"✅ Google News Search: Fallback successful - found {fallback_result.get('totalArticles', 0)} articles")
            fallback_result['used_fallback'] = True
            fallback_result['original_time_period'] = time_period
            return fallback_result
    
    return result

def gnews_top_headlines(category="general", lang="en", country="us", max_articles=10, from_date=None, to_date=None, query=None, nullable=None):
    """
    Get top headlines using SerpAPI Google News API (updated from GNews).
    
    Args:
        category (str): News category (general, world, business, technology, entertainment, sports, science, health)
        lang (str): Language code (e.g., 'en', 'fr', 'es')
        country (str): Country code (e.g., 'us', 'fr', 'gb')
        max_articles (int): Number of articles to return
        from_date (str): Not supported by SerpAPI Google News (legacy parameter)
        to_date (str): Not supported by SerpAPI Google News (legacy parameter)
        query (str): Optional search query
        nullable (str): Not supported by SerpAPI Google News (legacy parameter)
    
    Returns:
        dict: API response with articles or error information
    """
    logger.info(f"🔍 Google News Top Headlines (SerpAPI): Category '{category}', Lang: {lang}, Country: {country}")
    
    # Convert parameters to SerpAPI format
    gl = country
    hl = lang
    
    # If we have a specific query, search for it
    if query:
        return gnews_search(query, lang, country, max_articles, from_date, to_date)
    
    # Map GNews categories to SerpAPI topic tokens
    # These tokens are for US English - different countries/languages may have different tokens
    category_topic_tokens = {
        "general": None,  # No topic token = general homepage
        "world": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YTJJZ0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # World
        "business": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Business
        "technology": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Technology
        "entertainment": "CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Entertainment
        "sports": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Sports
        "science": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FTb0pFZ0ptQWpYUUFRUUFQUQ",  # Science (using tech token as fallback)
        "health": "CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3Q0ZGpVU0FTb0pFZ0EQAg"  # Health
    }
    
    # Get the topic token for the requested category
    topic_token = category_topic_tokens.get(category.lower())
    
    # Determine time period based on from_date (approximate conversion)
    time_period = None
    if from_date:
        try:
            from datetime import datetime, timedelta
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            now = datetime.now(from_dt.tzinfo)
            diff = now - from_dt
            
            if diff <= timedelta(hours=1):
                time_period = "h"  # Last hour
            elif diff <= timedelta(days=1):
                time_period = "d"  # Last day
            elif diff <= timedelta(days=7):
                time_period = "w"  # Last week
        except:
            logger.warning(f"⚠️ Could not parse from_date '{from_date}', using all time")
    
    if category.lower() == "general" or topic_token is None:
        # For general news, get the homepage without a specific topic
        logger.info(f"📰 Fetching general homepage headlines")
        result = serpapi_google_news_search(
            query=None,
            gl=gl,
            hl=hl,
            max_articles=max_articles,
            time_period=time_period
        )
    else:
        # For specific categories, use the topic token
        logger.info(f"📰 Fetching {category} headlines using topic token: {topic_token}")
        result = serpapi_google_news_search(
            query=None,
            gl=gl,
            hl=hl,
            max_articles=max_articles,
            time_period=time_period,
            topic_token=topic_token
        )
    
    # Add category information to the response
    if result.get('success'):
        result['category'] = category
        result['topic_token_used'] = topic_token
    
    return result

# Legacy function for compatibility - no longer needed with SerpAPI
def sanitize_gnews_query(query):
    """
    Legacy function for GNews API query sanitization.
    SerpAPI handles query formatting automatically, so this just returns the original query.
    
    Args:
        query (str): The original search query
        
    Returns:
        str: The query (unchanged for SerpAPI)
    """
    return query

# Update the get_gnews_key function to point to SerpAPI
def get_gnews_key():
    """Legacy function that now returns SerpAPI key for backward compatibility."""
    return get_serpapi_key()

# Function to get ElevenLabs API key
def get_elevenlabs_key():
    """Retrieve ElevenLabs API key from environment or fallback to hardcoded value."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    logger.warning("ELEVENLABS_API_KEY not found in env, using fallback key")
    return "sk_332f27cd984ed4fb2eb9a18bd6eb202b45fe290873db787f"

# --- Placeholder for future endpoints ---
# TODO: Add your new endpoints here

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
        api_key = get_elevenlabs_key()
        elevenlabs = ElevenLabs(api_key=api_key)
        
        # Convert text to speech
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
        )
        
        # Convert the audio generator to bytes
        audio_bytes = b''.join(audio)
        
        # Return the audio file directly
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'audio/mpeg',
            'Content-Disposition': 'attachment; filename="speech.mp3"',
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

# TODO: Add your new endpoints here

# --- Text to Speech Helper Function ---
def generate_text_to_speech(text, voice_id="cmudN4ihcI42n48urXgc", model_id="eleven_multilingual_v2", output_format="mp3_44100_128"):
    """
    Generate speech from text using ElevenLabs API.
    
    Args:
        text (str): The text to convert to speech
        voice_id (str): ElevenLabs voice ID to use
        model_id (str): ElevenLabs model ID to use
        output_format (str): Audio output format
    
    Returns:
        bytes: Audio data as bytes, or None if error
    """
    try:
        logger.info(f"🔊 Converting text to speech: '{text[:100]}...' using voice {voice_id}")
        logger.info(f"📝 Text length: {len(text)} characters")
        logger.info(f"🎤 Voice ID: {voice_id}, Model: {model_id}, Format: {output_format}")
        
        # Initialize ElevenLabs client
        logger.info("🔑 Getting ElevenLabs API key...")
        api_key = get_elevenlabs_key()
        if not api_key:
            logger.error("❌ ElevenLabs API key is None or empty!")
            return None
        
        logger.info(f"🔑 ElevenLabs API key found: {api_key[:10]}...")
        
        logger.info("🚀 Initializing ElevenLabs client...")
        from elevenlabs import ElevenLabs
        elevenlabs = ElevenLabs(api_key=api_key)
        logger.info("✅ ElevenLabs client initialized successfully")
        
        # Convert text to speech
        logger.info("🎙️ Starting text-to-speech conversion...")
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
        )
        logger.info("✅ Text-to-speech conversion started, processing audio stream...")
        
        # Convert the audio generator to bytes
        logger.info("📦 Converting audio stream to bytes...")
        audio_bytes = b''.join(audio)
        
        logger.info(f"✅ Successfully generated {len(audio_bytes)} bytes of audio")
        return audio_bytes
        
    except ImportError as e:
        logger.error(f"❌ Import error - ElevenLabs library not found: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error generating text-to-speech: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Error details: {str(e)}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return None

# --- Text to Speech Endpoint using ElevenLabs ---

# --- Media Twin Script Generation ---
def generate_media_twin_script(topic_name, topic_posts_data, presenter_name="Alex", language="fr"):
    """
    Génère un script conversationnel pour un media twin (jumeau média) qui présente l'actualité.
    
    Args:
        topic_name (str): Nom du sujet (e.g., "Business", "Technology")
        topic_posts_data (dict): Données complètes des articles (même format que get_complete_topic_report)
        presenter_name (str): Nom du présentateur virtuel
        language (str): Langue du script ("fr", "en", "es", "ar")
    
    Returns:
        dict: Script généré avec segments et métadonnées
    """
    try:
        logger.info(f"Generating media twin script for {topic_name} in {language}")
        
        if not topic_posts_data.get("success"):
            raise ValueError(f"Invalid topic posts data: {topic_posts_data.get('error', 'Unknown error')}")
        
        # Templates par langue
        language_templates = {
            'fr': {
                'greeting': [
                    f"Salut ! C'est {presenter_name}, et je suis là pour te tenir au courant de tout ce qui bouge",
                    f"Hello ! {presenter_name} ici, et j'ai du lourd à te partager aujourd'hui",
                    f"Hey ! C'est {presenter_name}, prêt(e) pour ta dose d'actu ?"
                ],
                'transition_to_topic': [
                    f"Alors, parlons de {topic_name.lower()}.",
                    f"Aujourd'hui, on va plonger dans {topic_name.lower()}.",
                    f"Concentrons-nous sur {topic_name.lower()}."
                ],
                'subtopic_intro': [
                    "Passons maintenant à",
                    "On va maintenant regarder",
                    "Intéressons-nous à"
                ],
                'conclusion': [
                    "Voilà pour cette mise à jour ! J'espère que ça t'a aidé à y voir plus clair.",
                    "Et c'est tout pour aujourd'hui ! On se retrouve bientôt pour de nouvelles actus.",
                    "Ça, c'était ta dose d'info du jour ! À très vite pour la suite."
                ]
            },
            'en': {
                'greeting': [
                    f"Hey there! It's {presenter_name}, and I'm here to keep you updated on everything that's happening",
                    f"Hello! {presenter_name} here, and I've got some serious updates to share with you today",
                    f"What's up! It's {presenter_name}, ready for your news dose?"
                ],
                'transition_to_topic': [
                    f"So, let's talk about {topic_name.lower()}.",
                    f"Today, we're diving into {topic_name.lower()}.",
                    f"Let's focus on {topic_name.lower()}."
                ],
                'subtopic_intro': [
                    "Now let's move on to",
                    "Let's now look at", 
                    "Let's focus on"
                ],
                'conclusion': [
                    "That's it for this update! Hope it helped you stay in the loop.",
                    "And that's all for today! See you soon for more news.",
                    "That was your daily info dose! Catch you later for more updates."
                ]
            }
        }
        
        templates = language_templates.get(language, language_templates['fr'])
        
        # Obtenir le rapport complet
        complete_report = get_complete_topic_report(topic_name, topic_posts_data)
        if not complete_report.get("success"):
            raise ValueError("Failed to generate complete report")
        
        data = topic_posts_data.get("data", {})
        subtopics_data = data.get("subtopics", {})
        
        # Compter le nombre total d'articles et posts
        total_articles = len(data.get("topic_headlines", []))
        total_reddit_posts = 0
        for subtopic_data in subtopics_data.values():
            for subreddit_posts in subtopic_data.get("subreddits", {}).values():
                total_reddit_posts += len(subreddit_posts)
        
        segments = []
        
        # SEGMENT 1: Introduction accrocheuse
        import random
        greeting = random.choice(templates['greeting'])
        pickup_line = complete_report.get("pickup_line", f"On a du mouvement dans {topic_name.lower()} aujourd'hui.")
        
        intro_content = f"{greeting} ! {pickup_line}"
        
        if total_articles > 0:
            if language == 'fr':
                intro_content += f" J'ai analysé {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" et {total_reddit_posts} discussions Reddit"
                intro_content += f" pour te donner le meilleur résumé possible."
            else:
                intro_content += f" I've analyzed {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" and {total_reddit_posts} Reddit discussions"
                intro_content += f" to give you the best summary possible."
        
        segments.append({
            "type": "intro",
            "content": intro_content,
            "duration_estimate": "30s"
        })
        
        # SEGMENT 2: Vue d'ensemble du sujet
        transition = random.choice(templates['transition_to_topic'])
        topic_summary = complete_report.get("topic_summary", "")
        
        # Convertir le summary en script conversationnel
        main_content = f"{transition} "
        
        # Extraire les points clés du summary et les rendre conversationnels
        if topic_summary:
            # Simplifier le markdown et rendre plus conversationnel
            cleaned_summary = topic_summary.replace("**", "").replace("*", "").replace("#", "")
            
            # Diviser en phrases et rendre plus naturel
            sentences = [s.strip() for s in cleaned_summary.split('.') if s.strip()]
            conversational_points = []
            
            for sentence in sentences[:5]:  # Limite à 5 points principaux
                if len(sentence) > 20:  # Éviter les fragments trop courts
                    # Rendre plus conversationnel
                    if language == 'fr':
                        if "Le" in sentence or "La" in sentence:
                            sentence = sentence.replace("Le ", "").replace("La ", "")
                        if not sentence.startswith(("Alors", "Donc", "En fait", "Bref")):
                            sentence = f"En fait, {sentence.lower()}"
                    conversational_points.append(sentence)
            
            main_content += " ".join(conversational_points[:3])  # 3 points principaux max
        
        segments.append({
            "type": "main_topic", 
            "content": main_content,
            "duration_estimate": "1-2min"
        })
        
        # SEGMENT 3: Détails par sous-sujets
        for i, (subtopic_name, subtopic_report) in enumerate(complete_report.get("subtopics", {}).items()):
            subtopic_intro = random.choice(templates['subtopic_intro'])
            
            subtopic_content = f"{subtopic_intro} {subtopic_name.lower()}. "
            
            # Résumer le contenu du sous-sujet de manière conversationnelle
            subtopic_summary = subtopic_report.get("subtopic_summary", "")
            reddit_summary = subtopic_report.get("reddit_summary", "")
            
            if subtopic_summary:
                # Extraire 2-3 points clés
                cleaned = subtopic_summary.replace("**", "").replace("*", "").replace("#", "")
                key_points = [s.strip() for s in cleaned.split('.') if s.strip() and len(s) > 20][:2]
                
                for point in key_points:
                    if language == 'fr':
                        subtopic_content += f" {point}."
                    else:
                        subtopic_content += f" {point}."
            
            # Ajouter l'insight Reddit si pertinent
            if reddit_summary and "No significant" not in reddit_summary and "unavailable" not in reddit_summary:
                if language == 'fr':
                    subtopic_content += f" Côté communauté, on voit que les gens parlent beaucoup de ça sur Reddit."
                else:
                    subtopic_content += f" On the community side, people are really talking about this on Reddit."
            
            segments.append({
                "type": "subtopic",
                "subtopic_name": subtopic_name,
                "content": subtopic_content,
                "duration_estimate": "1min"
            })
        
        # SEGMENT 4: Conclusion
        conclusion = random.choice(templates['conclusion'])
        if language == 'fr':
            conclusion += f" Si tu veux creuser plus, n'hésite pas à checker les sources. Bisous !"
        else:
            conclusion += f" If you want to dive deeper, feel free to check the sources. Take care!"
        
        segments.append({
            "type": "conclusion",
            "content": conclusion,
            "duration_estimate": "20s"
        })
        
        # Assembler le script complet
        full_script = "\n\n".join([segment["content"] for segment in segments])
        
        # Calculs des métadonnées
        word_count = len(full_script.split())
        estimated_duration = f"{max(6, word_count // 150)}-{word_count // 120} minutes"
        
        result = {
            "success": True,
            "script": full_script,
            "segments": segments,
            "metadata": {
                "topic_name": topic_name,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "total_duration_estimate": estimated_duration,
                "articles_analyzed": total_articles,
                "reddit_posts_analyzed": total_reddit_posts,
                "subtopics_covered": len(complete_report.get("subtopics", {}))
            },
            "generation_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Media twin script generated: {word_count} words, {len(segments)} segments")
        return result
        
    except Exception as e:
        logger.error(f"Error generating media twin script for {topic_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "script": f"Désolé, il y a eu un problème pour générer le script pour {topic_name}. On va réessayer plus tard !",
            "segments": [],
            "metadata": {}
        }

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

def generate_user_media_twin_script(user_id, presenter_name="Alex", language="fr"):
    """
    Génère un script conversationnel pour un media twin basé sur tous les articles d'un utilisateur.
    Utilise get_complete_report pour récupérer tous les sujets et articles de l'utilisateur.
    
    Args:
        user_id (str): ID de l'utilisateur
        presenter_name (str): Nom du présentateur virtuel
        language (str): Langue du script ("fr", "en", "es", "ar")
    
    Returns:
        dict: Script généré avec segments et métadonnées
    """
    try:
        logger.info(f"Generating user media twin script for user {user_id} in {language}")
        
        # Étape 1: Récupérer le rapport complet de l'utilisateur
        complete_report = get_complete_report(user_id)
        
        if not complete_report.get("success"):
            raise ValueError(f"Failed to get complete report for user {user_id}: {complete_report.get('error', 'Unknown error')}")
        
        reports = complete_report.get("reports", {})
        if not reports:
            raise ValueError(f"No reports found for user {user_id}")
        
        # Templates par langue
        language_templates = {
            'fr': {
                'greeting': [
                    f"Salut ! C'est {presenter_name}, et j'ai préparé ton briefing personnalisé",
                    f"Hello ! {presenter_name} ici avec ta dose d'actu sur mesure",
                    f"Hey ! C'est {presenter_name}, prêt(e) pour ton résumé perso ?"
                ],
                'transition_global': [
                    "Alors, qu'est-ce qui se passe dans tes sujets favoris ?",
                    "Voyons ce qui bouge dans tes domaines d'intérêt.",
                    "Plongeons dans l'actu qui t'intéresse vraiment."
                ],
                'topic_transition': [
                    "Maintenant, côté",
                    "Passons à",
                    "On va voir ce qui se passe en"
                ],
                'subtopic_intro': [
                    "Plus spécifiquement sur",
                    "En détail sur",
                    "Zoom sur"
                ],
                'global_conclusion': [
                    "Et voilà pour ton briefing perso ! J'espère que ça t'aide à rester dans le game.",
                    "C'était ton résumé sur mesure ! À très bientôt pour la suite.",
                    "Ça, c'était ton actu personnalisée ! On se retrouve soon pour plus d'infos."
                ]
            },
            'en': {
                'greeting': [
                    f"Hey there! It's {presenter_name}, and I've prepared your personalized briefing",
                    f"Hello! {presenter_name} here with your custom news dose",
                    f"What's up! It's {presenter_name}, ready for your personal update?"
                ],
                'transition_global': [
                    "So, what's happening in your favorite topics?",
                    "Let's see what's moving in your areas of interest.",
                    "Let's dive into the news that really matters to you."
                ],
                'topic_transition': [
                    "Now, on the",
                    "Moving to",
                    "Let's see what's happening in"
                ],
                'subtopic_intro': [
                    "More specifically on",
                    "In detail about",
                    "Zooming in on"
                ],
                'global_conclusion': [
                    "And that's your personal briefing! Hope it helps you stay in the loop.",
                    "That was your custom summary! See you soon for more updates.",
                    "That was your personalized news! Catch you later for more insights."
                ]
            }
        }
        
        templates = language_templates.get(language, language_templates['fr'])
        
        # Compter les statistiques globales
        total_topics = len(reports)
        total_successful = complete_report.get("generation_stats", {}).get("successful_reports", 0)
        
        # Compter articles et posts Reddit
        total_articles = 0
        total_reddit_posts = 0
        
        for topic_name, topic_report in reports.items():
            subtopics = topic_report.get("subtopics", {})
            for subtopic_name, subtopic_data in subtopics.items():
                # Estimer le nombre d'articles basé sur le contenu
                summary = subtopic_data.get("subtopic_summary", "")
                reddit_summary = subtopic_data.get("reddit_summary", "")
                if summary and len(summary) > 100:
                    total_articles += 5  # Estimation moyenne
                if reddit_summary and "No significant" not in reddit_summary:
                    total_reddit_posts += 8  # Estimation moyenne
        
        segments = []
        
        # SEGMENT 1: Introduction personnalisée
        import random
        greeting = random.choice(templates['greeting'])
        
        intro_content = f"{greeting} !"
        
        if total_successful > 0:
            if language == 'fr':
                intro_content += f" J'ai analysé {total_successful} de tes sujets favoris"
                if total_articles > 0:
                    intro_content += f", en parcourant environ {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" et {total_reddit_posts} discussions Reddit"
                intro_content += " pour te donner le meilleur résumé personnalisé."
            else:
                intro_content += f" I've analyzed {total_successful} of your favorite topics"
                if total_articles > 0:
                    intro_content += f", going through about {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" and {total_reddit_posts} Reddit discussions"
                intro_content += " to give you the best personalized summary."
        
        segments.append({
            "type": "intro",
            "content": intro_content,
            "duration_estimate": "30s"
        })
        
        # SEGMENT 2: Transition globale
        transition = random.choice(templates['transition_global'])
        segments.append({
            "type": "global_transition",
            "content": transition,
            "duration_estimate": "10s"
        })
        
        # SEGMENT 3: Traiter chaque sujet
        for topic_name, topic_report in reports.items():
            if not topic_report.get("topic_summary"):
                continue
                
            topic_transition = random.choice(templates['topic_transition'])
            
            # Utiliser la pickup line comme accroche
            pickup_line = topic_report.get("pickup_line", "")
            topic_summary = topic_report.get("topic_summary", "")
            
            topic_content = f"{topic_transition} {topic_name.lower()}. "
            
            if pickup_line:
                # Rendre la pickup line conversationnelle
                if language == 'fr':
                    topic_content += f"{pickup_line} "
                else:
                    topic_content += f"{pickup_line} "
            
            # Extraire les points clés du résumé
            if topic_summary:
                cleaned_summary = topic_summary.replace("**", "").replace("*", "").replace("#", "")
                sentences = [s.strip() for s in cleaned_summary.split('.') if s.strip()]
                
                # Prendre 2-3 points clés
                key_points = []
                for sentence in sentences[:4]:
                    if len(sentence) > 30:  # Éviter les fragments
                        if language == 'fr':
                            if not sentence.startswith(("En fait", "Donc", "Bref")):
                                sentence = f"En gros, {sentence.lower()}"
                        key_points.append(sentence)
                
                if key_points:
                    topic_content += " ".join(key_points[:2])  # Max 2 points par sujet
            
            segments.append({
                "type": "topic",
                "topic_name": topic_name,
                "content": topic_content,
                "duration_estimate": "1-2min"
            })
            
            # SEGMENT 4: Sous-sujets détaillés
            subtopics = topic_report.get("subtopics", {})
            if subtopics:
                for subtopic_name, subtopic_data in list(subtopics.items())[:2]:  # Max 2 sous-sujets par topic
                    subtopic_intro = random.choice(templates['subtopic_intro'])
                    
                    subtopic_content = f"{subtopic_intro} {subtopic_name.lower()}. "
                    
                    subtopic_summary = subtopic_data.get("subtopic_summary", "")
                    reddit_summary = subtopic_data.get("reddit_summary", "")
                    
                    if subtopic_summary:
                        # Extraire 1-2 points clés
                        cleaned = subtopic_summary.replace("**", "").replace("*", "").replace("#", "")
                        key_points = [s.strip() for s in cleaned.split('.') if s.strip() and len(s) > 20][:1]
                        
                        if key_points:
                            subtopic_content += f"{key_points[0]}. "
                    
                    # Ajouter insight Reddit si pertinent
                    if reddit_summary and "No significant" not in reddit_summary and "unavailable" not in reddit_summary:
                        if language == 'fr':
                            subtopic_content += "La communauté en parle beaucoup actuellement."
                        else:
                            subtopic_content += "The community is really talking about this right now."
                    
                    segments.append({
                        "type": "subtopic",
                        "topic_name": topic_name,
                        "subtopic_name": subtopic_name,
                        "content": subtopic_content,
                        "duration_estimate": "45s"
                    })
        
        # SEGMENT FINAL: Conclusion globale
        conclusion = random.choice(templates['global_conclusion'])
        if language == 'fr':
            conclusion += " Reste connecté(e) pour ne rien rater ! Bisous !"
        else:
            conclusion += " Stay tuned for more updates! Take care!"
        
        segments.append({
            "type": "global_conclusion",
            "content": conclusion,
            "duration_estimate": "20s"
        })
        
        # Assembler le script complet
        full_script = "\n\n".join([segment["content"] for segment in segments])
        
        # Calculs des métadonnées
        word_count = len(full_script.split())
        estimated_duration = f"{max(8, word_count // 150)}-{word_count // 120} minutes"
        
        result = {
            "success": True,
            "script": full_script,
            "segments": segments,
            "metadata": {
                "user_id": user_id,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "total_duration_estimate": estimated_duration,
                "topics_covered": total_successful,
                "total_topics": total_topics,
                "estimated_articles": total_articles,
                "estimated_reddit_posts": total_reddit_posts,
                "report_generation_stats": complete_report.get("generation_stats", {})
            },
            "generation_timestamp": datetime.now().isoformat(),
            "based_on_report": {
                "refresh_timestamp": complete_report.get("refresh_timestamp"),
                "language": complete_report.get("language")
            }
        }
        
        logger.info(f"✅ User media twin script generated: {word_count} words, {len(segments)} segments for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating user media twin script for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "script": f"Désolé, il y a eu un problème pour générer ton briefing personnalisé. On va réessayer plus tard !",
            "segments": [],
            "metadata": {"user_id": user_id}
        }

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

def get_reddit_community_insights(subtopic_data):
    """Extract key insights from Reddit discussions."""
    subreddits = subtopic_data.get("subreddits", {})
    insights = []
    
    for subreddit_name, posts in subreddits.items():
        if posts:
            # Get top post
            top_post = max(posts, key=lambda x: x.get("score", 0))
            title = top_post.get("title", "")
            score = top_post.get("score", 0)
            
            if score > 20:  # Only significant discussions
                insights.append(f"La communauté r/{subreddit_name} discute activement de \"{title[:50]}...\" ({score} points)")
    
    return insights

def generate_complete_user_media_twin_script(user_id, presenter_name="Alex", language="fr"):
    """
    Generate complete media twin script using all real user articles with AI analysis.
    This version uses OpenAI to create intelligent, personalized content based on actual articles.
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter
        language (str): Language for the script ('fr' or 'en')
    
    Returns:
        dict: Complete script with AI-generated content
    """
    try:
        logger.info(f"🎤 Generating complete AI media twin script for user {user_id}")
        
        # Get user articles from database
        articles_data = get_user_articles_from_db(user_id)
        
        if not articles_data:
            raise Exception("No articles found for user")
        
        topics = articles_data.get("topics_data", {})
        
        if not topics:
            raise Exception("No topics found for user")
        
        logger.info(f"Processing {len(topics)} topics for AI script generation")
        
        # Count articles for script planning
        total_topics = len(topics)
        segment_duration = max(60, 240 // total_topics)  # Between 60s and 4min per segment
        
        # Start building the script
        if language == "fr":
            script = f"""🎙️ SCRIPT MÉDIA TWIN - {presenter_name.upper()}
====================================================

🎬 INTRO (30 secondes)
Salut et bienvenue dans votre briefing quotidien personnalisé ! Je suis {presenter_name}, et aujourd'hui on a un programme passionnant avec {total_topics} sujets choisis spécialement pour vous. Des startups européennes à l'intelligence artificielle, on va faire le tour de ce qui compte vraiment. C'est parti !

"""
        else:
            script = f"""🎙️ MEDIA TWIN SCRIPT - {presenter_name.upper()}
====================================================

🎬 INTRO (30 seconds)
Hello and welcome to your personalized daily briefing! I'm {presenter_name}, and today we have an exciting program with {total_topics} topics chosen especially for you. From European startups to artificial intelligence, we're going to cover what really matters. Let's go!

"""
        
        # Process each topic
        for i, (topic_name, topic_data) in enumerate(topics.items(), 1):
            logger.info(f"Processing topic {i}/{total_topics}: {topic_name}")
            
            script += f"""
🎬 SEGMENT {i}: {topic_name.upper()} ({segment_duration}s)
{'-' * 60}

"""
            
            # Generate AI pickup line
            pickup_result = get_pickup_line(topic_name, topic_data)
            if pickup_result.get("success"):
                script += f"""🎯 ACCROCHE: 
{pickup_result['pickup_line']}

"""
            
            # Generate AI topic summary
            summary_result = get_topic_summary(topic_name, topic_data)
            if summary_result.get("success"):
                if language == "fr":
                    script += f"""📰 LE BRIEFING:
{summary_result['topic_summary']}

"""
                else:
                    script += f"""📰 THE BRIEFING:
{summary_result['topic_summary']}

"""
            
            # Add subtopics breakdown
            subtopics = topic_data.get("data", {}).get("subtopics", {})
            if subtopics:
                if language == "fr":
                    script += "🔍 LES POINTS CLÉS:\n"
                else:
                    script += "🔍 KEY POINTS:\n"
                    
                for subtopic_name, subtopic_data in subtopics.items():
                    # Count articles in this subtopic
                    subtopic_articles = len(subtopic_data.get(subtopic_name, []))
                    query_articles = sum(len(articles) for articles in subtopic_data.get("queries", {}).values())
                    reddit_posts = sum(len(posts) for posts in subtopic_data.get("subreddits", {}).values())
                    
                    if language == "fr":
                        script += f"• {subtopic_name}: {subtopic_articles + query_articles} articles, {reddit_posts} discussions communautaires\n"
                    else:
                        script += f"• {subtopic_name}: {subtopic_articles + query_articles} articles, {reddit_posts} community discussions\n"
                    
                    # Add community insights
                    insights = get_reddit_community_insights(subtopic_data)
                    for insight in insights[:1]:  # Max 1 insight per subtopic
                        script += f"  💬 {insight}\n"
                
                script += "\n"
            
            # Add transition
            if i < total_topics:
                if language == "fr":
                    script += "🔄 Maintenant, passons à notre prochain sujet...\n"
                else:
                    script += "🔄 Now, let's move on to our next topic...\n"
        
        # Conclusion
        if language == "fr":
            script += f"""
🎬 CONCLUSION (25 secondes)
====================================================
Et voilà ! C'était votre briefing personnalisé couvrant {total_topics} sujets d'actualité. De l'innovation européenne aux avancées en IA, vous êtes maintenant à jour sur ce qui compte pour vous. Merci de m'avoir écouté, et à très bientôt pour de nouvelles actus !

📊 INFORMATIONS DU BRIEFING:
• Durée totale estimée: {50 + (segment_duration * total_topics)} secondes
• Articles analysés: {articles_data.get('summary', {}).get('total_articles', 'N/A')}
• Discussions Reddit: {articles_data.get('summary', {}).get('total_posts', 'N/A')}
• Dernière mise à jour: {articles_data.get('refresh_timestamp', 'N/A')[:10]}
• Présentateur: {presenter_name}
• Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}
"""
        else:
            script += f"""
🎬 CONCLUSION (25 seconds)
====================================================
And that's a wrap! That was your personalized briefing covering {total_topics} news topics. From European innovation to AI advances, you're now up to date on what matters to you. Thanks for listening, and see you soon for more news!

📊 BRIEFING INFORMATION:
• Total estimated duration: {50 + (segment_duration * total_topics)} seconds
• Articles analyzed: {articles_data.get('summary', {}).get('total_articles', 'N/A')}
• Reddit discussions: {articles_data.get('summary', {}).get('total_posts', 'N/A')}
• Last updated: {articles_data.get('refresh_timestamp', 'N/A')[:10]}
• Presenter: {presenter_name}
• Generated on: {datetime.now().strftime('%m/%d/%Y at %H:%M')}
"""

        # Calculate metadata
        word_count = len(script.split())
        estimated_duration_minutes = max(4, word_count // 150)
        
        result = {
            "success": True,
            "script": script.strip(),
            "metadata": {
                "user_id": user_id,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "total_duration_estimate": f"{estimated_duration_minutes} minutes",
                "topics_covered": len(topics),
                "articles_analyzed": articles_data.get('summary', {}).get('total_articles', 0),
                "reddit_discussions": articles_data.get('summary', {}).get('total_posts', 0),
                "ai_generated": True,
                "script_type": "complete_ai_media_twin"
            },
            "generation_timestamp": datetime.now().isoformat(),
            "refresh_timestamp": articles_data.get("refresh_timestamp")
        }
        
        logger.info(f"✅ Complete AI media twin script generated: {word_count} words for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating complete AI media twin script for user {user_id}: {e}")
        if language == "fr":
            fallback_script = f"Désolé, il y a eu un problème pour générer votre briefing personnalisé. On va réessayer plus tard ! (Erreur: {str(e)})"
        else:
            fallback_script = f"Sorry, there was an issue generating your personalized briefing. We'll try again later! (Error: {str(e)})"
            
        return {
            "success": False,
            "error": str(e),
            "script": fallback_script,
            "metadata": {"user_id": user_id, "error": True}
        }

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
def generate_simple_podcast_script(user_id, presenter_name="Alex", language="en"):
    """
    Generate a simple conversational podcast script based on user articles.
    Uses a straightforward approach with OpenAI to create natural, friendly commentary.
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter/host
        language (str): Language for the script ('en' or 'fr')
    
    Returns:
        dict: Simple script with success status
    """
    try:
        logger.info(f"🎙️ Generating simple podcast script for user {user_id}")
        
        # Get user articles from database
        articles_data = get_user_articles_from_db(user_id)
        
        if not articles_data:
            raise Exception("No articles found for user")
        
        topics_data = articles_data.get("topics_data", {})
        
        if not topics_data:
            raise Exception("No topics found for user")
        
        # Create the podcast generation prompt
        if language == "fr":
            system_prompt = """Tu es un animateur de podcast amical qui crée un script conversationnel pour un briefing d'actualités. Ton ton doit être décontracté, engageant et informatif - comme si tu racontais des nouvelles intéressantes à un ami.

Génère un script de podcast de 4-6 minutes basé sur TOUS les articles fournis, organisés par sujets et sous-sujets.

IMPORTANT: Écris UNIQUEMENT le texte à lire à voix haute - AUCUNE indication de mise en scène comme [intro], [outro], [pause], etc. Le script doit être du texte pur, fluide et lisible directement.

Directives de style:
- Conversationnel et naturel (comme si tu parlais à un ami)
- Utilise des transitions comme "En parlant de...", "Oh, et voici quelque chose d'intéressant...", "Tu sais ce qui m'a frappé?"
- Inclus des réactions personnelles ("C'est assez fou...", "J'ai trouvé ça fascinant...")
- Reste engageant mais informatif
- Utilise les noms des sources pour ajouter de la crédibilité
- Commence directement par un accueil naturel, termine par une conclusion naturelle
- Pas de marqueurs de temps ou d'instructions techniques

Flux naturel:
- Commence par un accueil chaleureux et un aperçu des sujets
- Enchaîne naturellement d'un sujet à l'autre avec des transitions fluides
- Termine par une conclusion naturelle et engageante

IMPORTANT: Couvre chaque article fourni - n'en laisse aucun de côté. Mentionne chaque titre d'article. Écris SEULEMENT ce qui doit être dit à voix haute."""

        else:
            system_prompt = """You are a friendly podcast host creating a conversational news briefing script. Your tone should be casual, engaging, and informative - like telling a friend about interesting news you've discovered.

Generate a 4-6 minute podcast script based on ALL the provided articles, organized by topics and subtopics.

IMPORTANT: Write ONLY the text to be read aloud - NO stage directions like [intro], [outro], [pause], etc. The script should be pure text, flowing and readable directly.

Style Guidelines:
- Conversational and natural (as if talking to a friend)
- Use transitions like "Speaking of...", "Oh, and here's something interesting...", "You know what caught my eye?"
- Include personal reactions/commentary ("This is pretty wild...", "I found this fascinating...")
- Keep it engaging but informative
- Use source names to add credibility
- Start with a natural welcome, end with a natural conclusion
- No timestamps or technical instructions

Natural flow:
- Start with a warm welcome and overview of topics
- Naturally transition from one topic to another with smooth transitions
- End with a natural and engaging conclusion

IMPORTANT: Cover every single article provided - don't leave any out. Mention every article title. Write ONLY what needs to be spoken aloud."""

        # Format the articles data as a clean JSON string
        user_message = f"Here's the news data to create a podcast script for:\n\n{json.dumps(topics_data, indent=2)}"
        
        # Use OpenAI to generate the script
        client = get_openai_client()
        if not client:
            raise Exception("OpenAI client not available")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Generate the podcast script with more tokens for a complete script
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2000,  # Enough for a 4-6 minute script
            temperature=0.7
        )
        
        script_content = response.choices[0].message.content
        
        # Clean up any remaining stage directions from the script
        import re
        # Remove stage directions like [intro], [outro], [pause], etc.
        script_content = re.sub(r'\[.*?\]', '', script_content)
        # Remove timestamp markers like (00:30), (2:15), etc.
        script_content = re.sub(r'\(\d+:\d+\)', '', script_content)
        # Remove excessive line breaks and clean up whitespace
        script_content = re.sub(r'\n\s*\n\s*\n', '\n\n', script_content)
        script_content = script_content.strip()
        
        logger.info(f"✅ Script cleaned and ready: {len(script_content)} characters")
        
        # Calculate metadata
        word_count = len(script_content.split())
        estimated_duration_minutes = max(4, word_count // 150)
        
        # Save script to Firebase Storage
        storage_url = None
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"podcast_scripts/{user_id}/script_{timestamp}.txt"
            
            # Get Firebase Storage bucket
            bucket = storage.bucket()
            blob = bucket.blob(filename)
            
            # Upload script content
            blob.upload_from_string(
                script_content, 
                content_type='text/plain; charset=utf-8'
            )
            
            # Make the file publicly readable (optional)
            blob.make_public()
            storage_url = blob.public_url
            
            logger.info(f"📁 Script saved to storage: {filename}")
            
        except Exception as storage_error:
            logger.error(f"Error saving script to storage: {storage_error}")
            # Continue execution even if storage fails
        
        # Save audio connection info to database
        db_storage_success = False
        try:
            db_client = firestore.client()
            
            audio_connection_data = {
                "user_id": user_id,
                "script_content": script_content,
                "storage_url": storage_url,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "estimated_duration": f"{estimated_duration_minutes} minutes",
                "topics_covered": len(topics_data),
                "articles_analyzed": articles_data.get('summary', {}).get('total_articles', 0),
                "script_type": "simple_conversational_podcast",
                "model_used": "gpt-4o",
                "created_at": datetime.now().isoformat(),
                "refresh_timestamp": articles_data.get("refresh_timestamp"),
                "status": "script_generated"  # Can be updated later when audio is generated
            }
            
            # Store in audio_connections collection
            doc_ref = db_client.collection('audio_connections').document()
            doc_ref.set(audio_connection_data)
            
            # Also update user's latest script reference
            user_audio_ref = db_client.collection('user_audio_connections').document(user_id)
            user_audio_ref.set({
                "latest_script_id": doc_ref.id,
                "latest_script_created": datetime.now().isoformat(),
                "storage_url": storage_url
            }, merge=True)
            
            db_storage_success = True
            logger.info(f"📀 Audio connection saved to database: {doc_ref.id}")
            
        except Exception as db_error:
            logger.error(f"Error saving audio connection to database: {db_error}")
        
        result = {
                "success": True,
                "script": script_content,
                "storage_url": storage_url,
                "db_saved": db_storage_success,
                "metadata": {
                    "user_id": user_id,
                    "presenter_name": presenter_name,
                    "language": language,
                    "word_count": word_count,
                    "estimated_duration": f"{estimated_duration_minutes} minutes",
                    "topics_covered": len(topics_data),
                    "articles_analyzed": articles_data.get('summary', {}).get('total_articles', 0),
                    "script_type": "simple_conversational_podcast",
                    "model_used": "gpt-4o"
                },
                "generation_timestamp": datetime.now().isoformat(),
                "refresh_timestamp": articles_data.get("refresh_timestamp")
        }
        return result  # ← ADD THIS RETURN STATEMENT
        
    except Exception as e:  # ← ADD THIS MAIN EXCEPT BLOCK
        logger.error(f"Error generating simple podcast script for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate podcast script",
            "metadata": {"user_id": user_id, "error": True}
        }
    
def generate_simple_podcast(user_id, presenter_name="Alex", language="en", voice_id="cmudN4ihcI42n48urXgc"):
    """
    Generate complete podcast: script + audio using ElevenLabs, with full storage and database saving.
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter/host
        language (str): Language for the script ('en' or 'fr')
        voice_id (str): ElevenLabs voice ID for audio generation
    
    Returns:
        dict: Complete result with script, audio URL, and storage info
    """
    try:
        logger.info(f"🎙️ Generating complete podcast (script + audio) for user {user_id}")
        
        # Step 1: Generate the script using existing function
        logger.info(f"📝 Step 1/3: Generating script for user {user_id}")
        script_result = generate_simple_podcast_script(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language
        )
        
        if not script_result.get("success"):
            raise Exception(f"Script generation failed: {script_result.get('error')}")
        
        script_content = script_result.get("script")
        script_storage_url = script_result.get("storage_url")
        
        logger.info(f"✅ Script generated: {len(script_content)} characters")
        
        # Step 2: Generate audio using ElevenLabs
        logger.info(f"🔊 Step 2/3: Converting script to audio with ElevenLabs...")
        logger.info(f"📊 About to convert {len(script_content)} characters to audio")
        
        audio_bytes = generate_text_to_speech(
            text=script_content,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        logger.info(f"🔍 Audio generation result: audio_bytes is {'None' if audio_bytes is None else f'{len(audio_bytes)} bytes'}")
        
        if not audio_bytes:
            logger.error("❌ Audio generation failed - audio_bytes is None or empty")
            raise Exception("Audio generation failed")
        
        logger.info(f"✅ Audio generated: {len(audio_bytes)} bytes")
        
        # Step 3: Save audio to Firebase Storage
        logger.info(f"💾 Step 3/3: Saving audio to Firebase Storage...")
        audio_storage_url = None
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"podcast_audio/{user_id}/podcast_{timestamp}.mp3"
            
            # Get Firebase Storage bucket
            bucket = storage.bucket()
            audio_blob = bucket.blob(audio_filename)
            
            # Upload audio content
            audio_blob.upload_from_string(
                audio_bytes,
                content_type='audio/mpeg'
            )
            
            # Make the file publicly readable
            audio_blob.make_public()
            audio_storage_url = audio_blob.public_url
            
            logger.info(f"📁 Audio saved to storage: {audio_filename}")
            
        except Exception as storage_error:
            logger.error(f"Error saving audio to storage: {storage_error}")
            raise Exception(f"Audio storage failed: {storage_error}")
        
        # Step 4: Update database with complete podcast info
        try:
            db_client = firestore.client()
            
            # Update the existing audio_connections document with audio info
            # Find the latest script document for this user
            audio_connections_ref = db_client.collection('audio_connections')
            query = audio_connections_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).limit(1)
            docs = query.stream()
            
            latest_doc = None
            for doc in docs:
                latest_doc = doc
                break
            
            if latest_doc:
                # Update existing document with audio info
                latest_doc.reference.update({
                    'audio_url': audio_storage_url,
                    'audio_filename': audio_filename,
                    'audio_generated_at': datetime.now().isoformat(),
                    'status': 'complete_podcast_generated',
                    'voice_id': voice_id
                })
                doc_id = latest_doc.id
            else:
                # Create new document if none exists
                complete_podcast_data = {
                    "user_id": user_id,
                    "script_content": script_content,
                    "script_storage_url": script_storage_url,
                    "audio_url": audio_storage_url,
                    "audio_filename": audio_filename,
                    "presenter_name": presenter_name,
                    "language": language,
                    "voice_id": voice_id,
                    "word_count": len(script_content.split()),
                    "estimated_duration": f"{max(4, len(script_content.split()) // 150)} minutes",
                    "script_type": "simple_conversational_podcast",
                    "model_used": "gpt-4o",
                    "audio_model": "eleven_multilingual_v2",
                    "created_at": datetime.now().isoformat(),
                    "audio_generated_at": datetime.now().isoformat(),
                    "status": "complete_podcast_generated"
                }
                
                doc_ref = db_client.collection('audio_connections').document()
                doc_ref.set(complete_podcast_data)
                doc_id = doc_ref.id
            
            logger.info(f"📀 Complete podcast saved to database: {doc_id}")
            
            # Step 5: Save audio link in audio > user_id collection with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    audio_user_ref = db_client.collection('audio').document(user_id)
                    audio_data = {
                        "latest_podcast_url": audio_storage_url,
                        "latest_podcast_created": datetime.now().isoformat(),
                        "latest_podcast_id": doc_id,
                        "script_url": script_storage_url,
                        "presenter_name": presenter_name,
                        "language": language,
                        "voice_id": voice_id,
                        "audio_filename": audio_filename,
                        "status": "complete_podcast_generated"
                    }
                    audio_user_ref.set(audio_data, merge=True)
                    logger.info(f"🎵 Audio link saved in audio/{user_id}")
                    break
                except Exception as audio_save_error:
                    logger.warning(f"Attempt {attempt + 1} failed to save to audio collection: {audio_save_error}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to save audio link after {max_retries} attempts: {audio_save_error}")
                        # Continue anyway - don't fail the whole process
            
        except Exception as db_error:
            logger.error(f"Error saving complete podcast to database: {db_error}")
            # Don't fail the whole process for DB errors, but log it prominently
            logger.error(f"🚨 DATABASE SAVE FAILED - Audio generated successfully but not saved to database: {db_error}")
        
        # Step 6: Prepare final result
        result = {
            "success": True,
            "script": script_content,
            "script_storage_url": script_storage_url,
            "audio_url": audio_storage_url,
            "audio_filename": audio_filename,
            "metadata": {
                "user_id": user_id,
                "presenter_name": presenter_name,
                "language": language,
                "voice_id": voice_id,
                "word_count": len(script_content.split()),
                "estimated_duration": f"{max(4, len(script_content.split()) // 150)} minutes",
                "script_type": "simple_conversational_podcast",
                "model_used": "gpt-4o",
                "audio_model": "eleven_multilingual_v2",
                "audio_size_bytes": len(audio_bytes)
            },
            "generation_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🎉 Complete podcast generation successful for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating complete podcast for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate complete podcast",
            "metadata": {"user_id": user_id, "error": True}
        }

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
        voice_id = request_json.get("voice_id", "cmudN4ihcI42n48urXgc")
        
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

@scheduler_fn.on_schedule(schedule="*/15 * * * *", timeout_sec=540, memory=options.MemoryOption.MB_512)  # Every 15 minutes, 9 min timeout, increased memory
def scheduled_user_updates(req):
    """
    Scheduled function that runs every 15 minutes to check user scheduling preferences
    and trigger updates for users whose scheduled time has arrived.
    
    This function:
    1. Gets current time
    2. Reads all scheduling preferences from Firestore
    3. Checks which users need updates based on their preferences
    4. Triggers async updates for those users
    """
    try:
        logger.info("⏰ Starting scheduled user updates check...")
        
        # Get current time
        current_time = datetime.now()
        logger.info(f"🕐 Current time: {current_time}")
        
        # Get Firestore client
        db = firestore.client()
        
        # Read all scheduling preferences
        scheduling_ref = db.collection('scheduling_preferences')
        all_schedules = scheduling_ref.stream()
        
        users_to_update = []
        total_users_checked = 0
        
        # Check each user's scheduling preferences
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
                logger.info(f"📋 Added user {user_id} to update queue")
        
        logger.info(f"📊 Scheduling check complete: {total_users_checked} users checked, {len(users_to_update)} users need updates")
        
        # Trigger updates for all qualifying users (async, non-blocking)
        for user_info in users_to_update:
            user_id = user_info['user_id']
            prefs = user_info['preferences']
            
            # You could customize these based on user preferences if stored
            presenter_name = "Alex"
            language = "en"
            voice_id = "cmudN4ihcI42n48urXgc"
            
            logger.info(f"🚀 Triggering async update for user: {user_id}")
            trigger_user_update_async(
                user_id=user_id,
                presenter_name=presenter_name,
                language=language,
                voice_id=voice_id
            )
        
        # Return summary (for logging)
        summary = {
            "success": True,
            "timestamp": current_time.isoformat(),
            "total_users_checked": total_users_checked,
            "users_triggered": len(users_to_update),
            "triggered_user_ids": [u['user_id'] for u in users_to_update]
        }
        
        logger.info(f"✅ Scheduled updates summary: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error in scheduled user updates: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

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
        voice_id = data.get('voice_id', 'cmudN4ihcI42n48urXgc')
        
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