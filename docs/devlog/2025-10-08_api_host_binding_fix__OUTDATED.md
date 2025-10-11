# API Host Binding Fix - 2025-10-08

## Problem

The API server was ignoring the user-configured `services.api.host` value in `config.yaml` and hardcoding `0.0.0.0` for LAN/WAN modes.

### Root Cause

Function `get_default_host()` in `api/run_api.py` (lines 120-147) implemented mode-based logic that bypassed the configured host value:

```python
# BROKEN CODE (Before Fix)
def get_default_host() -> str:
    mode = config.get('installation', {}).get('mode', 'localhost')

    # Server mode (LAN/WAN) binds to all interfaces, localhost mode binds to loopback only
    if mode in ('server', 'lan', 'wan'):
        logging.info(f"Detected {mode} mode - binding to 0.0.0.0 for network access")
        return "0.0.0.0"  # WRONG - ignores config.yaml setting!
```

This caused the API to bind to `0.0.0.0` (all interfaces) even when the user explicitly configured a specific network adapter IP (e.g., `10.1.0.164`) through the setup wizard.

### Impact

- API ignored user-selected network adapter from setup wizard
- Bound to all interfaces (0.0.0.0) instead of specific adapter IP
- Network topology choices from installer were not respected
- Security issue: More permissive binding than intended

## Solution

Modified `get_default_host()` to implement proper priority-based configuration loading:

### Priority Order

1. **services.api.host** from config.yaml (user-configured adapter IP)
2. **Mode-based default** only if host not configured:
   - `0.0.0.0` for lan/wan/server modes
   - `127.0.0.1` for localhost mode

### Fixed Implementation

```python
def get_default_host() -> str:
    """Get default host from config or mode-based default

    Priority:
    1. services.api.host from config.yaml (user-configured adapter IP)
    2. Mode-based default (127.0.0.1 for localhost, 0.0.0.0 for LAN/WAN)

    Returns:
        Host to bind to
    """
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"

        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

                # FIRST: Check if user configured a specific host
                configured_host = config.get('services', {}).get('api', {}).get('host')
                if configured_host:
                    logging.info(f"Using configured API host: {configured_host}")
                    return configured_host

                # FALLBACK: Use mode-based default only if not configured
                mode = config.get('installation', {}).get('mode', 'localhost')
                if mode in ('server', 'lan', 'wan'):
                    logging.info(f"No host configured, using mode-based default for {mode}: 0.0.0.0")
                    return "0.0.0.0"
                else:
                    logging.info(f"No host configured, using mode-based default for {mode}: 127.0.0.1")
                    return "127.0.0.1"
    except Exception as e:
        logging.warning(f"Could not read config: {e}, defaulting to localhost")

    return "127.0.0.1"
```

## Testing

### Test Configuration

```yaml
# config.yaml
installation:
  mode: lan

services:
  api:
    host: 10.1.0.164  # User-configured adapter IP
    port: 7272
```

### Test Results

```bash
# Integration test
INFO: Using configured API host: 10.1.0.164
Returned host: 10.1.0.164

SUCCESS: API will bind to configured adapter IP (10.1.0.164)
         NOT hardcoded 0.0.0.0
```

### Test Scenarios Verified

| Mode | Configured Host | Expected Result | Status |
|------|----------------|-----------------|--------|
| lan | 10.1.0.164 | 10.1.0.164 | PASS |
| lan | None | 0.0.0.0 | PASS |
| localhost | None | 127.0.0.1 | PASS |
| server | 192.168.1.100 | 192.168.1.100 | PASS |

## Changes Made

### Files Modified

- `api/run_api.py` - Fixed `get_default_host()` function

### Diff Summary

```diff
@@ -120,10 +120,14 @@ def get_port_from_sources() -> int:


 def get_default_host() -> str:
-    """Get default host based on config mode
+    """Get default host from config or mode-based default
+
+    Priority:
+    1. services.api.host from config.yaml (user-configured adapter IP)
+    2. Mode-based default (127.0.0.1 for localhost, 0.0.0.0 for LAN/WAN)

     Returns:
-        Default host: 127.0.0.1 for localhost mode, 0.0.0.0 for server mode
+        Host to bind to
     """
     try:
         # Import here to avoid circular dependencies
@@ -131,17 +135,23 @@ def get_default_host() -> str:
         if config_path.exists():
             with open(config_path, 'r') as f:
                 config = yaml.safe_load(f)
-                mode = config.get('installation', {}).get('mode', 'localhost')

-                # Server mode (LAN/WAN) binds to all interfaces, localhost mode binds to loopback only
+                # FIRST: Check if user configured a specific host
+                configured_host = config.get('services', {}).get('api', {}).get('host')
+                if configured_host:
+                    logging.info(f"Using configured API host: {configured_host}")
+                    return configured_host
+
+                # FALLBACK: Use mode-based default only if not configured
+                mode = config.get('installation', {}).get('mode', 'localhost')
                 if mode in ('server', 'lan', 'wan'):
-                    logging.info(f"Detected {mode} mode - binding to 0.0.0.0 for network access")
+                    logging.info(f"No host configured, using mode-based default for {mode}: 0.0.0.0")
                     return "0.0.0.0"
                 else:
-                    logging.info(f"Detected {mode} mode - binding to 127.0.0.1 for localhost only")
+                    logging.info(f"No host configured, using mode-based default for {mode}: 127.0.0.1")
                     return "127.0.0.1"
     except Exception as e:
-        logging.warning(f"Could not detect mode from config: {e}, defaulting to localhost")
+        logging.warning(f"Could not read config: {e}, defaulting to localhost")

     # Safe default: localhost only
     return "127.0.0.1"
```

## Benefits

1. **Respects User Configuration**: API now binds to user-selected network adapter
2. **Security**: More controlled binding (specific adapter vs all interfaces)
3. **Setup Wizard Integration**: Network topology choices are properly honored
4. **Backward Compatibility**: Mode-based defaults still work when host not configured
5. **Transparency**: Clear logging shows which configuration source is used

## Example Behavior

### Before Fix

```
# User selects adapter 10.1.0.164 in setup wizard
# Config saved as:
services:
  api:
    host: 10.1.0.164

# API startup:
INFO: Detected lan mode - binding to 0.0.0.0 for network access
Server binding to 0.0.0.0:7272  # WRONG - ignores config!
```

### After Fix

```
# User selects adapter 10.1.0.164 in setup wizard
# Config saved as:
services:
  api:
    host: 10.1.0.164

# API startup:
INFO: Using configured API host: 10.1.0.164
Server binding to 10.1.0.164:7272  # CORRECT - respects config!
```

## Related Issues

- Setup wizard saves adapter info to config.yaml (commit 33e3b19)
- Network adapter detection and validation (commit 89d2a3c)
- LAN mode configuration and CORS setup

## Verification

To verify the fix is working:

```bash
# Check config
cat config.yaml | grep -A 3 "services:"

# Test the function
python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from api.run_api import get_default_host
print(f'Host: {get_default_host()}')
"

# Start API and check binding
python api/run_api.py
# Look for: "Using configured API host: 10.1.0.164"
# And: "Server binding to 10.1.0.164:7272"
```

## Commit

```
commit 3ebb4a54d2d036dd194a93188dbbf6beaef39852
Author: GiljoAi <infoteam@giljo.ai>
Date:   Wed Oct 8 21:37:12 2025

fix: API server now respects configured adapter IP from config.yaml

Fixed get_default_host() to prioritize services.api.host from config.yaml
over mode-based hardcoded defaults.
```
