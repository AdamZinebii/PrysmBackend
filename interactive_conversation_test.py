#!/usr/bin/env python3
"""
Interactive Conversation Test for PrysmIOS Backend
Allows you to test the conversation system with topic selection and real-time chat.
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import functions from main.py
from main import build_system_prompt, format_conversation_history, generate_ai_response, gnews_top_headlines, gnews_search

# Available topics and subtopics - All GNews categories
AVAILABLE_TOPICS = {
    "general": {
        "fr": "général",
        "es": "general",
        "ar": "عام",
        "subtopics": {
            "en": ["Breaking News", "Top Stories", "Current Events", "Daily News", "Headlines"],
            "fr": ["Actualités", "Principales Nouvelles", "Événements Actuels", "Nouvelles Quotidiennes", "Gros Titres"],
            "es": ["Noticias de Última Hora", "Historias Principales", "Eventos Actuales", "Noticias Diarias", "Titulares"],
            "ar": ["أخبار عاجلة", "أهم الأخبار", "الأحداث الجارية", "الأخبار اليومية", "العناوين الرئيسية"]
        }
    },
    "world": {
        "fr": "monde",
        "es": "mundo",
        "ar": "عالم",
        "subtopics": {
            "en": ["International News", "Global Events", "Foreign Affairs", "World Politics", "International Relations"],
            "fr": ["Actualités Internationales", "Événements Mondiaux", "Affaires Étrangères", "Politique Mondiale", "Relations Internationales"],
            "es": ["Noticias Internacionales", "Eventos Globales", "Asuntos Exteriores", "Política Mundial", "Relaciones Internacionales"],
            "ar": ["الأخبار الدولية", "الأحداث العالمية", "الشؤون الخارجية", "السياسة العالمية", "العلاقات الدولية"]
        }
    },
    "nation": {
        "fr": "national",
        "es": "nacional",
        "ar": "وطني",
        "subtopics": {
            "en": ["Domestic Politics", "Government News", "National Elections", "Policy Changes", "Local Government"],
            "fr": ["Politique Intérieure", "Actualités Gouvernementales", "Élections Nationales", "Changements de Politique", "Gouvernement Local"],
            "es": ["Política Doméstica", "Noticias del Gobierno", "Elecciones Nacionales", "Cambios de Política", "Gobierno Local"],
            "ar": ["السياسة المحلية", "أخبار الحكومة", "الانتخابات الوطنية", "تغييرات السياسة", "الحكومة المحلية"]
        }
    },
    "business": {
        "fr": "affaires",
        "es": "negocios",
        "ar": "أعمال",
        "subtopics": {
            "en": ["Stock Market", "Startups", "Corporate News", "Economic Trends", "Cryptocurrency"],
            "fr": ["Bourse", "Startups", "Actualités d'Entreprise", "Tendances Économiques", "Cryptomonnaie"],
            "es": ["Bolsa de Valores", "Startups", "Noticias Corporativas", "Tendencias Económicas", "Criptomoneda"],
            "ar": ["سوق الأسهم", "الشركات الناشئة", "أخبار الشركات", "الاتجاهات الاقتصادية", "العملة المشفرة"]
        }
    },
    "technology": {
        "fr": "technologie",
        "es": "tecnología", 
        "ar": "تكنولوجيا",
        "subtopics": {
            "en": ["AI", "Smartphones & Gadgets", "Software Development", "Cybersecurity", "Tech Companies"],
            "fr": ["AI", "Smartphones & Gadgets", "Développement Logiciel", "Cybersécurité", "Entreprises Tech"],
            "es": ["AI", "Smartphones & Gadgets", "Desarrollo de Software", "Ciberseguridad", "Empresas Tech"],
            "ar": ["AI", "الهواتف الذكية", "تطوير البرمجيات", "الأمن السيبراني", "شركات التكنولوجيا"]
        }
    },
    "entertainment": {
        "fr": "divertissement",
        "es": "entretenimiento",
        "ar": "ترفيه",
        "subtopics": {
            "en": ["Movies & TV", "Music", "Celebrities", "Gaming", "Arts & Culture"],
            "fr": ["Films & TV", "Musique", "Célébrités", "Jeux Vidéo", "Arts & Culture"],
            "es": ["Películas & TV", "Música", "Celebridades", "Videojuegos", "Arte & Cultura"],
            "ar": ["أفلام وتلفزيون", "موسيقى", "مشاهير", "ألعاب", "فنون وثقافة"]
        }
    },
    "sports": {
        "fr": "sport",
        "es": "deportes",
        "ar": "رياضة",
        "subtopics": {
            "en": ["Football/Soccer", "Basketball", "Tennis", "Olympics", "Local Teams"],
            "fr": ["Football", "Basketball", "Tennis", "Jeux Olympiques", "Équipes Locales"],
            "es": ["Fútbol", "Baloncesto", "Tenis", "Juegos Olímpicos", "Equipos Locales"],
            "ar": ["كرة القدم", "كرة السلة", "التنس", "الألعاب الأولمبية", "الفرق المحلية"]
        }
    },
    "science": {
        "fr": "science",
        "es": "ciencia",
        "ar": "علوم",
        "subtopics": {
            "en": ["Research", "Space & Astronomy", "Climate Change", "Biology", "Physics"],
            "fr": ["Recherche", "Espace & Astronomie", "Changement Climatique", "Biologie", "Physique"],
            "es": ["Investigación", "Espacio & Astronomía", "Cambio Climático", "Biología", "Física"],
            "ar": ["بحث", "الفضاء والفلك", "تغير المناخ", "علم الأحياء", "فيزياء"]
        }
    },
    "health": {
        "fr": "santé",
        "es": "salud",
        "ar": "صحة",
        "subtopics": {
            "en": ["Medical Research", "Public Health", "Mental Health", "Fitness & Wellness", "Healthcare Policy"],
            "fr": ["Recherche Médicale", "Santé Publique", "Santé Mentale", "Fitness & Bien-être", "Politique de Santé"],
            "es": ["Investigación Médica", "Salud Pública", "Salud Mental", "Fitness & Bienestar", "Política de Salud"],
            "ar": ["البحث الطبي", "الصحة العامة", "الصحة النفسية", "اللياقة والعافية", "سياسة الرعاية الصحية"]
        }
    }
}

DETAIL_LEVELS = {
    "en": ["Light", "Medium", "Detailed"],
    "fr": ["Léger", "Moyen", "Détaillé"],
    "es": ["Ligero", "Medio", "Detallado"],
    "ar": ["خفيف", "متوسط", "مفصل"]
}

LANGUAGES = {
    "en": "English",
    "fr": "Français", 
    "es": "Español",
    "ar": "العربية"
}

def print_header():
    """Print the application header."""
    print("🤖 PrysmIOS Interactive Conversation Test")
    print("=" * 50)
    print("Test your conversation system with topic selection and real-time chat!")
    print()

def select_language():
    """Allow user to select language."""
    print("🌍 Select your language / Sélectionnez votre langue:")
    for i, (code, name) in enumerate(LANGUAGES.items(), 1):
        print(f"  {i}. {code.upper()} - {name}")
    
    while True:
        try:
            choice = input("\nEnter choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                lang_codes = list(LANGUAGES.keys())
                selected_lang = lang_codes[int(choice) - 1]
                print(f"✅ Selected: {LANGUAGES[selected_lang]}")
                return selected_lang
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            sys.exit(0)

def select_detail_level(language):
    """Allow user to select detail level."""
    levels = DETAIL_LEVELS[language]
    
    if language == "en":
        print("\n📊 Select your preferred detail level:")
    elif language == "fr":
        print("\n📊 Sélectionnez votre niveau de détail préféré:")
    elif language == "es":
        print("\n📊 Selecciona tu nivel de detalle preferido:")
    elif language == "ar":
        print("\n📊 اختر مستوى التفصيل المفضل لديك:")
    
    for i, level in enumerate(levels, 1):
        print(f"  {i}. {level}")
    
    while True:
        try:
            choice = input(f"\nEnter choice (1-{len(levels)}): ").strip()
            if choice in [str(i) for i in range(1, len(levels) + 1)]:
                selected_level = levels[int(choice) - 1]
                print(f"✅ Selected: {selected_level}")
                # Convert back to English for internal use
                level_mapping = {v: k for k, v in zip(DETAIL_LEVELS["en"], levels)}
                return level_mapping[selected_level]
            else:
                print(f"❌ Invalid choice. Please enter 1-{len(levels)}.")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            sys.exit(0)

def select_topics(language):
    """Allow user to select main topics."""
    if language == "en":
        print("\n📰 Select your news topics (you can choose multiple):")
    elif language == "fr":
        print("\n📰 Sélectionnez vos sujets d'actualités (vous pouvez en choisir plusieurs):")
    elif language == "es":
        print("\n📰 Selecciona tus temas de noticias (puedes elegir varios):")
    elif language == "ar":
        print("\n📰 اختر مواضيع الأخبار الخاصة بك (يمكنك اختيار عدة مواضيع):")
    
    # Display topics in selected language
    topic_list = []
    for i, (topic_key, topic_data) in enumerate(AVAILABLE_TOPICS.items(), 1):
        if language in topic_data:
            display_name = topic_data[language]
        else:
            display_name = topic_key
        print(f"  {i}. {display_name.title()}")
        topic_list.append(topic_key)
    
    if language == "en":
        print("\nEnter topic numbers separated by commas (e.g., 1,3,5):")
    elif language == "fr":
        print("\nEntrez les numéros des sujets séparés par des virgules (ex: 1,3,5):")
    elif language == "es":
        print("\nIngresa los números de temas separados por comas (ej: 1,3,5):")
    elif language == "ar":
        print("\nأدخل أرقام المواضيع مفصولة بفواصل (مثال: 1,3,5):")
    
    while True:
        try:
            choices = input("Your choice: ").strip().split(',')
            selected_topics = []
            selected_topic_keys = []
            
            for choice in choices:
                choice = choice.strip()
                if choice.isdigit() and 1 <= int(choice) <= len(topic_list):
                    topic_key = topic_list[int(choice) - 1]
                    selected_topic_keys.append(topic_key)
                    # Get display name in selected language
                    if language in AVAILABLE_TOPICS[topic_key]:
                        display_name = AVAILABLE_TOPICS[topic_key][language]
                    else:
                        display_name = topic_key
                    selected_topics.append(display_name)
                else:
                    print(f"❌ Invalid choice: {choice}")
                    break
            else:
                if selected_topics:
                    print(f"✅ Selected topics: {', '.join(selected_topics)}")
                    return selected_topics, selected_topic_keys
                else:
                    print("❌ Please select at least one topic.")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            sys.exit(0)

def select_subtopics(selected_topic_keys, language):
    """Allow user to select subtopics for each main topic."""
    all_subtopics = []
    
    for topic_key in selected_topic_keys:
        topic_data = AVAILABLE_TOPICS[topic_key]
        
        # Get topic display name
        if language in topic_data:
            topic_display = topic_data[language]
        else:
            topic_display = topic_key
        
        # Get subtopics for this language
        subtopics = topic_data["subtopics"].get(language, topic_data["subtopics"]["en"])
        
        if language == "en":
            print(f"\n🔍 Select specific interests for {topic_display.title()}:")
        elif language == "fr":
            print(f"\n🔍 Sélectionnez des intérêts spécifiques pour {topic_display.title()}:")
        elif language == "es":
            print(f"\n🔍 Selecciona intereses específicos para {topic_display.title()}:")
        elif language == "ar":
            print(f"\n🔍 اختر اهتمامات محددة لـ {topic_display.title()}:")
        
        for i, subtopic in enumerate(subtopics, 1):
            print(f"  {i}. {subtopic}")
        
        if language == "en":
            print(f"\nEnter subtopic numbers for {topic_display} (e.g., 1,3) or press Enter to skip:")
        elif language == "fr":
            print(f"\nEntrez les numéros des sous-sujets pour {topic_display} (ex: 1,3) ou Entrée pour passer:")
        elif language == "es":
            print(f"\nIngresa números de subtemas para {topic_display} (ej: 1,3) o Enter para omitir:")
        elif language == "ar":
            print(f"\nأدخل أرقام المواضيع الفرعية لـ {topic_display} (مثال: 1,3) أو Enter للتخطي:")
        
        while True:
            try:
                user_input = input("Your choice: ").strip()
                
                # Allow skipping
                if not user_input:
                    if language == "en":
                        print(f"⏭️ Skipped subtopics for {topic_display}")
                    elif language == "fr":
                        print(f"⏭️ Sous-sujets ignorés pour {topic_display}")
                    elif language == "es":
                        print(f"⏭️ Subtemas omitidos para {topic_display}")
                    elif language == "ar":
                        print(f"⏭️ تم تخطي المواضيع الفرعية لـ {topic_display}")
                    break
                
                choices = user_input.split(',')
                selected_subtopics = []
                
                for choice in choices:
                    choice = choice.strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(subtopics):
                        subtopic = subtopics[int(choice) - 1]
                        selected_subtopics.append(f"{topic_display}: {subtopic}")
                    else:
                        print(f"❌ Invalid choice: {choice}")
                        break
                else:
                    if selected_subtopics:
                        print(f"✅ Selected for {topic_display}: {', '.join([s.split(': ')[1] for s in selected_subtopics])}")
                        all_subtopics.extend(selected_subtopics)
                    break
                    
            except (ValueError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                sys.exit(0)
    
    return all_subtopics

def fetch_trending_headlines(topics, subtopics, language="en"):
    """
    Fetch trending headlines for selected topics and subtopics.
    
    Args:
        topics (list): List of selected topics (display names)
        subtopics (list): List of selected subtopics (display names)
        language (str): Language code
    
    Returns:
        dict: Headlines organized by topics and subtopics
    """
    headlines = {
        "topics": {},
        "subtopics": {}
    }
    
    # Map language codes for GNews API
    gnews_lang_map = {
        "en": "en",
        "fr": "fr", 
        "es": "es",
        "ar": "ar"
    }
    
    # Map country codes
    gnews_country_map = {
        "en": "us",
        "fr": "fr",
        "es": "es", 
        "ar": "sa"
    }
    
    gnews_lang = gnews_lang_map.get(language, "en")
    gnews_country = gnews_country_map.get(language, "us")
    
    # Direct mapping of English topic keys to GNews categories
    topic_category_map = {
        "general": "general",
        "world": "world",
        "nation": "nation",
        "business": "business",
        "technology": "technology",
        "entertainment": "entertainment",
        "sports": "sports",
        "science": "science",
        "health": "health"
    }
    
    print(f"🔍 Fetching trending headlines for {language}...")
    
    # Fetch headlines for topics using top-headlines endpoint
    for topic in topics:
        try:
            # Find the English key for this topic
            topic_key = None
            for key, data in AVAILABLE_TOPICS.items():
                if language in data and data[language].lower() == topic.lower():
                    topic_key = key
                    break
                elif key.lower() == topic.lower():
                    topic_key = key
                    break
            
            if topic_key and topic_key in topic_category_map:
                category = topic_category_map[topic_key]
                response = gnews_top_headlines(
                    category=category,
                    lang=gnews_lang,
                    country=gnews_country,
                    max_articles=4
                )
                
                if response.get("success") and response.get("articles"):
                    headlines["topics"][topic] = [
                        article.get("title", "").strip() 
                        for article in response["articles"][:3]
                        if article.get("title")
                    ]
                    print(f"  ✅ {topic}: {len(headlines['topics'][topic])} headlines")
                else:
                    print(f"  ❌ {topic}: No headlines found")
                    
        except Exception as e:
            print(f"  ❌ {topic}: Error fetching headlines - {e}")
    
    # Fetch headlines for subtopics using search endpoint
    for subtopic in subtopics:
        try:
            # Extract the actual subtopic name (remove "topic: " prefix if present)
            clean_subtopic = subtopic.split(": ")[-1] if ": " in subtopic else subtopic
            
            response = gnews_search(
                query=clean_subtopic,
                lang=gnews_lang,
                country=gnews_country,
                max_articles=3
            )
            
            if response.get("success") and response.get("articles"):
                headlines["subtopics"][subtopic] = [
                    article.get("title", "").strip() 
                    for article in response["articles"][:2]
                    if article.get("title")
                ]
                print(f"  ✅ {clean_subtopic}: {len(headlines['subtopics'][subtopic])} headlines")
            else:
                print(f"  ❌ {clean_subtopic}: No headlines found")
                
        except Exception as e:
            print(f"  ❌ {clean_subtopic}: Error fetching headlines - {e}")
    
    return headlines

def build_enhanced_system_prompt(user_preferences, headlines=None):
    """
    Build enhanced system prompt with trending headlines.
    
    Args:
        user_preferences (dict): User preferences
        headlines (dict): Headlines organized by topics and subtopics
    
    Returns:
        str: Enhanced system prompt
    """
    # Get base system prompt
    base_prompt = build_system_prompt(user_preferences)
    
    if not headlines or (not headlines.get("topics") and not headlines.get("subtopics")):
        return base_prompt
    
    language = user_preferences.get('language', 'en')
    
    # Language-specific headlines section
    headlines_sections = {
        'en': {
            'intro': "\n\nCURRENT TRENDING HEADLINES (MUST mention these in your response):",
            'topics_header': "\nTrending in your selected topics:",
            'subtopics_header': "\nTrending in your subtopics:",
            'instruction': "\nIMPORTANT: You MUST mention these trending headlines in your response. Ask about specific companies, people, or events from these titles. Example: 'I see [specific company/person/event from headlines] is trending - are you interested in following them specifically?'"
        },
        'fr': {
            'intro': "\n\nTITRES TENDANCE ACTUELS (DOIT les mentionner dans votre réponse):",
            'topics_header': "\nTendances dans vos sujets sélectionnés:",
            'subtopics_header': "\nTendances dans vos sous-sujets:",
            'instruction': "\nIMPORTANT: Vous DEVEZ mentionner ces titres tendance dans votre réponse. Demandez sur des entreprises, personnes ou événements spécifiques de ces titres. Exemple: 'Je vois que [entreprise/personne/événement spécifique des titres] est tendance - êtes-vous intéressé à les suivre spécifiquement?'"
        },
        'es': {
            'intro': "\n\nTITULARES TENDENCIA ACTUALES (DEBE mencionarlos en su respuesta):",
            'topics_header': "\nTendencias en tus temas seleccionados:",
            'subtopics_header': "\nTendencias en tus subtemas:",
            'instruction': "\nIMPORTANTE: DEBE mencionar estos titulares tendencia en su respuesta. Pregunte sobre empresas, personas o eventos específicos de estos títulos. Ejemplo: 'Veo que [empresa/persona/evento específico de los titulares] está en tendencia - ¿te interesa seguirlos específicamente?'"
        },
        'ar': {
            'intro': "\n\nالعناوين الرائجة الحالية (يجب ذكرها في ردك):",
            'topics_header': "\nالرائج في مواضيعك المختارة:",
            'subtopics_header': "\nالرائج في مواضيعك الفرعية:",
            'instruction': "\nمهم: يجب أن تذكر هذه العناوين الرائجة في ردك. اسأل عن شركات أو أشخاص أو أحداث محددة من هذه العناوين. مثال: 'أرى أن [شركة/شخص/حدث محدد من العناوين] رائج - هل تهتم بمتابعتهم تحديداً؟'"
        }
    }
    
    section = headlines_sections.get(language, headlines_sections['en'])
    
    # Build headlines section
    headlines_text = section['intro']
    
    # Add topic headlines
    if headlines.get("topics"):
        headlines_text += section['topics_header']
        for topic, titles in headlines["topics"].items():
            if titles:
                headlines_text += f"\n• {topic}:"
                for title in titles:
                    headlines_text += f"\n  - {title}"
    
    # Add subtopic headlines
    if headlines.get("subtopics"):
        headlines_text += section['subtopics_header']
        for subtopic, titles in headlines["subtopics"].items():
            if titles:
                headlines_text += f"\n• {subtopic}:"
                for title in titles:
                    headlines_text += f"\n  - {title}"
    
    headlines_text += section['instruction']
    
    # Combine base prompt with headlines
    enhanced_prompt = base_prompt + headlines_text
    
    return enhanced_prompt

def mock_openai_response(user_message, language="en"):
    """Generate a mock AI response based on user message and language."""
    responses = {
        "en": {
            "hello": "Hello! I'm excited to help you with news and current events. Based on your preferences, I can provide personalized news updates. What specific aspects would you like to explore?",
            "technology": "Great choice! Technology is such a dynamic field. Are you particularly interested in AI developments, smartphone innovations, or perhaps specific tech companies like Apple, Google, or Microsoft?",
            "sports": "Sports news is always exciting! Are you interested in specific teams, leagues, or particular sports? For example, do you follow football/soccer, basketball, or maybe Olympic sports?",
            "politics": "Political news can be quite complex. Are you interested in international relations, domestic policy, elections, or specific regions? I can help you stay informed on the areas that matter most to you.",
            "business": "Business and economics are fascinating topics! Are you interested in stock market trends, startup news, corporate developments, or perhaps cryptocurrency and emerging markets?",
            "default": "That's interesting! Could you tell me more about what specific aspects of this topic interest you most? I'd love to help you get more targeted news updates."
        },
        "fr": {
            "hello": "Bonjour ! Je suis ravi de vous aider avec les actualités et les événements actuels. Basé sur vos préférences, je peux fournir des mises à jour personnalisées. Quels aspects spécifiques aimeriez-vous explorer ?",
            "technology": "Excellent choix ! La technologie est un domaine si dynamique. Êtes-vous particulièrement intéressé par les développements de l'IA, les innovations smartphones, ou peut-être des entreprises tech spécifiques comme Apple, Google ou Microsoft ?",
            "sports": "Les actualités sportives sont toujours passionnantes ! Êtes-vous intéressé par des équipes spécifiques, des ligues, ou des sports particuliers ? Par exemple, suivez-vous le football, le basketball, ou peut-être les sports olympiques ?",
            "default": "C'est intéressant ! Pourriez-vous me dire plus sur les aspects spécifiques de ce sujet qui vous intéressent le plus ? J'aimerais vous aider à obtenir des mises à jour d'actualités plus ciblées."
        },
        "es": {
            "hello": "¡Hola! Estoy emocionado de ayudarte con noticias y eventos actuales. Basado en tus preferencias, puedo proporcionar actualizaciones personalizadas. ¿Qué aspectos específicos te gustaría explorar?",
            "technology": "¡Excelente elección! La tecnología es un campo tan dinámico. ¿Estás particularmente interesado en desarrollos de IA, innovaciones en smartphones, o quizás empresas tech específicas como Apple, Google o Microsoft?",
            "default": "¡Eso es interesante! ¿Podrías contarme más sobre qué aspectos específicos de este tema te interesan más? Me encantaría ayudarte a obtener actualizaciones de noticias más dirigidas."
        },
        "ar": {
            "hello": "مرحباً! أنا متحمس لمساعدتك في الأخبار والأحداث الجارية. بناءً على تفضيلاتك، يمكنني تقديم تحديثات مخصصة. ما الجوانب المحددة التي تود استكشافها؟",
            "technology": "اختيار ممتاز! التكنولوجيا مجال ديناميكي جداً. هل أنت مهتم بشكل خاص بتطورات الذكاء الاصطناعي، ابتكارات الهواتف الذكية، أو ربما شركات تقنية محددة مثل آبل أو جوجل أو مايكروسوفت؟",
            "default": "هذا مثير للاهتمام! هل يمكنك إخباري المزيد عن الجوانب المحددة من هذا الموضوع التي تهمك أكثر؟ أود مساعدتك في الحصول على تحديثات إخبارية أكثر استهدافاً."
        }
    }
    
    lang_responses = responses.get(language, responses["en"])
    user_lower = user_message.lower()
    
    # Simple keyword matching for demo
    if any(word in user_lower for word in ["hello", "hi", "bonjour", "hola", "مرحبا"]):
        return lang_responses.get("hello", lang_responses["default"])
    elif any(word in user_lower for word in ["tech", "technologie", "tecnología", "تكنولوجيا"]):
        return lang_responses.get("technology", lang_responses["default"])
    elif any(word in user_lower for word in ["sport", "deportes", "رياضة"]):
        return lang_responses.get("sports", lang_responses["default"])
    elif any(word in user_lower for word in ["politic", "politique", "política", "سياسة"]):
        return lang_responses.get("politics", lang_responses["default"])
    elif any(word in user_lower for word in ["business", "affaires", "negocios", "أعمال"]):
        return lang_responses.get("business", lang_responses["default"])
    else:
        return lang_responses["default"]

def test_parallel_update(user_id, conversation_history, user_message, language):
    """
    Test the parallel update functionality for specific subjects.
    This simulates the background analysis that happens in the real system.
    """
    print(f"🔍 Testing parallel analysis for user {user_id}...")
    
    # Import the analysis function from main.py
    try:
        from main import analyze_conversation_for_specific_subjects, update_specific_subjects_in_db
        
        # Analyze conversation for specific subjects
        analysis_result = analyze_conversation_for_specific_subjects(
            conversation_history, user_message, language
        )
        
        if analysis_result["success"]:
            specific_subjects = analysis_result.get("specific_subjects", [])
            usage = analysis_result.get("usage", {})
            
            print(f"📊 Analysis completed:")
            print(f"   - Subjects found: {specific_subjects}")
            print(f"   - Tokens used: {usage.get('total_tokens', 'N/A')}")
            
            if specific_subjects:
                print(f"💾 Simulating database update...")
                # In a real scenario, this would update Firebase Database
                # For testing, we'll just show what would be saved
                print(f"   - Would save to Firebase: {specific_subjects}")
                print(f"   - User ID: {user_id}")
                return {
                    "success": True,
                    "subjects_found": specific_subjects,
                    "analysis_usage": usage
                }
            else:
                print(f"   - No specific subjects found in this message")
                return {
                    "success": True,
                    "subjects_found": [],
                    "message": "No new subjects found"
                }
        else:
            error = analysis_result.get("error", "Unknown error")
            print(f"❌ Analysis failed: {error}")
            return {
                "success": False,
                "error": error
            }
            
    except ImportError as e:
        print(f"❌ Could not import analysis functions: {e}")
        print("💡 Make sure main.py is available and contains the analysis functions")
        return {
            "success": False,
            "error": f"Import error: {e}"
        }
    except Exception as e:
        print(f"❌ Error during parallel analysis test: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def start_conversation(user_preferences):
    """Start the interactive conversation using REAL OpenAI API."""
    language = user_preferences["language"]
    
    # Check if parallel testing is enabled
    enable_parallel_test = user_preferences.get("enable_parallel_test", False)
    
    # Generate a test user ID for parallel update testing (if enabled)
    test_user_id = None
    if enable_parallel_test:
        import uuid
        test_user_id = f"test_user_{str(uuid.uuid4())[:8]}"
    
    if language == "en":
        print("\n💬 Starting conversation... (type 'quit' to exit)")
        print("🤖 AI Assistant is ready to chat with REAL OpenAI!")
        if enable_parallel_test:
            print(f"🆔 Test User ID: {test_user_id}")
            print("🔍 Parallel analysis will be tested after each message")
    elif language == "fr":
        print("\n💬 Démarrage de la conversation... (tapez 'quit' pour quitter)")
        print("🤖 L'Assistant IA est prêt à discuter avec la VRAIE OpenAI !")
        if enable_parallel_test:
            print(f"🆔 ID Utilisateur Test: {test_user_id}")
            print("🔍 L'analyse parallèle sera testée après chaque message")
    elif language == "es":
        print("\n💬 Iniciando conversación... (escribe 'quit' para salir)")
        print("🤖 ¡El Asistente IA está listo para chatear con OpenAI REAL!")
        if enable_parallel_test:
            print(f"🆔 ID Usuario Prueba: {test_user_id}")
            print("🔍 El análisis paralelo se probará después de cada mensaje")
    elif language == "ar":
        print("\n💬 بدء المحادثة... (اكتب 'quit' للخروج)")
        print("🤖 مساعد الذكاء الاصطناعي جاهز للدردشة مع OpenAI الحقيقي!")
        if enable_parallel_test:
            print(f"🆔 معرف المستخدم التجريبي: {test_user_id}")
            print("🔍 سيتم اختبار التحليل المتوازي بعد كل رسالة")
    
    print("-" * 50)
    
    # Fetch trending headlines for enhanced system prompt
    topics = user_preferences.get('subjects', [])
    subtopics = user_preferences.get('subtopics', [])
    language = user_preferences.get('language', 'en')
    
    headlines = fetch_trending_headlines(topics, subtopics, language)
    
    # Build enhanced system prompt with headlines
    system_prompt = build_enhanced_system_prompt(user_preferences, headlines)
    conversation_history = []
    
    # Show system prompt for debugging
    print(f"🔧 Enhanced System Prompt Generated ({len(system_prompt)} chars)")
    print(f"📝 Preview: {system_prompt[:150]}...")
    if headlines.get("topics") or headlines.get("subtopics"):
        total_headlines = sum(len(titles) for titles in headlines.get("topics", {}).values()) + sum(len(titles) for titles in headlines.get("subtopics", {}).values())
        print(f"📰 Headlines included: {total_headlines} trending articles")
    print("-" * 50)
    
    # Initial AI greeting using REAL OpenAI
    if language == "en":
        initial_message = "Hello! I'm ready to help you with personalized news based on your preferences."
    elif language == "fr":
        initial_message = "Bonjour ! Je suis prêt à vous aider avec des actualités personnalisées selon vos préférences."
    elif language == "es":
        initial_message = "¡Hola! Estoy listo para ayudarte con noticias personalizadas según tus preferencias."
    elif language == "ar":
        initial_message = "مرحباً! أنا جاهز لمساعدتك في الأخبار المخصصة حسب تفضيلاتك."
    
    print("🔄 Generating initial AI response...")
    ai_response_result = generate_ai_response(system_prompt, [], initial_message)
    
    if ai_response_result["success"]:
        initial_greeting = ai_response_result["message"]
        usage = ai_response_result.get("usage", {})
        print(f"🤖 AI: {initial_greeting}")
        print(f"📊 Tokens used: {usage.get('total_tokens', 'N/A')}")
        conversation_history.append({"role": "assistant", "content": initial_greeting})
    else:
        print(f"❌ Error generating initial response: {ai_response_result.get('error', 'Unknown error')}")
        print("🔄 Falling back to mock response...")
        initial_greeting = mock_openai_response("hello", language)
        print(f"🤖 AI (Mock): {initial_greeting}")
        conversation_history.append({"role": "assistant", "content": initial_greeting})
    
    while True:
        try:
            # Get user input
            if language == "en":
                user_input = input("\n👤 You: ").strip()
            elif language == "fr":
                user_input = input("\n👤 Vous: ").strip()
            elif language == "es":
                user_input = input("\n👤 Tú: ").strip()
            elif language == "ar":
                user_input = input("\n👤 أنت: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'au revoir', 'adiós', 'وداعا']:
                if language == "en":
                    print("\n👋 Thanks for testing the conversation system! Goodbye!")
                elif language == "fr":
                    print("\n👋 Merci d'avoir testé le système de conversation ! Au revoir !")
                elif language == "es":
                    print("\n👋 ¡Gracias por probar el sistema de conversación! ¡Adiós!")
                elif language == "ar":
                    print("\n👋 شكراً لك على اختبار نظام المحادثة! وداعاً!")
                break
            
            if not user_input:
                continue
            
            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Test parallel analysis for specific subjects (if enabled)
            parallel_result = None
            if enable_parallel_test and test_user_id:
                print("\n" + "="*30 + " PARALLEL ANALYSIS TEST " + "="*30)
                parallel_result = test_parallel_update(
                    test_user_id, 
                    conversation_history[:-1],  # History without current message
                    user_input, 
                    language
                )
                print("="*80 + "\n")
            
            # Generate AI response using REAL backend function with enhanced prompt
            print("🔄 Generating AI response...")
            ai_response_result = generate_ai_response(system_prompt, conversation_history[:-1], user_input)
            
            if ai_response_result["success"]:
                ai_response = ai_response_result["message"]
                usage = ai_response_result.get("usage", {})
                
                # Display AI response
                print(f"🤖 AI: {ai_response}")
                print(f"📊 Tokens: {usage.get('total_tokens', 'N/A')} (prompt: {usage.get('prompt_tokens', 'N/A')}, completion: {usage.get('completion_tokens', 'N/A')})")
                
                # Add AI response to history
                conversation_history.append({"role": "assistant", "content": ai_response})
            else:
                error_msg = ai_response_result.get("error", "Unknown error")
                print(f"❌ Error generating AI response: {error_msg}")
                print("🔄 Falling back to mock response...")
                
                # Fallback to mock response
                ai_response = mock_openai_response(user_input, language)
                print(f"🤖 AI (Mock): {ai_response}")
                conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Show parallel analysis summary
            if parallel_result and parallel_result.get("success"):
                subjects_found = parallel_result.get("subjects_found", [])
                if subjects_found:
                    if language == "en":
                        print(f"🎯 Specific subjects discovered: {', '.join(subjects_found)}")
                    elif language == "fr":
                        print(f"🎯 Sujets spécifiques découverts: {', '.join(subjects_found)}")
                    elif language == "es":
                        print(f"🎯 Temas específicos descubiertos: {', '.join(subjects_found)}")
                    elif language == "ar":
                        print(f"🎯 المواضيع المحددة المكتشفة: {', '.join(subjects_found)}")
            
            # Show conversation stats
            if len(conversation_history) % 6 == 0:  # Every 3 exchanges
                if language == "en":
                    print(f"\n📊 Conversation stats: {len(conversation_history)} messages exchanged")
                elif language == "fr":
                    print(f"\n📊 Stats de conversation: {len(conversation_history)} messages échangés")
                elif language == "es":
                    print(f"\n📊 Estadísticas de conversación: {len(conversation_history)} mensajes intercambiados")
                elif language == "ar":
                    print(f"\n📊 إحصائيات المحادثة: {len(conversation_history)} رسالة متبادلة")
                
        except KeyboardInterrupt:
            print("\n\n👋 Conversation interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("🔄 Continuing conversation...")
            continue

def check_openai_setup():
    """Check if OpenAI is properly configured."""
    from main import get_openai_client
    
    print("🔍 Checking OpenAI configuration...")
    client = get_openai_client()
    
    if client is None:
        print("❌ OpenAI client not available!")
        print("💡 Make sure to set your OPENAI_API_KEY environment variable:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("🔄 Will use mock responses as fallback.")
        return False
    else:
        print("✅ OpenAI client configured successfully!")
        return True

def main():
    """Main function to run the interactive test."""
    print_header()
    
    # Check OpenAI setup
    openai_available = check_openai_setup()
    print()
    
    try:
        # Step 1: Select language
        language = select_language()
        
        # Step 2: Select detail level
        detail_level = select_detail_level(language)
        
        # Step 3: Select topics
        topics, topic_keys = select_topics(language)
        
        # Step 4: Select subtopics
        subtopics = select_subtopics(topic_keys, language)
        
        # Build user preferences
        user_preferences = {
            "language": language,
            "detail_level": detail_level,
            "subjects": topics,
            "subtopics": subtopics
        }
        
        # Step 5: Ask about parallel testing
        if language == "en":
            test_parallel = input("\n🔍 Test parallel analysis for specific subjects? (y/n): ").strip().lower()
        elif language == "fr":
            test_parallel = input("\n🔍 Tester l'analyse parallèle pour les sujets spécifiques? (o/n): ").strip().lower()
        elif language == "es":
            test_parallel = input("\n🔍 ¿Probar análisis paralelo para temas específicos? (s/n): ").strip().lower()
        elif language == "ar":
            test_parallel = input("\n🔍 اختبار التحليل المتوازي للمواضيع المحددة؟ (ن/ل): ").strip().lower()
        
        enable_parallel_test = test_parallel in ['y', 'yes', 'o', 'oui', 's', 'si', 'sí', 'ن', 'نعم']
        
        # Add parallel testing flag to preferences
        user_preferences["enable_parallel_test"] = enable_parallel_test
        
        # Display summary
        print(f"\n📋 Your Preferences Summary:")
        print(f"   Language: {LANGUAGES[language]}")
        print(f"   Detail Level: {detail_level}")
        print(f"   Topics: {', '.join(topics)}")
        print(f"   Subtopics: {', '.join(subtopics)}")
        print(f"   OpenAI Available: {'✅ Yes' if openai_available else '❌ No (using mock)'}")
        print(f"   Parallel Testing: {'✅ Enabled' if enable_parallel_test else '❌ Disabled'}")
        
        # Step 6: Start conversation
        start_conversation(user_preferences)
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    main() 