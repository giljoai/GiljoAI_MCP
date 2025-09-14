import json
import time
import subprocess
import sys
from datetime import datetime

def check_messages():
    """Check for new messages from agents"""
    try:
        result = subprocess.run([
            'python', '-c',
            '''
import requests
import json

url = "http://localhost:5000/api/messages/orchestrator"
try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        messages = response.json().get("messages", [])
        if messages:
            print(json.dumps({"status": "new_messages", "count": len(messages), "messages": messages[:3]}))
        else:
            print(json.dumps({"status": "no_messages"}))
    else:
        print(json.dumps({"status": "error", "code": response.status_code}))
except Exception as e:
    print(json.dumps({"status": "error", "error": str(e)}))
'''
        ], capture_output=True, text=True)
        
        if result.stdout:
            data = json.loads(result.stdout)
            if data.get("status") == "new_messages":
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{timestamp}] 🔔 NEW MESSAGES - {data['count']} pending")
                for msg in data.get("messages", []):
                    print(f"  📨 From: {msg.get('from_agent', 'unknown')}")
                return True
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    return False

print("=" * 50)
print("FAST MESSAGE MONITOR - 10 SECOND INTERVALS")
print("=" * 50)
print("[MONITOR] Starting fast message monitor for orchestrator...")
print("[MONITOR] Checking every 10 seconds for new messages...")
print("-" * 50)

while True:
    check_messages()
    time.sleep(10)  # Check every 10 seconds
