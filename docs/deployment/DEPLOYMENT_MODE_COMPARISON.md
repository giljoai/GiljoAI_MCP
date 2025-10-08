# Deployment Mode Comparison - Quick Reference

**Version:** 2.0
**Date:** 2025-10-07
**Purpose:** Quick reference guide for choosing and understanding GiljoAI MCP deployment modes

---

## At a Glance

| Mode | When to Use | Users | Network | Auth Required | Setup Time |
|------|-------------|-------|---------|---------------|------------|
| **LOCALHOST** | Solo development | 1 | 127.0.0.1 only | ❌ No | 5 min |
| **LAN** | Team collaboration | 3-10 | Local network | ✅ Yes (User accounts + API keys) | 15-30 min |
| **WAN** | Internet-facing | 10-1000+ | Public internet | ✅ Yes (Enhanced security) | 2-4 hours |
| **SaaS** | Multi-tenant SaaS | 1000+ | Global | ✅ Yes (OAuth2 + Multi-tenant) | Days (automated) |

---

## Detailed Feature Comparison

### Network & Access

| Feature | LOCALHOST | LAN | WAN | SaaS |
|---------|-----------|-----|-----|------|
| **Network Binding** | 127.0.0.1 | 0.0.0.0 (all interfaces) | 0.0.0.0 + Reverse Proxy | Load Balanced |
| **IP Access** | localhost only | LAN subnet | Internet | Global CDN |
| **Domain Name** | N/A | Optional | Required | Required |
| **SSL/TLS** | ❌ No | ⚠️ Optional | ✅ Mandatory | ✅ Mandatory |
| **Reverse Proxy** | ❌ No | ⚠️ Optional | ✅ Required (nginx/Caddy) | ✅ Required |
| **Firewall** | Host firewall (default) | Host firewall + LAN rules | Host + WAF + DDoS | Enterprise WAF + CDN |
| **Ports Open** | None (localhost) | 7272, 7274 (LAN only) | 80, 443 (public) | 443 (public) |

### Authentication & Security

| Feature | LOCALHOST | LAN | WAN | SaaS |
|---------|-----------|-----|-----|------|
| **User Accounts** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Admin Account** | N/A | ✅ Setup Wizard | ✅ Setup Wizard | ✅ Automated Provisioning |
| **Login Method** | N/A | Username/Password | Username/Password | OAuth2 + Username/Password |
| **Session Management** | N/A | JWT tokens (24h) | JWT tokens + CSRF | JWT + Refresh tokens |
| **Personal API Keys** | ❌ No | ✅ Yes (per-user) | ✅ Yes (per-user) | ✅ Yes + Service keys |
| **API Key Format** | N/A | gk_{user_id}_{random} | gk_{user_id}_{random} | gk_{user_id}_{random} |
| **Multi-User Support** | ❌ No | ✅ Yes (3-10 users) | ✅ Yes (10-1000+) | ✅ Yes (unlimited) |
| **Role-Based Access** | N/A | ✅ Admin, Developer, Viewer | ✅ Admin, Developer, Viewer | ✅ Custom roles + RBAC |
| **Multi-Tenancy** | N/A | ❌ No | ❌ No | ✅ Yes (company isolation) |
| **2FA/MFA** | N/A | ❌ No (future) | ⚠️ Optional (future) | ✅ Yes (future) |
| **OAuth2 Providers** | N/A | ❌ No | ❌ No | ✅ Google, GitHub, Microsoft |
| **Rate Limiting** | ❌ No | ✅ Basic (100/min) | ✅ Advanced (per-IP, per-user) | ✅ Per-plan quotas |
| **Audit Logging** | ❌ No | ✅ Per-user actions | ✅ Comprehensive | ✅ Comprehensive + compliance |

### Infrastructure & Deployment

