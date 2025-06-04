"""
Configuration et constantes pour Prysm Backend
"""
import os
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

# API Keys
SERPAPI_API_KEY_HARDCODED = "08ef5c4be14a2d80d5f0036ca726cb8f02e4428ceba23348ac04595a766327a3"
GNEWS_API_KEY = "75807d7923a12e3d80d64c971ff340da"
GNEWS_BASE_URL = "https://gnews.io/api/v4"
NEWSAPI_API_KEY = "31c5260ea92b400ca4972424b8a1f12b"  # Remplacez par votre vraie clé NewsAPI

# Country mapping (extrait de main.py)
COUNTRY_NAME_TO_CODE = {
    "afghanistan": "af", "albania": "al", "algeria": "dz", "argentina": "ar", 
    "armenia": "am", "australia": "au", "austria": "at", "azerbaijan": "az",
    "bahrain": "bh", "bangladesh": "bd", "belarus": "by", "belgium": "be",
    "bolivia": "bo", "bosnia and herzegovina": "ba", "brazil": "br", "bulgaria": "bg",
    "canada": "ca", "chile": "cl", "china": "cn", "colombia": "co", "croatia": "hr",
    "cuba": "cu", "cyprus": "cy", "czech republic": "cz", "denmark": "dk",
    "dominican republic": "do", "ecuador": "ec", "egypt": "eg", "estonia": "ee",
    "finland": "fi", "france": "fr", "georgia": "ge", "germany": "de", "ghana": "gh",
    "greece": "gr", "guatemala": "gt", "honduras": "hn", "hong kong": "hk",
    "hungary": "hu", "iceland": "is", "india": "in", "indonesia": "id", "iran": "ir",
    "iraq": "iq", "ireland": "ie", "israel": "il", "italy": "it", "jamaica": "jm",
    "japan": "jp", "jordan": "jo", "kazakhstan": "kz", "kenya": "ke", "kuwait": "kw",
    "latvia": "lv", "lebanon": "lb", "libya": "ly", "lithuania": "lt", "luxembourg": "lu",
    "malaysia": "my", "maldives": "mv", "malta": "mt", "mexico": "mx", "morocco": "ma",
    "myanmar": "mm", "nepal": "np", "netherlands": "nl", "new zealand": "nz",
    "nicaragua": "ni", "nigeria": "ng", "north korea": "kp", "norway": "no",
    "oman": "om", "pakistan": "pk", "panama": "pa", "paraguay": "py", "peru": "pe",
    "philippines": "ph", "poland": "pl", "portugal": "pt", "puerto rico": "pr",
    "romania": "ro", "russia": "ru", "saudi arabia": "sa", "senegal": "sn",
    "serbia": "rs", "singapore": "sg", "slovakia": "sk", "slovenia": "si",
    "somalia": "so", "south africa": "za", "south korea": "kr", "spain": "es",
    "sri lanka": "lk", "sudan": "sd", "sweden": "se", "switzerland": "ch",
    "syria": "sy", "taiwan": "tw", "tanzania": "tz", "thailand": "th", "tunisia": "tn",
    "turkey": "tr", "uganda": "ug", "ukraine": "ua", "united arab emirates": "ae",
    "united kingdom": "gb", "united states": "us", "uruguay": "uy", "venezuela": "ve",
    "vietnam": "vn", "yemen": "ye", "zimbabwe": "zw"
}

def get_openai_key():
    """Retrieve OpenAI API key from environment or fallback to hardcoded value."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    logger.warning("OPENAI_API_KEY not found in env, using fallback key")
    return "sk-HxFKqwvTI8JfWp0WbPRF75FsoEQokPS2IQHrKIKQwtT3BlbkFJwNHRfzhJb-_Xz39M9531MNdy35DGxMkTZ2s05X2sYA"

def get_serpapi_key():
    """Retrieve SerpAPI key from environment or use hardcoded fallback."""
    key = os.environ.get("SERPAPI_API_KEY")
    if key:
        return key
    logger.warning("SERPAPI_API_KEY not found in env, using fallback key")
    return SERPAPI_API_KEY_HARDCODED

def get_gnews_key():
    """Retrieve GNews API key."""
    return GNEWS_API_KEY

def get_elevenlabs_key():
    """Retrieve ElevenLabs API key."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    logger.warning("ELEVENLABS_API_KEY not found in env, using fallback key")
    return "sk_7b7a81c1e9c8c73b3e0c69c90c68c5c7b7a81c1e9c8c73b3e0c69c90c68c5c7"

def get_cartesia_key():
    """Retrieve Cartesia API key."""
    key = os.environ.get("CARTESIA_API_KEY")
    if key:
        return key
    logger.warning("CARTESIA_API_KEY not found in env, using fallback key")
    return "sk_car_fygBZkHQCaWQDUtWjBjcxc"

def get_newsapi_key():
    """Retrieve NewsAPI key from environment or use hardcoded fallback."""
    key = os.environ.get("NEWSAPI_API_KEY")
    if key:
        return key
    logger.warning("NEWSAPI_API_KEY not found in env, using fallback key")
    return NEWSAPI_API_KEY 