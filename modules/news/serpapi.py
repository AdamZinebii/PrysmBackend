"""
Module SerpAPI pour la recherche de nouvelles
"""
import sys
sys.stdout.write("--- main.py PYTHON SCRIPT STARTED (STDOUT) ---\n")
sys.stderr.write("--- main.py PYTHON SCRIPT STARTED (STDERR) ---\n")
print("--- main.py PYTHON SCRIPT STARTED (PRINT) ---")
import time
# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation
from ..config import get_serpapi_key, get_gnews_key, GNEWS_BASE_URL

from datetime import datetime, timedelta
import requests

def serpapi_google_news_search(query, gl="us", hl="en", max_articles=10, time_period=None, topic_token=None):
    """
    Search Google News using multi-tier fallback strategy:
    1. GNews API first (with US fallback)
    2. NewsAPI for 48h articles to complement
    3. SerpAPI as final fallback
    
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
    
    def _parse_gnews_article(gnews_article):
        """Convert GNews article to SerpAPI format for consistency."""
        try:
            return {
                "title": gnews_article.get("title", ""),
                "description": gnews_article.get("description", ""),
                "content": summarize_article_content(gnews_article.get("content", "")),
                "url": gnews_article.get("url", ""),
                "image": gnews_article.get("image", ""),
                "publishedAt": gnews_article.get("publishedAt", ""),
                "source": {
                    "name": gnews_article.get("source", {}).get("name", "Unknown"),
                    "url": gnews_article.get("source", {}).get("url", "")
                }
            }
        except Exception as e:
            logger.error(f"❌ Error parsing GNews article: {e}")
            return None

    def _parse_newsapi_article(newsapi_article):
        """Convert NewsAPI article to standard format for consistency."""
        try:
            source_info = newsapi_article.get("source", {})
            return {
                "title": newsapi_article.get("title", ""),
                "description": newsapi_article.get("description", ""),
                "content": newsapi_article.get("content", ""),
                "url": newsapi_article.get("url", ""),
                "image": newsapi_article.get("urlToImage", ""),
                "publishedAt": newsapi_article.get("publishedAt", ""),
                "source": {
                    "name": source_info.get("name", "Unknown"),
                    "url": ""  # NewsAPI doesn't provide source URL
                }
            }
        except Exception as e:
            logger.error(f"❌ Error parsing NewsAPI article: {e}")
            return None

    def _try_gnews_search(query, country, lang, max_articles, time_period, attempt_name):
        """Helper function to try GNews search with specific parameters."""
        try:
            from gnews_api_function import search_gnews
            
            logger.info(f"🔍 {attempt_name}: '{query}' | {country}/{lang} | Max: {max_articles}")
            
            if country == None:
                gnews_result = search_gnews(
                    query=query,
                    hl=lang, 
                    max_articles=max_articles,
                    time_period=time_period
                    
                )
            else:
                gnews_result = search_gnews(
                    query=query,
                    gl=country,
                    hl=lang, 
                    max_articles=max_articles,
                    time_period=time_period
                )
            
            articles = []
            if 'articles' in gnews_result and gnews_result['articles']:
                for gnews_article in gnews_result['articles'][:max_articles]:
                    parsed_article = _parse_gnews_article(gnews_article)
                    if parsed_article:
                        articles.append(parsed_article)
                
                logger.info(f"✅ {attempt_name}: Found {len(articles)} articles")
            else:
                logger.info(f"⚠️ {attempt_name}: No articles found")
                
            return articles
            
        except Exception as e:
            logger.warning(f"⚠️ {attempt_name} failed: {e}")
            return []

    def _try_newsapi_search(query, lang, articles_needed, attempt_name):
        """Helper function to try NewsAPI search for 48h articles."""
        try:
            from ..config import get_newsapi_key
            import requests
            from datetime import datetime, timedelta
            
            logger.info(f"🔍 {attempt_name}: '{query}' | {lang} | Max: {articles_needed}")
            
            # Calculate 48h period for NewsAPI
            now = datetime.utcnow()
            from_date = now - timedelta(hours=48)
            from_iso = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            to_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Direct NewsAPI call
            api_key = get_newsapi_key()
            url = "https://newsapi.org/v2/everything"
            params = {
                'apiKey': api_key,
                'q': query,
                'from': from_iso,
                'to': to_iso,
                'language': lang,
                'sortBy': 'publishedAt',
                'pageSize': min(articles_needed, 100)  # NewsAPI max is 100
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                newsapi_articles = data.get('articles', [])
                
                # Convert NewsAPI articles to our standard format
                articles = []
                for newsapi_article in newsapi_articles[:articles_needed]:
                    # Enhanced parsing with author and better source handling
                    source_info = newsapi_article.get("source", {})
                    
                    standard_article = {
                        "title": newsapi_article.get("title", ""),
                        "description": newsapi_article.get("description", ""),
                        "content": newsapi_article.get("content", ""),
                        "url": newsapi_article.get("url", ""),
                        "image": newsapi_article.get("urlToImage", ""),
                        "publishedAt": newsapi_article.get("publishedAt", ""),
                        "source": {
                            "name": source_info.get("name", "Unknown"),
                            "url": "",  # NewsAPI doesn't provide source URL
                            "id": source_info.get("id", "")  # Include source ID from NewsAPI
                        },
                        "author": newsapi_article.get("author", "")  # Include author from NewsAPI
                    }
                    
                    # Only add articles with minimum required fields
                    if standard_article["title"] and standard_article["url"]:
                        articles.append(standard_article)
                
                logger.info(f"✅ {attempt_name}: Found {len(articles)} articles")
                return articles
                
            elif response.status_code == 401:
                logger.warning(f"⚠️ {attempt_name}: Invalid API key")
                return []
                
            elif response.status_code == 429:
                logger.warning(f"⚠️ {attempt_name}: Rate limit exceeded")
                return []
                
            else:
                logger.warning(f"⚠️ {attempt_name}: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ {attempt_name} failed: {e}")
            return []
    
    # Step 1: Try GNews first (skip if topic_token is provided, as GNews doesn't support it)
    gnews_articles = []
    if query and not topic_token:  # GNews works best with queries, not for homepage browsing
        
        # Step 1a: Try GNews with original country
        gnews_articles = _try_gnews_search(query, gl, hl, max_articles, time_period, "GNews (original)")
        time.sleep(1.5)
        # Step 1b: If no results and original country is not "us", try with "us"
        if len(gnews_articles) == 0:
            logger.info(f"🔄 GNews original country '{gl}' returned no results, trying with US...")
            gnews_articles_us = _try_gnews_search(query, None, hl, max_articles, time_period, "GNews (US fallback)")
            gnews_articles = gnews_articles_us
            
            if len(gnews_articles) > 0:
                logger.info(f"🎯 GNews US fallback successful: found {len(gnews_articles)} articles")
        
        # If we have enough articles from GNews (either original or US fallback), return them
        if len(gnews_articles) >= max_articles:
            logger.info(f"🎯 GNews provided enough articles ({len(gnews_articles)}>={max_articles}), skipping NewsAPI and SerpAPI")
            return {
                "success": True,
                "totalArticles": max_articles,
                "articles": gnews_articles[:max_articles],
                "serpapi_data": {
                    "related_topics": [],
                    "menu_links": [],
                    "topic_token": topic_token
                },
                "source": "gnews_only",
                "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
            }
    
    # Step 1.5: Try NewsAPI for 48h articles to complement GNews results
    newsapi_articles = []
    articles_needed_for_newsapi = max_articles - len(gnews_articles)
    
    # if articles_needed_for_newsapi > 0 and query:  # NewsAPI requires a query
    #     logger.info(f"🔄 GNews provided {len(gnews_articles)} articles, trying NewsAPI for {articles_needed_for_newsapi} more")
    #     newsapi_articles = _try_newsapi_search(query, hl, articles_needed_for_newsapi, "NewsAPI (48h complement)")
        
    #     # Check if we now have enough articles
    #     total_articles_so_far = len(gnews_articles) + len(newsapi_articles)
    #     if total_articles_so_far >= max_articles:
    #         logger.info(f"🎯 GNews + NewsAPI provided enough articles ({total_articles_so_far}>={max_articles}), skipping SerpAPI")
    #         all_articles = (gnews_articles + newsapi_articles)[:max_articles]
            
    #         # Determine source
    #         if len(gnews_articles) > 0 and len(newsapi_articles) > 0:
    #             source = "gnews_and_newsapi"
    #         elif len(gnews_articles) > 0:
    #             source = "gnews_only"
    #         else:
    #             source = "newsapi_only"
            
    #         return {
    #             "success": True,
    #             "totalArticles": len(all_articles),
    #             "articles": all_articles,
    #             "serpapi_data": {
    #                 "related_topics": [],
    #                 "menu_links": [],
    #                 "topic_token": topic_token
    #             },
    #             "source": source,
    #             "gnews_count": len(gnews_articles),
    #             "newsapi_count": len(newsapi_articles),
    #             "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
    #         }

    # Step 2: Calculate how many more articles we need from SerpAPI
    articles_needed = max_articles - len(gnews_articles) - len(newsapi_articles)
    
    if articles_needed <= 0:
        # We already have enough from GNews + NewsAPI
        all_articles = (gnews_articles + newsapi_articles)[:max_articles]
        
        # Determine source
        if len(gnews_articles) > 0 and len(newsapi_articles) > 0:
            source = "gnews_and_newsapi"
        elif len(gnews_articles) > 0:
            source = "gnews_only"
        else:
            source = "newsapi_only"
            
        return {
            "success": True,
            "totalArticles": len(all_articles),
            "articles": all_articles,
            "serpapi_data": {
                "related_topics": [],
                "menu_links": [],
                "topic_token": topic_token
            },
            "source": source,
            "gnews_count": len(gnews_articles),
            "newsapi_count": len(newsapi_articles),
            "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
        }
    
    # Step 3: Fetch remaining articles from SerpAPI
    logger.info(f"🔄 GNews ({len(gnews_articles)}) + NewsAPI ({len(newsapi_articles)}) provided {len(gnews_articles) + len(newsapi_articles)} articles, fetching {articles_needed} more from SerpAPI")
    
    api_key = get_serpapi_key()
    
    if query:
        logger.info(f"🔍 SerpAPI Google News Search: '{query}' | {gl}/{hl} | Max: {articles_needed}")
    else:
        logger.info(f"🏠 SerpAPI Google News Browse: {gl}/{hl} | Max: {articles_needed} | Topic: {topic_token or 'Homepage'}")
    
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
    
   
    # Add topic token if provided (for category browsing)
    if topic_token:
        params["topic_token"] = topic_token
        logger.info(f"🏷️ Topic token: {topic_token}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data_nofilter = response.json()
            data = filter_news_last_24_hours(data_nofilter)
            serpapi_articles = []
            
            # Parse articles from different possible response structures
            news_results = data.get("news_results", [])
            stories = data.get("stories", [])
            
            # Handle news_results (from search queries) - limit to articles_needed
            for item in news_results[:articles_needed]:
                article = _parse_serpapi_story(item)
                if article:
                    serpapi_articles.append(article)
                    if len(serpapi_articles) >= articles_needed:
                        break
            
            # Handle stories (from homepage/category browsing) - limit to articles_needed
            if len(serpapi_articles) < articles_needed and stories:
                for story_section in stories:
                    section_stories = story_section.get("stories", [])
                    for story in section_stories:
                        if len(serpapi_articles) >= articles_needed:
                            break
                        article = _parse_serpapi_story(story)
                        if article:
                            serpapi_articles.append(article)
                    if len(serpapi_articles) >= articles_needed:
                        break
            
            logger.info(f"✅ SerpAPI: Found {len(serpapi_articles)} additional articles")
            
            # Step 4: Combine GNews, NewsAPI and SerpAPI articles
            all_articles = (gnews_articles + newsapi_articles + serpapi_articles)[:max_articles]
            
            # Determine the source
            sources_used = []
            if len(gnews_articles) > 0:
                sources_used.append("gnews")
            if len(newsapi_articles) > 0:
                sources_used.append("newsapi")
            if len(serpapi_articles) > 0:
                sources_used.append("serpapi")
            
            source = "_and_".join(sources_used) if sources_used else "none"
            
            return {
                "success": True,
                "totalArticles": len(all_articles),
                "articles": all_articles,
                "serpapi_data": {
                    "related_topics": data.get("related_topics", []),
                    "menu_links": data.get("menu_links", []),
                    "topic_token": topic_token
                },
                "source": source,
                "gnews_count": len(gnews_articles),
                "newsapi_count": len(newsapi_articles),
                "serpapi_count": len(serpapi_articles),
                "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
            }
        
        elif response.status_code == 401:
            logger.error("❌ SerpAPI: Invalid API key")
            # If SerpAPI fails but we have some articles from GNews/NewsAPI, return those
            if gnews_articles or newsapi_articles:
                final_articles = (gnews_articles + newsapi_articles)[:max_articles]
                
                # Determine source for fallback
                sources_used = []
                if len(gnews_articles) > 0:
                    sources_used.append("gnews")
                if len(newsapi_articles) > 0:
                    sources_used.append("newsapi")
                source = "_and_".join(sources_used) if sources_used else "none"
                
                logger.info(f"🔄 SerpAPI failed, returning {len(final_articles)} articles from {source}")
                return {
                    "success": True,
                    "totalArticles": len(final_articles),
                    "articles": final_articles,
                    "serpapi_data": {
                        "related_topics": [],
                        "menu_links": [],
                        "topic_token": topic_token
                    },
                    "source": source,
                    "gnews_count": len(gnews_articles),
                    "newsapi_count": len(newsapi_articles),
                    "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
                }
            else:
                return {
                    "success": False,
                    "error": "SerpAPI authentication failed and no articles available from other sources",
                    "totalArticles": 0,
                    "articles": []
                }
        else:
            logger.error(f"❌ SerpAPI: HTTP {response.status_code}")
            # Return articles from GNews/NewsAPI if available, even if SerpAPI fails
            if gnews_articles or newsapi_articles:
                final_articles = (gnews_articles + newsapi_articles)[:max_articles]
                
                # Determine source for fallback
                sources_used = []
                if len(gnews_articles) > 0:
                    sources_used.append("gnews")
                if len(newsapi_articles) > 0:
                    sources_used.append("newsapi")
                source = "_and_".join(sources_used) if sources_used else "none"
                
                logger.info(f"🔄 SerpAPI error, returning {len(final_articles)} articles from {source}")
                return {
                    "success": True,
                    "totalArticles": len(final_articles),
                    "articles": final_articles,
                    "serpapi_data": {
                        "related_topics": [],
                        "menu_links": [],
                        "topic_token": topic_token
                    },
                    "source": source,
                    "gnews_count": len(gnews_articles),
                    "newsapi_count": len(newsapi_articles),
                    "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
                }
            else:
                return {
                    "success": False,
                    "error": f"SerpAPI error: {response.status_code}",
                    "totalArticles": 0,
                    "articles": []
                }
                
    except Exception as e:
        logger.error(f"❌ SerpAPI request failed: {e}")
        # Return articles from GNews/NewsAPI if available
        if gnews_articles or newsapi_articles:
            final_articles = (gnews_articles + newsapi_articles)[:max_articles]
            
            # Determine source for fallback
            sources_used = []
            if len(gnews_articles) > 0:
                sources_used.append("gnews")
            if len(newsapi_articles) > 0:
                sources_used.append("newsapi")
            source = "_and_".join(sources_used) if sources_used else "none"
            
            logger.info(f"🔄 SerpAPI exception, returning {len(final_articles)} articles from {source}")
            return {
                "success": True,
                "totalArticles": len(final_articles),
                "articles": final_articles,
                "serpapi_data": {
                    "related_topics": [],
                    "menu_links": [],
                    "topic_token": topic_token
                },
                "source": source,
                "gnews_count": len(gnews_articles),
                "newsapi_count": len(newsapi_articles),
                "used_us_fallback": gl.lower() != "us" and len(gnews_articles) > 0
            }
        else:
            return {
                "success": False,
                "error": f"All APIs failed: {str(e)}",
                "totalArticles": 0,
                "articles": []
            }


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
            time_period = "d"
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
    # if result.get('success') and result.get('totalArticles', 0) == 0 and time_period:
    #     logger.info(f"🔄 Google News Search: No articles found with time filter, trying without time filter")
    #     fallback_result = serpapi_google_news_search(
    #         query=query,
    #         gl=gl,
    #         hl=hl,
    #         max_articles=max_articles,
    #         time_period=None
    #     )
        
    #     if fallback_result.get('success') and fallback_result.get('totalArticles', 0) > 0:
    #         logger.info(f"✅ Google News Search: Fallback successful - found {fallback_result.get('totalArticles', 0)} articles")
    #         fallback_result['used_fallback'] = True
    #         fallback_result['original_time_period'] = time_period
    #         return fallback_result
    
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
        
        # Start with empty description (SerpAPI doesn't provide it)
        description = ""
        
        # Try to extract article summary using newspaper3k
        if link:
            try:
                logger.info(f"🔍 Attempting to extract summary for: {link}")
                
                from newspaper import Article
                import requests
                
                # Create newspaper article object
                article = Article(link)
                
                # Set timeout and user agent
                article.config.request_timeout = 10
                article.config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                
                # Download and parse the article
                article.download()
                article.parse()
                
                # Try to get summary/description
                if article.summary and len(article.summary.strip()) > 20:
                    description = article.summary.strip()
                    logger.info(f"✅ Extracted summary ({len(description)} chars)")
                elif article.text and len(article.text.strip()) > 50:
                    # Use LLM to summarize the full article text
                    description = summarize_article_content(article.text.strip())
                    if not description:  # Fallback to truncated text if LLM fails
                        description = article.text.strip()[:200] + "..." if len(article.text.strip()) > 200 else article.text.strip()
                        logger.info(f"Error LLM Generation ({len(description)} chars)")
                    else:
                        logger.info(f"✅ Generated LLM description ({len(description)} chars)")
                else:
                    logger.warning(f"⚠️ No usable content found in article")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract summary with newspaper3k: {e}")
                # Keep description empty if extraction fails
                
        # Create article in our standard format
        article = {
            "title": title,
            "description": description,  # Now contains extracted summary or remains empty
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


def summarize_article_content(content):
    """
    Use OpenAI to create a concise summary of article content.
    
    Args:
        content (str): Full article text content
        
    Returns:
        str: Concise summary under 100 words, or empty string if failed
    """
    if not content or len(content.strip()) < 50:
        return ""
    
    try:
        # Lazy import to avoid circular dependency
        from ..ai.client import get_openai_client
        
        client = get_openai_client()
        if not client:
            return ""
        
        # Truncate content if too long (OpenAI token limits)
        max_content_length = 4000  # Leave room for prompt and response
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Summarize this news article in under 200 words. Focus on the key facts, main events, and most important details. Be concise and factual:

{content}

Summary:"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a news summarization expert. Create concise, factual summaries under 100 words that capture the essential information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Roughly 100 words
            temperature=0.3  # Lower temperature for more factual, consistent summaries
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"✅ Article summarized: {len(summary)} characters")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error summarizing article: {e}")
        return "" 
    

import re
from datetime import datetime, timedelta, timezone
import dateutil.parser
import copy

def filter_news_last_24_hours(response):
    if hasattr(response, 'json'):
        data = response.json()
    elif isinstance(response, dict):
        data = response
    else:
        raise TypeError("Unsupported response type")

    # Extract the reference time from the SerpAPI response
    processed_at = data.get("search_metadata", {}).get("processed_at")
    if not processed_at:
        raise ValueError("Missing 'processed_at' in search_metadata")

    # Convert processed_at to datetime with UTC timezone
    reference_time = dateutil.parser.parse(processed_at + " +0000").astimezone(timezone.utc)
    time_window = timedelta(hours=24)

    def clean_date_string(date_str):
        # Remove trailing timezone name (e.g., "UTC") after numeric offset
        return re.sub(r'(\+\d{4})\s+\w+$', r'\1', date_str.strip())

    filtered_data = copy.deepcopy(data)
    filtered_data["news_results"] = []

    for news_item in data.get("news_results", []):
        try:
            raw_date = news_item.get("highlight", {}).get("date") or news_item.get("date")
            parsed_date = dateutil.parser.parse(clean_date_string(raw_date)).astimezone(timezone.utc)
        except Exception:
            continue

        if reference_time - parsed_date <= time_window:
            filtered_stories = []
            for story in news_item.get("stories", []):
                try:
                    story_date = dateutil.parser.parse(clean_date_string(story["date"])).astimezone(timezone.utc)
                    if reference_time - story_date <= time_window:
                        filtered_stories.append(copy.deepcopy(story))
                except Exception:
                    continue

            news_copy = copy.deepcopy(news_item)
            news_copy["stories"] = filtered_stories
            filtered_data["news_results"].append(news_copy)

    return filtered_data
