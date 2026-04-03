# GiljoAI CE Trial Server — Technical Analysis & Implementation Runbook

**Date:** 2026-04-03
**Author:** Technical Analysis (for Product Manager review)
**Edition Scope:** CE (with controlled multi-tenant unlock)
**Status:** Planning
**Supersedes:** `Demo_server_prepp.md` (security recommendations incorporated here)

---

## 1. Executive Summary

Deploy GiljoAI Community Edition as a **self-service 7-day trial** at `demo.giljo.ai`, hosted on an Ubuntu server at the office, tunneled through Cloudflare to handle dynamic IP and TLS. Each trial user gets their own tenant (single-user, single-tenant) — leveraging the multi-tenant architecture CE already has. A lightweight registration portal handles sign-up, credential delivery, and lifecycle management.

This serves three strategic goals:
1. **Immediate:** Let prospects experience the product without installing anything
2. **Near-term:** Validate the deployment pipeline, TLS, and multi-tenant isolation under real traffic
3. **Long-term:** Groundwork for SaaS edition (Cloudflare, HTTPS, tenant provisioning, lifecycle automation)

---

## 2. Architecture Overview

```
                         ┌─────────────────────┐
                         │   www.giljo.ai       │
                         │   (Namecheap hosted) │
                         │   Marketing site     │
                         │   "Try Free" button  │
                         └────────┬────────────┘
                                  │ link to https://demo.giljo.ai/register
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Cloudflare (Free tier)                       │
│                                                                  │
│  demo.giljo.ai  ──── CNAME ───►  Cloudflare Tunnel ─────────►  │
│                       (proxied)   (cloudflared daemon)           │
│                                                                  │
│  Benefits: TLS termination, DDoS protection, WAF rules,         │
│            hides origin IP, handles dynamic IP automatically     │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ encrypted tunnel
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Ubuntu Server (Office)                         │
│                                                                  │
│  cloudflared daemon ──► localhost:7272 (FastAPI)                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              FastAPI (single port :7272)                  │    │
│  │                                                          │    │
│  │  /                    → Vue SPA (static from dist/)      │    │
│  │  /register            → Registration portal (new)        │    │
│  │  /api/*               → Application API                  │    │
│  │  /ws/*                → WebSocket                        │    │
│  │  /mcp/*               → MCP endpoints                    │    │
│  │  /trial/*             → Trial management API (new)       │    │
│  │                                                          │    │
│  │  Middleware: Auth, CSRF, Rate Limit, Metrics             │    │
│  └──────────────────────────────┬───────────────────────────┘    │
│                                  │                                │
│  ┌──────────────────────────────┴───────────────────────────┐    │
│  │           PostgreSQL 18 (localhost:5432 only)             │    │
│  │                                                           │    │
│  │  trial_accounts table (lifecycle tracking)                │    │
│  │  Per-tenant schemas/rows (standard CE multi-tenant)       │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Cron Jobs                                                 │   │
│  │  • Every hour: expire trials > 7 days (deactivate)        │   │
│  │  • Daily: purge retired trials > 30 days (delete data)    │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Why Cloudflare Tunnel (Not Port Forwarding)

| Concern | Port Forwarding | Cloudflare Tunnel |
|---------|----------------|-------------------|
| Dynamic IP | Requires DDNS, breaks on IP change | Tunnel is outbound — IP changes are invisible |
| TLS certificate | Must manage Let's Encrypt + renewal | Cloudflare provides edge TLS automatically |
| Origin IP exposure | Public, attackable | Hidden behind Cloudflare proxy |
| DDoS protection | None | Cloudflare free-tier protection |
| Firewall config | Open port 443 inbound | Zero inbound ports needed |
| Setup complexity | Moderate | Low (single daemon) |

---

## 4. Single-Port Prerequisite (0902)

The trial server **requires** the single-port work (handover 0902) to be completed first. Currently the product runs on two ports (7272 API + 7274 Vite frontend). For the demo:

- Cloudflare Tunnel maps `demo.giljo.ai` → `localhost:7272`
- FastAPI serves both the Vue SPA (from `frontend/dist/`) and the API on a single port
- No Vite dev server in production

**Status:** 0902 is planned, handovers written (0902a–d), marked as CE release blocker. This must ship before the trial server goes live.

---

## 5. DNS & Cloudflare Setup — Step by Step

### 5.1 Understanding the Change

Currently:
```
giljo.ai domain registration  → Namecheap (paid, multi-year)
giljo.ai DNS (nameservers)    → Namecheap BasicDNS
giljo.ai website hosting      → Namecheap
giljo.ai email (MX records)   → Microsoft 365
giljoai.com                    → Namecheap (separate domain, unaffected)
```

After:
```
giljo.ai domain registration  → Namecheap (unchanged, keeps your money)
giljo.ai DNS (nameservers)    → Cloudflare (free plan)
giljo.ai website hosting      → Namecheap (unchanged, just the DNS pointer moves)
giljo.ai email (MX records)   → Microsoft 365 (unchanged, records recreated in Cloudflare)
giljoai.com                    → Namecheap (completely unaffected)
demo.giljo.ai                 → NEW: Cloudflare Tunnel → office Ubuntu server
```

Only the **nameserver authority** moves. All records point to the same destinations. Your Namecheap hosting, Microsoft email, and domain registration are unaffected.

### 5.2 Before You Start — Record Your Current DNS

Log into Namecheap → Domain List → `giljo.ai` → Advanced DNS. Screenshot or copy every record. You'll need this to verify Cloudflare's auto-import. Typical records to look for:

| Type | Host | Value | Purpose |
|------|------|-------|---------|
| A | @ | (Namecheap hosting IP) | Website root |
| CNAME | www | (Namecheap hosting alias) | Website www |
| MX | @ | `*.mail.protection.outlook.com` | Microsoft 365 email |
| TXT | @ | `v=spf1 include:spf.protection.outlook.com ...` | Email SPF |
| CNAME | autodiscover | `autodiscover.outlook.com` | Outlook auto-config |
| TXT | @ | `MS=msXXXXXX` | Microsoft domain verification |
| Any others | ... | ... | ... |

**Write these down.** Cloudflare usually auto-imports them, but you need to verify nothing was missed.

### 5.3 Cloudflare Account & Domain Setup

**Step 1: Create Cloudflare account**
```
1. Go to https://dash.cloudflare.com/sign-up
2. Create account with your business email
3. Free plan is sufficient
```

**Step 2: Add giljo.ai to Cloudflare**
```
1. Cloudflare dashboard → "Add a site"
2. Enter: giljo.ai
3. Select: Free plan
4. Cloudflare scans your existing DNS records automatically
```

**Step 3: Verify auto-imported records**
```
Cloudflare shows you the records it found. Compare against your screenshot from 5.2.

