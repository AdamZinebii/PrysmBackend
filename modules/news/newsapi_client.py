"""
Module NewsAPI pour l'intégration dans Prysm Backend
Basé sur la documentation: https://newsapi.org/docs
"""

import requests
import logging
from datetime import datetime, timedelta
from ..config import get_newsapi_key

logger = logging.getLogger(__name__)

class NewsAPIClient:
    """Client NewsAPI intégré pour Prysm"""
    
    def __init__(self):
        self.api_key = get_newsapi_key()
        self.base_url = "https://newsapi.org/v2"
        
    def search_news_48h(self, query=None, sources=None, language='en', sort_by='publishedAt', max_articles=50):
        """
        Recherche d'articles publiés dans les dernières 48 heures (compatible avec format Prysm)
        
        Args:
            query (str): Terme de recherche
            sources (str): Sources séparées par virgules
            language (str): Code langue
            sort_by (str): Tri ('relevancy', 'popularity', 'publishedAt')
            max_articles (int): Nombre max d'articles
            
        Returns:
            dict: Réponse formatée pour Prysm
        """
        
        # Calculer la période des dernières 48h
        now = datetime.utcnow()
        from_date = now - timedelta(hours=48)
        
        from_iso = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        to_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logger.info(f"🔍 NewsAPI Search: {query or 'General'} | {language} | Period: {from_iso}-{to_iso}")
        
        # Paramètres de la requête
        params = {
            'apiKey': self.api_key,
            'from': from_iso,
            'to': to_iso,
            'language': language,
            'sortBy': sort_by,
            'pageSize': min(max_articles, 100)  # NewsAPI limite à 100
        }
        
        if query:
            params['q'] = query
            
        if sources:
            params['sources'] = sources
        
        try:
            url = f"{self.base_url}/everything"
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                # Convertir au format Prysm
                formatted_articles = []
                for article in articles[:max_articles]:
                    formatted_article = self._format_article_for_prysm(article)
                    if formatted_article:
                        formatted_articles.append(formatted_article)
                
                logger.info(f"✅ NewsAPI: {len(formatted_articles)} articles retrieved")
                
                return {
                    "success": True,
                    "totalArticles": len(formatted_articles),
                    "articles": formatted_articles,
                    "source": "newsapi",
                    "time_period": f"{from_iso} to {to_iso}",
                    "query_used": query,
                    "language": language
                }
                
            elif response.status_code == 401:
                logger.error("❌ NewsAPI: Invalid API key")
                return {
                    "success": False,
                    "error": "NewsAPI authentication failed",
                    "totalArticles": 0,
                    "articles": []
                }
                
            elif response.status_code == 429:
                logger.error("❌ NewsAPI: Rate limit exceeded")
                return {
                    "success": False,
                    "error": "NewsAPI rate limit exceeded",
                    "totalArticles": 0,
                    "articles": []
                }
                
            else:
                logger.error(f"❌ NewsAPI: HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"NewsAPI HTTP error {response.status_code}",
                    "totalArticles": 0,
                    "articles": []
                }
                
        except Exception as e:
            logger.error(f"❌ NewsAPI request failed: {e}")
            return {
                "success": False,
                "error": f"NewsAPI request failed: {str(e)}",
                "totalArticles": 0,
                "articles": []
            }
    
    def get_top_headlines(self, country='us', category=None, sources=None, max_articles=50):
        """
        Récupère les gros titres et les filtre pour les dernières 48h
        
        Args:
            country (str): Code pays
            category (str): Catégorie de news
            sources (str): Sources spécifiques
            max_articles (int): Nombre max d'articles
            
        Returns:
            dict: Réponse formatée pour Prysm
        """
        
        logger.info(f"📰 NewsAPI Headlines: {country} | {category or 'all'}")
        
        params = {
            'apiKey': self.api_key,
            'pageSize': min(max_articles, 100)
        }
        
        if country and not sources:
            params['country'] = country
            
        if category:
            params['category'] = category
            
        if sources:
            params['sources'] = sources
        
        try:
            url = f"{self.base_url}/top-headlines"
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Filtrer pour les dernières 48h
                now = datetime.utcnow()
                from_date = now - timedelta(hours=48)
                
                filtered_articles = []
                for article in data.get('articles', []):
                    pub_date_str = article.get('publishedAt')
                    if pub_date_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                            pub_date_utc = pub_date.replace(tzinfo=None)
                            
                            if pub_date_utc >= from_date:
                                formatted_article = self._format_article_for_prysm(article)
                                if formatted_article:
                                    filtered_articles.append(formatted_article)
                        except:
                            # Include article if date parsing fails
                            formatted_article = self._format_article_for_prysm(article)
                            if formatted_article:
                                filtered_articles.append(formatted_article)
                
                filtered_articles = filtered_articles[:max_articles]
                logger.info(f"✅ NewsAPI Headlines: {len(filtered_articles)} articles (48h filtered)")
                
                return {
                    "success": True,
                    "totalArticles": len(filtered_articles),
                    "articles": filtered_articles,
                    "source": "newsapi_headlines",
                    "country": country,
                    "category": category,
                    "filtered_48h": True
                }
                
            else:
                logger.error(f"❌ NewsAPI Headlines: HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"NewsAPI Headlines error {response.status_code}",
                    "totalArticles": 0,
                    "articles": []
                }
                
        except Exception as e:
            logger.error(f"❌ NewsAPI Headlines failed: {e}")
            return {
                "success": False,
                "error": f"NewsAPI Headlines failed: {str(e)}",
                "totalArticles": 0,
                "articles": []
            }
    
    def _format_article_for_prysm(self, newsapi_article):
        """
        Convertit un article NewsAPI au format Prysm standard
        
        Args:
            newsapi_article (dict): Article NewsAPI
            
        Returns:
            dict: Article formaté pour Prysm
        """
        try:
            # Extraire les informations de base
            title = newsapi_article.get('title', '').strip()
            url = newsapi_article.get('url', '').strip()
            description = newsapi_article.get('description', '').strip()
            content = newsapi_article.get('content', '').strip()
            
            # Informations de source
            source_info = newsapi_article.get('source', {})
            source_name = source_info.get('name', 'Unknown Source')
            
            # Image et dates
            image = newsapi_article.get('urlToImage', '')
            published_at = newsapi_article.get('publishedAt', '')
            author = newsapi_article.get('author', '')
            
            # Vérifier que l'article a les informations minimales requises
            if not title or not url:
                return None
            
            # Format Prysm standard
            formatted_article = {
                'title': title,
                'link': url,
                'source': source_name,
                'published': published_at,
                'snippet': description or content[:200] + '...' if content else '',
                'thumbnail': image,
                'content': content,
                'author': author
            }
            
            # Nettoyer les champs vides
            formatted_article = {k: v for k, v in formatted_article.items() if v}
            
            return formatted_article
            
        except Exception as e:
            logger.error(f"❌ Error formatting NewsAPI article: {e}")
            return None

