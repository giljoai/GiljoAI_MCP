# Devlog: API Host Binding Priority Fix

**Date:** 2025-10-08
**Type:** Critical Bug Fix
**Impact:** High - Affects all LAN/WAN deployments
**Status:** ✅ RESOLVED
**Related:** Network Topology & Wizard Integration Fixes

---

## Problem Statement

The API server was ignoring the user-configured `services.api.host` value from config.yaml and hardcoding `0.0.0.0` for all LAN/WAN deployments, despite the setup wizard correctly saving the selected adapter IP.

### Symptoms

- Setup wizard correctly writes `services.api.host: 10.1.0.164` to config.yaml
- API startup logs show `"Server binding to 0.0.0.0:7272"` instead of `"Server binding to 10.1.0.164:7272"`
- User's adapter selection is ignored
- Security issue: Binds to ALL network interfaces instead of selected adapter

### Impact on User Experience

Users would:
1. Carefully select their network adapter in the setup wizard
2. See the wizard save their selection to config.yaml
3. Start the API server
4. Watch it bind to 0.0.0.0 instead of their chosen IP
5. Wonder why their configuration was ignored

---

## Root Cause

**File:** `api/run_api.py`
**Function:** `get_default_host()` (lines 120-147)

### Broken Logic (BEFORE)

```python
# Lines 136-139 (OLD)
if mode in ('server', 'lan', 'wan'):
    logging.info(f"Detected {mode} mode - binding to 0.0.0.0 for network access")
    return "0.0.0.0"  # ❌ Hardcoded, ignores config!
```

The function was using mode to determine host binding, completely bypassing the `services.api.host` configuration value.

### Configuration Priority (WRONG)

1. ~~Mode-based hardcoded value~~ (was first - WRONG!)
2. ~~config.yaml services.api.host~~ (was ignored)

The logic prioritized deployment mode over explicit user configuration, which violated the principle of respecting user intent.

---

## Solution Implemented

### Fixed Logic (AFTER)

```python
# Lines 139-152 (NEW)
# FIRST: Check if user configured a specific host
configured_host = config.get('services', {}).get('api', {}).get('host')
if configured_host:
    logging.info(f"Using configured API host: {configured_host}")
    return configured_host  # ✅ Respects user configuration!

# FALLBACK: Use mode-based default only if not configured
mode = config.get('installation', {}).get('mode', 'localhost')
if mode in ('server', 'lan', 'wan'):
    logging.info(f"No host configured, using mode-based default for {mode}: 0.0.0.0")
    return "0.0.0.0"
```

### Configuration Priority (CORRECT)

1. `services.api.host` from config.yaml (user-configured adapter IP) - FIRST ✅
2. Mode-based default (0.0.0.0 or 127.0.0.1) - FALLBACK only ✅

### Design Principle

**Explicit Configuration > Mode-Based Defaults**

When a user explicitly configures a value, that value takes absolute priority. Mode-based defaults are only used as fallbacks when no explicit configuration exists.

---

## Technical Changes

### File Modified

**File:** `api/run_api.py`
**Lines Changed:** 120-157 (38 lines)
**Function:** `get_default_host()`

### Key Improvements

1. Read `services.api.host` FIRST from config.yaml
2. Return configured host if present (e.g., "10.1.0.164")
3. Fall back to mode-based defaults ONLY if not configured
4. Improved logging to show configuration source
5. Clear indication of whether config or default is being used

### Code Comparison

**Before:**
```python
def get_default_host() -> str:
    """Get default host based on deployment mode."""
    # ... load config ...
    mode = config.get('installation', {}).get('mode', 'localhost')

    # ❌ WRONG: Mode determines host, ignoring config
    if mode in ('server', 'lan', 'wan'):
        return "0.0.0.0"
    return "127.0.0.1"
```

**After:**
```python
def get_default_host() -> str:
    """Get default host, preferring configured value over mode-based default."""
    # ... load config ...

    # ✅ CORRECT: Check configured host first
    configured_host = config.get('services', {}).get('api', {}).get('host')
    if configured_host:
        logging.info(f"Using configured API host: {configured_host}")
        return configured_host

    # Fallback to mode-based default
    mode = config.get('installation', {}).get('mode', 'localhost')
    if mode in ('server', 'lan', 'wan'):
        logging.info(f"No host configured, using mode-based default for {mode}: 0.0.0.0")
        return "0.0.0.0"

    logging.info("Using default host for localhost mode: 127.0.0.1")
    return "127.0.0.1"
```

---

## Testing Evidence

### Before Fix

```
Config: services.api.host = "10.1.0.164"
Output: "Server binding to 0.0.0.0:7272"
Result: ❌ WRONG - Ignores config
```

### After Fix

```
Config: services.api.host = "10.1.0.164"
Output: "Using configured API host: 10.1.0.164"
Output: "Server binding to 10.1.0.164:7272"
Result: ✅ CORRECT - Respects config
```

### Verification Steps

1. Setup wizard selects adapter with IP 10.1.0.164
2. Wizard writes to config.yaml:
   ```yaml
   services:
     api:
       host: 10.1.0.164
   ```
3. Start API server: `python api/run_api.py`
4. Check logs:
   ```
   INFO: Using configured API host: 10.1.0.164
   INFO: Server binding to 10.1.0.164:7272
   ```
5. Verify network binding:
   ```bash
   netstat -an | grep 7272
   # Should show: 10.1.0.164:7272 (NOT 0.0.0.0:7272)
   ```

