# 🔥 Trending Subtopics API - PrysmIOS Backend

## 📋 **Overview**

New API endpoint that analyzes current news articles for a given topic and extracts trending subtopics using AI/LLM analysis.

## 🚀 **How It Works**

1. **Fetch Headlines**: Uses existing `gnews_top_headlines()` function to get latest articles
2. **LLM Analysis**: Sends article titles and descriptions to GPT-4o-mini for analysis
3. **Extract Keywords**: AI identifies 5-8 trending subtopic keywords from the articles
4. **Return Results**: Returns a clean list of trending subtopic keywords

## 🔧 **API Endpoint**

### **POST** `/get_trending_subtopics`

**Request Body:**
```json
{
    "topic": "technology",
    "lang": "en",
    "country": "us",
    "max_articles": 10
}
```

**Parameters:**
- `topic` (required): Main topic/category to analyze
  - Valid values: `"general"`, `"world"`, `"nation"`, `"business"`, `"technology"`, `"entertainment"`, `"sports"`, `"science"`, `"health"`
- `lang` (optional): Language code (default: `"en"`)
- `country` (optional): Country code (default: `"us"`)
- `max_articles` (optional): Number of articles to analyze (1-20, default: 10)

**Response:**
```json
{
    "success": true,
    "topic": "technology",
    "articles_analyzed": 10,
    "subtopics": [
        "AI regulation",
        "ChatGPT updates", 
        "tech layoffs",
        "startup funding",
        "cybersecurity threats",
        "Apple Vision Pro",
        "quantum computing"
    ],
    "usage": {
        "prompt_tokens": 1250,
        "completion_tokens": 45,
        "total_tokens": 1295
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "error": "No articles found for topic: invalidtopic",
    "subtopics": []
}
```

## 💡 **Usage Examples**

### **Technology Trends**
```bash
curl -X POST https://your-firebase-function-url/get_trending_subtopics \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "technology",
    "lang": "en",
    "country": "us",
    "max_articles": 10
  }'
```

### **Sports Trends**
```bash
curl -X POST https://your-firebase-function-url/get_trending_subtopics \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "sports",
    "lang": "en",
    "country": "us",
    "max_articles": 15
  }'
```

### **French Business Trends**
```bash
curl -X POST https://your-firebase-function-url/get_trending_subtopics \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "business",
    "lang": "fr",
    "country": "fr",
    "max_articles": 8
  }'
```

## 🔍 **Function Details**

### **Core Function: `extract_trending_subtopics()`**

```python
def extract_trending_subtopics(topic, lang="en", country="us", max_articles=10):
    """
    Extract trending subtopics from news articles for a given topic using LLM analysis.
    
    Args:
        topic (str): The main topic/category to analyze
        lang (str): Language code 
        country (str): Country code
        max_articles (int): Number of articles to analyze
    
    Returns:
        dict: Response with success status and list of trending subtopic keywords
    """
```

### **HTTP Endpoint: `get_trending_subtopics()`**

- **Method**: POST
- **Timeout**: 120 seconds
- **CORS**: Enabled for all origins
- **Rate Limiting**: Inherits from Firebase Functions

## 🎯 **LLM Analysis Process**

### **Prompt Strategy**
The LLM receives a carefully crafted prompt that:
- Analyzes article titles and descriptions
- Focuses on SPECIFIC trending themes
- Avoids general concepts
- Extracts 5-8 keyword subtopics
- Returns comma-separated keywords

### **Example LLM Input**
```
You are a news analysis expert. Analyze the following 10 news articles about "technology" and extract the top trending subtopics.

TASK: Extract 5-8 specific trending subtopics as keywords from these articles.

RULES:
1. Focus on SPECIFIC trending themes, not general concepts
2. Extract keywords that represent current trends and hot topics
3. Avoid very general terms like "news" or "updates"
4. Prefer specific technologies, events, companies, or phenomena mentioned
5. Return ONLY the keywords, separated by commas
6. Each keyword should be 1-3 words maximum
7. Focus on what's currently trending or newsworthy

ARTICLES TO ANALYZE:
Article 1:
Title: Apple Vision Pro Sales Disappoint as Mixed Reality Market Struggles
Description: Apple's highly anticipated Vision Pro headset faces lukewarm reception...

Article 2:
Title: OpenAI Announces GPT-5 Development Amid AI Regulation Debates
Description: The AI company reveals plans for next-generation language model...
...
```

### **Example LLM Output**
```
Vision Pro sales, GPT-5 development, AI regulation, mixed reality, quantum breakthrough, tech layoffs, startup funding, cybersecurity threats
```

## ⚡ **Performance & Limits**

- **Response Time**: ~5-15 seconds (depends on article count and LLM processing)
- **Article Limit**: Maximum 20 articles per request
- **Token Usage**: ~1000-2000 tokens per request
- **Rate Limits**: Subject to Firebase Functions and OpenAI API limits

## 🔗 **Integration with Existing Functions**

This new functionality builds on top of existing backend functions:

1. **`gnews_top_headlines()`** - Fetches articles from GNews API
2. **`get_openai_client()`** - Gets configured OpenAI client
3. **`get_gnews_key()`** - Retrieves GNews API key

No existing functions were modified - this is purely additive functionality.

## 🛠️ **Error Handling**

The API handles various error scenarios:

- **No articles found**: Returns empty subtopics array
- **OpenAI API unavailable**: Returns error message
- **Invalid topic**: Falls back to "general" category
- **Network timeouts**: Returns timeout error
- **Rate limiting**: Returns rate limit error

## 📊 **Use Cases**

1. **Dynamic Subcategory Discovery**: Automatically discover trending subtopics for user preferences
2. **Content Curation**: Identify hot topics for news feed personalization  
3. **Trend Analysis**: Track what's currently trending in different categories
4. **User Onboarding**: Show users current trending topics during preference setup
5. **Real-time Insights**: Get up-to-date view of what's newsworthy in each category

## 🎉 **Benefits**

- **Real-time**: Always reflects current news trends
- **AI-powered**: Intelligent extraction of meaningful subtopics
- **Flexible**: Works with any supported topic/language/country
- **Scalable**: Built on existing robust infrastructure
- **Non-intrusive**: Doesn't modify existing functionality 