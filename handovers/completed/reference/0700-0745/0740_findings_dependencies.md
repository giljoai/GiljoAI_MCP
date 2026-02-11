# 0740 Findings: Dependencies

## Executive Summary

This audit examined all dependency manifests for the GiljoAI MCP Server project (Python backend + Vue 3 frontend). The key findings are:

- **1 critical security vulnerability** in the Python stack: MCP SDK v1.12.3 has CVE-2025-66416 (DNS rebinding, fix in v1.23.0)
- **7 npm vulnerabilities** including 1 critical (happy-dom RCE), 2 high (axios DoS, glob command injection), and 4 moderate
- **7 unused npm production dependencies** that can be removed: `@vue-flow/*` (4 packages), `chart.js`, `d3`, `gsap`, `socket.io-client`, `vue-chartjs`, `vuedraggable`
- **1 unused Python production dependency**: `pydantic-settings` (zero imports found)
- **Duplicate dependencies**: `sass` + `sass-embedded` (redundant), `happy-dom` + `jsdom` (dual test environments), `.eslintrc.json` + `eslint.config.js` (dual ESLint configs)
- **Version pinning gap**: Python requirements use minimum version ranges (`>=`) for most packages; only `mcp` and `bcrypt` are pinned
- **Dev dependency segregation is clean**: Python dev tools are properly separated into `dev-requirements.txt`

**Estimated savings from removing unused npm packages**: ~15-20 MB from `node_modules`, faster installs, reduced attack surface.

## Methodology

1. Read all dependency manifests: `requirements.txt`, `dev-requirements.txt`, `dev_tools/requirements.txt`, `dev_tools/simulator/requirements.txt`, `frontend/package.json`
2. For each listed package, searched the codebase for actual import/require statements using ripgrep
3. Cross-referenced with runtime usage patterns (CLI tools, transitive dependencies, build-time-only usage)
4. Ran `pip-audit` against `requirements.txt` for Python CVEs
5. Ran `npm audit` for frontend vulnerabilities
6. Checked installed vs latest versions using `pip list --outdated` and `npm audit`
7. Validated each "unused" claim against false-positive scenarios (indirect imports, plugin systems, runtime-only usage)

---

## Python Dependencies

### Unused (can be removed)

| Package | Listed In | Evidence of Non-Use |
|---------|-----------|-------------------|
| `pydantic-settings` | `requirements.txt` | Zero imports of `pydantic_settings` or `BaseSettings` found anywhere in the codebase (src/, api/, tests/). No `.env`-based settings classes exist. Configuration is managed through `config_manager.py` using `pyyaml` + `dataclass`. |

### Potentially Removable (installed but not in requirements.txt)

| Package | Installed Version | Evidence |
|---------|------------------|----------|
| `python-jose` | 3.5.0 | Installed but NOT listed in `requirements.txt`. Comment in requirements says "using PyJWT instead of python-jose". Zero imports of `from jose` or `import jose` found. This is a leftover from a prior migration. Should be uninstalled. |

### Security Vulnerabilities

| Package | Installed Version | Vulnerability | Severity | Fix Version |
|---------|------------------|--------------|----------|-------------|
| `mcp` | 1.12.3 | CVE-2025-66416: DNS Rebinding via HTTP - FastMCP class does not enable DNS rebinding protection by default for HTTP-based servers running on localhost. An attacker could use a malicious website to perform DNS rebinding attacks against local MCP servers. | **HIGH** (CVSS 7.6) | 1.23.0 |

**Note on MCP pinning**: The `requirements.txt` comment states `mcp==1.12.3 # MCP SDK (pinned for serena-agent compatibility)`. Upgrading to 1.23.0+ requires validating serena-agent compatibility first, but the security fix is important. The project uses HTTP-only MCP (stdio removed per Handover 0334), making this vulnerability directly relevant.

### Version Pinning Status

