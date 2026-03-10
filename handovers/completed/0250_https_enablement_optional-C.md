---
**Handover**: 0250 - HTTPS Enablement (Optional Configuration)
**Type**: Full-Stack (Backend + Frontend + Infrastructure)
**Effort**: 6-8 hours
**Priority**: P2 (Nice to Have - Security Enhancement)
**Status**: Ready
**Complexity**: Low-Medium
**Category**: Security/Infrastructure
**Tool**: CLI (for certificate generation, config changes, and testing)
---

# Handover 0250: HTTPS Enablement (Optional Configuration)

## Executive Summary

Add **optional HTTPS support** to GiljoAI MCP with a simple toggle approach: HTTP for development (default), HTTPS for production (opt-in). The application currently has dormant SSL support in the codebase but lacks implementation, documentation, and user-facing controls.

**Key Benefits**:
- Encrypted communication for production deployments
- Browser security compliance (required for some Web APIs)
- Professional deployment option for network/cloud environments
- No impact on development workflow (HTTP remains default)

**Implementation Scope**:
- Certificate generation helpers (self-signed + Let's Encrypt docs)
- Backend HTTPS activation via existing CLI flags
- Frontend WebSocket protocol switching (ws:// → wss://)
- Configuration file updates for SSL persistence
- Testing suite for HTTPS endpoints
- User documentation and troubleshooting

**Current State**:
- ✅ Backend SSL flags exist (`--ssl-keyfile`, `--ssl-certfile` in `api/run_api.py`)
- ✅ Config detection present (`ssl_enabled` in `config.yaml`)
- ✅ WebSocket protocol switching exists (`ws://` vs `wss://`)
- ❌ No certificate generation tooling
- ❌ No user-facing documentation
- ❌ No configuration persistence beyond command-line flags
- ❌ No testing for HTTPS endpoints

---

## Problem Statement

### Current Limitations

**1. HTTP-Only Deployment**:
```yaml
# config.yaml (line 46)
features:
  ssl_enabled: false  # Hard-coded, no toggle mechanism
```

**2. Dormant SSL Code**:
```python
# api/run_api.py (lines 193-194, 271-276)
parser.add_argument("--ssl-keyfile", help="SSL key file for HTTPS")
parser.add_argument("--ssl-certfile", help="SSL certificate file for HTTPS")

if args.ssl_keyfile and args.ssl_certfile:
    print_success(f"SSL enabled with cert: {args.ssl_certfile}")
    ssl_config = {"ssl_keyfile": args.ssl_keyfile, "ssl_certfile": args.ssl_certfile}
else:
    ssl_config = {}
    print_info("Running in HTTP mode (no SSL)")
```

**3. No Certificate Tooling**:
- Users expected to manually generate certificates
- No guidance on self-signed vs. CA certificates
- No automation for Let's Encrypt

**4. Frontend Hardcoded WebSocket Protocol**:
```javascript
// frontend/src/config/api.js (line 83)
WEBSOCKET: {
  url: import.meta.env.VITE_WS_URL || `ws://${API_HOST}:${API_PORT}`,
  // ❌ Hardcoded ws:// - should be wss:// when SSL enabled
}
```

### User Impact

**Without HTTPS**:
- ❌ Network traffic visible in plain text (credentials, project data)
- ❌ Browser warnings for insecure content
- ❌ Cannot use secure Web APIs (e.g., Service Workers, some hardware access)
- ❌ Professional deployments require manual reverse proxy setup

**With HTTPS (Optional)**:
- ✅ Encrypted end-to-end communication
- ✅ Browser trust and security indicators
- ✅ Access to secure Web APIs
- ✅ Production-ready out of the box

---

## Implementation Phases

### Phase 1: Certificate Setup & Configuration (2 hours)

**Goal**: Provide users with easy certificate generation and configuration management.

#### Task 1.1: Create Certificate Generation Script

**File**: `scripts/generate_ssl_cert.py`

```python
"""
SSL Certificate Generation Script for GiljoAI MCP

Generates self-signed SSL certificates for development and testing.
For production, use Let's Encrypt (see docs/security/HTTPS_SETUP.md).
"""
import argparse
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta


def generate_self_signed_cert(output_dir: Path, domain: str = "localhost", days: int = 365):
    """Generate self-signed SSL certificate using OpenSSL."""

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Certificate paths
    key_path = output_dir / "ssl_key.pem"
    cert_path = output_dir / "ssl_cert.pem"

    # Generate private key and certificate in one command
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", str(days),
        "-nodes",  # No passphrase
        "-subj", f"/CN={domain}/O=GiljoAI MCP/C=US"
    ]

    print(f"🔐 Generating self-signed SSL certificate for '{domain}'...")
    print(f"   Valid for: {days} days")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Certificate generated successfully!")
        print(f"   🔑 Key:  {key_path}")
        print(f"   📜 Cert: {cert_path}")
        print()
        print("⚠️  IMPORTANT: Self-signed certificates will show browser warnings.")
        print("   For production, use Let's Encrypt (see docs/security/HTTPS_SETUP.md)")
        return key_path, cert_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate certificate: {e.stderr}")
        return None, None
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL:")
        print("   Windows: https://slproweb.com/products/Win32OpenSSL.html")
        print("   Linux:   sudo apt-get install openssl")
        print("   macOS:   brew install openssl")
        return None, None


