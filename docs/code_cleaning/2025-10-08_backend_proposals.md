# Code Cleanliness Audit – 2025-10-08

## Scope & Method
- Focused on backend modules under `src/giljo_mcp/` plus supporting services that ship with the MCP server.
- Used structural review + ripgrep scans to trace imports, grep for references, and spot unreferenced or placeholder implementations.
- Cross-checked findings against API usage, tests, and documentation to distinguish active code from dormant fragments.

## High-Risk Zombies & Dead Ends
- `src/giljo_mcp/tools/tool_accessor_enhanced.py:1` – Never imported by API, tools, or tests; duplicates the active `ToolAccessor` while adding retries/perf logging. Keeping both invites drift and hides unused branches.
  - **Next checks**: Confirm no runtime dynamic import; run `rg "EnhancedToolAccessor"` (already zero hits outside file) and consider archiving module after verifying tests `tests/test_tool_accessor*.py` still pass.
- `src/giljo_mcp/tools/claude_code_integration.py:1-200` – Not referenced anywhere in runtime. Still imports `get_db_session` and `get_current_tenant_key`, APIs that no longer exist, so the module would fail at import. Represents a stale Claude-Code bridge.
  - **Next checks**: Build a minimal repro by adding `sys.path.append('src')` and `import giljo_mcp.tools.claude_code_integration`; expect ImportError today. Decide whether to revive (update to async `DatabaseManager`) or remove along with outdated docs (`docs/INTEGRATE_CLAUDE_CODE.md`).

## Orphaned Serena Services
- `src/giljo_mcp/services/serena_detector.py:1-166` & `src/giljo_mcp/services/claude_config_manager.py:1-280` – Only touched by legacy/archived tests; production code never instantiates them. Meanwhile `config_manager.check_serena_mcp_available()` relies on `importlib` instead, so these subprocess-heavy helpers are effectively dead weight.
  - **Next checks**: Validate via `rg "SerenaDetector" -g"*.py"` (no matches outside tests). Decide whether to relocate to an opt-in adapter or remove tests that keep them alive artificially.
- `src/giljo_mcp/discovery.py:592-664` (`SerenaHooks`) – Still injected into `DiscoveryManager`, but every method returns placeholder messages (“Use mcp__serena-mcp__…”) with no integration path. Templates and onboarding copy insist Serena is first-class, yet runtime yields empty data.
  - **Next checks**: Trace call-sites (`DiscoveryManager._load_code`) to confirm placeholders surface to agents. If Serena cannot be shipped, gate these branches behind feature flags and adjust templates to avoid promising functionality.

## Additional Observations
- Auth continues to route through `src/giljo_mcp/auth_legacy.py`; while in use, naming signals debt. Factor into future cleanup planning.
- Extensive Serena-specific instructions remain embedded in orchestrator templates (`src/giljo_mcp/template_manager.py:150+`) despite missing backend support, risking misleading runtime behavior.

## Recommended Follow-Up Tests
1. Execute backend smoke suite: `pytest tests/test_tool_accessor.py tests/test_message_queue.py` to confirm no regressions while auditing unused modules.
2. If retiring Serena services, rerun `pytest tests/integration/test_serena_*` (many sit under docs/archive) to ensure expectations are updated or archived fully.
3. After any Claude integration decision, run `pytest -k 'claude'` to confirm no stray references remain.
