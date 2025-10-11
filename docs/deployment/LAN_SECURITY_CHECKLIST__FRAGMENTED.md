# GiljoAI MCP - LAN Security Checklist

**Version:** 1.0
**Date:** 2025-10-04
**Purpose:** Security validation checklist for LAN deployments
**Applies To:** Phase 1 - Local Area Network deployments only

---

## Overview

This checklist ensures your GiljoAI MCP LAN deployment follows security best practices for trusted network environments. Complete all sections before allowing team access.

**Security Level:** MEDIUM (Trusted LAN Environment)

**Note:** For WAN deployments, see WAN Security Checklist (additional requirements apply).

---

## Pre-Deployment Security Checklist

### System Security

- [ ] **OS Security Updates**
  - All security patches applied
  - Auto-update enabled for critical patches
  - Reboot scheduled for pending updates

- [ ] **User Access Control**
  - Server has dedicated service account (not root/administrator)
  - Service account has minimum required permissions
  - Remote access (SSH/RDP) uses key-based auth or strong passwords

- [ ] **Antivirus/Malware Protection**
  - Up-to-date antivirus installed (if required by policy)
  - Exclusions configured for GiljoAI directories
  - Real-time protection enabled

---

## Network Security

### Firewall Configuration

- [ ] **Host Firewall Enabled**
  - Windows Firewall / UFW / pf enabled
  - Default policy: deny incoming, allow outgoing
  - Explicit rules for GiljoAI ports only

- [ ] **Required Ports Open (LAN only)**
  - [ ] Port 7272/TCP (API)
  - [ ] Port 6003/TCP (WebSocket)
  - [ ] Port 7274/TCP (Dashboard)

- [ ] **PostgreSQL Port Restricted**
  - [ ] Port 5432/TCP accessible ONLY from localhost OR specific LAN IPs
  - [ ] NOT accessible from entire LAN (unless required)

- [ ] **Firewall Rules Tested**
  - Connection from allowed LAN IPs successful
  - Connection from external networks blocked (if edge firewall tested)

### Network Isolation

- [ ] **Network Segmentation**
  - Server on dedicated VLAN (if available)
  - Management network separate from user network (if applicable)

- [ ] **Access Control Lists (ACLs)**
  - Network ACLs configured (if using managed switches)
  - Only required clients can reach server ports

---

## Authentication and Authorization

### API Key Security

- [ ] **API Key Generation**
  - API keys are 32+ characters
  - Generated using cryptographically secure method
  - Keys follow naming convention: `giljo_lan_[random]`

- [ ] **API Key Storage**
  - Server: stored in `.env` file with restricted permissions (600/0600)
  - Clients: stored in user home directory config file
  - Never committed to version control
  - `.gitignore` includes `.env` and API key files

- [ ] **API Key Distribution**
  - Keys distributed via secure channel (encrypted email, password manager)
  - One key per team OR one key per user (document which approach)
  - Key distribution logged

- [ ] **API Key Enforcement**
  - config.yaml has `api_key_required: true`
  - Tested: requests without key are rejected (401)
  - Tested: requests with invalid key are rejected (401)

### Rate Limiting

- [ ] **Rate Limiting Enabled**
  - config.yaml has `rate_limiting: true`
  - `max_requests_per_minute` set appropriately (100 recommended)
  - Burst size configured

- [ ] **Rate Limiting Tested**
  - Exceeded limit results in 429 Too Many Requests
  - Rate limit resets after time window

### Admin Access

- [ ] **Admin Credentials**
  - Admin password is strong (16+ characters, mixed case, symbols)
  - Admin password stored securely (password manager)
  - Admin password NOT shared with regular users

- [ ] **Admin Account Protection**
  - Admin account used only for administration
  - Regular users do NOT have admin credentials

---

## Database Security

### PostgreSQL Configuration

- [ ] **Authentication Method**
  - Using `scram-sha-256` (NOT `md5` or `trust`)
  - Verified in `pg_hba.conf`

- [ ] **Network Access Control**
  - `listen_addresses` configured appropriately:
    - `'localhost'` if API and DB on same server (recommended)
    - Specific IP if API on different server
    - `'*'` ONLY if required, with strict pg_hba.conf rules

- [ ] **pg_hba.conf Rules**
  - Specific LAN subnet configured (e.g., `192.168.0.0/16`)
  - NO `0.0.0.0/0` entries (reject all other connections)
  - Rules tested: allowed IPs can connect, others cannot

### Database Users

- [ ] **Database User Permissions**
  - Application user (`giljo_user`) has minimum required permissions
  - Application user does NOT have SUPERUSER privilege
  - Separate admin user for database administration

- [ ] **Password Security**
  - Strong passwords (16+ characters)
  - Passwords stored in `.env` file only
  - Database password different from admin password

### Database Hardening

- [ ] **Connection Limits**
  - `max_connections` set appropriately (100 recommended)
  - Connection pooling configured in application

- [ ] **Logging Enabled**
  - `log_connections = on`
  - `log_disconnections = on`
  - Connection attempts logged

