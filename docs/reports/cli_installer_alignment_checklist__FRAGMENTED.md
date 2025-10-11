# CLI Installer Alignment Checklist
**Date**: 2025-09-30
**Reference**: setup_gui.py (Primary Source of Truth)
**Target**: setup_cli.py

## Priority 0 - Critical Issues (Breaking Functionality)

### ☐ 1. Standardize Mode Naming
**Current State**: CLI uses "local"/"server", GUI uses "localhost"/"server"
**Required Changes**:
```python
# In setup_cli.py, line ~374-376:
# CHANGE FROM:
deployment_mode = os.environ.get('GILJO_DEPLOYMENT_MODE', 'local').lower()
if deployment_mode not in ['local', 'server']:
    deployment_mode = 'local'

# CHANGE TO:
deployment_mode = os.environ.get('GILJO_DEPLOYMENT_MODE', 'localhost').lower()
if deployment_mode not in ['localhost', 'server']:
    deployment_mode = 'localhost'
```

**Files to Update**:
- [ ] setup_cli.py - Update mode values throughout
- [ ] Update mode selection menu text
- [ ] Update all conditionals checking mode
- [ ] Update configuration output

### ☐ 2. Implement CORS Configuration for Server Mode
**Current State**: CLI missing CORS configuration entirely
**Required Changes**:
```python
# Add new method to GiljoCLISetup class:
def configure_cors(self) -> list:
    """Configure CORS allowed origins for server mode"""
    print("\n" + self.ui.color("Configure CORS Settings", "BOLD"))
    print("Enter allowed origins (one per line, empty line to finish)")
    print("Example: http://localhost:3000")

    allowed_origins = []
    while True:
        origin = input("> ").strip()
        if not origin:
            break
        allowed_origins.append(origin)

    return allowed_origins if allowed_origins else ["*"]
```

**Integration Points**:
- [ ] Call after port configuration in server mode
- [ ] Store in config["cors_allowed_origins"]
- [ ] Display in final summary

## Priority 1 - High Impact Issues

### ☐ 3. Add Explicit Network Mode Selection
**Current State**: CLI infers network mode from deployment mode
**Required Changes**:
```python
# Add network mode selection for server deployment
def select_network_mode(self) -> str:
    """Select network binding mode"""
    if self.deployment_mode == "localhost":
        return "localhost"

    print("\n" + self.ui.color("Network Access Mode", "BOLD"))
    print("1) Localhost only (127.0.0.1)")
    print("2) Network accessible (0.0.0.0)")

    while True:
        choice = input("\nSelect network mode (1-2): ").strip()
        if choice == "1":
            return "localhost"
        elif choice == "2":
            return "network"
        print(self.ui.color("Invalid choice", "RED"))
```

**Integration**:
- [ ] Add method to GiljoCLISetup class
- [ ] Call after deployment mode selection
- [ ] Store in config["network_mode"]
- [ ] Use for bind address configuration

### ☐ 4. Implement Configuration Review Step
**Current State**: CLI goes directly to installation
**Required Changes**:
```python
def review_configuration(self) -> bool:
    """Display configuration for review before installation"""
    self.ui.clear_screen()
    print(self.ui.color("Configuration Review", "BOLD"))
    print("=" * 60)

    # Display all configuration
    print(f"Deployment Mode: {self.deployment_mode}")
    print(f"Network Mode: {self.config.get('network_mode', 'localhost')}")
    print(f"PostgreSQL Host: {self.config.get('pg_host', 'localhost')}")
    print(f"PostgreSQL Port: {self.config.get('pg_port', 5432)}")
    print(f"Server Port: {self.server_port}")

    if self.deployment_mode == "server":
        print(f"API Key: {self.config.get('api_key', 'Will be generated')}")
        print(f"CORS Origins: {self.config.get('cors_allowed_origins', ['*'])}")

    print("\n" + "=" * 60)
    print("\nOptions:")
    print("1) Continue with installation")
    print("2) Modify configuration")
    print("3) Cancel installation")

    while True:
        choice = input("\nSelect option (1-3): ").strip()
        if choice == "1":
            return True
        elif choice == "2":
            return False  # Restart configuration
        elif choice == "3":
            print("Installation cancelled.")
            sys.exit(0)
        print(self.ui.color("Invalid choice", "RED"))
```

**Integration**:
- [ ] Add before installation begins
- [ ] Allow user to go back and modify
- [ ] Show all configured values

## Priority 2 - UX Improvements

### ☐ 5. Enhanced Progress Tracking
**Current State**: Basic text output during installation
**Required Changes**:
```python
def install_dependencies_with_progress(self):
    """Install dependencies with package-level progress tracking"""
    packages = self.get_required_packages()
    total = len(packages)

    for i, package in enumerate(packages, 1):
        # Show package being installed
        print(f"\n[{i}/{total}] Installing {package}...")

        # Check if it's a known large package
        if package in LARGE_PACKAGES:
            print(f"  Note: {LARGE_PACKAGES[package]} - this may take a moment")

        # Install package
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(self.ui.color(f"  ✓ {package} installed", "GREEN"))
        else:
            print(self.ui.color(f"  ✗ {package} failed", "RED"))
            print(f"  Error: {result.stderr[:200]}")
```

