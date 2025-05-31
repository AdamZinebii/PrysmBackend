import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any

def search_gnews(query: str, gl: str = "us", hl: str = "en", max_articles: int = 10, time_period: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for news articles using the GNews API.
    
    Args:
        query (str): Search query/keywords
        gl (str): Country code (default: "us")
        hl (str): Language code (default: "en") 
        max_articles (int): Maximum number of articles to return (default: 10)
        time_period (str, optional): Time period filter (e.g., "7d", "1m", "1y")
        
    Returns:
        Dict[str, Any]: JSON response from GNews API
    """
    
    # Base URL for GNews API
    base_url = "https://gnews.io/api/v4/search"
    
    # Map parameters to GNews API format
    params = {
        "q": query,
        "country": gl, 
        "lang": hl,
        "max": max_articles,
        "apikey": "75807d7923a12e3d80d64c971ff340da"  # GNews API key
    }
    
    # Add time period if specified
    if time_period:
        params["period"] = time_period
    
    # Encode parameters
    encoded_params = urllib.parse.urlencode(params)
    url = f"{base_url}?{encoded_params}"
    
    try:
        # Make the request
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
            
    except urllib.error.HTTPError as e:
        return {
            "error": f"HTTP Error {e.code}: {e.reason}",
            "status": "failed"
        }
    except urllib.error.URLError as e:
        return {
            "error": f"URL Error: {e.reason}",
            "status": "failed"
        }
    except json.JSONDecodeError as e:
        return {
            "error": f"JSON Decode Error: {e}",
            "status": "failed"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "status": "failed"
        } 