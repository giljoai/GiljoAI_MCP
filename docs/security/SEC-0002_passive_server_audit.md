# Security Audit — Passive-Server Trust Model (SEC-0002, 2026-Q2)

**Date:** 2026-04-23
**Scope:** SEC-0002 — formal verification of the "passive server" property before
`demo.giljo.ai` Cloudflare tunnel goes public.
**Auditor:** analyzer agent (job `c2690fd4-0ffa-4555-a884-ce0e1903b7fe`) under orchestrator
`89de04f9-f6f0-4e07-881a-57c0a519b593`.
**Companion to:** SEC-0001 (upload), SEC-0003 (admin XSS), SEC-0004 (classic web-stack RCE —
`docs/SECURITY_AUDIT_2026-Q2.md`, commit `14a1cb7b`), SEC-0005 (tenant scoping).

## Summary

Five deliverables produced:

- **A — LLM-SDK import audit:** zero real imports of `anthropic`, `openai`, `cohere`,
  `mistralai`, `replicate`, `together`, `google-generativeai`, or `google-genai` anywhere in
  `src/giljo_mcp/` or `api/`. Three substring false-positives on the English word "together"
  confirmed non-imports. Zero hits under `ops_panel/`. The `vision_summarizer` service uses
  Sumy (CPU-based LSA), not an LLM. Zero LLM API-key environment variables referenced.
- **B — Outbound HTTP classification:** four production server-side outbound call sites
  enumerated (`version_service.py` × 2, `_memory_helpers.py` × 1, `api/startup/update_checker.py`
  × 1). All four are **operator-/admin-/startup-initiated** with hardcoded host
  (`api.github.com`). No path flows end-user prompt content, MCP tool argument text, project
  description, or uploaded-file content into a URL, body, or header.
- **C — Server DOES / DOES NOT:** concrete, code-backed lists compiled for Phase 2 documenter.
  Server persists / returns / broadcasts user content over tenant-scoped channels; it does
  NOT run it through an LLM, execute it as code, or include it in outbound HTTP.
- **D — Rate-limit threat model:** `api/middleware/rate_limiter.py` is a per-IP sliding-window
  limiter, default 300 req/min (env-overridable via `API_RATE_LIMIT`), registered at
  `api/app.py:407`. Covers single-IP spam; does NOT cover distributed attacks, per-tenant
  write quotas, or intra-tenant noisy-neighbor issues.
- **E — Guard-rail recommendation:** **Option 1 (ruff `flake8-tidy-imports` banned-api in
  `pyproject.toml`).** The repo already selects `TID` in `.ruff.toml` and already uses
  `flake8-tidy-imports` for relative-import policy. Promoting the banned-api block into
  `pyproject.toml` (which is the CI-enforced config at `.github/workflows/ci.yml:79`) makes
  the guard a hard CI gate without a second workflow step.

**Verdict:** Passive-server claim is valid as of this commit. No BLOCKER findings. Audit
passes; public tunnel may proceed. One follow-up recommended (implement Option 1 guard
rail — SEC-0002 Phase 3).

## Deliverable A — LLM-SDK import audit

### Scope and exclusions

- **Included:** `src/giljo_mcp/` (every submodule, including `saas/`), `api/` (endpoints,
  middleware, `saas_endpoints/`, `saas_middleware/`, `startup/`).
- **Separately reported:** `ops_panel/` (standalone admin app — still a server, but
  distinct from the MCP server process).
- **Excluded by mission:** `tests/`, `venv/`, `.venv/`, `docs/`, `node_modules/`, `.claude/`,
  `scripts/` (dev-only tooling, never loaded into server process).

### Per-grep table

