# Handover 0709-SECURITY: Security Hardening

**Series:** 0700 Code Cleanup Series
**Risk Level:** MEDIUM
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-06

---

## CRITICAL: Large File Handling

**Files over 20K tokens (~500+ lines) MUST be read in batches.** Do NOT skip large files.

```python
# Read large files in chunks of 200 lines:
Read(file_path, offset=0, limit=200)    # Lines 1-200
Read(file_path, offset=200, limit=200)  # Lines 201-400
Read(file_path, offset=400, limit=200)  # Lines 401-600
# Continue until entire file is processed
```

---

## Mission Statement

Address security-related lint issues and perform security audit. Fix timezone handling, subprocess calls, and other security concerns flagged by ruff's S rules and bandit.

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

### Launch Validation Subagent

```
"Validate 0709-SECURITY scope for security hardening.

CHECK 1: All security-related lint issues
```bash
ruff check src/ api/ --select S --statistics
```

CHECK 2: Datetime timezone issues
```bash
ruff check src/ api/ --select DTZ --statistics
```

CHECK 3: Subprocess security
```bash
ruff check src/ api/ --select S603,S607,PLW1510 --statistics
```

CHECK 4: Bandit scan (if available)
```bash
bandit -r src/ api/ -ll 2>&1 | tail -30
```

CHECK 5: Hardcoded secrets check
```bash
grep -rn "password\s*=\s*['\"]" src/ api/ --include="*.py" | grep -v test | grep -v "#"
grep -rn "secret\s*=\s*['\"]" src/ api/ --include="*.py" | grep -v test | grep -v "#"
grep -rn "api_key\s*=\s*['\"]" src/ api/ --include="*.py" | grep -v test | grep -v "#"
```

REPORT: Confirm security issues and prioritize by severity."
```

---

## PHASE 1: EXECUTION

### Task 1: DTZ - Timezone-Aware Datetimes (~59 instances)

**Strategy:** Use timezone-aware datetime functions.

```python
# BEFORE (naive - bad)
from datetime import datetime
now = datetime.now()
utc_now = datetime.utcnow()

# AFTER (timezone-aware - good)
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
# Or use a helper
from src.giljo_mcp.utils import utc_now
```

**Common fixes:**
- `datetime.now()` → `datetime.now(timezone.utc)`
- `datetime.utcnow()` → `datetime.now(timezone.utc)`
- `datetime.fromtimestamp(ts)` → `datetime.fromtimestamp(ts, tz=timezone.utc)`

### Task 2: S603/S607 - Subprocess Security (~12 instances)

**Strategy:** Use safe subprocess patterns.

```python
# BEFORE (risky)
import subprocess
subprocess.run(command)  # No shell=False explicit
subprocess.run(["cmd", user_input])  # Unsanitized input

# AFTER (safe)
import subprocess
import shlex

# Explicit shell=False
subprocess.run(command, shell=False, check=True)

# Sanitize inputs
safe_arg = shlex.quote(user_input)
subprocess.run(["cmd", safe_arg], shell=False, check=True)
```

### Task 3: PLW1510 - Subprocess Without Check (~5 instances)

**Strategy:** Always check subprocess return codes.

```python
# BEFORE (ignores errors)
subprocess.run(["git", "status"])

# AFTER (raises on error)
subprocess.run(["git", "status"], check=True)

# Or handle explicitly
result = subprocess.run(["git", "status"], capture_output=True)
if result.returncode != 0:
    logger.error(f"Git failed: {result.stderr}")
```

### Task 4: S311 - Non-Cryptographic Random (~7 instances)

**Strategy:** Use secrets module for security-sensitive randomness.

```python
# BEFORE (predictable)
import random
token = ''.join(random.choices(string.ascii_letters, k=32))

# AFTER (cryptographically secure)
import secrets
token = secrets.token_urlsafe(32)
```

**Note:** `random` is OK for non-security uses (shuffling, sampling).

### Task 5: S301 - Pickle Usage (~1 instance)

**Strategy:** Review and secure pickle usage.

```python
# If pickle is necessary, validate source
# Or switch to safer serialization (JSON, msgpack)
```

### Task 6: Hardcoded Credentials Audit

Search and remediate:
- Move to environment variables
- Use config files (gitignored)
- Use secrets management

```python
# BEFORE (bad)
API_KEY = "sk-abc123..."

# AFTER (good)
import os
API_KEY = os.environ.get("API_KEY")
```

---

## PHASE 2: VERIFICATION

```bash
# Check remaining security issues
ruff check src/ api/ --select S,DTZ --statistics

# Run bandit
bandit -r src/ api/ -ll

# Verify no regressions
python -c "from api.app import app; print('API OK')"
pytest tests/ -x -q --tb=short

# Check for secrets in git
git secrets --scan 2>/dev/null || echo "git-secrets not installed"
```

---

## Success Criteria

- [ ] Phase 0 validation complete
- [ ] DTZ issues resolved (timezone-aware datetimes)
- [ ] Subprocess calls secured (shell=False, check=True)
- [ ] No hardcoded credentials in code
- [ ] Bandit scan passes with no high/critical issues
- [ ] All tests passing
- [ ] Committed

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
    "dtz_issues_fixed": "[X]",
    "subprocess_secured": "[X]",
    "random_to_secrets": "[X]",
    "hardcoded_creds_found": "[X]",
    "bandit_high_remaining": 0,
    "bandit_medium_remaining": "[X]"
  }
}
```

---

## Commit Message Template

```
security(0709): Harden security posture

- Fixed [X] timezone-naive datetime calls (DTZ*)
- Secured [X] subprocess calls with shell=False, check=True
- Replaced [X] random usages with secrets module
- Removed [X] hardcoded credentials
- Bandit scan: 0 high, [X] medium remaining

Co-Authored-By: Claude <noreply@anthropic.com>
```
