# Demo Server Preparation - Security Recommendations

**Edition Scope:** CE
**Date:** 2026-03-26
**Status:** Recommendation

## Context

This Ubuntu PC will serve as a public-facing demo/trial server. Users will create accounts via the web frontend, which redirects them into a new demo session (expiring after ~5 days). All components (frontend, backend API, PostgreSQL) run on the same machine.

## Architecture

```
Internet --> Web Frontend (port 443) --> Backend API --> PostgreSQL (localhost:5432)
                                       all on this PC
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

### 4. Demo Session Expiry

- Session lifetime TBD (~5 days under consideration)
- Implement a scheduled cleanup job to purge expired demo data
- Consider rate-limiting account creation to prevent abuse

### 5. pg_hba.conf Configuration

```
# Admin: local sudo only
local   all             postgres                                peer

# App roles: password over TCP, localhost only
host    giljo_db        giljo_owner     127.0.0.1/32            scram-sha-256
host    giljo_db        giljo_user      127.0.0.1/32            scram-sha-256

# Reject everything else
host    all             all             0.0.0.0/0               reject
```

## Conclusion

The existing installer security model is solid. The main action items for demo server deployment are firewall configuration, verifying PostgreSQL listens on localhost only, and implementing session expiry cleanup.