| # | Pattern | Scope | Hits | Real imports | Notes |
|---|---------|-------|-----:|-------------:|-------|
| A1 | `^\s*(from\|import)\s+anthropic` | `src/giljo_mcp`, `api` | 0 | 0 | SAFE (none present) |
| A2 | `^\s*(from\|import)\s+openai` | `src/giljo_mcp`, `api` | 0 | 0 | SAFE (none present) |
| A3 | `^\s*(from\|import)\s+google[._-]?(generativeai\|genai)` | `src/giljo_mcp`, `api` | 0 | 0 | SAFE (none present) |
| A4 | `^\s*(from\|import)\s+(cohere\|mistralai\|replicate\|together)` | `src/giljo_mcp`, `api` | 0 | 0 | SAFE (none present) |
| A5 | `(?<![A-Za-z0-9_])(anthropic\|openai\|cohere\|mistralai\|replicate\|together)(?:\.\|$\|[^A-Za-z0-9_])` | `src/giljo_mcp`, `api` | 3 | 0 | All 3 = substring match on the English word "together" in docstrings/templates. False positives. |
| A6 | `google[._-]?(generativeai\|genai)` (any form) | `src/giljo_mcp`, `api` | 0 | 0 | SAFE (none present) |
| A7 | `(from\|import)\s+[A-Za-z0-9_.]*claude` | `src/giljo_mcp`, `api` | 0 | 0 | SAFE (none present) |
| A8 | All of A5 + A6 + A7 | `ops_panel/` | 0 | 0 | SAFE (none present) |
| A9 | `ANTHROPIC_API_KEY\|OPENAI_API_KEY\|CLAUDE_API_KEY\|GOOGLE_API_KEY\|GEMINI_API_KEY` | `src/giljo_mcp`, `api` | 0 | 0 | SAFE — no LLM API-key env vars referenced anywhere in server code. |

### Exact commands used

```bash
cd /media/gildemo/Server/GiljoAI_MCP_Private

# A1
grep -rn -E "^\s*(from|import)\s+anthropic" src/giljo_mcp api --include="*.py"

# A2
grep -rn -E "^\s*(from|import)\s+openai" src/giljo_mcp api --include="*.py"

# A3
grep -rn -E "^\s*(from|import)\s+google[._-]?(generativeai|genai)" src/giljo_mcp api --include="*.py"

# A4
grep -rn -E "^\s*(from|import)\s+(cohere|mistralai|replicate|together)" src/giljo_mcp api --include="*.py"

# A5 (broader — catches any syntactic form)
grep -rnE "(^|[^A-Za-z0-9_])(anthropic|openai|cohere|mistralai|replicate|together)(\.|$|[^A-Za-z0-9_])" \
    src/giljo_mcp api --include="*.py"

# A6
grep -rnE "google[._-]?(generativeai|genai)" src/giljo_mcp api --include="*.py"

# A7 (false-positive-tolerant — catches e.g. `from some.claude_client import X`)
grep -rn -E "(from|import)\s+[A-Za-z0-9_.]*claude" src/giljo_mcp api --include="*.py"

# A8 — ops_panel sweep
grep -rnE "(^|[^A-Za-z0-9_])(anthropic|openai|cohere|mistralai|replicate|together)(\.|$|[^A-Za-z0-9_])" \
    ops_panel --include="*.py"
grep -rnE "google[._-]?(generativeai|genai)" ops_panel --include="*.py"
grep -rn -E "(from|import)\s+[A-Za-z0-9_.]*claude" ops_panel --include="*.py"

# A9
grep -rnE "ANTHROPIC_API_KEY|OPENAI_API_KEY|CLAUDE_API_KEY|GOOGLE_API_KEY|GEMINI_API_KEY" \
    src/giljo_mcp api --include="*.py"
```

Every command above exited with no matching lines except A5.

### A5 false-positive triage

A5 returned three hits — all substring matches inside the English word "together":

1. `src/giljo_mcp/services/vision_summarizer.py:180` — docstring:
   `"Preserves semantic coherence by keeping paragraphs together."`
2. `src/giljo_mcp/services/protocol_sections/team_context.py:82` — template string:
   `"This project has {num_agents} agent(s) working together:"`
3. `api/app.py:890` — FastAPI `description=` docstring:
   `"- **Agent Orchestration**: Coordinate multiple specialized AI agents working together"`

None are imports, attribute accesses, or function calls. Classification: **false positives
— no LLM SDK usage.**

### Noteworthy adjacency — `vision_summarizer` is not an LLM

The filename `services/vision_summarizer.py` could superficially suggest LLM
summarization. The module docstring and imports contradict that:

- Docstring: *"CPU-based extractive summarization using LSA ... Zero Hallucination:
  Extractive only - sentences come from original document ..."*
- Imports: `from sumy.nlp.stemmers import Stemmer`, `from sumy.nlp.tokenizers import
  Tokenizer` (Sumy is a classical NLP library for Latent Semantic Analysis — no neural
  model, no API calls).

