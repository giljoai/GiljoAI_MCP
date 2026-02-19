# Handover 0397: Deprecate stdio Proxy for Codex Native HTTP Support

**Status**: Ready for Execution
**Priority**: MEDIUM
**Estimated Effort**: 2-3 hours
**Risk Level**: Low (non-breaking change, documentation-focused)
**Complexity**: Low (research-validated deprecation path)

---

## Executive Summary

### What
Deprecate the stdio-to-HTTP proxy (`mcp_http_stdin_proxy.py`) and migrate Codex CLI users to native HTTP transport support introduced in Codex v0.44.0+ (October 2025).

### Why
**Research Findings** (2026-02-07):
- Codex CLI now has **native streamable HTTP support** since v0.44.0 (October 2025)
- Users can connect directly to GiljoAI's `/mcp` HTTP endpoint without proxy
- The `mcp` package (v1.12.3) has a security vulnerability (GHSA-9h52-p55h-vw2f)
- The proxy adds unnecessary complexity and maintenance burden

### Goal
1. Mark stdio proxy as **DEPRECATED** with clear migration path
2. Update documentation to show native HTTP configuration
3. Remove `mcp` package dependency (eliminates security vulnerability)
4. Simplify installation for Codex users

---

## Research Validation

### Codex HTTP Support Timeline

| Date | Event | Details |
|------|-------|---------|
| **Sept 2025** | Alpha releases | Experimental `streamable HTTP` support added with feature flag |
| **Oct 2025 (v0.44.0)** | Initial implementation | HTTP/SSE support with `url` and `bearer_token` config |
| **Oct 2025 (v0.46.0)** | Enhanced support | OAuth login, improved authentication, stability fixes |
| **Feb 2026** | Current | Native HTTP is production-ready |

