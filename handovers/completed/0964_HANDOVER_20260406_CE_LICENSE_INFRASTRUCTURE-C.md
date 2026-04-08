# 0964 — CE License Infrastructure

**Priority:** High
**Status:** Not Started
**Edition:** [CE] — Community Edition (`main` branch only)
**Estimated Effort:** Medium (1 session)

---

## Context

GiljoAI MCP Community Edition is source-available. Before public release, the codebase needs three things that currently do not exist:

1. **License headers** in every Python source file
2. **A license validation stub** that returns `"CE"` mode — architecturally ready for a commercial key validator to slot in without touching CE code
3. **Edition boundary comments** marking code that a commercial build would override or extend

This is not a functional change. No behavior changes. No new dependencies. This is structural hygiene that protects the project legally and makes the future commercial build clean.

**Do not implement actual cryptographic key validation.** That belongs in the private commercial repo. CE only needs the stub.

---

## Scope

### In Scope
- Add license header to every `.py` file under `src/`, `api/`, `tests/`, and root-level scripts (`install.py`, `run.py`, etc.)
- Create `src/giljo_mcp/licensing/` package with a single `validator.py` module (CE stub only)
- Wire the stub into application startup — called once at boot, result stored in app state
- Add `# [CE]` boundary comments at the three key enforcement points listed below
- Update `pyproject.toml` if a new package path is introduced

### Out of Scope
- Cryptographic key generation or validation (commercial repo only)
- Any UI changes
- Any database changes
- Any behavior changes to existing functionality

---

## Implementation

### Phase 1 — License Headers

Add the following header block to the top of **every** `.py` file in `src/`, `api/`, `tests/`, and root scripts. Place it after any `#!/usr/bin/env python` shebang line, before all imports.

```python
# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.
```

**Implementation approach:**
- Use a script to scan all `.py` files and prepend the header if not already present
- Skip `__init__.py` files that are completely empty (zero bytes)
- Run `ruff check` after to confirm no lint issues introduced
- Commit as a single atomic commit: `[CE] chore: add license headers to all Python source files`

**Do not** manually edit 200+ files. Write a script, run it, verify, commit.

---

### Phase 2 — License Validator Stub

Create the following package structure:

```
src/giljo_mcp/licensing/
    __init__.py
    validator.py
```

**`src/giljo_mcp/licensing/__init__.py`**
```python
# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

from .validator import LicenseValidator, LicenseResult

__all__ = ["LicenseValidator", "LicenseResult"]
```

**`src/giljo_mcp/licensing/validator.py`**
```python
# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
License validation module.

Community Edition: always returns CE mode. No enforcement.

Commercial builds replace this module with a cryptographic key validator
that verifies a signed license file at startup. The interface contract
(LicenseResult dataclass + LicenseValidator.validate()) is stable and
must not change in CE without a corresponding update in the commercial build.
"""

from dataclasses import dataclass
from enum import Enum


class LicenseEdition(str, Enum):
    CE = "CE"
    # [CE] Commercial editions declared here in the commercial build.
    # Do not add values to this enum in CE.


@dataclass(frozen=True)
class LicenseResult:
    edition: LicenseEdition
    valid: bool
    seat_limit: int | None  # None = unlimited (CE)
    licensee: str | None    # None = CE (no licensee)
    message: str


class LicenseValidator:
    """
    Validates the runtime license.

    CE behavior: always returns a valid CE result. No file I/O, no network
    calls, no cryptographic checks. This is intentional.

    Commercial behavior (private repo): reads a signed license file,
    verifies the Ed25519 signature against the embedded public key,
    extracts seat count and expiry, returns the appropriate LicenseResult.
    The commercial build overrides this class entirely — it does not
    subclass it. The interface contract is the only shared surface.
    """

    def validate(self) -> LicenseResult:
        # [CE] CE always returns valid CE mode. Do not modify this return value.
        # Commercial builds replace this method with cryptographic validation.
        return LicenseResult(
            edition=LicenseEdition.CE,
            valid=True,
            seat_limit=1,
            licensee=None,
            message="GiljoAI MCP Community Edition — single-user use only.",
        )
```

---

### Phase 3 — Wire Into Application Startup

In `app.py` (or wherever `lifespan` / startup is defined), call the validator once at boot and store the result in application state.

**Add to startup sequence — after config load, before first request:**

```python
from giljo_mcp.licensing import LicenseValidator

# [CE] License validation — CE always passes. Commercial builds enforce here.
license_result = LicenseValidator().validate()
if not license_result.valid:
    # Commercial builds raise here with a user-facing error message.
    # CE never reaches this branch.
    raise RuntimeError(f"License validation failed: {license_result.message}")

app.state.license = license_result
```

Log the result at INFO level on startup:
```
INFO: License: GiljoAI MCP Community Edition — single-user use only.
```

---

### Phase 4 — Edition Boundary Comments

Add `# [CE]` comments at these three specific points. These mark where the commercial build diverges. Do not add them elsewhere — over-commenting creates noise.

1. **Single-user enforcement in auth** — wherever the system enforces or would enforce user count limits. Add:
   ```python
   # [CE] Single-user limit enforced by license only. No runtime seat check in CE.
   ```

2. **The startup license check** added in Phase 3 (already included above).

3. **Any location where a config flag or feature gate would differ between editions** — search for `edition` or `tier` in existing code. If none exist, no additional comments needed.

---

## Tests

Add `tests/test_licensing.py`:

```python
# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

from giljo_mcp.licensing import LicenseValidator, LicenseResult
from giljo_mcp.licensing.validator import LicenseEdition


def test_ce_validator_returns_valid_result():
    result = LicenseValidator().validate()
    assert isinstance(result, LicenseResult)
    assert result.valid is True


def test_ce_validator_returns_ce_edition():
    result = LicenseValidator().validate()
    assert result.edition == LicenseEdition.CE


def test_ce_validator_enforces_single_seat():
    result = LicenseValidator().validate()
    assert result.seat_limit == 1


def test_ce_validator_has_no_licensee():
    result = LicenseValidator().validate()
    assert result.licensee is None


def test_ce_validator_message_is_present():
    result = LicenseValidator().validate()
    assert isinstance(result.message, str)
    assert len(result.message) > 0
```

All 5 tests must pass. No mocking required — the CE stub has no external dependencies.

---

## Commit Sequence

```
[CE] chore: add license headers to all Python source files
[CE] feat: add LicenseValidator stub and LicenseResult dataclass
[CE] feat: wire license validation into application startup
[CE] test: add licensing module tests (5 assertions)
```

---

## Success Criteria

- [ ] Every `.py` file in `src/`, `api/`, `tests/`, and root scripts has the license header
- [ ] `src/giljo_mcp/licensing/validator.py` exists with the interface defined above
- [ ] Application boots and logs the CE license message
- [ ] 5 licensing tests pass
- [ ] `ruff check src/ api/ tests/` passes clean
- [ ] Pre-commit hooks pass — no `--no-verify`
- [ ] Deletion test: removing `src/giljo_mcp/licensing/` and replacing with a stub import does not break any non-licensing tests

---

## Notes for Agent

- The `LicenseResult` dataclass and `LicenseValidator.validate()` signature are a **stable interface contract**. The commercial build depends on them. Do not rename fields or change return types without flagging this to the user.
- The `seat_limit=1` in CE is informational only. CE does not enforce it at runtime. The license text enforces it legally.
- Do not introduce any third-party dependencies in this module. The CE licensing stub must have zero imports outside the Python standard library.
- If `app.py` uses a lifespan context manager pattern, add the license call inside the startup block, not at module import time.