# Fonctions d'interface pour compatibilité avec le système existant
def newsapi_search(query, lang="en", country="us", max_articles=10, time_period="48h"):
    """
    Interface de recherche NewsAPI compatible avec le système Prysm
    
    Args:
        query (str): Terme de recherche
        lang (str): Code langue
        country (str): Code pays
        max_articles (int): Nombre max d'articles
        time_period (str): Période (pour compatibilité, toujours 48h)
        
    Returns:
        dict: Résultat formaté pour Prysm
    """
    client = NewsAPIClient()
    return client.search_news_48h(
        query=query,
        language=lang,
        max_articles=max_articles
    )

def newsapi_top_headlines(category="general", lang="en", country="us", max_articles=10):
    """
    Interface des gros titres NewsAPI compatible avec le système Prysm
    
    Args:
        category (str): Catégorie de news
        lang (str): Code langue
        country (str): Code pays
        max_articles (int): Nombre max d'articles
        
    Returns:
        dict: Résultat formaté pour Prysm
    """
    client = NewsAPIClient()
    
    # Mappage des catégories si nécessaire
    newsapi_category = None if category == "general" else category
    
    return client.get_top_headlines(
        country=country,
        category=newsapi_category,
        max_articles=max_articles
    )

def format_newsapi_articles_for_prysm(newsapi_response):
    """
    Convertit une réponse NewsAPI au format Prysm (pour compatibilité)
    
    Args:
        newsapi_response (dict): Réponse NewsAPI
        
    Returns:
        list: Liste d'articles formatés pour Prysm
    """
    if not newsapi_response.get("success") or not newsapi_response.get("articles"):
        return []
    
    return newsapi_response["articles"] 