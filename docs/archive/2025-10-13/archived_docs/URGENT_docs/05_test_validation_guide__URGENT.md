# CLI Installation Test Guide

## Overview

Step-by-step test scenarios for validating the CLI installation system. Both localhost and server modes must be thoroughly tested.

## Pre-Test Setup

### Environment Requirements
- [ ] Clean test environment
- [ ] PostgreSQL 18 NOT installed (for full test)
- [ ] Python 3.10+ installed
- [ ] Admin/sudo access available
- [ ] Network access for server mode tests

### Test Preparation
```bash
# Create test directory
mkdir test_install
cd test_install

# Get installer
git clone https://github.com/giljoai/mcp.git
cd mcp
```

## Test Scenario 1: Localhost Installation

### 1.1 Interactive Mode - Fresh Install
```bash
python install.py
```

**Expected Prompts:**
```
Installation mode [localhost/server]: localhost
PostgreSQL host [localhost]: <enter>
PostgreSQL port [5432]: <enter>
```

**Validation Points:**
- [ ] PostgreSQL detection works
- [ ] If missing, shows download link
- [ ] Prompts are clear and have defaults
- [ ] Progress shows real operations

### 1.2 Database Creation - Direct Path
**With Admin Access:**
```
PostgreSQL admin password: ****
```

**Expected:**
- Database created directly
- Roles created (giljo_owner, giljo_user)
- Migrations run automatically
- .env and config.yaml generated

**Verify:**
```bash
# Check database exists
PGPASSWORD=<admin_pass> psql -U postgres -l | grep giljo_mcp

# Check config files
ls -la .env config.yaml

# Check permissions (Unix)
stat -c %a .env  # Should be 600
```

### 1.3 Database Creation - Fallback Path
**Without Admin Access:**
```
# When prompted for admin password, press Ctrl+C
# Or enter wrong password
```

**Expected:**
- Script generated: `installer/scripts/create_db.ps1` or `.sh`
- Clear instructions shown
- Waits for user to run script

**Test Fallback:**
```bash
# Windows (Admin PowerShell)
.\installer\scripts\create_db.ps1

# Linux/macOS
sudo bash installer/scripts/create_db.sh
```

**Then:**
- Press Enter in installer to continue
- Installer verifies and completes

### 1.4 Immediate Launch Test
```bash
# Immediately after installation
python start_giljo.py
```

**Expected:**
- No configuration prompts
- Services start in order
- Browser opens automatically
- All services accessible

**Verify Services:**
```bash
# Check API
curl http://localhost:8000/health

# Check Dashboard
curl http://localhost:3000

# Check database connection
PGPASSWORD=<from_env> psql -U giljo_user -d giljo_mcp -c "SELECT 1"
```

## Test Scenario 2: Server Mode Installation

### 2.1 Interactive Server Setup
```bash
python install.py --mode server
```

**Expected Prompts:**
```
PostgreSQL host [localhost]: <enter>
PostgreSQL port [5432]: <enter>
PostgreSQL admin password: ****

Network Configuration:
  Bind address [0.0.0.0]: <enter>
  ⚠️  WARNING: Server will be accessible over network!
  Continue with network exposure? [y/N]: y

Enable SSL/TLS? [y/N]: y
SSL certificate [self-signed/existing]: self-signed

Admin User Configuration:
  Username [admin]: admin
  Password: ****
  Confirm: ****

Generate API key for programmatic access? [Y/n]: y
```

**Validation:**
- [ ] Network warning shown clearly
- [ ] SSL strongly recommended
- [ ] Self-signed cert generated
- [ ] API key displayed once
- [ ] Firewall rules generated

### 2.2 Firewall Rules
**Expected Output:**
```
🔥 Firewall Configuration Required
================================

Windows Firewall (run as Administrator):
netsh advfirewall firewall add rule ...

Linux (UFW):
sudo ufw allow 8000/tcp comment 'GiljoAI MCP API'
...

📝 Rules saved to: firewall_rules.txt
```

