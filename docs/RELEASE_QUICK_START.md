# Release Quick Start Guide

**Quick reference for creating production releases**

## Before Creating Release

### 1. Review Critical Checklist
```bash
# Open and review:
docs/CRITICAL_RELEASE-NOTES.MD
```

### 2. Run Local Tests
```bash
# Security scan (must pass)
bandit -r src/ api/ installer/ -x tests

# Python tests
pytest tests/

# Frontend audit
cd frontend && npm audit --production
```

### 3. Build Frontend Locally (Test)
```bash
cd frontend
npm run build
# Check that dist/ was created successfully
ls -la dist/
cd ..
```

## Create Release via GitHub

### 1. Go to GitHub Actions
```
https://github.com/YOUR_USERNAME/GiljoAI_MCP/actions/workflows/create-release.yml
```

### 2. Click "Run workflow"
- Enter version (e.g., `1.0.0`)
- Check "pre-release" if beta
- Click "Run workflow"

### 3. Workflow Automatically:
- ✅ Checks CRITICAL_RELEASE-NOTES.MD exists
- ✅ Builds frontend production bundle
- ✅ Runs security scans
- ✅ Runs tests
- ✅ Creates git tag
- ✅ Generates release archives
- ✅ Creates GitHub release

## What Gets Included

The workflow uses `git archive` which respects `.gitattributes`.

**Included:**
- `src/` - Core application
- `api/` - Backend API
- `frontend/dist/` - Built frontend (production)
- `installer/` - Installation system
- `docs/` - User documentation
- `requirements.txt`, `package.json`, etc.

**Auto-Excluded (via .gitattributes):**
- `frontend/node_modules/`
- `frontend/src/` (only built dist/)
- `__pycache__/`, `*.pyc`
- `.git/`, `.github/`
- Development logs and sessions
- Test files

## After Release

### 1. Verify Release
- Check GitHub releases page
- Download and test archive
- Verify frontend is pre-built

### 2. Test Installation
```bash
# On clean system:
wget https://github.com/YOUR_USERNAME/GiljoAI_MCP/releases/download/vX.Y.Z/GiljoAI_MCP-vX.Y.Z.tar.gz
tar -xzf GiljoAI_MCP-vX.Y.Z.tar.gz
cd GiljoAI_MCP-vX.Y.Z
python bootstrap.py
```

## Troubleshooting

### Workflow Fails on Security Scan
- Fix security issues locally first
- Commit fixes
- Re-run workflow

### Frontend Build Fails
- Check for Vue syntax errors
- Test `npm run build` locally
- Fix and commit

### Tests Fail
- Run `pytest tests/` locally
- Fix failing tests
- Commit and re-run

## Configuration Notes

### Vite fs.strict Setting
- ✅ Safe in releases (only affects dev server)
- Production uses built files from `dist/`
- No action needed - automatic

### Database Password
- ⚠️ Change from default `4010` for production
- Use environment variables in releases
- Document in installation guide

## Quick Commands

```bash
# Check what would be released
git archive --format=tar.gz HEAD | tar -tzf - | head -20

# Test frontend build
cd frontend && npm ci && npm run build && cd ..

# Run all local checks
bandit -r src/ api/ installer/ -x tests && \
pytest tests/ && \
cd frontend && npm audit --production && cd ..
```

---

**See Also:**
- [CRITICAL_RELEASE-NOTES.MD](./CRITICAL_RELEASE-NOTES.MD) - Full checklist
- [GitHub Workflow](.github/workflows/create-release.yml) - Automation details
