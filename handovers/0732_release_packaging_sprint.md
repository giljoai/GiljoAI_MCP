# Handover 0732: Open Source Release Packaging Sprint

**Handover ID:** 0732
**Priority:** P2 - MEDIUM
**Estimated Effort:** 3-5 hours
**Status:** DEFERRED (execute after remaining features complete)
**Branch:** Create `release/0732-packaging` from master
**Dependencies:** 0731 (typed service returns - must be merged first)

---

## 1. Mission & Context

### What We're Doing
Package the codebase for open source release. The code quality is solid (architecture score ~8.5/10 after 0731). This handover addresses the community/release score (~6/10) by adding the artifacts that experienced developers expect in the first 60 seconds of evaluating a repository.

### Why This Matters
First impressions drive adoption. A developer evaluating GiljoAI MCP will check:
1. Can I see what it does? (screenshots)
2. Can I run it? (Docker)
3. Can I contribute? (templates)
4. Do the tests pass? (fix failures)
5. What changed recently? (changelog)

Code quality won't matter if they bounce before reading any code.

### What Already Exists
- README.md (good - badges, quick start, architecture overview)
- LICENSE (MIT)
- CONTRIBUTING.md (added in 0745 series)
- CODE_OF_CONDUCT.md (added in 0745 series)
- SECURITY.md (added in 0745 series)
- CI pipeline (.github/workflows/ci.yml - 5 jobs)

---

## 2. Tasks

### Task 1: GitHub Issue & PR Templates (20 min)

Create `.github/ISSUE_TEMPLATE/bug_report.md`:
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python version, PostgreSQL version)
- Logs/screenshots

Create `.github/ISSUE_TEMPLATE/feature_request.md`:
- Problem description
- Proposed solution
- Alternatives considered

Create `.github/PULL_REQUEST_TEMPLATE.md`:
- Summary of changes
- Type (bug fix / feature / refactor / docs)
- Testing checklist
- Screenshots (if UI changes)

### Task 2: README Screenshots (30 min)

Capture and add 3-4 screenshots to README:
- Dashboard overview (main view after login)
- Agent monitoring / Jobs tab (shows real-time agent status)
- Project launch view (orchestrator workflow)
- Settings page (shows configurability)

Store in `docs/screenshots/` and reference from README with relative paths.

Note: This requires a running instance. Take screenshots manually or use Playwright.

### Task 3: CHANGELOG.md (15 min)

Generate from conventional commits using git log:
```bash
git log --pretty=format:"- %s" --no-merges v0.1.0..HEAD
```

Or install git-cliff for auto-generation. Structure as:
- v3.3.x (Current) - Typed service returns, code cleanup, audit
- v3.2.x - Orchestrator workflow, GUI redesign
- v3.1.x - Backend refactoring, remediation
- v3.0.x - Context management v2, 360 memory

Keep it high-level. Link to handover docs for details.

### Task 4: Fix Pre-Existing Test Failures (1-2 hours)

12 pre-existing test failures identified in 0731b chain log:
- consolidation_service tests
- orchestration_consolidation tests
- project_service_exceptions tests
- vision_summarizer_multi_level tests

Also: Install `pytest-timeout` to fix the test suite hanging issue.

```bash
pip install pytest-timeout
# Add to pyproject.toml [project.optional-dependencies] or requirements-dev.txt
```

Run `pytest tests/ --timeout=30 -v` and fix all failures.

### Task 5: Dockerfile + docker-compose.yml (2-3 hours)

Create `Dockerfile`:
- Multi-stage build (builder + runtime)
- Python 3.11+ base image
- Copy requirements, install deps
- Copy source code
- Expose API port (from config.yaml, default 7171)
- CMD: `python startup.py`

Create `docker-compose.yml`:
- PostgreSQL 18 service (with health check)
- GiljoAI MCP service (depends on postgres)
- Frontend build (or serve from backend)
- Volume mounts for data persistence
- Environment variables for config

Create `docker-compose.dev.yml` (optional):
- Hot reload for development
- Exposed PostgreSQL port for debugging

Update README with Docker quick start:
```bash
docker compose up -d
# Visit http://localhost:7171
```

---

## 3. Success Criteria

- [ ] GitHub issue templates work (test by creating issue on GitHub)
- [ ] PR template appears when opening new PR
- [ ] README has 3-4 screenshots showing key workflows
- [ ] CHANGELOG.md covers major versions
- [ ] All tests pass with `pytest --timeout=30`
- [ ] `docker compose up` launches working instance from clean clone
- [ ] Community score >= 8/10

---

## 4. Subagent Recommendations

| Task | Agent | Can Parallel? |
|------|-------|---------------|
| GitHub templates | documentation-manager | Yes |
| CHANGELOG | documentation-manager | Yes |
| Test fixes | tdd-implementor | Yes |
| Dockerfile | installation-flow-agent | After templates |
| Screenshots | Manual (requires running instance) | After Docker |

Tasks 1-3 can run in parallel. Task 4 is independent. Task 5 depends on nothing but is the most complex.

---

## 5. Estimated Impact

| Metric | Before | After |
|--------|--------|-------|
| Community/release score | ~6/10 | ~8-9/10 |
| Time to first run (new dev) | 15-30 min (manual install) | 2 min (docker compose up) |
| Issue submission quality | Unstructured | Templated |
| PR quality | No checklist | Structured checklist |

---

**Created**: 2026-02-11
**Execute When**: After remaining features are implemented, before public release
**Depends On**: 0731 merged to master
