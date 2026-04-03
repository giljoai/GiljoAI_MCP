# Demo Server Preparation - Security Recommendations

**Edition Scope:** CE
**Date:** 2026-03-26
**Status:** Recommendation

## Context

This Ubuntu PC will serve as a public-facing demo/trial server. Users will create accounts via the web frontend, which redirects them into a new demo session (expiring after ~5 days). All components (frontend, backend API, PostgreSQL) run on the same machine.

## Hardware Inventory

| Component | Details |
|-----------|---------|
| **Machine** | HP ZBook Fury 16 G9 Mobile Workstation |
| **CPU** | Intel i7-12800HX — 16 cores / 24 threads (Alder Lake) |
| **RAM** | 24 GB |
| **OS** | Ubuntu 24.04.4 LTS, kernel 6.17.0-19 |
| **Network** | 1 Gbps Ethernet (wired) |

### Storage — Two NVMe Drives

| | **Drive 0 (OS)** | **Drive 1 (Server)** |
|---|---|---|
| **Model** | KIOXIA KXG6AZNV512G | Toshiba KXG50ZNV512G |
| **Interface** | NVMe PCIe Gen3 x4 | NVMe PCIe Gen3 x4 |
| **Size** | 477 GB (422 GB free) | 477 GB (445 GB free) |
| **Mount** | `/` (LVM) | `/media/gildemo/Server` (ext4) |
| **Seq Write** | **2.2 GB/s** | **671 MB/s** |

The primary KIOXIA drive is **3.3x faster** than the secondary Toshiba. Both connect via PCIe Gen3 x4 (8 GT/s).

### Drive Layout Decision

**Keep OS, application, and PostgreSQL together on the primary drive.** Rationale:

- The secondary drive is significantly slower — moving PostgreSQL there would hurt query latency
- A demo server with a handful of concurrent users will not stress the primary drive
- The 1 Gbps network link (~125 MB/s) is the real throughput ceiling, not disk I/O
- Splitting across drives only helps when both drives are comparable speed and I/O contention is real

**Use the secondary drive for:**

| Purpose | Path |
|---|---|
| Automated DB backups | `/media/gildemo/Server/backups/` |
| Rotated app + PG logs | `/media/gildemo/Server/logs/` |
| User-uploaded content | `/media/gildemo/Server/uploads/` |
| Build artifacts / temp | `/media/gildemo/Server/scratch/` |

## Architecture

```
Internet --> Web Frontend (port 443) --> Backend API --> PostgreSQL (localhost:5432)
                                       all on this PC

Primary (KIOXIA - 2.2 GB/s):        Secondary (Toshiba - 671 MB/s):
  /                     OS + Ubuntu    /media/gildemo/Server/backups/  DB snapshots
  /var/lib/postgresql/  PostgreSQL     /media/gildemo/Server/logs/     Rotated logs
  /home/gildemo/Work/   Application    /media/gildemo/Server/uploads/  User content
```

## PostgreSQL Installation

- PostgreSQL 18.3 installed via official PGDG apt repository
- Default peer authentication retained for the `postgres` superuser

## Database User Security Assessment

The existing `install.py` and `installer/core/database.py` already implement a secure setup:

| Practice | Status |
|---|---|
| Dedicated roles (`giljo_owner`, `giljo_user`) | Done |
| 20-char random passwords via `secrets.choice()` | Done |
| Separate owner (DDL) vs app user (DML only) | Done |
| Least privilege (CONNECT + SELECT/INSERT/UPDATE/DELETE) | Done |
| Parameterized SQL (no injection risk) | Done |
| Default privileges for future tables | Done |
| Passwords stored in `.env`, not source code | Done |

## Recommendations for Demo Server Hardening

### 1. PostgreSQL Access

- **Keep peer auth** for `postgres` superuser (admin via `sudo -u postgres psql` only)
- **Password auth (scram-sha-256)** for `giljo_owner` and `giljo_user` over TCP localhost
- **`listen_addresses = 'localhost'`** in `postgresql.conf` (verify this is set)
- PostgreSQL port 5432 must NOT be exposed through the firewall

