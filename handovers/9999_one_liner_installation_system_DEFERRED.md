# Handover 0100: One-Liner Installation System

---
**⚠️ CRITICAL UPDATE (2025-11-12): DEFERRED TO HANDOVER 0512**

This handover has been **reorganized** into the 0500 series remediation project:

**New Scope**: Part of Handover 0512 - Documentation and Knowledge Base (Installation Documentation)
**Parent Project**: Projectplan_500.md
**Status**: Deferred until after critical remediation (Handovers 0500-0514 complete)

**Reason**: The refactoring (Handovers 0120-0130) left 23 critical implementation gaps that must be fixed BEFORE proceeding with this enhancement. One-liner installation requires stable, tested system first. See:
- **Investigation Reports**: Products, Projects, Settings, Orchestration breakage
- **Master Plan**: `handovers/Projectplan_500.md`
- **New Handover**: `handovers/0512_documentation_knowledge_base.md`

**Original scope below** (preserved for historical reference):

---

**Date**: 2025-11-02
**Status**: Deferred - See Handover 0512
**Priority**: High (after 0500-0514)
**Complexity**: Medium
**Related**: Handover 0082 (Production-Grade npm Installation)

---

## Overview

Implement a professional one-liner installation system for GiljoAI MCP Server, enabling simple website distribution like Claude Code, Cursor, and other AI developer tools. Users download and install with a single command, while maintaining production-grade reliability from Handover 0082.

**Key Achievement**: Zero-friction installation for end users while preserving interactive setup wizard and production-grade npm installation.

---

## Problem Solved

### Current State

Users must:
1. Manually clone GitHub repository
2. Navigate to directory
3. Run `python install.py`
4. Understand git, Python paths, etc.

**Friction points**:
- Requires git knowledge
- Manual directory navigation
- Multiple steps prone to errors
- Not suitable for website download page

### Target State

Users run ONE command from website:

**macOS / Linux**:
```bash
curl -fsSL https://install.giljoai.com/install.sh | bash
```

**Windows**:
```powershell
irm https://install.giljoai.com/install.ps1 | iex
```

**Result**: Automatic download, dependency checks, and interactive setup wizard.

---

## Solution Architecture

### Distribution Strategy

**Website-First Distribution** (like Claude Code):
- Landing page shows platform-specific one-liners
- Scripts hosted at `https://install.giljoai.com/*`
- GitHub remains available for developers (manual installation)

### Two-Tier Installation System

**Tier 1: End Users (Website) - One-Liner**
```
Website → install.sh/install.ps1 → Downloads repo → Runs install.py → Interactive wizard
```

**Tier 2: Developers (GitHub) - Manual**
```
Git clone → python install.py → Interactive wizard
```

**Both paths converge** at `install.py` (no duplicate logic).

### Install Script Responsibilities

**Pre-Flight Checks**:
1. Verify Python 3.11+ installed
2. Verify PostgreSQL 14+ installed (or provide install link)
3. Verify Node.js 18+ installed (for frontend)
4. Check available disk space (2GB minimum)
5. Verify internet connectivity

**Download & Setup**:
1. Download latest release from GitHub
2. Extract to user-selected directory (default: `~/giljoai-mcp` or `C:\GiljoAI_MCP`)
3. Verify download integrity (file count check)
4. Execute `python install.py` with all existing functionality

**Error Handling**:
- Clear error messages for missing prerequisites
- Links to installation guides for Python/PostgreSQL/Node.js
- Graceful exit with troubleshooting steps
- Log file creation for diagnostics

### Integration with Handover 0082

**Reuse Production-Grade npm Logic**:
- Install scripts do NOT handle npm directly
- `install.py` already contains 0082 npm logic (smart ci→install fallback, retry, verification)
- Scripts only verify Node.js is installed (prerequisite check)
- Actual npm operations delegated to `install.py`

**Why This Works**:
- ✅ Zero duplication of npm logic
- ✅ Scripts remain simple (prereq checks + download + delegate)
- ✅ `install.py` remains single source of truth
- ✅ Both installation paths get same reliability

---

## Implementation Plan

### Phase 1: Create install.sh (macOS/Linux)

**File**: `install.sh` (root directory)

