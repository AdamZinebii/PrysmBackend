#!/usr/bin/env python3
"""
Script d'analyse pour identifier les fonctions de main.py 
qui ne sont pas encore dans les modules
"""

import os
import re
from pathlib import Path

def extract_functions_from_file(file_path):
    """Extrait toutes les fonctions d'un fichier Python"""
    functions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex pour trouver les définitions de fonctions
        pattern = r'^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.finditer(pattern, content, re.MULTILINE)
        
        for match in matches:
            func_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            functions.append({
                'name': func_name,
                'line': line_num,
                'file': str(file_path)
            })
    except Exception as e:
        print(f"❌ Erreur lecture {file_path}: {e}")
    
    return functions

def scan_modules_directory(modules_dir):
    """Scanne tous les modules et extrait leurs fonctions"""
    module_functions = {}
    
    for root, dirs, files in os.walk(modules_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = Path(root) / file
                relative_path = file_path.relative_to(modules_dir)
                
                functions = extract_functions_from_file(file_path)
                if functions:
                    module_name = str(relative_path).replace('.py', '').replace('/', '.')
                    module_functions[module_name] = functions
    
    return module_functions

def analyze_main_vs_modules():
    """Analyse main.py vs modules"""
    print("🔍 ANALYSE DES FONCTIONS - Main.py vs Modules")
    print("=" * 60)
    
    # Extraire fonctions de main.py
    main_functions = extract_functions_from_file('main.py')
    print(f"📄 Main.py: {len(main_functions)} fonctions trouvées")
    
    # Extraire fonctions des modules
    modules_functions = scan_modules_directory('modules')
    total_module_functions = sum(len(funcs) for funcs in modules_functions.values())
    print(f"📁 Modules: {total_module_functions} fonctions trouvées")
    
    # Créer un set des noms de fonctions dans les modules
    module_function_names = set()
    for module_name, functions in modules_functions.items():
        for func in functions:
            module_function_names.add(func['name'])
    
    # Identifier les fonctions manquantes
    missing_functions = []
    for func in main_functions:
        if func['name'] not in module_function_names:
            missing_functions.append(func)
    
    # Afficher les résultats
    print(f"\n🚨 FONCTIONS MANQUANTES: {len(missing_functions)}")
    print("-" * 40)
    
    if missing_functions:
        # Grouper par type/catégorie approximative
        categorized = {
            'Endpoints (HTTP)': [],
            'Database': [],
            'Content/Generation': [],
            'News/Search': [],
            'Scheduled/Tasks': [],
            'Utilities': [],
            'Other': []
        }
        
        for func in missing_functions:
            name = func['name']
            if 'endpoint' in name or '_fn.' in func['file']:
                categorized['Endpoints (HTTP)'].append(func)
            elif any(x in name for x in ['_db', 'save_', 'get_user', 'update_']):
                categorized['Database'].append(func)
            elif any(x in name for x in ['generate_', 'script', 'podcast', 'media', 'report']):
                categorized['Content/Generation'].append(func)
            elif any(x in name for x in ['news', 'articles', 'trending', 'serpapi']):
                categorized['News/Search'].append(func)
            elif any(x in name for x in ['scheduled', 'update', 'refresh', 'trigger']):
                categorized['Scheduled/Tasks'].append(func)
            elif any(x in name for x in ['format_', 'parse_', 'find_', 'convert_']):
                categorized['Utilities'].append(func)
            else:
                categorized['Other'].append(func)
        
        for category, funcs in categorized.items():
            if funcs:
                print(f"\n📂 {category} ({len(funcs)} fonctions):")
                for func in funcs:
                    print(f"   • {func['name']} (ligne {func['line']})")
    
    # Afficher les modules existants
    print(f"\n✅ MODULES EXISTANTS:")
    print("-" * 30)
    for module_name, functions in modules_functions.items():
        print(f"📁 {module_name}: {len(functions)} fonctions")
        for func in functions:
            print(f"   • {func['name']}")
    
    # Fonctions dupliquées dans main.py
    print(f"\n🔄 VÉRIFICATION DES DOUBLONS dans main.py:")
    print("-" * 40)
    func_counts = {}
    for func in main_functions:
        name = func['name']
        if name not in func_counts:
            func_counts[name] = []
        func_counts[name].append(func)
    
    duplicates = {name: funcs for name, funcs in func_counts.items() if len(funcs) > 1}
    if duplicates:
        for name, funcs in duplicates.items():
            print(f"🔄 {name}: {len(funcs)} versions")
            for func in funcs:
                print(f"   • Ligne {func['line']}")
    else:
        print("✅ Aucun doublon détecté")
    
    return {
        'main_functions': main_functions,
        'module_functions': modules_functions,
        'missing_functions': missing_functions,
        'duplicates': duplicates
    }

def generate_migration_plan(analysis_result):
    """Génère un plan de migration"""
    missing = analysis_result['missing_functions']
    
    print(f"\n📋 PLAN DE MIGRATION SUGGÉRÉ:")
    print("=" * 40)
    
    # Suggérer de nouveaux modules
    suggestions = {
        'modules/database/operations.py': [],
        'modules/content/generation.py': [],
        'modules/content/topics.py': [],
        'modules/content/podcast.py': [],
        'modules/scheduling/tasks.py': [],
        'modules/utils/helpers.py': [],
        'modules/news/formatters.py': []
    }
    
    for func in missing:
        name = func['name']
        if any(x in name for x in ['_db', 'save_', 'get_user', 'update_specific']):
            suggestions['modules/database/operations.py'].append(func)
        elif any(x in name for x in ['generate_', 'script', 'report', 'summary']):
            suggestions['modules/content/generation.py'].append(func)
        elif any(x in name for x in ['topic', 'subtopic', 'trending']):
            suggestions['modules/content/topics.py'].append(func)
        elif any(x in name for x in ['podcast', 'media_twin']):
            suggestions['modules/content/podcast.py'].append(func)
        elif any(x in name for x in ['scheduled', 'update', 'refresh', 'trigger']):
            suggestions['modules/scheduling/tasks.py'].append(func)
        elif any(x in name for x in ['format_', 'parse_']):
            suggestions['modules/news/formatters.py'].append(func)
        else:
            suggestions['modules/utils/helpers.py'].append(func)
    
    for module_path, funcs in suggestions.items():
        if funcs:
            print(f"\n📁 {module_path}:")
            for func in funcs:
                print(f"   • {func['name']} (ligne {func['line']})")

if __name__ == "__main__":
    try:
        analysis = analyze_main_vs_modules()
        generate_migration_plan(analysis)
        
        print(f"\n🎯 RÉSUMÉ:")
        print(f"   • Main.py: {len(analysis['main_functions'])} fonctions")
        print(f"   • Modules: {sum(len(f) for f in analysis['module_functions'].values())} fonctions")
        print(f"   • Manquantes: {len(analysis['missing_functions'])} fonctions")
        print(f"   • Doublons: {len(analysis['duplicates'])} fonctions")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc() 