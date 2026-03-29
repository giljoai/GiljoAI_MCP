# Handover: 0842m Pre-existing Bug Fixes

**Date:** 2026-03-28
**From Agent:** Strategic session (Claude.ai)
**To Agent:** Coding agent (Claude Code)
**Priority:** High
**Estimated Complexity:** 30-60 minutes
**Status:** Not Started

---

## Task Summary

Fix two pre-existing bugs discovered during the 0842 branch audit. Neither was introduced by 0842 work. Both affect production correctness.

---

## Bug 1: `ai_tools.py` references non-existent `config.services`

**File:** `api/endpoints/ai_tools.py` line ~203
**Problem:** Code calls `config.services.external_host` but ConfigManager exposes `config.server` (a `ServerConfig` dataclass), not `config.services`. This raises `AttributeError` at runtime.
**Fix:** Replace with `config.get_nested("services.external_host")` which reads from the YAML config structure correctly.

**Steps:**
1. Read `api/endpoints/ai_tools.py` and find all references to `config.services`
2. Grep the entire `api/` directory for other `config.services` references (there may be more)
3. Replace each with the correct accessor: `config.get_nested("services.external_host")` or the appropriate nested key
4. Verify `config.get_nested()` exists and confirm its return type/behavior by reading `config_manager.py`
5. If `config.get_nested()` returns `None` for missing keys, ensure callers handle that

**Test:** Start the server, navigate to the AI Tools configuration page, confirm it loads without error and displays the correct external_host value.

---

## Bug 2: `install.py` does not pass `network_mode` to ConfigManager

**File:** `install.py` lines ~1733-1741
**Problem:** The installer builds `config_settings` dict but omits `network_mode`, `selected_adapter`, and `initial_ip`. As a result, `security.network.mode` in `config.yaml` is always written as `"localhost"` regardless of what the user selected during installation.

**Impact:** `api/app.py` line ~283 has startup logic that only runs for `auto` or `static` mode. With mode stuck on `"localhost"`, the dynamic IP auto-detection at startup is defeated. If a user selects LAN IP during install and their DHCP lease later changes, the server cannot auto-detect the new IP.

**Steps:**
1. Read `install.py` around lines 1730-1750 to find the `config_settings` dict construction
2. Find where the user's network mode selection is stored during the install flow (variable names like `network_mode`, `selected_adapter`, `initial_ip`)
3. Add these to `config_settings` so they are written to `config.yaml` under the correct keys:
   - `security.network.mode` = the selected mode (`localhost`, `auto`, `static`)
   - `security.network.selected_adapter` = the adapter name (if auto/static)
   - `security.network.initial_ip` = the detected or entered IP
4. Verify by reading `api/app.py` line ~283 to confirm what keys it reads and match them exactly

**Test:**
1. Run `install.py` and select "auto-detect" network mode
2. Check `config.yaml` after install: `security.network.mode` should say `auto` (not `localhost`)
3. Start the server and confirm the startup log shows auto-detection running

---

## Quality Gate

- Pre-commit hooks must pass
- No new dead code
- No `--no-verify` commits
- Both fixes should be a single commit: `fix: 0842m pre-existing bug fixes (config.services + network_mode passthrough)`

---

## Rollback

Both are isolated fixes. Revert the single commit if anything breaks.