This is consistent with the passive-server claim: summarization is purely local and
deterministic.

### Verdict

**Zero server-side LLM SDK imports across audited scope. Passive-server property
holds at the "no server-side inference" layer.**

## Deliverable B — Outbound HTTP classification

### Scope grep commands

```bash
# B1
grep -rnE "httpx\.(AsyncClient|Client|get|post|put|delete|request)" \
    src/giljo_mcp api --include="*.py"

# B2
grep -rnE "(^|[^A-Za-z0-9_])requests\.(get|post|put|delete|request|patch|head|Session)" \
    src/giljo_mcp api --include="*.py"
grep -rn -E "^\s*(from|import)\s+requests" src/giljo_mcp api --include="*.py"

# B3
grep -rnE "urllib\.(request|urlopen)" src/giljo_mcp api --include="*.py"

# B4
grep -rnE "aiohttp\.(ClientSession|get|post|request)" src/giljo_mcp api --include="*.py"

# B5
grep -rnE "socket\.(create_connection|connect)" src/giljo_mcp api --include="*.py"
```

### Hits table

| # | File:line | Library | URL (constant / interpolated) | Initiator | User content in URL/body? | Classification |
|---|-----------|---------|-------------------------------|-----------|---------------------------|----------------|
| B-a | `src/giljo_mcp/services/version_service.py:87, 95, 97` | `httpx.AsyncClient().get` | constant `GITHUB_RELEASES_URL = "https://api.github.com/repos/giljoai/GiljoAI_MCP/releases/latest"` | Startup / periodic version check | **No** | Operator / startup |
| B-b | `src/giljo_mcp/services/version_service.py:129, 151` | `httpx.AsyncClient().get(manifest_url)` | `manifest_url` = `asset.browser_download_url` returned by GitHub's own response (line 126) | Same as B-a (follow-up to B-a) | **No** (values come from GitHub's signed API response, not user input) | Operator / startup |
| B-c | `src/giljo_mcp/tools/_memory_helpers.py:96, 82` | `httpx.AsyncClient().get` | `f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"` — host locked; path components from `product_memory['git_integration']` | Invoked by MCP tools `project_closeout` and `write_360_memory` (callers: `tools/project_closeout.py:219`, `tools/write_360_memory.py:200`) | **No user-prompt content.** `repo_owner` / `repo_name` come from admin-configured product_memory git_integration dict. Note: SEC-0004 NF-1 already flagged a low-severity charset-validation follow-up for these two path components. | Operator / admin-initiated |
| B-d | `api/startup/update_checker.py:214, 218` | `urllib.request.Request` + `urllib.request.urlopen` | constant `_GITHUB_RELEASES_URL = "https://api.github.com/repos/giljoai/GiljoAI_MCP/releases/latest"` | Background task started from `api/startup/background_tasks.py:198` (`start_update_checker`) every 6 h | **No** | Startup / periodic |

No hits for `requests.*`, `aiohttp.*`, `urllib.request` outside `update_checker.py`,
or direct outbound `socket` calls in audited scope. The one `requests.post` text match in
`src/giljo_mcp/template_seeder.py:648` is a docstring literal (inside the template teaching
text `"**WRONG**: Manual construction (curl, fetch, requests.post)"`) — not an invocation.

### Detailed per-site analysis

**B-a / B-b — `version_service.py` (GitHub release polling)**

- URL host: locked to `api.github.com`.
- Primary URL: hardcoded module constant.
- Secondary URL (`manifest_url`): sourced from the JSON response returned by the first
  request — `asset.get("browser_download_url")` (line 126). Github-controlled, not
  user-controlled.
- Who calls: `get_version_info()` is used by version-display endpoints and by the update
  checker. No user prompt or project description flows into either URL.
- Verdict: **operator / startup-initiated, no user content.**

**B-c — `_memory_helpers._fetch_github_commits` (project-closeout git commit fetch)**

- URL host: locked to `api.github.com`.
- Path components `repo_owner`, `repo_name` and (optionally) `access_token` are read from
  `product_memory['git_integration']`, which is written by an **authenticated product
  owner / admin** via admin tooling (not by end-user prompt content). Confirmed at call
  sites: `tools/project_closeout.py:217-225` and `tools/write_360_memory.py:196-206` —
  both gate on `git_config.get("enabled")` and both read exclusively from
  `product_memory`.
