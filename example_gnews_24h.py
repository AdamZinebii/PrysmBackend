#!/usr/bin/env python3
"""
Script d'exemple pour tester la fonctionnalité GNews avec limite de 24h
Usage: python example_gnews_24h.py
"""

import sys
import os
from datetime import datetime, timedelta

# Ajouter le main au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import gnews_search, gnews_top_headlines, format_gnews_articles_for_prysm

def test_gnews_24h_limit():
    """
    Teste la fonctionnalité GNews avec différentes limites temporelles
    """
    print("🔍 Test GNews avec limites temporelles")
    print("=" * 50)
    
    # Test 1: Articles des dernières 24 heures
    print("\n1️⃣ Articles des dernières 24 heures")
    print("-" * 40)
    
    # Date d'il y a 24 heures
    from_date_24h = (datetime.now() - timedelta(hours=24)).isoformat() + "Z"
    
    try:
        result_24h = gnews_search(
            query="intelligence artificielle",
            lang="fr", 
            country="fr",
            max_articles=5,
            from_date=from_date_24h
        )
        
        print(f"✅ Succès: {result_24h.get('success', False)}")
        print(f"📊 Articles trouvés: {result_24h.get('totalArticles', 0)}")
        print(f"🔧 Source utilisée: {result_24h.get('source', 'unknown')}")
        
        if result_24h.get('articles'):
            print(f"📰 Premier article: {result_24h['articles'][0].get('title', 'N/A')[:80]}...")
            
        # Afficher le fallback si utilisé
        if result_24h.get('used_fallback'):
            print(f"🔄 Fallback utilisé (période originale: {result_24h.get('original_time_period')})")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 2: Articles de la dernière heure 
    print("\n2️⃣ Articles de la dernière heure")
    print("-" * 40)
    
    from_date_1h = (datetime.now() - timedelta(hours=1)).isoformat() + "Z"
    
    try:
        result_1h = gnews_search(
            query="actualités urgentes",
            lang="fr",
            country="fr", 
            max_articles=3,
            from_date=from_date_1h
        )
        
        print(f"✅ Succès: {result_1h.get('success', False)}")
        print(f"📊 Articles trouvés: {result_1h.get('totalArticles', 0)}")
        print(f"🔧 Source utilisée: {result_1h.get('source', 'unknown')}")
        
        if result_1h.get('articles'):
            for i, article in enumerate(result_1h['articles'][:2], 1):
                title = article.get('title', 'N/A')[:60]
                print(f"   {i}. {title}...")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 3: Articles de la dernière semaine
    print("\n3️⃣ Articles de la dernière semaine")  
    print("-" * 40)
    
    from_date_1w = (datetime.now() - timedelta(days=7)).isoformat() + "Z"
    
    try:
        result_1w = gnews_search(
            query="technologie France",
            lang="fr",
            country="fr",
            max_articles=4,
            from_date=from_date_1w
        )
        
        print(f"✅ Succès: {result_1w.get('success', False)}")
        print(f"📊 Articles trouvés: {result_1w.get('totalArticles', 0)}")
        print(f"🔧 Source utilisée: {result_1w.get('source', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 4: Top headlines actuels
    print("\n4️⃣ Top headlines technologie")
    print("-" * 40)
    
    try:
        headlines = gnews_top_headlines(
            category="technology",
            lang="fr",
            country="fr",
            max_articles=3
        )
        
        print(f"✅ Succès: {headlines.get('success', False)}")
        print(f"📊 Articles trouvés: {headlines.get('totalArticles', 0)}")
        print(f"🏷️ Catégorie: {headlines.get('category', 'N/A')}")
        
        if headlines.get('articles'):
            for i, article in enumerate(headlines['articles'][:2], 1):
                title = article.get('title', 'N/A')[:60]
                print(f"   {i}. {title}...")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 5: Formatage pour Prysm
    print("\n5️⃣ Test formatage Prysm")
    print("-" * 40)
    
    try:
        # Utiliser le résultat du test 1
        if 'result_24h' in locals() and result_24h.get('success'):
            formatted = format_gnews_articles_for_prysm(result_24h)
            print(f"📝 Articles formatés: {len(formatted)}")
            
            if formatted:
                article = formatted[0]
                print(f"   📰 Titre: {article.get('title', 'N/A')[:50]}...")
                print(f"   🔗 Lien: {article.get('link', 'N/A')[:50]}...")
                print(f"   📅 Publié: {article.get('published', 'N/A')}")
                print(f"   📰 Source: {article.get('source', 'N/A')}")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Tests terminés!")

def test_time_period_mapping():
    """
    Teste le mapping des périodes temporelles
    """
    print("\n🕒 Test mapping périodes temporelles")
    print("=" * 50)
    
    test_cases = [
        ("30 minutes", timedelta(minutes=30), "h"),
        ("2 heures", timedelta(hours=2), "d"), 
        ("12 heures", timedelta(hours=12), "d"),
        ("3 jours", timedelta(days=3), "w"),
        ("1 semaine", timedelta(days=7), "w"),
        ("2 semaines", timedelta(days=14), None)  # Plus de 1 semaine
    ]
    
    for description, delta, expected_period in test_cases:
        from_date = (datetime.now() - delta).isoformat() + "Z"
        
        print(f"\n📅 Test: {description}")
        print(f"   Date: {from_date}")
        print(f"   Période attendue: {expected_period or 'None (tout temps)'}")
        
        # Note: Ce test nécessiterait de mocker la fonction pour voir le time_period
        # En mode réel, on verrait le comportement dans les logs

if __name__ == "__main__":
    print("🚀 Démarrage des tests GNews avec limite 24h")
    print("⚠️  Ces tests utilisent les vraies APIs - attention aux quotas!")
    
    # Vérifier que les clés API sont disponibles
    try:
        from main import get_serpapi_key
        api_key = get_serpapi_key()
        if api_key:
            print(f"✅ Clé SerpAPI disponible: {api_key[:10]}...")
        else:
            print("❌ Aucune clé SerpAPI trouvée")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur lors de la vérification de la clé: {e}")
        sys.exit(1)
    
    # Exécuter les tests
    test_gnews_24h_limit()
    test_time_period_mapping()
    
    print("\n✨ Tous les tests sont terminés!") 