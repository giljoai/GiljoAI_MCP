# Handover 0732b: README Screenshots

**Handover ID:** 0732b
**Priority:** P3 - LOW
**Estimated Effort:** 30 min
**Status:** Deferred (post-launch or pre-launch polish)
**Edition Scope:** CE

---

## 1. Task

Capture 3-4 screenshots of the running application and add them to the README.

### Screenshots Needed

1. **Dashboard overview** -- main view after login (shows project list, agent status)
2. **Agent monitoring / Jobs tab** -- real-time agent status with phase badges
3. **Project launch view** -- orchestrator workflow with agent cards
4. **Settings page** -- shows configurability and admin features

### Where They Go

- Store in `docs/screenshots/`
- Reference from `README.md` with relative paths
- Use PNG format, reasonable resolution (~1200px wide)

### How to Capture

This requires a running instance with sample data. Options:
- Manual: Run the app, navigate, take screenshots
- Automated: Playwright script (overkill for 4 images)
- Browser automation: Claude-in-Chrome MCP tools

---

## 2. Why Deferred

Screenshots need a running instance with realistic sample data (projects, agents, jobs). This is a manual task that doesn't benefit from agent automation. It can be done anytime before or shortly after CE public release without blocking the launch.

---

**Created**: 2026-03-08
**Execute When**: Before or shortly after CE public release