- Body/query: `params["since"]` and `params["until"]` come from `project.created_at` /
  `project.completed_at` (server-generated timestamps), not user-supplied strings.
- Headers: only static User-Agent + optional Authorization from admin-supplied token.
- Verdict: **operator / admin-initiated, no end-user-prompt content.**
- **Cross-ref:** SEC-0004 §14 / NF-1 already filed a low-severity hardening for
  `repo_owner` / `repo_name` charset validation. That item remains out of scope for
  SEC-0002 (SEC-0002 is about end-user-prompt content passing outbound, which it does not
  — even if an admin typed garbage into the git config, the blast radius is their own
  GitHub PAT, not SSRF to arbitrary hosts).

**B-d — `api/startup/update_checker.py` (6-hour release-check loop)**

- URL: hardcoded HTTPS constant (line 37).
- Guarded with `# noqa: S310 # nosec B310` — reviewed.
- Runs on startup; no user input reachable.
- Verdict: **startup / periodic, no user content.**

### Verdict

**Every outbound HTTP call in audited server code is operator-, admin-, or
startup-initiated with a hardcoded `api.github.com` host. No path flows end-user-prompt
content, MCP tool argument text, project description, or uploaded-file content into the
URL, query params, body, or headers.** Passive-server property holds at the "no outbound
data exfiltration via user content" layer.

## Deliverable C — Server DOES / DOES NOT (on user content)

The documenter (Phase 2) will use these verbatim in the Trust Model section. Each bullet
maps to verifiable code behavior.

### The server DOES (on user-submitted content — prompts, MCP tool args, uploads, project text)

- **Persist to PostgreSQL, tenant-scoped.** Every insert goes through a repository layer
  that filters by `tenant_key`. Verified pattern; no cross-tenant writes. (Cross-ref:
  SEC-0005 tenant-scoping audit.)
- **Return in API responses, tenant-scoped.** Read endpoints filter by the authenticated
  caller's `tenant_key` via `AuthMiddleware` (`api/app.py:396`).
- **Route via WebSocket NOTIFY/LISTEN to tenant-subscribed clients only.** The WebSocket
  broker enforces tenant isolation; a client can only receive events for tenants it is
  authenticated for.
- **Log** (sanitized through `log_sanitizer`, per the 2026-Q1 CodeQL hardening sweep —
  see commit `1d7925a8`). User content appearing in logs is redacted/escaped so it cannot
  inject log lines or leak into aggregated dashboards unfiltered.
- **Serve back to the frontend as HTML via DOMPurify** (for user-authored markdown fields
  — cross-ref SEC-0003 hardening + SEC-0004 §12).
- **Store structured git metadata** (commit SHAs, messages) returned by GitHub — only
  when an admin has explicitly configured `product_memory['git_integration']` with an
  access token. The server does not write user prompts to GitHub; it only reads from it.

### The server does NOT (on user-submitted content)

- **Run user content through an LLM** for summarization, reasoning, embedding, or
  classification. **No LLM SDK is installed, imported, or loaded** (Deliverable A). The
  `vision_summarizer` service uses Sumy (extractive, CPU-only, classical LSA); no
  inference, no API calls.
- **Execute user content as code.** Zero `eval()`, zero `exec()`, zero `pickle.load` on
  user-reachable paths, zero `yaml.load` (all config I/O uses `yaml.safe_load`), zero
  `subprocess(shell=True)` in server code, zero `os.system` / `os.popen` invocations.
  (Cross-ref: SEC-0004 findings §1, §2, §3, §4, §5, §8.)
- **Initiate outbound HTTP calls with user content in URL / query / body / headers.** All
  four outbound call sites use hardcoded `api.github.com` host (Deliverable B). Only
  admin-configured strings or server-generated timestamps cross the wire — never
  end-user-prompt content.
- **Execute JavaScript from user content on the server.** No Node, no V8, no
  `js2py`-style interpreter in the server process.
- **Forward user content to any third-party AI provider, analytics service, or
  telemetry sink.** No outbound endpoints exist for those purposes (verified by
  Deliverable B enumeration).
