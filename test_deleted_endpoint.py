#!/usr/bin/env python3
"""Quick test script for /deleted endpoint"""

import json

import requests


# Login first
login_response = requests.post(
    "http://10.1.0.164:7272/api/v1/auth/login", json={"username": "patrik", "password": "GiljoMCP"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print("✓ Logged in successfully")

# Test deleted endpoint
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://10.1.0.164:7272/api/v1/projects/deleted", headers=headers)

print(f"\nStatus Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print("\nResponse Body:")
try:
    print(json.dumps(response.json(), indent=2))
except:
    print(response.text)
