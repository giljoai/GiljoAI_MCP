# LAN Authentication - Deployment Checklist

**Version:** 1.0.0
**Last Updated:** 2025-10-07
**Audience:** DevOps Engineers, System Administrators

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Security Checklist](#security-checklist)
3. [Post-Deployment Verification](#post-deployment-verification)
4. [Production Hardening](#production-hardening)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)
6. [Rollback Procedures](#rollback-procedures)

---

## Pre-Deployment Checklist

### Database Setup

- [ ] **PostgreSQL 18 installed and running**
  ```bash
  psql --version  # Should be 18.x
  sudo systemctl status postgresql
  ```

- [ ] **Database migration applied**
  ```bash
  alembic current  # Should show: 11b1e4318444 (head)
  alembic upgrade head  # Apply if needed
  ```

- [ ] **Tables created successfully**
  ```bash
  psql -U postgres -d giljo_mcp -c "\dt"
  # Should show: users, api_keys (among others)
  ```

- [ ] **Indexes verified**
  ```bash
  psql -U postgres -d giljo_mcp -c "\di"
  # Should show: idx_user_tenant, idx_apikey_hash, etc.
  ```

### Configuration

- [ ] **config.yaml mode set correctly**
  ```yaml
  installation:
    mode: lan  # or 'server' (not 'localhost')
  ```

- [ ] **API binding configured for network access**
  ```yaml
  services:
    api:
      host: 0.0.0.0  # Not 127.0.0.1
      port: 7272
  ```

- [ ] **CORS origins configured**
  ```yaml
  security:
    cors:
      allowed_origins:
        - http://192.168.1.100:7274  # Your server IP
        - http://your-domain.com:7274
  ```

- [ ] **Authentication required for LAN mode**
  ```yaml
  security:
    api_keys:
      require_for_modes:
        - lan
        - server
        - wan
  ```

### Environment Variables

- [ ] **JWT_SECRET set (32+ characters)**
  ```bash
  # Linux/Mac
  export JWT_SECRET="your_very_long_random_secret_key_here_at_least_32_chars"

  # Windows PowerShell
  $env:JWT_SECRET = "your_very_long_random_secret_key_here_at_least_32_chars"
  ```

- [ ] **DATABASE_URL configured**
  ```bash
  export DATABASE_URL="postgresql://giljo_user:PASSWORD@localhost:5432/giljo_mcp"
  ```

- [ ] **Environment file secured (.env with proper permissions)**
  ```bash
  chmod 600 .env  # Owner read/write only
  ```

### First Admin User

- [ ] **Admin user created**
  ```bash
  # Via installer
  python installer/cli/install.py

  # Or verify existing
  psql -U postgres -d giljo_mcp -c "SELECT username, role FROM users WHERE role='admin';"
  ```

- [ ] **Admin password secure (12+ chars, complex)**

- [ ] **Admin can log in successfully**
  ```bash
  curl -X POST http://localhost:7272/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"YOUR_PASSWORD"}'
  ```

---

## Security Checklist

### Network Security

- [ ] **Firewall configured**
  ```bash
  # Allow API port (7272)
  sudo ufw allow 7272/tcp

  # Allow Frontend port (7274)
  sudo ufw allow 7274/tcp

  # Deny PostgreSQL from external (5432 localhost only)
  sudo ufw deny 5432/tcp
  ```

- [ ] **PostgreSQL accepts localhost only**
  ```bash
  # Check pg_hba.conf
  sudo cat /etc/postgresql/18/main/pg_hba.conf | grep -v "^#"
  # Should show: host all all 127.0.0.1/32 md5 (or similar)
  ```

- [ ] **API server binding verified**
  ```bash
  netstat -tuln | grep 7272
  # Should show: 0.0.0.0:7272 (not 127.0.0.1:7272)
  ```

### Authentication Security

- [ ] **Localhost bypass disabled for network access**
  - Config mode = `lan` or `server`
  - Server binding = `0.0.0.0`
  - Test from remote machine should require auth

- [ ] **JWT secret is strong (32+ chars, random)**
  ```bash
  echo $JWT_SECRET | wc -c  # Should be >= 32
  ```

- [ ] **Password hashing verified**
  ```bash
  psql -U postgres -d giljo_mcp -c "SELECT username, password_hash FROM users LIMIT 1;"
  # password_hash should start with $2b$ (bcrypt)
  ```

- [ ] **API keys hashed in database**
  ```bash
  psql -U postgres -d giljo_mcp -c "SELECT name, key_hash, key_prefix FROM api_keys LIMIT 1;"
  # key_hash should start with $2b$ (bcrypt)
  # key_prefix should be gk_... (first 12 chars only)
  ```

### HTTPS/TLS (Production)

- [ ] **Reverse proxy configured (nginx/Apache)**
  - SSL certificate installed
  - HTTPS redirect enabled
  - Proxy to API backend (port 7272)
  - Proxy to frontend (port 7274)

- [ ] **SSL certificate valid**
  ```bash
  openssl s_client -connect YOUR_DOMAIN:443 -servername YOUR_DOMAIN
  # Check expiration date
  ```

- [ ] **Secure cookie flag enabled (HTTPS only)**
  ```python
  # In api/endpoints/auth.py
  response.set_cookie(
      key="access_token",
      value=token,
      secure=True,  # MUST be True for production HTTPS
      httponly=True,
      samesite="strict"
  )
  ```

### CORS Security

- [ ] **CORS origins explicitly listed (no wildcards)**
  ```yaml
  # BAD: ["*"]
  # GOOD:
  security:
    cors:
      allowed_origins:
        - https://your-domain.com
        - https://192.168.1.100:7274
  ```

- [ ] **Test CORS preflight**
  ```bash
  curl -X OPTIONS http://YOUR_IP:7272/api/auth/login \
    -H "Origin: http://unauthorized.com" \
    -H "Access-Control-Request-Method: POST"
  # Should NOT return CORS headers
  ```

### Rate Limiting

- [ ] **Rate limiting enabled**
  ```yaml
  security:
    rate_limiting:
      enabled: true
      requests_per_minute: 60
  ```

- [ ] **Rate limiting tested**
  ```bash
  # Send 65 requests in 1 minute
  for i in {1..65}; do
    curl http://YOUR_IP:7272/api/projects -H "X-API-Key: gk_test" &
  done
  # Should see 429 Too Many Requests after limit
  ```

---

## Post-Deployment Verification

### API Server Health

- [ ] **API server running**
  ```bash
  curl http://YOUR_IP:7272/api/health
  # Should return: {"status":"healthy"}
  ```

- [ ] **API docs accessible**
  - Open: http://YOUR_IP:7272/docs
  - Should show Swagger UI with auth endpoints

- [ ] **Database connectivity confirmed**
  ```bash
  curl http://YOUR_IP:7272/api/health/db
  # Should return: {"database":"connected"}
  ```

### Authentication Tests

- [ ] **Login works from localhost**
  ```bash
  curl -X POST http://127.0.0.1:7272/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"YOUR_PASSWORD"}' \
    -c cookies.txt
  # Should return: {"message":"Login successful",...}
  ```

- [ ] **Login works from LAN client**
  ```bash
  # From another machine on LAN
  curl -X POST http://YOUR_SERVER_IP:7272/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"YOUR_PASSWORD"}' \
    -c cookies.txt
  # Should return: {"message":"Login successful",...}
  ```

- [ ] **JWT cookie authentication works**
  ```bash
  curl http://YOUR_IP:7272/api/auth/me -b cookies.txt
  # Should return user profile
  ```

- [ ] **API key generation works**
  ```bash
  curl -X POST http://YOUR_IP:7272/api/auth/api-keys \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d '{"name":"Test Key","permissions":["*"]}'
  # Should return: {"api_key":"gk_...","message":"..."}
  ```

- [ ] **API key authentication works**
  ```bash
  curl http://YOUR_IP:7272/api/projects \
    -H "X-API-Key: gk_your_generated_key"
  # Should return projects list
  ```

- [ ] **Unauthenticated requests blocked**
  ```bash
  # From LAN client (not localhost)
  curl http://YOUR_SERVER_IP:7272/api/projects
  # Should return: 401 Unauthorized
  ```

- [ ] **Localhost bypass works (if enabled)**
  ```bash
  # From server itself
  curl http://127.0.0.1:7272/api/projects
  # Should work WITHOUT authentication (if mode=localhost)
  ```

### Frontend Tests

- [ ] **Frontend accessible from LAN**
  - Open: http://YOUR_SERVER_IP:7274
  - Should load login page

- [ ] **Login page works**
  - Enter admin credentials
  - Should redirect to dashboard

- [ ] **Dashboard loads with user info**
  - Should show username in top-right
  - Should show role badge

- [ ] **API key manager accessible**
  - Navigate to Settings → API Keys
  - Should show existing keys (if any)

- [ ] **API key generation via UI works**
  - Click "Generate New Key"
  - Enter name and permissions
  - Should show plaintext key once

- [ ] **Logout works**
  - Click user menu → Logout
  - Should redirect to login page
  - Cookie should be cleared

### MCP Tools Integration

- [ ] **MCP client can authenticate**
  ```bash
  # Configure claude.json with API key
  # Test MCP connection
  ```

- [ ] **MCP tools can access API**
  - Create project via MCP
  - Should succeed with API key auth

- [ ] **MCP tools update last_used timestamp**
  ```bash
  psql -U postgres -d giljo_mcp -c "SELECT name, last_used FROM api_keys;"
  # Should show recent timestamp
  ```

---

## Production Hardening

### Security Enhancements

- [ ] **Reverse proxy configured (nginx/Apache)**
  ```nginx
  server {
      listen 443 ssl http2;
      server_name your-domain.com;

      ssl_certificate /path/to/fullchain.pem;
      ssl_certificate_key /path/to/privkey.pem;
      ssl_protocols TLSv1.2 TLSv1.3;
      ssl_ciphers HIGH:!aNULL:!MD5;

      # API proxy
      location /api/ {
          proxy_pass http://127.0.0.1:7272/api/;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }

      # Frontend proxy
      location / {
          proxy_pass http://127.0.0.1:7274/;
          proxy_set_header Host $host;
      }
  }
  ```

- [ ] **Security headers configured**
  ```nginx
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  ```

- [ ] **Rate limiting at reverse proxy**
  ```nginx
  limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;

  location /api/auth/login {
      limit_req zone=api_limit burst=5 nodelay;
      proxy_pass http://127.0.0.1:7272;
  }
  ```

### Monitoring Setup

- [ ] **Logging configured**
  ```yaml
  # config.yaml
  logging:
    level: INFO
    file: /var/log/giljo-mcp/api.log
  ```

- [ ] **Failed login attempts logged**
  ```bash
  tail -f /var/log/giljo-mcp/api.log | grep "Login failed"
  ```

- [ ] **API key usage logged**
  ```bash
  tail -f /var/log/giljo-mcp/api.log | grep "API key"
  ```

- [ ] **Health check endpoint monitored**
  ```bash
  # Add to monitoring system (Prometheus, Datadog, etc.)
  curl http://127.0.0.1:7272/api/health
  ```

### Backup and Recovery

- [ ] **Database backups automated**
  ```bash
  # Daily backup cron job
  0 2 * * * pg_dump -U postgres giljo_mcp > /backups/giljo_mcp_$(date +\%Y\%m\%d).sql
  ```

- [ ] **Backup retention policy configured**
  - Keep daily backups for 7 days
  - Keep weekly backups for 1 month
  - Keep monthly backups for 1 year

- [ ] **Restore procedure tested**
  ```bash
  # Test restore on staging environment
  psql -U postgres -d giljo_mcp_test < /backups/giljo_mcp_20251007.sql
  ```

- [ ] **Configuration files backed up**
  ```bash
  tar -czf /backups/giljo-config-$(date +\%Y\%m\%d).tar.gz \
    config.yaml .env
  ```

---

## Monitoring and Maintenance

### Daily Checks

- [ ] **API server uptime**
  ```bash
  systemctl status giljo-api
  ```

- [ ] **Database connections**
  ```bash
  psql -U postgres -d giljo_mcp -c "SELECT count(*) FROM pg_stat_activity;"
  ```

- [ ] **Disk space**
  ```bash
  df -h /var/lib/postgresql  # Database directory
  df -h /var/log/giljo-mcp    # Log directory
  ```

### Weekly Checks

- [ ] **Review failed login attempts**
  ```bash
  grep "Login failed" /var/log/giljo-mcp/api.log | wc -l
  ```

- [ ] **Review API key usage**
  ```bash
  psql -U postgres -d giljo_mcp -c "
    SELECT name, last_used
    FROM api_keys
    WHERE is_active = true
    ORDER BY last_used DESC;
  "
  ```

- [ ] **Check inactive users**
  ```bash
  psql -U postgres -d giljo_mcp -c "
    SELECT username, last_login
    FROM users
    WHERE is_active = true
    ORDER BY last_login ASC;
  "
  ```

### Monthly Checks

- [ ] **Review and revoke unused API keys**
  ```bash
  # Keys not used in 90 days
  psql -U postgres -d giljo_mcp -c "
    SELECT id, name, last_used
    FROM api_keys
    WHERE last_used < NOW() - INTERVAL '90 days'
    AND is_active = true;
  "
  ```

- [ ] **Audit user accounts**
  - Remove inactive users
  - Verify role assignments
  - Confirm email addresses

- [ ] **Update SSL certificates (if expiring)**
  ```bash
  certbot renew --dry-run
  ```

### Quarterly Checks

- [ ] **Password rotation reminder (users)**

- [ ] **Update dependencies**
  ```bash
  pip list --outdated
  npm outdated
  ```

- [ ] **Security audit**
  - Review access logs
  - Check for suspicious activity
  - Update security policies

---

## Rollback Procedures

### Scenario 1: Auth System Issues

**Symptoms:**
- Users cannot log in
- API keys not working
- 500 errors on auth endpoints

**Rollback Steps:**

1. **Switch to localhost mode (emergency bypass)**
   ```yaml
   # config.yaml
   installation:
     mode: localhost  # Temporarily disable auth
   ```

2. **Restart API server**
   ```bash
   sudo systemctl restart giljo-api
   ```

3. **Verify localhost access works**
   ```bash
   curl http://127.0.0.1:7272/api/projects
   # Should work without auth
   ```

4. **Investigate root cause**
   ```bash
   tail -100 /var/log/giljo-mcp/api.log
   ```

5. **Fix issue and re-enable LAN mode**

### Scenario 2: Database Migration Failure

**Symptoms:**
- Users/APIKeys tables missing
- Auth endpoints return 500 errors
- Database schema errors

**Rollback Steps:**

1. **Restore database from backup**
   ```bash
   psql -U postgres -d giljo_mcp < /backups/giljo_mcp_LATEST.sql
   ```

2. **Check Alembic migration status**
   ```bash
   alembic current
   alembic history
   ```

3. **Rollback migration if needed**
   ```bash
   alembic downgrade -1  # Go back one migration
   ```

4. **Verify database state**
   ```bash
   psql -U postgres -d giljo_mcp -c "\dt"
   ```

5. **Re-apply migration with fixes**
   ```bash
   alembic upgrade head
   ```

### Scenario 3: Lost Admin Password

**Recovery Steps:**

1. **Access server with PostgreSQL access**

2. **Reset admin password directly**
   ```python
   python3 <<EOF
   from passlib.hash import bcrypt
   import psycopg2

   new_password = "new_secure_password123"
   password_hash = bcrypt.hash(new_password)

   conn = psycopg2.connect(
       host="localhost",
       database="giljo_mcp",
       user="postgres",
       password="4010"
   )
   cur = conn.cursor()
   cur.execute(
       "UPDATE users SET password_hash = %s WHERE username = 'admin'",
       (password_hash,)
   )
   conn.commit()
   print("Admin password reset successfully")
   EOF
   ```

3. **Test new password**
   ```bash
   curl -X POST http://localhost:7272/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"new_secure_password123"}'
   ```

---

## Deployment Sign-Off

**Deployment Date:** _______________

**Deployed By:** _______________

**Verification Checklist:**

- [ ] All pre-deployment checks passed
- [ ] All security checks passed
- [ ] All post-deployment tests passed
- [ ] Production hardening complete
- [ ] Monitoring configured
- [ ] Backups verified
- [ ] Rollback procedures documented
- [ ] Team trained on new auth system
- [ ] Documentation updated

**Sign-Off:**

- **System Administrator:** _______________ Date: _______________
- **Security Lead:** _______________ Date: _______________
- **Development Lead:** _______________ Date: _______________

---

## Additional Resources

- **[User Guide](LAN_AUTH_USER_GUIDE.md)** - End-user documentation
- **[Architecture](LAN_AUTH_ARCHITECTURE.md)** - Technical design
- **[API Reference](LAN_AUTH_API_REFERENCE.md)** - API documentation
- **[Migration Guide](LAN_AUTH_MIGRATION_GUIDE.md)** - Upgrade instructions
- **[Test Report](LAN_AUTH_TEST_REPORT.md)** - Testing results

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-07
**Maintained By:** Documentation Manager Agent
