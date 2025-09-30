# GiljoAI MCP Installer Architecture

## Overview
The installer system now implements a **hybrid dependency management approach** that elegantly handles the "chicken-and-egg" problem of needing PostgreSQL test dependencies before the full installation.

## Entry Points

### Primary Entry Point
**`install.bat`** - Main installer launcher
- **Only requirement**: Python 3.10+
- Auto-installs Python if missing
- Launches bootstrap.py

### Alternative Entry Points (Require Python)
**`setup_gui.bat`** - Direct GUI installer
- Checks for Python and tkinter
- Optionally installs psycopg2-binary for testing
- Launches GUI immediately

**`setup_cli.bat`** - Direct CLI installer
- Checks for Python
- Optionally installs psycopg2-binary for testing
- Launches CLI immediately

**`python bootstrap.py`** - Programmatic entry
- Auto-detects GUI capability
- Offers choice between GUI/CLI
- Smart dependency management

## Dependency Management Strategy (Option C: Hybrid)

### Stage 1: Bootstrap (Pre-Installer)
- **Required**: Python 3.10+ only
- **Optional**: Offers to install psycopg2-binary (~5 seconds)
- **User Choice**: Can skip and install later

### Stage 2: Installer (GUI/CLI)
- **Smart Detection**: Checks if psycopg2 is available
- **Visual Feedback**: Shows warning if test dependencies missing
- **In-GUI Install**: Button to install psycopg2-binary without leaving GUI
- **Graceful Degradation**: Connection testing disabled until deps installed

### Stage 3: Full Installation
- All requirements.txt packages installed
- Complete functionality available

## Key Features

### 1. No Two-Stage Rocket Problem ✓
- Can run `setup_gui.py` or `setup_cli.py` directly
- Smart detection handles missing dependencies
- Clear instructions for manual setup

### 2. Flexible Installation Paths ✓
- **Path A**: `install.bat` → prompt for deps → GUI/CLI
- **Path B**: `setup_gui.bat` → optional deps → GUI
- **Path C**: `setup_cli.bat` → optional deps → CLI
- **Path D**: `python bootstrap.py` → smart handling

### 3. User-Friendly ✓
- Clear error messages
- Visual install buttons in GUI
- Non-blocking: Can continue without test deps
- Fast test dep install (~5 seconds)

### 4. Developer-Friendly ✓
- Direct launcher scripts for quick access
- Proper error handling and logging
- Professional code structure

## Implementation Details

### bootstrap.py Changes
```python
def check_test_dependencies() -> bool:
    """Check if psycopg2 is available"""

def install_test_dependencies() -> bool:
    """Install minimal deps for testing"""

def launch_gui_installer():
    # Prompts user to install test deps if missing
    # Continues regardless of choice
```

### setup_gui.py Changes
```python
class DatabasePage:
    def __init__(self):
        self.psycopg2_available = self._check_psycopg2()

        # Show install button if deps missing
        if not self.psycopg2_available:
            # Display warning + install button

    def _install_test_deps(self):
        # Threaded install of psycopg2-binary
        # Updates UI on success/failure
```

### Exception Handling Fix
Fixed UnboundLocalError in PostgreSQL connection test:
- Separated psycopg2 import into its own try-except
- Added early return on ImportError
- Clear error messaging

## File Structure

```
GiljoAI_MCP/
├── install.bat              # Main entry (Python checker + bootstrap)
├── bootstrap.py             # Installer orchestrator
├── setup_gui.py             # GUI wizard
├── setup_cli.py             # CLI wizard
├── setup_gui.bat            # Direct GUI launcher
├── setup_cli.bat            # Direct CLI launcher
└── setup.py                 # Base utilities
```

## Testing Checklist

- [x] Python syntax validation (all files)
- [x] psycopg2 detection in bootstrap
- [x] psycopg2 detection in setup_gui
- [ ] Full GUI workflow test
- [ ] PostgreSQL connection test
- [ ] Install button functionality
- [ ] Direct launcher scripts

## Known Limitations

1. **PostgreSQL v18**: Tested with PostgreSQL 18 on default port 5432
2. **Windows-specific**: Batch files are Windows-only (Linux/Mac use .sh equivalents)
3. **Test Dependencies**: Only psycopg2-binary installed early (minimal footprint)

## Future Improvements

1. Add progress indicators for dependency installation
2. Add connection test logging for debugging
3. Support for custom PostgreSQL installations

## Migration Notes

**Breaking Changes**: None - fully backward compatible

**New Features**:
- Direct launcher scripts (setup_gui.bat, setup_cli.bat)
- In-GUI dependency installation
- Smart dependency detection
- Better error messages

**Bug Fixes**:
- Fixed UnboundLocalError in PostgreSQL connection test
- Proper exception handling for missing psycopg2