### 2. Firewall

Only expose web ports:

```bash
sudo ufw default deny incoming
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow ssh
sudo ufw enable
```

### 3. Credentials File

Verify `installer/credentials/db_credentials.txt` is:
- Listed in `.gitignore`
- Not accessible via the web server
- Readable only by the application user (`chmod 600`)

### 4. PostgreSQL Tuning for 24 GB RAM

```ini
# postgresql.conf adjustments
shared_buffers = 6GB
effective_cache_size = 18GB
work_mem = 64MB
maintenance_work_mem = 512MB
wal_buffers = 64MB
```

### 5. Secondary Drive Mount Options

Mount with `noatime` to reduce unnecessary write overhead for backup/log workloads:

```
# /etc/fstab entry for secondary drive
/dev/nvme1n1p1  /media/gildemo/Server  ext4  defaults,noatime  0  2
```

### 6. Automated Backups to Secondary Drive

Set up a cron job for regular `pg_dump` snapshots:

```bash
# /etc/cron.d/giljo-backup (runs daily at 03:00)
0 3 * * * postgres pg_dump -Fc giljo_db > /media/gildemo/Server/backups/giljo_db_$(date +\%Y\%m\%d).dump
# Prune backups older than 14 days
0 4 * * * root find /media/gildemo/Server/backups/ -name "*.dump" -mtime +14 -delete
```

### 7. Demo Session Expiry

- Session lifetime TBD (~5 days under consideration)
- Implement a scheduled cleanup job to purge expired demo data
- Consider rate-limiting account creation to prevent abuse

### 8. pg_hba.conf Configuration

```
# Admin: local sudo only
local   all             postgres                                peer

# App roles: password over TCP, localhost only
host    giljo_db        giljo_owner     127.0.0.1/32            scram-sha-256
host    giljo_db        giljo_user      127.0.0.1/32            scram-sha-256

# Reject everything else
host    all             all             0.0.0.0/0               reject
```

### 6. TLS via Cloudflare Tunnel (Recommended for Demo)

The server uses mkcert for local HTTPS, which installs a root CA only on the machine that ran `install.py`. Remote users would get untrusted-cert browser warnings, and "proceed anyway" only applies to the page — background API calls (e.g. to port 7272) still fail silently, causing the frontend to fall back to `/welcome` as if it were a fresh install.

**Solution:** Use a Cloudflare Tunnel to expose the server behind a real TLS certificate with zero friction for end users.

#### Setup

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate (one-time, opens browser)
cloudflared tunnel login

# Create a named tunnel
cloudflared tunnel create giljo-demo

# Configure tunnel (create ~/.cloudflared/config.yml)
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: giljo-demo
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  # Frontend (Vite)
  - hostname: demo.giljo.ai
    service: https://127.0.0.1:7274
    originRequest:
      noTLSVerify: true
  # API (FastAPI)
  - hostname: api.demo.giljo.ai
    service: https://127.0.0.1:7272
    originRequest:
      noTLSVerify: true
  # Catch-all (required)
  - service: http_status:404
EOF

# Add DNS records (one-time per hostname)
cloudflared tunnel route dns giljo-demo demo.giljo.ai
cloudflared tunnel route dns giljo-demo api.demo.giljo.ai

# Run the tunnel
cloudflared tunnel run giljo-demo
```

#### How It Works

```
User browser (any device)
  --> https://demo.giljo.ai (Cloudflare edge, real TLS cert)
  --> Cloudflare Tunnel (encrypted)
  --> localhost:7274 (frontend) / localhost:7272 (API)
      (noTLSVerify: true skips mkcert validation on the tunnel side)
```

- Users get a valid TLS certificate from Cloudflare — no warnings, no root CA to install
- The tunnel connects outbound from the server (no inbound ports needed besides SSH)
- `noTLSVerify: true` tells cloudflared to accept the local mkcert certs without validation
- Firewall only needs to allow SSH — ports 7272/7274 stay unexposed to the internet

#### Frontend API Base URL

The frontend must know to call `api.demo.giljo.ai` instead of `10.1.0.116:7272`. Set this in the Vite environment or via `config.yaml`:

```yaml
# config.yaml
services:
  external_host: api.demo.giljo.ai
  external_port: 443
  external_protocol: https
