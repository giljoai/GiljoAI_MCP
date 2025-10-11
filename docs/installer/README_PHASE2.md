# GiljoAI MCP - Phase 2: Network Engineering

## Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| [PHASE2_SUMMARY.md](../PHASE2_SUMMARY.md) | Quick reference and overview | All users |
| [PHASE2_NETWORK_DELIVERY.md](PHASE2_NETWORK_DELIVERY.md) | Complete technical delivery | Developers |
| [PHASE2_ARCHITECTURE.md](PHASE2_ARCHITECTURE.md) | System architecture diagrams | Architects |
| [examples/server_mode_example.py](examples/server_mode_example.py) | Working code examples | Developers |

---

## What's New in Phase 2

Phase 2 adds **server mode** capabilities to the GiljoAI MCP installer, enabling network-accessible deployments with enterprise-grade security.

### Core Features

✅ **Network Configuration**
- SSL/TLS certificate generation (self-signed or existing)
- Network binding management (localhost vs 0.0.0.0)
- Port availability checking and conflict detection
- Security warnings for network exposure

✅ **Firewall Management**
- Cross-platform firewall rule generation
- Windows (PowerShell/netsh), Linux (UFW/iptables), macOS (pfctl)
- Rules generated but NOT auto-applied (security by design)
- Comprehensive platform-specific documentation

✅ **Security & Authentication**
- API key generation (gai_<token> format)
- Password hashing (PBKDF2-SHA256)
- Admin user creation
- Secure credential storage

---

## Installation Modes

### Localhost Mode (Phase 1)
```python
settings = {'mode': 'localhost'}
installer = LocalhostInstaller(settings)
installer.install()
```
- Binds to 127.0.0.1 only
- No firewall configuration needed
- Minimal security requirements
- Perfect for development

### Server Mode (Phase 2)
```python
settings = {
    'mode': 'server',
    'bind': '0.0.0.0',
    'features': {'ssl': True, 'api_keys': True},
    'ssl': {'type': 'self-signed'},
    'server': {
        'admin_user': 'admin',
        'admin_password': 'SecurePassword123!'
    }
}
installer = ServerInstaller(settings)
installer.install()
```
- Network-accessible deployment
- SSL/TLS encryption
- API key authentication
- Firewall configuration required

---

## Quick Start: Server Mode

### 1. Basic Server Installation

```bash
# Install with Python
python installer/cli.py --mode server \
    --bind 0.0.0.0 \
    --enable-ssl \
    --admin-username admin \
    --admin-password "SecurePass123!"
```

### 2. Review Generated Files

```
Installation creates:
├── certs/
│   ├── server.crt              # SSL certificate
│   └── server.key              # Private key
├── config.yaml                 # Main configuration
├── .env                        # Environment variables
├── firewall_rules.txt          # Quick firewall reference
└── installer/
    ├── credentials/
    │   ├── api_keys.yaml       # API key hashes
    │   └── users.yaml          # User credentials
    └── scripts/firewall/       # Platform-specific scripts
```

### 3. Apply Firewall Rules (Manual)

**Windows (PowerShell as Admin):**
```powershell
powershell -ExecutionPolicy Bypass installer\scripts\firewall\configure_windows_firewall.ps1
```

**Linux (Ubuntu/Debian):**
```bash
sudo bash installer/scripts/firewall/configure_ufw_firewall.sh
```

**macOS:**
```bash
sudo bash installer/scripts/firewall/configure_macos_firewall.sh
```

### 4. Start Server

```bash
# Windows
launchers\start_giljo.bat

# Linux/macOS
./launchers/start_giljo.sh
```

---

## Key Concepts

### Network Binding

| Binding | Accessibility | Use Case | Security |
|---------|--------------|----------|----------|
| 127.0.0.1 | Local only | Development | Minimal |
| 0.0.0.0 | Network/Internet | Production | Maximum |

**Important:** Binding to 0.0.0.0 exposes server to network. Always use SSL in production!

### SSL/TLS Certificates

#### Self-Signed (Development)
```python
settings = {
    'ssl': {'type': 'self-signed'},
    'hostname': 'example.com'  # Optional
}
```
- Generated automatically
- 2048-bit RSA encryption
- Valid for 365 days
- ⚠️ Browser warnings expected

