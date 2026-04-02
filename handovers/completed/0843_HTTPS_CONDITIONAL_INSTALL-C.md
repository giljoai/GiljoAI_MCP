# 0843 - HTTPS Conditional Installation

**Priority:** High (CE launch requirement)
**Edition:** Community Edition (CE)
**Status:** Not Started
**Created:** 2026-03-29

---

## Problem

The Clipboard API (`navigator.clipboard.writeText`) requires a "secure context" (HTTPS or localhost). When a user installs GiljoAI MCP on a server and accesses the dashboard from another machine over LAN/WAN via HTTP, the browser silently refuses clipboard operations. Copy buttons fail with no error. The product appears broken.

The existing `execCommand('copy')` fallback also fails in this scenario because prompt content is assembled server-side on click. The async round-trip to the API causes the browser gesture window to expire before the copy fires.

**Root cause:** Dynamic prompt assembly on click is architecturally incompatible with HTTP on non-localhost origins. The modern Clipboard API solves the async problem natively but requires HTTPS.

**Industry context:** No self-hosted product has solved raw-LAN-IP HTTPS without warnings. Home Assistant, Synology NAS, and Plex all use one of: cloud relay, DNS tricks with real CAs, or plain HTTP. For CE, the practical solution is mkcert with a one-time client cert install.

---

## Solution

Split the installer into two tracks based on user's answer to the existing network configuration prompt. The installer already asks this question (option 2 = localhost, option 3 = LAN IP, option 4 = custom). This handover extends the consequences of that choice.

### Track 1: Localhost

When user selects localhost (option 2):

1. **Bind API to `127.0.0.1` only** (not `0.0.0.0`). This prevents anyone on the LAN from reaching the server and accidentally hitting the broken clipboard path. The machine physically refuses non-local connections.
2. **No HTTPS.** HTTP works perfectly because all browsers grant localhost a secure context exemption. Clipboard API works. No certs needed.
3. **No changes to frontend URLs.** Everything stays `http://localhost:...`

### Track 2: LAN/WAN (any non-localhost selection)

When user selects a LAN IP (option 3), auto-detect (option 1), or custom address (option 4):

1. **Check for mkcert.** If not found, print install instructions per OS and exit gracefully. mkcert is already a known dependency in the project.
2. **Run `mkcert -install`** to create and trust the local root CA on the server machine.
3. **Generate certificates** for the selected external host: `mkcert <external_host> localhost 127.0.0.1 ::1`. Store certs in a predictable location (e.g., `certs/` directory in the project root or a platform-appropriate config path).
4. **Configure server for HTTPS.** Update `config.yaml` to point at the cert files. Uvicorn supports `--ssl-keyfile` and `--ssl-certfile` directly.
5. **Update frontend URLs** to use `https://` in the generated configuration.
6. **Bind API to `0.0.0.0`** as it does today for LAN access.
7. **Print client certificate instructions** at the end of install (see below).

### CLI Output After LAN/WAN Install

After successful cert generation, the installer prints:

```
HTTPS configured! This machine already trusts the certificate.

To connect from OTHER machines without browser warnings,
copy the root CA file to each client machine:

  File: /home/<user>/.local/share/mkcert/rootCA.pem

  Transfer it (pick one):
    scp <user>@<external_host>:/home/<user>/.local/share/mkcert/rootCA.pem ~/Downloads/

  Then install on the client:
    macOS:   sudo security add-trusted-cert -d -r trustRoot \
               -k /Library/Keychains/System.keychain ~/Downloads/rootCA.pem
    Windows: certutil -addstore -f "ROOT" %USERPROFILE%\Downloads\rootCA.pem
    Linux:   sudo cp ~/Downloads/rootCA.pem /usr/local/share/ca-certificates/giljoai.crt \
               && sudo update-ca-certificates

This is a one-time step per client machine.
```

The rootCA.pem is a public key (not sensitive). It can be transferred over HTTP, SCP, USB, email, or any convenient method.

