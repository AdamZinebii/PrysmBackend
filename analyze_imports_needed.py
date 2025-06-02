#!/usr/bin/env python3
"""
Analyze function calls and dependencies across all Python files
to determine what imports are needed.
"""

import os
import re
import ast
from collections import defaultdict

def extract_function_calls_from_file(file_path):
    """Extract function calls from a Python file using AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        calls = set()
        
        class FunctionCallVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    # Handle chained calls like module.function()
                    attr_name = node.func.attr
                    calls.add(attr_name)
                self.generic_visit(node)
        
        visitor = FunctionCallVisitor()
        visitor.visit(tree)
        return calls
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set()

def extract_function_definitions_from_file(file_path):
    """Extract function definitions from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        functions = set()
        
        class FunctionDefVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                functions.add(node.name)
                self.generic_visit(node)
        
        visitor = FunctionDefVisitor()
        visitor.visit(tree)
        return functions
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set()

def get_all_python_files():
    """Get all Python files in the project."""
    python_files = []
    
    # Add main.py
    if os.path.exists('main.py'):
        python_files.append('main.py')
    
    # Add all module files
    if os.path.exists('modules'):
        for root, dirs, files in os.walk('modules'):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    python_files.append(os.path.join(root, file))
    
    return python_files

def analyze_dependencies():
    """Analyze function dependencies across all files."""
    
    print("🔍 ANALYSE COMPLÈTE DES IMPORTS NÉCESSAIRES")
    print("=" * 70)
    
    python_files = get_all_python_files()
    
    # Extract function definitions from each file
    file_functions = {}
    all_functions = {}  # function_name -> file_path
    
    for file_path in python_files:
        functions = extract_function_definitions_from_file(file_path)
        file_functions[file_path] = functions
        
        for func in functions:
            if func in all_functions:
                print(f"⚠️  Duplicate function '{func}' found in {file_path} and {all_functions[func]}")
            all_functions[func] = file_path
    
    print(f"\n📄 Fichiers analysés: {len(python_files)}")
    print(f"🔧 Fonctions trouvées: {len(all_functions)}")
    
    # Extract function calls from each file
    file_calls = {}
    for file_path in python_files:
        calls = extract_function_calls_from_file(file_path)
        file_calls[file_path] = calls
    
    print(f"\n🎯 IMPORTS NÉCESSAIRES POUR CHAQUE FICHIER:")
    print("=" * 60)
    
    # Analyze dependencies for each file and output import statements
    for file_path in sorted(python_files):
        print(f"\n📁 {file_path}")
        print("-" * 50)
        
        calls_in_file = file_calls.get(file_path, set())
        functions_in_file = file_functions.get(file_path, set())
        
        # Find external function calls (functions not defined in this file)
        external_calls = calls_in_file - functions_in_file
        
        # Group external calls by the file they're defined in
        needed_imports = defaultdict(list)
        
        for call in external_calls:
            if call in all_functions:
                source_file = all_functions[call]
                if source_file != file_path:  # Don't import from self
                    needed_imports[source_file].append(call)
        
        if needed_imports:
            print("# Imports nécessaires:")
            for source_file, functions in sorted(needed_imports.items()):
                # Convert file path to module path
                if source_file.startswith('modules/'):
                    module_path = source_file[8:-3].replace('/', '.')  # Remove 'modules/' and '.py'
                    print(f"from modules.{module_path} import {', '.join(sorted(functions))}")
                elif source_file == 'main.py' and file_path.startswith('modules/'):
                    print(f"# From main.py: {', '.join(sorted(functions))}")
                else:
                    print(f"# From {source_file}: {', '.join(sorted(functions))}")
        else:
            print("# Aucun import externe nécessaire")
        
        print()  # Add blank line for readability
    
    print(f"\n🎯 RÉSUMÉ DES MODULES:")
    print("-" * 30)
    
    module_files = [f for f in python_files if f.startswith('modules/')]
    for module_file in sorted(module_files):
        functions = file_functions.get(module_file, set())
        module_name = module_file[8:-3].replace('/', '.')  # Convert to module path
        print(f"📦 modules.{module_name}: {len(functions)} fonctions")
        for func in sorted(functions):
            print(f"   • {func}")
    
    print(f"\n📄 MAIN.PY:")
    print("-" * 15)
    main_functions = file_functions.get('main.py', set())
    print(f"🎯 {len(main_functions)} fonctions (endpoints)")
    for func in sorted(main_functions):
        print(f"   • {func}")
    
    print(f"\n🔗 IMPORTS SPÉCIAUX:")
    print("-" * 20)
    print("Note: Vous devrez aussi ajouter les imports standards comme:")
    print("import json, logging, datetime, requests, etc.")
    print("selon les besoins de chaque fichier.")

if __name__ == "__main__":
    analyze_dependencies() 