| Package | Pinned? | Installed | Latest Available | Gap |
|---------|---------|-----------|-----------------|-----|
| `fastapi` | `>=0.100.0` (range) | 0.128.0 | 0.128.7 | Patch |
| `uvicorn` | `>=0.23.0` (range) | 0.40.0 | 0.40.0 | Current |
| `pydantic` | `>=2.0.0` (range) | 2.12.5 | 2.12.5 | Current |
| `pydantic-settings` | `>=2.0.0` (range) | 2.12.0 | 2.12.0 | Current (UNUSED) |
| `sqlalchemy` | `>=2.0.0` (range) | 2.0.45 | 2.0.46 | Patch |
| `alembic` | `>=1.12.0` (range) | 1.18.0 | 1.18.3 | Patch |
| `psycopg2-binary` | `>=2.9.0` (range) | 2.9.11 | 2.9.11 | Current |
| `asyncpg` | `>=0.29.0` (range) | 0.31.0 | 0.31.0 | Current |
| `passlib` | `>=1.7.4` (range) | 1.7.4 | 1.7.4 | Current |
| `bcrypt` | `>=3.2.0,<4.0.0` (pinned range) | 3.2.2 | 5.0.0 | Major (intentional pin - passlib 1.7.4 incompatible with 4.x+) |
| `cryptography` | `>=42.0.0` (range) | 46.0.3 | 46.0.4 | Patch |
| `python-multipart` | `>=0.0.6` (range) | 0.0.21 | 0.0.22 | Patch |
| `PyJWT` | `>=2.8.0` (range) | 2.10.1 | 2.11.0 | Minor |
| `email-validator` | `>=2.1.0` (range) | 2.3.0 | 2.3.0 | Current |
| `mcp` | `==1.12.3` (exact pin) | 1.12.3 | 1.26.0 | **Major** (13 minor versions behind, CVE-2025-66416) |
| `python-dotenv` | `>=1.0.0` (range) | 1.2.1 | 1.2.1 | Current |
| `pyyaml` | `>=6.0.0` (range) | 6.0.3 | 6.0.3 | Current |
| `click` | `>=8.1.0` (range) | 8.3.1 | 8.3.1 | Current |
| `colorama` | `>=0.4.6` (range) | 0.4.6 | 0.4.6 | Current |
| `httpx` | `>=0.25.0` (range) | 0.28.1 | 0.28.1 | Current |
| `aiohttp` | `>=3.9.0` (range) | 3.13.3 | 3.13.3 | Current |
| `websockets` | `>=12.0` (range) | 16.0 | 16.0 | Current |
| `psutil` | `>=5.9.0` (range) | 7.2.1 | 7.2.2 | Patch |
| `aiofiles` | `>=24.1.0` (range) | 25.1.0 | 25.1.0 | Current |
| `tiktoken` | `>=0.5.0` (range) | 0.12.0 | 0.12.0 | Current |
| `structlog` | `>=25.0.0` (range) | 25.5.0 | 25.5.0 | Current |
| `watchdog` | `>=3.0.0` (range) | 6.0.0 | 6.0.0 | Current |
| `sumy` | `>=0.11.0` (range) | 0.11.0 | 0.11.0 | Current |
| `nltk` | `>=3.8` (range) | 3.9.2 | 3.9.2 | Current |
| `numpy` | `>=1.24.0` (range) | 2.4.1 | 2.4.2 | Patch |
| `scipy` | `>=1.10.0` (range) | 1.17.0 | 1.17.0 | Current |

### Outdated Python Packages (patch/minor updates available)

| Package | Installed | Latest | Update Type |
|---------|-----------|--------|-------------|
| `fastapi` | 0.128.0 | 0.128.7 | Patch |
| `alembic` | 1.18.0 | 1.18.3 | Patch |
| `cryptography` | 46.0.3 | 46.0.4 | Patch |
| `python-multipart` | 0.0.21 | 0.0.22 | Patch |
| `sqlalchemy` | 2.0.45 | 2.0.46 | Patch |
| `numpy` | 2.4.1 | 2.4.2 | Patch |
| `psutil` | 7.2.1 | 7.2.2 | Patch |
| `PyJWT` | 2.10.1 | 2.11.0 | Minor |
| `mcp` | 1.12.3 | 1.26.0 | **Major** (security fix) |

---

## Frontend Dependencies

### Unused Production Dependencies (can be removed)