**Platform note:** The mkcert root CA path varies by OS. Use `mkcert -CAROOT` to get the actual path at runtime rather than hardcoding it.

---

## Escape Hatch

Add a `--no-ssl` flag to `startup.py` (or equivalent config override) that forces HTTP even on a LAN/WAN configuration. This is for Docker, CI/CD, reverse-proxy setups, or any environment where HTTPS is handled externally. When `--no-ssl` is active, the installer skips cert generation entirely. Document this in the CLI help text.

---

## UI Fallback (Settings Page)

Add a "Connect Another Machine" section to the Settings page (Network tab or a new subsection). This is the safety net for users who:

- Skipped the CLI output
- Added a second client machine months later
- Switched from localhost to LAN after initial install

Contents:

1. Download link for `rootCA.pem` (served from a simple authenticated endpoint)
2. OS-specific install commands (same as CLI output)
3. Brief explanation: "Install this certificate once on any machine that accesses GiljoAI MCP over your network."

**Important:** This is NOT the primary path. The CLI install is the primary path. The UI page is the fallback.

---

## What Already Exists (do NOT rebuild)

The HTTPS infrastructure is already implemented. This handover rewires the decision tree, not the plumbing.

| Component | Status | Location |
|-----------|--------|----------|
| mkcert integration | Done | `install.py:946-1170` — `setup_https()` method with mkcert install, CA trust, cert generation |
| mkcert auto-install (Windows) | Done | `install.py:1174-1230` — `_install_mkcert()` via winget |
| SSL config in config.yaml | Done | `features.ssl_enabled`, `paths.ssl_cert`, `paths.ssl_key` |
| Uvicorn SSL passthrough | Done | `api/app.py:320-321` — reads `ssl_enabled` from config |
| Startup SSL health check | Done | `startup.py:442-458` — `get_ssl_enabled()`, SSL-aware health checks |
| Frontend protocol detection | Done | `install.py:2297` — sets `http`/`https` based on `ssl_enabled` |
| NODE_EXTRA_CA_CERTS guidance | Done | `install.py:1123-1170` — post-install instructions for Node.js CLI tools |

---

## Files to Modify

### Core install/runtime changes

| File | Change |
|------|--------|
| `install.py` | **Remove the y/N prompt at line 966.** Instead: if network choice is localhost → skip HTTPS entirely, set bind to `127.0.0.1`. If network choice is LAN/WAN/custom → run `setup_https()` automatically. Update defaults at lines 203, 1739, 1794 to use `127.0.0.1` for localhost track. |
| `Linux_Installer/linux_install.py` | Same branching logic. Update bind defaults at lines 86, 812, 862. |
| `startup.py` | Add `--no-ssl` flag as escape hatch. When set, skip SSL config regardless of config.yaml. |
| `api/run_api.py` | Read bind address from config instead of hardcoding `0.0.0.0`. Update docstrings at lines 131, 138, 141, 144, 157, 163. |
| `api/app.py` | Pass bind address from config to uvicorn. Refuse HTTP when SSL is configured (no dual-bind). |
| `api/endpoints/network.py:72` | Read bind from config instead of hardcoding `0.0.0.0`. |
| `api/endpoints/configuration.py:575` | Update docstring to reflect conditional binding. |
| `api/startup/database.py:34` | Update comment. |
| `src/giljo_mcp/config_manager.py` | Update comments/logic at lines 32, 40, 49, 54, 64, 326, 551. Bind address should come from config, not be hardcoded. |
| `scripts/init_config.py` | Update comments at lines 26, 38, 57. Local config should set `bind: 127.0.0.1`. |
| `installer/core/config.py` | Update comments and hardcoded values at lines 3, 22, 134, 174-175, 232, 366, 398, 418, 430. |
| `Linux_Installer/core/config.py` | Same as above — lines 3, 23, 127, 167-168, 222, 349, 381, 390, 402. |

### UI changes

