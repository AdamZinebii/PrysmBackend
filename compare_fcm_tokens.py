#!/usr/bin/env python3
"""
Script pour comparer les FCM tokens en détail
"""
import sys
import os

# Ajouter le main au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firebase_admin import firestore
import firebase_admin

def init_firebase():
    """Initialise Firebase Admin si pas déjà fait"""
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()

def get_fcm_token_details(user_id):
    """Récupère et analyse le token FCM d'un utilisateur"""
    try:
        init_firebase()
        db = firestore.client()
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            return None, f"User {user_id} not found"
        
        user_data = user_doc.to_dict()
        fcm_token = user_data.get('fcmToken')
        
        if not fcm_token:
            return None, f"No FCM token for user {user_id}"
        
        return fcm_token, "OK"
        
    except Exception as e:
        return None, str(e)

def analyze_token(token, label):
    """Analyse détaillée d'un token"""
    print(f"\n🔍 {label}")
    print("=" * 50)
    print(f"📏 Longueur: {len(token)} caractères")
    print(f"🔤 Premier caractère: '{token[0]}' (ASCII: {ord(token[0])})")
    print(f"🔤 Dernier caractère: '{token[-1]}' (ASCII: {ord(token[-1])})")
    print(f"📝 Token complet: {repr(token)}")
    print(f"🧹 Token stripped: {repr(token.strip())}")
    
    # Vérifier les caractères spéciaux
    special_chars = []
    for i, char in enumerate(token):
        if ord(char) < 32 or ord(char) > 126:  # Caractères non-printables
            special_chars.append(f"Position {i}: '{char}' (ASCII: {ord(char)})")
    
    if special_chars:
        print(f"⚠️  Caractères spéciaux détectés:")
        for char_info in special_chars:
            print(f"   - {char_info}")
    else:
        print("✅ Aucun caractère spécial détecté")
    
    # Hash du token pour comparaison
    import hashlib
    token_hash = hashlib.md5(token.encode()).hexdigest()
    print(f"🔐 Hash MD5: {token_hash}")
    
    return token.strip(), token_hash

def compare_tokens():
    """Compare les tokens des deux utilisateurs"""
    print("🎯 Comparaison détaillée des FCM tokens")
    print("=" * 60)
    
    user1 = "6wot9fy9YBgLrf9CWRq4W1aJj6O2"  # Qui marche
    user2 = "hWR0Z7AvhQU3EWB5jdm5eg2Tqzz1"  # Qui marche pas
    
    # Récupérer les tokens
    token1, status1 = get_fcm_token_details(user1)
    token2, status2 = get_fcm_token_details(user2)
    
    if not token1:
        print(f"❌ Erreur User1: {status1}")
        return
    
    if not token2:
        print(f"❌ Erreur User2: {status2}")
        return
    
    # Analyser chaque token
    clean_token1, hash1 = analyze_token(token1, "USER 1 (✅ Marche)")
    clean_token2, hash2 = analyze_token(token2, "❌ Marche pas)")
    
    # Comparaison
    print(f"\n🔄 COMPARAISON")
    print("=" * 30)
    print(f"📏 Longueurs: {len(token1)} vs {len(token2)}")
    print(f"🔐 Hashes identiques: {hash1 == hash2}")
    print(f"🧹 Tokens nettoyés identiques: {clean_token1 == clean_token2}")
    print(f"📝 Tokens bruts identiques: {token1 == token2}")
    
    if token1 != token2:
        print(f"\n🚨 DIFFÉRENCES DÉTECTÉES!")
        
        # Comparaison caractère par caractère
        min_len = min(len(token1), len(token2))
        differences = []
        
        for i in range(min_len):
            if token1[i] != token2[i]:
                differences.append(f"Position {i}: '{token1[i]}' vs '{token2[i]}'")
        
        if len(token1) != len(token2):
            differences.append(f"Longueurs différentes: {len(token1)} vs {len(token2)}")
        
        for diff in differences[:10]:  # Limite à 10 différences
            print(f"   - {diff}")
    else:
        print("✅ Tokens identiques")

if __name__ == "__main__":
    compare_tokens() 