| Package | Listed In | Evidence of Non-Use |
|---------|-----------|-------------------|
| `@vue-flow/background` | dependencies | Zero imports of `@vue-flow` anywhere in `frontend/src/`. No flow diagram components exist. |
| `@vue-flow/controls` | dependencies | Same as above - zero references to vue-flow in source. |
| `@vue-flow/core` | dependencies | Same as above. |
| `@vue-flow/minimap` | dependencies | Same as above. |
| `chart.js` | dependencies | Zero imports of `chart.js` or `Chart` constructor found in `frontend/src/`. |
| `d3` | dependencies | Zero imports of `d3` found in `frontend/src/`. |
| `gsap` | dependencies | Zero imports of `gsap`, `ScrollTrigger`, `TimelineLite`, or `TweenMax` found in `frontend/src/`. |
| `socket.io-client` | dependencies | Zero imports of `socket.io-client` or `io(` found. The project uses **native WebSocket** (`new WebSocket()`) in `useWebSocket.js` composable and `websocket.js` store - not Socket.IO. |
| `vue-chartjs` | dependencies | Zero imports of `vue-chartjs` found. The `Bar`/`Line`/`Pie` matches from grep are standard Vue component names in other contexts (e.g., NavigationDrawer `<v-list-item>`), not chart components. |
| `vuedraggable` | dependencies | Zero imports of `vuedraggable` or `Draggable` component found in `frontend/src/`. |

### Unused Dev Dependencies (can be removed)

| Package | Listed In | Evidence of Non-Use |
|---------|-----------|-------------------|
| `@eslint/compat` | devDependencies | Not referenced in `eslint.config.js` or `.eslintrc.json`. |
| `tailwindcss` | devDependencies | No `tailwind.config.js` at project root. Zero usage of `@apply`, `@screen`, `@tailwind`, or any Tailwind utility classes in `frontend/src/`. The project uses Vuetify for styling. |
| `autoprefixer` | devDependencies | No `postcss.config.js` at project root. Only referenced in `package.json`. Typically paired with Tailwind which is unused. |

### Questionable Dev Dependencies

| Package | Listed In | Notes |
|---------|-----------|-------|
| `happy-dom` | devDependencies | Used in `vite.config.js` test section (`environment: 'happy-dom'`) BUT `vitest.config.js` uses `jsdom`. Two test environments exist simultaneously. |
| `jsdom` | devDependencies | Used in `vitest.config.js` (`environment: 'jsdom'`). The dual config should be consolidated. |
| `sass` + `sass-embedded` | devDependencies | Both installed. `sass-embedded` is the modern replacement for `sass` with identical API but better performance. Only one is needed. |
| `@vue/eslint-config-prettier` | devDependencies | Referenced in `.eslintrc.json` (legacy config) but NOT in `eslint.config.js` (flat config). If flat config is the active one, this can be removed. |

### Security Vulnerabilities

| Package | Installed Version | Vulnerability | Severity | Fix Available |
|---------|------------------|--------------|----------|---------------|
| `happy-dom` | 19.0.2 | GHSA-37j7-fg3j-429f: VM Context Escape leading to RCE + GHSA-qpm2-6cq5-7pq5: Code generation bypass | **CRITICAL** | 20.6.0 (breaking) |
| `axios` | 1.12.1 | GHSA-43fc-jf86-j433: DoS via `__proto__` key in mergeConfig | **HIGH** (CVSS 7.5) | Latest (npm audit fix) |
| `glob` (transitive) | 10.x | GHSA-5j98-mcp5-4vw2: Command injection via -c/--cmd | **HIGH** (CVSS 7.5) | 10.5.0+ |
| `js-yaml` | 4.1.0 | GHSA-mh29-5h37-fv8m: Prototype pollution in merge (`<<`) | Moderate (CVSS 5.3) | 4.1.1 |
| `lodash-es` | 4.17.21 | GHSA-xxjr-mmjv-4gpg: Prototype Pollution in `_.unset` and `_.omit` | Moderate (CVSS 6.5) | 4.17.23+ |
| `lodash` (transitive) | 4.17.21 | GHSA-xxjr-mmjv-4gpg: Same as above | Moderate (CVSS 6.5) | 4.17.23+ |
| `vite` | 7.1.9 | GHSA-93m4-6634-74q7: `server.fs.deny` bypass via backslash on Windows | Moderate | 7.1.11+ |