| File | Change |
|------|--------|
| Settings > Network tab (Vue component) | Add "Connect Another Machine" section with cert download and OS-specific install instructions. |
| New API endpoint | `GET /api/setup/root-ca` (authenticated) — serve the rootCA.pem file. |

### Bandit security config

| File | Change |
|------|--------|
| `.bandit` or `pyproject.toml` bandit config | B104 skip comment says "intentional 0.0.0.0 binding." Update to say "LAN/WAN track binds 0.0.0.0, localhost track binds 127.0.0.1 — both intentional." |

---

## Documentation Updates (MANDATORY — part of this handover)

The v3.0 "always bind 0.0.0.0" philosophy is referenced in 40+ locations. The new policy is:

> **Localhost installs bind `127.0.0.1` (HTTP, no certs). LAN/WAN installs bind `0.0.0.0` with mandatory HTTPS via mkcert. The bind address and protocol are derived from the user's network choice at install time.**

### Active documentation — MUST update

| File | Lines | Current text | New text |
|------|-------|-------------|----------|
| `CLAUDE.md` | 30 | `Server binds 0.0.0.0, OS firewall controls access` | `Localhost binds 127.0.0.1 (HTTP). LAN/WAN binds 0.0.0.0 with mandatory HTTPS (mkcert). Bind address derived from install-time network choice.` |
| `README.md` | 119 | `Always binds to 0.0.0.0 (all interfaces)` | `Localhost: binds 127.0.0.1. LAN/WAN: binds 0.0.0.0 with HTTPS` |
| `README.md` | 231 | `v3.1 unified architecture (0.0.0.0 binding with firewall control)` | `v3.1 unified architecture (conditional binding + HTTPS for LAN/WAN)` |
| `README.md` | 360 | `API binds to 0.0.0.0, firewall controls access` | `Localhost: 127.0.0.1. LAN/WAN: 0.0.0.0 + HTTPS` |
| `docs/README_FIRST.md` | 110 | `API always binds to 0.0.0.0 (all network interfaces)` | `Localhost: API binds to 127.0.0.1. LAN/WAN: binds to 0.0.0.0 with HTTPS` |
| `docs/README_FIRST.md` | 184 | `Starts API server on port 7272 (binds to 0.0.0.0)` | `Starts API server on port 7272 (bind address from install config)` |
| `docs/README_FIRST.md` | 433 | `host: 0.0.0.0  # Always bind to all interfaces` | `host: 127.0.0.1  # localhost track; LAN/WAN uses 0.0.0.0 + HTTPS` |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | 26 | `ALWAYS binds to all network interfaces` | Rewrite paragraph to explain conditional binding |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | 31 | `API server ALWAYS binds to 0.0.0.0` | `API server binds to 127.0.0.1 (localhost) or 0.0.0.0 + HTTPS (LAN/WAN)` |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | 78, 1426, 2102, 2138 | Various `0.0.0.0 binding` references | Update to reflect conditional binding |
| `docs/GILJOAI_MCP_PURPOSE.md` | 343, 570, 583 | `0.0.0.0 binding` references | Update to conditional binding |
| `docs/INSTALLATION_FLOW_PROCESS.md` | 718 | `'--host', '0.0.0.0'  # Always bind` | `'--host', bind_address  # from install config` |

### Reference docs — update if still active

| File | Lines | Action |
|------|-------|--------|
| `handovers/Reference_docs/start_to_finish_agent_FLOW.md` | 1784, 1891 | Update troubleshooting guidance |

### Archived docs — DO NOT change

All files under `docs/archive/` and `handovers/completed/` are historical records. Do not modify them. They accurately reflect the architecture at the time they were written.

### Code comments (updated as part of the code changes above)

The following files have `# v3.0: Always bind all interfaces` or similar comments that must be updated inline when the code is changed:

