# Handover 0902c: Startup + Install Mode Toggle

**Date:** 2026-04-03
**Priority:** High (CE release blocker)
**Edition Scope:** CE
**Status:** Complete
**Parent:** 0902 Single-Port Frontend Serving
**Dependencies:** 0902a (backend mount) + 0902b (port fixes)
**Estimated Complexity:** 2 hours

---

## Task Summary

Add production/development mode detection to `startup.py` and a mode prompt to `install.py`. Production auto-detects `frontend/dist/` and skips Vite. The `--dev` flag forces two-port dev mode.

---

## Implementation

### 1. `startup.py` — Production detection in `start_frontend_server()`

Find `start_frontend_server()` (around line 628). Add dist/ detection at the top:

```python
def start_frontend_server():
    # Check for --dev flag override
    if "--dev" in sys.argv:
        log_info("Development mode (--dev): launching Vite dev server")
        # ... fall through to existing Vite launch code ...
    else:
        dist_dir = Path("frontend/dist")
        if dist_dir.exists() and (dist_dir / "index.html").exists():
            log_info("Production frontend detected (frontend/dist/).")
            log_info(f"Frontend served by FastAPI on port {api_port}.")
            return None  # No subprocess — FastAPI serves static files
        # else: no dist/, fall through to Vite dev server

    # ... existing Vite dev server launch code (unchanged) ...
```

### 2. `startup.py` — Update browser URL

Find where the browser URL is constructed (look for `7274` or `dashboard_port`). In production mode, open the API port instead:

```python
dist_dir = Path("frontend/dist")
if dist_dir.exists() and (dist_dir / "index.html").exists() and "--dev" not in sys.argv:
    browser_url = f"{protocol}://localhost:{api_port}"
else:
    browser_url = f"{protocol}://localhost:{frontend_port}"
```

### 3. `startup.py` — Add `--dev` to argparse/help

If startup.py uses argparse, add the flag. If it uses manual sys.argv parsing, add it to the help text and the existing flag checks.

### 4. `install.py` — Mode prompt

Find the section after npm install succeeds. Add:

```python
print("\nHow will you use GiljoAI?")
print("  1. Production (recommended) - Single port, optimized build")
print("  2. Development - Two ports, hot-reload for code changes")
mode = input("\nSelect [1/2] (default: 1): ").strip() or "1"

if mode == "1":
    print("\nBuilding production frontend...")
    subprocess.run([npm_cmd, "run", "build"], cwd=frontend_dir, check=True)
    print("Frontend built to frontend/dist/")
    # Optionally set config.yaml: services.frontend.dev_server = false
else:
    # Ensure dist/ doesn't exist (avoid confusion)
    dist_dir = Path("frontend/dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    print("\nDevelopment mode: Vite dev server will run on port 7274")
```

### 5. `startup_prod.py` — Deprecate

Add a deprecation notice at the top:

```python
print("WARNING: startup_prod.py is deprecated. Use 'python startup.py' instead.")
print("Production mode is now automatic when frontend/dist/ exists.")
print("Falling through to startup.py...\n")
# ... delegate to startup.py ...
```

### 6. `config.yaml` — Add dev_server flag (optional)

If install.py sets this, startup.py can read it as a secondary signal:

```yaml
services:
  frontend:
    dev_server: false  # true = always Vite, false = use dist/ if available
```

---

## Files to Modify

| File | Change |
|------|--------|
| `startup.py` | Production detection, --dev flag, browser URL |
| `install.py` | Mode prompt, npm run build for production |
| `startup_prod.py` | Deprecation notice |

## Testing

```bash
# Test production mode
cd frontend && npm run build && cd ..
python startup.py          # Should NOT launch Vite, should open :7272

# Test dev override
python startup.py --dev    # Should launch Vite on :7274

# Test auto-detection (no dist/)
rm -rf frontend/dist
python startup.py          # Should launch Vite on :7274

# Test install.py prompt
python install.py          # Should ask production/development
```

## Success Criteria

- [ ] `startup.py` auto-detects `frontend/dist/` and skips Vite
- [ ] `startup.py --dev` forces Vite even when dist/ exists
- [ ] `startup.py` opens correct browser URL per mode
- [ ] `install.py` prompts for production/development
- [ ] Production install runs `npm run build`
- [ ] Development install ensures no stale `dist/` directory
- [ ] `startup_prod.py` shows deprecation warning
