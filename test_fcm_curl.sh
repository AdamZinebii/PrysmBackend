#!/bin/bash

# Script pour tester un FCM token directement avec l'API Firebase REST
# Usage: ./test_fcm_curl.sh <FCM_TOKEN>

echo "🧪 Test FCM Token avec curl"
echo "=========================="

if [ "$#" -ne 1 ]; then
    echo "❌ Usage: $0 <FCM_TOKEN>"
    echo "Example: $0 dA1B2c3D4e5F6g7H8i9J..."
    exit 1
fi

FCM_TOKEN="$1"

# Récupérer un access token Firebase (besoin des credentials)
echo "🔑 Génération du token d'accès Firebase..."

# Alternative: Test avec endpoint Firebase direct
PROJECT_ID="prysmios"
ENDPOINT="https://fcm.googleapis.com/v1/projects/${PROJECT_ID}/messages:send"

echo "📱 Token FCM à tester: ${FCM_TOKEN:0:20}...${FCM_TOKEN: -20}"
echo "🎯 Endpoint: $ENDPOINT"

# Test message simple
TEST_MESSAGE='{
  "message": {
    "token": "'$FCM_TOKEN'",
    "notification": {
      "title": "🧪 Test FCM Token",
      "body": "Test de validité du token avec curl"
    }
  }
}'

echo "📤 Envoi du message test..."
echo "⚠️  Note: Il faut un access token Firebase valide pour ce test"
echo ""
echo "Utilise plutôt: python test_fcm_token.py <USER_ID>" 