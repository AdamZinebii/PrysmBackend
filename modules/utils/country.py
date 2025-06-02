"""
Utilitaires pour la gestion des pays
"""
import sys
sys.stdout.write("--- main.py PYTHON SCRIPT STARTED (STDOUT) ---\n")
sys.stderr.write("--- main.py PYTHON SCRIPT STARTED (STDERR) ---\n")
print("--- main.py PYTHON SCRIPT STARTED (PRINT) ---")

# Configure logging AS EARLY AS POSSIBLE
import logging
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

from firebase_admin import firestore
logger.info("--- main.py: Logging configured ---")
from ..config import COUNTRY_NAME_TO_CODE
def get_country_code(country_name):
    """
    Convert country name to ISO 3166-1 alpha-2 country code for SerpAPI/GNews.
    
    Args:
        country_name (str): Country name (case insensitive)
    
    Returns:
        str: ISO country code (e.g., 'us', 'fr', 'de') or original input if not found
    """
    if not country_name or not isinstance(country_name, str):
        return "us"  # Default to US
    
    # Normalize the country name
    normalized_name = country_name.lower().strip()
    
    # Check if it's already a valid country code (2 letters)
    if len(normalized_name) == 2 and normalized_name.isalpha():
        return normalized_name.lower()
    
    # Look up in mapping
    country_code = COUNTRY_NAME_TO_CODE.get(normalized_name)
    
    if country_code:
        return country_code
    
    # If not found, try to find partial matches
    for name, code in COUNTRY_NAME_TO_CODE.items():
        if normalized_name in name or name in normalized_name:
            return code
    
    # Default to US if no match found
    return "us"

def get_user_country_from_db(user_id):
    """
    Get user's country from database at users/{user_id}/country.
    
    Args:
        user_id (str): User ID
    
    Returns:
        str: Country code (e.g., 'us', 'fr', 'de')
    """
    try:
        db_client = firestore.client()
        user_doc = db_client.collection('users').document(user_id).get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            country = user_data.get('country')
            
            if country:
                # Convert country name/code to standard code
                country_code = get_country_code(country)
                logger.info(f"User {user_id} country: {country} → {country_code}")
                return country_code
        
        logger.warning(f"No country found for user {user_id}, defaulting to 'us'")
        return "us"
        
    except Exception as e:
        logger.error(f"Error fetching user country for {user_id}: {e}")
        return "us" 