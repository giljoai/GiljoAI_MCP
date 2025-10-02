# Phase 2: Network Engineering Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GiljoAI MCP Server Mode                      │
│                     Network Architecture                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Installation Flow                           │
└─────────────────────────────────────────────────────────────────┘

    User CLI Input
         │
         ▼
    ┌─────────────────┐
    │ ServerInstaller │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────┐
    │  mode_specific_setup() - Server Mode        │
    └─────────────────────────────────────────────┘
             │
             ├──────────┐
             │          │
             ▼          ▼
    ┌────────────┐  ┌─────────────┐
    │  Network   │  │  Security   │
    │  Manager   │  │  Manager    │
    └─────┬──────┘  └──────┬──────┘
          │                │
          │                ├── API Key Generation (gai_<token>)
          │                ├── Admin User Creation (PBKDF2)
          │                └── Auth Config (JWT/Session)
          │
          ├── SSL/TLS Setup (cryptography)
          ├── Port Conflict Check (socket)
          └── Network Binding Validation
             │
             ▼
    ┌─────────────────┐
    │     Firewall    │
    │     Manager     │
    └────────┬────────┘
             │
             ├── Windows (PowerShell/netsh)
             ├── Linux (UFW/iptables)
             └── macOS (pfctl)
             │
             ▼
    ┌─────────────────────────────────┐
    │  Generated Configuration Files   │
    └─────────────────────────────────┘
             │
             ├── config.yaml (network settings)
             ├── .env (environment variables)
             ├── firewall_rules.txt
             ├── certs/server.{crt,key}
             ├── installer/credentials/*.yaml
             └── installer/scripts/firewall/*.{ps1,sh}
```

---

## Module Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                     Module Dependency Graph                      │
└─────────────────────────────────────────────────────────────────┘

installer.core.installer (ServerInstaller)
    │
    ├─── installer.core.network (NetworkManager)
    │    │
    │    ├─── cryptography (SSL generation)
    │    ├─── socket (port checking)
    │    └─── platform (OS detection)
    │
    ├─── installer.core.firewall (FirewallManager)
    │    │
    │    ├─── platform (OS-specific scripts)
    │    └─── pathlib (file generation)
    │
    └─── installer.core.security (SecurityManager)
         │
         ├─── secrets (token generation)
         ├─── hashlib (password/key hashing)
         └─── yaml (credential storage)

External Dependencies:
    ├─── cryptography>=41.0.0 (NEW - SSL certificates)
    ├─── pyyaml>=6.0.0 (existing)
    └─── Standard library: socket, secrets, hashlib, platform
```

---

## Network Security Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Network Security Flow                         │
└─────────────────────────────────────────────────────────────────┘

1. NETWORK BINDING
   ├─ localhost (127.0.0.1) → ✅ Safe, no warnings
   └─ 0.0.0.0 (all interfaces)
      │
      ├─ SSL Enabled → ⚠️  Warning + Proceed
      │   └─ Generate/Load Certificates
      │
      └─ SSL Disabled → 🚨 CRITICAL WARNING
          └─ Require Explicit User Consent
              │
              ├─ User Confirms → Continue with warnings
              └─ User Declines → Abort installation

2. PORT CONFIGURATION
   ├─ Check Port Availability (API, WS, Dashboard)
   │   ├─ All Available → ✅ Proceed
   │   └─ Conflicts Detected → ❌ Show alternatives, abort
   │
   └─ Detect Common Conflicts
       ├─ Port 8000: Django, Alternative HTTP
       ├─ Port 3000: React, Node.js
       └─ Port 5432: PostgreSQL

3. FIREWALL RULES
   ├─ Generate Platform-Specific Scripts
   │   ├─ Windows: PowerShell + Batch
   │   ├─ Linux: UFW + iptables
   │   └─ macOS: pfctl
   │
   └─ 🔒 NO AUTO-APPLY (Security Policy)
       └─ User Must Manually Execute

4. SSL/TLS SETUP
   ├─ Self-Signed Certificate
   │   ├─ Generate 2048-bit RSA key
   │   ├─ Create X.509 certificate
   │   ├─ Valid for 365 days
   │   └─ Store in certs/
   │
   └─ Existing Certificate
       ├─ Validate paths exist
       ├─ Verify file permissions
       └─ Link in config.yaml
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Security Component Stack                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┐
│         API Key Layer            │
│  ┌────────────────────────────┐  │
│  │ gai_<32-byte-urlsafe-token>│  │
│  └────────────────────────────┘  │
│           │                       │
│           ▼                       │
│     SHA-256 Hashing               │
│           │                       │
│           ▼                       │
│  Store in api_keys.yaml           │
│  (hash only, not plaintext)       │
└──────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│      Password Security Layer     │
│  ┌────────────────────────────┐  │
│  │   User Password (input)    │  │
│  └────────────────────────────┘  │
│           │                       │
│           ▼                       │
│  PBKDF2-SHA256 (100k iterations)  │
│           │                       │
│           ▼                       │
│  32-byte random salt + hash       │
│           │                       │
│           ▼                       │
│  Store in users.yaml              │
│  (base64 encoded)                 │
└──────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│      File Security Layer         │
│                                   │
│  Unix Permissions:                │
│  ├─ Credentials:  0600 (owner)   │
│  ├─ Certificates: 0644 (public)  │
│  └─ Keys:         0600 (owner)   │
│                                   │
│  .gitignore:                      │
│  ├─ credentials/*                 │
│  ├─ *.key                         │
│  └─ api_key_secret.txt            │
└──────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              Server Mode Installation Data Flow                  │
└─────────────────────────────────────────────────────────────────┘

User Input
    │
    ├── mode: 'server'
    ├── bind: '0.0.0.0'
    ├── features: {ssl: true, api_keys: true}
    └── admin credentials
    │
    ▼
ServerInstaller.install()
    │
    ├─── Step 1: Database Setup (Phase 1)
    │    └── Creates PostgreSQL database
    │
    ├─── Step 2: Network Configuration (Phase 2)
    │    │
    │    ├── NetworkManager.configure()
    │    │   ├── Validate binding
    │    │   ├── Check ports
    │    │   └── Setup SSL
    │    │       └── generates: certs/server.{crt,key}
    │    │
    │    └── outputs: {
    │         ssl_cert: path,
    │         ssl_key: path,
    │         warnings: [...]
    │        }
    │
    ├─── Step 3: Security Configuration (Phase 2)
    │    │
    │    ├── SecurityManager.configure()
    │    │   ├── Generate API key
    │    │   │   └── gai_<token>
    │    │   │       └── hash with SHA-256
    │    │   │           └── store in api_keys.yaml
    │    │   │
    │    │   └── Create admin user
    │    │       └── hash password (PBKDF2)
    │    │           └── store in users.yaml
    │    │
    │    └── outputs: {
    │         api_key: plaintext (display once),
    │         api_key_file: path,
    │         admin_user: username
    │        }
    │
    ├─── Step 4: Firewall Rules (Phase 2)
    │    │
    │    ├── FirewallManager.generate_firewall_rules()
    │    │   ├── Detect platform
    │    │   └── Generate scripts
    │    │       ├── Windows: .ps1, .bat
    │    │       ├── Linux: .sh (ufw, iptables)
    │    │       └── macOS: .sh (pfctl)
    │    │
    │    └── outputs: {
    │         files: [script paths],
    │         instructions: text
    │        }
    │
    ├─── Step 5: Config Generation
    │    │
    │    ├── ConfigManager.generate_all()
    │    │   ├── .env
    │    │   │   ├── SERVICE_BIND=0.0.0.0
    │    │   │   ├── SSL_CERT_PATH=...
    │    │   │   └── SSL_KEY_PATH=...
    │    │   │
    │    │   └── config.yaml
    │    │       ├── network: {bind, ssl_enabled}
    │    │       ├── ssl: {cert_path, key_path}
    │    │       └── security: {admin_user, api_key_required}
    │    │
    │    └── outputs: config files
    │
    └─── Step 6: Launcher Creation
         └── Platform-specific start scripts

Installation Complete
    │
    ├── Display network warnings
    ├── Display firewall instructions
    ├── Show API key (once)
    └── Return result
```

---

## File System Layout

```
C:\Projects\GiljoAI_MCP\
│
├── certs/                          # 🔒 SSL Certificates
│   ├── .gitkeep
│   ├── server.crt                  # (generated)
│   └── server.key                  # (generated, 0600)
│
├── installer/
│   ├── core/                       # Core modules
│   │   ├── __init__.py            # Module exports
│   │   ├── installer.py           # Base + Server installer
│   │   ├── network.py             # 🆕 Network configuration
│   │   ├── firewall.py            # 🆕 Firewall management
│   │   ├── security.py            # 🆕 Security & auth
│   │   ├── database.py            # Database setup
│   │   └── config.py              # Config generation
│   │
│   ├── credentials/                # 🔒 Secure credentials (runtime)
│   │   ├── .gitignore             # Exclude all
│   │   ├── api_keys.yaml          # API key hashes
│   │   ├── users.yaml             # User credentials
│   │   └── api_key_secret.txt     # Plaintext (delete!)
│   │
│   ├── scripts/
│   │   └── firewall/               # 🆕 Firewall scripts (runtime)
│   │       ├── README.md           # Detailed instructions
│   │       ├── configure_windows_firewall.ps1
│   │       ├── configure_windows_firewall.bat
│   │       ├── configure_ufw_firewall.sh
│   │       ├── configure_iptables_firewall.sh
│   │       └── configure_macos_firewall.sh
│   │
│   ├── examples/                   # 🆕 Usage examples
│   │   └── server_mode_example.py
│   │
│   ├── PHASE2_NETWORK_DELIVERY.md  # 🆕 Full documentation
│   └── PHASE2_ARCHITECTURE.md      # 🆕 This file
│
├── config.yaml                     # Main configuration
├── .env                            # Environment variables
├── firewall_rules.txt              # 🆕 Quick reference (runtime)
└── PHASE2_SUMMARY.md               # 🆕 Quick summary

Legend:
  🆕 New in Phase 2
  🔒 Secure/restricted access
  (runtime) Generated during installation
```

---

## API Key Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Key Lifecycle                             │
└─────────────────────────────────────────────────────────────────┘

1. GENERATION
   ├── secrets.token_urlsafe(32)
   │   └── 32 bytes = 256 bits of entropy
   │       └── URL-safe base64 encoding
   │           └── ~43 characters
   │
   └── Prefix with "gai_"
       └── Result: gai_<43-char-token>

2. STORAGE
   ├── Hash with SHA-256
   │   └── 64-character hex digest
   │
   ├── Store in api_keys.yaml
   │   └── {
   │        id: 'default',
   │        name: 'Default API Key',
   │        key_hash: '<sha256-hex>',
   │        permissions: ['read', 'write', 'admin'],
   │        enabled: true,
   │        created: '2025-10-02T...'
   │      }
   │
   └── Save plaintext to api_key_secret.txt
       └── ⚠️  DELETE AFTER COPYING!

3. DISPLAY
   └── Show to user ONCE during installation
       └── User must save securely
           └── Never shown again

4. VALIDATION (Runtime)
   ├── Receive API key from request
   ├── Hash with SHA-256
   ├── Compare with stored hash
   │   └── secrets.compare_digest() (constant time)
   └── Grant/Deny access

5. ROTATION
   ├── Generate new key
   ├── Mark old key as revoked
   │   └── {enabled: false, revoked: '2025-10-03T...'}
   └── Display new key to user

6. REVOCATION
   └── Set enabled: false
       └── Key becomes invalid immediately
```

---

## Network Security Zones

```
┌─────────────────────────────────────────────────────────────────┐
│                    Network Security Zones                        │
└─────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                   ZONE 1: Localhost                    │
│                (Default - Most Secure)                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Binding: 127.0.0.1                              │  │
│  │  Access: Local machine only                      │  │
│  │  SSL: Optional (localhost trust)                 │  │
│  │  Firewall: Not required                          │  │
│  │  Security: Minimal (trusted environment)         │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│               ZONE 2: LAN (Private Network)            │
│              (Server Mode - Medium Security)           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Binding: 0.0.0.0 (filtered by firewall)        │  │
│  │  Access: Local network (192.168.x.x, 10.x.x.x)  │  │
│  │  SSL: Strongly recommended                       │  │
│  │  Firewall: Required (LAN subnet only)           │  │
│  │  Security: Moderate (API keys, passwords)       │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│              ZONE 3: Internet (Public Access)          │
│                 (Server Mode - High Security)          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Binding: 0.0.0.0 (exposed to internet)         │  │
│  │  Access: Worldwide                               │  │
│  │  SSL: MANDATORY (CA-signed certificates)         │  │
│  │  Firewall: Required + Rate limiting              │  │
│  │  Security: Maximum (all features enabled)        │  │
│  │           - API keys required                    │  │
│  │           - Strong passwords                     │  │
│  │           - IP whitelisting                      │  │
│  │           - Reverse proxy (nginx/Apache)         │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘

Security Escalation:
  Localhost → LAN → Internet
     ↓         ↓       ↓
  Optional → Recommended → Mandatory (SSL)
  None → Basic → Advanced (Authentication)
  Trust → Verify → Zero Trust (Architecture)
```

---

## Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│              Phase 1 ↔ Phase 2 Integration                       │
└─────────────────────────────────────────────────────────────────┘

Phase 1 (Localhost)          Phase 2 (Server Mode)
─────────────────────────────────────────────────────────────────

BaseInstaller                ServerInstaller (extends Base)
    │                            │
    ├── install()                ├── install() (inherited)
    │   ├── Database setup       │   ├── Database setup ✓
    │   ├── Config generation    │   ├── Network config 🆕
    │   ├── Launchers            │   ├── Security setup 🆕
    │   └── Validation           │   ├── Firewall rules 🆕
    │                            │   ├── Config generation ✓
    └── mode_specific_setup()    │   └── Validation ✓
        (no-op for localhost)    │
                                 └── mode_specific_setup()
                                     ├── NetworkManager
                                     ├── SecurityManager
                                     └── FirewallManager

DatabaseInstaller            DatabaseNetworkConfig
    │                            │
    ├── setup()                  ├── configure_for_server()
    ├── create_database()        │   ├── Update postgresql.conf
    └── create_users()           │   │   └── listen_addresses
                                 │   └── Update pg_hba.conf
                                 │       └── Allow LAN/WAN
                                 └── (extends Database setup)

ConfigManager                ConfigManager (enhanced)
    │                            │
    ├── generate_env()           ├── generate_env()
    │   └── localhost vars       │   ├── localhost vars ✓
    │                            │   └── server vars 🆕
    │                            │       ├── SERVICE_BIND
    └── generate_config_yaml()   │       ├── SSL_CERT_PATH
        └── localhost config     │       └── SSL_KEY_PATH
                                 │
                                 └── generate_config_yaml()
                                     ├── localhost config ✓
                                     └── server config 🆕
                                         ├── network section
                                         ├── ssl section
                                         └── security section
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Strategy                       │
└─────────────────────────────────────────────────────────────────┘

NetworkManager.configure()
    │
    ├── Port already in use
    │   └── Return: {success: false, errors: ['Port X in use']}
    │       └── ServerInstaller: Abort installation
    │           └── Display error to user
    │
    ├── SSL certificate generation fails
    │   └── Return: {success: false, errors: ['cryptography not installed']}
    │       └── ServerInstaller: Continue without SSL (if user confirms)
    │           └── Display WARNING
    │
    └── Network binding invalid
        └── Return: {success: false, errors: ['Invalid bind address']}
            └── ServerInstaller: Abort installation

SecurityManager.configure()
    │
    ├── Admin password missing
    │   └── Return: {success: false, errors: ['Password required']}
    │       └── ServerInstaller: Abort installation
    │
    └── API key storage fails
        └── Log error, continue with warning
            └── User can generate key later

FirewallManager.generate_firewall_rules()
    │
    ├── Unsupported platform
    │   └── Return: {success: false, errors: ['Platform not supported']}
    │       └── ServerInstaller: Log warning, continue
    │           └── User must configure firewall manually
    │
    └── Script directory creation fails
        └── Return: {success: false, errors: ['Permission denied']}
            └── ServerInstaller: Continue with warning
                └── Scripts can be generated later

General Error Strategy:
1. Critical errors (database, ports) → Abort installation
2. Security warnings (SSL disabled) → Warn user, require confirmation
3. Optional features (firewall scripts) → Warn, continue
4. All errors logged to: install_logs/install_server_YYYYMMDD_HHMMSS.log
```

---

## Future Enhancements (Phase 3+)

```
┌─────────────────────────────────────────────────────────────────┐
│                  Phase 3: Advanced Features                      │
└─────────────────────────────────────────────────────────────────┘

Network Enhancements:
├── IPv6 support
├── Advanced network topology detection
├── Automatic port conflict resolution
├── Dynamic port allocation
└── Network interface selection (multi-NIC)

Security Enhancements:
├── Certificate auto-renewal (Let's Encrypt)
├── Multi-factor authentication (MFA)
├── OAuth2/OIDC integration
├── API key expiration and auto-rotation
├── Advanced rate limiting (per-key, per-IP)
└── Security audit logging

Firewall Enhancements:
├── Automatic firewall detection and configuration
├── Cloud provider security groups (AWS, Azure, GCP)
├── Container network policies (Docker, Kubernetes)
├── Advanced IP filtering (geolocation, blacklists)
└── DDoS protection integration

Monitoring:
├── Real-time network metrics
├── SSL certificate expiration alerts
├── Failed authentication tracking
├── Port scanning detection
└── Traffic analysis and visualization
```

---

**Phase 2 Network Engineering Architecture - Complete**
