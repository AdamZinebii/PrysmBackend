# ENHANCED podcast script cleanup
import re

def clean_podcast_script(script_content):
    """Clean podcast script by removing stage directions, URLs, and link references"""
    
    # Step 1: Remove bold stage directions **[intro]**, **[Main Content]**, etc.
    script_content = re.sub(r'\*\*\[.*?\]\*\*', ' ', script_content)
    
    # Step 2: Remove all brackets content [intro], [outro], etc.
    script_content = re.sub(r'\[.*?\]', ' ', script_content)
    
    # Step 3: Remove markdown links [here](url) and variations
    script_content = re.sub(r'\[[^\]]*\]\([^)]*\)', ' ', script_content)
    
    # Step 4: Remove standalone URLs
    script_content = re.sub(r'https?://[^\s)]+', ' ', script_content)
    
    # Step 5: Remove link reference phrases
    phrases_to_remove = [
        r'[Yy]ou can (read more|check|find|dive deeper)[^.!?]*[.!?]',
        r'[Cc]heck it out[^.!?]*[.!?]', 
        r'[Ii]f you\'re curious[^.!?]*[.!?]',
        r'[Ii]t\'s worth a peek[^.!?]*[.!?]',
        r'[Dd]on\'t hesitate to[^.!?]*[.!?]'
    ]
    for pattern in phrases_to_remove:
        script_content = re.sub(pattern, ' ', script_content)
    
    # Step 6: Clean whitespace
    script_content = re.sub(r'\s+', ' ', script_content)  # Multiple spaces
    script_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', script_content)  # Multiple line breaks
    script_content = script_content.strip()
    
    return script_content

# Test with user's problematic script
test_script = '''**[Intro]** Hey there, friends! Welcome back to your friendly neighborhood news update. You can check the full article [here](https://www.realestatenews.com/2025/03/13/the-housing-market-is-improving-but-buyers-are-anxious). **[Main Content]** Let's start with the ever-evolving real estate market. You can dive deeper into this topic [here](https://www.newsweek.com/recession-housing-market-mortgage-rates-price-trump-tariffs-2043195). **[Outro]** And there you have it, folks!'''

print("BEFORE CLEANUP:")
print(test_script)
print("\nAFTER CLEANUP:")
print(clean_podcast_script(test_script)) 