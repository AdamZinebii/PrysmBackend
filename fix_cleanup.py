#!/usr/bin/env python3

# Script to fix the cleanup section in main.py
import re

def main():
    # Read the current file
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Find and replace the cleanup section
    old_cleanup = r'''        # Clean up any remaining stage directions from the script
        import re
        # Remove stage directions like \[intro\], \[outro\], \[pause\], etc\.
        script_content = re\.sub\(r'\\\[.*?\\\]', '', script_content\)
        # Remove timestamp markers like \(00:30\), \(2:15\), etc\.
        script_content = re\.sub\(r'\\\(\\\d\+:\\\d\+\\\)', '', script_content\)
        # Remove excessive line breaks and clean up whitespace
        script_content = re\.sub\(r'\\\n\\\s\*\\\n\\\s\*\\\n', '\\\n\\\n', script_content\)
        script_content = script_content\.strip\(\)'''
    
    new_cleanup = '''        # ENHANCED cleanup for stage directions and URLs
        import re
        
        # Remove bold stage directions **[intro]**, **[Main Content]**, etc.
        script_content = re.sub(r'\\*\\*\\[.*?\\]\\*\\*', ' ', script_content)
        
        # Remove all brackets content [intro], [outro], etc.
        script_content = re.sub(r'\\[.*?\\]', ' ', script_content)
        
        # Remove markdown links [here](url) and variations
        script_content = re.sub(r'\\[[^\\]]*\\]\\([^)]*\\)', ' ', script_content)
        
        # Remove standalone URLs
        script_content = re.sub(r'https?://[^\\s)]+', ' ', script_content)
        
        # Remove link reference phrases
        phrases_to_remove = [
            r'[Yy]ou can (read more|check|find|dive deeper)[^.!?]*[.!?]',
            r'[Cc]heck it out[^.!?]*[.!?]',
            r'[Ii]f you\\'re curious[^.!?]*[.!?]',
            r'[Ii]t\\'s worth a peek[^.!?]*[.!?]'
        ]
        for pattern in phrases_to_remove:
            script_content = re.sub(pattern, ' ', script_content)
        
        # Clean whitespace
        script_content = re.sub(r'\\s+', ' ', script_content)
        script_content = re.sub(r'\\n\\s*\\n\\s*\\n+', '\\n\\n', script_content)
        script_content = script_content.strip()'''
    
    # Replace the old cleanup with new cleanup
    content = re.sub(old_cleanup, new_cleanup, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write back to file
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Cleanup section updated successfully!")

if __name__ == "__main__":
    main() 