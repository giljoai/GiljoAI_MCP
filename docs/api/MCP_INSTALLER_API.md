# MCP Installer API Reference

**Last Updated:** 2025-10-09  
**Version:** 3.0  
**Audience:** Developers integrating programmatically

---

## Overview

The MCP Installer API provides RESTful endpoints for generating and distributing MCP integration installer scripts. This API enables programmatic deployment workflows, automated onboarding, and integration with existing DevOps pipelines.

### Base URL

```
http://localhost:7272/api/mcp-installer  # Localhost mode
http://10.1.0.164:7272/api/mcp-installer # LAN mode
https://your-domain.com/api/mcp-installer # WAN mode
```

### Authentication

All authenticated endpoints require either:
- **JWT Token:** Obtained via login endpoint
- **API Key:** Generated in dashboard (LAN/WAN modes)

**Authentication Headers:**

```http
# JWT Token
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# API Key
X-API-Key: gk_username_1234567890abcdef
```

### Rate Limiting

| Mode | Rate Limit | Burst |
|------|------------|-------|
| Localhost | Unlimited | N/A |
| LAN | 60 req/min | 10 |
| WAN | 30 req/min | 5 |

Rate limit headers included in responses:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 57
X-RateLimit-Reset: 1696860000
```

---

## Endpoints

### GET /api/mcp-installer/windows

Generate Windows batch installer script with embedded credentials.

#### Authentication
**Required:** Yes (JWT or API key)

#### Request

```http
GET /api/mcp-installer/windows HTTP/1.1
Host: localhost:7272
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Response

**Success (200 OK):**

```http
HTTP/1.1 200 OK
Content-Type: application/bat
Content-Disposition: attachment; filename=giljo-mcp-setup.bat
Content-Length: 12847

@echo off
REM ============================================================
REM GiljoAI MCP Tool Integration Installer
REM Generated for: Personal
REM User: john.doe
REM Server: http://localhost:7272
REM Generated: 2025-10-09T14:30:22Z
REM ============================================================

setlocal enabledelayedexpansion

REM Configuration Variables
set GILJO_SERVER=http://localhost:7272
set GILJO_API_KEY=gk_john_doe_abc123
...
```

**Error Responses:**

```http
# Unauthorized
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "detail": "Authentication required for MCP installer download"
}
```

```http
# Template not found
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "detail": "Installer template not found. Please contact administrator."
}
```

#### Example Usage

**cURL:**
```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:7272/api/mcp-installer/windows \
  -o giljo-mcp-setup.bat
```

**Python:**
```python
import requests

response = requests.get(
    "http://localhost:7272/api/mcp-installer/windows",
    headers={"Authorization": f"Bearer {jwt_token}"}
)

if response.status_code == 200:
    with open("giljo-mcp-setup.bat", "wb") as f:
        f.write(response.content)
    print("Installer downloaded successfully")
else:
    print(f"Error: {response.json()['detail']}")
```

**JavaScript/Node.js:**
```javascript
const axios = require('axios');
const fs = require('fs');

async function downloadInstaller() {
  try {
    const response = await axios.get(
      'http://localhost:7272/api/mcp-installer/windows',
      {
        headers: { 'Authorization': `Bearer ${jwtToken}` },
        responseType: 'arraybuffer'
      }
    );
    
    fs.writeFileSync('giljo-mcp-setup.bat', response.data);
    console.log('Installer downloaded');
  } catch (error) {
    console.error('Download failed:', error.response.data);
  }
}
```

---

### GET /api/mcp-installer/unix

Generate macOS/Linux shell installer script with embedded credentials.

#### Authentication
**Required:** Yes (JWT or API key)

#### Request

```http
GET /api/mcp-installer/unix HTTP/1.1
Host: localhost:7272
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Response

**Success (200 OK):**

```http
HTTP/1.1 200 OK
Content-Type: application/x-sh
Content-Disposition: attachment; filename=giljo-mcp-setup.sh
Content-Length: 15203