---

## Impact Analysis

### Security

- **Before:** Binds to ALL interfaces (0.0.0.0) even when user selected specific adapter
- **After:** Binds only to user-selected adapter
- **Improvement:** More secure default behavior, respects principle of least privilege

### User Experience

- **Before:** Adapter selection in wizard has no effect
- **After:** Adapter selection works end-to-end
- **Improvement:** No manual config edits required, predictable behavior

### Consistency

- **Before:** Disconnect between wizard configuration and runtime behavior
- **After:** Runtime behavior matches wizard configuration exactly
- **Improvement:** System behaves as user expects

### Deployment Modes

| Mode | Configured Host | Actual Binding (Before) | Actual Binding (After) |
|------|----------------|------------------------|----------------------|
| LAN | 10.1.0.164 | 0.0.0.0:7272 ❌ | 10.1.0.164:7272 ✅ |
| LAN | (none) | 0.0.0.0:7272 ✅ | 0.0.0.0:7272 ✅ |
| localhost | 127.0.0.1 | 127.0.0.1:7272 ✅ | 127.0.0.1:7272 ✅ |

---

## Related Work

This fix completes the network topology work from earlier today:

1. **Setup Wizard Fix** (`api/endpoints/setup.py:481`)
   - Writes selected adapter IP to config.yaml
   - Properly structures network configuration

2. **API Runtime Fix** (`api/run_api.py:120-157`)
   - Reads and uses selected adapter IP
   - Respects user configuration priority

3. **Documentation**
   - Network Topology Principles in CLAUDE.md
   - Architecture updates in TECHNICAL_ARCHITECTURE.md
   - Network adapter selection guide

4. **Tests**
   - 19 integration tests validating correct behavior
   - Coverage for all deployment modes
   - Configuration priority validation

### Complete Flow

```
User Action → Wizard → Config → Runtime
    ↓           ↓        ↓        ↓
Select      Write    Read     Bind
Adapter     IP to    IP from  to
            YAML     YAML     IP
```

**Before:** Flow broke at Runtime (ignored config)
**After:** Flow works end-to-end ✅

---

## Verification Commands

### Check Configuration

```bash
# View current API host setting
cat config.yaml | grep -A 2 "services:" | grep host
```

### Start API Server

```bash
python api/run_api.py
```

### Expected Log Output

```
INFO: Using configured API host: 10.1.0.164
INFO: Server binding to 10.1.0.164:7272
```

### NOT Expected (Wrong)

```
INFO: Detected lan mode - binding to 0.0.0.0  # ❌ WRONG
INFO: Server binding to 0.0.0.0:7272          # ❌ WRONG
```

### Verify Network Binding

```bash
# Check active network connections
netstat -an | grep 7272

# Should show:
# TCP    10.1.0.164:7272    0.0.0.0:0    LISTENING

# NOT:
# TCP    0.0.0.0:7272       0.0.0.0:0    LISTENING
```

---

## Files Modified

- `api/run_api.py` - Fixed host configuration priority in `get_default_host()` function

---

## Lessons Learned

### 1. Configuration Priority Matters

Always check explicit user configuration before applying mode-based defaults. User intent should be the highest priority.

### 2. Test End-to-End

Don't just test the wizard in isolation. Test the complete flow:
- Wizard configuration
- Config file writing
- Config file reading
- Runtime startup
- Network binding

### 3. Log Configuration Sources

Clear logging makes debugging infinitely easier:
```python
logging.info(f"Using configured API host: {configured_host}")  # ✅ Good
logging.info(f"Detected {mode} mode - binding to 0.0.0.0")    # ❌ Unclear
```

### 4. Respect User Intent

If a user explicitly configures a value, that value should be used. Period. Don't override it with "smart" defaults based on other settings.

### 5. Document Decision Trees

When there are multiple sources for a configuration value, document the priority clearly:
```python
# Priority:
# 1. Explicitly configured host in config.yaml
# 2. Mode-based default (lan/wan: 0.0.0.0, localhost: 127.0.0.1)
# 3. Hardcoded fallback (127.0.0.1)
```

---

## Future Enhancements

### Validation

- Warn if configured host doesn't match any active network interface
- Validate that configured IP is syntactically valid
- Check if configured IP is reachable before binding

### Error Handling

- Graceful fallback if configured IP cannot be bound
- Clear error messages explaining binding failures
- Suggestion to run `ipconfig` or `ip addr` to find available IPs

### Documentation

- Add inline comments explaining configuration priority
- Document the decision tree in the function docstring
- Include examples in CLAUDE.md

### Testing

- Add unit tests for `get_default_host()` with various configs
- Integration tests for binding behavior
- Validate all deployment mode combinations

---

## Resolution

**Status:** ✅ RESOLVED

The API server now properly binds to the user-configured adapter IP from config.yaml instead of hardcoding 0.0.0.0 for LAN/WAN modes.

**Configuration Priority (Final):**
1. User-configured `services.api.host` (PRIMARY)
2. Mode-based default (FALLBACK)
3. Hardcoded 127.0.0.1 (ULTIMATE FALLBACK)

**Result:** Setup wizard adapter selection now works end-to-end, with the API binding exactly where the user expects.

---

**Next Steps:**
- Monitor for any edge cases in production
- Consider adding validation warnings
- Document best practices for network adapter selection
