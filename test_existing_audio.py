#!/usr/bin/env python3
"""
Test des timestamps avec les fichiers audio existants
"""

import os
import sys
from typing import Dict, Any

# Add modules to path
sys.path.append('modules')

def load_existing_timeline():
    """Load timeline from existing JSON file"""
    import json
    
    timeline_files = [f for f in os.listdir('.') if f.startswith('timeline_') and f.endswith('.json')]
    
    if not timeline_files:
        print("❌ Aucun fichier timeline trouvé")
        return None
        
    latest_timeline = sorted(timeline_files)[-1]
    print(f"📊 Chargement du timeline: {latest_timeline}")
    
    with open(latest_timeline, 'r') as f:
        timeline = json.load(f)
    
    return timeline

def show_existing_files():
    """Show available audio files"""
    print("\n🎵 Fichiers audio disponibles:")
    
    wav_files = [f for f in os.listdir('.') if f.endswith('.wav')]
    chunk_files = [f for f in wav_files if f.startswith('chunk_')]
    podcast_files = [f for f in wav_files if 'podcast' in f or 'test' in f]
    
    print("\n📁 Chunks individuels:")
    for f in sorted(chunk_files)[-5:]:  # Derniers 5
        size_mb = os.path.getsize(f) / (1024*1024)
        print(f"   {f} ({size_mb:.1f}MB)")
    
    print("\n📁 Podcasts complets:")
    for f in sorted(podcast_files)[-3:]:  # Derniers 3
        size_mb = os.path.getsize(f) / (1024*1024)
        print(f"   {f} ({size_mb:.1f}MB)")

def test_timeline_data():
    """Test timeline data structure"""
    timeline = load_existing_timeline()
    
    if not timeline:
        return
    
    print("\n📊 ANALYSE DU TIMELINE")
    print("-" * 60)
    
    total_sections = len(timeline)
    print(f"Nombre de sections: {total_sections}")
    
    for i, (time_range, section_info) in enumerate(timeline.items(), 1):
        start = section_info.get('start_seconds', 0)
        end = section_info.get('end_seconds', 0)
        duration = end - start
        section_name = section_info.get('section_name', 'Unknown')
        
        print(f"{i:2d}. {section_name:<15} | {start:6.1f}s - {end:6.1f}s | {duration:5.1f}s")
    
    if timeline:
        total_duration = max([info.get('end_seconds', 0) for info in timeline.values()])
        print(f"\nDurée totale estimée: {total_duration:.1f}s ({total_duration/60:.1f}min)")

def interactive_timestamp_test():
    """Test interactif des timestamps"""
    from modules.interaction.chunked_podcast import find_article_at_timestamp, format_timestamp_for_display
    
    timeline = load_existing_timeline()
    if not timeline:
        return
    
    total_duration = max([info.get('end_seconds', 0) for info in timeline.values()])
    
    print(f"\n🎮 TEST INTERACTIF DES TIMESTAMPS")
    print(f"Durée totale: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    print("Commandes:")
    print("  <nombre>     - Tester un timestamp (ex: 45.5)")
    print("  timeline     - Afficher le timeline")
    print("  random       - Tester 5 timestamps aléatoires")
    print("  quit         - Quitter")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n> ").strip().lower()
            
            if user_input in ['quit', 'exit', 'q']:
                break
            elif user_input == 'timeline':
                test_timeline_data()
            elif user_input == 'random':
                import random
                print("\n🎲 Test de 5 timestamps aléatoires:")
                for i in range(5):
                    timestamp = random.uniform(0, total_duration)
                    test_single_timestamp(timeline, timestamp, f"Test {i+1}")
            else:
                try:
                    timestamp = float(user_input)
                    test_single_timestamp(timeline, timestamp)
                except ValueError:
                    print("❌ Commande invalide. Entrez un nombre ou une commande.")
                    
        except KeyboardInterrupt:
            print("\n👋 Au revoir!")
            break
        except EOFError:
            break

def test_single_timestamp(timeline: Dict[str, Any], timestamp: float, label: str = ""):
    """Test un timestamp spécifique"""
    from modules.interaction.chunked_podcast import find_article_at_timestamp, format_timestamp_for_display
    
    section_info = find_article_at_timestamp(timeline, timestamp)
    
    prefix = f"[{label}] " if label else ""
    
    if section_info:
        print(f"\n🎯 {prefix}TIMESTAMP: {timestamp:.1f}s ({format_timestamp_for_display(timestamp)})")
        print(f"📍 Section: {section_info['section_name']}")
        print(f"⏰ Plage: {section_info['formatted_range']}")
        print(f"📝 Contenu: {section_info['content_preview'][:80]}...")
        if section_info.get('article_id'):
            print(f"🔗 Article ID: {section_info['article_id']}")
    else:
        print(f"❌ {prefix}Aucune section trouvée à {timestamp:.1f}s")

def main():
    print("🧪 TEST DES TIMESTAMPS AVEC FICHIERS EXISTANTS")
    print("=" * 55)
    
    show_existing_files()
    test_timeline_data()
    interactive_timestamp_test()

if __name__ == "__main__":
    main() 