**The `vite` vulnerability is particularly relevant**: this project runs on Windows (`win32` platform) and the bypass uses backslash path traversal specific to Windows.

### Version Pinning Status (npm)

All npm dependencies use caret ranges (`^`), which allows minor and patch updates. This is standard practice for npm and is acceptable. The `package-lock.json` ensures reproducible installs.

| Package | Specified | Installed | Notes |
|---------|-----------|-----------|-------|
| `vue` | ^3.4.0 | 3.5.21 | Stable |
| `vuetify` | ^3.4.0 | 3.10.0 | Stable |
| `pinia` | ^3.0.3 | 3.0.3 | Current |
| `vue-router` | ^4.2.0 | 4.5.1 | Stable |
| `axios` | ^1.6.0 | 1.12.1 | Has vulnerability |
| `date-fns` | ^3.0.0 | 3.6.0 | Stable |
| `lodash-es` | ^4.17.21 | 4.17.21 | Has vulnerability, no fix in ^4 range |
| `marked` | ^17.0.0 | 17.0.0 | Current |
| `vite` | ^7.1.8 | 7.1.9 | Has vulnerability |

---

## Duplicate/Redundant Dependencies

### 1. `sass` + `sass-embedded` (npm devDependencies)
Both provide identical SCSS compilation functionality. `sass-embedded` uses a native Dart VM for better performance. The `vite.config.js` uses `scss: { api: 'modern-compiler' }` which works with either. **Recommendation**: Keep `sass-embedded`, remove `sass`.

### 2. `httpx` + `aiohttp` (Python)
Both are async HTTP clients. `httpx` is used in 80+ files (tests, API endpoints, tools). `aiohttp` is used in 5 files (agent coordination, mock simulators). Both serve distinct purposes -- `httpx` for general HTTP and `aiohttp` specifically for WebSocket client functionality. **Verdict**: Not a true duplicate; both are justified.

### 3. `happy-dom` + `jsdom` (npm devDependencies)
Two DOM simulation libraries for testing. `vite.config.js` configures `happy-dom`, while `vitest.config.js` configures `jsdom`. This indicates a configuration drift between two test configs. **Recommendation**: Consolidate on one test environment (preferably `jsdom` since `happy-dom` has critical CVEs). Remove the unused one.

### 4. `.eslintrc.json` + `eslint.config.js` (ESLint configs)
Two ESLint configuration files coexist. ESLint v9+ uses flat config (`eslint.config.js`) by default, but the legacy `.eslintrc.json` is also present with different rules. The `eslint.config.js` uses `@babel/eslint-parser` but does NOT use `@eslint/compat` or `@vue/eslint-config-prettier`. **Recommendation**: Consolidate to one config (prefer flat config for ESLint 9+).

### 5. `@vue-flow/*` (4 packages) + `d3` + `chart.js` + `vue-chartjs`
Multiple visualization libraries installed but none are used. These appear to be aspirational dependencies added for future features that were never implemented. **Recommendation**: Remove all.

---

## Dev Dependencies in Production

### Python: Clean Separation
Dev tools are properly separated:
- `requirements.txt` -- production only (correct)
- `dev-requirements.txt` -- pytest, black, ruff, mypy, mkdocs (correct)

No dev tools found in the main `requirements.txt`. This is good.

### npm: Clean Separation
All dev tools are correctly in `devDependencies`:
- Testing: vitest, @vue/test-utils, @playwright/test, happy-dom, jsdom
- Linting: eslint, prettier, eslint-plugin-vue
- Build: vite, sass, postcss
- Coverage: @vitest/coverage-v8

No dev tools found in `dependencies`. This is good.

---

## False Positive Analysis

The following 20 packages were validated to confirm they are NOT false positives for "unused" claims:

