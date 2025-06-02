import sys


# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

import requests
from modules.news.serpapi import  gnews_search, gnews_top_headlines

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
        # Lazy import to avoid circular dependency
        from ..ai.client import get_openai_client
        
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
        # Lazy import to avoid circular dependency
        from ..ai.client import get_openai_client
        
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