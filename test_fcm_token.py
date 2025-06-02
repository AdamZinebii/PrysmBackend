#!/usr/bin/env python3
"""
Test script pour vérifier la validité des FCM tokens
"""
import sys
import os
import json

# Ajouter le main au path pour utiliser les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firebase_admin import firestore, messaging
import firebase_admin
from firebase_admin import credentials

# Initialisation Firebase Admin
def init_firebase():
    """Initialise Firebase Admin si pas déjà fait"""
    try:
        firebase_admin.get_app()
    except ValueError:
        # App pas encore initialisée - utilise les credentials par défaut
        firebase_admin.initialize_app()

def test_fcm_token_validity(user_id):
    """
    Teste si le FCM token d'un utilisateur est valide
    """
    try:
        print(f"🔍 Test FCM token pour user: {user_id}")
        print("-" * 50)
        
        # Init Firebase
        init_firebase()
        
        # Connexion à Firestore
        db = firestore.client()
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            print(f"❌ User document non trouvé pour: {user_id}")
            return False
        
        user_data = user_doc.to_dict()
        fcm_token = user_data.get('fcmToken')
        
        print(f"📱 FCM Token trouvé: {fcm_token[:20]}...{fcm_token[-20:] if fcm_token and len(fcm_token) > 40 else 'Token court ou None'}")
        
        if not fcm_token:
            print("❌ Aucun FCM token trouvé pour cet utilisateur")
            return False
        
        # Test 1: Envoi d'un message test
        test_message = messaging.Message(
            notification=messaging.Notification(
                title="🧪 Test FCM Token",
                body="Test de validité du token FCM"
            ),
            token=fcm_token
        )
        
        print("📤 Envoi du message test...")
        response = messaging.send(test_message)
        print(f"✅ Token VALIDE ! Message ID: {response}")
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Erreur lors du test: {error_str}")
        
        # Analyse des erreurs communes
        if "Requested entity was not found" in error_str:
            print("💡 Possible cause: Token FCM expiré ou invalide")
        elif "The registration token is not a valid FCM registration token" in error_str:
            print("💡 Cause: Format de token FCM invalide")
        elif "Sender ID mismatch" in error_str:
            print("💡 Cause: Token appartient à un autre projet Firebase")
        
        return False

def test_multiple_users():
    """
    Teste plusieurs utilisateurs
    """
    test_users = [
        "6wot9fy9YBgLrf9CWRq4W1aJj6O2", 
        "hWR0Z7AvhQU3EWB5jdm5eg2Tqzz1",
        "GDofaXAIvnPp5jjSF2D1FHuPfly1"
    ]
    
    print("🎯 Test des FCM tokens pour plusieurs utilisateurs")
    print("=" * 60)
    
    for user_id in test_users:
        test_fcm_token_validity(user_id)
        print()

if __name__ == "__main__":
    # Test manuel
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        test_fcm_token_validity(user_id)
    else:
        test_multiple_users() 