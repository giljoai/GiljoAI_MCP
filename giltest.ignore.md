# giltest.ignore.md - Release Simulation Exclusions

This file documents which files and directories should be **excluded** when `giltest.py` copies files to simulate a clean GitHub release download.

## Purpose

`giltest.py` simulates what a user receives when downloading a GitHub release archive. This means:
- **Development files**: EXCLUDED (tests, logs, sessions, dev docs)
- **Production files**: INCLUDED (source code, user docs, configs)
- **Generated files**: EXCLUDED (build artifacts, caches, coverage)

## Reference Implementation

The exclusion patterns are implemented in `giltest.py` in the `EXCLUDE_DIRS`, `EXCLUDE_FILES`, and `EXCLUDE_PATTERNS` variables.

---

## Directory Exclusions

### Version Control
```
.git/
.github/
```

### Development Environments
```
venv/
.venv/
env/
ENV/
```

### Python Caches & Build Artifacts
```
__pycache__/
.eggs/
*.egg-info/
build/
dist/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
coverage/
```

### Node/Frontend Build
```
node_modules/
frontend/dist/
frontend/.nuxt/
frontend/.output/
```

### IDE & Editors
```
.vscode/
.idea/
.claude/
```

### Development Tools
```
.serena/          # Serena MCP cache
```

### Testing
```
tests/
test/
Tests/
Test/
benchmark*/
performance*/
```

### Development Documentation
```
devlog/
sessions/
session/
docs/Sessions/
docs/devlog/
docs/adr/
docs/backup_pre_subagent/
docs/design/
docs/component_specs/
```

### Temporary & Runtime
```
scratch/
drafts/
tmp/
temp/
logs/
install_logs/
test_logs/
uploads/
```

### Archives & Backups (in root)
```
archive/
backups/
```

---

## File Exclusions

### Development Markdown Files (Root)
```
NEXT_AGENT_*.md
PHASE*.md
*_REPORT.md
*_SUMMARY.md
*_summary.md
*context recovery.md
POSTGRESQL_MIGRATION.md
MIGRATION_NOTES.md
TECHDEBT.md
GILTEST_README.md
VALIDATION_SUMMARY.md
WEBSOCKET_TEST_COVERAGE_REPORT.md
```

### Development Documentation (docs/)
```
docs/AGENT_INSTRUCTIONS.md
docs/audit_report*.md
docs/linting_*.md
docs/PROJECT_*.md
docs/*_INTERNAL.md
docs/*_internal.md
```

### Development Scripts
```
*test*.py       # Unless it's setup or essential
*debug*.py
*mock*.py
analyze_*.py
validate_*.py
cleanup_*.py
```

### Development Config Files
```
.gitattributes
.dockerignore
.coveragerc
.pre-commit-config.yaml
ruff.toml
.ruff.toml
mypy.ini
pytest.ini
```

### Lock Files (optional, include uv.lock for reproducibility)
```
# Keep: uv.lock (for reproducible installs)
# Exclude: frontend/package-lock.json (npm install generates)
```

### Logs & Databases
```
*.log
*.sqlite
*.db
*.db-shm
*.db-wal
```

### Generated Reports
```
*.json       # Most are test/coverage reports
coverage.xml
dependency_report.json
test_results.json
*_test_results.json
```

### Environment & Secrets
```
.env
.env.*
api_keys.json
config.yaml
install_config.yaml
.mcp.json
```

---

## File Inclusions (What SHOULD be in Release)

### Root Documentation
```
README.md
INSTALLATION.md
INSTALL.md
CLAUDE.md
CONTRIBUTING.md
SECURITY.md
LICENSE
PROJECT_CONNECTION.md
QUICK_START.md
SERVER_MODE_QUICKSTART.md
```

### User-Facing Documentation (docs/)
```
docs/ARCHITECTURE_V2.md
docs/TECHNICAL_ARCHITECTURE.md
docs/AI_TOOL_INTEGRATION.md
docs/color_themes.md
docs/installer_user_guide.md
docs/installer_troubleshooting.md
docs/API_REFERENCE.md
```

### Source Code
```
src/**/*.py
api/**/*.py
installer/**/*.py
migrations/**/*.py
```

### Frontend
```
frontend/src/**/*
frontend/public/**/*
frontend/*.config.js
frontend/package.json
frontend/index.html
```

### Configuration Templates
```
.env.example
config.yaml.example
docker-compose.yml
docker-compose.dev.yml
docker-compose.prod.yml
```

### Installation Scripts
```
install.py
install.bat
setup_*.py (production installers only)
bootstrap.py
quickstart.sh
```

### Essential Dependencies
```
requirements.txt
pyproject.toml
uv.lock
frontend/package.json
```

---

## Pattern Matching Notes

For `giltest.py` implementation:

1. **Exact matches**: Use string equality (`dirname == "tests"`)
2. **Wildcards**: Use `fnmatch` or `glob` (`*.log`, `*test*.py`)
3. **Partial matches**: Use `in` or `startswith` (`"test" in dirname.lower()`)

Example usage in `giltest.py`:
```python
EXCLUDE_DIRS = [
    ".git", ".github", "venv", "__pycache__",
    "tests", "devlog", "sessions", # ... etc
]

EXCLUDE_PATTERNS = [
    "*.log", "*.pyc", "*.sqlite",
    "*test*.py", "PHASE*.md", # ... etc
]
```

---

## Maintenance

When adding new development files/directories to the project:
1. Add to `.gitignore` if they're generated/temporary
2. Add to this file if they're dev-only but committed
3. Update `giltest.py` exclusion lists accordingly

Last updated: 2025-10-02