#!/bin/bash
# ============================================================
# GiljoAI MCP Tool Integration Installer
# Generated for: Personal
# User: john.doe
# Server: http://localhost:7272
# Generated: 2025-10-09T14:30:22Z
# ============================================================

set -e  # Exit on error

# Configuration Variables
GILJO_SERVER="http://localhost:7272"
GILJO_API_KEY="gk_john_doe_abc123"
...
```

**Error Responses:**

Same as Windows endpoint (401, 500).

#### Example Usage

**cURL:**
```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:7272/api/mcp-installer/unix \
  -o giljo-mcp-setup.sh

chmod +x giljo-mcp-setup.sh
```

**Python:**
```python
import requests
import os

response = requests.get(
    "http://localhost:7272/api/mcp-installer/unix",
    headers={"Authorization": f"Bearer {jwt_token}"}
)

if response.status_code == 200:
    with open("giljo-mcp-setup.sh", "wb") as f:
        f.write(response.content)
    
    # Make executable
    os.chmod("giljo-mcp-setup.sh", 0o755)
    print("Installer downloaded and made executable")
```

---

### POST /api/mcp-installer/share-link

Generate secure share links for email distribution.

#### Authentication
**Required:** Yes (JWT or API key)

#### Request

```http
POST /api/mcp-installer/share-link HTTP/1.1
Host: localhost:7272
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Body:** None required

#### Response

**Success (200 OK):**

```json
{
  "windows_url": "http://localhost:7272/download/mcp/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwaXJlc19hdCI6IjIwMjUtMTAtMTZUMTQ6MzA6MjJaIiwidHlwZSI6Im1jcF9pbnN0YWxsZXJfZG93bmxvYWQifQ.abc123def456/windows",
  "unix_url": "http://localhost:7272/download/mcp/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwaXJlc19hdCI6IjIwMjUtMTAtMTZUMTQ6MzA6MjJaIiwidHlwZSI6Im1jcF9pbnN0YWxsZXJfZG93bmxvYWQifQ.abc123def456/unix",
  "expires_at": "2025-10-16T14:30:22Z",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwaXJlc19hdCI6IjIwMjUtMTAtMTZUMTQ6MzA6MjJaIiwidHlwZSI6Im1jcF9pbnN0YWxsZXJfZG93bmxvYWQifQ.abc123def456"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `windows_url` | string | Public download URL for Windows installer |
| `unix_url` | string | Public download URL for Unix installer |
| `expires_at` | string | ISO 8601 timestamp of token expiration |
| `token` | string | JWT token (for programmatic use) |

**Error Responses:**

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "detail": "Authentication required to generate share links"
}
```

#### Example Usage

**cURL:**
```bash
curl -X POST http://localhost:7272/api/mcp-installer/share-link \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" | jq .
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:7272/api/mcp-installer/share-link",
    headers={
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Windows: {data['windows_url']}")
    print(f"Unix: {data['unix_url']}")
    print(f"Expires: {data['expires_at']}")
else:
    print(f"Error: {response.json()['detail']}")
```

**JavaScript/Node.js:**
```javascript
const axios = require('axios');

async function generateShareLink() {
  try {
    const response = await axios.post(
      'http://localhost:7272/api/mcp-installer/share-link',
      {},
      {
        headers: {
          'Authorization': `Bearer ${jwtToken}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('Windows URL:', response.data.windows_url);
    console.log('Unix URL:', response.data.unix_url);
    console.log('Expires:', response.data.expires_at);
    
    return response.data;
  } catch (error) {
    console.error('Failed:', error.response.data);
  }
}
```

---

### GET /download/mcp/{token}/{platform}

Public download endpoint using secure token (no authentication required).

#### Authentication
**Required:** No (uses token from URL)

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `token` | string | JWT token from share link generation |
| `platform` | string | Platform type: `windows` or `unix` |

#### Request

```http
GET /download/mcp/eyJ...abc123/windows HTTP/1.1
Host: localhost:7272
```

#### Response

**Success (200 OK):**

Returns installer script (same as authenticated endpoints).

**Error Responses:**

```http
# Invalid or expired token
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "detail": "Invalid or expired token"
}
```

```http
# User not found
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "detail": "User not found"
}
```

```http
# Invalid platform
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "Invalid platform. Must be 'windows' or 'unix'"
}
```

#### Example Usage

**Direct Browser Access:**
```
http://localhost:7272/download/mcp/eyJ...abc123/windows
```

**cURL:**
```bash
# Download Windows installer
curl http://localhost:7272/download/mcp/$TOKEN/windows \
  -o giljo-mcp-setup.bat