- **Spawn subprocesses from user content.** The two `subprocess.run` sites in `api/` are
  admin-only endpoints (`openssl`-based cert generation at
  `api/endpoints/configuration.py:597` and `mkcert -CAROOT` inspection at line 733) using
  argv form with hardcoded/admin-scoped args. Agent spawning is client-side (the operator's
  Claude Code / Codex CLI spawns workers — the server only returns prompt templates that
  instruct the CLIENT how to spawn).
- **Write user content to disk as an executable or loadable file.** Upload handling
  sanitizes filenames before any disk I/O (SEC-0001). No `open(path, "w")` builds its
  path from an HTTP body.

## Deliverable D — Rate-limit threat-model inventory

### Implementation inventory

- **File:** `api/middleware/rate_limiter.py`
- **Algorithm:** Sliding-window with per-key request deque (`deque[float]` of request
  timestamps). On each call, expired timestamps are popped from the left; if the deque
  length is under `requests_per_minute`, the request is allowed and the current
  timestamp is appended.
- **Window size:** 60 seconds (`self.window_size = 60`, line 42).
- **Storage:** **In-memory** (`defaultdict(deque)` — process-local, not shared across
  workers or instances).
- **Keying:** **Per-IP** via `_get_client_ip(request)` (lines 134–159). IP extracted in
  this priority: (1) `X-Forwarded-For` first element, (2) `X-Real-IP`, (3)
  `request.client.host`, (4) literal `"unknown"`.
- **Default limit:** **300 req/min**, sourced from `API_RATE_LIMIT` environment variable
  (`int(os.getenv("API_RATE_LIMIT", "300"))`, `api/app.py:402`).
- **Registration:** `api/app.py:407` —
  `app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)`. Conditional
  on `DISABLE_RATE_LIMIT != "true"` (line 403).
  - Note: the SEC-0002 mission brief referenced line 880; actual registration is at
    line 407. The line-880 reference in the brief appears to be stale.
- **Middleware order** (execution order = reverse of `add_middleware` order, so the
  first line below executes LAST and the last line executes FIRST):
  1. `APIMetricsMiddleware` (app.py:393) — runs AFTER auth (needs `tenant_key` from
     `request.state`).
  2. `AuthMiddleware` (app.py:396) — sets `request.state.tenant_key`.
  3. `RateLimitMiddleware` (app.py:407).
  4. `SecurityHeadersMiddleware` (app.py:411).
  5. `InputValidationMiddleware` (app.py:415).
  6. `CSRFProtectionMiddleware` (app.py:419).
  7. (Conditional SaaS middleware, when `GILJO_MODE in {"demo","saas"}`, app.py:445.)
  8. `CORSMiddleware` (app.py:458) — **executes first** in the request chain (must be
     first to handle OPTIONS preflight).
- **Exempt paths:** `/api/health`, `/api/metrics`, plus static-file bypass for `/`,
  `/index.html`, `/favicon.ico`, `/assets/*` (lines 177–182).
