"""
Test de la fonction serpapi_google_news_search améliorée avec NewsAPI
Stratégie à 3 niveaux : GNews → NewsAPI → SerpAPI
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.news.serpapi import serpapi_google_news_search
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_search():
    """Test de la stratégie de fallback à 3 niveaux"""
    
    print("🚀 Test de la stratégie de fallback améliorée")
    print("=" * 60)
    print("📋 Stratégie : GNews → NewsAPI (48h) → SerpAPI")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "🔍 Test 1: Query AI (max 3 articles)",
            "query": "artificial intelligence",
            "max_articles": 3,
            "gl": "us",
            "hl": "en"
        },
        {
            "name": "🔍 Test 2: Query Tech (max 8 articles)",
            "query": "technology news",
            "max_articles": 8,
            "gl": "us", 
            "hl": "en"
        },
        {
            "name": "🔍 Test 3: Query français (max 5 articles)",
            "query": "intelligence artificielle",
            "max_articles": 5,
            "gl": "fr",
            "hl": "fr"
        },
        {
            "name": "🏠 Test 4: Homepage browsing (pas de query)",
            "query": None,
            "max_articles": 5,
            "gl": "us",
            "hl": "en"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print("-" * 50)
        
        try:
            result = serpapi_google_news_search(
                query=test_case['query'],
                gl=test_case['gl'],
                hl=test_case['hl'],
                max_articles=test_case['max_articles']
            )
            
            # Afficher les résultats
            print(f"✅ Succès: {result.get('success')}")
            print(f"📊 Articles obtenus: {result.get('totalArticles')}/{test_case['max_articles']}")
            print(f"🎯 Source finale: {result.get('source', 'unknown')}")
            
            # Détail par source
            gnews_count = result.get('gnews_count', 0)
            newsapi_count = result.get('newsapi_count', 0)
            serpapi_count = result.get('serpapi_count', 0)
            
            print(f"📈 Détail des sources:")
            print(f"   🔹 GNews: {gnews_count} articles")
            print(f"   🔹 NewsAPI: {newsapi_count} articles")
            print(f"   🔹 SerpAPI: {serpapi_count} articles")
            
            # Vérifications
            total_from_sources = gnews_count + newsapi_count + serpapi_count
            if total_from_sources != result.get('totalArticles', 0):
                print(f"⚠️ Attention: Incohérence dans le décompte")
            
            # Afficher les fallbacks utilisés
            if result.get('used_us_fallback'):
                print(f"🔄 Fallback US utilisé pour GNews")
                
            # Afficher quelques titres d'articles
            articles = result.get('articles', [])
            if articles:
                print(f"📰 Premiers articles:")
                for j, article in enumerate(articles[:2], 1):
                    title = article.get('title', 'Pas de titre')[:60] + '...' if len(article.get('title', '')) > 60 else article.get('title', '')
                    source = article.get('source', {}).get('name', 'Source inconnue')
                    print(f"   {j}. {title} | {source}")
            
            if result.get('error'):
                print(f"❌ Erreur: {result.get('error')}")
                
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    print(f"\n🎉 Tests terminés!")
    print(f"\n📊 Résumé de la stratégie:")
    print(f"1️⃣ GNews: Première tentative (rapide, gratuite)")
    print(f"2️⃣ NewsAPI: Complément 48h (précis, API tierce)")
    print(f"3️⃣ SerpAPI: Fallback final (robuste, payant)")
    print(f"\n✨ Avantages:")
    print(f"   • Optimisation des quotas APIs payantes")
    print(f"   • Diversification des sources")
    print(f"   • Robustesse en cas d'échec")
    print(f"   • Articles récents garantis (NewsAPI 48h)")

def analyze_source_performance():
    """Analyse de performance par source"""
    
    print(f"\n🔬 Analyse de performance des sources")
    print("=" * 50)
    
    queries = ["python programming", "climate change", "space exploration"]
    results = {}
    
    for query in queries:
        print(f"\n🔍 Test query: '{query}'")
        result = serpapi_google_news_search(
            query=query,
            max_articles=10,
            gl="us",
            hl="en"
        )
        
        results[query] = {
            'gnews': result.get('gnews_count', 0),
            'newsapi': result.get('newsapi_count', 0), 
            'serpapi': result.get('serpapi_count', 0),
            'total': result.get('totalArticles', 0),
            'source': result.get('source', 'unknown')
        }
        
        print(f"   📊 GNews: {results[query]['gnews']}")
        print(f"   📰 NewsAPI: {results[query]['newsapi']}")
        print(f"   🌐 SerpAPI: {results[query]['serpapi']}")
        print(f"   🎯 Total: {results[query]['total']} | Source: {results[query]['source']}")
    
    # Statistiques globales
    total_gnews = sum(r['gnews'] for r in results.values())
    total_newsapi = sum(r['newsapi'] for r in results.values())
    total_serpapi = sum(r['serpapi'] for r in results.values())
    total_all = sum(r['total'] for r in results.values())
    
    print(f"\n📈 Statistiques globales:")
    print(f"   🔹 GNews: {total_gnews}/{total_all} articles ({total_gnews/total_all*100:.1f}%)")
    print(f"   🔹 NewsAPI: {total_newsapi}/{total_all} articles ({total_newsapi/total_all*100:.1f}%)")
    print(f"   🔹 SerpAPI: {total_serpapi}/{total_all} articles ({total_serpapi/total_all*100:.1f}%)")

if __name__ == "__main__":
    test_enhanced_search()
    analyze_source_performance() 