#### Existing Certificates (Production)
```python
settings = {
    'ssl': {
        'type': 'existing',
        'cert_path': '/path/to/cert.crt',
        'key_path': '/path/to/key.key'
    }
}
```
- Use CA-signed certificates
- No browser warnings
- Recommended for production

### API Keys

Format: `gai_<32-byte-urlsafe-token>`

**Generation:**
```python
from installer.core import APIKeyManager

api_mgr = APIKeyManager()
api_key = api_mgr.generate_key(name='production')
print(f"API Key: {api_key}")
```

**Usage:**
```bash
# HTTP Header
curl -H "X-API-Key: gai_..." https://api.example.com

# Query Parameter
curl https://api.example.com?api_key=gai_...
```

**Security:**
- Keys stored as SHA-256 hashes
- Displayed only once during generation
- Rotate regularly for security

---

## Security Best Practices

### 1. Network Exposure
- ✅ Use SSL/TLS for all network-accessible deployments
- ✅ Configure firewall to limit access
- ✅ Use strong admin passwords
- ❌ Never expose server without SSL to internet

### 2. SSL/TLS
- ✅ Use CA-signed certificates for production
- ✅ Renew certificates before expiration
- ✅ Use 2048-bit or stronger RSA keys
- ❌ Don't use self-signed certs in production

### 3. Authentication
- ✅ Enable API key authentication
- ✅ Rotate API keys regularly
- ✅ Use strong password policies
- ❌ Never commit credentials to version control

### 4. Firewall
- ✅ Apply rules manually (review first)
- ✅ Limit access to specific IP ranges
- ✅ Close unused ports
- ❌ Don't auto-apply firewall rules

---

## Troubleshooting

### Port Already in Use
```
Error: Port 8000 is already in use
```

**Solution:**
1. Find process using port: `netstat -ano | findstr :8000` (Windows)
2. Stop the process or choose different port
3. Use port conflict detection:
   ```python
   from installer.core import detect_network_conflicts
   conflicts = detect_network_conflicts()
   ```

### SSL Certificate Generation Failed
```
Error: cryptography library not installed
```

**Solution:**
```bash
pip install cryptography>=41.0.0
```

### Firewall Script Permission Denied
```
Error: Access denied
```

**Solution:**
- Windows: Run PowerShell as Administrator
- Linux/macOS: Use `sudo bash script.sh`

### API Key Not Working
```
Error: Invalid API key
```

**Solution:**
1. Verify key format: `gai_...`
2. Check if key is active: `api_mgr.list_keys()`
3. Ensure key not revoked
4. Regenerate if needed: `api_mgr.generate_key()`

---

## Module Reference

### NetworkManager
```python
from installer.core import NetworkManager

network = NetworkManager(settings)
result = network.configure()

# Check port availability
is_available = network._is_port_available(8000)

# Generate SSL certificate
ssl_result = network.generate_self_signed_cert()

# Get network info
info = network.get_network_info()
```

### FirewallManager
```python
from installer.core import FirewallManager

firewall = FirewallManager(settings)
result = firewall.generate_firewall_rules()

# Print instructions
print(firewall.print_firewall_instructions())
```

### SecurityManager
```python
from installer.core import SecurityManager

security = SecurityManager(settings)
result = security.configure()

# Verify password
is_valid = security.verify_password(password, hash)
```

### APIKeyManager
```python
from installer.core import APIKeyManager

api_mgr = APIKeyManager()

# Generate key
api_key = api_mgr.generate_key(name='production')

# Validate key
is_valid = api_mgr.validate_key(api_key)

# List all keys
keys = api_mgr.list_keys()

# Revoke key
api_mgr.revoke_key(api_key)
```

---

## Configuration Reference

### config.yaml (Server Mode)
```yaml
installation:
  version: 2.0.0
  mode: server

network:
  bind: 0.0.0.0
  ssl_enabled: true

ssl:
  cert_path: ./certs/server.crt
  key_path: ./certs/server.key
  self_signed: true

security:
  admin_user: admin
  api_key_required: true
  rate_limiting:
    enabled: true
    requests_per_minute: 60

services:
  bind: 0.0.0.0
  api_port: 8000
  websocket_port: 8001
  dashboard_port: 3000
```