**Test Application:**
```bash
# Apply one firewall rule
# Test remote connection from another machine
curl http://<server_ip>:8000/health
```

### 2.3 SSL Verification
```bash
# Start with SSL
python start_giljo.py

# Expected: Services start with HTTPS
# Browser warning for self-signed cert (normal)
```

**Test HTTPS:**
```bash
# Allow self-signed cert
curl -k https://localhost:8000/health
```

### 2.4 API Key Authentication
```bash
# Test without key (should fail)
curl http://localhost:8000/api/agents

# Test with key (should work)
curl -H "X-API-Key: gai_<key_from_install>" http://localhost:8000/api/agents
```

## Test Scenario 3: Batch Mode

### 3.1 Localhost Batch
```bash
python install.py \
  --mode localhost \
  --pg-password admin123 \
  --batch
```

**Expected:**
- No interactive prompts
- Uses defaults for unspecified options
- Completes silently
- Exit code 0 on success

### 3.2 Server Batch
```bash
python install.py \
  --mode server \
  --bind 192.168.1.100 \
  --pg-password admin123 \
  --admin-username admin \
  --admin-password secure123 \
  --enable-ssl \
  --batch
```

**Validation:**
- [ ] No prompts
- [ ] SSL cert generated
- [ ] Config reflects all options

## Test Scenario 4: Error Handling

### 4.1 Port Conflict
```bash
# Start blocking service
python -m http.server 8000 &

# Try to launch
python start_giljo.py
```

**Expected:**
- Detects port 8000 in use
- Offers alternative (8001)
- Updates config if accepted
- Continues with new port

### 4.2 PostgreSQL Down
```bash
# Stop PostgreSQL
sudo systemctl stop postgresql-18  # Linux
net stop postgresql-x64-18         # Windows

# Try to launch
python start_giljo.py
```

**Expected:**
- Detects database down
- Attempts to start PostgreSQL
- If can't start, provides clear error

### 4.3 Missing Configuration
```bash
# Remove config file
rm config.yaml

# Try to launch
python start_giljo.py
```

**Expected:**
- Detects missing config
- Tells user to run installer
- Exits cleanly

## Test Scenario 5: Cross-Platform

### 5.1 Windows Specific
```powershell
# Run installer
python install.py

# Check script generation
ls installer\scripts\create_db.ps1

# Test launcher
.\start_giljo.bat
```

### 5.2 Linux Specific
```bash
# Run installer
python install.py

# Check script permissions
ls -la installer/scripts/create_db.sh

# Test launcher
./start_giljo.sh
```

### 5.3 macOS Specific
```bash
# With Homebrew PostgreSQL
python install.py

# Test launcher
./start_giljo.sh
```

## Performance Tests

### Installation Time
```bash
time python install.py --mode localhost --batch
```
**Target:** < 5 minutes

### Launch Time
```bash
time python start_giljo.py
```
**Target:** < 30 seconds

### Resource Usage
Monitor during install:
- Memory: < 500MB
- CPU: < 50% average
- Disk: < 1GB total

## Test Report Template

```markdown
# Installation Test Report

Date: _______
Tester: _______
Platform: _______

## Test Results

### Scenario 1: Localhost Installation
- [ ] Interactive mode works
- [ ] Database creation (direct) works
- [ ] Database creation (fallback) works
- [ ] Immediate launch works
**Notes:** _______

### Scenario 2: Server Mode
- [ ] Network configuration works
- [ ] SSL setup works
- [ ] API key auth works
- [ ] Firewall rules generated
**Notes:** _______

### Scenario 3: Batch Mode
- [ ] Localhost batch works
- [ ] Server batch works
**Notes:** _______

### Scenario 4: Error Handling
- [ ] Port conflict handled
- [ ] Database down handled
- [ ] Missing config detected
**Notes:** _______

### Scenario 5: Cross-Platform
- [ ] Windows works
- [ ] Linux works
- [ ] macOS works
**Notes:** _______

## Performance Metrics
- Installation time: _____ minutes
- Launch time: _____ seconds
- Peak memory: _____ MB

## Issues Found
1. _______
2. _______

## Overall Assessment
[ ] Ready for release
[ ] Minor fixes needed
[ ] Major issues found
```