- [ ] **SSL/TLS (Optional for LAN)**
  - If using SSL: certificates configured
  - If using SSL: `ssl = on` in postgresql.conf
  - If NOT using SSL: documented as acceptable risk for LAN

---

## Application Security

### Configuration Security

- [ ] **config.yaml Permissions**
  - File permissions: 600 (owner read/write only)
  - Contains no sensitive data (passwords in .env)

- [ ] **.env File Permissions**
  - File permissions: 600 (owner read/write only)
  - Contains database password and API key
  - NOT world-readable

- [ ] **Secrets Management**
  - All secrets in `.env` file
  - `.env` file in `.gitignore`
  - No hardcoded secrets in code

### Service Security

- [ ] **Service Account**
  - Service runs as dedicated user (not root/Administrator)
  - Service user has minimum required permissions
  - Service user cannot log in interactively

- [ ] **Service Auto-Start**
  - Service configured to start on boot
  - Service restarts automatically on failure
  - Restart limits configured (prevent restart loops)

### Application Updates

- [ ] **Update Strategy**
  - Update procedure documented
  - Testing environment available
  - Rollback plan documented

---

## Logging and Monitoring

### Log Configuration

- [ ] **Application Logging**
  - Log level: INFO or higher
  - Log file location configured
  - Log rotation enabled (size or time-based)
  - Old logs archived or deleted

- [ ] **Security Event Logging**
  - Failed authentication attempts logged
  - API key usage logged
  - Admin actions logged

- [ ] **Database Logging**
  - Connection events logged
  - Failed login attempts logged
  - Slow queries logged (optional, for performance)

### Log Management

- [ ] **Log File Permissions**
  - Log files have restricted permissions (640)
  - Only service user and admins can read logs

- [ ] **Log Monitoring**
  - Logs reviewed regularly (weekly minimum)
  - Monitoring for:
    - Failed authentication attempts
    - Unusual traffic patterns
    - Error spikes
    - Disk space issues

- [ ] **Log Retention**
  - Retention policy defined (30 days minimum recommended)
  - Old logs archived or securely deleted

---

## Backup and Recovery

### Backup Strategy

- [ ] **Database Backups**
  - Automated backup script created
  - Backup schedule configured (daily recommended)
  - Backup tested (restore verified)

- [ ] **Backup Storage**
  - Backups stored on separate disk/server
  - Backup location has sufficient space
  - Backup files have restricted permissions

- [ ] **Configuration Backups**
  - `config.yaml` backed up
  - `.env` backed up (securely!)
  - PostgreSQL configuration files backed up

### Recovery Plan

- [ ] **Disaster Recovery Documented**
  - Recovery steps documented
  - Recovery tested (at least once)
  - Recovery time objective (RTO) defined

- [ ] **Backup Restoration Tested**
  - Database restore tested successfully
  - Configuration restore tested
  - Full system restore tested (if applicable)

---

## Incident Response

### Incident Response Plan

- [ ] **Security Incident Contacts**
  - Primary contact identified
  - Escalation path defined
  - Contact information documented and accessible

- [ ] **Incident Response Procedures**
  - Steps for suspected security incident documented
  - Include: isolate, investigate, remediate, document
  - Team trained on procedures

### Security Breach Procedures

- [ ] **Immediate Actions Defined**
  - [ ] Disconnect from network
  - [ ] Revoke API keys
  - [ ] Change passwords
  - [ ] Preserve logs
  - [ ] Notify stakeholders

- [ ] **Post-Incident Actions**
  - Root cause analysis process defined
  - Remediation steps documented
  - Lessons learned review process

---

## Compliance and Documentation

### Security Documentation

- [ ] **Security Policy Documented**
  - Acceptable use policy
  - Password policy
  - Access control policy

- [ ] **Network Diagram**
  - LAN topology documented
  - Server IP addresses documented
  - Firewall rules documented

- [ ] **User Documentation**
  - User guide for connecting to server
  - API key usage instructions
  - Troubleshooting guide

### Audit and Compliance

- [ ] **Security Audit Trail**
  - Admin actions logged
  - Configuration changes logged
  - Access logs maintained

- [ ] **Compliance Requirements**
  - Organizational security policies reviewed
  - Industry regulations checked (if applicable)
  - Compliance gaps documented

- [ ] **Regular Reviews**
  - Security review scheduled (quarterly recommended)
  - Checklist re-verification scheduled

---

## LAN-Specific Security Considerations

### Trusted Network Assumptions

- [ ] **Network Perimeter Security**
  - Documented: network has edge firewall
  - Documented: network access is controlled (Wi-Fi passwords, physical access)
  - Documented: network is for trusted users only

- [ ] **Physical Security**
  - Server in secured location (locked room/rack)
  - Server console password-protected
  - Physical access logged (if applicable)

### Optional LAN Security Enhancements

- [ ] **TLS/SSL (Optional)**
  - Decision documented: using or not using TLS
  - If using: certificates configured and tested
  - If not using: documented as acceptable for LAN

- [ ] **Network Monitoring**
  - IDS/IPS deployed (if available)
  - Network traffic monitored
  - Anomaly detection configured

- [ ] **Client Certificate Authentication (Advanced)**
  - Client certificates issued (optional)
  - Certificate validation configured
  - Certificate revocation process defined

