"""
Client OpenAI et fonctions AI
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

import openai

import json

from modules.database.operations import update_specific_subjects_in_db
from modules.config import get_openai_key


def get_openai_client():
    """Get configured OpenAI client."""
    try:
        api_key = get_openai_key()
        client = openai.OpenAI(api_key=api_key, timeout=30.0)
        logger.info("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None

def generate_ai_response(system_prompt, conversation_history, user_message):
    """
    Generate AI response using OpenAI GPT.
    
    Args:
        system_prompt (str): System prompt for the conversation
        conversation_history (list): Previous messages in the conversation
        user_message (str): Current user message
    
    Returns:
        str: AI response or error message
    """
    try:
        client = get_openai_client()
        if not client:
            return "❌ OpenAI client initialization failed"
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"🤖 Making OpenAI request with {len(messages)} messages")
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"✅ OpenAI response generated: {len(ai_response)} characters")
        
        return ai_response
        
    except Exception as e:
        logger.error(f"❌ Error generating AI response: {e}")
        return f"❌ Une erreur s'est produite lors de la génération de la réponse: {str(e)}"

    
def build_system_prompt(user_preferences):
    """
    Build the system prompt based on user preferences.
    
    Args:
        user_preferences (dict): User preferences including subjects, subtopics, detail_level, language, specific_subjects, etc.
    
    Returns:
        str: Complete system prompt for the AI
    """
    subjects = user_preferences.get('subjects', [])
    subtopics = user_preferences.get('subtopics', [])
    specific_subjects = user_preferences.get('specific_subjects', [])
    detail_level = user_preferences.get('detail_level', 'Medium')
    language = user_preferences.get('language', 'en')
    
    # Language-specific prompts
    language_prompts = {
        'en': {
            'role': "You are a preferences discovery assistant for PrysmIOS app.",
            'task': "Your ONLY goal is to discover the user's specific news interests and preferences. DO NOT provide news articles or current events. Keep responses SHORT (max 3-4 sentences).",
            'guide': "Ask questions to understand what specific topics, companies, people, or events they want to follow. Be proactive in discovering their interests.",
            'subjects_intro': "User selected:",
            'subtopics_intro': "Subtopics:",
            'detail_intro': f"Detail level: {detail_level.lower()}.",
            'refinement_task': "Ask about specific entities they want to follow from their topics. Examples: 'Which tech companies interest you?' or 'Any specific sports teams you follow?'",
            'guidelines': "DISCOVER PREFERENCES, DON'T GIVE NEWS! Examples: Technology → Ask 'Which tech companies like Apple, Tesla, or OpenAI interest you?' Sports → Ask 'Do you follow specific teams like Lakers or players like Messi?'",
            'conversation_flow': "When you have enough specific interests, say: 'Perfect! I've learned about your interests. Your personalized news feed is ready!'"
        },
        'fr': {
            'role': "Tu es un assistant de découverte de préférences pour l'application PrysmIOS.",
            'task': "Ton SEUL objectif est de découvrir les intérêts et préférences spécifiques de l'utilisateur. NE DONNE PAS d'articles d'actualités ou d'événements actuels. Reste BREF (max 3-4 phrases).",
            'guide': "Pose des questions pour comprendre quels sujets spécifiques, entreprises, personnes ou événements ils veulent suivre. Sois proactif dans la découverte de leurs intérêts.",
            'subjects_intro': "Utilisateur a choisi :",
            'subtopics_intro': "Sous-sujets :",
            'detail_intro': f"Niveau de détail : {detail_level.lower()}.",
            'refinement_task': "Demande quelles entités spécifiques ils veulent suivre dans leurs sujets. Exemples : 'Quelles entreprises tech t'intéressent ?' ou 'Tu suis des équipes sportives particulières ?'",
            'guidelines': "DÉCOUVRE LES PRÉFÉRENCES, NE DONNE PAS D'ACTUALITÉS ! Exemples : Technologie → Demande 'Quelles entreprises comme Apple, Tesla ou OpenAI t'intéressent ?' Sport → Demande 'Tu suis des équipes comme Real Madrid ou des joueurs comme Messi ?'",
            'conversation_flow': "Quand tu as assez d'intérêts spécifiques, dis : 'Parfait ! J'ai appris tes intérêts. Ton flux d'actualités personnalisé est prêt !'"
        },
        'es': {
            'role': "Eres un asistente de descubrimiento de preferencias para la aplicación PrysmIOS.",
            'task': "Tu ÚNICO objetivo es descubrir los intereses y preferencias específicos del usuario. NO proporciones artículos de noticias o eventos actuales. Mantente BREVE (máx 3-4 frases).",
            'guide': "Haz preguntas para entender qué temas específicos, empresas, personas o eventos quieren seguir. Sé proactivo en descubrir sus intereses.",
            'subjects_intro': "Usuario eligió:",
            'subtopics_intro': "Subtemas:",
            'detail_intro': f"Nivel de detalle: {detail_level.lower()}.",
            'refinement_task': "Pregunta qué entidades específicas quieren seguir de sus temas. Ejemplos: '¿Qué empresas tecnológicas te interesan?' o '¿Sigues equipos deportivos específicos?'",
            'guidelines': "¡DESCUBRE PREFERENCIAS, NO DES NOTICIAS! Ejemplos: Tecnología → Pregunta '¿Qué empresas como Apple, Tesla u OpenAI te interesan?' Deportes → Pregunta '¿Sigues equipos como Real Madrid o jugadores como Messi?'",
            'conversation_flow': "Cuando tengas suficientes intereses específicos, di: '¡Perfecto! He aprendido sobre tus intereses. ¡Tu feed de noticias personalizado está listo!'"
        },
        'ar': {
            'role': "أنت مساعد اكتشاف التفضيلات لتطبيق PrysmIOS.",
            'task': "هدفك الوحيد هو اكتشاف اهتمامات وتفضيلات المستخدم المحددة. لا تقدم مقالات إخبارية أو أحداث جارية. كن مختصراً (حد أقصى 3-4 جمل).",
            'guide': "اطرح أسئلة لفهم المواضيع المحددة والشركات والأشخاص أو الأحداث التي يريدون متابعتها. كن استباقياً في اكتشاف اهتماماتهم.",
            'subjects_intro': "المستخدم اختار:",
            'subtopics_intro': "المواضيع الفرعية:",
            'detail_intro': f"مستوى التفصيل: {detail_level.lower()}.",
            'refinement_task': "اسأل عن الكيانات المحددة التي يريدون متابعتها من مواضيعهم. أمثلة: 'ما الشركات التقنية التي تهمك؟' أو 'هل تتابع فرق رياضية معينة؟'",
            'guidelines': "اكتشف التفضيلات، لا تعطِ أخباراً! أمثلة: التكنولوجيا → اسأل 'ما الشركات مثل آبل أو تسلا أو OpenAI التي تهمك؟' الرياضة → اسأل 'هل تتابع فرق مثل ريال مدريد أو لاعبين مثل ميسي؟'",
            'conversation_flow': "عندما تحصل على اهتمامات محددة كافية، قل: 'ممتاز! لقد تعلمت عن اهتماماتك. تدفق أخبارك الشخصي جاهز!'"
        }
    }
    
    prompt_data = language_prompts.get(language, language_prompts['en'])
    
    # Build the complete system prompt
    system_prompt = f"""IMPORTANT: You are NOT a news provider. You do NOT give news articles, headlines, or current events.

