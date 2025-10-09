# GiljoAI MCP - Network Topology and Deployment Guide

**Version:** 2.0
**Date:** 2025-10-08
**Purpose:** Eliminate confusion between deployment modes and database topology

---

## Critical Distinction

**The most important concept to understand about GiljoAI MCP deployment:**

### Deployment Mode ≠ Database Topology

These are **TWO SEPARATE** architectural concerns:

1. **Deployment Mode** - Controls how users access the API server
2. **Database Topology** - Controls where PostgreSQL runs (always localhost)

**NEVER confuse these two concepts.** Mixing them leads to security vulnerabilities and configuration errors.

---

## 1. Deployment Mode (User Access Layer)

Deployment mode determines **where the API server binds** and **who can connect to it**.

### Localhost Mode

**Purpose:** Single developer on one machine

```yaml
installation:
  mode: localhost

services:
  api:
    host: 127.0.0.1  # API binds to localhost only
    port: 7272

database:
  host: localhost    # Database is ALWAYS localhost
  port: 5432
```

**Characteristics:**
- API accessible only from: `http://127.0.0.1:7272`
- No authentication required
- Single-machine development
- Database on localhost (standard)

**Access Pattern:**
```
Developer's Machine:
  ├── Browser/CLI → http://127.0.0.1:7272 → API Server
  └── API Server → localhost:5432 → PostgreSQL
```

---

### LAN Mode

**Purpose:** Team collaboration on local network

```yaml
installation:
  mode: lan

services:
  api:
    host: 10.1.0.164  # API binds to network adapter IP
    port: 7272

database:
  host: localhost     # Database STILL localhost (never changes!)
  port: 5432

security:
  api_keys:
    require_for_modes: ["server", "lan", "wan"]
  cors:
    allowed_origins:
      - http://10.1.0.164:7274  # Specific IPs only
```

**Characteristics:**
- API accessible from: `http://10.1.0.164:7272` (LAN devices)
- API key authentication required
- Team access on local network
- Database REMAINS on localhost (security)

**Access Pattern:**
```
Server Machine (10.1.0.164):
  ├── API Server (binds to 10.1.0.164:7272)
  └── PostgreSQL (binds to 127.0.0.1:5432)

Client Machine 1 (10.1.0.50):
  └── Browser → http://10.1.0.164:7272 → API Server

Client Machine 2 (10.1.0.51):
  └── CLI → http://10.1.0.164:7272 → API Server

Database Connection (server internal only):
  API Server → localhost:5432 → PostgreSQL
```

**Key Point:** Database is NOT accessible from network (10.1.0.50, 10.1.0.51 cannot connect to database directly).

---

### WAN Mode

**Purpose:** Internet-facing deployment

```yaml
installation:
  mode: wan

services:
  api:
    host: <public_ip>  # API binds to public IP or domain
    port: 443

database:
  host: localhost      # Database STILL localhost (critical security!)
  port: 5432

security:
  api_keys:
    require_for_modes: ["server", "lan", "wan"]
  ssl:
    enabled: true      # TLS/SSL mandatory
    cert_path: /path/to/cert.pem
```

**Characteristics:**
- API accessible from: `https://example.com` (internet)
- OAuth + API key + TLS required
- Public internet access
- Database REMAINS on localhost (secured)

**Access Pattern:**
```
Server (public IP: 203.0.113.45):
  ├── API Server (binds to 203.0.113.45:443, TLS enabled)
  └── PostgreSQL (binds to 127.0.0.1:5432, NOT exposed)

Internet Client 1 (anywhere):
  └── Browser → https://example.com → API Server

Internet Client 2 (anywhere):
  └── CLI → https://example.com → API Server

Database Connection (server internal only):
  API Server → localhost:5432 → PostgreSQL
```

**Security:** Database is NEVER exposed to internet, even though API is public.

---

## 2. Database Topology (Always Localhost)

### The Invariant Principle

**No matter what deployment mode you choose, the database configuration NEVER changes:**

```yaml
database:
  host: localhost  # ALWAYS localhost
  port: 5432       # Standard PostgreSQL port
  name: giljo_mcp
  user: giljo_user
```

### Why Database is Always Localhost

1. **Security:** Database is not exposed to network attacks
2. **Performance:** Localhost connections are faster (Unix sockets)
3. **Simplicity:** No need for network-level database authentication
4. **Architecture:** Backend and database are co-located

### PostgreSQL Configuration

PostgreSQL `postgresql.conf` should have:

```conf
# For all deployment modes (localhost, lan, wan):
listen_addresses = '127.0.0.1'  # ONLY localhost (NOT '*' or '0.0.0.0')
port = 5432
```

PostgreSQL `pg_hba.conf` should have:

```conf
# Local connections only (all modes)
local   all   all   scram-sha-256
host    all   all   127.0.0.1/32   scram-sha-256
host    all   all   ::1/128        scram-sha-256

# NO network connections (even in LAN/WAN mode)
# Do NOT add entries like: host all all 0.0.0.0/0 scram-sha-256
```

---

## 3. Network Architecture Diagrams

### Localhost Mode Architecture

