#!/usr/bin/env python3
"""
Test DIRECT de l'API GNews.io (pas le système hybride)
Pour voir exactement ce que retourne l'API GNews pure
"""

import requests
import json
import argparse
from datetime import datetime, timedelta

# Clé API GNews directement depuis le main.py
GNEWS_API_KEY = "75807d7923a12e3d80d64c971ff340da"
GNEWS_BASE_URL = "https://gnews.io/api/v4"

def test_gnews_direct_search(query, lang="fr", country="fr", max_articles=5):
    """
    Test direct de l'API GNews.io pour voir ce qu'elle retourne
    """
    print(f"🔍 Test GNews DIRECT: '{query}'")
    print(f"   📍 Langue: {lang} | Pays: {country} | Max: {max_articles}")
    print("-" * 50)
    
    url = f"{GNEWS_BASE_URL}/search"
    params = {
        "q": query,
        "lang": lang,
        "country": country,
        "max": max_articles,
        "apikey": GNEWS_API_KEY
    }
    
    try:
        print(f"📡 Appel API: {url}")
        print(f"📋 Paramètres: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"🔢 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Réponse reçue!")
            print(f"📊 Structure de la réponse:")
            print(f"   - Keys: {list(data.keys())}")
            
            if 'articles' in data:
                articles = data['articles']
                print(f"   - Nombre d'articles: {len(articles)}")
                
                if articles:
                    print(f"\n📰 Premier article:")
                    first_article = articles[0]
                    for key, value in first_article.items():
                        if isinstance(value, str):
                            print(f"   - {key}: {value[:100]}...")
                        else:
                            print(f"   - {key}: {value}")
                
                print(f"\n📋 Structure complète de la réponse:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1500] + "...")
                
            return data
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📝 Réponse: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_gnews_direct_with_24h_limit(query, lang="fr", country="fr", max_articles=5):
    """
    Test GNews direct avec limite 24h
    """
    print(f"\n🕒 Test GNews DIRECT avec limite 24h")
    print(f"   🔍 Query: '{query}' | 📍 {lang}/{country}")
    print("=" * 60)
    
    # Date d'il y a 24h 
    from_date = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    url = f"{GNEWS_BASE_URL}/search"
    params = {
        "q": query,
        "lang": lang,
        "country": country, 
        "max": max_articles,
        "from": from_date,  # Paramètre de date GNews
        "apikey": GNEWS_API_KEY
    }
    
    try:
        print(f"📅 Date limite: {from_date}")
        print(f"📡 Appel API: {url}")
        print(f"📋 Paramètres: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"🔢 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Réponse avec limite 24h reçue!")
            print(f"📊 Articles trouvés: {len(data.get('articles', []))}")
            
            if data.get('articles'):
                for i, article in enumerate(data['articles'][:3], 1):
                    title = article.get('title', 'N/A')
                    published = article.get('publishedAt', 'N/A')
                    print(f"   {i}. {title[:80]}...")
                    print(f"      📅 Publié: {published}")
            
            return data
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📝 Réponse: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_gnews_direct_top_headlines(lang="fr", country="fr", max_articles=5):
    """
    Test GNews direct pour les top headlines
    """
    print(f"\n📰 Test GNews DIRECT - Top Headlines")
    print(f"   📍 Langue: {lang} | Pays: {country}")
    print("=" * 60)
    
    url = f"{GNEWS_BASE_URL}/top-headlines"
    params = {
        "lang": lang,
        "country": country,
        "max": max_articles,
        "apikey": GNEWS_API_KEY
    }
    
    try:
        print(f"📡 Appel API: {url}")
        print(f"📋 Paramètres: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        
        print(f"🔢 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Top headlines reçus!")
            print(f"📊 Articles trouvés: {len(data.get('articles', []))}")
            
            if data.get('articles'):
                for i, article in enumerate(data['articles'][:3], 1):
                    title = article.get('title', 'N/A')
                    source = article.get('source', {}).get('name', 'N/A')
                    print(f"   {i}. {title[:80]}...")
                    print(f"      📰 Source: {source}")
            
            return data
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📝 Réponse: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_different_time_limits(query, lang="fr", country="fr"):
    """
    Test GNews avec différentes limites de temps
    """
    print(f"\n⏰ Test GNews DIRECT - Différentes limites temporelles")
    print(f"   🔍 Query: '{query}' | 📍 {lang}/{country}")
    print("=" * 70)
    
    time_tests = [
        ("1 heure", timedelta(hours=1)),
        ("6 heures", timedelta(hours=6)), 
        ("24 heures", timedelta(hours=24)),
        ("3 jours", timedelta(days=3)),
        ("1 semaine", timedelta(days=7))
    ]
    
    for desc, delta in time_tests:
        print(f"\n🕒 Test: {desc}")
        print("-" * 30)
        
        from_date = (datetime.now() - delta).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        url = f"{GNEWS_BASE_URL}/search"
        params = {
            "q": query,
            "lang": lang,
            "country": country,
            "max": 3,
            "from": from_date,
            "apikey": GNEWS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles_count = len(data.get('articles', []))
                print(f"✅ {articles_count} articles trouvés depuis {desc}")
                
                if data.get('articles'):
                    latest = data['articles'][0]
                    print(f"   📰 Plus récent: {latest.get('title', 'N/A')[:60]}...")
                    print(f"   📅 Publié: {latest.get('publishedAt', 'N/A')}")
            else:
                print(f"❌ Erreur: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")

def get_user_input():
    """
    Demande les paramètres à l'utilisateur
    """
    print("🔧 Configuration du test")
    print("-" * 30)
    
    query = input("🔍 Query (recherche): ").strip()
    if not query:
        query = "intelligence artificielle"
        print(f"   → Utilisation par défaut: '{query}'")
    
    lang = input("🌍 Langue (ex: fr, en, es): ").strip().lower()
    if not lang:
        lang = "fr"
        print(f"   → Utilisation par défaut: {lang}")
    
    country = input("🏳️ Pays (ex: fr, us, gb): ").strip().lower()
    if not country:
        country = "fr"  
        print(f"   → Utilisation par défaut: {country}")
    
    max_articles = input("📊 Nombre max d'articles (défaut: 5): ").strip()
    try:
        max_articles = int(max_articles) if max_articles else 5
    except:
        max_articles = 5
        print(f"   → Utilisation par défaut: {max_articles}")
    
    return query, lang, country, max_articles

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tests directs de l'API GNews.io")
    parser.add_argument("-q", "--query", help="Query de recherche")
    parser.add_argument("-l", "--lang", help="Langue (ex: fr, en, es)", default="fr")
    parser.add_argument("-c", "--country", help="Pays (ex: fr, us, gb)", default="fr")
    parser.add_argument("-m", "--max", type=int, help="Nombre max d'articles", default=5)
    parser.add_argument("-i", "--interactive", action="store_true", help="Mode interactif")
    
    args = parser.parse_args()
    
    print("🚀 Tests DIRECTS de l'API GNews.io")
    print("=" * 60)
    print("⚠️  Ces tests appellent directement GNews.io, pas le système hybride!")
    print()
    
    # Mode interactif ou arguments
    if args.interactive or not args.query:
        query, lang, country, max_articles = get_user_input()
    else:
        query = args.query
        lang = args.lang
        country = args.country
        max_articles = args.max
    
    print(f"\n🎯 Configuration:")
    print(f"   🔍 Query: '{query}'")
    print(f"   🌍 Langue: {lang}")
    print(f"   🏳️ Pays: {country}")
    print(f"   📊 Max articles: {max_articles}")
    print()
    
    # Test 1: Recherche basique
    result1 = test_gnews_direct_search(query, lang, country, max_articles)
    
    # Test 2: Avec limite 24h
    result2 = test_gnews_direct_with_24h_limit(query, lang, country, max_articles)
    
    # Test 3: Top headlines
    result3 = test_gnews_direct_top_headlines(lang, country, max_articles)
    
    # Test 4: Différentes limites temporelles
    test_different_time_limits(query, lang, country)
    
    print(f"\n✨ Tests directs GNews terminés!")
    print("🔍 Tu peux voir exactement ce que retourne l'API GNews pure") 