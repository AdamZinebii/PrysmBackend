# Modules Prysm Backend

Structure modulaire du backend Prysm pour améliorer la maintenabilité et l'organisation du code.

## 📁 Structure

```
modules/
├── config.py              # Configuration et clés API
├── ai/
│   └── client.py          # Client OpenAI et fonctions AI
├── audio/
│   └── cartesia.py        # Text-to-Speech avec Cartesia
├── news/
│   └── serpapi.py         # Recherche de nouvelles (SerpAPI/GNews)
├── notifications/
│   └── push.py            # Notifications push Firebase
└── utils/
    └── country.py         # Utilitaires pour les pays
```

## 🚀 Utilisation

### Dans main.py (après refactoring) :

```python
# Import des modules
from modules.config import get_openai_key
from modules.ai.client import get_openai_client, generate_ai_response
from modules.audio.cartesia import generate_text_to_speech
from modules.notifications.push import send_push_notification
from modules.news.serpapi import serpapi_google_news_search
from modules.utils.country import get_country_code, get_user_country_from_db

# Utilisation directe
client = get_openai_client()
audio = generate_text_to_speech("Hello world")
result = send_push_notification("user123", "Title", "Body")
```

### Avantages :

✅ **Séparation des responsabilités**  
✅ **Code plus maintenable**  
✅ **Réutilisabilité**  
✅ **Tests plus faciles**  
✅ **Compatible Firebase Functions**  

## 🔧 Migration

1. **Les modules sont créés** ✅
2. **Main.py reste intact** pour l'instant
3. **Tu peux maintenant** :
   - Tester chaque module indépendamment
   - Importer graduellement dans main.py
   - Retirer les fonctions du main.py au fur et à mesure

## 🧪 Test des modules

```python
# Test du module AI
from modules.ai.client import get_openai_client
client = get_openai_client()

# Test du module notifications  
from modules.notifications.push import send_push_notification
result = send_push_notification("user_id", "Test", "Message")
```

## 📦 Compatibilité Firebase

Tous les modules sont compatibles avec Firebase Functions car ils :
- Utilisent les mêmes imports Firebase
- Conservent la même logique métier
- Respectent les timeouts et contraintes Cloud Functions 