#!/usr/bin/env python3
"""
Interactive tester with corrected timeline
"""

import json
import sys
import os
import random

# Add modules to path
sys.path.append('modules')
from modules.interaction.chunked_podcast import find_article_at_timestamp, format_timestamp_for_display

def load_corrected_timeline():
    """Load the corrected timeline"""
    corrected_files = [f for f in os.listdir('.') if f.startswith('corrected_timeline_') and f.endswith('.json')]
    
    if not corrected_files:
        print("❌ Aucun timeline corrigé trouvé. Exécutez d'abord fix_timeline_with_existing_files.py")
        return None
        
    latest_file = sorted(corrected_files)[-1]
    print(f"📊 Chargement: {latest_file}")
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def show_timeline(timeline):
    """Show timeline summary"""
    print(f"\n📊 TIMELINE CORRIGÉ")
    print("-" * 65)
    print(f"{'Plage':<12} {'Durée':<8} {'Section':<15} {'Aperçu'}")
    print("-" * 65)
    
    for time_range, info in timeline.items():
        start_str = format_timestamp_for_display(info['start_seconds'])
        end_str = format_timestamp_for_display(info['end_seconds'])
        duration = info['duration_seconds']
        section = info['section_name']
        preview = info['content_preview'][:25] + "..." if len(info['content_preview']) > 25 else info['content_preview']
        
        print(f"{start_str}-{end_str:<6} {duration:>6.1f}s {section:<15} {preview}")
    
    total_duration = max([info['end_seconds'] for info in timeline.values()])
    print("-" * 65)
    print(f"Total: {format_timestamp_for_display(total_duration)}")

def test_timestamp(timeline, timestamp):
    """Test a specific timestamp"""
    result = find_article_at_timestamp(timeline, timestamp)
    
    if result:
        print(f"\n🎯 TIMESTAMP: {timestamp:.1f}s ({format_timestamp_for_display(timestamp)})")
        print(f"📍 Section: {result['section_name']}")
        print(f"⏰ Plage: {result['formatted_range']}")
        print(f"📝 Contenu: {result['content_preview'][:100]}...")
        if result.get('article_id'):
            print(f"🔗 Article ID: {result['article_id']}")
    else:
        print(f"❌ Aucune section à {timestamp:.1f}s")

def interactive_mode():
    """Interactive testing mode"""
    timeline = load_corrected_timeline()
    if not timeline:
        return
    
    total_duration = max([info['end_seconds'] for info in timeline.values()])
    
    show_timeline(timeline)
    
    print(f"\n🎮 MODE INTERACTIF")
    print(f"Durée totale: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    print("Commandes:")
    print("  <nombre>     - Tester timestamp (ex: 45.5)")
    print("  timeline     - Réafficher timeline")
    print("  random       - 5 timestamps aléatoires")
    print("  sections     - Tester frontières sections")
    print("  demo         - Demo des sections")
    print("  quit         - Quitter")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n> ").strip().lower()
            
            if user_input in ['quit', 'exit', 'q']:
                break
            elif user_input == 'timeline':
                show_timeline(timeline)
            elif user_input == 'random':
                print(f"\n🎲 5 timestamps aléatoires:")
                for i in range(5):
                    ts = random.uniform(0, total_duration)
                    print(f"\n--- Test {i+1} ---")
                    test_timestamp(timeline, ts)
            elif user_input == 'sections':
                print(f"\n🔍 Test des frontières:")
                for time_range, info in timeline.items():
                    start = info['start_seconds']
                    end = info['end_seconds']
                    mid = (start + end) / 2
                    
                    print(f"\n--- {info['section_name']} ---")
                    print(f"Début ({start:.1f}s):")
                    test_timestamp(timeline, start)
                    print(f"Milieu ({mid:.1f}s):")
                    test_timestamp(timeline, mid)
            elif user_input == 'demo':
                print(f"\n🎬 DEMO - Simulation lecture:")
                for i in range(0, int(total_duration), 10):
                    print(f"\n⏱️ {i}s:")
                    test_timestamp(timeline, i)
            else:
                try:
                    timestamp = float(user_input)
                    if 0 <= timestamp <= total_duration:
                        test_timestamp(timeline, timestamp) 
                    else:
                        print(f"❌ Timestamp hors limite (0-{total_duration:.1f}s)")
                except ValueError:
                    print("❌ Commande invalide. Tapez un nombre ou une commande.")
                    
        except KeyboardInterrupt:
            print("\n👋 Au revoir!")
            break
        except EOFError:
            break

def main():
    print("🧪 TESTEUR INTERACTIF - TIMELINE CORRIGÉ")
    print("=" * 45)
    interactive_mode()

if __name__ == "__main__":
    main() 