CRITICAL CHECKS:
✅ MX records for Microsoft 365 present and correct
✅ SPF TXT record present
✅ A/CNAME for www and @ pointing to Namecheap hosting
✅ autodiscover CNAME for Outlook
✅ Any Microsoft verification TXT records

If anything is missing, add it manually now.

For records pointing to Namecheap hosting (A record for @, CNAME for www):
  → Set the proxy status to "DNS only" (gray cloud icon)
  → This ensures Namecheap hosting works unchanged
  → You can enable proxying later if desired

For MX, TXT, and autodiscover records:
  → These are always "DNS only" (can't be proxied)
```

**Step 4: Note the Cloudflare nameservers**
```
Cloudflare assigns you two nameservers, e.g.:
  aria.ns.cloudflare.com
  owen.ns.cloudflare.com

Copy these — you need them for the next step.
```

### 5.4 Switch Nameservers at Namecheap

```
1. Log into Namecheap → Domain List → giljo.ai
2. Under "Nameservers", change from "Namecheap BasicDNS" to "Custom DNS"
3. Enter the two Cloudflare nameservers:
     aria.ns.cloudflare.com
     owen.ns.cloudflare.com
4. Save (green checkmark)
```

**Propagation:** Takes 10 minutes to 48 hours (usually under 1 hour). During propagation:
- Your website continues to work (records haven't changed, just who serves them)
- Email continues to work (MX records are the same)
- Cloudflare dashboard shows "Pending" until it detects the nameserver change

**Verification:**
```bash
# From any machine, check nameservers
nslookup -type=NS giljo.ai
# Should return the Cloudflare nameservers

# Verify website still resolves
nslookup www.giljo.ai
# Should return same IP as before

# Verify email MX still resolves
nslookup -type=MX giljo.ai
# Should return Microsoft 365 mail servers
```

### 5.5 Cloudflare SSL/TLS Settings

Once the domain is active on Cloudflare:

```
Cloudflare dashboard → giljo.ai → SSL/TLS → Overview

Set encryption mode to: "Full"
  (NOT "Full (Strict)" — your Namecheap hosting may not have a valid origin cert)
  (NOT "Flexible" — can cause redirect loops)

For demo.giljo.ai specifically, "Full" is fine because cloudflared handles the 
tunnel encryption end-to-end.
```

### 5.6 Important: What NOT to Do

- **Do NOT** delete any DNS records at Namecheap — they're now irrelevant (Cloudflare is authoritative)
- **Do NOT** change your Namecheap hosting plan — it still serves your website
- **Do NOT** touch `giljoai.com` — completely separate domain, unaffected
- **Do NOT** set proxy mode (orange cloud) on your website A/CNAME records initially — keep them gray cloud (DNS only) until you've confirmed everything works
- **If something breaks** — change nameservers back to "Namecheap BasicDNS" in Namecheap and everything reverts within minutes

---

## 6. Cloudflare Tunnel Setup — Step by Step

### 6.1 Install cloudflared on Ubuntu Server

```bash
# Download and install
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
  -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb

# Verify
cloudflared --version
```

### 6.2 Authenticate cloudflared

```bash
# This opens a browser window — select giljo.ai when prompted
cloudflared tunnel login

# Creates: ~/.cloudflared/cert.pem
```

If the Ubuntu server is headless (no browser), the command prints a URL. Open it on any machine, authenticate, and the cert is saved on the server.

### 6.3 Create the Tunnel

```bash
# Create named tunnel
cloudflared tunnel create giljo-demo

# Output shows tunnel UUID — note it, e.g.: a1b2c3d4-e5f6-7890-abcd-ef1234567890
# Creates: ~/.cloudflared/<tunnel-uuid>.json (credentials)
```

### 6.4 Configure the Tunnel

```bash
# Create config file
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: giljo-demo
credentials-file: /home/<your-user>/.cloudflared/<tunnel-uuid>.json

ingress:
  # Single-port: everything goes to FastAPI on 7272
  - hostname: demo.giljo.ai
    service: http://localhost:7272
  # Catch-all (required by cloudflared)
  - service: http_status:404
EOF
```

**Note:** We use `http://localhost:7272` (not https) because:
- Cloudflare handles TLS at the edge (user ↔ Cloudflare)
- The tunnel itself is encrypted (Cloudflare ↔ cloudflared)
- localhost:7272 doesn't need its own TLS — traffic never leaves the machine
- This is simpler than the old setup which needed `noTLSVerify: true` for mkcert certs

### 6.5 Create DNS Route

```bash
# This creates a CNAME record in Cloudflare DNS automatically
cloudflared tunnel route dns giljo-demo demo.giljo.ai
```

Verify in Cloudflare dashboard → DNS → you should see:
```
CNAME   demo   <tunnel-uuid>.cfargotunnel.com   Proxied
```

### 6.6 Test the Tunnel (Manual)

```bash
# Start the tunnel (foreground, for testing)
cloudflared tunnel run giljo-demo

# From another machine, open:
# https://demo.giljo.ai
# Should show the GiljoAI app (once FastAPI + dist/ are deployed)
```

### 6.7 Install as systemd Service (Auto-Start on Boot)

```bash
# Install as system service
sudo cloudflared service install

# This copies config to /etc/cloudflared/config.yml
# and credentials to /etc/cloudflared/<tunnel-uuid>.json

# Enable and start
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Verify
sudo systemctl status cloudflared
```

### 6.8 Tunnel Health Check

```bash
# Check tunnel status
cloudflared tunnel info giljo-demo

# Check from outside
curl -I https://demo.giljo.ai
# Should return HTTP 200 with Cloudflare headers:
#   cf-ray: xxxxx
#   server: cloudflare
```

---

## 7. Ubuntu Server Setup & Hardening

### 7.1 Base OS

```bash
# Ubuntu 24.04 LTS recommended (or latest LTS available)
# Ensure system is updated
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y curl git python3.12 python3.12-venv nodejs npm ufw fail2ban
```

### 7.2 Firewall (UFW)

With Cloudflare Tunnel, **no inbound web ports are needed.** The tunnel connects outbound.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
# That's it — no 80/tcp, no 443/tcp needed
sudo ufw enable
sudo ufw status
```

Expected output:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
```

### 7.3 Fail2ban for SSH

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Default config bans IPs after 5 failed SSH attempts for 10 minutes
# Customize in /etc/fail2ban/jail.local if needed
```

### 7.4 PostgreSQL 18

```bash
# Add PGDG repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
sudo apt update
sudo apt install -y postgresql-18

# Verify listening on localhost only
sudo grep listen_addresses /etc/postgresql/18/main/postgresql.conf
# Should show: listen_addresses = 'localhost'
```

### 7.5 pg_hba.conf (Database Access Control)

```
# /etc/postgresql/18/main/pg_hba.conf

# Admin: local sudo only
local   all             postgres                                peer

# App roles: password over TCP, localhost only
host    giljo_db        giljo_owner     127.0.0.1/32            scram-sha-256
host    giljo_db        giljo_user      127.0.0.1/32            scram-sha-256

# Reject everything else
host    all             all             0.0.0.0/0               reject
```

### 7.6 Unattended Security Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Select "Yes" to enable automatic security updates
```

### 7.7 Deploy GiljoAI CE

```bash
# Clone repository
git clone <repo-url> /opt/giljo-mcp
cd /opt/giljo-mcp

# Run installer (creates DB roles, schema, initial tenant)
python3 install.py

# Build frontend for production (single-port mode)
cd frontend
npm install
npm run build
# Creates frontend/dist/ — FastAPI serves this statically

# Start the application
cd /opt/giljo-mcp
python3 startup.py
# Listens on localhost:7272
```

### 7.8 GiljoAI as systemd Service

```bash
# Create service file
sudo cat > /etc/systemd/system/giljo-mcp.service << 'EOF'
[Unit]
Description=GiljoAI MCP Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=giljo
Group=giljo
WorkingDirectory=/opt/giljo-mcp
ExecStart=/opt/giljo-mcp/.venv/bin/python startup.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable giljo-mcp
sudo systemctl start giljo-mcp
```

---

## 8. Email Delivery Setup (Resend)

### 8.1 Why Resend

| Service | Free Tier | Setup | Verdict |
|---------|-----------|-------|---------|
| **Resend** | 100 emails/day | API key + domain verify | Best DX, modern, recommended |
| Mailgun | 100 emails/day (sandbox) | Heavier setup | Good but more complex |
| SendGrid | 100 emails/day | Straightforward | Works, less modern |
| SMTP (Namecheap) | Included | Direct | Deliverability concerns |

100 emails/day is plenty for a trial server (that's 100 new signups per day).

### 8.2 Resend Account Setup

```
1. Go to https://resend.com/signup
2. Create account
3. Dashboard → API Keys → Create API Key
4. Name: "giljo-demo-trial"
5. Permission: "Sending access" only
6. Domain: giljo.ai (add after domain verification)
7. Copy the API key — store in server .env file
```

### 8.3 Domain Verification (Critical for Deliverability)

To send from `noreply@giljo.ai` without landing in spam:

```
1. Resend dashboard → Domains → Add Domain → giljo.ai
2. Resend gives you DNS records to add. Add these in CLOUDFLARE (since Cloudflare is now your DNS):

   Type    Host                          Value                           
   TXT     resend._domainkey.giljo.ai    (DKIM key provided by Resend)  
   TXT     giljo.ai                      (SPF — merge with existing Microsoft SPF record)
   
3. SPF MERGE — you already have an SPF record for Microsoft:
   
   Existing:  v=spf1 include:spf.protection.outlook.com -all
   New:       v=spf1 include:spf.protection.outlook.com include:send.resend.com -all
   
   DO NOT create two SPF TXT records — merge them into one.

4. Wait for Resend to verify (usually minutes, up to 24 hours)
5. Once verified, Resend shows green checkmark — you can send from @giljo.ai
```

### 8.4 DMARC Record (Recommended)

If not already present, add a DMARC record in Cloudflare DNS:

```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=quarantine; rua=mailto:admin@giljo.ai
```

This tells email providers how to handle messages that fail SPF/DKIM checks.

### 8.5 Integration Code

```python
# trial/email_service.py
import httpx
from pathlib import Path

RESEND_API_KEY = os.environ["RESEND_API_KEY"]  # From .env

async def send_trial_credentials(email: str, username: str, password: str, expires_at: str):
    html = _render_welcome_email(username, password, expires_at)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": "GiljoAI <noreply@giljo.ai>",
                "to": email,
                "subject": "Your GiljoAI Trial — Credentials Inside",
                "html": html,
            },
        )
        response.raise_for_status()

async def send_expiry_warning(email: str, days_remaining: int):
    # Day 5: "Your trial expires in 2 days"
    ...

async def send_expired_notice(email: str):
    # Day 7: "Your trial has ended. Download CE to keep using GiljoAI."
    ...
```

---

## 9. Registration & Trial Lifecycle

### 9.1 Registration Flow

```
User visits https://demo.giljo.ai/register
        │
        ▼
┌─────────────────────────┐
│  Registration Portal     │
│  (standalone page)       │
│                          │
│  Fields:                 │
│  • Email address         │
│  • (optional) Name       │
│                          │
│  [Start Free Trial]      │
└────────────┬────────────┘
             │ POST /trial/register
             ▼
┌─────────────────────────────────────────────┐
│  Trial Registration API                      │
│                                              │
│  1. Validate email (format, not disposable)  │
│  2. Rate-limit check (3/IP/hour)             │
│  3. Check: email not already active          │
│  4. Generate username (email address itself)  │
│  5. Generate secure random password (16 char)│
│  6. Create tenant via TenantManager          │
│  7. Create user in that tenant               │
│  8. Insert trial_accounts row                │
│  9. Send welcome email via Resend            │
│ 10. Return success page                      │
└─────────────────────────────────────────────┘
             │
             ▼
    Email arrives:
    ─────────────────────────────────
    Welcome to GiljoAI!

    Your trial is active for 7 days.

    URL:      https://demo.giljo.ai
    Username: patrik@example.com
    Password: xK9mR2vL7nQ4pW8z

    Log in and start orchestrating.
    ─────────────────────────────────
```

### 9.2 Registration Portal — Separate Page, Not in CE App

The registration page is served at `/register` as a standalone HTML page — **not** part of the Vue SPA. This keeps trial infrastructure decoupled from the CE product.

```
FastAPI routes:
  /register          → serves register.html (static, no auth)
  /trial/register    → POST API endpoint (no auth, rate-limited)
  /trial/status      → GET admin endpoint (auth required)
  /                  → Vue SPA (auth required — normal CE app)
```

Auth middleware exemptions: `/register`, `/trial/register`, `/assets/register/*`

### 9.3 Trial Account Lifecycle

```
States:
  ACTIVE   → account usable, all features available
  EXPIRED  → 7 days elapsed, login disabled, data preserved
  RETIRED  → 30 days after expiry, data scheduled for deletion
  DELETED  → tenant and all data purged

Timeline:
  Day 0 ──────── Day 5 ────── Day 7 ──────── Day 37 ──────── Day 38+
  ACTIVE          Warning      EXPIRED         RETIRED          DELETED
                  email        (login blocked) (data preserved) (tenant purged)
```

### 9.4 Database Schema

```sql
CREATE TABLE trial_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    tenant_key      VARCHAR(64) NOT NULL REFERENCES tenants(tenant_key),
    user_id         UUID NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,           -- created_at + 7 days
    retired_at      TIMESTAMPTZ,                    -- set when status → retired
    deleted_at      TIMESTAMPTZ,                    -- set when status → deleted
    ip_address      INET,                           -- abuse tracking
    CONSTRAINT chk_status CHECK (status IN ('active', 'expired', 'retired', 'deleted'))
);

CREATE INDEX idx_trial_status ON trial_accounts(status) WHERE status IN ('active', 'expired');
CREATE INDEX idx_trial_expires ON trial_accounts(expires_at) WHERE status = 'active';
```

### 9.5 Lifecycle Cron Jobs

```python
# Run hourly via systemd timer or APScheduler
async def expire_trials():
    """Deactivate trials past 7 days."""
    # UPDATE trial_accounts SET status = 'expired'
    #   WHERE status = 'active' AND expires_at < now()
    # For each: disable the user account (set is_active = false)

# Run daily at 03:00 UTC
async def send_expiry_warnings():
    """Warn users 2 days before expiry."""
    # SELECT * FROM trial_accounts
    #   WHERE status = 'active' AND expires_at BETWEEN now() AND now() + interval '2 days'
    # Send warning email for each

# Run daily at 04:00 UTC
async def retire_expired_trials():
    """Mark 30-day-old expired trials for deletion."""
    # UPDATE trial_accounts SET status = 'retired', retired_at = now()
    #   WHERE status = 'expired' AND expires_at < now() - interval '30 days'

# Run daily at 05:00 UTC
async def purge_retired_trials():
    """Delete all data for retired trials."""
    # For each retired trial:
    #   1. Delete all tenant data (jobs, missions, documents, etc.)
    #   2. Delete the tenant via TenantManager
    #   3. UPDATE trial_accounts SET status = 'deleted', deleted_at = now()
```

---

## 10. Security — Abuse Prevention

| Threat | Mitigation |
|--------|------------|
| Mass registration (spam bots) | Rate limit: 3 registrations per IP per hour |
| Disposable email addresses | Block known disposable domains (maintainable list) |
| Re-registration after expiry | Allow after 30-day retirement period (new tenant) |
| Credential stuffing on login | Existing CE rate limiting on login endpoint |
| Resource exhaustion per tenant | Per-tenant caps: max jobs, max documents, max storage |
| Data exfiltration | Standard CE tenant isolation (tenant_key on every query) |
| DDoS | Cloudflare free-tier DDoS protection at edge |
| Server compromise | UFW (SSH only), fail2ban, unattended security updates |
| Database exposure | PostgreSQL on localhost only, scram-sha-256, dedicated roles |

### What "CE Unlocked for Multi-Tenant" Means

CE already has full multi-tenant support (TenantManager, tenant_key on all tables, tenant-scoped queries). The trial server simply:
1. Creates a new tenant per registration (existing CE capability)
2. Creates a single user in that tenant (existing CE capability)
3. Adds trial lifecycle management on top (new, thin layer)

No CE code changes needed for multi-tenancy — it's already there.

---

## 11. Infrastructure Bill of Materials

| Component | Provider | Cost |
|-----------|----------|------|
| `giljo.ai` DNS management | Cloudflare (free plan) | $0 |
| Cloudflare Tunnel | Cloudflare (free, included) | $0 |
| TLS certificate (edge) | Cloudflare (automatic) | $0 |
| DDoS protection | Cloudflare (free tier) | $0 |
| Email delivery | Resend (100/day free tier) | $0 |
| Ubuntu server | Existing office hardware | $0 (electricity) |
| Internet | Existing office connection | $0 (already paying) |
| Domain registration | Namecheap (already owned, prepaid) | $0 (sunk cost) |
| **Total incremental cost** | | **$0/month** |

---

## 12. Implementation Phases — Detailed

### Phase 0: Prerequisites (Must Complete First)

| # | Task | Status | Blocks |
|---|------|--------|--------|
| 0.1 | **0902 Single-Port Serving** — FastAPI serves Vue SPA + API on :7272 | Handovers written (0902a–d) | Everything |
| 0.2 | **Ubuntu server provisioned** — hardware, OS installed, SSH access | Not started | Phase 1+ |
| 0.3 | **PostgreSQL 18 installed** on Ubuntu, localhost-only | Not started | Phase 2+ |
| 0.4 | **GiljoAI CE deployed** on Ubuntu, running on :7272 | Not started | Phase 1+ |

### Phase 1: DNS Migration & Tunnel (~2–3 hours)

| # | Task | Detail |
|---|------|--------|
| 1.1 | Screenshot current Namecheap DNS records | Backup before migration |
| 1.2 | Create Cloudflare account (free) | dash.cloudflare.com |
| 1.3 | Add `giljo.ai` to Cloudflare | Auto-scan imports records |
| 1.4 | Verify all DNS records imported | MX (Microsoft), SPF, A/CNAME (website), autodiscover |
| 1.5 | Set website A/CNAME records to "DNS only" (gray cloud) | Prevents Cloudflare proxying Namecheap-hosted site |
| 1.6 | Change nameservers at Namecheap to Cloudflare's | Custom DNS → two CF nameservers |
| 1.7 | Wait for propagation + verify | `nslookup -type=NS giljo.ai`, test website + email |
| 1.8 | Install `cloudflared` on Ubuntu | apt/deb package |
| 1.9 | Authenticate: `cloudflared tunnel login` | Selects giljo.ai domain |
| 1.10 | Create tunnel: `cloudflared tunnel create giljo-demo` | Note UUID |
| 1.11 | Configure tunnel: `config.yml` → demo.giljo.ai → localhost:7272 | Single ingress rule |
| 1.12 | Route DNS: `cloudflared tunnel route dns giljo-demo demo.giljo.ai` | Auto-creates CNAME |
| 1.13 | Test tunnel: `cloudflared tunnel run giljo-demo` | Verify https://demo.giljo.ai |
| 1.14 | Install as systemd service | Auto-start on boot |
| 1.15 | Set Cloudflare SSL mode to "Full" | dashboard → SSL/TLS |

**Verification checklist after Phase 1:**
- [ ] `www.giljo.ai` still loads (Namecheap hosting)
- [ ] Email to `@giljo.ai` still arrives (Microsoft 365)
- [ ] `https://demo.giljo.ai` shows GiljoAI app
- [ ] `https://demo.giljo.ai/api/health` returns healthy
- [ ] Certificate in browser shows Cloudflare-issued cert for `demo.giljo.ai`

### Phase 2: Resend Email Setup (~1–2 hours)

| # | Task | Detail |
|---|------|--------|
| 2.1 | Create Resend account | resend.com |
| 2.2 | Generate API key | "Sending access" permission only |
| 2.3 | Add `giljo.ai` domain in Resend | Get DKIM/SPF records |
| 2.4 | Add DKIM TXT record in Cloudflare DNS | `resend._domainkey.giljo.ai` |
| 2.5 | Merge SPF record in Cloudflare DNS | Add `include:send.resend.com` to existing SPF |
| 2.6 | Add DMARC TXT record if missing | `_dmarc.giljo.ai` |
| 2.7 | Wait for Resend domain verification | Usually minutes |
| 2.8 | Test: send email from Resend dashboard | Verify it arrives, not in spam |
| 2.9 | Store API key in server `.env` | `RESEND_API_KEY=re_xxxxx` |

### Phase 3: Trial Registration API (~8–12 hours)

| # | Task | Detail |
|---|------|--------|
| 3.1 | Create Alembic migration for `trial_accounts` table | With idempotency guards |
| 3.2 | Build `trial/` module: models, repository, service | Standard CE layered pattern |
| 3.3 | Build `POST /trial/register` endpoint | Validates email, creates tenant+user, sends email |
| 3.4 | Build `GET /trial/status` endpoint | Admin-only, lists active/expired trials |
| 3.5 | Implement disposable email blocking | Maintainable blocklist |
| 3.6 | Rate limiter on `/trial/register` | 3 per IP per hour |
| 3.7 | Auth middleware exemption for `/register`, `/trial/register` | Public endpoints |
| 3.8 | CSRF middleware exemption for `/trial/register` | Public POST |
| 3.9 | Email service integration (Resend) | Welcome email + warning + expiry emails |
| 3.10 | Welcome email HTML template | Branded, responsive, contains credentials |
| 3.11 | Warning email HTML template | "2 days remaining" |
| 3.12 | Expired email HTML template | "Trial ended — download CE" |
| 3.13 | Unit tests for trial registration flow | Happy path + edge cases |

### Phase 4: Registration Portal UI (~4–6 hours)

| # | Task | Detail |
|---|------|--------|
| 4.1 | Design registration page | Branded, minimal, matches GiljoAI design system |
| 4.2 | Build `register.html` + supporting assets | Standalone (not Vue SPA) |
| 4.3 | Form: email input + submit button | Client-side email validation |
| 4.4 | Success page: "Check your email" | Shown after successful registration |
| 4.5 | Error states: duplicate email, rate limit, validation | User-friendly messages |
| 4.6 | Serve via FastAPI static route at `/register` | Exempt from auth |
| 4.7 | Mobile responsive | Trial users may be on phones |

### Phase 5: Lifecycle Automation (~4–6 hours)

| # | Task | Detail |
|---|------|--------|
| 5.1 | Implement `expire_trials()` cron | Hourly, deactivates expired accounts |
| 5.2 | Implement `send_expiry_warnings()` cron | Daily, emails at day 5 |
| 5.3 | Implement `retire_expired_trials()` cron | Daily, marks for deletion at day 37 |
| 5.4 | Implement `purge_retired_trials()` cron | Daily, deletes tenant data |
| 5.5 | Set up systemd timers (or APScheduler) | Reliable scheduling |
| 5.6 | Logging for all lifecycle transitions | Audit trail |
| 5.7 | Per-tenant resource caps | Prevent any single trial from hogging resources |

### Phase 6: www.giljo.ai Integration (~2 hours)

| # | Task | Detail |
|---|------|--------|
| 6.1 | Add "Try Free" CTA button on marketing site | Prominent placement |
| 6.2 | Link target: `https://demo.giljo.ai/register` | Cross-origin link |
| 6.3 | Update marketing copy | Mention 7-day free trial |
| 6.4 | Add trial information to any landing pages | Feature highlights |

### Phase 7: Monitoring & Operational Readiness (~2–4 hours)

| # | Task | Detail |
|---|------|--------|
| 7.1 | Uptime monitoring | External ping (e.g., UptimeRobot free tier) → `https://demo.giljo.ai/api/health` |
| 7.2 | Disk space monitoring | Alert at 80% usage |
| 7.3 | Log rotation | Configure for FastAPI + cloudflared logs |
| 7.4 | PostgreSQL backup | Daily pg_dump to local + optional offsite |
| 7.5 | Alert on trial registration failures | Email or Slack notification |
| 7.6 | Document runbook for server maintenance | Restart procedures, log locations, troubleshooting |

**Total estimated effort: 24–36 hours across all phases**

---

## 13. What This Gives Us Toward SaaS

This trial infrastructure is **directly reusable** for SaaS edition:

| Trial Component | SaaS Reuse |
|----------------|------------|
| Cloudflare DNS + Tunnel + TLS | Same setup, upgrade to Pro for analytics if needed |
| Tenant provisioning API | Becomes SaaS onboarding flow |
| Email integration (Resend) | Transactional emails: invites, resets, billing receipts |
| Account lifecycle management | Becomes subscription lifecycle (Stripe integration point) |
| Registration portal | Evolves into sign-up with plans/pricing |
| Multi-tenant isolation (CE) | Foundation for SaaS multi-org |
| Server hardening playbook | Production deployment baseline |
| systemd services + monitoring | Operational maturity for SaaS |
| Per-tenant resource caps | Becomes plan-based limits (free/pro/enterprise) |

The trial is effectively **SaaS v0.1** — single-user tenants, no billing, time-limited. Adding Stripe and multi-user unlocks SaaS proper.

---

## 14. Deployment Topology Summary

```
www.giljo.ai (Namecheap hosted)         demo.giljo.ai (Cloudflare → Office)
┌──────────────────────┐                ┌──────────────────────────────┐
│  Marketing website    │   "Try Free"  │  Cloudflare DNS (proxied)    │
│  Static site / CMS   │──────────────►│  Cloudflare Tunnel           │
│  Hosted: Namecheap   │                │  Edge TLS (automatic)        │
│  DNS: Cloudflare     │                │  DDoS protection             │
└──────────────────────┘                └──────────────┬───────────────┘
                                                       │ outbound tunnel
                                                       │ (no inbound ports)
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │  Ubuntu Server (Office LAN)  │
                                        │                              │
                                        │  cloudflared ─► :7272        │
                                        │  FastAPI (single port)       │
                                        │  PostgreSQL (localhost)       │
                                        │  Cron (trial lifecycle)      │
                                        │  Resend (outbound email)     │
                                        └──────────────────────────────┘
```

---

## 15. Open Questions for Product Manager

1. **Trial duration:** 7 days confirmed? Or should we test 7 vs 14?
2. **Trial extensions:** Can a user request more time? Manual or self-serve?
3. **Data export before expiry:** Should users be able to export their trial data?
4. **Re-registration:** After the 30-day retirement, can the same email sign up again?
5. **Usage limits:** Should trial tenants have caps (e.g., max 10 jobs, 50 documents)?
6. **Conversion CTA:** When trial expires — "Download CE for free" or "Contact sales"?
7. **Analytics:** Track trial engagement (logins, jobs created, features used)?
8. **Marketing site readiness:** Is `www.giljo.ai` ready for a "Try Free" button?
9. **Support channel:** Where do trial users go for help? Email? Discord? GitHub?
10. **In-app branding:** Show "Trial — X days remaining" banner in the UI?
11. **Password policy:** Let trial users change their generated password? Or keep it simple?
12. **Concurrent trial limit:** Cap total active trials to protect server resources (e.g., max 50)?

---

## 16. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Office internet outage | Medium | Trial users can't access | Cloudflare shows error page; move to VPS if frequent |
| Dynamic IP change | None (tunnel) | None | Cloudflare Tunnel is immune to IP changes |
| Server hardware failure | Low | Full outage | PostgreSQL backups; replacement hardware or migrate to VPS |
| Server compromise | Low | Trial data breach (emails only) | Hardened per section 7; minimal PII |
| Abuse / spam registrations | Medium | Resource exhaustion | Rate limiting, disposable email blocking, tenant caps |
| Trial data fills disk | Low | Server instability | 30-day purge cycle, disk monitoring, alerts |
| Email lands in spam | Medium | Users don't get credentials | Domain verification (SPF/DKIM/DMARC), Resend reputation |
| 0902 single-port delays | Medium | Blocks trial launch | Already prioritized as CE release blocker |
| Cloudflare free tier limits | Low | Throttling under load | Free tier is generous; upgrade to Pro ($20/mo) if needed |
| Namecheap DNS migration issue | Low | Website/email disruption | Record backup in 5.2; revert nameservers to Namecheap BasicDNS |

---

## 17. Recommended Execution Order

```
NOW          ──►  Complete 0902 Single-Port (CE release blocker)
                  Provision Ubuntu server + OS hardening
                  Install PostgreSQL 18

WEEK 1       ──►  Phase 1: Cloudflare + DNS migration
                  Phase 2: Resend email setup
                  Deploy GiljoAI CE on Ubuntu, verify via tunnel

WEEK 2       ──►  Phase 3: Trial registration API
                  Phase 4: Registration portal UI

WEEK 3       ──►  Phase 5: Lifecycle automation (cron jobs, emails)
                  Phase 7: Monitoring + uptime checks

WEEK 4       ──►  Internal testing (team signs up, uses trial, verifies lifecycle)
                  Phase 6: www.giljo.ai "Try Free" button
                  Soft launch (limited audience)

WEEK 5       ──►  Public launch of demo.giljo.ai
```

---

## Appendix A: Reverting DNS to Namecheap

If anything goes wrong after the nameserver migration:

```
1. Namecheap → Domain List → giljo.ai
2. Nameservers → change from "Custom DNS" back to "Namecheap BasicDNS"
3. Save
4. Wait 10-60 minutes for propagation
5. Everything reverts to exactly how it was before
```

Your Namecheap DNS records are still there — they were never deleted, just dormant while Cloudflare was authoritative.

## Appendix B: Quick Test Without Domain (Day-One Validation)

Before setting up DNS, validate the tunnel works:

```bash
# On Ubuntu server with GiljoAI running on :7272
cloudflared tunnel --url http://localhost:7272

# Outputs a temporary URL like: https://random-words.trycloudflare.com
# Open it in a browser — should show GiljoAI
# No DNS or domain config needed — just proves the concept works
```

## Appendix C: Relationship to Existing Documentation

| Document | Status |
|----------|--------|
| `handovers/Demo_server_prepp.md` | **Superseded** — security recommendations incorporated into sections 7 and 10 of this document. Old tunnel config used two-port setup which is obsolete once 0902 ships. |
| `handovers/0902_SINGLE_PORT_FRONTEND_SERVING.md` | **Prerequisite** — must complete before trial server deployment |
| `docs/EDITION_ISOLATION_GUIDE.md` | **Reference** — trial infrastructure is CE-native, no SaaS code involved |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | **Reference** — network topology section will need updating to reflect single-port + Cloudflare deployment option |

---

*This document is a technical analysis and implementation runbook for product review. Implementation handovers will be created per the standard protocol once the approach is approved.*