**Sources**:
- [Codex MCP Documentation](https://developers.openai.com/codex/mcp) - Official transport types
- [PR #4317](https://github.com/openai/codex/pull/4317) - Original HTTP support PR
- [Release 0.46.0](https://github.com/openai/codex/releases/tag/rust-v0.46.0) - Enhanced HTTP support

### Current Proxy Usage

**File**: `src/giljo_mcp/mcp_http_stdin_proxy.py` (128 lines)
- **Purpose**: Bridge Codex stdio expectation → GiljoAI HTTP MCP server
- **Dependencies**: `mcp==1.12.3` (has security vulnerability)
- **Usage**: Referenced in Codex installation docs

**Zero production usage** - only used by external Codex CLI users who configure it.

---

## Phase 1: Documentation Updates

### 1.1 Update Installation Docs

**File**: `docs/INSTALLATION_FLOW_PROCESS.md` or Codex-specific guide

**Add section**: "Codex CLI Native HTTP Configuration (Recommended)"

```markdown
## Codex CLI Configuration (Recommended: Native HTTP)

Codex CLI v0.44.0+ supports native HTTP transport. Connect directly to GiljoAI without a proxy.

### Prerequisites
- Codex CLI v0.44.0 or later
- GiljoAI MCP server running (default: http://localhost:7272)
- API key from GiljoAI dashboard

### Configuration

1. Enable experimental HTTP client:
```toml
# ~/.codex/config.toml
[features]
experimental_use_rmcp_client = true
```

2. Add GiljoAI MCP server:
```toml
[mcp_servers.giljo]
url = "http://localhost:7272/mcp"
bearer_token_env_var = "GILJO_API_KEY"
```

3. Set your API key:
```bash
export GILJO_API_KEY="your-api-key-here"
```

4. Verify connection:
```bash
codex mcp list
# Should show "giljo" in the list
```

### Alternative: CLI Command
```bash
codex mcp add giljo --url http://localhost:7272/mcp
```

Then configure authentication in `~/.codex/config.toml` as shown above.
```

**Add deprecation notice** for stdio proxy:

```markdown
### Legacy: stdio Proxy (Deprecated)

**⚠️ DEPRECATED**: The stdio proxy is no longer needed as of Codex v0.44.0+.

If you're using Codex CLI v0.43.x or earlier, see [Legacy stdio Proxy Guide](./legacy_stdio_proxy.md).

For modern Codex versions, use the native HTTP configuration above.
```

### 1.2 Create Legacy Guide

**File**: `docs/legacy_stdio_proxy.md` (new file)

Move current stdio proxy documentation here with clear deprecation warnings.

---

## Phase 2: Code Deprecation

### 2.1 Mark Proxy Module as Deprecated

**File**: `src/giljo_mcp/mcp_http_stdin_proxy.py`

Add deprecation warnings at top of file:

```python
"""
StdIO -> HTTP MCP proxy for Codex CLI.

⚠️ DEPRECATED (2026-02-07):
This proxy is no longer needed as of Codex CLI v0.44.0+ (October 2025).
Codex now has native HTTP transport support.

For modern Codex installations, configure native HTTP:
    [mcp_servers.giljo]
    url = "http://localhost:7272/mcp"
    bearer_token_env_var = "GILJO_API_KEY"

See: docs/INSTALLATION_FLOW_PROCESS.md

This module will be removed in v4.0 (scheduled: Q2 2026).
"""

import warnings

warnings.warn(
    "mcp_http_stdin_proxy is deprecated. "
    "Use Codex native HTTP transport instead. "
    "See docs/INSTALLATION_FLOW_PROCESS.md for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)
```

### 2.2 Update Requirements

**File**: `requirements.txt`

Change from:
```
mcp==1.12.3                 # MCP SDK (pinned for serena-agent compatibility)
```

To:
```
# mcp==1.12.3               # DEPRECATED (2026-02-07): Only needed for legacy stdio proxy
                            # Proxy deprecated in favor of Codex native HTTP (v0.44.0+)
                            # Uncomment if you need legacy stdio proxy support
                            # Security note: v1.12.3 has vulnerability GHSA-9h52-p55h-vw2f
```

**File**: `pyproject.toml`

Change from:
```toml
dependencies = [
    "mcp==1.12.3",
    ...
]
```

To:
```toml
dependencies = [
    # Removed: mcp==1.12.3 (stdio proxy deprecated 2026-02-07)
    ...
]

[project.optional-dependencies]
legacy-codex-proxy = [
    "mcp==1.12.3",  # Legacy stdio proxy for Codex CLI <v0.44.0
]
```

This allows users who need the proxy to install with:
```bash
pip install giljo-mcp[legacy-codex-proxy]
```

---

## Phase 3: User Communication

### 3.1 Update CHANGELOG.md

Add entry:

```markdown
## [v3.3.x] - 2026-02-07

### Deprecated
- **stdio MCP Proxy** (`mcp_http_stdin_proxy.py`): Codex CLI v0.44.0+ supports native HTTP transport. The proxy is no longer needed. Migration guide: [docs/INSTALLATION_FLOW_PROCESS.md](docs/INSTALLATION_FLOW_PROCESS.md)
- **mcp package dependency**: Moved to optional dependency `[legacy-codex-proxy]`

### Security
- Removed `mcp==1.12.3` from core dependencies (had vulnerability GHSA-9h52-p55h-vw2f)

### Migration Guide
Codex users should:
1. Upgrade to Codex CLI v0.44.0+
2. Configure native HTTP in `~/.codex/config.toml`:
   ```toml
   [mcp_servers.giljo]
   url = "http://localhost:7272/mcp"
   bearer_token_env_var = "GILJO_API_KEY"
   ```
3. Remove stdio proxy configuration
```

### 3.2 Add Migration Notice to README

**File**: `README.md`

Add notice in Codex CLI section:

```markdown
## Codex CLI Support

✅ **Native HTTP Support** (Recommended)
- Codex CLI v0.44.0+ connects directly via HTTP
- No proxy needed
- See: [Codex Configuration Guide](docs/INSTALLATION_FLOW_PROCESS.md#codex-cli-native-http-configuration)

⚠️ **Legacy stdio Proxy** (Deprecated)
- Only for Codex CLI v0.43.x and earlier
- Will be removed in v4.0
- See: [Legacy Guide](docs/legacy_stdio_proxy.md)
```

---

## Phase 4: Testing & Validation

### 4.1 Verify Native HTTP Works

**Manual test with Codex CLI** (if available):

1. Configure native HTTP in `~/.codex/config.toml`
2. Run `codex mcp list` - should show "giljo"
3. Test tool invocation - verify connection works
4. Check logs for proper authentication

### 4.2 Verify Legacy Proxy Still Works (Optional)

Only if you want to support legacy users during deprecation period:

```bash
# Install with legacy proxy
pip install giljo-mcp[legacy-codex-proxy]

# Test proxy
GILJO_MCP_SERVER_URL=http://localhost:7272 \
GILJO_API_KEY=your-key \
python -m giljo_mcp.mcp_http_stdin_proxy
```

---

## Phase 5: Future Removal (v4.0)

### Scheduled for Q2 2026

**Complete removal**:
1. Delete `src/giljo_mcp/mcp_http_stdin_proxy.py`
2. Remove `[legacy-codex-proxy]` optional dependency
3. Remove all stdio proxy documentation
4. Update CHANGELOG with removal notice

**Before removal**:
- Announce removal 1 month in advance
- Check if any users still using proxy (analytics/support tickets)
- Ensure Codex CLI v0.44.0+ is widely adopted

---

## Success Criteria

- ✅ Documentation updated with native HTTP configuration
- ✅ Deprecation warnings added to proxy module
- ✅ `mcp` package moved to optional dependency
- ✅ CHANGELOG updated with migration guide
- ✅ README updated with deprecation notice
- ✅ Manual verification that native HTTP works with Codex CLI v0.44.0+
- ✅ Security vulnerability eliminated from core dependencies

---

## Rollback Plan

If issues discovered:

1. **Keep proxy in codebase** - already done, just deprecated
2. **Restore mcp dependency** - easy pip install
3. **Update docs** - revert to stdio proxy as primary method
4. **Investigate issues** - why isn't native HTTP working?

No breaking changes - rollback is trivial.

---

## Risk Assessment

### Low Risk Items

1. **Documentation updates** - No code changes
2. **Deprecation warnings** - Non-breaking, informational only
3. **Optional dependency** - Users can still install if needed
4. **Native HTTP is proven** - Codex v0.46.0 has been stable since Oct 2025

### Mitigation

- Keep proxy code in repo (just deprecated)
- Maintain clear migration path for 6+ months
- Support both methods during transition
- Document troubleshooting for native HTTP issues

---

## Related Documentation

- **Codex MCP Docs**: https://developers.openai.com/codex/mcp
- **HTTP Support PR**: https://github.com/openai/codex/pull/4317
- **Release Notes**: https://github.com/openai/codex/releases/tag/rust-v0.46.0
- **Security Advisory**: pip-audit finding for mcp==1.12.3

---

## Implementation Notes

### For the Executing Agent

1. **Research validation complete** - Codex native HTTP is production-ready
2. **Non-breaking change** - Deprecation only, no removal yet
3. **Security win** - Eliminates vulnerability in core deps
4. **User-friendly** - Clear migration path with examples
5. **Timeline** - 6-month deprecation period before removal

### Execution Order

1. Phase 1: Documentation updates (30 min)
2. Phase 2: Code deprecation warnings (20 min)
3. Phase 3: User communication (CHANGELOG, README) (20 min)
4. Phase 4: Testing validation (30 min)
5. Commit all changes (10 min)

**Total**: ~2 hours

### Git Commit Message Template

```
deprecate(0397): Deprecate stdio proxy for Codex native HTTP

Codex CLI v0.44.0+ (October 2025) now supports native HTTP transport.
The stdio proxy is no longer needed.

Changes:
- Marked mcp_http_stdin_proxy.py as DEPRECATED
- Moved mcp package to optional [legacy-codex-proxy] dependency
- Added native HTTP configuration guide
- Created legacy proxy documentation
- Updated CHANGELOG and README with migration path

Security:
- Removed mcp==1.12.3 from core deps (vulnerability GHSA-9h52-p55h-vw2f)

Migration:
- Users should upgrade to Codex v0.44.0+
- Configure native HTTP in ~/.codex/config.toml
- Proxy will be removed in v4.0 (Q2 2026)

Files:
- src/giljo_mcp/mcp_http_stdin_proxy.py (deprecated)
- requirements.txt (mcp commented out)
- pyproject.toml (mcp moved to optional dependency)
- docs/INSTALLATION_FLOW_PROCESS.md (native HTTP guide)
- docs/legacy_stdio_proxy.md (new legacy guide)
- CHANGELOG.md (deprecation notice)
- README.md (migration notice)
```

---

**Handover 0397**: Deprecate stdio proxy in favor of Codex native HTTP support.