# Download Unix installer
curl http://localhost:7272/download/mcp/$TOKEN/unix \
  -o giljo-mcp-setup.sh
```

**Python:**
```python
import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
platform = "unix"

url = f"http://localhost:7272/download/mcp/{token}/{platform}"
response = requests.get(url)

if response.status_code == 200:
    filename = f"giljo-mcp-setup.{'bat' if platform == 'windows' else 'sh'}"
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"Downloaded: {filename}")
else:
    print(f"Error: {response.json()['detail']}")
```

---

## Data Models

### ShareLinkResponse

Response model for share link generation.

```typescript
interface ShareLinkResponse {
  windows_url: string;   // Public download URL for Windows
  unix_url: string;      // Public download URL for Unix
  expires_at: string;    // ISO 8601 timestamp
  token: string;         // JWT token
}
```

**Example:**
```json
{
  "windows_url": "http://localhost:7272/download/mcp/{token}/windows",
  "unix_url": "http://localhost:7272/download/mcp/{token}/unix",
  "expires_at": "2025-10-16T14:30:22Z",
  "token": "eyJ..."
}
```

### Token Payload

JWT token structure used in share links.

```typescript
interface TokenPayload {
  user_id: string;         // User identifier
  expires_at: string;      // ISO 8601 timestamp with 'Z' suffix
  type: string;            // Always "mcp_installer_download"
}
```

**Example:**
```json
{
  "user_id": "123",
  "expires_at": "2025-10-16T14:30:22Z",
  "type": "mcp_installer_download"
}
```

---

## Error Handling

### Error Response Format

All API errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Status | Meaning | Common Causes |
|--------|---------|---------------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Invalid platform parameter |
| 401 | Unauthorized | Missing/invalid authentication, expired token |
| 404 | Not Found | Endpoint doesn't exist |
| 500 | Internal Server Error | Template missing, database error |
| 503 | Service Unavailable | Server maintenance |

### Error Code Examples

**Authentication Error:**
```json
{
  "detail": "Authentication required for MCP installer download"
}
```

**Token Expired:**
```json
{
  "detail": "Invalid or expired token"
}
```

**User Not Found:**
```json
{
  "detail": "User not found"
}
```

**Invalid Platform:**
```json
{
  "detail": "Invalid platform. Must be 'windows' or 'unix'"
}
```

**Template Missing:**
```json
{
  "detail": "Installer template not found. Please contact administrator."
}
```

---

## Integration Examples

### Automated Onboarding System

Complete example of automated team onboarding:

```python
#!/usr/bin/env python3
"""
Automated MCP installer deployment system.
Integrates with HR system to onboard new developers.
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List

class MCPOnboardingSystem:
    def __init__(self, api_base: str, admin_jwt: str, smtp_config: Dict):
        self.api_base = api_base
        self.admin_jwt = admin_jwt
        self.smtp_config = smtp_config
    
    def generate_share_link(self) -> Dict[str, str]:
        """Generate share link for installer download."""
        url = f"{self.api_base}/api/mcp-installer/share-link"
        headers = {
            "Authorization": f"Bearer {self.admin_jwt}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def send_onboarding_email(self, recipient: Dict, links: Dict):
        """Send welcome email with installer links."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Welcome to Engineering - MCP Setup Required'
        msg['From'] = self.smtp_config['from_email']
        msg['To'] = recipient['email']
        
        # Plain text version
        text = f"""
        Hi {recipient['name']},
        
        Welcome to the engineering team! To set up your development environment:
        
        1. Download the installer for your operating system:
           Windows: {links['windows_url']}
           macOS/Linux: {links['unix_url']}
        
        2. Run the installer script
        3. Restart your development tools
        
        These links expire on {links['expires_at'][:10]}.
        
        Need help? Check the user guide: {self.api_base}/docs/mcp-integration
        
        Best regards,
        IT Team
        """
        
        # HTML version
        html = f"""
        <html>
          <body>
            <h2>Welcome to Engineering, {recipient['name']}!</h2>
            <p>To set up your development environment with GiljoAI MCP:</p>
            <ol>
              <li>Download the installer for your OS:
                <ul>
                  <li><a href="{links['windows_url']}">Windows Installer</a></li>
                  <li><a href="{links['unix_url']}">macOS/Linux Installer</a></li>
                </ul>
              </li>
              <li>Run the installer script</li>
              <li>Restart your development tools</li>
            </ol>
            <p><strong>Note:</strong> Links expire {links['expires_at'][:10]}</p>
            <p>Need help? <a href="{self.api_base}/docs/mcp-integration">User Guide</a></p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        with smtplib.SMTP(self.smtp_config['server'], 
                         self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['username'], 
                        self.smtp_config['password'])
            server.send_message(msg)
    
    def onboard_developer(self, developer: Dict):
        """Complete onboarding workflow for a developer."""
        print(f"Onboarding: {developer['name']} ({developer['email']})")
        
        try:
            # Generate share link
            links = self.generate_share_link()
            print(f"  ✓ Share link generated (expires: {links['expires_at']})")
            
            # Send email
            self.send_onboarding_email(developer, links)
            print(f"  ✓ Welcome email sent")
            
            # Log to audit system
            self.log_onboarding(developer, links)
            print(f"  ✓ Onboarding logged")
            
            return True
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
    
    def log_onboarding(self, developer: Dict, links: Dict):
        """Log onboarding event for audit trail."""
        # Implement logging to your audit system
        pass
    
    def bulk_onboard(self, developers: List[Dict]):
        """Onboard multiple developers."""
        print(f"Starting bulk onboarding for {len(developers)} developers\n")
        
        successful = 0
        failed = 0
        
        for dev in developers:
            if self.onboard_developer(dev):
                successful += 1
            else:
                failed += 1
            print()  # Blank line between developers
        
        print(f"Onboarding complete: {successful} successful, {failed} failed")

# Usage
if __name__ == "__main__":
    onboarding = MCPOnboardingSystem(
        api_base="http://localhost:7272",
        admin_jwt="your_admin_jwt_here",
        smtp_config={
            "server": "smtp.gmail.com",
            "port": 587,
            "from_email": "it@example.com",
            "username": "it@example.com",
            "password": "your_smtp_password"
        }
    )
    
    # Onboard new developers
    new_hires = [
        {
            "name": "Alice Smith",
            "email": "alice.smith@example.com",
            "department": "Engineering"
        },
        {
            "name": "Bob Johnson",
            "email": "bob.johnson@example.com",
            "department": "Engineering"
        }
    ]
    
    onboarding.bulk_onboard(new_hires)
```

### CI/CD Integration

Integrate with CI/CD pipelines for automated setup:

```yaml
# .gitlab-ci.yml
stages:
  - provision
  - deploy

provision_mcp_integration:
  stage: provision
  image: python:3.11
  script:
    - pip install requests
    - |
      python3 << EOF
      import requests
      import os
      
      # Get share link from API
      response = requests.post(
          os.getenv('GILJO_API_BASE') + '/api/mcp-installer/share-link',
          headers={'Authorization': f"Bearer {os.getenv('ADMIN_JWT')}"}
      )
      
      links = response.json()
      
      # Store as CI/CD variables for later stages
      with open('mcp_links.env', 'w') as f:
          f.write(f"WINDOWS_INSTALLER_URL={links['windows_url']}\n")
          f.write(f"UNIX_INSTALLER_URL={links['unix_url']}\n")
      EOF
  artifacts:
    reports:
      dotenv: mcp_links.env
  only:
    - schedules  # Run on scheduled pipeline for weekly updates

deploy_to_fileserver:
  stage: deploy
  dependencies:
    - provision_mcp_integration
  script:
    - curl $WINDOWS_INSTALLER_URL -o installers/giljo-mcp-setup.bat
    - curl $UNIX_INSTALLER_URL -o installers/giljo-mcp-setup.sh
    - scp installers/* fileserver:/shared/giljo-mcp/
  only:
    - schedules
```

### Slack Bot Integration

Provide self-service installer distribution via Slack:

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

app = App(token="xoxb-your-bot-token")

@app.command("/giljo-mcp-setup")
def handle_setup_command(ack, respond, command):
    """Handle /giljo-mcp-setup slash command."""
    ack()
    
    # Generate share link
    response = requests.post(
        "http://localhost:7272/api/mcp-installer/share-link",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    
    if response.status_code == 200:
        links = response.json()
        
        respond({
            "text": "GiljoAI MCP Installer Links",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*GiljoAI MCP Setup*\n\nChoose your operating system:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Windows"},
                            "url": links['windows_url'],
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "macOS/Linux"},
                            "url": links['unix_url']
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Links expire: {links['expires_at'][:10]}"
                        }
                    ]
                }
            ]
        })
    else:
        respond("Failed to generate installer links. Please contact IT.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, "xapp-your-app-token")
    handler.start()
```

---

## Security Considerations

### Token Security

**Token Lifetime:**
- Default: 7 days
- Configurable via environment variable: `INSTALLER_TOKEN_EXPIRY_DAYS`
- Tokens are single-use for share links (regenerate after expiry)

**Token Storage:**
- Never commit tokens to version control
- Store in secure secrets management (Vault, AWS Secrets Manager)
- Rotate regularly (weekly/monthly)

**Token Validation:**
- Signature verification using HMAC-SHA256
- Expiration checked on every request
- User existence validated before generating installer

### API Key Security

**Best Practices:**
- Use environment variables for API keys
- Implement key rotation policies
- Monitor for unusual usage patterns
- Revoke compromised keys immediately

**Example Secure Configuration:**
```python
import os
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        # Load encryption key from environment
        self.cipher = Fernet(os.getenv('CONFIG_ENCRYPTION_KEY'))
    
    def get_api_key(self) -> str:
        """Retrieve and decrypt API key."""
        encrypted = os.getenv('GILJO_API_KEY_ENCRYPTED')
        return self.cipher.decrypt(encrypted.encode()).decode()
```

### Rate Limiting

Implement client-side rate limiting:

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def allow_request(self) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        
        # Remove expired requests
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # Check limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """Calculate time to wait before next request."""
        if not self.requests:
            return 0
        
        oldest = self.requests[0]
        return max(0, self.time_window - (time.time() - oldest))

# Usage
limiter = RateLimiter(max_requests=60, time_window=60)  # 60 req/min

if limiter.allow_request():
    # Make API call
    pass
else:
    wait = limiter.wait_time()
    print(f"Rate limited. Wait {wait:.1f}s")
    time.sleep(wait)
```

---

## Testing

### Unit Tests

```python
import unittest
from unittest.mock import patch, MagicMock
import requests

class TestMCPInstallerAPI(unittest.TestCase):
    def setUp(self):
        self.api_base = "http://localhost:7272"
        self.jwt_token = "test_jwt_token"
        self.headers = {"Authorization": f"Bearer {self.jwt_token}"}
    
    def test_download_windows_installer(self):
        """Test Windows installer download."""
        response = requests.get(
            f"{self.api_base}/api/mcp-installer/windows",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/bat')
        self.assertIn('giljo-mcp-setup.bat', 
                     response.headers['Content-Disposition'])
        self.assertIn(b'@echo off', response.content)
    
    def test_download_unix_installer(self):
        """Test Unix installer download."""
        response = requests.get(
            f"{self.api_base}/api/mcp-installer/unix",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/x-sh')
        self.assertIn(b'#!/bin/bash', response.content)
    
    def test_generate_share_link(self):
        """Test share link generation."""
        response = requests.post(
            f"{self.api_base}/api/mcp-installer/share-link",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('windows_url', data)
        self.assertIn('unix_url', data)
        self.assertIn('token', data)
        self.assertIn('expires_at', data)
    
    def test_unauthorized_access(self):
        """Test authentication requirement."""
        response = requests.get(
            f"{self.api_base}/api/mcp-installer/windows"
            # No Authorization header
        )
        
        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', response.json())

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```python
import pytest
import requests
from datetime import datetime, timedelta

@pytest.fixture
def api_client():
    """Fixture for API client with authentication."""
    return {
        'base_url': 'http://localhost:7272',
        'headers': {'Authorization': 'Bearer test_jwt'}
    }

def test_full_onboarding_workflow(api_client):
    """Test complete onboarding workflow."""
    # Step 1: Generate share link
    response = requests.post(
        f"{api_client['base_url']}/api/mcp-installer/share-link",
        headers=api_client['headers']
    )
    assert response.status_code == 200
    links = response.json()
    token = links['token']
    
    # Step 2: Download via share link (no auth)
    response = requests.get(links['windows_url'])
    assert response.status_code == 200
    assert b'@echo off' in response.content
    
    # Step 3: Verify token expiration
    expires_at = datetime.fromisoformat(links['expires_at'].replace('Z', '+00:00'))
    expected_expiry = datetime.utcnow() + timedelta(days=7)
    assert abs((expires_at - expected_expiry).total_seconds()) < 60  # Within 1 minute

def test_expired_token_rejection(api_client):
    """Test that expired tokens are rejected."""
    # Use a manually created expired token
    expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Expired
    
    response = requests.get(
        f"{api_client['base_url']}/download/mcp/{expired_token}/windows"
    )
    assert response.status_code == 401
    assert 'expired' in response.json()['detail'].lower()
```

---

## Troubleshooting

### Common API Issues

**Issue: 401 Unauthorized**

```python
# Check JWT token is valid
import jwt

try:
    payload = jwt.decode(token, options={"verify_signature": False})
    print(f"Token user_id: {payload.get('user_id')}")
    print(f"Token expires: {payload.get('exp')}")
except jwt.DecodeError:
    print("Invalid token format")
```

**Issue: Rate Limit Exceeded**

```python
# Implement exponential backoff
import time

def download_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:  # Too Many Requests
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

**Issue: Template Not Found (500 Error)**

Check server-side template paths:
```bash
# Verify templates exist
ls -la installer/templates/
# Should show:
# giljo-mcp-setup.bat.template
# giljo-mcp-setup.sh.template
```

---

## Changelog

### Version 3.0.0 (2025-10-09)
- Initial release of MCP Installer API
- Windows and Unix installer generation
- Share link functionality with 7-day expiry
- Public download endpoints via token
- JWT-based authentication
- Rate limiting support

### Version 3.1.0 (Planned)
- Custom template support
- Configurable token expiry
- Bulk download endpoint
- Webhook notifications
- Usage analytics endpoints

---

## Support

### Resources

- **User Guide:** [MCP Integration Guide](../guides/MCP_INTEGRATION_GUIDE.md)
- **Admin Guide:** [Admin MCP Setup](../guides/ADMIN_MCP_SETUP.md)
- **Technical Docs:** [Technical Architecture](../TECHNICAL_ARCHITECTURE.md)

### Contact

- **GitHub Issues:** Report bugs and feature requests
- **Documentation:** `docs/README_FIRST.md`
- **API Status:** `http://localhost:7272/health`

---

**Last Updated:** 2025-10-09  
**API Version:** 3.0  
**Maintainer:** Documentation Manager Agent
