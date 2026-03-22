# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.3.x   | Yes       |
| 3.2.x   | Yes       |
| < 3.2   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to **abuse@giljo.ai**
3. Include a description of the vulnerability, steps to reproduce, and potential impact

## Response Timeline

- **Acknowledgment**: Within 48 hours of report
- **Assessment**: Within 7 days
- **Fix/Mitigation**: Depends on severity (critical: 48h, high: 7 days, medium: 30 days)

## Security Architecture

- **Authentication**: Always enabled, JWT-based with bcrypt password hashing
- **No default credentials**: First user created via `/welcome` setup wizard
- **Multi-tenant isolation**: Per-user tenant keys with database-level filtering
- **API authentication**: `X-API-Key` header for MCP tool access
- **Password reset**: Recovery PIN system with rate limiting
- **WebSocket security**: JWT token required for all connections

## Dependency Security

- Python dependencies are pinned in `requirements.txt`
- Frontend dependencies managed via `package-lock.json`
- Regular security audits via `pip audit` and `npm audit`
