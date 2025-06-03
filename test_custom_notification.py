#!/usr/bin/env python3
"""
Test custom notification for specific user
"""
import sys
import os

# Add main to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.notifications.push import send_push_notification
import firebase_admin

def test_custom_notification():
    """Test notification with custom French message"""
    
    try:
        firebase_admin.initialize_app()
    except ValueError:
        pass  # Already initialized
    
    print("🧪 TEST DE NOTIFICATION PERSONNALISÉE")
    print("=" * 50)
    
    user_id = "M4nTf6IhNPO2xYIGJsLZWRwhewr1"
    title = "🧪 Test de notification"
    body = "je teste juste si les notifs marchent, si oui dis le moi"
    
    print(f"👤 User ID: {user_id}")
    print(f"📧 Titre: {title}")
    print(f"💬 Message: {body}")
    print()
    
    print("📤 Envoi de la notification...")
    
    result = send_push_notification(
        user_id=user_id,
        title=title,
        body=body
    )
    
    print("\n📱 RÉSULTAT DU TEST:")
    print("-" * 30)
    
    if result.get('success'):
        print(f"✅ SUCCÈS! Notification envoyée!")
        print(f"📨 Message ID: {result.get('message_id')}")
        print(f"📱 Token utilisé: {result.get('token_used')}")
        print(f"📧 Titre envoyé: {result.get('title')}")
        print(f"💬 Corps envoyé: {result.get('body')}")
        print()
        print("🎉 La notification devrait apparaître sur l'appareil TestFlight!")
        print("📱 L'utilisateur peut maintenant confirmer si ça marche!")
    else:
        print(f"❌ ÉCHEC de l'envoi:")
        print(f"🚨 Erreur: {result.get('error')}")
        print(f"🔍 Type d'erreur: {result.get('error_type')}")
        print(f"💡 Suggestion: {result.get('suggestion')}")

if __name__ == "__main__":
    test_custom_notification() 