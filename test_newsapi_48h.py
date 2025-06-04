"""
Test NewsAPI pour récupérer les articles des dernières 48 heures
Documentation: https://newsapi.org/docs
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# Ajouter le module au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.config import get_newsapi_key
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsAPIClient:
    """Client pour interagir avec NewsAPI"""
    
    def __init__(self):
        self.api_key = get_newsapi_key()
        self.base_url = "https://newsapi.org/v2"
        
    def search_everything_48h(self, query=None, sources=None, language='en', sort_by='publishedAt', page_size=100):
        """
        Recherche d'articles publiés dans les dernières 48 heures
        
        Args:
            query (str): Terme de recherche (optionnel)
            sources (str): Sources spécifiques séparées par virgules (optionnel)
            language (str): Code de langue (en, fr, es, etc.)
            sort_by (str): Tri par 'relevancy', 'popularity', ou 'publishedAt'
            page_size (int): Nombre d'articles par page (max 100)
            
        Returns:
            dict: Réponse de l'API avec les articles
        """
        
        # Calculer les dates des dernières 48 heures
        now = datetime.utcnow()
        from_date = now - timedelta(hours=48)
        
        # Format ISO 8601 requis par NewsAPI
        from_iso = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        to_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logger.info(f"🔍 Recherche NewsAPI - Période: {from_iso} à {to_iso}")
        
        # Paramètres de la requête
        params = {
            'apiKey': self.api_key,
            'from': from_iso,
            'to': to_iso,
            'language': language,
            'sortBy': sort_by,
            'pageSize': page_size
        }
        
        # Ajouter query si spécifié
        if query:
            params['q'] = query
            logger.info(f"🔍 Query: '{query}'")
            
        # Ajouter sources si spécifiées
        if sources:
            params['sources'] = sources
            logger.info(f"📰 Sources: {sources}")
        
        try:
            # Appel à l'endpoint /everything
            url = f"{self.base_url}/everything"
            response = requests.get(url, params=params, timeout=30)
            
            logger.info(f"🌐 Requête: {url}")
            logger.info(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                total_results = data.get('totalResults', 0)
                articles_count = len(data.get('articles', []))
                
                logger.info(f"✅ Succès: {articles_count} articles récupérés sur {total_results} totaux")
                
                return {
                    'success': True,
                    'status': data.get('status'),
                    'totalResults': total_results,
                    'articlesReturned': articles_count,
                    'articles': data.get('articles', []),
                    'time_period': f"{from_iso} à {to_iso}",
                    'query_used': query,
                    'sources_used': sources
                }
                
            elif response.status_code == 401:
                logger.error("❌ Erreur 401: Clé API invalide ou manquante")
                return {
                    'success': False,
                    'error': 'Invalid API key',
                    'status_code': 401
                }
                
            elif response.status_code == 429:
                logger.error("❌ Erreur 429: Limite de taux dépassée")
                return {
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'status_code': 429
                }
                
            else:
                logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'status_code': response.status_code,
                    'response': response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout de la requête")
            return {
                'success': False,
                'error': 'Request timeout'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur de requête: {e}")
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    
    def get_top_headlines_48h(self, country='us', category=None, sources=None, page_size=100):
        """
        Récupère les gros titres des dernières 48 heures
        
        Args:
            country (str): Code pays (us, fr, gb, etc.)
            category (str): Catégorie (business, entertainment, general, health, science, sports, technology)
            sources (str): Sources spécifiques séparées par virgules
            page_size (int): Nombre d'articles par page (max 100)
            
        Returns:
            dict: Réponse de l'API avec les gros titres
        """
        
        logger.info(f"📰 Top Headlines - Pays: {country}, Catégorie: {category or 'toutes'}")
        
        # Paramètres de la requête
        params = {
            'apiKey': self.api_key,
            'pageSize': page_size
        }
        
        # Ajouter pays si spécifié (et pas de sources)
        if country and not sources:
            params['country'] = country
            
        # Ajouter catégorie si spécifiée
        if category:
            params['category'] = category
            
        # Ajouter sources si spécifiées
        if sources:
            params['sources'] = sources
        
        try:
            # Appel à l'endpoint /top-headlines
            url = f"{self.base_url}/top-headlines"
            response = requests.get(url, params=params, timeout=30)
            
            logger.info(f"🌐 Requête: {url}")
            logger.info(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Filtrer les articles des dernières 48 heures
                now = datetime.utcnow()
                from_date = now - timedelta(hours=48)
                
                filtered_articles = []
                for article in data.get('articles', []):
                    pub_date_str = article.get('publishedAt')
                    if pub_date_str:
                        try:
                            # Parser la date de publication
                            pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                            pub_date_utc = pub_date.replace(tzinfo=None)
                            
                            # Vérifier si l'article est dans les dernières 48h
                            if pub_date_utc >= from_date:
                                filtered_articles.append(article)
                        except:
                            # En cas d'erreur de parsing, inclure l'article
                            filtered_articles.append(article)
                    else:
                        # Si pas de date, inclure l'article
                        filtered_articles.append(article)
                
                total_results = len(filtered_articles)
                logger.info(f"✅ Succès: {total_results} gros titres des dernières 48h")
                
                return {
                    'success': True,
                    'status': data.get('status'),
                    'totalResults': total_results,
                    'articles': filtered_articles,
                    'country_used': country,
                    'category_used': category,
                    'sources_used': sources,
                    'filtered_for_48h': True
                }
                
            else:
                logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def format_article_summary(article):
    """Formate un résumé d'article pour l'affichage"""
    title = article.get('title', 'Pas de titre')
    source = article.get('source', {}).get('name', 'Source inconnue')
    published = article.get('publishedAt', 'Date inconnue')
    description = article.get('description', 'Pas de description')
    url = article.get('url', '#')
    
    return f"""