---

## Platform-Specific Security

### Windows Security

- [ ] **Windows Defender**
  - Enabled and up-to-date
  - Exclusions configured for GiljoAI directories
  - Real-time protection active

- [ ] **Windows Firewall**
  - Enabled for Domain and Private profiles
  - GiljoAI rules configured
  - Logging enabled

- [ ] **User Account Control (UAC)**
  - UAC enabled
  - Service runs as non-administrator

- [ ] **Windows Updates**
  - Automatic updates configured
  - Update history reviewed

### Linux Security

- [ ] **SELinux/AppArmor**
  - SELinux or AppArmor status documented
  - If enforcing: policies configured for GiljoAI
  - If disabled: documented as organizational decision

- [ ] **UFW/iptables**
  - Firewall enabled
  - Rules configured and tested
  - IPv6 rules configured (if IPv6 used)

- [ ] **System Hardening**
  - Unnecessary services disabled
  - SSH key-based auth (if SSH enabled)
  - Root login disabled (SSH)

- [ ] **Package Updates**
  - unattended-upgrades configured (Debian/Ubuntu)
  - Auto-update for security patches

### macOS Security

- [ ] **Gatekeeper**
  - Gatekeeper enabled
  - App verification active

- [ ] **FileVault**
  - FileVault encryption (optional but recommended)

- [ ] **Application Firewall**
  - Application firewall enabled
  - Python allowed through firewall

- [ ] **System Updates**
  - Auto-update for security patches
  - Update history reviewed

---

## Testing and Validation

### Security Testing

- [ ] **Authentication Testing**
  - [ ] Valid API key: access granted
  - [ ] Invalid API key: access denied (401)
  - [ ] No API key: access denied (401)
  - [ ] Expired API key: access denied (if key expiry implemented)

- [ ] **Network Access Testing**
  - [ ] Server accessible from allowed LAN IPs: SUCCESS
  - [ ] Server accessible from test client on LAN: SUCCESS
  - [ ] PostgreSQL accessible ONLY from allowed IPs: VERIFIED
  - [ ] Firewall blocks unexpected ports: VERIFIED

- [ ] **Rate Limiting Testing**
  - [ ] Excessive requests trigger rate limit: 429 response
  - [ ] Rate limit reset after time window: VERIFIED

### Penetration Testing (Optional)

- [ ] **Internal Scan**
  - Port scan from LAN client
  - Vulnerability scan (Nessus, OpenVAS, etc.)
  - Results reviewed and issues remediated

- [ ] **Authentication Testing**
  - Brute force attack simulation
  - API key guessing attempts
  - Results logged and analyzed

---

## Sign-Off

### Pre-Production Checklist

- [ ] **All checklist items completed**
- [ ] **Security testing passed**
- [ ] **Documentation complete**
- [ ] **Team trained**
- [ ] **Backups verified**

### Approval

**Deployed By:**
- Name: ___________________________
- Date: ___________________________
- Signature: ___________________________

**Reviewed By (Security/IT Manager):**
- Name: ___________________________
- Date: ___________________________
- Signature: ___________________________

### Post-Deployment

- [ ] **Monitoring Configured**
- [ ] **First backup completed successfully**
- [ ] **Client connections verified**
- [ ] **Incident response plan communicated**

---

## Maintenance Schedule

### Regular Security Tasks

**Daily:**
- Review security logs for anomalies

**Weekly:**
- Verify backups completed successfully
- Check for failed authentication attempts
- Review disk space and log rotation

**Monthly:**
- Review firewall rules
- Check for software updates
- Audit user access

**Quarterly:**
- Full security review
- Re-run this checklist
- Update documentation
- Test disaster recovery

**Annually:**
- Rotate API keys
- Change admin passwords
- Security audit by external party (if required)

---

## Common Security Pitfalls to Avoid

1. **Weak API Keys:** Use strong, random keys (32+ characters)
2. **Exposed PostgreSQL:** Ensure port 5432 is NOT accessible from entire LAN unless required
3. **Missing Backups:** Automate and test backups regularly
4. **Ignored Logs:** Review logs for security events
5. **Shared Admin Credentials:** Each admin should have own credentials
6. **No Rate Limiting:** Enable rate limiting to prevent abuse
7. **Hardcoded Secrets:** Always use `.env` file, never hardcode
8. **World-Readable Config Files:** Set strict file permissions (600)
9. **No Monitoring:** Monitor logs and system health
10. **Skipping Updates:** Apply security patches promptly

---

## Additional Resources

- **LAN Deployment Guide:** `docs/deployment/LAN_DEPLOYMENT_GUIDE.md`
- **Server Mode Testing:** `tests/SERVER_MODE_TESTING_STRATEGY.md`
- **Technical Architecture:** `docs/TECHNICAL_ARCHITECTURE.md`
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **CIS Benchmarks:** https://www.cisecurity.org/cis-benchmarks/

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-04 | Initial LAN security checklist | Documentation Manager |

---

**Document Status:** Production Ready
**Next Review:** After first LAN deployment

**End of LAN Security Checklist**
