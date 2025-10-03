# CRITICAL RELEASE NOTES

**⚠️ IMPORTANT: Review this document before creating ANY release version**

This document tracks critical items that MUST be addressed when preparing release packages for distribution.

---

## Pre-Release Checklist

### 🔴 CRITICAL - Must Be Done

- [ ] **Remove Development-Only Configuration**
  - [ ] Vite `fs.strict: false` is dev-only (auto-handled by build process)
  - [ ] Ensure production build uses `npm run build` (creates `dist/`)
  - [ ] Verify no symlink dependencies in release package

- [ ] **Build Production Frontend**
  ```bash
  cd frontend/
  npm run build
  # Outputs to frontend/dist/
  ```

- [ ] **Database Configuration**
  - [ ] PostgreSQL password changed from default `4010`
  - [ ] Database credentials use environment variables
  - [ ] No hardcoded development credentials

- [ ] **Port Configuration**
  - [ ] Verify standard ports: 7272 (API), 7273 (fallback), 7274 (frontend)
  - [ ] Ensure port conflicts documented
  - [ ] Test port auto-detection works

- [ ] **Security Scan**
  - [ ] Run `bandit` security scan (must pass)
  - [ ] Check for exposed secrets/API keys
  - [ ] Verify no development tokens in code

- [ ] **Dependencies**
  - [ ] Run `npm audit` for frontend
  - [ ] Run `pip-audit` for backend
  - [ ] Update vulnerable packages

### 🟡 IMPORTANT - Should Be Done

- [ ] **Documentation**
  - [ ] README.md updated with current version
  - [ ] Installation instructions tested
  - [ ] API documentation current
  - [ ] Frontend user guide updated

- [ ] **Testing**
  - [ ] Unit tests passing
  - [ ] Integration tests passing
  - [ ] Manual installation test on clean system
  - [ ] Test on Windows/Linux/macOS (if applicable)

- [ ] **Version Numbers**
  - [ ] Update version in `package.json`
  - [ ] Update version in `pyproject.toml` or `setup.py`
  - [ ] Update version in installer
  - [ ] Create git tag with version number

- [ ] **Logging**
  - [ ] Set production log level (INFO or WARNING)
  - [ ] Remove verbose debug logging
  - [ ] Ensure no sensitive data in logs

### 🟢 RECOMMENDED - Nice to Have

- [ ] **Performance**
  - [ ] Frontend bundle size optimized
  - [ ] Database queries optimized
  - [ ] Large dependencies reviewed

- [ ] **User Experience**
  - [ ] Error messages user-friendly
  - [ ] Installation wizard tested
  - [ ] Browser compatibility verified

---

## Known Development Settings

### Vite Configuration (`frontend/vite.config.js`)
```javascript
// Current setting (for symlinked development):
server: {
  fs: {
    strict: false,  // ⚠️ DEVELOPMENT ONLY
    allow: ['..']   // ⚠️ DEVELOPMENT ONLY
  }
}
```

**Status:** ✅ Safe for release
- These settings only affect `npm run dev` (development server)
- Production builds use `npm run build` which ignores these settings
- Release packages serve pre-built static files from `dist/`

**No action needed** - Build process handles this automatically.

---

## Release Build Process

### Automated Release Steps (GitHub Actions)

The release workflow should:

1. **Clean Build**
   ```bash
   # Remove development artifacts
   rm -rf frontend/node_modules/.vite
   rm -rf frontend/dist
   rm -rf __pycache__
   find . -name "*.pyc" -delete
   ```

2. **Build Frontend**
   ```bash
   cd frontend
   npm ci  # Clean install
   npm run build
   cd ..
   ```

3. **Prepare Python Package**
   ```bash
   # Install only production dependencies
   pip install -r requirements.txt --no-dev

   # Run tests
   pytest tests/
   ```

4. **Create Release Archive**
   ```bash
   # Include:
   # - src/
   # - api/
   # - frontend/dist/  (NOT frontend/src)
   # - installer/
   # - requirements.txt
   # - config.yaml.example
   # - README.md
   # - LICENSE

   # Exclude:
   # - frontend/node_modules/
   # - frontend/src/
   # - venv/
   # - .git/
   # - __pycache__/
   # - *.pyc
   # - logs/
   # - .env
   ```

5. **Security Scan**
   ```bash
   # Must pass before release
   bandit -r src/ api/ installer/ -x tests
   npm audit --production
   ```

6. **Version Tag**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

---

## Environment-Specific Settings

### Development Environment
```yaml
# config.yaml (development)
mode: local
database:
  password: "4010"  # ⚠️ Development only
logging:
  level: DEBUG      # ⚠️ Development only
```

### Production Environment
```yaml
# config.yaml (production)
mode: server
database:
  password: ${DB_PASSWORD}  # From environment
logging:
  level: INFO               # Production level
```

---

## Testing Release Package

### Manual Test on Clean System

1. **Extract release archive**
2. **Run installer**
   ```bash
   python install.py
   ```

3. **Verify services start**
   ```bash
   python start_giljo.py
   ```

4. **Check frontend loads**
   - Open browser to `http://localhost:7274`
   - Verify no module resolution errors
   - Test key features

5. **Check backend API**
   - Open `http://localhost:7272/docs`
   - Test API endpoints
   - Verify database connection

---

## Rollback Plan

If issues are found after release:

1. **Tag as broken**
   ```bash
   git tag -a v1.0.0-broken -m "Known issues"
   ```

2. **Create hotfix branch**
   ```bash
   git checkout -b hotfix/v1.0.1 v1.0.0
   ```

3. **Fix and re-release**
   ```bash
   # Make fixes
   git tag -a v1.0.1 -m "Hotfix release"
   ```

---

## Contact for Questions

If uncertain about any release step:
- Review `/docs/devlog/` for recent changes
- Check `/docs/session/` for context
- Test on clean VM before releasing

---

**Last Updated:** 2025-01-03
**Next Review:** Before each major release
