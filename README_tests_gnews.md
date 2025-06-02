# Tests GNews - Backend Prysm

Ce dossier contient des tests pour les fonctions GNews du backend Prysm, avec un focus spécial sur la fonctionnalité de limite temporelle de 24 heures.

## 📁 Fichiers

### `test_gnews.py`
Fichier de tests unitaires complets utilisant `unittest` et des mocks pour tester les fonctions GNews sans consommer d'API.

### `example_gnews_24h.py`
Script d'exemple pratique qui teste les fonctions GNews avec de vraies APIs pour démontrer la fonctionnalité de limite temporelle.

## 🚀 Utilisation

### Tests unitaires (recommandé pour le développement)

```bash
# Exécuter tous les tests unitaires
python test_gnews.py

# Exécuter les tests en mode verbose
python test_gnews.py --verbose

# Exécuter le test manuel avec de vraies APIs (attention aux quotas!)
python test_gnews.py --manual
```

### Tests d'exemple avec vraies APIs

```bash
# ⚠️ Attention: utilise les vraies APIs et consomme des quotas
python example_gnews_24h.py
```

## 🧪 Fonctionnalités testées

### ⏰ Limites temporelles
- **1 heure** : `time_period="h"` pour les articles de la dernière heure
- **24 heures** : `time_period="d"` pour les articles du dernier jour  
- **1 semaine** : `time_period="w"` pour les articles de la dernière semaine
- **Plus de 1 semaine** : Pas de filtre temporel (tous les articles)

### 🔍 Fonctions testées
- `gnews_search()` - Recherche d'articles avec filtres temporels
- `gnews_top_headlines()` - Headlines par catégorie
- `format_gnews_articles_for_prysm()` - Formatage pour l'interface Prysm
- `serpapi_google_news_search()` - API SerpAPI sous-jacente
- Mécanisme de fallback quand aucun article trouvé avec filtre temporel

### 🔄 Cas de test spéciaux
- Fallback automatique sans filtre temporel
- Gestion des formats de date invalides
- Combinaison GNews + SerpAPI
- Différentes langues et pays

## 📊 Exemples de sortie

### Test avec limite 24h
```python
# Articles des dernières 24 heures
from_date_24h = (datetime.now() - timedelta(hours=24)).isoformat() + "Z"

result = gnews_search(
    query="intelligence artificielle",
    lang="fr", 
    country="fr",
    max_articles=5,
    from_date=from_date_24h
)
```

### Test fallback
Si aucun article trouvé avec le filtre temporel, le système fait automatiquement un fallback sans filtre :

```python
# Premier appel avec time_period="d" → 0 articles
# Deuxième appel sans time_period → articles trouvés
# Résultat contient: used_fallback=True, original_time_period="d"
```

## 🔧 Configuration

### Variables d'environnement
- `SERPAPI_API_KEY` : Clé API SerpAPI (optionnel, fallback hardcodé disponible)
- `OPENAI_API_KEY` : Clé OpenAI (pour certains tests)

### Dépendances
```bash
pip install requests unittest-mock
```

## 📝 Structure des réponses

### Réponse GNews standard
```json
{
    "success": true,
    "totalArticles": 5,
    "articles": [...],
    "source": "gnews_and_serpapi",
    "gnews_count": 2,
    "serpapi_count": 3,
    "serpapi_data": {
        "related_topics": [...],
        "menu_links": [...],
        "topic_token": "..."
    }
}
```

### Réponse avec fallback
```json
{
    "success": true,
    "totalArticles": 3,
    "articles": [...],
    "used_fallback": true,
    "original_time_period": "d"
}
```

## ⚠️ Limitations et notes

### Quotas API
- **Tests unitaires** : N'utilisent pas de vraies APIs (mocks)
- **Tests manuels** : Consomment des quotas SerpAPI/GNews
- **Recommandation** : Utiliser les tests unitaires pour le développement

### Mapping temporel
- `< 1 heure` → `time_period="h"`
- `1 heure - 1 jour` → `time_period="d"`  
- `1 jour - 1 semaine` → `time_period="w"`
- `> 1 semaine` → `time_period=None` (tous les articles)

### Fallback automatique
Le système fait automatiquement un fallback sans filtre temporel si :
- Aucun article trouvé avec le filtre
- La requête avec filtre réussit (`success=True`)
- Au moins un article trouvé sans filtre

## 🐛 Debugging

### Logs utiles
```python
import logging
logging.basicConfig(level=logging.INFO)

# Les fonctions GNews loggent automatiquement :
# - Paramètres d'appel
# - Nombre d'articles trouvés  
# - Source utilisée (GNews, SerpAPI, ou combiné)
# - Utilisation du fallback
```

### Tests de débogage
```bash
# Test avec verbose pour voir tous les détails
python test_gnews.py --verbose

# Test manuel pour voir le comportement réel
python test_gnews.py --manual
```

## 🔗 Liens utiles

- [Documentation SerpAPI Google News](https://serpapi.com/google-news-api)
- [Documentation GNews API](https://gnews.io/docs/v4)
- [Code source principal](./main.py) - Fonctions GNews lignes 208-367

---

**Note** : Ces tests sont spécialement conçus pour valider la fonctionnalité de limite temporelle de 24h requise par le backend Prysm. 