- `install.py:203, 1794`
- `Linux_Installer/linux_install.py:86, 862`
- `api/run_api.py:131, 138, 141, 144, 157, 163`
- `api/startup/database.py:34`
- `src/giljo_mcp/config_manager.py:32, 40, 49, 54, 64, 326, 551`
- `scripts/init_config.py:26, 38, 57`
- `installer/core/config.py:3, 22, 134, 174, 232, 366, 398, 418, 430`
- `Linux_Installer/core/config.py:3, 23, 127, 167, 222, 349, 381, 390, 402`
- `dev_tools/simulator/process_manager.py:80`
- `dev_tools/control_panel.py:1108, 1289`

---

## What NOT to Change

- **Database binding.** PostgreSQL stays on `localhost` always. This handover does not touch the database layer.
- **Authentication flow.** JWT auth is unchanged. HTTPS encrypts the transport but the auth logic is identical.
- **CORS configuration.** May need the `https://` origin added to allowed origins, but the existing CORS setup already uses `external_host` — just verify it picks up the scheme change.
- **MCP protocol.** WebSocket connections will naturally upgrade to `wss://` when the server runs HTTPS. No MCP-layer changes needed.
- **Archived/completed handovers.** Files in `handovers/completed/` and `docs/archive/` are historical records. They describe the architecture at the time of writing and must not be retroactively edited.

---

## Testing Requirements

1. **Localhost track:** Install with localhost selected. Confirm server binds to `127.0.0.1` (not `0.0.0.0`). Confirm clipboard copy works in browser. Confirm LAN connection is refused.
2. **LAN track:** Install with LAN IP selected. Confirm mkcert runs automatically (no y/N prompt), certs are generated, server starts on HTTPS. Confirm clipboard copy works from the server's own browser (root CA already trusted). Confirm a client machine without the cert sees a browser warning. Confirm after installing the root CA on the client machine, the warning disappears and clipboard works.
3. **`--no-ssl` flag:** Install with LAN IP + `--no-ssl`. Confirm server starts on HTTP, no certs generated.
4. **Settings fallback:** Confirm the root CA download endpoint works (authenticated). Confirm the UI displays correct instructions.
5. **Upgrade path:** Existing installations that chose LAN before this handover should not break. The installer should detect "already configured" and offer to add HTTPS, or the user re-runs setup.
6. **All 19 clipboard operations:** On a LAN HTTPS install, confirm all copy buttons show success toasts and content lands in clipboard.

---

## Escape Hatch

Add a `--no-ssl` flag to `startup.py` (or equivalent config override) that forces HTTP even on a LAN/WAN configuration. This is for Docker, CI/CD, reverse-proxy setups, or any environment where HTTPS is handled externally. When `--no-ssl` is active, the installer skips cert generation entirely. Document this in the CLI help text.

---

## Dependencies

- `mkcert` must be installable on Windows, Linux, and macOS. The installer already handles this (winget on Windows, package manager guidance on Linux/macOS).
- The existing network configuration prompt in `install.py` (options 1-4) is the entry point. This handover changes the consequences of that choice, not the question itself.

---

## Context for Agent

- **Existing HTTPS code:** `install.py:946-1230` already has the full mkcert flow. Do NOT rewrite it. The change is removing the y/N prompt and making it automatic for LAN/WAN selections.
- **0842j** (completed) fixed the `execCommand` fallback for clipboard copy inside Vuetify dialogs. That fix handles the synchronous copy path on non-secure contexts. HTTPS makes the async Clipboard API available, fixing the 7 remaining async-before-copy operations.
- **v3.0 philosophy update:** The v3.0 "always bind 0.0.0.0" decision was correct when browsers didn't gate features behind secure contexts. The refinement is: bind address now follows from the network choice. This is not a deployment mode — it's a consequence of the user's answer to a question we already ask. The 40+ doc/comment updates listed above must be completed as part of this handover.
- The setup wizard redesign (0855 series, not started) includes a "Connect to GiljoAI" step. The cert distribution UI could integrate there, but that is out of scope for this handover. Build the Settings page fallback now; the 0855 series can reference it later.