```

Or via `.env` for the frontend build:

```
VITE_API_BASE_URL=https://api.demo.giljo.ai
```

#### Running as a Service

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

#### Quick Test (No Domain Required)

For a quick throwaway demo without a custom domain:

```bash
cloudflared tunnel --url https://127.0.0.1:7274 --no-tls-verify
```

This gives a temporary `*.trycloudflare.com` URL with valid TLS. Only works for a single origin (frontend), so the API would need to be proxied through the frontend or served on the same port.

### 7. TLS for Second Workstation (Non-Demo, Same User)

For users running GiljoAI on one machine and accessing from another on the same LAN, export the mkcert root CA:

```bash
# On the install machine: find the root CA
mkcert -CAROOT
# Copy rootCA.pem to the second machine

# Windows: double-click rootCA.pem -> Install Certificate -> Local Machine -> Trusted Root CAs
# macOS:   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain rootCA.pem
# Linux:   sudo cp rootCA.pem /usr/local/share/ca-certificates/giljo-ca.crt && sudo update-ca-certificates
```

After installing the root CA, both ports (7274 frontend, 7272 API) are trusted — no browser warnings.

## Capacity Estimates for This Hardware

### Per-User Resource Footprint

GiljoAI MCP does **no LLM inference** — it coordinates external AI clients (Claude Code, Cursor, etc.) via MCP tool endpoints. The server workload is lightweight REST + WebSocket + PostgreSQL.

| Resource | Per Active User |
|---|---|
| **RAM** | ~100-200 KB (WebSocket + session metadata) |
| **DB connections** | 1-3 from pool (returned between requests) |
| **DB storage** | 5-50 MB (grows with projects/messages) |
| **CPU** | Negligible except during vision doc chunking |
| **Network** | Bursty; small JSON payloads + WebSocket events |

### Hardware Budget

| Resource | Total Available | App Overhead | Available for Users |
|---|---|---|---|
| **RAM** | 24 GB | ~2-3 GB (Python + PG + template cache + OS) | ~20 GB |
| **DB connections** | 120 (pool 40 + overflow 80, after tuning) | ~5 (background tasks, broker) | ~115 |
| **CPU threads** | 24 | ~2-4 idle | ~20 |
| **Disk** | 422 GB free | ~5 GB (app + PG base) | ~400 GB |
| **Network** | 1 Gbps | minimal | ~1 Gbps |

### Concurrent User Estimates

| Scenario | Concurrent Users | Notes |
|---|---|---|
| **Conservative** | **50-75** | Default pool settings, safety margin |
| **Tuned (current config)** | **100-150** | Pool 40 + overflow 80, PG max_connections 200 |
| **With PgBouncer** | **200-300** | Connection multiplexing for higher density |

### Over a 5-Day Demo Window

| Metric | Estimate |
|---|---|
| **Peak concurrent** | 50-150 (depending on tuning) |
| **Total registered users** | **500-1,000+** over 5 days |
| **Assumption** | 10-20% of registered users active simultaneously |
| **DB storage at 1,000 users** | ~5-50 GB (well within 422 GB free) |

### Bottleneck Priority

1. **DB connection pool** — primary limit, addressed by auto-scaling in DatabaseManager
2. **Network (1 Gbps)** — hard ceiling at ~125 MB/s, sufficient for demo scale
3. **RAM** — not a concern at 24 GB for this workload
4. **CPU** — not a concern; no LLM inference, async I/O

## Conclusion

The existing installer security model is solid. The main action items for demo server deployment are:
- Firewall configuration (SSH only when using Cloudflare Tunnel)
- Verifying PostgreSQL listens on localhost only
- Cloudflare Tunnel for zero-friction TLS to remote users
- DatabaseManager auto-scales connection pool from system RAM at runtime
- Implementing session expiry cleanup
