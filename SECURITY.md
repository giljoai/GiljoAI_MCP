# Security Policy

## Security Scanning

This project implements comprehensive security scanning through multiple tools:
- **Bandit**: Python AST security linter
- **Trivy**: Container and dependency vulnerability scanner
- **Pre-commit hooks**: Security checks before code commits

## Intentional Security Exceptions

We have carefully reviewed and intentionally bypass certain security warnings that are false positives or necessary for functionality:

### 1. MD5 Hashing (B324)
**Files**: `src/giljo_mcp/tools/chunking.py`, `src/giljo_mcp/discovery.py`
**Reason**: MD5 is used solely for content deduplication and change detection, NOT for cryptographic security. We explicitly set `usedforsecurity=False` to indicate this intent.

### 2. Binding to All Interfaces (B104)
**Files**: Multiple server components
**Reason**: As an orchestration server, GiljoAI MCP must be accessible from network interfaces. This is intentional and required functionality. Users should:
- Use firewall rules to restrict access
- Deploy behind a reverse proxy in production
- Use the built-in authentication mechanisms

### 3. Assert Statements (B101)
**Reason**: Used only in development/testing code for debugging. Production deployments should use `python -O` to disable assertions.

### 4. Paramiko (B601)
**Reason**: False positive - we don't actually use Paramiko, but the check sometimes triggers on similar SSH-related code patterns.

## Security Best Practices

### For Developers
- All security exceptions must be documented here
- New exceptions require team review
- Security scans run on every commit via CI/CD
- Critical/High vulnerabilities block deployments

### For Deployment
1. **Network Security**
   - Deploy behind a firewall
   - Use TLS certificates for production
   - Implement rate limiting

2. **Authentication**
   - Use strong API keys (provided by installer)
   - Enable OAuth2 for WAN deployments
   - Rotate keys regularly

3. **Database Security**
   - Use PostgreSQL with SSL for production
   - Implement row-level security for multi-tenant mode
   - Regular backups with encryption

4. **CORS Configuration**
   - **Purpose**: Allows the built-in web dashboard to communicate with the API
   - **NOT for MCP clients**: MCP protocol connections bypass CORS entirely
   - **When to configure**:
     - Local: `http://localhost:*` (dashboard and API on same machine)
     - LAN: `http://192.168.x.x:*` (accessing dashboard from network)
     - WAN/SaaS: `https://dashboard.yourdomain.com` (public deployment)
   - **Security Note**: Only allow origins where you host the dashboard

## Reporting Security Issues

Please report security vulnerabilities to:
- Email: [security contact to be added]
- Do NOT create public GitHub issues for security problems

## Security Scan Results

Current scan status:
- Python Security: ✅ Passing (with documented exceptions)
- Dependency Scan: ✅ Passing
- Frontend Security: ✅ Passing

Last full security audit: 2025-01-24

## Compliance

This project aims to meet:
- OWASP Top 10 mitigation strategies
- CWE/SANS Top 25 awareness
- WCAG 2.1 AA accessibility (which has security benefits)

## Version Support

Security updates are provided for:
- Current release: Full support
- Previous release: Critical security fixes only
- Older versions: No support

---

*This document is part of our commitment to transparent security practices.*