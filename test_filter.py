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



url = "https://serpapi.com/search.json"
params = {
    "engine": "google_news",
    "api_key": "08ef5c4be14a2d80d5f0036ca726cb8f02e4428ceba23348ac04595a766327a3",
}

# Add query if provided
params["q"] = "Startup"

# Add time period filter if provided



import requests

response = requests.get(url, params=params, timeout=30)
print(response.json())
print("__________________\n___________________\n")
print(filter_news_last_24_hours(response))