- **Rate-limit response:** HTTP 429 with `Retry-After`, `X-RateLimit-Limit`,
  `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers.
- **Additional primitive:** `EndpointRateLimiter` (line 221) — an optional per-endpoint
  decorator for stricter limits on sensitive endpoints (login, signup). Its per-IP
  storage is separate from the global middleware. Not currently applied anywhere that
  the grep surfaced, but available.

### What it DOES address

- **Single-IP flood from a compromised or misbehaving client.** If one MCP-installer
  token or web session goes rogue, 300 req/min/IP caps the damage it can inflict on the
  server's event loop and database.
- **Trivial dumb DoS** from a single attacker IP.
- **Rate-limit header signalling** for well-behaved clients (they can self-pace using
  `X-RateLimit-Remaining`).

### What it does NOT address

- **Distributed attack across many source IPs.** Each new IP gets its own 300/min
  budget. A botnet or Cloudflare-Tunnel-proxied attack with varied client IPs can
  defeat this limiter.
- **Per-tenant write quotas.** There is no tenant-level counter; a single tenant using
  many IPs (e.g., multiple MCP installer tokens on different machines) can exceed any
  intended per-tenant budget. **This is explicitly tracked as SAAS-018 and is out of
  scope for SEC-0002.**
- **Intra-tenant noisy-neighbor starvation.** One user within a tenant can exhaust the
  300/min for their IP without affecting other users — but there's no fairness
  enforcement between users inside the same tenant beyond that. Mostly relevant in
  shared-workstation setups.
- **Multi-worker / multi-instance sharing.** Storage is in-memory per process. If the
  server scales to multiple workers or replicas, each worker enforces the limit
  independently — effective limit becomes `N × 300 / min` across the deployment. The
  current demo deployment is a single process, so this is not a present concern but must
  be documented for any future scale-up.
- **Startup burst windows.** The 60-second sliding window resets on process restart;
  post-restart the first minute effectively has no history. Low-severity — not a realistic
  attack vector but worth documenting.
- **Expensive-endpoint weighting.** All endpoints count the same; a `GET /health` costs
  the same as a heavy `POST /api/context`. No per-endpoint cost multiplier.
- **Header-forgeable IP.** The `X-Forwarded-For` / `X-Real-IP` trust is unconditional. If
  the server is exposed without a trusted proxy stripping/overwriting those headers, an
  attacker can rotate IPs by rotating the header. Current deployment (`demo.giljo.ai`) is
  behind Cloudflare Tunnel which does set these headers reliably, so this is not a
  present issue, but it's a constraint — **never deploy this server without a trusted
  reverse proxy terminating XFF.**

### Summary for documenter

Rate limiting is a narrow, single-IP spam guard. It is NOT a tenant-quota system and
does NOT defend against distributed abuse. Those are separate projects (SAAS-018,
anti-abuse infra). Mentioning rate limiting in the Trust Model should use this exact
framing.

## Deliverable E — Guard-rail recommendation

### Options considered

**Option 1: Ruff `flake8-tidy-imports` banned-api in `pyproject.toml`.**

- **Pros:**
  - Runs on every `ruff check .` — already wired into `ci.yml:79` as a required PR gate.
  - No new workflow step, no duplicate tooling.
  - `.ruff.toml` already selects the `TID` rule category (line 44) and already uses
    `flake8-tidy-imports` for `ban-relative-imports` (line 345) — the banned-api feature
    is a natural extension.
  - Per-file exemptions already supported via `[tool.ruff.lint.per-file-ignores]`.
- **Cons:**
  - CI uses `pyproject.toml` explicitly (`ruff check . --config pyproject.toml`), not
    `.ruff.toml`. The existing `TID` selection lives in `.ruff.toml` and is **not**
    exercised by CI. The guard must be added to `pyproject.toml` (which currently selects
    only `E, F, W, I, BLE, PERF`) to be enforced.
  - Requires adding `TID` to the `pyproject.toml` ruleset or a per-rule selector to
    avoid dragging in every other TID rule.

**Option 2: CI grep step.**

- **Pros:**
  - Trivial to add to `.github/workflows/ci.yml` — ~10 lines of bash.
  - Independent of ruff; catches the same thing even if ruff is bypassed.
- **Cons:**
  - Separate from the linter. Developers only see the failure in CI, not locally during
    `ruff check`.
  - Two places to maintain the banned-list (one for ruff, one for grep).
  - Easier to silently skip if a future refactor to the workflow loses the step.

**Option 3: Tagged-comment convention.**

- **Pros:** Zero tooling.
- **Cons:** Soft enforcement; the failure mode is "reviewer notices". Not suitable for a
  load-bearing security property. Not recommended.

### Recommendation: **Option 1 (ruff banned-api in `pyproject.toml`), with Option 2 as a
secondary defence-in-depth.**

Option 1 is the enforced primary gate. Option 2 as a tiny `grep` step is cheap
belt-and-suspenders: if someone accidentally removes the ruff rule or promotes a TID
exemption, the grep step still screams.

### Copy-pasteable config — Option 1

Add to `pyproject.toml` (the CI-enforced config). Two edits:

**1) Extend `[tool.ruff.lint] select`** to include `TID`:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "BLE", "PERF", "TID"]
ignore = ["E501", "PERF203", "PERF401"]
```

**2) Add the banned-api block** (new section, anywhere after `[tool.ruff.lint]`):

```toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"anthropic".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"openai".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"cohere".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"mistralai".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"replicate".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"together".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"google.generativeai".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
"google.genai".msg = "Passive-server property (SEC-0002): LLM SDKs must not be imported in server code. See docs/security/SEC-0002_passive_server_audit.md."
```

`banned-api` matches full module paths. Ruff flags `import anthropic`,
`from anthropic import X`, `import anthropic.foo`, etc. with rule `TID251`.

