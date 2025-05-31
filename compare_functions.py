#!/usr/bin/env python3
"""
Compare local Firebase Functions with deployed functions.
"""

# Deployed functions (from firebase functions:list)
DEPLOYED_FUNCTIONS = [
    'answer',
    'fetch_news_with_gnews',
    'generate_complete_user_media_twin_script_endpoint',
    'generate_media_twin_script_endpoint',
    'generate_simple_podcast_endpoint',
    'generate_user_media_twin_script_endpoint',
    'get_aifeed_reports_endpoint',
    'get_articles_subtopics_user_endpoint',
    'get_complete_report_endpoint',
    'get_complete_topic_report_endpoint',
    'get_pickup_line_endpoint',
    'get_reddit_world_summary_endpoint',
    'get_topic_posts_endpoint',
    'get_topic_summary_endpoint',
    'get_trending_for_subtopic',
    'get_trending_subtopics',
    'get_user_articles_endpoint',
    'get_user_preferences',
    'health_check',
    'refresh_articles_endpoint',
    'save_initial_preferences',
    'test_gnews_api',
    'text_to_speech',
    'update_specific_subjects'
]

# Local functions (from main.py)
LOCAL_FUNCTIONS = [
    'answer',
    'fetch_news_with_gnews',
    'generate_complete_user_media_twin_script_endpoint',
    'generate_media_twin_script_endpoint',
    'generate_simple_podcast_endpoint',
    'generate_user_media_twin_script_endpoint',
    'get_aifeed_reports_endpoint',
    'get_articles_subtopics_user_endpoint',
    'get_complete_report_endpoint',
    'get_complete_topic_report_endpoint',
    'get_pickup_line_endpoint',
    'get_reddit_world_summary_endpoint',
    'get_topic_posts_endpoint',
    'get_topic_summary_endpoint',
    'get_trending_for_subtopic',
    'get_trending_subtopics',
    'get_user_articles_endpoint',
    'get_user_preferences',
    'health_check',
    'refresh_articles_endpoint',
    'save_initial_preferences',
    'test_gnews_api',
    'text_to_speech',
    'update_endpoint',
    'update_specific_subjects'
]

def compare_functions():
    """Compare deployed vs local functions."""
    print("🔍 FIREBASE FUNCTIONS COMPARISON")
    print("=" * 50)
    
    deployed_set = set(DEPLOYED_FUNCTIONS)
    local_set = set(LOCAL_FUNCTIONS)
    
    # Functions in both
    both = deployed_set & local_set
    print(f"✅ MATCHING FUNCTIONS ({len(both)}):")
    for func in sorted(both):
        print(f"   ✓ {func}")
    
    # Only in deployed
    only_deployed = deployed_set - local_set
    if only_deployed:
        print(f"\n⚠️  ONLY IN DEPLOYED ({len(only_deployed)}):")
        for func in sorted(only_deployed):
            print(f"   🌐 {func}")
    
    # Only in local
    only_local = local_set - deployed_set
    if only_local:
        print(f"\n⚠️  ONLY IN LOCAL ({len(only_local)}):")
        for func in sorted(only_local):
            print(f"   🏠 {func}")
    
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY:")
    print(f"   • Deployed: {len(deployed_set)} functions")
    print(f"   • Local: {len(local_set)} functions") 
    print(f"   • Matching: {len(both)} functions")
    print(f"   • Only deployed: {len(only_deployed)} functions")
    print(f"   • Only local: {len(only_local)} functions")
    
    if len(both) == len(deployed_set) == len(local_set):
        print(f"\n🎉 PERFECT MATCH! Your local and deployed functions are identical.")
        return True
    else:
        print(f"\n⚠️  DIFFERENCES FOUND! Review the functions above.")
        return False

if __name__ == "__main__":
    compare_functions() 