import sys
import logging
import requests
from datetime import datetime

# Configure logging AS EARLY AS POSSIBLE
logger = logging.getLogger(__name__)

# Welcome to Cloud Functions for Firebase for Python!
# Implementation of the Prysm backend for news aggregation

from firebase_admin import firestore, storage

import json

from modules.ai.client import get_openai_client
from modules.audio.cartesia import generate_text_to_speech
from modules.content.generation import get_complete_topic_report, get_pickup_line, get_reddit_community_insights, get_topic_summary
from modules.database.operations import get_user_articles_from_db
from modules.audio.openai_tts import generate_text_to_speech_openai

logger.info("--- main.py: Logging configured ---")

def generate_media_twin_script(topic_name, topic_posts_data, presenter_name="Alex", language="fr"):
    """
    Génère un script conversationnel pour un media twin (jumeau média) qui présente l'actualité.
    
    Args:
        topic_name (str): Nom du sujet (e.g., "Business", "Technology")
        topic_posts_data (dict): Données complètes des articles (même format que get_complete_topic_report)
        presenter_name (str): Nom du présentateur virtuel
        language (str): Langue du script ("fr", "en", "es", "ar")
    
    Returns:
        dict: Script généré avec segments et métadonnées
    """
    try:
        logger.info(f"Generating media twin script for {topic_name} in {language}")
        
        if not topic_posts_data.get("success"):
            raise ValueError(f"Invalid topic posts data: {topic_posts_data.get('error', 'Unknown error')}")
        
        # Templates par langue
        language_templates = {
            'fr': {
                'greeting': [
                    f"Salut ! C'est {presenter_name}, et je suis là pour te tenir au courant de tout ce qui bouge",
                    f"Hello ! {presenter_name} ici, et j'ai du lourd à te partager aujourd'hui",
                    f"Hey ! C'est {presenter_name}, prêt(e) pour ta dose d'actu ?"
                ],
                'transition_to_topic': [
                    f"Alors, parlons de {topic_name.lower()}.",
                    f"Aujourd'hui, on va plonger dans {topic_name.lower()}.",
                    f"Concentrons-nous sur {topic_name.lower()}."
                ],
                'subtopic_intro': [
                    "Passons maintenant à",
                    "On va maintenant regarder",
                    "Intéressons-nous à"
                ],
                'conclusion': [
                    "Voilà pour cette mise à jour ! J'espère que ça t'a aidé à y voir plus clair.",
                    "Et c'est tout pour aujourd'hui ! On se retrouve bientôt pour de nouvelles actus.",
                    "Ça, c'était ta dose d'info du jour ! À très vite pour la suite."
                ]
            },
            'en': {
                'greeting': [
                    f"Hey there! It's {presenter_name}, and I'm here to keep you updated on everything that's happening",
                    f"Hello! {presenter_name} here, and I've got some serious updates to share with you today",
                    f"What's up! It's {presenter_name}, ready for your news dose?"
                ],
                'transition_to_topic': [
                    f"So, let's talk about {topic_name.lower()}.",
                    f"Today, we're diving into {topic_name.lower()}.",
                    f"Let's focus on {topic_name.lower()}."
                ],
                'subtopic_intro': [
                    "Now let's move on to",
                    "Let's now look at", 
                    "Let's focus on"
                ],
                'conclusion': [
                    "That's it for this update! Hope it helped you stay in the loop.",
                    "And that's all for today! See you soon for more news.",
                    "That was your daily info dose! Catch you later for more updates."
                ]
            }
        }
        
        templates = language_templates.get(language, language_templates['fr'])
        
        # Obtenir le rapport complet
        complete_report = get_complete_topic_report(topic_name, topic_posts_data)
        if not complete_report.get("success"):
            raise ValueError("Failed to generate complete report")
        
        data = topic_posts_data.get("data", {})
        subtopics_data = data.get("subtopics", {})
        
        # Compter le nombre total d'articles et posts
        total_articles = len(data.get("topic_headlines", []))
        total_reddit_posts = 0
        for subtopic_data in subtopics_data.values():
            for subreddit_posts in subtopic_data.get("subreddits", {}).values():
                total_reddit_posts += len(subreddit_posts)
        
        segments = []
        
        # SEGMENT 1: Introduction accrocheuse
        import random
        greeting = random.choice(templates['greeting'])
        pickup_line = complete_report.get("pickup_line", f"On a du mouvement dans {topic_name.lower()} aujourd'hui.")
        
        intro_content = f"{greeting} ! {pickup_line}"
        
        if total_articles > 0:
            if language == 'fr':
                intro_content += f" J'ai analysé {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" et {total_reddit_posts} discussions Reddit"
                intro_content += f" pour te donner le meilleur résumé possible."
            else:
                intro_content += f" I've analyzed {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" and {total_reddit_posts} Reddit discussions"
                intro_content += f" to give you the best summary possible."
        
        segments.append({
            "type": "intro",
            "content": intro_content,
            "duration_estimate": "30s"
        })
        
        # SEGMENT 2: Vue d'ensemble du sujet
        transition = random.choice(templates['transition_to_topic'])
        topic_summary = complete_report.get("topic_summary", "")
        
        # Convertir le summary en script conversationnel
        main_content = f"{transition} "
        
        # Extraire les points clés du summary et les rendre conversationnels
        if topic_summary:
            # Simplifier le markdown et rendre plus conversationnel
            cleaned_summary = topic_summary.replace("**", "").replace("*", "").replace("#", "")
            
            # Diviser en phrases et rendre plus naturel
            sentences = [s.strip() for s in cleaned_summary.split('.') if s.strip()]
            conversational_points = []
            
            for sentence in sentences[:5]:  # Limite à 5 points principaux
                if len(sentence) > 20:  # Éviter les fragments trop courts
                    # Rendre plus conversationnel
                    if language == 'fr':
                        if "Le" in sentence or "La" in sentence:
                            sentence = sentence.replace("Le ", "").replace("La ", "")
                        if not sentence.startswith(("Alors", "Donc", "En fait", "Bref")):
                            sentence = f"En fait, {sentence.lower()}"
                    conversational_points.append(sentence)
            
            main_content += " ".join(conversational_points[:3])  # 3 points principaux max
        
        segments.append({
            "type": "main_topic", 
            "content": main_content,
            "duration_estimate": "1-2min"
        })
        
        # SEGMENT 3: Détails par sous-sujets
        for i, (subtopic_name, subtopic_report) in enumerate(complete_report.get("subtopics", {}).items()):
            subtopic_intro = random.choice(templates['subtopic_intro'])
            
            subtopic_content = f"{subtopic_intro} {subtopic_name.lower()}. "
            
            # Résumer le contenu du sous-sujet de manière conversationnelle
            subtopic_summary = subtopic_report.get("subtopic_summary", "")
            reddit_summary = subtopic_report.get("reddit_summary", "")
            
            if subtopic_summary:
                # Extraire 2-3 points clés
                cleaned = subtopic_summary.replace("**", "").replace("*", "").replace("#", "")
                key_points = [s.strip() for s in cleaned.split('.') if s.strip() and len(s) > 20][:2]
                
                for point in key_points:
                    if language == 'fr':
                        subtopic_content += f" {point}."
                    else:
                        subtopic_content += f" {point}."
            
            # Ajouter l'insight Reddit si pertinent
            if reddit_summary and "No significant" not in reddit_summary and "unavailable" not in reddit_summary:
                if language == 'fr':
                    subtopic_content += f" Côté communauté, on voit que les gens parlent beaucoup de ça sur Reddit."
                else:
                    subtopic_content += f" On the community side, people are really talking about this on Reddit."
            
            segments.append({
                "type": "subtopic",
                "subtopic_name": subtopic_name,
                "content": subtopic_content,
                "duration_estimate": "1min"
            })
        
        # SEGMENT 4: Conclusion
        conclusion = random.choice(templates['conclusion'])
        if language == 'fr':
            conclusion += f" Si tu veux creuser plus, n'hésite pas à checker les sources. Bisous !"
        else:
            conclusion += f" If you want to dive deeper, feel free to check the sources. Take care!"
        
        segments.append({
            "type": "conclusion",
            "content": conclusion,
            "duration_estimate": "20s"
        })
        
        # Assembler le script complet
        full_script = "\n\n".join([segment["content"] for segment in segments])
        
        # Calculs des métadonnées
        word_count = len(full_script.split())
        estimated_duration = f"{max(6, word_count // 150)}-{word_count // 120} minutes"
        
        result = {
            "success": True,
            "script": full_script,
            "segments": segments,
            "metadata": {
                "topic_name": topic_name,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "total_duration_estimate": estimated_duration,
                "articles_analyzed": total_articles,
                "reddit_posts_analyzed": total_reddit_posts,
                "subtopics_covered": len(complete_report.get("subtopics", {}))
            },
            "generation_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Media twin script generated: {word_count} words, {len(segments)} segments")
        return result
        
    except Exception as e:
        logger.error(f"Error generating media twin script for {topic_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "script": f"Désolé, il y a eu un problème pour générer le script pour {topic_name}. On va réessayer plus tard !",
            "segments": [],
            "metadata": {}
        }