**Script Flow**:
```bash
#!/bin/bash

# 1. Display banner
echo "GiljoAI MCP Server - Installation"

# 2. Prerequisite checks
check_python_version()    # Python 3.11+
check_postgresql()        # PostgreSQL 14+
check_nodejs()            # Node.js 18+
check_disk_space()        # 2GB minimum
check_internet()          # curl test

# 3. User prompts
prompt_install_directory()  # Default: ~/giljoai-mcp

# 4. Download latest release
download_latest_release()  # GitHub latest tag or main branch

# 5. Extract and verify
extract_archive()
verify_installation()      # Check critical files exist

# 6. Execute install.py
cd "$INSTALL_DIR"
python3 install.py

# 7. Success message
echo "Installation complete! Run: cd $INSTALL_DIR && python3 startup.py"
```

**Error Handling**:
- Each prerequisite check provides install link if missing
- Download failures show GitHub manual install instructions
- Extraction errors show troubleshooting steps
- All errors logged to `~/giljoai_install.log`

**Testing Requirements**:
- Test on Ubuntu 22.04 LTS
- Test on macOS 13+ (Intel and Apple Silicon)
- Test with missing prerequisites (Python, PostgreSQL, Node.js)
- Test with insufficient disk space
- Test with network failures
- Test with existing installation (upgrade scenario)

### Phase 2: Create install.ps1 (Windows)

**File**: `install.ps1` (root directory)

**Script Flow**:
```powershell
# 1. Display banner
Write-Host "GiljoAI MCP Server - Installation"

# 2. Prerequisite checks
Check-PythonVersion      # Python 3.11+
Check-PostgreSQL         # PostgreSQL 14+
Check-NodeJS             # Node.js 18+
Check-DiskSpace          # 2GB minimum
Check-Internet           # Test-NetConnection

# 3. User prompts
Get-InstallDirectory     # Default: C:\GiljoAI_MCP

# 4. Download latest release
Download-LatestRelease   # GitHub latest tag or main branch

# 5. Extract and verify
Expand-Archive
Test-Installation        # Check critical files exist

# 6. Execute install.py
Set-Location $InstallDir
python install.py

# 7. Success message
Write-Host "Installation complete! Run: python startup.py"
```

**PowerShell-Specific Considerations**:
- Use `Invoke-WebRequest` (irm alias) for downloads
- Use `Expand-Archive` for extraction
- Handle execution policy (may need `-ExecutionPolicy Bypass`)
- Use `Test-Path` for file verification
- Use `Get-PSDrive` for disk space check

**Testing Requirements**:
- Test on Windows 10 and Windows 11
- Test with missing prerequisites
- Test execution policy restrictions
- Test with existing installation
- Test with network failures

### Phase 3: Update install.py Integration

**Changes to install.py**:

**Add detection for scripted installation**:
```python
def is_scripted_install() -> bool:
    """Detect if running from install.sh/install.ps1"""
    return os.environ.get('GILJO_SCRIPTED_INSTALL') == 'true'

def main():
    if is_scripted_install():
        print("Continuing from automated installation script...")
        # Skip directory prompts (already handled by script)
    else:
        print("Manual installation mode...")
        # Existing behavior
```

**Environment variable passed by scripts**:
```bash
# In install.sh
export GILJO_SCRIPTED_INSTALL=true
python3 install.py
```

```powershell
# In install.ps1
$env:GILJO_SCRIPTED_INSTALL = "true"
python install.py
```

**Why**: Prevents duplicate prompts (scripts already ask for install directory)

### Phase 4: Documentation Updates

**CLAUDE.md**:
```markdown
## Quick Install

**macOS / Linux**:
```bash
curl -fsSL https://install.giljoai.com/install.sh | bash
```

**Windows**:
```powershell
irm https://install.giljoai.com/install.ps1 | iex
```

**Manual Installation** (Developers):
```bash
git clone https://github.com/patrik-giljoai/GiljoAI-MCP
cd GiljoAI-MCP
python install.py
```

## Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Node.js 18+

See [Installation Guide](docs/INSTALLATION_FLOW_PROCESS.md) for details.
```

**docs/INSTALLATION_FLOW_PROCESS.md**:
- Add "Quick Install" section at top
- Add "Manual Install" section (existing content)
- Add "Prerequisites Installation" section with links
- Add "Troubleshooting" section for install script errors

### Phase 5: Website Content Creation

**Create reference file**: `docs/website/installation_page.md`

