#!/usr/bin/env python3
"""
Comprehensive architecture verification script for Prysm Backend
Checks imports, circular dependencies, function organization, and overall structure
"""

import os
import sys
import ast
import importlib.util
from collections import defaultdict, deque
import traceback

def check_file_structure():
    """Check if all expected files and directories exist."""
    print("🏗️  VÉRIFICATION DE LA STRUCTURE DES FICHIERS")
    print("=" * 60)
    
    expected_files = [
        "main.py",
        "modules/__init__.py",
        "modules/config.py",
        "modules/ai/client.py",
        "modules/audio/cartesia.py",
        "modules/content/generation.py",
        "modules/content/podcast.py",
        "modules/content/topics.py",
        "modules/database/operations.py",
        "modules/news/news_helper.py",
        "modules/news/serpapi.py",
        "modules/notifications/push.py",
        "modules/scheduling/tasks.py",
        "modules/utils/country.py"
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in expected_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path} - MANQUANT")
    
    print(f"\n📊 Résultat: {len(existing_files)}/{len(expected_files)} fichiers trouvés")
    
    if missing_files:
        print(f"⚠️  Fichiers manquants: {len(missing_files)}")
        return False
    
    return True

def extract_imports_from_file(file_path):
    """Extract import statements from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        return imports
    except Exception as e:
        print(f"Erreur lors de l'analyse de {file_path}: {e}")
        return []

def check_circular_dependencies():
    """Check for circular dependencies between modules."""
    print("\n🔄 VÉRIFICATION DES DÉPENDANCES CIRCULAIRES")
    print("=" * 60)
    
    # Build dependency graph
    dependencies = defaultdict(set)
    module_files = []
    
    for root, dirs, files in os.walk('modules'):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(root, file)
                module_files.append(file_path)
    
    # Add main.py
    if os.path.exists('main.py'):
        module_files.append('main.py')
    
    for file_path in module_files:
        imports = extract_imports_from_file(file_path)
        
        # Convert file path to module name
        if file_path == 'main.py':
            from_module = 'main'
        else:
            from_module = file_path[:-3].replace('/', '.')
        
        for imp in imports:
            if imp.startswith('modules.'):
                to_module = imp
                dependencies[from_module].add(to_module)
    
    # Detect cycles using DFS
    def has_cycle(graph):
        color = {}  # 0: white, 1: gray, 2: black
        cycles = []
        
        def dfs(node, path):
            if node in color:
                if color[node] == 1:  # Gray node - cycle detected
                    cycle_start = path.index(node)
                    cycles.append(path[cycle_start:] + [node])
                    return True
                elif color[node] == 2:  # Black node - already processed
                    return False
            
            color[node] = 1  # Mark as gray
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if dfs(neighbor, path):
                    return True
            
            path.pop()
            color[node] = 2  # Mark as black
            return False
        
        for node in graph:
            if node not in color:
                if dfs(node, []):
                    break
        
        return cycles
    
    cycles = has_cycle(dependencies)
    
    if cycles:
        print("❌ DÉPENDANCES CIRCULAIRES DÉTECTÉES:")
        for i, cycle in enumerate(cycles, 1):
            print(f"   Cycle {i}: {' → '.join(cycle)}")
        return False
    else:
        print("✅ Aucune dépendance circulaire détectée")
        return True

def test_imports():
    """Test if all module imports work correctly."""
    print("\n📦 TEST DES IMPORTS")
    print("=" * 60)
    
    # Test main.py imports first
    print("Testing main.py imports...")
    
    import_tests = [
        ("modules.config", "get_openai_key"),
        ("modules.ai.client", "get_openai_client"),
        ("modules.audio.cartesia", "generate_text_to_speech_cartesia"),
        ("modules.content.generation", "get_topic_summary"),
        ("modules.database.operations", "get_user_preferences_from_db"),
        ("modules.news.serpapi", "gnews_search"),
        ("modules.notifications.push", "send_push_notification"),
    ]
    
    successful_imports = 0
    failed_imports = []
    
    for module_name, function_name in import_tests:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, function_name):
                print(f"✅ {module_name}.{function_name}")
                successful_imports += 1
            else:
                print(f"❌ {module_name}.{function_name} - Fonction non trouvée")
                failed_imports.append(f"{module_name}.{function_name}")
        except ImportError as e:
            print(f"❌ {module_name} - Erreur d'import: {e}")
            failed_imports.append(module_name)
        except Exception as e:
            print(f"❌ {module_name} - Erreur: {e}")
            failed_imports.append(module_name)
    
    print(f"\n📊 Résultat: {successful_imports}/{len(import_tests)} imports réussis")
    
    if failed_imports:
        print("❌ Imports échoués:")
        for imp in failed_imports:
            print(f"   • {imp}")
        return False
    
    return True

def analyze_function_distribution():
    """Analyze how functions are distributed across modules."""
    print("\n📊 ANALYSE DE LA DISTRIBUTION DES FONCTIONS")
    print("=" * 60)
    
    def count_functions_in_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
            
            return functions
        except Exception as e:
            print(f"Erreur analyse {file_path}: {e}")
            return []
    
    # Analyze all files
    all_files = ['main.py']
    
    for root, dirs, files in os.walk('modules'):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                all_files.append(os.path.join(root, file))
    
    total_functions = 0
    distribution = {}
    
    for file_path in all_files:
        if os.path.exists(file_path):
            functions = count_functions_in_file(file_path)
            total_functions += len(functions)
            
            if file_path == 'main.py':
                category = "HTTP Endpoints"
            elif 'content' in file_path:
                category = "Content Generation"
            elif 'database' in file_path:
                category = "Database Operations"
            elif 'news' in file_path:
                category = "News/Search"
            elif 'ai' in file_path:
                category = "AI/OpenAI"
            elif 'audio' in file_path:
                category = "Audio/TTS"
            elif 'notifications' in file_path:
                category = "Push Notifications"
            elif 'scheduling' in file_path:
                category = "Scheduling/Tasks"
            elif 'utils' in file_path:
                category = "Utilities"
            else:
                category = "Other"
            
            if category not in distribution:
                distribution[category] = []
            
            distribution[category].append({
                'file': file_path,
                'functions': functions,
                'count': len(functions)
            })
    
    print(f"Total fonctions: {total_functions}")
    print("\nDistribution par catégorie:")
    
    for category, files in sorted(distribution.items()):
        total_in_category = sum(f['count'] for f in files)
        print(f"\n📂 {category}: {total_in_category} fonctions")
        
        for file_info in files:
            print(f"   📄 {file_info['file']}: {file_info['count']} fonctions")
            for func in file_info['functions'][:5]:  # Show first 5 functions
                print(f"      • {func}")
            if len(file_info['functions']) > 5:
                print(f"      • ... et {len(file_info['functions']) - 5} autres")

def check_architecture_health():
    """Overall architecture health check."""
    print("\n🏥 BILAN DE SANTÉ DE L'ARCHITECTURE")
    print("=" * 60)
    
    checks = []
    
    # Run all checks
    structure_ok = check_file_structure()
    checks.append(("Structure des fichiers", structure_ok))
    
    circular_deps_ok = check_circular_dependencies()
    checks.append(("Dépendances circulaires", circular_deps_ok))
    
    imports_ok = test_imports()
    checks.append(("Tests d'imports", imports_ok))
    
    # Summary
    print(f"\n📋 RÉSUMÉ:")
    print("-" * 30)
    
    passed = 0
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Score global: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 Architecture parfaitement organisée!")
        return True
    else:
        print("⚠️  Des améliorations sont nécessaires.")
        return False

def main():
    """Main verification function."""
    print("🔍 VÉRIFICATION COMPLÈTE DE L'ARCHITECTURE PRYSM BACKEND")
    print("=" * 70)
    
    try:
        # Run architecture health check
        success = check_architecture_health()
        
        # Run function distribution analysis
        analyze_function_distribution()
        
        print(f"\n{'='*70}")
        if success:
            print("✅ VÉRIFICATION TERMINÉE - Architecture validée!")
        else:
            print("❌ VÉRIFICATION TERMINÉE - Corrections nécessaires")
        
        return success
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 