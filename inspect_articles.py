#!/usr/bin/env python3

import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    """Initialize Firebase if not already done."""
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()

def inspect_user_articles():
    print("🔍 INSPECTION DES ARTICLES UTILISATEUR")
    print("=" * 60)
    
    user_id = "GDofaXAIvnPp5jjSF2D1FHuPfly1"
    print(f"👤 User ID: {user_id}")
    print()
    
    try:
        # Get user articles
        db = initialize_firebase()
        user_doc_ref = db.collection('articles').document(user_id)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            print("❌ Aucun document trouvé")
            return
        
        data = user_doc.to_dict()
        topics_data = data.get("topics_data", {})
        
        print(f"📊 Document trouvé avec {len(topics_data)} topics")
        print(f"🕒 Dernière mise à jour: {data.get('refresh_timestamp', 'N/A')}")
        print()
        
        for topic_name, topic_info in topics_data.items():
            print(f"📁 TOPIC: {topic_name.upper()}")
            print("-" * 50)
            
            if not topic_info.get("success"):
                print("❌ Topic non récupéré avec succès")
                continue
            
            topic_data = topic_info.get("data", {})
            
            # Examine topic headlines
            topic_headlines = topic_data.get("topic_headlines", [])
            print(f"📰 Topic Headlines: {len(topic_headlines)} articles")
            
            for i, article in enumerate(topic_headlines[:3], 1):  # Show first 3
                title = article.get("title", "Pas de titre")
                source = article.get("source", "Source inconnue")
                published = article.get("published_date", "Date inconnue")
                print(f"  {i}. {title[:100]}...")
                print(f"     📍 Source: {source} | 📅 {published}")
                
                # Show content preview if available
                content = article.get("content", article.get("description", ""))
                if content:
                    print(f"     📝 Contenu: {content[:150]}...")
                print()
            
            # Examine subtopics
            subtopics = topic_data.get("subtopics", {})
            print(f"📂 Subtopics: {len(subtopics)} sous-sujets")
            
            for subtopic_name, subtopic_data in subtopics.items():
                print(f"\n  🔸 SUBTOPIC: {subtopic_name}")
                
                # Subtopic articles
                subtopic_articles = subtopic_data.get(subtopic_name, [])
                print(f"    📰 Articles directs: {len(subtopic_articles)}")
                
                for i, article in enumerate(subtopic_articles[:2], 1):  # Show first 2
                    title = article.get("title", "Pas de titre")
                    source = article.get("source", "Source inconnue")
                    print(f"      {i}. {title[:80]}...")
                    print(f"         📍 {source}")
                
                # Query articles
                queries = subtopic_data.get("queries", {})
                if queries:
                    print(f"    🔍 Query articles: {len(queries)} requêtes")
                    for query_name, query_articles in queries.items():
                        print(f"      📋 Query '{query_name}': {len(query_articles)} articles")
                        for i, article in enumerate(query_articles[:1], 1):  # Show first 1
                            title = article.get("title", "Pas de titre")
                            print(f"        • {title[:60]}...")
                
                # Reddit posts
                subreddits = subtopic_data.get("subreddits", {})
                if subreddits:
                    print(f"    🔴 Reddit posts: {len(subreddits)} subreddits")
                    for subreddit_name, posts in subreddits.items():
                        print(f"      📋 r/{subreddit_name}: {len(posts)} posts")
                        for i, post in enumerate(posts[:1], 1):  # Show first 1
                            title = post.get("title", "Pas de titre")
                            score = post.get("score", 0)
                            print(f"        • {title[:60]}... (Score: {score})")
                
                print()
            
            print("=" * 50)
            print()
        
        # Show summary stats
        print("📊 RÉSUMÉ STATISTIQUES:")
        summary = data.get("summary", {})
        print(f"  • Topics traités: {summary.get('topics_processed', 'N/A')}")
        print(f"  • Total articles: {summary.get('total_articles', 'N/A')}")
        print(f"  • Total posts Reddit: {summary.get('total_posts', 'N/A')}")
        print(f"  • Langue: {summary.get('language', 'N/A')}")
        print(f"  • Pays: {summary.get('country', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_user_articles() 