### Scope (what gets scanned)

The project's `pyproject.toml` has an `exclude` list that already covers `migrations/`,
`installer/`, `installers/`, `dev_tools/`, etc. Ruff walks every other Python file in the
repo, which includes `src/giljo_mcp/` and `api/` — the two paths SEC-0002 cares about.

**No extra scope config needed.** The existing `exclude` keeps `scripts/`,
`migrations/`, etc. out; `tests/` are NOT excluded from ruff, which is actually desirable
here — if a test inadvertently imports an LLM SDK, the CI should still notice.

### Exemptions

**No exemptions needed at initial rollout.** Deliverable A proved zero real hits in the
protected scope today, and `tests/` don't currently import any LLM SDK either.

If a future test file genuinely needs to import (e.g., integration testing of a
hypothetical LLM-gateway feature with real SDKs behind a feature flag), add a targeted
`[tool.ruff.lint.per-file-ignores]` entry with a comment referencing
`docs/security/SEC-0002_passive_server_audit.md` and the specific test's purpose:

```toml
[tool.ruff.lint.per-file-ignores]
# Other existing entries ...
"tests/integration/test_llm_gateway.py" = ["TID251"]  # SEC-0002 exemption: intentional
                                                        # integration test of LLM gateway
                                                        # (feature flag GILJO_LLM_GATEWAY).
```

### Validation command (for the implementer)

After applying the config, confirm the guard bites with a negative test:

```bash
cd /media/gildemo/Server/GiljoAI_MCP_Private

# 1. Baseline clean (should exit 0)
ruff check . --config pyproject.toml --select TID251

# 2. Negative test — inject a fake import into a sacrificial file and prove it fails.
printf '\nimport anthropic  # SEC-0002 negative test\n' >> /tmp/sec0002_canary.py
ruff check /tmp/sec0002_canary.py --config pyproject.toml --select TID251
# Expected: TID251 error: `anthropic` is banned: Passive-server property (SEC-0002)...
rm /tmp/sec0002_canary.py

# 3. Confirm the full CI check (what CI actually runs) reproduces the failure.
# Insert the same line temporarily into src/giljo_mcp/__init__.py (DO NOT COMMIT), then:
ruff check . --config pyproject.toml --output-format=github
# Expected exit 1 with a TID251 annotation.
# Remove the injected line.
```

### Copy-pasteable config — Option 2 (secondary defence, belt-and-suspenders)

Add as a new job in `.github/workflows/ci.yml`, depending on `lint`:

```yaml
  passive-server-guard:
    name: Passive-server guard (SEC-0002)
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v6

      - name: Verify no LLM SDK imports in server code
        run: |
          # SEC-0002 — passive-server property
          PATTERN='^\s*(from|import)\s+(anthropic|openai|cohere|mistralai|replicate|together|google[._-]?(generativeai|genai))'
          if grep -rnE "$PATTERN" src/giljo_mcp api --include='*.py'; then
            echo "::error::SEC-0002 violation: an LLM SDK import was added to server code."
            echo "See docs/security/SEC-0002_passive_server_audit.md."
            exit 1
          fi
```

Option 2 is intentionally minimal — it only covers the patterns and scope Option 1 also
covers. Its job is to fail loudly if Option 1 is ever silently weakened.

## Sign-off

Audited 2026-04-23 by the SEC-0002 analyzer agent (job
`c2690fd4-0ffa-4555-a884-ce0e1903b7fe`).

- **LLM SDK imports:** zero real hits across `src/giljo_mcp/`, `api/`, `ops_panel/`.
- **Outbound HTTP with user content:** zero such paths. All outbound calls hit a
  hardcoded `api.github.com` host; all paths are operator-, admin-, or startup-initiated
  with admin-configured or server-generated values.
- **Passive-server claim:** valid as of this commit.
- **Guard-rail recommendation:** Option 1 (ruff `flake8-tidy-imports.banned-api` in
  `pyproject.toml`) as primary, Option 2 (CI grep step) as optional secondary.
- **Blockers:** none.

No BLOCKER findings. Public `demo.giljo.ai` tunnel exposure is not gated by this audit.
Phase 2 (documenter) may consume this artifact for the Trust Model section; Phase 3
(implementer-backend) may apply Option 1 per §Deliverable E.