def generate_user_media_twin_script(user_id, presenter_name="Alex", language="fr"):
    """
    Génère un script conversationnel pour un media twin basé sur tous les articles d'un utilisateur.
    Utilise get_complete_report pour récupérer tous les sujets et articles de l'utilisateur.
    
    Args:
        user_id (str): ID de l'utilisateur
        presenter_name (str): Nom du présentateur virtuel
        language (str): Langue du script ("fr", "en", "es", "ar")
    
    Returns:
        dict: Script généré avec segments et métadonnées
    """
    try:
        logger.info(f"Generating user media twin script for user {user_id} in {language}")
        
        # Étape 1: Récupérer le rapport complet de l'utilisateur
        # Lazy import to avoid circular dependency
        from ..scheduling.tasks import get_complete_report
        
        complete_report = get_complete_report(user_id)
        
        if not complete_report.get("success"):
            raise ValueError(f"Failed to get complete report for user {user_id}: {complete_report.get('error', 'Unknown error')}")
        
        reports = complete_report.get("reports", {})
        if not reports:
            raise ValueError(f"No reports found for user {user_id}")
        
        # Templates par langue
        language_templates = {
            'fr': {
                'greeting': [
                    f"Salut ! C'est {presenter_name}, et j'ai préparé ton briefing personnalisé",
                    f"Hello ! {presenter_name} ici avec ta dose d'actu sur mesure",
                    f"Hey ! C'est {presenter_name}, prêt(e) pour ton résumé perso ?"
                ],
                'transition_global': [
                    "Alors, qu'est-ce qui se passe dans tes sujets favoris ?",
                    "Voyons ce qui bouge dans tes domaines d'intérêt.",
                    "Plongeons dans l'actu qui t'intéresse vraiment."
                ],
                'topic_transition': [
                    "Maintenant, côté",
                    "Passons à",
                    "On va voir ce qui se passe en"
                ],
                'subtopic_intro': [
                    "Plus spécifiquement sur",
                    "En détail sur",
                    "Zoom sur"
                ],
                'global_conclusion': [
                    "Et voilà pour ton briefing perso ! J'espère que ça t'aide à rester dans le game.",
                    "C'était ton résumé sur mesure ! À très bientôt pour la suite.",
                    "Ça, c'était ton actu personnalisée ! On se retrouve soon pour plus d'infos."
                ]
            },
            'en': {
                'greeting': [
                    f"Hey there! It's {presenter_name}, and I've prepared your personalized briefing",
                    f"Hello! {presenter_name} here with your custom news dose",
                    f"What's up! It's {presenter_name}, ready for your personal update?"
                ],
                'transition_global': [
                    "So, what's happening in your favorite topics?",
                    "Let's see what's moving in your areas of interest.",
                    "Let's dive into the news that really matters to you."
                ],
                'topic_transition': [
                    "Now, on the",
                    "Moving to",
                    "Let's see what's happening in"
                ],
                'subtopic_intro': [
                    "More specifically on",
                    "In detail about",
                    "Zooming in on"
                ],
                'global_conclusion': [
                    "And that's your personal briefing! Hope it helps you stay in the loop.",
                    "That was your custom summary! See you soon for more updates.",
                    "That was your personalized news! Catch you later for more insights."
                ]
            }
        }
        
        templates = language_templates.get(language, language_templates['fr'])
        
        # Compter les statistiques globales
        total_topics = len(reports)
        total_successful = complete_report.get("generation_stats", {}).get("successful_reports", 0)
        
        # Compter articles et posts Reddit
        total_articles = 0
        total_reddit_posts = 0
        
        for topic_name, topic_report in reports.items():
            subtopics = topic_report.get("subtopics", {})
            for subtopic_name, subtopic_data in subtopics.items():
                # Estimer le nombre d'articles basé sur le contenu
                summary = subtopic_data.get("subtopic_summary", "")
                reddit_summary = subtopic_data.get("reddit_summary", "")
                if summary and len(summary) > 100:
                    total_articles += 5  # Estimation moyenne
                if reddit_summary and "No significant" not in reddit_summary:
                    total_reddit_posts += 8  # Estimation moyenne
        
        segments = []
        
        # SEGMENT 1: Introduction personnalisée
        import random
        greeting = random.choice(templates['greeting'])
        
        intro_content = f"{greeting} !"
        
        if total_successful > 0:
            if language == 'fr':
                intro_content += f" J'ai analysé {total_successful} de tes sujets favoris"
                if total_articles > 0:
                    intro_content += f", en parcourant environ {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" et {total_reddit_posts} discussions Reddit"
                intro_content += " pour te donner le meilleur résumé personnalisé."
            else:
                intro_content += f" I've analyzed {total_successful} of your favorite topics"
                if total_articles > 0:
                    intro_content += f", going through about {total_articles} articles"
                if total_reddit_posts > 0:
                    intro_content += f" and {total_reddit_posts} Reddit discussions"
                intro_content += " to give you the best personalized summary."
        
        segments.append({
            "type": "intro",
            "content": intro_content,
            "duration_estimate": "30s"
        })
        
        # SEGMENT 2: Transition globale
        transition = random.choice(templates['transition_global'])
        segments.append({
            "type": "global_transition",
            "content": transition,
            "duration_estimate": "10s"
        })
        
        # SEGMENT 3: Traiter chaque sujet
        for topic_name, topic_report in reports.items():
            if not topic_report.get("topic_summary"):
                continue
                
            topic_transition = random.choice(templates['topic_transition'])
            
            # Utiliser la pickup line comme accroche
            pickup_line = topic_report.get("pickup_line", "")
            topic_summary = topic_report.get("topic_summary", "")
            
            topic_content = f"{topic_transition} {topic_name.lower()}. "
            
            if pickup_line:
                # Rendre la pickup line conversationnelle
                if language == 'fr':
                    topic_content += f"{pickup_line} "
                else:
                    topic_content += f"{pickup_line} "
            
            # Extraire les points clés du résumé
            if topic_summary:
                cleaned_summary = topic_summary.replace("**", "").replace("*", "").replace("#", "")
                sentences = [s.strip() for s in cleaned_summary.split('.') if s.strip()]
                
                # Prendre 2-3 points clés
                key_points = []
                for sentence in sentences[:4]:
                    if len(sentence) > 30:  # Éviter les fragments
                        if language == 'fr':
                            if not sentence.startswith(("En fait", "Donc", "Bref")):
                                sentence = f"En gros, {sentence.lower()}"
                        key_points.append(sentence)
                
                if key_points:
                    topic_content += " ".join(key_points[:2])  # Max 2 points par sujet
            
            segments.append({
                "type": "topic",
                "topic_name": topic_name,
                "content": topic_content,
                "duration_estimate": "1-2min"
            })
            
            # SEGMENT 4: Sous-sujets détaillés
            subtopics = topic_report.get("subtopics", {})
            if subtopics:
                for subtopic_name, subtopic_data in list(subtopics.items())[:2]:  # Max 2 sous-sujets par topic
                    subtopic_intro = random.choice(templates['subtopic_intro'])
                    
                    subtopic_content = f"{subtopic_intro} {subtopic_name.lower()}. "
                    
                    subtopic_summary = subtopic_data.get("subtopic_summary", "")
                    reddit_summary = subtopic_data.get("reddit_summary", "")
                    
                    if subtopic_summary:
                        # Extraire 1-2 points clés
                        cleaned = subtopic_summary.replace("**", "").replace("*", "").replace("#", "")
                        key_points = [s.strip() for s in cleaned.split('.') if s.strip() and len(s) > 20][:1]
                        
                        if key_points:
                            subtopic_content += f"{key_points[0]}. "
                    
                    # Ajouter insight Reddit si pertinent
                    if reddit_summary and "No significant" not in reddit_summary and "unavailable" not in reddit_summary:
                        if language == 'fr':
                            subtopic_content += "La communauté en parle beaucoup actuellement."
                        else:
                            subtopic_content += "The community is really talking about this right now."
                    
                    segments.append({
                        "type": "subtopic",
                        "topic_name": topic_name,
                        "subtopic_name": subtopic_name,
                        "content": subtopic_content,
                        "duration_estimate": "45s"
                    })
        
        # SEGMENT FINAL: Conclusion globale
        conclusion = random.choice(templates['global_conclusion'])
        if language == 'fr':
            conclusion += " Reste connecté(e) pour ne rien rater ! Bisous !"
        else:
            conclusion += " Stay tuned for more updates! Take care!"
        
        segments.append({
            "type": "global_conclusion",
            "content": conclusion,
            "duration_estimate": "20s"
        })
        
        # Assembler le script complet
        full_script = "\n\n".join([segment["content"] for segment in segments])
        
        # Calculs des métadonnées
        word_count = len(full_script.split())
        estimated_duration = f"{max(8, word_count // 150)}-{word_count // 120} minutes"
        
        result = {
            "success": True,
            "script": full_script,
            "segments": segments,
            "metadata": {
                "user_id": user_id,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "total_duration_estimate": estimated_duration,
                "topics_covered": total_successful,
                "total_topics": total_topics,
                "estimated_articles": total_articles,
                "estimated_reddit_posts": total_reddit_posts,
                "report_generation_stats": complete_report.get("generation_stats", {})
            },
            "generation_timestamp": datetime.now().isoformat(),
            "based_on_report": {
                "refresh_timestamp": complete_report.get("refresh_timestamp"),
                "language": complete_report.get("language")
            }
        }
        
        logger.info(f"✅ User media twin script generated: {word_count} words, {len(segments)} segments for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating user media twin script for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "script": f"Désolé, il y a eu un problème pour générer ton briefing personnalisé. On va réessayer plus tard !",
            "segments": [],
            "metadata": {"user_id": user_id}
        }
    