| # | Package | Initially Flagged? | Validation | Verdict |
|---|---------|-------------------|------------|---------|
| 1 | `uvicorn` | No | CLI tool (`python -m uvicorn`), imported in `run_api.py` | **Used** (runtime CLI) |
| 2 | `python-multipart` | Considered | Required by FastAPI for `UploadFile`/`File()` - used in `vision_documents.py`, `downloads.py`, `claude_export.py`. Not directly imported. | **Used** (implicit runtime dep) |
| 3 | `bcrypt` | No | Backend for `passlib[bcrypt]`. Directly imported in `auth_utils.py` and test files. | **Used** |
| 4 | `numpy` | Considered | Not directly imported BUT required by `sumy` for LSA matrix operations. Transitive runtime dependency. | **Used** (transitive) |
| 5 | `scipy` | Considered | Not directly imported BUT required by `sumy` for SVD in LSA summarization. | **Used** (transitive) |
| 6 | `pydantic-settings` | Yes | Zero imports of `pydantic_settings`, `BaseSettings`, or any settings class. Config uses `pyyaml` + `dataclass`. | **UNUSED** (confirmed) |
| 7 | `watchdog` | No | Imported in `config_manager.py` for file system event monitoring (hot-reload). | **Used** |
| 8 | `click` | No | Imported in `install.py`, `startup.py`, `startup_prod.py` for CLI. | **Used** |
| 9 | `colorama` | No | Imported in `startup.py`, `install.py`, `colored_logger.py` for terminal colors. | **Used** |
| 10 | `structlog` | No | Imported in 14 files across `logging/`, `tools/context_tools/`, `services/`. | **Used** |
| 11 | `socket.io-client` (npm) | Yes | Zero imports. WebSocket store uses `new WebSocket()` natively. | **UNUSED** (confirmed) |
| 12 | `chart.js` (npm) | Yes | Zero imports of Chart.js constructor or registration. | **UNUSED** (confirmed) |
| 13 | `d3` (npm) | Yes | Zero imports of d3 modules. | **UNUSED** (confirmed) |
| 14 | `gsap` (npm) | Yes | Zero imports of gsap or any animation library. | **UNUSED** (confirmed) |
| 15 | `vue-chartjs` (npm) | Yes | Zero imports of vue-chartjs components. | **UNUSED** (confirmed) |
| 16 | `vuedraggable` (npm) | Yes | Zero imports of draggable components. | **UNUSED** (confirmed) |
| 17 | `@vue-flow/*` (npm) | Yes | Zero imports of any vue-flow modules. | **UNUSED** (confirmed) |
| 18 | `js-yaml` (npm) | Considered | Used in `vite.config.js` (build tool) to read `config.yaml` for dev server proxy. NOT in `src/`. | **Used** (build-time) |
| 19 | `lodash-es` (npm) | Considered | Imported `debounce` in `useAutoSave.js`. Only 1 function used from large library. | **Used** (but consider replacing with native `setTimeout`-based debounce) |
| 20 | `tailwindcss` (npm) | Yes | No config file, zero utility classes, Vuetify is the styling framework. | **UNUSED** (confirmed) |

---

## Recommendations

### Priority 1: Security Fixes (Immediate)

1. **Upgrade MCP SDK**: `mcp==1.12.3` -> `mcp>=1.23.0` (CVE-2025-66416, HIGH severity)
   - Risk: API changes between 1.12 and 1.23 need validation
   - The requirements.txt comment says pinned for "serena-agent compatibility" -- test serena integration after upgrade
   - This is the only Python CVE found

2. **Run `npm audit fix`**: Resolves 4 of 7 npm vulnerabilities automatically:
   - `axios` -> patched version
   - `js-yaml` -> 4.1.1
   - `glob` (transitive) -> patched
   - `vite` -> 7.1.11+ (Windows `server.fs.deny` bypass -- directly relevant to this project)

3. **Upgrade `happy-dom`**: 19.0.2 -> 20.6.0 (CRITICAL RCE -- but this is a breaking change, and the package may be removable entirely; see below)

### Priority 2: Remove Unused Dependencies