## Automated Test Script

```python
#!/usr/bin/env python
"""Automated installation tests"""

import subprocess
import time
import os
import pytest

class TestInstallation:
    
    def test_localhost_install(self):
        """Test basic localhost installation"""
        result = subprocess.run([
            'python', 'install.py',
            '--mode', 'localhost',
            '--pg-password', 'test123',
            '--batch'
        ], capture_output=True)
        
        assert result.returncode == 0
        assert os.path.exists('.env')
        assert os.path.exists('config.yaml')
    
    def test_immediate_launch(self):
        """Test launch after install"""
        # Start launcher in background
        proc = subprocess.Popen(['python', 'start_giljo.py'])
        
        # Wait for startup
        time.sleep(10)
        
        # Check services
        import requests
        response = requests.get('http://localhost:8000/health')
        assert response.status_code == 200
        
        # Cleanup
        proc.terminate()
    
    def test_server_mode_config(self):
        """Test server mode configuration"""
        result = subprocess.run([
            'python', 'install.py',
            '--mode', 'server',
            '--bind', '0.0.0.0',
            '--admin-username', 'admin',
            '--admin-password', 'secure123',
            '--pg-password', 'test123',
            '--batch'
        ], capture_output=True)
        
        assert result.returncode == 0
        
        # Check config has server settings
        import yaml
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        assert config['installation']['mode'] == 'server'
        assert config['network']['bind'] == '0.0.0.0'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

## Success Criteria Summary

### Critical Path
- [x] CLI installer works
- [x] Both modes functional
- [x] Database created during install
- [x] Immediate launch capability
- [x] Error recovery works
- [x] Cross-platform support

### Quality Metrics
- [x] < 5 min install (localhost)
- [x] < 10 min install (server)
- [x] < 30 sec launch
- [x] Clear error messages
- [x] Professional output

## Agent Coordination Matrix

| From → To | Handoff | Critical Points |
|-----------|---------|-----------------|
| Orchestrator → Database | PostgreSQL requirements | Version 18, fallback strategy |
| Database → Network | Remote access config | pg_hba.conf, SSL requirements |
| Network → Implementation | Server mode features | SSL paths, API keys |
| Implementation → Testing | Complete installer | Both modes, all platforms |
| Testing → Orchestrator | Test results | Go/no-go decision |

## Communication Protocols

### Task Assignment

task:
  agent: database-specialist
  action: implement-fallback-scripts
  requirements:
    - Windows PowerShell version
    - Linux/macOS bash version
    - Idempotent operations
    - Clear user guidance
  success_criteria:
    - Scripts generated with parameters
    - User can run elevated
    - Installation continues after
Status Reporting
yamlstatus:
  agent: implementation-developer
  phase: localhost-cli
  progress: 75%
  completed:
    - CLI framework
    - Interactive prompts
    - Batch mode
  blocking:
    - None
  next:
    - Configuration generation
    - Launcher creation
Issue Escalation
yamlissue:
  agent: network-engineer
  severity: medium
  description: SSL cert generation failing on Windows
  impact: Server mode without SSL
  recommendation: Use OpenSSL binary or Python cryptography
  decision_needed: true
Quality Standards
All agents must ensure:

No GUI components - CLI only
Two modes only - Localhost and server
PostgreSQL 18 - Single database option
Zero post-install - Must work immediately
Cross-platform - Windows, Linux, macOS
Professional output - Clear, helpful, no emojis
Error recovery - Never fail silently
Security by default - Localhost binding, explicit network consent

Success Metrics
Phase 1 (Localhost)

Database created during install ✓
Fallback scripts work ✓
start_giljo launches immediately ✓

Phase 2 (Server)

Network binding with warnings ✓
SSL optional but recommended ✓
Firewall rules generated ✓

Phase 3 (Polish)

Launch validation complete ✓
Error recovery implemented ✓
Performance targets met ✓