| Feature | LOCALHOST | LAN | WAN | SaaS |
|---------|-----------|-----|-----|------|
| **Database** | PostgreSQL (localhost) | PostgreSQL (localhost or LAN) | PostgreSQL + SSL | PostgreSQL HA cluster |
| **Redis/Caching** | ❌ No | ⚠️ Optional | ✅ Required | ✅ Required (cluster) |
| **High Availability** | ❌ No | ❌ No | ⚠️ Optional | ✅ Yes (multi-region) |
| **Auto-Scaling** | ❌ No | ❌ No | ⚠️ Optional | ✅ Yes |
| **Load Balancer** | ❌ No | ❌ No | ⚠️ Optional | ✅ Required |
| **CDN** | ❌ No | ❌ No | ⚠️ Optional | ✅ Required |
| **Monitoring** | Basic logs | Basic logs | ✅ Grafana/Prometheus | ✅ Enterprise monitoring |
| **Backups** | Manual | ⚠️ Recommended (automated) | ✅ Automated + offsite | ✅ Automated + multi-region |

### Costs (Monthly Estimates)

| Resource | LOCALHOST | LAN | WAN (Small) | WAN (Large) | SaaS |
|----------|-----------|-----|-------------|-------------|------|
| **Infrastructure** | $0 (local) | $0-50 (server) | $45-110 | $270-650 | $1,120-4,300+ |
| **Domain** | $0 | $0 (optional) | $12/year | $12/year | $12/year |
| **SSL Certificate** | $0 | $0 (optional) | $0 (Let's Encrypt) | $0-200/year | $0 (automated) |
| **Monitoring** | $0 | $0 | $0-50 | $20-50 | $100-300 |
| **WAF/DDoS Protection** | $0 | $0 | $0-20 | $20-200 | Included |
| **Total Est.** | **$0** | **$0-50** | **$45-180/month** | **$310-900/month** | **$1,220-4,612/month** |

---

## Use Case Recommendations

### LOCALHOST Mode ✅

**Best For:**
- Solo developers building and testing
- Development environments
- Proof of concept / experimentation
- Learning the system

**Not Suitable For:**
- Team collaboration
- Production workloads
- Network-accessible deployment
- Multi-user environments

**Example Scenario:**
> "I'm a developer wanting to try GiljoAI MCP on my laptop for personal projects."

### LAN Mode ✅

**Best For:**
- Small development teams (3-10 people)
- Office/company internal networks
- Trusted network environments
- Cost-effective team collaboration
- Educational institutions (campus network)

**Not Suitable For:**
- Internet-facing deployment
- Untrusted networks
- Remote teams (unless VPN)
- Large scale (100+ users)

**Example Scenario:**
> "Our 5-person dev team wants to share one GiljoAI MCP server in the office. Everyone is on the same network, and we don't need external access."

### WAN Mode ✅

**Best For:**
- Internet-facing deployments
- Remote teams across geographies
- Public API services
- Medium-scale production (10-1000 users)
- Enterprise deployments

**Not Suitable For:**
- Multi-tenant SaaS (use SaaS mode)
- Budget-constrained small teams (use LAN)
- Local-only access (use LAN)

**Example Scenario:**
> "Our company has 50 developers across 3 countries. We need secure internet access to GiljoAI MCP from anywhere."

### SaaS/Hosted Mode ✅ (Future)

**Best For:**
- Multi-tenant SaaS offerings
- Large-scale production (1000+ users)
- Multiple companies/organizations
- Global deployment
- Managed service providers

**Not Suitable For:**
- Small teams (overhead too high)
- On-premises requirements
- Cost-sensitive deployments

**Example Scenario:**
> "We're building a SaaS platform where multiple companies can sign up and use GiljoAI MCP with their own isolated environments."

---

## Authentication Comparison

### Login Flow

| Mode | Dashboard Login | MCP Tool/CLI Access |
|------|-----------------|---------------------|
| **LOCALHOST** | No login required | No authentication |
| **LAN** | Username/Password → JWT cookie | Personal API key in header |
| **WAN** | Username/Password → JWT cookie (HTTPS) | Personal API key in header |
| **SaaS** | OAuth2 or Username/Password → JWT | Personal API key in header |

### User Lifecycle

| Step | LOCALHOST | LAN | WAN | SaaS |
|------|-----------|-----|-----|------|
| **First User** | N/A | Admin via Setup Wizard | Admin via Setup Wizard | OAuth signup or invite |
| **Add Users** | N/A | Admin creates in dashboard | Admin creates in dashboard | Self-signup or company admin |
| **User Login** | N/A | Username/Password | Username/Password | OAuth2 or Username/Password |
| **API Key Gen** | N/A | User dashboard → Settings → API Keys | User dashboard → Settings → API Keys | User dashboard → Settings → API Keys |
| **Revoke Access** | N/A | Admin disables user or user revokes key | Admin disables user or user revokes key | Company admin or user revokes |

---

## Migration Paths

### Localhost → LAN

**Difficulty:** ⭐ Easy
**Time:** 15-30 minutes
**Downtime:** 5-10 minutes
**Key Changes:**
- ✅ Run Setup Wizard
- ✅ Create admin account
- ✅ Update config.yaml (mode: lan, host: 0.0.0.0)
- ✅ Configure firewall rules
- ✅ Test from LAN device

**See:** Section in `NETWORK_AUTHENTICATION_ARCHITECTURE.md`

### LAN → WAN

**Difficulty:** ⭐⭐⭐ Moderate to Advanced
**Time:** 2-4 hours
**Downtime:** 30 min - 2 hours (or zero with parallel deployment)
**Key Changes:**
- ✅ Obtain domain name + DNS
- ✅ Obtain SSL certificate (Let's Encrypt or commercial)
- ✅ Configure reverse proxy (nginx/Caddy/IIS)
- ✅ Enable HTTPS/TLS
- ✅ Add WAF/DDoS protection
- ✅ Enhanced rate limiting
- ✅ Firewall hardening

**See:** `LAN_TO_WAN_MIGRATION.md`

### WAN → SaaS

**Difficulty:** ⭐⭐⭐⭐⭐ Expert
**Time:** Days to weeks
**Downtime:** Minimal (gradual rollout)
**Key Changes:**
- ✅ Implement multi-tenancy (tenant_key isolation)
- ✅ Add OAuth2 providers (Google, GitHub, Microsoft)
- ✅ Billing & subscription management
- ✅ Usage quotas per plan
- ✅ Company/team management
- ✅ Deploy to multiple regions
- ✅ Advanced monitoring and compliance

**See:** `WAN_ARCHITECTURE.md` (future sections)

---

## Security Model Comparison

### Threat Model

| Threat | LOCALHOST | LAN | WAN | SaaS |
|--------|-----------|-----|-----|------|
| **Network Eavesdropping** | ✅ Protected (localhost) | ⚠️ Medium risk (unencrypted LAN) | ✅ Protected (HTTPS) | ✅ Protected (HTTPS + CDN) |
| **Unauthorized Access** | ⚠️ Physical access = full access | ✅ User auth + API keys | ✅ User auth + API keys + rate limiting | ✅ Enhanced auth + MFA |
| **Brute Force Attacks** | N/A | ⚠️ Possible (need fail2ban) | ✅ Protected (rate limit + fail2ban) | ✅ Protected (advanced detection) |
| **DDoS Attacks** | N/A | ⚠️ Vulnerable (LAN saturation) | ✅ Protected (WAF + CloudFlare) | ✅ Protected (enterprise CDN) |
| **Data Breaches** | ⚠️ Local backups needed | ⚠️ LAN backups recommended | ✅ Encrypted backups + offsite | ✅ Encrypted + multi-region |
| **Insider Threats** | N/A | ✅ Per-user audit logs | ✅ Per-user audit logs | ✅ Comprehensive audit + compliance |

### Defense Layers

| Layer | LOCALHOST | LAN | WAN | SaaS |
|-------|-----------|-----|-----|------|
| **Network Security** | localhost binding | Firewall (LAN ports) | Firewall + WAF + DDoS | Enterprise WAF + CDN + DDoS |
| **Transport Security** | N/A | ⚠️ Optional TLS | ✅ HTTPS/TLS (mandatory) | ✅ HTTPS/TLS (enforced) |
| **Authentication** | None | Username/Password + API keys | Username/Password + API keys | OAuth2 + MFA + API keys |
| **Authorization** | Full access | Role-based (Admin/Dev/Viewer) | Role-based (Admin/Dev/Viewer) | Custom RBAC + tenant isolation |
| **Session Security** | N/A | JWT (httpOnly cookies) | JWT + CSRF tokens | JWT + Refresh tokens + CSRF |
| **Data Encryption** | ❌ No | Database optional | Database + Backups | Database + Backups + At-rest |
| **Audit Logging** | ❌ No | ✅ Per-user actions | ✅ Comprehensive | ✅ Compliance-grade |

---

## Quick Decision Tree

```
START: What is your deployment scenario?

┌─ Single developer, local machine?
│  └─> LOCALHOST MODE ✅
│
├─ Small team (3-10), same office network?
│  ├─ Need remote access?
│  │  ├─ No → LAN MODE ✅
│  │  └─ Yes → Consider WAN MODE (or VPN + LAN)
│  └─> LAN MODE ✅
│
├─ Remote team, need internet access?
│  ├─ < 100 users?
│  │  └─> WAN MODE ✅
│  ├─ 100-1000 users?
│  │  └─> WAN MODE ✅ (with HA setup)
│  └─ > 1000 users?
│     └─> Consider SaaS MODE (or WAN with multi-region)
│
└─ Multiple companies/tenants?
   └─> SaaS MODE ✅ (future)
```

---

## Feature Availability Timeline

| Feature | LOCALHOST | LAN | WAN | SaaS |
|---------|-----------|-----|-----|------|
| **Basic Functionality** | ✅ Available | ✅ Available | ✅ Available | 🔮 Planned |
| **User Accounts** | N/A | ✅ Available (new) | ✅ Available | 🔮 Planned |
| **Personal API Keys** | N/A | ✅ Available (new) | ✅ Available | 🔮 Planned |
| **JWT Authentication** | N/A | ✅ Available (new) | ✅ Available | 🔮 Planned |
| **HTTPS/TLS** | N/A | ⚠️ Manual setup | ✅ Available | 🔮 Planned |
| **Reverse Proxy** | N/A | ⚠️ Manual setup | ✅ Available | 🔮 Planned |
| **WAF/DDoS Protection** | N/A | ❌ Not needed | ✅ Available (CloudFlare) | 🔮 Planned |
| **OAuth2 Integration** | N/A | ❌ No | ❌ No (future) | 🔮 Planned |
| **Multi-Tenancy** | N/A | ❌ No | ❌ No | 🔮 Planned |
| **2FA/MFA** | N/A | 🔮 Future | 🔮 Future | 🔮 Planned |
| **Auto-Scaling** | N/A | ❌ No | ⚠️ Manual | 🔮 Planned |
| **Multi-Region** | N/A | ❌ No | ⚠️ Manual | 🔮 Planned |

**Legend:**
- ✅ Available now
- ⚠️ Possible (manual configuration required)
- ❌ Not applicable/not available
- 🔮 Planned for future release

---

## Configuration Comparison

### config.yaml Differences

**LOCALHOST:**
```yaml
installation:
  mode: localhost

services:
  api:
    host: 127.0.0.1
    port: 7272

security:
  api_key_required: false
  user_accounts: false
```

**LAN:**
```yaml
installation:
  mode: lan

services:
  api:
    host: 0.0.0.0  # Network accessible
    port: 7272

security:
  api_key_required: true
  user_accounts: true
  jwt_auth: true

  jwt:
    algorithm: HS256
    expiry_hours: 24

  cors:
    allowed_origins:
      - http://10.1.0.118:7274
      - http://10.1.0.*:7274
```

**WAN:**
```yaml
installation:
  mode: wan
  environment: production

services:
  api:
    host: 127.0.0.1  # Reverse proxy handles external
    port: 7272

security:
  ssl_enabled: true
  api_key_required: true
  user_accounts: true
  jwt_auth: true

  jwt:
    algorithm: HS256
    expiry_hours: 24
    cookie_secure: true  # HTTPS only

  cors:
    allowed_origins:
      - https://giljo.company.com

  rate_limiting:
    enabled: true
    auth_endpoint: "5/minute"
    api_endpoint: "100/minute"
```

---

## Next Steps by Mode

### After Setting Up LOCALHOST

1. ✅ Test basic functionality
2. ✅ Create a test project
3. ✅ Spawn test agents
4. ✅ Explore MCP tools
5. ⏭️ When ready for team: Migrate to LAN

### After Setting Up LAN

1. ✅ Create admin account (Setup Wizard)
2. ✅ Log in to dashboard
3. ✅ Generate personal API key (Settings → API Keys)
4. ✅ Configure MCP tools with API key
5. ✅ Add team users (Admin → Users → Add New User)
6. ✅ Test from multiple LAN devices
7. ⏭️ When ready for internet: Migrate to WAN

### After Setting Up WAN

1. ✅ Complete security audit
2. ✅ Configure monitoring (Grafana/Prometheus)
3. ✅ Set up automated backups
4. ✅ Test SSL/TLS (ssllabs.com)
5. ✅ Load test the system
6. ✅ Configure WAF rules
7. ✅ Document incident response procedures
8. ⏭️ When ready for multi-tenancy: Plan SaaS migration

---

## Common Questions

### Q: Can I skip LAN and go straight from LOCALHOST to WAN?

**A:** Yes, but **not recommended**. LAN mode helps you:
- Test team collaboration on a trusted network first
- Learn user management and API key distribution
- Validate authentication flows without public exposure
- Debug issues in a controlled environment

### Q: What happens to my data when migrating between modes?

**A:** Data is preserved through migrations:
- Database schema unchanged (same PostgreSQL database)
- Projects, agents, tasks, messages all retained
- Only configuration changes (auth, network binding, security settings)

### Q: Can I run LAN mode without user accounts (like the old single API key approach)?

**A:** No. The new architecture requires per-user authentication for:
- Security: Individual accountability and audit trails
- Collaboration: Multiple users with different permissions
- Scalability: Foundation for WAN and SaaS modes

### Q: How many API keys can each user have?

**A:** Up to 5 keys per user (configurable). Users can have different keys for:
- Laptop/Desktop
- CI/CD pipeline
- Mobile device
- Testing environment
- Backup key

### Q: What if I lose my API key?

**A:**
1. Log in to dashboard with username/password
2. Go to Settings → API Keys
3. Revoke lost key
4. Generate new key
5. Update MCP tool configuration

### Q: Can I use OAuth2 in LAN mode?

**A:** Not currently. OAuth2 is planned for WAN/SaaS modes. LAN uses username/password authentication.

---

## Summary

**Choose Your Mode:**

| Scenario | Recommended Mode | Key Reason |
|----------|------------------|------------|
| Solo developer, learning | LOCALHOST | No setup, instant start |
| Small team, same office | LAN | Team collaboration, minimal cost |
| Remote team, internet access | WAN | Secure internet deployment |
| SaaS product, multi-tenant | SaaS (future) | Scalable multi-tenancy |

**Migration Path:**
```
LOCALHOST → LAN → WAN → SaaS
(5 min)    (30 min) (4 hours) (days)
```

**For More Details:**
- Complete architecture: `NETWORK_AUTHENTICATION_ARCHITECTURE.md`
- LAN setup: `LAN_DEPLOYMENT_GUIDE.md`
- WAN setup: `WAN_DEPLOYMENT_GUIDE.md`
- Migration guide: `LAN_TO_WAN_MIGRATION.md`

---

**Document Status:** Production Ready
**Version:** 2.0
**Last Updated:** 2025-10-07
**Next Review:** After SaaS mode implementation