4. **Remove unused npm production dependencies** (save ~15-20 MB, reduce attack surface):
   ```json
   // Remove from "dependencies" in package.json:
   "@vue-flow/background"
   "@vue-flow/controls"
   "@vue-flow/core"
   "@vue-flow/minimap"
   "chart.js"
   "d3"
   "gsap"
   "socket.io-client"
   "vue-chartjs"
   "vuedraggable"
   ```

5. **Remove unused npm dev dependencies**:
   ```json
   // Remove from "devDependencies" in package.json:
   "@eslint/compat"
   "tailwindcss"
   "autoprefixer"
   ```

6. **Remove `pydantic-settings`** from `requirements.txt`:
   - Zero usage anywhere in codebase
   - Configuration is handled by `config_manager.py` using `pyyaml` + `dataclass`

7. **Uninstall `python-jose`** (installed but not in requirements.txt, zero imports):
   ```
   pip uninstall python-jose
   ```

### Priority 3: Consolidation

8. **Consolidate SCSS compilers**: Remove `sass` from `devDependencies`, keep `sass-embedded` (better performance, same API)

9. **Consolidate test DOM environments**: Choose one of `happy-dom` or `jsdom`:
   - Recommended: Keep `jsdom` (used by `vitest.config.js`), remove `happy-dom` (has critical CVEs, only in `vite.config.js` test section)
   - Update `vite.config.js` test environment from `happy-dom` to `jsdom`

10. **Consolidate ESLint configs**: Remove `.eslintrc.json` (legacy), keep `eslint.config.js` (flat config for ESLint 9+)
    - After removal, `@vue/eslint-config-prettier` can also be removed from devDependencies

### Priority 4: Version Pinning Strategy

11. **Consider tighter pinning for Python production dependencies**:
    - Current: Most use `>=X.Y.Z` (allows any future version)
    - Recommended: Use `~=X.Y.Z` (compatible release, e.g., `~=0.128.0` allows 0.128.x but not 0.129.0)
    - This prevents unexpected breaking changes on fresh installs while still accepting patch updates
    - Critical packages to pin: `fastapi`, `sqlalchemy`, `pydantic`, `asyncpg`

12. **Consider replacing `lodash-es`** with a native debounce utility:
    - Only 1 function (`debounce`) is used from the entire lodash library
    - A 10-line native implementation would eliminate the dependency and its moderate-severity vulnerability
    - Alternatively, use `lodash-es/debounce` (tree-shaking should already handle this)

### Priority 5: Patch Updates (Low Risk)

13. **Apply available Python patch updates** (all low-risk):
    - `fastapi` 0.128.0 -> 0.128.7
    - `alembic` 1.18.0 -> 1.18.3
    - `cryptography` 46.0.3 -> 46.0.4
    - `sqlalchemy` 2.0.45 -> 2.0.46
    - `python-multipart` 0.0.21 -> 0.0.22
    - `numpy` 2.4.1 -> 2.4.2
    - `psutil` 7.2.1 -> 7.2.2

---

## Appendix: File Locations

| File | Purpose |
|------|---------|
| `F:\GiljoAI_MCP\requirements.txt` | Python production dependencies (30 packages) |
| `F:\GiljoAI_MCP\dev-requirements.txt` | Python development dependencies (7 packages) |
| `F:\GiljoAI_MCP\dev_tools\requirements.txt` | Dev control panel dependencies (3 packages) |
| `F:\GiljoAI_MCP\dev_tools\simulator\requirements.txt` | Simulator dependencies (5 packages) |
| `F:\GiljoAI_MCP\frontend\package.json` | npm dependencies (14 prod + 22 dev = 36 packages) |
| `F:\GiljoAI_MCP\frontend\package-lock.json` | npm lock file for reproducible installs |
| `F:\GiljoAI_MCP\frontend\vite.config.js` | Vite build configuration (uses js-yaml, happy-dom) |
| `F:\GiljoAI_MCP\frontend\vitest.config.js` | Vitest test configuration (uses jsdom) |
| `F:\GiljoAI_MCP\frontend\eslint.config.js` | ESLint flat config (active for ESLint 9+) |
| `F:\GiljoAI_MCP\frontend\.eslintrc.json` | ESLint legacy config (may be inactive) |