{prompt_data['role']}

{prompt_data['task']}

{prompt_data['guide']}

{prompt_data['subjects_intro']} {', '.join(subjects) if subjects else 'None specified'}

"""
    
    # Add subtopics if available
    if subtopics:
        system_prompt += f"{prompt_data['subtopics_intro']} {', '.join(subtopics)}\n\n"
    
    system_prompt += f"""{prompt_data['detail_intro']}

{prompt_data['refinement_task']}

{prompt_data['guidelines']}

{prompt_data['conversation_flow']}"""
    
    return system_prompt

def format_conversation_history(messages):
    """
    Format conversation history for OpenAI API.
    
    Args:
        messages (list): List of message objects with 'role' and 'content'
    
    Returns:
        list: Formatted messages for OpenAI API
    """
    formatted_messages = []
    
    for message in messages:
        role = message.get('role', '').lower()
        content = message.get('content', '')
        
        # Map roles to OpenAI format
        if role in ['user', 'human']:
            formatted_messages.append({"role": "user", "content": content})
        elif role in ['assistant', 'chatbot', 'ai']:
            formatted_messages.append({"role": "assistant", "content": content})
        elif role == 'system':
            formatted_messages.append({"role": "system", "content": content})
    
    return formatted_messages


def analyze_conversation_for_specific_subjects(conversation_history, user_message, language='en'):
    """
    Analyze conversation to extract specific subjects using a separate LLM call.
    
    Args:
        conversation_history (list): Previous conversation messages
        user_message (str): Current user message
        language (str): Language code for analysis
    
    Returns:
        dict: Analysis result with extracted subjects
    """
    try:
        client = get_openai_client()
        if not client:
            return {"success": False, "error": "OpenAI client not available"}
        
        # Build analysis prompt based on language
        analysis_prompts = {
            'en': """CRITICAL TASK: Extract ONLY specific entities that the USER explicitly mentions in their messages.

