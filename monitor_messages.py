import time
from datetime import datetime

import requests


AGENT_NAME = "ui-analyzer"
PROJECT_ID = "86b708fd-6b53-4067-acec-08ab005d0f3d"
API_URL = "http://localhost:8000"

def check_messages():
    """Check for new messages from AKE-MCP"""
    try:
        # Using the API endpoint to get messages
        response = requests.get(f"{API_URL}/api/agents/{AGENT_NAME}/messages")
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            if messages:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(messages)} new message(s)")
                for msg in messages:
                    print(f"  From: {msg.get('from', 'unknown')}")
                    print(f"  Content: {msg.get('content', '')[:100]}...")
                    print(f"  Priority: {msg.get('priority', 'normal')}")
                    print("  ---")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No new messages")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] API check failed: {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error checking messages: {e}")

print(f"Starting message monitor for {AGENT_NAME}")
print("Checking every 10 seconds...")
print("Press Ctrl+C to stop")
print("-" * 50)

while True:
    check_messages()
    time.sleep(10)