📰 {title}
📅 {published} | 🏢 {source}
📝 {description[:150]}{'...' if len(description) > 150 else ''}
🔗 {url}
---"""

def save_results_to_file(results, filename):
    """Sauvegarde les résultats dans un fichier JSON"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Résultats sauvegardés dans {filename}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde: {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Test NewsAPI - Articles des dernières 48 heures")
    print("=" * 60)
    
    # Initialiser le client
    client = NewsAPIClient()
    
    # Test 1: Recherche générale des dernières 48h
    print("\n🔍 Test 1: Recherche générale (toutes catégories)")
    results_general = client.search_everything_48h(
        query="technology OR science OR business",
        language='en',
        sort_by='publishedAt',
        page_size=20
    )
    
    if results_general['success']:
        print(f"✅ {results_general['articlesReturned']} articles trouvés")
        
        # Afficher les premiers articles
        for i, article in enumerate(results_general['articles'][:3]):
            print(format_article_summary(article))
            
        # Sauvegarder
        save_results_to_file(results_general, 'newsapi_general_48h.json')
    else:
        print(f"❌ Erreur: {results_general.get('error')}")
    
    # Test 2: Top headlines technologie
    print("\n📰 Test 2: Top Headlines - Technologie (US)")
    results_tech = client.get_top_headlines_48h(
        country='us',
        category='technology',
        page_size=15
    )
    
    if results_tech['success']:
        print(f"✅ {results_tech['totalResults']} gros titres tech trouvés")
        
        # Afficher les premiers articles
        for i, article in enumerate(results_tech['articles'][:3]):
            print(format_article_summary(article))
            
        # Sauvegarder
        save_results_to_file(results_tech, 'newsapi_tech_headlines_48h.json')
    else:
        print(f"❌ Erreur: {results_tech.get('error')}")
    
    # Test 3: Sources spécifiques
    print("\n🏢 Test 3: Sources spécifiques (TechCrunch, Ars Technica)")
    results_sources = client.search_everything_48h(
        sources='techcrunch,ars-technica',
        language='en',
        sort_by='publishedAt',
        page_size=10
    )
    
    if results_sources['success']:
        print(f"✅ {results_sources['articlesReturned']} articles de sources spécifiques")
        
        # Afficher les premiers articles
        for i, article in enumerate(results_sources['articles'][:2]):
            print(format_article_summary(article))
            
        # Sauvegarder
        save_results_to_file(results_sources, 'newsapi_sources_48h.json')
    else:
        print(f"❌ Erreur: {results_sources.get('error')}")
    
    print("\n🎉 Tests terminés! Consultez les fichiers JSON générés pour les détails complets.")

if __name__ == "__main__":
    main() 