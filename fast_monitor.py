import json
import subprocess
import time
from datetime import datetime


def check_messages():
    """Check for new messages from agents"""
    try:
        result = subprocess.run(
            [
                "python",
                "-c",
                """
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
""",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            data = json.loads(result.stdout)
            if data.get("status") == "new_messages":
                datetime.now().strftime("%H:%M:%S")
                for _msg in data.get("messages", []):
                    pass
                return True
    except Exception:
        pass
    return False


while True:
    check_messages()
    time.sleep(10)  # Check every 10 seconds
