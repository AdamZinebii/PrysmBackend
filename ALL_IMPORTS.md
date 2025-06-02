# 🔗 ALL MODULE IMPORTS NEEDED FOR PRYSM BACKEND

This file contains ONLY the module-to-module import statements needed for each file.

## 📁 **main.py**

```python
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
from modules.config import get_openai_key
from modules.database.operations import update_specific_subjects_in_db

from modules.config import get_cartesia_key

from modules.ai.client import get_openai_client

---

## 📁 **modules/content/podcast.py**

```python
from modules.ai.client import get_openai_client
from modules.audio.cartesia import generate_text_to_speech
from modules.content.generation import get_complete_topic_report, get_pickup_line, get_reddit_community_insights, get_topic_summary
from modules.database.operations import get_user_articles_from_db
from modules.scheduling.tasks import get_complete_report, update
```

---

## 📁 **modules/content/topics.py**

```python
from modules.ai.client import get_openai_client
from modules.news.serpapi import gnews_search, gnews_top_headlines
```

---

## 📁 **modules/database/operations.py**

```python
from modules.content.topics import convert_old_topic_to_gnews, find_parent_topic_for_subtopic, find_subtopic_in_catalog
```

---

## 📁 **modules/news/news_helper.py**

```python
from modules.content.generation import get_reddit_post_comments
from modules.news.serpapi import format_gnews_articles_for_prysm, gnews_search
```

---

## 📁 **modules/news/serpapi.py**

```python
from modules.ai.client import summarize_article_content
from modules.config import get_gnews_key, get_serpapi_key, GNEWS_BASE_URL
```

---

## 📁 **modules/notifications/push.py**

```python
# No module imports needed
```

---

## 📁 **modules/scheduling/tasks.py**

```python
from modules.content.generation import get_complete_topic_report
from modules.content.podcast import generate_simple_podcast
from modules.database.operations import get_user_articles_from_db, get_user_preferences_from_db
from modules.notifications.push import send_push_notification
from modules.utils.country import get_user_country_from_db
```

---

## 📁 **modules/utils/country.py**

```python
# No module imports needed
```

## 🎯 **Usage Instructions**

1. Copy the imports for each file
2. Add them at the top of each respective file
3. Remove any imports that aren't actually used
4. Add standard imports (json, logging, etc.) as needed
5. Test each file to ensure all imports resolve correctly

## ⚠️ **Notes**

- Some functions may not be used in all contexts - remove unused imports to keep code clean
- Standard library imports (json, logging, datetime, etc.) are included as suggestions
- Firebase imports are included where needed for database operations
- The circular import between `modules.content.podcast` and `modules.scheduling.tasks` may need attention 