def generate_complete_user_media_twin_script(user_id, presenter_name="Alex", language="fr"):
    """
    Generate complete media twin script using all real user articles with AI analysis.
    This version uses OpenAI to create intelligent, personalized content based on actual articles.
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter
        language (str): Language for the script ('fr' or 'en')
    
    Returns:
        dict: Complete script with AI-generated content
    """
    try:
        logger.info(f"🎤 Generating complete AI media twin script for user {user_id}")
        
        # Get user articles from database
        articles_data = get_user_articles_from_db(user_id)
        
        if not articles_data:
            raise Exception("No articles found for user")
        
        topics = articles_data.get("topics_data", {})
        
        if not topics:
            raise Exception("No topics found for user")
        
        logger.info(f"Processing {len(topics)} topics for AI script generation")
        
        # Count articles for script planning
        total_topics = len(topics)
        segment_duration = max(60, 240 // total_topics)  # Between 60s and 4min per segment
        
        # Start building the script
        if language == "fr":
            script = f"""🎙️ SCRIPT MÉDIA TWIN - {presenter_name.upper()}
====================================================

🎬 INTRO (30 secondes)
Salut et bienvenue dans votre briefing quotidien personnalisé ! Je suis {presenter_name}, et aujourd'hui on a un programme passionnant avec {total_topics} sujets choisis spécialement pour vous. Des startups européennes à l'intelligence artificielle, on va faire le tour de ce qui compte vraiment. C'est parti !

"""
        else:
            script = f"""🎙️ MEDIA TWIN SCRIPT - {presenter_name.upper()}
====================================================

🎬 INTRO (30 seconds)
Hello and welcome to your personalized daily briefing! I'm {presenter_name}, and today we have an exciting program with {total_topics} topics chosen especially for you. From European startups to artificial intelligence, we're going to cover what really matters. Let's go!

"""
        
        # Process each topic
        for i, (topic_name, topic_data) in enumerate(topics.items(), 1):
            logger.info(f"Processing topic {i}/{total_topics}: {topic_name}")
            
            script += f"""
🎬 SEGMENT {i}: {topic_name.upper()} ({segment_duration}s)
{'-' * 60}

"""
            
            # Generate AI pickup line
            pickup_result = get_pickup_line(topic_name, topic_data)
            if pickup_result.get("success"):
                script += f"""🎯 ACCROCHE: 
{pickup_result['pickup_line']}

"""
            
            # Generate AI topic summary
            summary_result = get_topic_summary(topic_name, topic_data)
            if summary_result.get("success"):
                if language == "fr":
                    script += f"""📰 LE BRIEFING:
{summary_result['topic_summary']}

"""
                else:
                    script += f"""📰 THE BRIEFING:
{summary_result['topic_summary']}

"""
            
            # Add subtopics breakdown
            subtopics = topic_data.get("data", {}).get("subtopics", {})
            if subtopics:
                if language == "fr":
                    script += "🔍 LES POINTS CLÉS:\n"
                else:
                    script += "🔍 KEY POINTS:\n"
                    
                for subtopic_name, subtopic_data in subtopics.items():
                    # Count articles in this subtopic
                    subtopic_articles = len(subtopic_data.get(subtopic_name, []))
                    query_articles = sum(len(articles) for articles in subtopic_data.get("queries", {}).values())
                    reddit_posts = sum(len(posts) for posts in subtopic_data.get("subreddits", {}).values())
                    
                    if language == "fr":
                        script += f"• {subtopic_name}: {subtopic_articles + query_articles} articles, {reddit_posts} discussions communautaires\n"
                    else:
                        script += f"• {subtopic_name}: {subtopic_articles + query_articles} articles, {reddit_posts} community discussions\n"
                    
                    # Add community insights
                    insights = get_reddit_community_insights(subtopic_data)
                    for insight in insights[:1]:  # Max 1 insight per subtopic
                        script += f"  💬 {insight}\n"
                
                script += "\n"
            
            # Add transition
            if i < total_topics:
                if language == "fr":
                    script += "🔄 Maintenant, passons à notre prochain sujet...\n"
                else:
                    script += "🔄 Now, let's move on to our next topic...\n"
        
        # Conclusion
        if language == "fr":
            script += f"""
🎬 CONCLUSION (25 secondes)
====================================================
Et voilà ! C'était votre briefing personnalisé couvrant {total_topics} sujets d'actualité. De l'innovation européenne aux avancées en IA, vous êtes maintenant à jour sur ce qui compte pour vous. Merci de m'avoir écouté, et à très bientôt pour de nouvelles actus !

📊 INFORMATIONS DU BRIEFING:
• Durée totale estimée: {50 + (segment_duration * total_topics)} secondes
• Articles analysés: {articles_data.get('summary', {}).get('total_articles', 'N/A')}
• Discussions Reddit: {articles_data.get('summary', {}).get('total_posts', 'N/A')}
• Dernière mise à jour: {articles_data.get('refresh_timestamp', 'N/A')[:10]}
• Présentateur: {presenter_name}
• Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}
"""
        else:
            script += f"""
🎬 CONCLUSION (25 seconds)
====================================================
And that's a wrap! That was your personalized briefing covering {total_topics} news topics. From European innovation to AI advances, you're now up to date on what matters to you. Thanks for listening, and see you soon for more news!

📊 BRIEFING INFORMATION:
• Total estimated duration: {50 + (segment_duration * total_topics)} seconds
• Articles analyzed: {articles_data.get('summary', {}).get('total_articles', 'N/A')}
• Reddit discussions: {articles_data.get('summary', {}).get('total_posts', 'N/A')}
• Last updated: {articles_data.get('refresh_timestamp', 'N/A')[:10]}
• Presenter: {presenter_name}
• Generated on: {datetime.now().strftime('%m/%d/%Y at %H:%M')}
"""

        # Calculate metadata
        word_count = len(script.split())
        estimated_duration_minutes = max(4, word_count // 150)
        
        result = {
            "success": True,
            "script": script.strip(),
            "metadata": {
                "user_id": user_id,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "total_duration_estimate": f"{estimated_duration_minutes} minutes",
                "topics_covered": len(topics),
                "articles_analyzed": articles_data.get('summary', {}).get('total_articles', 0),
                "reddit_discussions": articles_data.get('summary', {}).get('total_posts', 0),
                "ai_generated": True,
                "script_type": "complete_ai_media_twin"
            },
            "generation_timestamp": datetime.now().isoformat(),
            "refresh_timestamp": articles_data.get("refresh_timestamp")
        }
        
        logger.info(f"✅ Complete AI media twin script generated: {word_count} words for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating complete AI media twin script for user {user_id}: {e}")
        if language == "fr":
            fallback_script = f"Désolé, il y a eu un problème pour générer votre briefing personnalisé. On va réessayer plus tard ! (Erreur: {str(e)})"
        else:
            fallback_script = f"Sorry, there was an issue generating your personalized briefing. We'll try again later! (Error: {str(e)})"
            
        return {
            "success": False,
            "error": str(e),
            "script": fallback_script,
            "metadata": {"user_id": user_id, "error": True}
        }

def generate_simple_podcast_script(user_id, presenter_name="Alex", language="en"):
    """
    Generate a simple conversational podcast script based on user articles.
    Uses a straightforward approach with OpenAI to create natural, friendly commentary.
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter/host
        language (str): Language for the script ('en' or 'fr')
    
    Returns:
        dict: Simple script with success status
    """
    try:
        logger.info(f"🎙️ Generating simple podcast script for user {user_id}")
        
        # Get user articles from database
        articles_data = get_user_articles_from_db(user_id)
        
        if not articles_data:
            raise Exception("No articles found for user")
        
        topics_data = articles_data.get("topics_data", {})
        
        if not topics_data:
            raise Exception("No topics found for user")
        
        # Create the podcast generation prompt
        if language == "fr":
            system_prompt = """Tu es un animateur de podcast amical qui crée un script conversationnel pour un briefing d'actualités. Ton ton doit être décontracté, engageant et informatif - comme si tu racontais des nouvelles intéressantes à un ami.

Génère un script de podcast de 4-6 minutes basé sur TOUS les articles fournis, organisés par sujets et sous-sujets.

IMPORTANT: Écris UNIQUEMENT le texte à lire à voix haute - AUCUNE indication de mise en scène comme [intro], [outro], [pause], etc. Le script doit être du texte pur, fluide et lisible directement.

Directives de style:
- Conversationnel et naturel (comme si tu parlais à un ami)
- Utilise des transitions comme "En parlant de...", "Oh, et voici quelque chose d'intéressant...", "Tu sais ce qui m'a frappé?"
- Inclus des réactions personnelles ("C'est assez fou...", "J'ai trouvé ça fascinant...")
- Reste engageant mais informatif
- Utilise les noms des sources pour ajouter de la crédibilité
- Commence directement par un accueil naturel, termine par une conclusion naturelle
- Pas de marqueurs de temps ou d'instructions techniques

Flux naturel:
- Commence par un accueil chaleureux et un aperçu des sujets
- Enchaîne naturellement d'un sujet à l'autre avec des transitions fluides
- Termine par une conclusion naturelle et engageante

IMPORTANT: Couvre chaque article fourni - n'en laisse aucun de côté. Mentionne chaque titre d'article. Écris SEULEMENT ce qui doit être dit à voix haute."""

        else:
            system_prompt = """You are a friendly podcast host creating a conversational news briefing script. Your tone should be casual, engaging, and informative - like telling a friend about interesting news you've discovered.

Generate a 10-12 minute podcast (1500-1700 words) script based on ALL the provided articles, organized by topics and subtopics.

CRITICAL FORMATTING REQUIREMENT:
Structure your script with clear article-based sections using this EXACT format:

INTRO:
[Your welcoming introduction text here]

<<articlelink1>>:
[Content discussing this specific article]

<<articlelink2>>:
[Content discussing this specific article]

<<articlelink3>>:
[Content discussing this specific article]

[Continue for ALL articles...]

CONCLUSION:
[Your closing remarks]

IMPORTANT RULES:
- Write ONLY the text to be read aloud - NO stage directions like [intro], [outro], [pause], etc.
- Each article section should flow naturally when read consecutively
- Use natural transitions between articles ("Speaking of...", "Oh, and here's something interesting...", "You know what caught my eye?")
- Include personal reactions/commentary ("This is pretty wild...", "I found this fascinating...")
- Keep it engaging but informative
- Use source names to add credibility
- When article links are removed, the script should flow as one continuous, natural conversation
- Cover every single article provided - don't leave any out
- Write ONLY what needs to be spoken aloud

The script must work both as:
1. Structured sections (with article links as headers)
2. One flowing conversation (when article links are removed)"""


        # Fodrmat the articles data as a clean JSON string
        user_message = f"Here's the news data to create a podcast script for:\n\n{json.dumps(topics_data, indent=2)}"
        
        # Use OpenAI to generate the script
        client = get_openai_client()
        if not client:
            raise Exception("OpenAI client not available")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Generate the podcast script with more tokens for a complete script
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=6000,  # Enough for a 4-6 minute script
            temperature=0.7
        )
        
        script_content = response.choices[0].message.content
        
        # Clean up any remaining stage directions from the script
        import re
        # Remove stage directions like [intro], [outro], [pause], etc.
        script_content = re.sub(r'\[.*?\]', '', script_content)
        # Remove timestamp markers like (00:30), (2:15), etc.
        script_content = re.sub(r'\(\d+:\d+\)', '', script_content)
        # Remove excessive line breaks and clean up whitespace
        script_content = re.sub(r'\n\s*\n\s*\n', '\n\n', script_content)
        script_content = script_content.strip()
        
        logger.info(f"✅ Script cleaned and ready: {len(script_content)} characters")
        
        # Calculate metadata
        word_count = len(script_content.split())
        estimated_duration_minutes = max(4, word_count // 150)
        
        # Save script to Firebase Storage
        storage_url = None
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"podcast_scripts/{user_id}/script_{timestamp}.txt"
            
            # Get Firebase Storage bucket
            bucket = storage.bucket()
            blob = bucket.blob(filename)
            
            # Upload script content
            blob.upload_from_string(
                script_content, 
                content_type='text/plain; charset=utf-8'
            )
            
            # Make the file publicly readable (optional)
            blob.make_public()
            storage_url = blob.public_url
            
            logger.info(f"📁 Script saved to storage: {filename}")
            
        except Exception as storage_error:
            logger.error(f"Error saving script to storage: {storage_error}")
            # Continue execution even if storage fails
        
        # Save audio connection info to database
        db_storage_success = False
        try:
            db_client = firestore.client()
            
            audio_connection_data = {
                "user_id": user_id,
                "script_content": script_content,
                "storage_url": storage_url,
                "presenter_name": presenter_name,
                "language": language,
                "word_count": word_count,
                "estimated_duration": f"{estimated_duration_minutes} minutes",
                "topics_covered": len(topics_data),
                "articles_analyzed": articles_data.get('summary', {}).get('total_articles', 0),
                "script_type": "simple_conversational_podcast",
                "model_used": "gpt-4o",
                "created_at": datetime.now().isoformat(),
                "refresh_timestamp": articles_data.get("refresh_timestamp"),
                "status": "script_generated"  # Can be updated later when audio is generated
            }
            
            # Store in audio_connections collection
            doc_ref = db_client.collection('audio_connections').document()
            doc_ref.set(audio_connection_data)
            
            # Also update user's latest script reference
            user_audio_ref = db_client.collection('user_audio_connections').document(user_id)
            user_audio_ref.set({
                "latest_script_id": doc_ref.id,
                "latest_script_created": datetime.now().isoformat(),
                "storage_url": storage_url
            }, merge=True)
            
            db_storage_success = True
            logger.info(f"📀 Audio connection saved to database: {doc_ref.id}")
            
        except Exception as db_error:
            logger.error(f"Error saving audio connection to database: {db_error}")
        
        result = {
                "success": True,
                "script": script_content,
                "storage_url": storage_url,
                "db_saved": db_storage_success,
                "metadata": {
                    "user_id": user_id,
                    "presenter_name": presenter_name,
                    "language": language,
                    "word_count": word_count,
                    "estimated_duration": f"{estimated_duration_minutes} minutes",
                    "topics_covered": len(topics_data),
                    "articles_analyzed": articles_data.get('summary', {}).get('total_articles', 0),
                    "script_type": "simple_conversational_podcast",
                    "model_used": "gpt-4o"
                },
                "generation_timestamp": datetime.now().isoformat(),
                "refresh_timestamp": articles_data.get("refresh_timestamp")
        }
        return result  # ← ADD THIS RETURN STATEMENT
        
    except Exception as e:  # ← ADD THIS MAIN EXCEPT BLOCK
        logger.error(f"Error generating simple podcast script for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate podcast script",
            "metadata": {"user_id": user_id, "error": True}
        }
    
def generate_simple_podcast(user_id, presenter_name="Alex", language="en", voice_id="96c64eb5-a945-448f-9710-980abe7a514c"):
    """
    Generate complete podcast: script + audio using ElevenLabs, with full storage and database saving.
    
    Args:
        user_id (str): User ID to get articles for
        presenter_name (str): Name of the presenter/host
        language (str): Language for the script ('en' or 'fr')
        voice_id (str): ElevenLabs voice ID for audio generation
    
    Returns:
        dict: Complete result with script, audio URL, and storage info
    """
    try:
        logger.info(f"🎙️ Generating complete podcast (script + audio) for user {user_id}")
        
        # Step 1: Generate the script using existing function
        logger.info(f"📝 Step 1/3: Generating script for user {user_id}")
        script_result = generate_simple_podcast_script(
            user_id=user_id,
            presenter_name=presenter_name,
            language=language
        )
        
        if not script_result.get("success"):
            raise Exception(f"Script generation failed: {script_result.get('error')}")
        
        script_content = script_result.get("script")
        script_storage_url = script_result.get("storage_url")
        
        logger.info(f"✅ Script generated: {len(script_content)} characters")
        
        # Step 2: Generate audio using ElevenLabs
        logger.info(f"🔊 Step 2/3: Converting script to audio with ElevenLabs...")
        logger.info(f"📊 About to convert {len(script_content)} characters to audio")
        
        audio_bytes = generate_text_to_speech(
            text=script_content,
            voice_id=voice_id,
            model_id="sonic-2",
            language=language
        )
        # audio_bytes = generate_text_to_speech_openai(
        #      text=script_content)
        
        logger.info(f"🔍 Audio generation result: audio_bytes is {'None' if audio_bytes is None else f'{len(audio_bytes)} bytes'}")
        
        if not audio_bytes:
            logger.error("❌ Audio generation failed - audio_bytes is None or empty")
            raise Exception("Audio generation failed")
        
        logger.info(f"✅ Audio generated: {len(audio_bytes)} bytes")
        
        # Step 3: Save audio to Firebase Storage
        logger.info(f"💾 Step 3/3: Saving audio to Firebase Storage...")
        audio_storage_url = None
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"podcast_audio/{user_id}/podcast_{timestamp}.wav"  # WAV extension
            
            # Get Firebase Storage bucket
            bucket = storage.bucket()
            audio_blob = bucket.blob(audio_filename)
            
            # Upload audio content
            audio_blob.upload_from_string(
                audio_bytes,
                content_type='audio/wav'  # WAV content-type
            )
            
            # Make the file publicly readable
            audio_blob.make_public()
            audio_storage_url = audio_blob.public_url
            
            logger.info(f"📁 Audio saved to storage: {audio_filename}")
            
        except Exception as storage_error:
            logger.error(f"Error saving audio to storage: {storage_error}")
            raise Exception(f"Audio storage failed: {storage_error}")
        
        # Step 4: Update database with complete podcast info
        try:
            db_client = firestore.client()
            
            # Update the existing audio_connections document with audio info
            # Find the latest script document for this user
            audio_connections_ref = db_client.collection('audio_connections')
            query = audio_connections_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).limit(1)
            docs = query.stream()
            
            latest_doc = None
            for doc in docs:
                latest_doc = doc
                break
            
            if latest_doc:
                # Update existing document with audio info
                latest_doc.reference.update({
                    'audio_url': audio_storage_url,
                    'audio_filename': audio_filename,
                    'audio_generated_at': datetime.now().isoformat(),
                    'status': 'complete_podcast_generated',
                    'voice_id': voice_id
                })
                doc_id = latest_doc.id
            else:
                # Create new document if none exists
                complete_podcast_data = {
                    "user_id": user_id,
                    "script_content": script_content,
                    "script_storage_url": script_storage_url,
                    "audio_url": audio_storage_url,
                    "audio_filename": audio_filename,
                    "presenter_name": presenter_name,
                    "language": language,
                    "voice_id": voice_id,
                    "word_count": len(script_content.split()),
                    "estimated_duration": f"{max(4, len(script_content.split()) // 150)} minutes",
                    "script_type": "simple_conversational_podcast",
                    "model_used": "gpt-4o",
                    "audio_model": "eleven_multilingual_v2",
                    "created_at": datetime.now().isoformat(),
                    "audio_generated_at": datetime.now().isoformat(),
                    "status": "complete_podcast_generated"
                }
                
                doc_ref = db_client.collection('audio_connections').document()
                doc_ref.set(complete_podcast_data)
                doc_id = doc_ref.id
            
            logger.info(f"📀 Complete podcast saved to database: {doc_id}")
            
            # Step 5: Save audio link in audio > user_id collection with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    audio_user_ref = db_client.collection('audio').document(user_id)
                    audio_data = {
                        "latest_podcast_url": audio_storage_url,
                        "latest_podcast_created": datetime.now().isoformat(),
                        "latest_podcast_id": doc_id,
                        "script_url": script_storage_url,
                        "presenter_name": presenter_name,
                        "language": language,
                        "voice_id": voice_id,
                        "audio_filename": audio_filename,
                        "status": "complete_podcast_generated"
                    }
                    audio_user_ref.set(audio_data, merge=True)
                    logger.info(f"🎵 Audio link saved in audio/{user_id}")
                    break
                except Exception as audio_save_error:
                    logger.warning(f"Attempt {attempt + 1} failed to save to audio collection: {audio_save_error}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to save audio link after {max_retries} attempts: {audio_save_error}")
                        # Continue anyway - don't fail the whole process
            
        except Exception as db_error:
            logger.error(f"Error saving complete podcast to database: {db_error}")
            # Don't fail the whole process for DB errors, but log it prominently
            logger.error(f"🚨 DATABASE SAVE FAILED - Audio generated successfully but not saved to database: {db_error}")
        
        # Step 6: Prepare final result
        result = {
            "success": True,
            "script": script_content,
            "script_storage_url": script_storage_url,
            "audio_url": audio_storage_url,
            "audio_filename": audio_filename,
            "metadata": {
                "user_id": user_id,
                "presenter_name": presenter_name,
                "language": language,
                "voice_id": voice_id,
                "word_count": len(script_content.split()),
                "estimated_duration": f"{max(4, len(script_content.split()) // 150)} minutes",
                "script_type": "simple_conversational_podcast",
                "model_used": "gpt-4o",
                "audio_model": "eleven_multilingual_v2",
                "audio_size_bytes": len(audio_bytes)
            },
            "generation_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🎉 Complete podcast generation successful for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating complete podcast for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate complete podcast",
            "metadata": {"user_id": user_id, "error": True}
        }