**Requirements**:
- [ ] Track individual package installation
- [ ] Show current/total counter
- [ ] Indicate large packages
- [ ] Show success/failure per package

### ☐ 6. Improve Error Handling
**Current State**: Basic try/except blocks
**Required Changes**:
```python
def safe_execute(self, func, error_msg="Operation failed", allow_retry=True):
    """Execute function with comprehensive error handling"""
    max_retries = 3 if allow_retry else 1

    for attempt in range(max_retries):
        try:
            return func()
        except KeyboardInterrupt:
            print("\n" + self.ui.color("Installation interrupted by user", "YELLOW"))
            if self.confirm("Do you want to continue?"):
                continue
            sys.exit(1)
        except Exception as e:
            print(self.ui.color(f"{error_msg}: {str(e)}", "RED"))

            if attempt < max_retries - 1 and allow_retry:
                if self.confirm(f"Retry? (Attempt {attempt + 2}/{max_retries})"):
                    continue

            # Log error details
            self.log_error(e)

            if self.confirm("Continue with installation anyway?"):
                return None
            sys.exit(1)
```

**Apply to**:
- [ ] PostgreSQL connection
- [ ] Database creation
- [ ] Port checking
- [ ] Dependency installation
- [ ] File operations

### ☐ 7. Add Installation Logging
**Current State**: No persistent logs created
**Required Changes**:
```python
class CLIInstallationLogger:
    def __init__(self):
        self.log_dir = Path("install_logs")
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"cli_install_{timestamp}.log"

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.log_file, "a") as f:
            f.write(log_entry)

        # Also print to console with appropriate color
        if level == "ERROR":
            print(self.ui.color(message, "RED"))
        elif level == "WARNING":
            print(self.ui.color(message, "YELLOW"))
        else:
            print(message)
```

**Integration**:
- [ ] Initialize logger at setup start
- [ ] Log all major operations
- [ ] Log errors with stack traces
- [ ] Show log location at end

## Priority 3 - Nice to Have

### ☐ 8. Windows Administrator Check
**Current State**: No admin check on Windows
**Required Changes**:
```python
def check_admin_windows(self):
    """Check for administrator privileges on Windows"""
    if sys.platform != "win32":
        return True

    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

        if not is_admin:
            print(self.ui.color("Warning: Not running as administrator", "YELLOW"))
            print("Some operations may fail without admin privileges.")
            if not self.confirm("Continue anyway?"):
                # Attempt to restart with elevation
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
                sys.exit(0)
        return is_admin
    except:
        return False
```

**Integration**:
- [ ] Check at startup on Windows
- [ ] Warn user if not admin
- [ ] Offer to restart with elevation

### ☐ 9. Navigation Improvements
**Current State**: Linear flow only, can't go back
**Required Changes**:
- [ ] Track configuration state
- [ ] Allow "back" option at each step
- [ ] Preserve entered values when going back
- [ ] Clear navigation indicators

## Testing Checklist

### Functional Tests
- [ ] Localhost mode installation
- [ ] Server mode installation
- [ ] PostgreSQL not installed scenario
- [ ] PostgreSQL already installed scenario
- [ ] Port conflict handling
- [ ] API key generation
- [ ] CORS configuration
- [ ] Network binding (localhost vs 0.0.0.0)

### Error Scenarios
- [ ] Database connection failure
- [ ] Port already in use
- [ ] Insufficient permissions
- [ ] Network unreachable
- [ ] Disk space issues
- [ ] Interrupted installation

### Platform Tests
- [ ] Windows 10/11
- [ ] Ubuntu 20.04/22.04
- [ ] macOS 12+
- [ ] SSH session (no GUI)
- [ ] Docker container

### Non-Interactive Mode
- [ ] Environment variable configuration
- [ ] Silent installation
- [ ] Error handling in non-interactive

## Implementation Order

1. **Phase 1 - Critical** (Fix Breaking Issues)
   - Standardize mode naming
   - Add CORS configuration
   - Add network mode selection

2. **Phase 2 - Essential** (Core Features)
   - Add review step
   - Improve error handling
   - Add logging

3. **Phase 3 - Enhancement** (UX Polish)
   - Enhanced progress tracking
   - Windows admin check
   - Navigation improvements

## Validation Criteria

Each implemented feature should:
1. Match GUI behavior exactly (where applicable)
2. Maintain CLI-appropriate UX
3. Work in non-interactive mode
4. Be properly logged
5. Have appropriate error handling
6. Be tested on all platforms

## Notes

- Keep ASCII art and terminal-friendly UI
- Maintain non-interactive mode support
- Preserve lightweight nature of CLI
- Don't add unnecessary dependencies
- Keep messages concise and clear
- Use consistent terminology with GUI

---

*Use this checklist to track implementation progress. Check off items as completed.*