import sys


# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation


from datetime import datetime, timedelta

import requests
import time

from modules.news.serpapi import format_gnews_articles_for_prysm, gnews_search

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
            max_articles=4,
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
            result[subtopic_name] = format_gnews_articles_for_prysm(subtopic_response)[:4]
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
                max_articles=4,
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
            max_articles=4,
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
                max_articles=4,
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
