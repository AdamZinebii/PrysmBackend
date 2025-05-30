#!/usr/bin/env python3
"""
Script to update Firebase Cloud Functions to allow public access.
"""

import subprocess
import json
import time
import os

# Set the project ID
PROJECT_ID = "prysmios"

# Functions to update
FUNCTIONS = [
    "generate_news_summary",
    "get_news_summary", 
    "set_user_preferences"
]

def run_command(cmd):
    """Run a shell command and return the output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def set_function_public(region, function_name):
    """Make a cloud function public by setting allUsers as invoker."""
    # For 2nd gen cloud functions
    cmd = [
        "curl", "-X", "POST",
        f"https://cloudfunctions.googleapis.com/v2/projects/{PROJECT_ID}/locations/{region}/functions/{function_name}:setIamPolicy",
        "-H", "Authorization: Bearer $(gcloud auth print-access-token)",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "policy": {
                "bindings": [
                    {
                        "role": "roles/cloudfunctions.invoker",
                        "members": ["allUsers"]
                    }
                ]
            }
        })
    ]
    
    print(f"To make the function {function_name} public, run this command in your Google Cloud Shell:")
    print(" ".join(cmd))
    print("\n")

# Print instructions
print("=====================================================")
print("Firebase Cloud Functions Public Access Instructions")
print("=====================================================")
print("\nInstructions to make your Cloud Functions publicly accessible:")
print("\n1. Go to https://console.cloud.google.com/")
print("2. Select your project: prysmios")
print("3. Open the Cloud Shell (terminal icon in the top right)")
print("4. Copy and run each of the following commands in the Cloud Shell:\n")

# Generate command for each function
for function in FUNCTIONS:
    set_function_public("us-central1", function)

print("\n5. Wait a few minutes for the changes to propagate")
print("6. Test your function with: curl https://us-central1-prysmios.cloudfunctions.net/generate_news_summary?user_id=test123")
print("\nNote: These changes open your Cloud Functions to public access. In a production environment, consider adding proper authentication.") 