RULES:
1. Look ONLY at messages that start with "user:"
2. Extract ONLY what the user explicitly names or mentions
3. IGNORE everything the assistant says
4. Extract specific names, companies, people, products, events, AND specific technologies

What to extract (ONLY if user mentions them):
- Company names: "Tesla", "Apple", "Microsoft", "OpenAI", "Google"
- People names: "Elon Musk", "Tim Cook", "Biden", "Cristiano Ronaldo"
- Products: "iPhone", "ChatGPT", "PlayStation", "Rubik's Cube"
- Events: "Olympics 2024", "CES", "World Cup"
- Specific technologies: "LLMs", "GPT-4", "machine learning", "AI", "robotique", "robot"
- Specific topics: "robot qui a battu le record", "innovations en robotique"

What NOT to extract:
- Very general concepts like "technology", "sports" (without specifics)
- Things only the assistant mentioned
- Implied topics not explicitly mentioned

IMPORTANT: If user says "LLMs", "robot", "robotique", "machine learning", "AI" - these ARE specific enough to extract.

Return ONLY a JSON array of specific entities the USER explicitly mentioned: ["entity1", "entity2"]
If user mentioned no specific entities, return: []""",
            
            'fr': """TÂCHE CRITIQUE: Extraire SEULEMENT les entités spécifiques que l'UTILISATEUR mentionne explicitement dans ses messages.

RÈGLES:
1. Regarde SEULEMENT les messages qui commencent par "user:"
2. Extrait SEULEMENT ce que l'utilisateur nomme ou mentionne explicitement
3. IGNORE tout ce que l'assistant dit
4. Extrait les noms spécifiques, entreprises, personnes, produits, événements, ET technologies spécifiques