```
┌─────────────────────────────────────────────┐
│  Developer's Machine (127.0.0.1)            │
│                                              │
│  User (Browser/CLI)                          │
│       ↓                                      │
│  http://127.0.0.1:7272                       │
│       ↓                                      │
│  ┌──────────────────┐                        │
│  │  API Server      │                        │
│  │  Bind: 127.0.0.1 │                        │
│  │  Port: 7272      │                        │
│  └────────┬─────────┘                        │
│           │                                  │
│           │ localhost socket                 │
│           ↓                                  │
│  ┌──────────────────┐                        │
│  │  PostgreSQL      │                        │
│  │  Bind: 127.0.0.1 │                        │
│  │  Port: 5432      │                        │
│  └──────────────────┘                        │
│                                              │
└─────────────────────────────────────────────┘
```

---

### LAN Mode Architecture

```
┌───────────────────────────────────────────────────────┐
│  LAN Network (192.168.1.0/24 or 10.1.0.0/24)          │
├───────────────────────────────────────────────────────┤
│                                                        │
│  Client Machine 1 (10.1.0.50)                         │
│       │                                               │
│       │ http://10.1.0.164:7272 (with API key)        │
│       ↓                                               │
│  ┌────────────────────────────────────────────┐       │
│  │  Server Machine (10.1.0.164)               │       │
│  │                                             │       │
│  │  ┌──────────────────┐                       │       │
│  │  │  API Server      │ ← Client Machine 2   │       │
│  │  │  Bind: 10.1.0.164│   (10.1.0.51)        │       │
│  │  │  Port: 7272      │                       │       │
│  │  └────────┬─────────┘                       │       │
│  │           │                                 │       │
│  │           │ localhost socket ONLY           │       │
│  │           │ (NOT network connection)        │       │
│  │           ↓                                 │       │
│  │  ┌──────────────────┐                       │       │
│  │  │  PostgreSQL      │ ← Network clients     │       │
│  │  │  Bind: 127.0.0.1 │   CANNOT access       │       │
│  │  │  Port: 5432      │   (security)          │       │
│  │  └──────────────────┘                       │       │
│  │                                             │       │
│  └─────────────────────────────────────────────┘       │
│                                                        │
└───────────────────────────────────────────────────────┘
```

**Key Points:**
- API server listens on LAN IP (10.1.0.164)
- Database listens ONLY on localhost (127.0.0.1)
- Network clients can reach API, but NOT database

---

### WAN Mode Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Internet                                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Internet Client 1                                       │
│       │                                                 │
│       │ https://example.com (with OAuth + API key)     │
│       ↓                                                 │
│  ┌────────────────────────────────────────────┐         │
│  │  Server (public IP: 203.0.113.45)          │         │
│  │                                             │         │
│  │  ┌──────────────────┐                       │         │
│  │  │  Nginx/Proxy     │ ← Internet Client 2  │         │
│  │  │  TLS termination │                       │         │
│  │  └────────┬─────────┘                       │         │
│  │           │                                 │         │
│  │           ↓                                 │         │
│  │  ┌──────────────────┐                       │         │
│  │  │  API Server      │                       │         │
│  │  │  Bind: public IP │                       │         │
│  │  │  Port: 8000      │                       │         │
│  │  └────────┬─────────┘                       │         │
│  │           │                                 │         │
│  │           │ localhost socket ONLY           │         │
│  │           │ (database NOT on internet)      │         │
│  │           ↓                                 │         │
│  │  ┌──────────────────┐                       │         │
│  │  │  PostgreSQL      │ ← Internet clients    │         │
│  │  │  Bind: 127.0.0.1 │   CANNOT access       │         │
│  │  │  Port: 5432      │   (critical security) │         │
│  │  └──────────────────┘                       │         │
│  │                                             │         │
│  └─────────────────────────────────────────────┘         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Security Layers:**
- TLS/SSL encryption for all traffic
- OAuth + API key authentication
- Database isolated on localhost
- Rate limiting and DDoS protection

---

## 4. Common Misconfigurations (AVOID)

### WRONG: Database on Network

```yaml
# ❌ NEVER DO THIS - Major security vulnerability
database:
  host: 0.0.0.0      # Exposes database to network
  host: 10.1.0.164   # Makes database network-accessible
```

**Why wrong:** Anyone on the network can attempt to connect to your database.

### WRONG: API with 0.0.0.0 in LAN Mode

```yaml
# ❌ AVOID - Less secure than specific adapter IP
services:
  api:
    host: 0.0.0.0    # Binds to ALL network interfaces
```

**Why wrong:** Binds to all interfaces, including unintended ones. Use specific adapter IP instead.

### WRONG: Localhost Database Config Different Per Mode

```yaml
# ❌ WRONG - Database config should NEVER vary by mode
# Localhost mode
database:
  host: localhost

# LAN mode (WRONG!)
database:
  host: 10.1.0.164   # NEVER put database on network
```

**Why wrong:** Database should always be localhost for security.

---

## 5. Correct Configurations

### Localhost Mode (CORRECT)

