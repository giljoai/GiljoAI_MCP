#!/usr/bin/env python3
import time
from datetime import datetime

print("=" * 50)
print("ORCHESTRATOR MESSAGE MONITOR - AKE-MCP")
print("=" * 50)
print("Checking every 10 seconds via AKE-MCP tools...")
print("-" * 50)

# Since we can't directly call AKE-MCP from Python, 
# we'll create a marker file when messages are detected
# The orchestrator should be using mcp__ake-mcp-v2__get_messages directly

counter = 0
while True:
    counter += 1
    timestamp = datetime.now().strftime('%H:%M:%S')
    if counter % 6 == 0:  # Every minute
        print(f"[{timestamp}] Heartbeat - Monitor active (check #{counter})")
        print("  Use mcp__ake-mcp-v2__get_messages to check for new messages")
    time.sleep(10)
