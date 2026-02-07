# Kickoff: Handover 0709-SECURITY - Security Hardening

**Series:** 0700 Code Cleanup Series
**Risk Level:** MEDIUM
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-06

---

## Mission Statement

Address security-related lint issues. Fix timezone handling, subprocess security, and audit for hardcoded credentials.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0709_SECURITY.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

### Launch Validation Subagent

```
"Validate 0709-SECURITY scope.

```bash
# Security issues (S rules)
ruff check src/ api/ --select S --statistics

# Datetime timezone issues
ruff check src/ api/ --select DTZ --statistics

# Subprocess issues
ruff check src/ api/ --select S603,S607,PLW1510 --statistics

# Hardcoded secrets scan
grep -rn "password\s*=\s*['\"]" src/ api/ --include="*.py" | grep -v test | grep -v "#" | wc -l
grep -rn "api_key\s*=\s*['\"]" src/ api/ --include="*.py" | grep -v test | grep -v "#" | wc -l
```

REPORT: Security issues by severity."
```

---

## PHASE 1: EXECUTION PRIORITY

1. **DTZ*** - Timezone-aware datetimes (data integrity)
2. **S603/S607** - Subprocess security (command injection)
3. **PLW1510** - Subprocess check=True (error handling)
4. **S311** - Cryptographic random (security tokens)
5. **Hardcoded credentials** - Move to env vars

---

## PHASE 2: VERIFICATION

```bash
# Security lint check
ruff check src/ api/ --select S,DTZ --statistics

# Install bandit if needed
pip install bandit

# Bandit scan
bandit -r src/ api/ -ll

# Tests pass
pytest tests/ -x -q
```

---

## Communication

```json
{
  "id": "0709-security-complete-001",
  "timestamp": "[ISO]",
  "from_handover": "0709-SECURITY",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Security hardening complete",
  "message": "[Summary]",
  "files_affected": [],
  "action_required": false,
  "context": {
    "dtz_fixed": "[X]",
    "subprocess_secured": "[X]",
    "secrets_replaced": "[X]",
    "bandit_high": 0,
    "bandit_medium": "[X]"
  }
}
```

---

## Success Criteria

- [ ] DTZ issues = 0
- [ ] Subprocess calls secured
- [ ] No hardcoded credentials
- [ ] Bandit: 0 high severity
- [ ] Tests passing
- [ ] Committed