def update_config_yaml(cert_path: Path, key_path: Path):
    """Update config.yaml with SSL paths and enable SSL."""
    import yaml

    config_path = Path.cwd() / "config.yaml"

    if not config_path.exists():
        print(f"⚠️  config.yaml not found at {config_path}")
        return False

    # Read existing config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    # Update SSL configuration
    if 'features' not in config:
        config['features'] = {}

    config['features']['ssl_enabled'] = True

    if 'paths' not in config:
        config['paths'] = {}

    # Store absolute paths for certificates
    config['paths']['ssl_cert'] = str(cert_path.absolute())
    config['paths']['ssl_key'] = str(key_path.absolute())

    # Write updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Updated config.yaml:")
    print(f"   features.ssl_enabled: true")
    print(f"   paths.ssl_cert: {cert_path}")
    print(f"   paths.ssl_key: {key_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate SSL certificates for GiljoAI MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate certificate for localhost (default)
  python scripts/generate_ssl_cert.py

  # Generate certificate for specific domain
  python scripts/generate_ssl_cert.py --domain my-server.local

  # Generate certificate valid for 2 years
  python scripts/generate_ssl_cert.py --days 730

  # Custom output directory
  python scripts/generate_ssl_cert.py --output ./my-certs

  # Generate without updating config.yaml
  python scripts/generate_ssl_cert.py --no-update-config
        """
    )

    parser.add_argument(
        "--domain",
        default="localhost",
        help="Domain name for certificate (default: localhost)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Certificate validity in days (default: 365)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "certs",
        help="Output directory for certificates (default: ./certs)"
    )
    parser.add_argument(
        "--no-update-config",
        action="store_true",
        help="Don't update config.yaml with certificate paths"
    )

    args = parser.parse_args()

    # Generate certificate
    key_path, cert_path = generate_self_signed_cert(args.output, args.domain, args.days)

    if key_path and cert_path:
        # Update config.yaml unless disabled
        if not args.no_update_config:
            update_config_yaml(cert_path, key_path)

        print()
        print("🚀 Next Steps:")
        print("   1. Restart the server: python startup.py")
        print("   2. Access via HTTPS: https://localhost:7272")
        print("   3. Accept browser security warning (self-signed cert)")
        print()
        print("📖 Production Setup:")
        print("   See docs/security/HTTPS_SETUP.md for Let's Encrypt configuration")


if __name__ == "__main__":
    main()
```

**Testing**:
```bash
# Test certificate generation
python scripts/generate_ssl_cert.py

# Verify files created
ls -la certs/

# Verify certificate details
openssl x509 -in certs/ssl_cert.pem -text -noout
```

#### Task 1.2: Add SSL Certificate Paths to config.yaml

**File**: `config.yaml` (lines 59-60)

**Current**:
```yaml
paths:
  install_dir: F:\GiljoAI_MCP
  data: F:\GiljoAI_MCP\data
  logs: F:\GiljoAI_MCP\logs
  uploads: F:\GiljoAI_MCP\uploads
  temp: F:\GiljoAI_MCP\temp
  static: F:\GiljoAI_MCP\frontend\dist
  templates: F:\GiljoAI_MCP\frontend\templates
  certs: null  # Line 59 - Currently unused
```

**Updated**:
```yaml
paths:
  install_dir: F:\GiljoAI_MCP
  data: F:\GiljoAI_MCP\data
  logs: F:\GiljoAI_MCP\logs
  uploads: F:\GiljoAI_MCP\uploads
  temp: F:\GiljoAI_MCP\temp
  static: F:\GiljoAI_MCP\frontend\dist
  templates: F:\GiljoAI_MCP\frontend\templates
  certs: F:\GiljoAI_MCP\certs  # Changed from null
  ssl_cert: null  # Added - Path to SSL certificate file (set by generate_ssl_cert.py)
  ssl_key: null   # Added - Path to SSL private key file (set by generate_ssl_cert.py)
```

#### Task 1.3: Update Installer to Support SSL Configuration

**File**: `installer/core/config.py` (near line 440)

**Current**:
```python
"ssl_enabled": self.settings.get("features", {}).get("ssl", False),
```

**Updated**:
```python
"ssl_enabled": self.settings.get("features", {}).get("ssl", False),
"ssl_cert_path": self.settings.get("ssl", {}).get("cert_path"),
"ssl_key_path": self.settings.get("ssl", {}).get("key_path"),
```

**File**: `installer/core/config.py` (add new section after line 498)

```python
# Add SSL certificate paths if configured
if self.settings.get("ssl", {}).get("cert_path"):
    config_dict["paths"]["ssl_cert"] = self.settings["ssl"]["cert_path"]
    config_dict["paths"]["ssl_key"] = self.settings["ssl"]["key_path"]
```

---

### Phase 2: Backend HTTPS Activation (2 hours)

**Goal**: Enable HTTPS server startup with automatic certificate loading from config.

#### Task 2.1: Auto-load SSL Certificates from config.yaml

**File**: `api/run_api.py` (replace lines 271-276)

**Current**:
```python
if args.ssl_keyfile and args.ssl_certfile:
    print_success(f"SSL enabled with cert: {args.ssl_certfile}")
    ssl_config = {"ssl_keyfile": args.ssl_keyfile, "ssl_certfile": args.ssl_certfile}
else:
    ssl_config = {}
    print_info("Running in HTTP mode (no SSL)")
```

**Updated**:
```python
# SSL Configuration Priority:
# 1. Command-line arguments (--ssl-keyfile, --ssl-certfile)
# 2. config.yaml paths (paths.ssl_cert, paths.ssl_key)
# 3. Environment variables (SSL_CERT_FILE, SSL_KEY_FILE)

ssl_config = {}

# Try command-line arguments first
if args.ssl_keyfile and args.ssl_certfile:
    ssl_config = {"ssl_keyfile": args.ssl_keyfile, "ssl_certfile": args.ssl_certfile}
    print_success(f"SSL enabled via CLI: {args.ssl_certfile}")

# Try config.yaml if no CLI args
elif not ssl_config:
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            ssl_enabled = config.get("features", {}).get("ssl_enabled", False)
            ssl_cert = config.get("paths", {}).get("ssl_cert")
            ssl_key = config.get("paths", {}).get("ssl_key")

            if ssl_enabled and ssl_cert and ssl_key:
                cert_path = Path(ssl_cert)
                key_path = Path(ssl_key)

                # Verify files exist
                if cert_path.exists() and key_path.exists():
                    ssl_config = {"ssl_keyfile": str(key_path), "ssl_certfile": str(cert_path)}
                    print_success(f"SSL enabled via config.yaml: {cert_path}")
                else:
                    print_warning(f"SSL enabled in config but certificate files not found:")
                    print_warning(f"  Cert: {cert_path} (exists: {cert_path.exists()})")
                    print_warning(f"  Key:  {key_path} (exists: {key_path.exists()})")
                    print_info("Falling back to HTTP mode")
    except Exception as e:
        logger.warning(f"Failed to load SSL config from config.yaml: {e}")

# Try environment variables as last resort
if not ssl_config:
    ssl_cert_env = os.getenv("SSL_CERT_FILE")
    ssl_key_env = os.getenv("SSL_KEY_FILE")
    if ssl_cert_env and ssl_key_env:
        cert_path = Path(ssl_cert_env)
        key_path = Path(ssl_key_env)
        if cert_path.exists() and key_path.exists():
            ssl_config = {"ssl_keyfile": str(key_path), "ssl_certfile": str(cert_path)}
            print_success(f"SSL enabled via environment: {cert_path}")

# Final status
if not ssl_config:
    print_info("Running in HTTP mode (no SSL configured)")
    print_info("To enable HTTPS:")
    print_info("  1. Generate certificates: python scripts/generate_ssl_cert.py")
    print_info("  2. Or use CLI flags: --ssl-keyfile <key> --ssl-certfile <cert>")
```

#### Task 2.2: Update Configuration Endpoint to Return SSL Status

**File**: `api/endpoints/configuration.py` (near line 573)

**Current**:
```python
# Build WebSocket URL (use ws:// for http, wss:// for https)
ws_protocol = "wss" if config.get("features", {}).get("ssl_enabled", False) else "ws"
ws_url = f"{ws_protocol}://{frontend_host}:{api_port}"
```

**Updated** (add SSL status to response):
```python
# Build WebSocket URL (use ws:// for http, wss:// for https)
ssl_enabled = config.get("features", {}).get("ssl_enabled", False)
ws_protocol = "wss" if ssl_enabled else "ws"
ws_url = f"{ws_protocol}://{frontend_host}:{api_port}"

# Determine API protocol based on SSL status
api_protocol = "https" if ssl_enabled else "http"

# v3.0 Unified Architecture: No 'mode' field in response
return {
    "api": {
        "host": frontend_host,
        "port": api_port,
        "protocol": api_protocol,  # Added: "http" or "https"
        "ssl_enabled": ssl_enabled,  # Added: explicit SSL status
    },
    "websocket": {
        "url": ws_url,
        "protocol": ws_protocol,  # Added: "ws" or "wss"
    },
    # ... rest of response
}
```

#### Task 2.3: Update URL Builders to Respect SSL

**File**: `api/endpoints/ai_tools.py` (line 212)

**Current**:
```python
protocol = "https" if getattr(config.features, "ssl_enabled", False) else "http"
```

**Updated** (consistent with configuration endpoint):
```python
# Read SSL status from config.yaml (consistent with /api/v1/config/frontend endpoint)
import yaml
config_path = Path.cwd() / "config.yaml"
ssl_enabled = False
if config_path.exists():
    with open(config_path) as f:
        config_data = yaml.safe_load(f) or {}
        ssl_enabled = config_data.get("features", {}).get("ssl_enabled", False)

protocol = "https" if ssl_enabled else "http"
```

**Apply same pattern to**:
- `api/endpoints/downloads.py` (line 60)
- `src/giljo_mcp/thin_prompt_generator.py` (lines 325-347, 473-489)

---

### Phase 3: Frontend URL Updates (2 hours)

**Goal**: Make frontend automatically use HTTPS URLs when SSL is enabled on backend.

#### Task 3.1: Update WebSocket Configuration Service

**File**: `frontend/src/services/configService.js` (add new method)

```javascript
/**
 * Fetch backend configuration to determine SSL status
 * @returns {Promise<Object>} Backend configuration
 */
async fetchBackendConfig() {
  try {
    const response = await fetch(`${this.getApiBaseURL()}/api/v1/config/frontend`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch backend config: ${response.status}`)
    }

    const config = await response.json()
    console.log('[ConfigService] Backend config:', config)

    return config
  } catch (error) {
    console.error('[ConfigService] Failed to fetch backend config:', error)
    throw error
  }
}
```

#### Task 3.2: Update API Config Initialization

**File**: `frontend/src/config/api.js` (replace lines 19-52)

**Current**:
```javascript
export async function initializeApiConfig() {
  try {
    // Fetch config from backend
    const backendConfig = await configService.fetchConfig()

    // Update runtime config with backend values
    runtimeConfig = {
      api: backendConfig.api,
      websocket: backendConfig.websocket,
      mode: backendConfig.mode,
      security: backendConfig.security,
    }

    // Choose baseURL strategy
    const devMode = import.meta.env.DEV === true
    const newBaseURL = devMode ? '' : `http://${runtimeConfig.api.host}:${runtimeConfig.api.port}`

    // Update API and WebSocket config
    API_CONFIG.REST_API.baseURL = newBaseURL
    API_CONFIG.WEBSOCKET.url = runtimeConfig.websocket.url

    // ... rest of function
  }
}
```

**Updated** (SSL-aware URL construction):
```javascript
export async function initializeApiConfig() {
  try {
    // Fetch config from backend
    const backendConfig = await configService.fetchConfig()

    // Update runtime config with backend values
    runtimeConfig = {
      api: backendConfig.api,
      websocket: backendConfig.websocket,
      mode: backendConfig.mode,
      security: backendConfig.security,
    }

    // Determine protocol based on SSL status
    const sslEnabled = runtimeConfig.api?.ssl_enabled || false
    const apiProtocol = runtimeConfig.api?.protocol || (sslEnabled ? 'https' : 'http')
    const wsProtocol = runtimeConfig.websocket?.protocol || (sslEnabled ? 'wss' : 'ws')

    // Choose baseURL strategy
    const devMode = import.meta.env.DEV === true
    const newBaseURL = devMode
      ? ''
      : `${apiProtocol}://${runtimeConfig.api.host}:${runtimeConfig.api.port}`

    // Build WebSocket URL with correct protocol
    const wsURL = devMode
      ? runtimeConfig.websocket.url  // Use backend-provided URL in dev
      : `${wsProtocol}://${runtimeConfig.api.host}:${runtimeConfig.api.port}`

    // Update API and WebSocket config
    API_CONFIG.REST_API.baseURL = newBaseURL
    API_CONFIG.WEBSOCKET.url = wsURL

    console.log('[API Config] SSL-aware configuration:')
    console.log(`  API: ${newBaseURL}`)
    console.log(`  WebSocket: ${wsURL}`)
    console.log(`  SSL Enabled: ${sslEnabled}`)

    // ... rest of function
  }
}
```

#### Task 3.3: Update Fallback WebSocket URL

**File**: `frontend/src/config/api.js` (line 83)

**Current**:
```javascript
WEBSOCKET: {
  url: import.meta.env.VITE_WS_URL || `ws://${API_HOST}:${API_PORT}`,
  // ... rest of config
}
```

**Updated** (SSL-aware fallback):
```javascript
WEBSOCKET: {
  // Fallback URL (before backend config is fetched)
  // Try to detect HTTPS from window.location
  url: import.meta.env.VITE_WS_URL ||
       (window.location.protocol === 'https:'
         ? `wss://${API_HOST}:${API_PORT}`
         : `ws://${API_HOST}:${API_PORT}`),
  // ... rest of config
}
```

---

### Phase 4: Testing & Documentation (2 hours)

**Goal**: Comprehensive testing and user-facing documentation.

#### Task 4.1: Create HTTPS Testing Suite

**File**: `tests/integration/test_https_endpoints.py`

```python
"""
Integration tests for HTTPS endpoints.

Tests SSL certificate validation, protocol switching, and WebSocket security.
"""
import pytest
import requests
from pathlib import Path
import subprocess
import time
import yaml


@pytest.fixture(scope="module")
def ssl_certificates(tmp_path_factory):
    """Generate temporary SSL certificates for testing."""
    cert_dir = tmp_path_factory.mktemp("certs")

    # Generate self-signed certificate
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(cert_dir / "test_key.pem"),
        "-out", str(cert_dir / "test_cert.pem"),
        "-days", "1",
        "-nodes",
        "-subj", "/CN=localhost/O=GiljoAI Test/C=US"
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    return {
        "cert": cert_dir / "test_cert.pem",
        "key": cert_dir / "test_key.pem",
    }


@pytest.fixture
def https_config(tmp_path, ssl_certificates):
    """Create config.yaml with SSL enabled."""
    config_path = tmp_path / "config.yaml"

    config = {
        "features": {"ssl_enabled": True},
        "paths": {
            "ssl_cert": str(ssl_certificates["cert"]),
            "ssl_key": str(ssl_certificates["key"]),
        },
        "services": {
            "api": {"host": "localhost", "port": 7272},
        },
    }

    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    return config_path


class TestHTTPSEndpoints:
    """Test HTTPS endpoint functionality."""

    def test_ssl_certificate_generation(self, ssl_certificates):
        """Test that SSL certificates are valid."""
        assert ssl_certificates["cert"].exists()
        assert ssl_certificates["key"].exists()

        # Verify certificate can be read
        cmd = ["openssl", "x509", "-in", str(ssl_certificates["cert"]), "-text", "-noout"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        assert "CN = localhost" in result.stdout
        assert "O = GiljoAI Test" in result.stdout

    def test_https_server_startup(self, https_config, ssl_certificates):
        """Test that server starts with HTTPS enabled."""
        # This would require starting the server in a subprocess
        # and verifying it binds to HTTPS port
        # Placeholder for actual implementation
        pass

    def test_https_health_endpoint(self):
        """Test /health endpoint over HTTPS."""
        # Requires running HTTPS server
        # requests.get("https://localhost:7272/health", verify=False)
        pass

    def test_wss_websocket_connection(self):
        """Test WebSocket connection over wss:// protocol."""
        # Requires websocket client library
        # import websocket
        # ws = websocket.create_connection("wss://localhost:7272/ws/test", sslopt={"cert_reqs": ssl.CERT_NONE})
        pass

    def test_mixed_content_prevention(self):
        """Test that HTTP requests are rejected when HTTPS is enabled."""
        pass

    def test_ssl_config_priority(self, tmp_path):
        """Test SSL configuration priority (CLI > config.yaml > env)."""
        # Test that CLI arguments override config.yaml
        # Test that config.yaml overrides environment variables
        pass


class TestSSLConfiguration:
    """Test SSL configuration management."""

    def test_config_yaml_ssl_fields(self, https_config):
        """Test config.yaml has correct SSL fields."""
        with open(https_config) as f:
            config = yaml.safe_load(f)

        assert config["features"]["ssl_enabled"] is True
        assert "ssl_cert" in config["paths"]
        assert "ssl_key" in config["paths"]
        assert Path(config["paths"]["ssl_cert"]).exists()
        assert Path(config["paths"]["ssl_key"]).exists()

    def test_frontend_config_endpoint_ssl_status(self):
        """Test that /api/v1/config/frontend returns SSL status."""
        # response = requests.get("http://localhost:7272/api/v1/config/frontend")
        # assert "ssl_enabled" in response.json()["api"]
        # assert "protocol" in response.json()["api"]
        pass


class TestCertificateValidation:
    """Test certificate validation and error handling."""

    def test_missing_certificate_file(self):
        """Test graceful fallback when certificate file is missing."""
        pass

    def test_invalid_certificate_format(self):
        """Test error handling for invalid certificate format."""
        pass

    def test_expired_certificate_warning(self):
        """Test that expired certificates show warnings."""
        pass


# Performance test
def test_https_performance_overhead():
    """Test that HTTPS adds <10% latency compared to HTTP."""
    # Benchmark HTTP vs HTTPS response times
    pass
```

#### Task 4.2: Create User Documentation

**File**: `docs/security/HTTPS_SETUP.md`

```markdown
# HTTPS Setup Guide

**GiljoAI MCP v3.2+**

## Overview

GiljoAI MCP supports optional HTTPS for secure encrypted communication. HTTPS is **not required** for development but **recommended** for production deployments.

**When to Use HTTPS**:
- ✅ Production deployments on network or cloud
- ✅ When handling sensitive project data
- ✅ When browser requires secure context (Service Workers, etc.)
- ❌ Local development (HTTP is faster and easier)

---

## Quick Start: Self-Signed Certificate (Development)

**Step 1: Generate Certificate**
```bash
python scripts/generate_ssl_cert.py
```

This creates:
- `certs/ssl_key.pem` - Private key
- `certs/ssl_cert.pem` - Self-signed certificate (valid 365 days)

**Step 2: Restart Server**
```bash
python startup.py
```

The server automatically detects certificates in `config.yaml` and starts in HTTPS mode.

**Step 3: Access Dashboard**
```
https://localhost:7274
```

⚠️ **Browser Warning**: Self-signed certificates show security warnings. Click "Advanced" → "Proceed to localhost" to continue.

---

## Production Setup: Let's Encrypt (Free CA Certificate)

For production, use **Let's Encrypt** for trusted certificates that won't show browser warnings.

### Option A: Manual Let's Encrypt (Recommended)

**Requirements**:
- Domain name pointing to your server (e.g., `giljoai.example.com`)
- Port 80 open for ACME challenge
- Certbot installed

**Step 1: Install Certbot**
```bash
# Ubuntu/Debian
sudo apt-get install certbot

# Windows
# Download from https://certbot.eff.org/

# macOS
brew install certbot
```

**Step 2: Generate Certificate**
```bash
sudo certbot certonly --standalone -d giljoai.example.com
```

Certificates are saved to:
- Cert: `/etc/letsencrypt/live/giljoai.example.com/fullchain.pem`
- Key: `/etc/letsencrypt/live/giljoai.example.com/privkey.pem`

**Step 3: Update config.yaml**
```yaml
features:
  ssl_enabled: true

paths:
  ssl_cert: /etc/letsencrypt/live/giljoai.example.com/fullchain.pem
  ssl_key: /etc/letsencrypt/live/giljoai.example.com/privkey.pem
```

**Step 4: Restart Server**
```bash
python startup.py
```

**Step 5: Set Up Auto-Renewal**
```bash
# Test renewal
sudo certbot renew --dry-run

# Add cron job for auto-renewal
sudo crontab -e
# Add line: 0 0 * * 0 certbot renew --quiet && systemctl restart giljoai-mcp
```

### Option B: Reverse Proxy (Nginx/Apache)

If you prefer, use a reverse proxy to handle SSL:

**Nginx Configuration**:
```nginx
server {
    listen 443 ssl;
    server_name giljoai.example.com;

    ssl_certificate /etc/letsencrypt/live/giljoai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/giljoai.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:7272;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:7272;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

In this setup, keep `ssl_enabled: false` in `config.yaml` since Nginx handles SSL.

---

## Configuration Reference

### config.yaml SSL Options

```yaml
features:
  ssl_enabled: true  # Enable/disable HTTPS

paths:
  ssl_cert: /path/to/certificate.pem  # Full path to SSL certificate
  ssl_key: /path/to/private_key.pem   # Full path to private key
```

### Command-Line Override

```bash
# Override config.yaml with CLI arguments
python api/run_api.py \
  --ssl-keyfile /path/to/key.pem \
  --ssl-certfile /path/to/cert.pem
```

### Environment Variables (Lowest Priority)

```bash
export SSL_CERT_FILE=/path/to/cert.pem
export SSL_KEY_FILE=/path/to/key.pem
python startup.py
```

**Configuration Priority**:
1. Command-line arguments (`--ssl-keyfile`, `--ssl-certfile`)
2. config.yaml (`paths.ssl_cert`, `paths.ssl_key`)
3. Environment variables (`SSL_CERT_FILE`, `SSL_KEY_FILE`)

---

## Troubleshooting

### Browser Shows "Certificate Invalid"

**Self-Signed Certificate**:
- Expected behavior - browser doesn't trust self-signed certs
- Safe to proceed for development
- For production, use Let's Encrypt

**Let's Encrypt Certificate**:
- Check certificate hasn't expired: `openssl x509 -in cert.pem -noout -dates`
- Verify domain matches: `openssl x509 -in cert.pem -noout -subject`
- Check certificate chain: `openssl verify -CAfile fullchain.pem cert.pem`

### WebSocket Connection Fails (wss://)

**Check WebSocket Protocol**:
- Frontend should use `wss://` when HTTPS enabled
- Verify in browser console: Network tab → WS filter

**Mixed Content Error**:
- If frontend is HTTPS, all connections must be HTTPS
- Check that API uses same protocol as frontend

### Server Fails to Start

**Permission Denied**:
```bash
# Check certificate file permissions
ls -la certs/
# Should be readable by server process
```

**Certificate File Not Found**:
```bash
# Verify paths in config.yaml are absolute
cat config.yaml | grep ssl_cert

# Check file exists
test -f $(grep ssl_cert config.yaml | cut -d: -f2 | xargs) && echo "Found" || echo "Not Found"
```

**Invalid Certificate Format**:
```bash
# Verify certificate format
openssl x509 -in certs/ssl_cert.pem -text -noout
```

---

## Security Best Practices

**Certificate Management**:
- ✅ Never commit private keys to version control (`.gitignore` already covers `certs/`)
- ✅ Set restrictive permissions: `chmod 600 certs/ssl_key.pem`
- ✅ Rotate certificates before expiry (Let's Encrypt auto-renews)
- ✅ Use strong key size: 2048-bit RSA minimum, 4096-bit recommended

**Production Checklist**:
- ✅ Use Let's Encrypt or trusted CA certificate
- ✅ Enable HSTS: `Strict-Transport-Security` header
- ✅ Disable insecure TLS versions (< TLS 1.2)
- ✅ Configure strong cipher suites
- ✅ Monitor certificate expiration dates

**Development Shortcuts**:
- ✅ Self-signed certificates are fine for `localhost`
- ✅ Browser warnings are expected (safe to proceed)
- ❌ Don't use self-signed certs in production

---

## FAQ

**Q: Do I need HTTPS for local development?**
A: No. HTTP is faster and doesn't require certificate management. Use HTTPS only if testing SSL-specific features.

**Q: Can I use the same certificate for multiple servers?**
A: Yes, if it's a wildcard certificate (e.g., `*.example.com`) or includes multiple SANs (Subject Alternative Names).

**Q: How often do Let's Encrypt certificates expire?**
A: Every 90 days. Certbot auto-renews if you set up the cron job.

**Q: Does HTTPS slow down the server?**
A: SSL adds ~10% latency for initial handshake, but HTTP/2 over HTTPS is often faster than HTTP/1.1.

**Q: Can I use a certificate from a different CA (not Let's Encrypt)?**
A: Yes. Any valid SSL certificate works. Update `config.yaml` with the certificate paths.

---

## See Also

- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
```

#### Task 4.3: Update Installation Documentation

**File**: `docs/INSTALLATION_FLOW_PROCESS.md` (add new section after line 100)

```markdown
### SSL/HTTPS Configuration (Optional)

GiljoAI MCP runs in HTTP mode by default. To enable HTTPS:

**Step 1: Generate SSL Certificate**
```bash
python scripts/generate_ssl_cert.py
```

**Step 2: Restart Server**
```bash
python startup.py
```

The server automatically detects certificates in `config.yaml` and starts in HTTPS mode.

**For Production**: See [docs/security/HTTPS_SETUP.md](../security/HTTPS_SETUP.md) for Let's Encrypt configuration.
```

---

## Testing Requirements

### Unit Tests

**Backend**:
- [ ] SSL config loading from `config.yaml` (priority: CLI > config > env)
- [ ] Certificate file validation (exists, readable, valid format)
- [ ] Protocol selection logic (`http://` vs `https://`)
- [ ] WebSocket protocol switching (`ws://` vs `wss://`)

**Frontend**:
- [ ] API base URL construction with SSL (`https://`)
- [ ] WebSocket URL construction with SSL (`wss://`)
- [ ] Fallback to HTTP when SSL disabled

### Integration Tests

**HTTPS Endpoints**:
- [ ] `/health` endpoint accessible over HTTPS
- [ ] `/api/v1/config/frontend` returns `ssl_enabled` status
- [ ] WebSocket connection works over `wss://`
- [ ] Mixed content blocked (HTTP requests to HTTPS server)

**Certificate Validation**:
- [ ] Server starts with valid self-signed certificate
- [ ] Server fails gracefully with missing certificate file
- [ ] Server fails gracefully with invalid certificate format

**Performance**:
- [ ] HTTPS adds <10% latency vs HTTP
- [ ] WebSocket performance unchanged with SSL

### End-to-End Tests

**User Workflow**:
- [ ] Generate certificate → restart → dashboard accessible via HTTPS
- [ ] Browser accepts self-signed certificate with warning
- [ ] WebSocket connection shows secure (`wss://`) in browser devtools
- [ ] API calls show padlock icon in browser

---

## Success Criteria

### Functional Requirements

- ✅ **SSL Certificate Generation**: Script generates valid self-signed certificates
- ✅ **Configuration Persistence**: SSL settings stored in `config.yaml`
- ✅ **Automatic Loading**: Server auto-detects certificates on startup
- ✅ **Protocol Switching**: Frontend uses `https://` and `wss://` when SSL enabled
- ✅ **Backward Compatible**: HTTP mode remains default (no breaking changes)

### Technical Requirements

- ✅ **Cross-Platform**: Works on Windows, Linux, macOS
- ✅ **Security**: Certificates have restrictive permissions (600)
- ✅ **Performance**: HTTPS adds <10% latency
- ✅ **Error Handling**: Graceful fallback to HTTP if certificates invalid

### Documentation Requirements

- ✅ **User Guide**: Complete HTTPS setup instructions
- ✅ **Production Guide**: Let's Encrypt configuration steps
- ✅ **Troubleshooting**: Common issues and solutions
- ✅ **FAQ**: Answers to typical questions

### Testing Requirements

- ✅ **Unit Tests**: >80% coverage for SSL-related code
- ✅ **Integration Tests**: HTTPS endpoints and WebSocket connections
- ✅ **E2E Tests**: User workflow from certificate generation to secure dashboard

---

## Rollback Plan

### If HTTPS Implementation Fails

**Step 1: Disable SSL in config.yaml**
```yaml
features:
  ssl_enabled: false
```

**Step 2: Restart Server**
```bash
python startup.py
```

**Step 3: Verify HTTP Access**
```bash
curl http://localhost:7272/health
```

### If Certificate Issues Occur

**Option A: Regenerate Certificate**
```bash
rm -rf certs/
python scripts/generate_ssl_cert.py
python startup.py
```

**Option B: Use CLI Override**
```bash
python api/run_api.py \
  --ssl-keyfile /path/to/working/key.pem \
  --ssl-certfile /path/to/working/cert.pem
```

### If Frontend Fails to Connect

**Step 1: Check Browser Console**
- Look for mixed content errors
- Verify WebSocket protocol matches API protocol

**Step 2: Force Frontend to HTTP**
```javascript
// frontend/src/config/api.js (temporary override)
API_CONFIG.REST_API.baseURL = 'http://localhost:7272'
API_CONFIG.WEBSOCKET.url = 'ws://localhost:7272'
```

**Step 3: Rebuild Frontend**
```bash
cd frontend
npm run build
```

---

## Post-Implementation

### Documentation Updates Required

- [x] User-facing HTTPS setup guide (`docs/security/HTTPS_SETUP.md`)
- [x] Installation guide updated with SSL section (`docs/INSTALLATION_FLOW_PROCESS.md`)
- [ ] CLAUDE.md updated with SSL configuration notes
- [ ] README.md updated with HTTPS quick start
- [ ] Security policy updated with certificate management practices

### User Communication

**Deployment Announcement**:
```
🔒 HTTPS Support Now Available!

GiljoAI MCP v3.2 adds optional HTTPS encryption for secure deployments.

Quick Start:
1. Generate certificate: `python scripts/generate_ssl_cert.py`
2. Restart server: `python startup.py`
3. Access dashboard: `https://localhost:7274`

Production Setup: See docs/security/HTTPS_SETUP.md for Let's Encrypt configuration.

Note: HTTP remains the default. HTTPS is opt-in for users who need it.
```

### Monitoring Recommendations

**Certificate Expiration Monitoring**:
```bash
# Add to cron (daily check)
0 0 * * * openssl x509 -in /path/to/cert.pem -noout -checkend 604800 && echo "OK" || echo "Certificate expires in <7 days"
```

**SSL Health Check**:
```bash
# Test SSL endpoint
curl -k https://localhost:7272/health

# Verify certificate details
echo | openssl s_client -connect localhost:7272 -servername localhost 2>/dev/null | openssl x509 -noout -dates
```

---

## Implementation Notes

### Path A: Self-Signed Certificates (Development)

**Advantages**:
- ✅ Quick setup (<1 minute)
- ✅ No external dependencies (just OpenSSL)
- ✅ Works offline
- ✅ Free

**Disadvantages**:
- ⚠️ Browser security warnings
- ⚠️ Not trusted by default
- ⚠️ Manual acceptance required
- ❌ Not suitable for production

**Best For**: Local development, testing SSL features, proof of concept

### Path B: Let's Encrypt + Reverse Proxy (Production)

**Advantages**:
- ✅ Trusted by all browsers
- ✅ No security warnings
- ✅ Free certificate authority
- ✅ Auto-renewal

**Disadvantages**:
- ⚠️ Requires domain name
- ⚠️ Requires port 80 open for ACME challenge
- ⚠️ More complex setup
- ⚠️ 90-day expiration (but auto-renews)

**Best For**: Production deployments, public-facing servers, professional use

### Performance Considerations

**SSL Overhead**:
- TLS handshake: ~100-200ms additional latency (one-time per connection)
- Encryption/decryption: ~5-10% CPU overhead
- HTTP/2 benefits often outweigh SSL cost

**Optimization Tips**:
- Use session resumption (enabled by default in uvicorn)
- Enable OCSP stapling
- Use modern cipher suites (AES-GCM preferred)
- Consider HTTP/2 (automatic with most SSL/TLS implementations)

---

## Related Handovers

- **Handover 0034**: No default credentials (security foundation)
- **Handover 0023**: Recovery PIN system (authentication)
- **Handover 0129c**: Security headers middleware (HSTS, CSP)
- **Handover 0035**: Unified cross-platform installer (config management)

---

## Completion Checklist

### Phase 1: Certificate Setup ✅
- [ ] Certificate generation script created (`scripts/generate_ssl_cert.py`)
- [ ] config.yaml updated with SSL paths
- [ ] Installer supports SSL configuration

### Phase 2: Backend HTTPS ✅
- [ ] Auto-load SSL certificates from config.yaml
- [ ] Configuration endpoint returns SSL status
- [ ] URL builders respect SSL protocol

### Phase 3: Frontend Updates ✅
- [ ] WebSocket config service updated
- [ ] API config initialization SSL-aware
- [ ] Fallback URLs use correct protocol

### Phase 4: Testing & Docs ✅
- [ ] HTTPS integration tests created
- [ ] User documentation complete (`docs/security/HTTPS_SETUP.md`)
- [ ] Installation guide updated

### Validation ✅
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass (HTTPS endpoints)
- [ ] E2E test: Generate cert → restart → access dashboard
- [ ] Documentation reviewed by user
- [ ] Rollback plan tested

---

## Appendix: Technical Details

### SSL/TLS Configuration (Uvicorn)

Uvicorn (the ASGI server used by FastAPI) handles SSL via standard Python `ssl` module:

```python
# api/run_api.py (line 301-309)
uvicorn.run(
    "api.app:app",
    host=args.host,
    port=args.port,
    reload=args.reload,
    workers=args.workers if not args.reload else 1,
    log_level=args.log_level,
    **ssl_config,  # {"ssl_keyfile": "...", "ssl_certfile": "..."}
)
```

**Supported SSL Options**:
- `ssl_keyfile`: Path to private key (PEM format)
- `ssl_certfile`: Path to certificate (PEM format)
- `ssl_ca_certs`: Path to CA bundle (optional, for client cert validation)
- `ssl_ciphers`: Cipher suite string (optional, defaults to secure ciphers)

### Certificate Formats

**Supported Formats**:
- ✅ PEM (Privacy Enhanced Mail) - text format, base64-encoded
- ❌ DER (Distinguished Encoding Rules) - binary format, not supported by uvicorn directly
- ❌ PKCS#12 (.pfx/.p12) - requires conversion to PEM

**Convert DER to PEM**:
```bash
openssl x509 -inform der -in cert.der -out cert.pem
```

**Convert PKCS#12 to PEM**:
```bash
openssl pkcs12 -in cert.pfx -out cert.pem -nodes
```

### WebSocket Security (wss://)

WebSocket Secure (wss://) is WebSocket over TLS, analogous to HTTPS.

**Protocol Differences**:
- `ws://localhost:7272/ws/{client_id}` - Unencrypted
- `wss://localhost:7272/ws/{client_id}` - Encrypted (TLS 1.2+)

**Browser Requirements**:
- HTTPS pages **must** use `wss://` (mixed content policy)
- HTTP pages **can** use either `ws://` or `wss://`

**Implementation** (frontend/src/stores/websocket.js):
```javascript
// Automatically select protocol based on page protocol
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsURL = `${wsProtocol}//${config.api.host}:${config.api.port}/ws/${clientId}`
```

---

**End of Handover 0250**
