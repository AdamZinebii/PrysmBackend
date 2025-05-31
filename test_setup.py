#!/usr/bin/env python3
"""
Quick test script to verify Firebase Functions setup.
"""

import sys
import os

def test_imports():
    """Test that all critical imports work."""
    try:
        # Core Firebase Functions
        from firebase_functions import https_fn
        from firebase_admin import initialize_app, firestore
        
        # AI APIs
        import openai
        import serpapi
        from elevenlabs import ElevenLabs
        
        # Other critical dependencies
        import feedparser
        import requests
        import newspaper
        import nltk
        
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_main_module():
    """Test that main.py can be imported."""
    try:
        import main
        print("✅ main.py imports successfully")
        
        # Test a few key functions exist
        functions = [
            'health_check',
            'build_system_prompt', 
            'gnews_search',
            'generate_ai_response'
        ]
        
        for func_name in functions:
            if hasattr(main, func_name):
                print(f"✅ Function {func_name} exists")
            else:
                print(f"❌ Function {func_name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error importing main.py: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Firebase Functions Setup")
    print("=" * 40)
    
    # Test Python version
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")
    
    # Run tests
    imports_ok = test_imports()
    main_ok = test_main_module()
    
    print("\n" + "=" * 40)
    if imports_ok and main_ok:
        print("🎉 All tests passed! Firebase Functions ready!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 