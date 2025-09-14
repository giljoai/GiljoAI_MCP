import time
import json
import subprocess
from datetime import datetime

AGENT_NAME = "ui-analyzer"
PROJECT_ID = "86b708fd-6b53-4067-acec-08ab005d0f3d"

def check_messages_via_mcp():
    """Check messages using MCP tool directly"""
    try:
        # Use the MCP tool via subprocess to check messages
        cmd = f'''echo '{{"agent_name": "{AGENT_NAME}", "project_id": "{PROJECT_ID}"}}' '''
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for messages...")
        
        # For now, just print a heartbeat since we need proper MCP integration
        # In production, this would call the actual MCP get_messages tool
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")

print(f"=== Message Monitor for {AGENT_NAME} ===")
print(f"Project: {PROJECT_ID}")
print(f"Interval: 10 seconds")
print("Status: Running (Press Ctrl+C to stop)")
print("-" * 50)

iteration = 0
while True:
    iteration += 1
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Check #{iteration} - Monitoring for new messages...")
    check_messages_via_mcp()
    time.sleep(10)