**Content for website landing page**:
```markdown
# Installation

## Quick Install

**macOS / Linux**:
```bash
curl -fsSL https://install.giljoai.com/install.sh | bash
```

**Windows (PowerShell)**:
```powershell
irm https://install.giljoai.com/install.ps1 | iex
```

## What This Does

✓ Checks prerequisites (Python 3.11+, PostgreSQL 14+, Node.js 18+)
✓ Downloads latest release
✓ Runs interactive setup wizard
✓ Configures database & network
✓ Creates first admin user

Installation takes ~2 minutes.

## Prerequisites

Before installing, ensure you have:
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 14+** - [Download](https://www.postgresql.org/download/)
- **Node.js 18+** - [Download](https://nodejs.org/)

All three are free and cross-platform.

## Manual Installation

Advanced users can clone the repository:

```bash
git clone https://github.com/patrik-giljoai/GiljoAI-MCP
cd GiljoAI-MCP
python install.py
```

## Troubleshooting

Having issues? Check our [Support Documentation](./docs/INSTALLATION_FLOW_PROCESS.md) or [open an issue](https://github.com/patrik-giljoai/GiljoAI-MCP/issues).
```

---

## Script Hosting Strategy

### Option 1: GitHub Pages (Recommended for MVP)

**Setup**:
1. Create `docs/install/` directory in repo
2. Place `install.sh` and `install.ps1` there
3. Enable GitHub Pages (Settings → Pages → Source: main branch, /docs folder)
4. Access at: `https://patrik-giljoai.github.io/GiljoAI-MCP/install/install.sh`

**Pros**:
- ✅ Free hosting
- ✅ Automatic HTTPS
- ✅ Version control integrated
- ✅ Simple setup

**Cons**:
- ❌ Long URL (use URL shortener or custom domain)
- ❌ GitHub dependency

### Option 2: Custom Domain (Future Enhancement)

**Setup**:
1. Register `install.giljoai.com` subdomain
2. Point CNAME to GitHub Pages or static hosting
3. Short, professional URLs

**Pros**:
- ✅ Branded URLs
- ✅ Professional appearance
- ✅ Flexible hosting backend

**Cons**:
- ❌ Domain costs (~$12/year)
- ❌ DNS configuration needed

**Recommendation for v1**: Use GitHub Pages with shortened URL, migrate to custom domain when budget allows.

---

## Testing Strategy

### Automated Testing (Future)

**GitHub Actions workflow** to test install scripts:
```yaml
name: Test Installation Scripts

on: [push, pull_request]

jobs:
  test-install-sh:
    runs-on: ubuntu-latest
    steps:
      - name: Test install.sh
        run: |
          curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash

  test-install-ps1:
    runs-on: windows-latest
    steps:
      - name: Test install.ps1
        run: |
          irm https://raw.githubusercontent.com/.../install.ps1 | iex
```

### Manual Testing Checklist

**macOS/Linux (install.sh)**:
- [ ] Fresh Ubuntu 22.04 VM
- [ ] Fresh macOS 13+ system
- [ ] System with Python 3.11 already installed
- [ ] System WITHOUT PostgreSQL (should fail gracefully)
- [ ] System WITHOUT Node.js (should fail gracefully)
- [ ] System with insufficient disk space
- [ ] Network disconnected scenario
- [ ] Upgrade scenario (existing installation)

**Windows (install.ps1)**:
- [ ] Fresh Windows 10 VM
- [ ] Fresh Windows 11 VM
- [ ] System with Python 3.11 already installed
- [ ] System WITHOUT PostgreSQL (should fail gracefully)
- [ ] System WITHOUT Node.js (should fail gracefully)
- [ ] Execution policy restricted scenario
- [ ] Network disconnected scenario
- [ ] Upgrade scenario (existing installation)

---

## Files to Create/Modify

### New Files

**install.sh** (~200 lines):
- Bash script for macOS/Linux one-liner installation
- Prerequisite checks, download, extraction, delegation to install.py

**install.ps1** (~200 lines):
- PowerShell script for Windows one-liner installation
- Same logic as install.sh, PowerShell syntax

**docs/website/installation_page.md** (~100 lines):
- Website copy for installation landing page
- Reference for marketing site development

### Modified Files

**install.py** (+50 lines):
- Add `is_scripted_install()` detection
- Skip duplicate prompts when called from scripts
- Add environment variable handling

**CLAUDE.md** (+20 lines):
- Quick Install section at top
- One-liner commands for all platforms
- Manual install instructions

**docs/INSTALLATION_FLOW_PROCESS.md** (+150 lines):
- Quick Install section
- Prerequisites installation guides
- Troubleshooting section for script errors
- Script architecture explanation

**README.md** (+15 lines):
- Quick Install section at top (most visible location)
- Link to full installation docs

---

## Success Criteria