Quoi extraire (SEULEMENT si l'utilisateur les mentionne):
- Noms d'entreprises: "Tesla", "Apple", "Microsoft", "OpenAI", "Google"
- Noms de personnes: "Elon Musk", "Tim Cook", "Biden", "Cristiano Ronaldo"
- Produits: "iPhone", "ChatGPT", "PlayStation", "Rubik's Cube"
- Événements: "Jeux Olympiques 2024", "CES", "Coupe du Monde"
- Technologies spécifiques: "LLMs", "GPT-4", "apprentissage automatique", "IA", "robotique", "robot"
- Sujets spécifiques: "robot qui a battu le record", "innovations en robotique"

Quoi NE PAS extraire:
- Concepts très généraux comme "technologie", "sport" (sans spécificités)
- Choses mentionnées seulement par l'assistant
- Sujets impliqués ou suggérés

IMPORTANT: Si l'utilisateur dit "LLMs", "robot", "robotique", "apprentissage automatique", "IA" - ces termes SONT assez spécifiques pour être extraits.

Retourne SEULEMENT un array JSON d'entités spécifiques que l'UTILISATEUR a explicitement mentionnées: ["entité1", "entité2"]
Si l'utilisateur n'a mentionné aucune entité spécifique, retourne: []""",
            
            'es': """TAREA CRÍTICA: Extraer SOLO entidades específicas que el USUARIO menciona explícitamente en sus mensajes.

REGLAS:
1. Mira SOLO mensajes que empiecen con "user:"
2. Extrae SOLO lo que el usuario nombra o menciona explícitamente
3. IGNORA todo lo que dice el asistente
4. IGNORA temas generales como "IA", "tecnología", "deportes"
5. Extrae SOLO nombres específicos, empresas, personas, productos, eventos

Qué extraer (SOLO si el usuario los menciona):
- Nombres de empresas: "Tesla", "Apple", "Microsoft"
- Nombres de personas: "Elon Musk", "Tim Cook", "Biden"
- Productos: "iPhone", "ChatGPT", "PlayStation"
- Eventos: "Olimpiadas 2024", "CES", "Copa Mundial"
- Tecnologías específicas: "LLMs" (si el usuario lo dice), "GPT-4"

Qué NO extraer:
- Conceptos generales: "IA", "tecnología", "aprendizaje automático"
- Cosas mencionadas solo por el asistente
- Temas implícitos o sugeridos

Devuelve SOLO un array JSON de entidades específicas que el USUARIO mencionó explícitamente: ["entidad1", "entidad2"]
Si el usuario no mencionó entidades específicas, devuelve: []""",
            
            'ar': """مهمة حاسمة: استخراج فقط الكيانات المحددة التي يذكرها المستخدم صراحة في رسائله.

القواعد:
1. انظر فقط إلى الرسائل التي تبدأ بـ "user:"
2. استخرج فقط ما يسميه أو يذكره المستخدم صراحة
3. تجاهل كل ما يقوله المساعد
4. تجاهل المواضيع العامة مثل "الذكاء الاصطناعي"، "التكنولوجيا"، "الرياضة"
5. استخرج فقط الأسماء المحددة، الشركات، الأشخاص، المنتجات، الأحداث

ما يجب استخراجه (فقط إذا ذكرها المستخدم):
- أسماء الشركات: "تسلا"، "آبل"، "مايكروسوفت"
- أسماء الأشخاص: "إيلون ماسك"، "تيم كوك"، "بايدن"
- المنتجات: "آيفون"، "ChatGPT"، "بلايستيشن"
- الأحداث: "أولمبياد 2024"، "CES"، "كأس العالم"
- التقنيات المحددة: "LLMs" (إذا قالها المستخدم)، "GPT-4"

ما لا يجب استخراجه:
- المفاهيم العامة: "الذكاء الاصطناعي"، "التكنولوجيا"، "التعلم الآلي"
- الأشياء التي ذكرها المساعد فقط
- المواضيع الضمنية أو المقترحة

أرجع فقط مصفوفة JSON للكيانات المحددة التي ذكرها المستخدم صراحة: ["كيان1", "كيان2"]
إذا لم يذكر المستخدم أي كيانات محددة، أرجع: []"""
        }
        
        analysis_prompt = analysis_prompts.get(language, analysis_prompts['en'])
        
        # Build conversation context
        conversation_text = ""
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            role = msg.get('role', '')
            content = msg.get('content', '')
            conversation_text += f"{role}: {content}\n"
        
        conversation_text += f"user: {user_message}\n"
        
        # Create analysis messages
        messages = [
            {"role": "system", "content": analysis_prompt},
            {"role": "user", "content": f"Conversation to analyze:\n{conversation_text}"}
        ]
        
        # Generate analysis
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200,
            temperature=0.3
        )
        
        analysis_result = response.choices[0].message.content.strip()
        
        # Try to parse JSON
        try:
            specific_subjects = json.loads(analysis_result)
            if isinstance(specific_subjects, list):
                # Filter out empty strings and duplicates
                specific_subjects = list(set([s.strip() for s in specific_subjects if s.strip()]))
                
                return {
                    "success": True,
                    "specific_subjects": specific_subjects,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            else:
                return {"success": False, "error": "Invalid response format"}
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis result as JSON: {analysis_result}")
            return {"success": False, "error": "Failed to parse analysis result"}
            
    except Exception as e:
        logger.error(f"Error analyzing conversation for specific subjects: {e}")
        return {"success": False, "error": str(e)}

# --- Background Analysis Helper ---

def analyze_and_update_specific_subjects(user_id, conversation_history, user_message, language):
    """
    Background function to analyze conversation and update specific subjects.
    This runs in a separate thread to not block the main conversation response.
    """
    try:
        logger.info(f"Background analysis started for user {user_id}")
        
        # Analyze conversation for specific subjects
        analysis_result = analyze_conversation_for_specific_subjects(
            conversation_history, user_message, language
        )
        
        if analysis_result["success"] and analysis_result.get("specific_subjects"):
            # Update database with new specific subjects
            update_result = update_specific_subjects_in_db(
                user_id, analysis_result["specific_subjects"]
            )
            
            if update_result["success"]:
                logger.info(f"Background analysis completed for user {user_id}. New subjects: {analysis_result['specific_subjects']}")
        else:
            logger.info(f"Background analysis completed for user {user_id}. No new subjects found.")
            
    except Exception as e:
        logger.error(f"Error in background analysis for user {user_id}: {e}")