```yaml
installation:
  mode: localhost

services:
  api:
    host: 127.0.0.1  # ✅ API on localhost

database:
  host: localhost    # ✅ Database on localhost
  port: 5432
```

### LAN Mode (CORRECT)

```yaml
installation:
  mode: lan

services:
  api:
    host: 10.1.0.164  # ✅ API on network adapter IP (specific, not 0.0.0.0)

database:
  host: localhost     # ✅ Database STILL on localhost
  port: 5432

security:
  api_keys:
    require_for_modes: ["server", "lan", "wan"]
```

### WAN Mode (CORRECT)

```yaml
installation:
  mode: wan

services:
  api:
    host: <public_ip>  # ✅ API on public IP

database:
  host: localhost      # ✅ Database STILL on localhost (secured)
  port: 5432

security:
  api_keys:
    require_for_modes: ["server", "lan", "wan"]
  ssl:
    enabled: true
```

---

## 6. Verification Commands

### Check API Server Binding

**Windows:**
```powershell
netstat -an | findstr 7272
```

**Linux/macOS:**
```bash
netstat -an | grep 7272
# or
ss -tulpn | grep 7272
```

**Expected Results:**
- **Localhost mode:** `127.0.0.1:7272` or `localhost:7272`
- **LAN mode:** `10.1.0.164:7272` (your adapter IP)
- **WAN mode:** `<public_ip>:443`

### Check PostgreSQL Binding

**Windows:**
```powershell
netstat -an | findstr 5432
```

**Linux/macOS:**
```bash
netstat -an | grep 5432
# or
ss -tulpn | grep 5432
```

**Expected Result (ALL modes):**
- `127.0.0.1:5432` or `localhost:5432`
- **NEVER:** `0.0.0.0:5432` or `*:5432` or `10.1.0.164:5432`

### Test Connectivity

**Localhost Mode:**
```bash
# Should work
curl http://127.0.0.1:7272/health

# Should fail (not bound to network)
curl http://10.1.0.164:7272/health
```

**LAN Mode:**
```bash
# Both should work (from server)
curl http://127.0.0.1:7272/health
curl http://10.1.0.164:7272/health

# Should work from LAN client
curl -H "X-API-Key: gk_your_key" http://10.1.0.164:7272/health

# Database should NEVER be accessible from network
psql -h 10.1.0.164 -U giljo_user -d giljo_mcp  # Should fail
psql -h localhost -U giljo_user -d giljo_mcp   # Should work (on server only)
```

---

## 7. Migration Checklist

If you need to change deployment modes:

### Localhost → LAN

1. **Update config.yaml:**
   ```yaml
   installation:
     mode: lan

   services:
     api:
       host: <your_lan_ip>  # e.g., 10.1.0.164

   # Database section UNCHANGED
   ```

2. **Generate API key:**
   ```bash
   python -c "import secrets; print(f'gk_{secrets.token_urlsafe(32)}')"
   ```

3. **Update CORS origins:**
   ```yaml
   security:
     cors:
       allowed_origins:
         - http://<your_lan_ip>:7274
   ```

4. **Configure firewall** (allow port 7272 on LAN)

5. **Restart services**

6. **Test from LAN client**

### LAN → WAN

1. **Setup domain/public IP**

2. **Obtain TLS/SSL certificates**

3. **Update config.yaml:**
   ```yaml
   installation:
     mode: wan

   services:
     api:
       host: <public_ip>

   security:
     ssl:
       enabled: true
       cert_path: /path/to/cert.pem

   # Database section STILL UNCHANGED
   ```

4. **Setup reverse proxy (nginx/caddy)**

5. **Configure firewall** (restrict access, rate limiting)

6. **Enable OAuth** (recommended)

7. **Test from internet**

---

## 8. Summary

### Golden Rules

1. **Database is ALWAYS on localhost** - No exceptions
2. **API binding varies by deployment mode** - This is correct
3. **Never expose database to network** - Security principle
4. **Use specific adapter IP in LAN mode** - Not 0.0.0.0
5. **TLS is mandatory for WAN mode** - Non-negotiable

### Quick Reference

| Component | Localhost Mode | LAN Mode | WAN Mode |
|-----------|---------------|----------|----------|
| **API Binding** | 127.0.0.1 | Network adapter IP | Public IP/Domain |
| **API Port** | 7272 | 7272 | 443 (HTTPS) |
| **Database Host** | localhost | localhost | localhost |
| **Database Binding** | 127.0.0.1 | 127.0.0.1 | 127.0.0.1 |
| **Authentication** | None | API Key | API Key + OAuth |
| **Encryption** | Optional | Optional | Mandatory (TLS) |
| **Network Access** | Same machine | LAN devices | Internet |

---

## Related Documentation

- **TECHNICAL_ARCHITECTURE.md** - System architecture with network topology section
- **CLAUDE.md** - Development guidelines with topology principles
- **LAN_DEPLOYMENT_GUIDE.md** - Detailed LAN setup instructions
- **WAN_DEPLOYMENT_GUIDE.md** - Internet-facing deployment guide

---

**Document Version:** 2.0
**Last Updated:** 2025-10-08
**Status:** Production Ready
**Next Review:** After first production LAN deployment