**Definition of Done**:
- [ ] `install.sh` works on Ubuntu 22.04 and macOS 13+
- [ ] `install.ps1` works on Windows 10 and Windows 11
- [ ] Both scripts check all prerequisites correctly
- [ ] Both scripts fail gracefully with helpful error messages
- [ ] Both scripts successfully download and extract repo
- [ ] Both scripts delegate to `install.py` correctly
- [ ] `install.py` detects scripted installation mode
- [ ] CLAUDE.md updated with one-liner instructions
- [ ] docs/INSTALLATION_FLOW_PROCESS.md updated
- [ ] README.md updated with quick install
- [ ] Website content created (docs/website/installation_page.md)
- [ ] Manual testing completed on all platforms
- [ ] Scripts hosted on GitHub Pages (or equivalent)
- [ ] Installation takes <2 minutes on fresh system (with prereqs)

---

## Rollback Plan

**If scripts cause issues**:
1. Remove `install.sh` and `install.ps1` from repo
2. Update website to show manual install instructions only
3. Keep existing `install.py` workflow (unaffected)
4. No database changes, no API changes - zero risk

**Fallback**: Manual installation via git clone always available.

---

## Architecture Benefits

### User Experience
- ✅ **Zero friction**: One command to install
- ✅ **Professional**: Industry-standard approach (like Claude Code)
- ✅ **Platform-aware**: Detects OS and provides correct command
- ✅ **Helpful errors**: Clear messages with install links

### Developer Experience
- ✅ **Zero duplication**: Scripts delegate to install.py
- ✅ **Maintainable**: Logic in one place (install.py)
- ✅ **Testable**: Scripts are simple, install.py has tests
- ✅ **Flexible**: GitHub manual install still available

### Business Impact
- ✅ **Website-ready**: Simple installation page like Claude Code
- ✅ **Professional brand**: Polished installation experience
- ✅ **Low friction**: More downloads, less support burden
- ✅ **Zero cost**: Free hosting via GitHub Pages

### Technical Quality
- ✅ **Reuses 0082**: Production-grade npm logic preserved
- ✅ **Cross-platform**: Works on Windows, macOS, Linux
- ✅ **Robust**: Prerequisite checks prevent common failures
- ✅ **Logged**: Diagnostic logs for troubleshooting

---

## Integration with Handover 0082

**Relationship**:
- 0082 implemented production-grade npm installation **inside install.py**
- 0100 adds one-liner download scripts **that call install.py**
- No changes to 0082 npm logic required
- Scripts verify Node.js prerequisite, install.py handles npm

**Architecture**:
```
User runs one-liner
    ↓
install.sh/install.ps1 (new)
    ↓
Checks: Python, PostgreSQL, Node.js, disk space
    ↓
Downloads repo
    ↓
Runs: python install.py
    ↓
install.py (existing, with 0082 npm logic)
    ↓
Frontend npm install (0082: smart ci→install, retry, verify)
    ↓
Interactive setup wizard
    ↓
Done
```

**Benefits**:
- ✅ One-liner gets 0082 reliability automatically
- ✅ Scripts stay simple (no npm logic duplication)
- ✅ Both installation paths converge at install.py

---

## Future Enhancements (Optional)

### Post-v1 Ideas

1. **Auto-update checker** - Check for new releases on startup
2. **Uninstall script** - `uninstall.sh` / `uninstall.ps1`
3. **Docker image** - Alternative installation method
4. **Homebrew formula** - macOS native package manager
5. **Windows installer exe** - PyInstaller bundled (if budget allows for code signing)
6. **Telemetry** - Anonymous installation success rate tracking

### Not Recommended

- ❌ **pip install giljoai-mcp** - Not a Python package, it's a server application
- ❌ **npm install -g @giljoai/mcp** - Not a Node.js CLI tool
- ❌ **Snap/Flatpak** - Overkill for developer-focused tool

---

## Lessons Learned (From 0082)

**Applying 0082 insights to 0100**:

1. **Pre-flight checks are critical** - Verify prerequisites BEFORE download
2. **Clear error messages reduce support** - Show install links for missing tools
3. **Logging saves time** - Create diagnostic logs from the start
4. **Test cross-platform** - Windows behaves differently than Unix
5. **Keep it simple** - Delegate complex logic to install.py

---

## Summary

Handover 0100 implements a professional one-liner installation system that enables simple website distribution like Claude Code, while preserving the interactive setup wizard and production-grade npm reliability from Handover 0082. Users get zero-friction installation with platform-specific one-line commands, while developers maintain a clean architecture with zero logic duplication. The solution is testable, cross-platform, and ready for professional marketing site deployment.

**Impact**: Transforms installation from multi-step manual process into professional one-liner, reducing barrier to entry for new users while maintaining production-grade reliability.