### .env (Server Mode)
```bash
# Service Binding
SERVICE_BIND=0.0.0.0

# SSL Configuration
SSL_CERT_PATH=./certs/server.crt
SSL_KEY_PATH=./certs/server.key

# Admin Settings
ADMIN_USER=admin
ADMIN_EMAIL=admin@localhost

# Security
ENABLE_SSL=true
ENABLE_API_KEYS=true
```

---

## Testing

### Run Examples
```bash
# All examples
python installer/examples/server_mode_example.py --example all

# Specific example
python installer/examples/server_mode_example.py --example ssl
python installer/examples/server_mode_example.py --example api-key
python installer/examples/server_mode_example.py --example firewall
```

### Syntax Validation
```bash
python -m py_compile installer/core/network.py
python -m py_compile installer/core/firewall.py
python -m py_compile installer/core/security.py
```

### Integration Test
```python
from installer.core import ServerInstaller

settings = {
    'mode': 'server',
    'bind': '0.0.0.0',
    'features': {'ssl': True},
    'ssl': {'type': 'self-signed'},
    'server': {'admin_user': 'admin', 'admin_password': 'test123'}
}

installer = ServerInstaller(settings)
result = installer.install()

assert result['success'] == True
assert 'api_key' in result
assert 'firewall_files' in result
```

---

## File Locations

All paths are absolute from project root:

### Core Modules
- `C:\Projects\GiljoAI_MCP\installer\core\network.py`
- `C:\Projects\GiljoAI_MCP\installer\core\firewall.py`
- `C:\Projects\GiljoAI_MCP\installer\core\security.py`

### Generated Files
- `C:\Projects\GiljoAI_MCP\certs\server.crt`
- `C:\Projects\GiljoAI_MCP\certs\server.key`
- `C:\Projects\GiljoAI_MCP\firewall_rules.txt`
- `C:\Projects\GiljoAI_MCP\installer\credentials\api_keys.yaml`
- `C:\Projects\GiljoAI_MCP\installer\credentials\users.yaml`

### Scripts
- `C:\Projects\GiljoAI_MCP\installer\scripts\firewall\*`

### Documentation
- `C:\Projects\GiljoAI_MCP\PHASE2_SUMMARY.md`
- `C:\Projects\GiljoAI_MCP\installer\PHASE2_NETWORK_DELIVERY.md`
- `C:\Projects\GiljoAI_MCP\installer\PHASE2_ARCHITECTURE.md`

---

## Dependencies

### Required
```
cryptography>=41.0.0    # SSL certificate generation
pyyaml>=6.0.0          # Configuration files
```

### Standard Library
```
socket      # Port checking
secrets     # Secure random generation
hashlib     # Password/key hashing
platform    # OS detection
pathlib     # File operations
```

---

## Support

### For Developers
- Module documentation: See inline docstrings
- Architecture diagrams: [PHASE2_ARCHITECTURE.md](PHASE2_ARCHITECTURE.md)
- Code examples: [examples/server_mode_example.py](examples/server_mode_example.py)

### For Users
- Quick start: This README
- Detailed guide: [PHASE2_NETWORK_DELIVERY.md](PHASE2_NETWORK_DELIVERY.md)
- Firewall setup: `installer/scripts/firewall/README.md`

### For System Administrators
- Security policies: [PHASE2_NETWORK_DELIVERY.md](PHASE2_NETWORK_DELIVERY.md#security-principles-implemented)
- Network topology: [PHASE2_ARCHITECTURE.md](PHASE2_ARCHITECTURE.md#network-security-zones)
- Firewall configuration: `installer/scripts/firewall/README.md`

---

## What's Next

### Phase 3: Advanced Features
- Connection pooling and load balancing
- Advanced monitoring and metrics
- Multi-user session management
- Certificate auto-renewal
- OAuth2/OIDC integration

### Contributing
Phase 2 is complete and ready for integration testing. Report issues or suggestions to the project maintainers.

---

**Phase 2 Network Engineering - Ready for Production**

Last Updated: 2025-10-02
Version: 2.0.0
Status: ✅ Complete
