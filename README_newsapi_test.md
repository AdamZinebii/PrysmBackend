# Test NewsAPI - Articles des dernières 48 heures

Ce fichier de test utilise l'[API NewsAPI](https://newsapi.org/docs) pour récupérer les articles de presse des dernières 48 heures.

## Configuration

### 1. Obtenir une clé API NewsAPI

1. Rendez-vous sur [newsapi.org](https://newsapi.org/)
2. Créez un compte gratuit
3. Récupérez votre clé API
4. Remplacez `YOUR_NEWSAPI_KEY_HERE` dans `modules/config.py` par votre vraie clé

### 2. Variable d'environnement (recommandé)

```bash
export NEWSAPI_API_KEY="votre_cle_api_ici"
```

## Utilisation

### Lancer le test complet

```bash
python test_newsapi_48h.py
```

### Fonctionnalités du test

Le script effectue 3 tests différents :

#### Test 1: Recherche générale
- **Query** : "technology OR science OR business"
- **Période** : 48 dernières heures
- **Langue** : Anglais
- **Tri** : Par date de publication
- **Résultat** : `newsapi_general_48h.json`

#### Test 2: Top Headlines Technologie
- **Catégorie** : Technology
- **Pays** : États-Unis
- **Période** : 48 dernières heures (filtré côté client)
- **Résultat** : `newsapi_tech_headlines_48h.json`

#### Test 3: Sources spécifiques
- **Sources** : TechCrunch, Ars Technica
- **Période** : 48 dernières heures
- **Tri** : Par date de publication
- **Résultat** : `newsapi_sources_48h.json`

## Structure de la réponse

### Réponse réussie

```json
{
  "success": true,
  "status": "ok",
  "totalResults": 1234,
  "articlesReturned": 20,
  "articles": [
    {
      "source": {
        "id": "techcrunch",
        "name": "TechCrunch"
      },
      "author": "John Doe",
      "title": "Titre de l'article",
      "description": "Description de l'article...",
      "url": "https://example.com/article",
      "urlToImage": "https://example.com/image.jpg",
      "publishedAt": "2024-01-15T10:30:00Z",
      "content": "Contenu de l'article..."
    }
  ],
  "time_period": "2024-01-13T10:30:00Z à 2024-01-15T10:30:00Z",
  "query_used": "technology OR science OR business",
  "sources_used": null
}
```

### Réponse d'erreur

```json
{
  "success": false,
  "error": "Invalid API key",
  "status_code": 401
}
```

## Endpoints utilisés

### 1. `/everything` - Recherche d'articles

Permet de rechercher dans tous les articles disponibles avec :
- **Filtre temporel** : `from` et `to` en format ISO 8601
- **Query** : Termes de recherche avec opérateurs booléens
- **Sources** : Liste de sources spécifiques
- **Langue** : Code de langue (en, fr, es, etc.)
- **Tri** : relevancy, popularity, publishedAt

### 2. `/top-headlines` - Gros titres

Récupère les gros titres avec :
- **Pays** : Code pays à 2 lettres
- **Catégorie** : business, entertainment, general, health, science, sports, technology
- **Sources** : Sources spécifiques (incompatible avec pays/catégorie)

## Limites de l'API

### Plan gratuit
- **100 requêtes/jour**
- **Articles des 30 derniers jours uniquement**
- **Pas d'usage commercial**

### Plan payant
- Plus de requêtes
- Historique complet
- Usage commercial autorisé

## Gestion des erreurs

Le script gère automatiquement :
- **401** : Clé API invalide
- **429** : Limite de taux dépassée
- **Timeout** : Délai d'attente dépassé
- **Erreurs réseau** : Problèmes de connexion

## Fichiers générés

Après exécution, trois fichiers JSON sont créés :
1. `newsapi_general_48h.json` - Recherche générale
2. `newsapi_tech_headlines_48h.json` - Headlines technologie
3. `newsapi_sources_48h.json` - Sources spécifiques

## Exemple d'output

```
🚀 Test NewsAPI - Articles des dernières 48 heures
============================================================

🔍 Test 1: Recherche générale (toutes catégories)
✅ 20 articles trouvés

📰 Breaking: New AI Technology Revolutionizes Healthcare
📅 2024-01-15T08:30:00Z | 🏢 TechCrunch
📝 A groundbreaking AI system has been developed that can diagnose diseases with 99% accuracy...
🔗 https://techcrunch.com/2024/01/15/ai-healthcare-breakthrough
---

📰 Test 2: Top Headlines - Technologie (US)
✅ 15 gros titres tech trouvés

🎉 Tests terminés! Consultez les fichiers JSON générés pour les détails complets.
```

## Intégration dans le projet

Ce client NewsAPI peut être intégré dans le système Prysm existant comme source alternative ou complémentaire aux APIs GNews et SerpAPI actuellement utilisées. 