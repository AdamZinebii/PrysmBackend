#!/usr/bin/env python3
"""
Script to configure public access for Cloud Run functions (Firebase Functions v2)
"""

import subprocess
import json
import sys

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error: {result.stderr}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Exception running command: {command}")
        print(f"Exception: {e}")
        return None

def get_project_id():
    """Get the current Firebase project ID"""
    result = run_command("firebase use")
    if result:
        # firebase use returns just the project ID
        return result.strip()
    return None

def configure_public_access(function_name, project_id):
    """Configure public access for a Cloud Run function"""
    print(f"Configuring public access for {function_name}...")
    
    # The Cloud Run service name for Firebase Functions v2
    service_name = function_name
    region = "us-central1"
    
    # Command to add IAM policy binding for public access
    command = f"""gcloud run services add-iam-policy-binding {service_name} \
        --region={region} \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --project={project_id}"""
    
    result = run_command(command)
    if result:
        print(f"✅ Successfully configured public access for {function_name}")
        return True
    else:
        print(f"❌ Failed to configure public access for {function_name}")
        return False

def main():
    """Main function"""
    print("🔧 Configuring public access for Firebase Functions v2...")
    
    # Get project ID
    project_id = get_project_id()
    if not project_id:
        print("❌ Could not determine Firebase project ID")
        sys.exit(1)
    
    print(f"📋 Project ID: {project_id}")
    
    # Functions to configure
    functions = [
        "save-initial-preferences",
        "answer", 
        "update-specific-subjects"
    ]
    
    success_count = 0
    for function_name in functions:
        if configure_public_access(function_name, project_id):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{len(functions)} functions configured successfully")
    
    if success_count == len(functions):
        print("🎉 All functions are now publicly accessible!")
        print("\n🧪 Test the functions:")
        for function_name in functions:
            url = f"https://{function_name}-za2ovv4k4q-uc.a.run.app"
            print(f"  {function_name}: {url}")
    else:
        print("⚠️  Some functions may still require manual configuration")
        print("\n💡 Alternative: Install gcloud CLI and run:")
        print("   brew install google-cloud-sdk")
        print("   gcloud auth login")
        print("   python configure_public_access.py")

if __name__ == "__main__":
    main() 