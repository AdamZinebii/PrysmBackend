import sys

import time
# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

from datetime import datetime

import requests

from modules.ai.client import get_openai_client
from modules.news.news_helper import get_articles_subtopics_user, get_reddit_post_comments

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

def get_topic_summary(topic_name, topic_content_data):
    """
    Generate a comprehensive summary of all topic content with key facts from each article.
    Now includes smooth source citations in the format <<url>> after relevant content.
    
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
                "topic_summary": "Comprehensive formatted summary with key facts and source citations...",
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
        
        # Prepare content for LLM analysis WITH URLS
        content_text = f"TOPIC: {topic_name}\n\n"
        
        # Add topic headlines with URLs
        if all_content["topic_headlines"]:
            content_text += "🔥 MAIN TOPIC HEADLINES:\n"
            for i, article in enumerate(all_content["topic_headlines"], 1):
                title = article.get('title', 'No title')
                snippet = article.get('snippet', article.get('description', ''))
                source = article.get('source', 'Unknown source')
                url = article.get('url', article.get('link', ''))
                content_text += f"{i}. {title}\n"
                content_text += f"   Source: {source}\n"
                if url:
                    content_text += f"   URL: {url}\n"
                if snippet:
                    content_text += f"   Summary: {snippet}\n"
                content_text += "\n"
        
        # Add subtopic articles with URLs
        if all_content["subtopic_articles"]:
            content_text += "📊 SUBTOPIC ARTICLES:\n"
            for subtopic_name, articles in all_content["subtopic_articles"].items():
                content_text += f"\n{subtopic_name.upper()}:\n"
                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'No title')
                    snippet = article.get('snippet', article.get('description', ''))
                    source = article.get('source', 'Unknown source')
                    url = article.get('url', article.get('link', ''))
                    content_text += f"  {i}. {title}\n"
                    content_text += f"     Source: {source}\n"
                    if url:
                        content_text += f"     URL: {url}\n"
                    if snippet:
                        content_text += f"     Summary: {snippet}\n"
                content_text += "\n"
        
        # Add query-based articles with URLs
        if all_content["query_articles"]:
            content_text += "🔍 QUERY-BASED ARTICLES:\n"
            for query_label, articles in all_content["query_articles"].items():
                content_text += f"\n{query_label.upper()}:\n"
                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'No title')
                    snippet = article.get('snippet', article.get('description', ''))
                    source = article.get('source', 'Unknown source')
                    url = article.get('url', article.get('link', ''))
                    content_text += f"  {i}. {title}\n"
                    content_text += f"     Source: {source}\n"
                    if url:
                        content_text += f"     URL: {url}\n"
                    if snippet:
                        content_text += f"     Summary: {snippet}\n"
                content_text += "\n"
        
        # Add Reddit discussions (no URLs needed for Reddit)
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
        
        # Create LLM prompt for summary generation WITH CITATION INSTRUCTIONS
        summary_prompt = f"""You are a professional news analyst creating clean, structured summaries. Create a concise summary of the {topic_name} topic based on the content below.

INSTRUCTIONS:
1. Write in a professional, factual tone
2. Use clean structure with clear sections
3. Keep the entire summary under 100 words
4. Use minimal formatting for better mobile readability
5. Focus on key facts and developments
6. No excessive emojis or dramatic language
7. Use simple bullet points and clear sections

CITATION INSTRUCTIONS:
8. When you mention facts from articles, add the source URL AFTER the final period of the sentence using format: <<URL>>
9. ONLY add citations for article-based information (not Reddit discussions)
10. Integrate citations smoothly into the text flow
11. If multiple facts come from the same article, cite once at the end of that content
12. Example: "Tesla reported 20% growth in Q3 deliveries. <<https://example.com/tesla-news>>"

FORMATTING RULES FOR iOS:
- Use double line breaks between sections
- Use "•" for bullet points (not dashes or asterisks)  
- Put each bullet point on its own line
- Avoid complex markdown - keep it simple
- Use **bold** only for section headers
- Use ***bold*** (triple asterisks) for important words within paragraphs
- CREATE YOUR OWN SECTION TITLES based on the actual content - don't use generic templates

DYNAMIC FORMATTING INSTRUCTIONS:
- Analyze the content and create 2-3 relevant section titles that match what you're discussing
- Section titles should be specific to the content, not generic like "Key Developments" or "Market Impact"
- Examples of good dynamic titles: "AI Chip Shortage", "Federal Reserve Updates", "Tesla Production Changes", "European Energy Crisis", etc.
- Make titles descriptive and specific to what's actually happening
- Highlight key companies, numbers, or important terms within sentences using ***triple asterisks***

FORMAT STRUCTURE:
**{topic_name} Summary**

**[Your Dynamic Title 1 Based on Actual Content]**
• [Brief fact 1 with ***important words*** highlighted]. <<URL>>
• [Brief fact 2 with ***key terms*** highlighted]. <<URL>>

**[Your Dynamic Title 2 Based on Actual Content]**
• [Relevant information with ***significant details*** highlighted]. <<URL>>

**[Your Dynamic Title 3 Based on Actual Content]** (if needed)
• [Important trends with ***crucial data*** highlighted]. <<URL>>

IMPORTANT: Every URL citation must be enclosed with EXACTLY two angle brackets: <<URL>>

CONTENT TO ANALYZE:
{content_text}

Generate the clean, professional summary now with properly formatted source citations (MAX 100 WORDS):"""

        # Get OpenAI client and generate response
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional news analyst who creates clean, factual summaries with DYNAMIC section titles and smooth source citations. When mentioning facts from articles, immediately add the source URL in <<URL>> format. Analyze the content and create specific, relevant section headers. Use simple formatting, avoid excessive emojis, and focus on key facts. Keep summaries concise and professional."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=600,  # Increased to accommodate citations and ensure completion
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
- Use **bold** for section headers
- Use ***bold*** (triple asterisks) for important words within paragraphs
- Highlight key companies, numbers, countries, or important terms using ***triple asterisks***
- Avoid complex markdown formatting
- Ensure proper spacing between elements

FORMAT:
**Key Developments:**

• [Major trend/event 1 with ***important details*** highlighted]

• [Major trend/event 2 with ***key information*** highlighted]

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
        logger.info(f"Fetchinxg pdosts for topdcic: {topic_name} with {len(topic_data)} subtopics")
        
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