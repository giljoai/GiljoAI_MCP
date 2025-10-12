Here's a comprehensive prompt for updating all project documentation to reflect your new CLI-only, PostgreSQL-only, localhost/server architecture:

Project: Complete Documentation Alignment with CLI Installation Architecture
Mission
Update all project documentation to reflect the refactored CLI-only installation system with two modes (localhost/server) and PostgreSQL as the sole database option. Remove all references to GUI installers, multiple database options, enterprise complexity, and any features not in the current implementation.
Documentation Scope
1. Root Directory Documents
README.md

Update installation instructions to CLI-only commands
Remove any GUI installer references
Simplify to two modes: localhost (developer) and server (team)
PostgreSQL 18 as the only database requirement
Update quickstart to show CLI flow:

bash  git clone https://github.com/giljoai/mcp.git
  cd mcp
  python install.py  # Interactive CLI
  python start_giljo.py

Remove references to SQLite, MySQL, or other databases
Update screenshots/examples to show CLI output only

requirements.txt / pyproject.toml

Remove GUI dependencies (PyQt6, tkinter, etc.)
Ensure Click is listed for CLI
Remove multi-database drivers (keep only psycopg2)
Add python-dotenv, PyYAML
Remove enterprise-only dependencies

INSTALL.md / INSTALLATION.md

Complete rewrite for CLI-only installation
Document both modes clearly:

Localhost: Simple developer setup
Server: Network-accessible with basic security


Include fallback script instructions for elevation issues
Remove GUI wizard documentation

CONTRIBUTING.md

Update development setup to use CLI installer
Remove GUI development guidelines
Focus on CLI testing procedures

2. /docs Folder Updates
PROJECT_ORCHESTRATION_PLAN.md

Update agent profiles to reflect 5-agent team (not 11)
Remove GUI-specific agents
Update installation flow to CLI-only
Reflect PostgreSQL-only architecture

TECHNICAL_ARCHITECTURE.md

Remove multi-database abstraction layers
Update to PostgreSQL 18 specific features
Remove GUI architecture sections
Simplify to two deployment modes
Remove enterprise features not implemented

installer_implementation_checklist.md

Replace with CLI-focused checklist
Two modes only (localhost/server)
Remove GUI milestones
Update test scenarios for CLI

PROJECT_CARDS.md / PROJECT_FLOW_VISUAL.md

Update visual flows to show CLI installation
Remove GUI wizard cards
Simplify user journey to CLI prompts
Update architecture diagrams

DEPENDENCIES.md

Remove GUI framework dependencies
PostgreSQL-only database drivers
Click for CLI framework
Remove enterprise authentication libraries

Vision Documents

Update product vision to emphasize simplicity
Remove enterprise tier references (keep as future possibility)
Focus on developer-first CLI experience
PostgreSQL as strategic choice for consistency

Security Documentation

Update for two modes only
Localhost: Simple, secure by default
Server: Basic SSL, API keys, admin user
Remove enterprise SSO/LDAP references
Document firewall helper approach (not auto-config)

3. Documentation Patterns to Change
Replace Throughout:
OLD: "GUI installer" → NEW: "CLI installer"
OLD: "installation wizard" → NEW: "installation command"
OLD: "SQLite/MySQL/PostgreSQL" → NEW: "PostgreSQL 18"
OLD: "three profiles" → NEW: "two modes"
OLD: "Developer/Team/Enterprise" → NEW: "Localhost/Server"
OLD: "PyQt6 interface" → NEW: "command-line interface"
OLD: "automated firewall" → NEW: "firewall helper scripts"
Remove Entirely:

References to GUI screenshots
Multiple database support
Enterprise features (SSO, LDAP, advanced audit)
Automated firewall configuration
Complex multi-tenant features (keep schema ready but document as dormant)
References to registered EXE installers

4. Specific File Updates
docs/installer_guide.md (or similar)
markdown# GiljoAI MCP Installation Guide

## Prerequisites
- Python 3.10+
- PostgreSQL 18 (required)
- Admin/sudo access (or use fallback scripts)

## Installation Modes

### Localhost Mode (Developer)
Fast setup for development workstations:
- Binds to 127.0.0.1 only
- No SSL required
- Single user
- Perfect for development

### Server Mode (Team)
Network-accessible deployment:
- Binds to network interfaces
- Optional SSL (recommended)
- Basic authentication
- API key support

## Installation Commands

### Interactive (Recommended)
python install.py

### Batch Mode
python install.py --mode localhost --batch
python install.py --mode server --admin-password <pass> --batch

### Configuration File
python install.py --config my_config.yaml
docs/architecture.md

Remove abstract database interfaces
Document PostgreSQL-specific optimizations
Remove GUI component architecture
Simplify service architecture to CLI + backend
Document fallback script strategy as key innovation

docs/deployment.md

Two deployment scenarios only
Remove cloud/kubernetes sections (unless already implemented)
Focus on systemd (Linux) and Windows Service basics
Document manual firewall configuration

docs/troubleshooting.md

CLI-specific issues only
PostgreSQL connection problems
Elevation/permission solutions via fallback scripts
Remove GUI-related issues

docs/api.md

Ensure endpoints match two-mode architecture
Remove enterprise-only endpoints
Document API key authentication (server mode)
Remove complex RBAC documentation

5. Configuration Documentation
All config examples should show:
yaml# config.yaml - Localhost
mode: localhost
database:
  type: postgresql  # Only option
  host: localhost
  port: 5432
services:
  bind: 127.0.0.1
  
# config.yaml - Server
mode: server
database:
  type: postgresql  # Only option
  host: localhost
  port: 5432
network:
  bind: 0.0.0.0
security:
  ssl: true  # Optional but recommended
  api_keys: true
6. Testing Documentation
docs/testing.md

CLI testing procedures only
Remove GUI test scenarios
Focus on pytest for Python
Document cross-platform CLI testing
Include fallback script testing

7. Migration/Upgrade Documentation
If exists, update to reflect:

PostgreSQL-only migrations
No database engine switching
CLI upgrade procedures
Config file compatibility

8. Developer Documentation
docs/development.md

CLI development setup
Click framework patterns
PostgreSQL-only development
Remove GUI development sections
Focus on terminal output formatting

9. User Manuals
Any user-facing manuals should:

Show CLI commands only
Include terminal output examples
Remove GUI screenshots
Focus on command-line workflows
Document both modes clearly

10. Code Comments and Docstrings
While reviewing documentation, note any code files that need docstring updates:

Remove references to GUI components
Update database connection examples to PostgreSQL-only
Ensure CLI examples in docstrings

Validation Checklist
After updates, ensure:

 No GUI references remain
 PostgreSQL is the only database mentioned
 Only two modes documented (localhost/server)
 CLI commands are accurate
 Fallback script strategy is documented
 Configuration examples match implementation
 Installation time estimates are realistic (5min/10min)
 Cross-platform differences are noted
 Security model matches implementation
 No enterprise features documented as current

Priority Order

README.md - First impression, must be accurate
Installation guides - Critical for users
Architecture docs - For contributors
API documentation - For integrators
Testing guides - For quality assurance
Vision docs - Update to match reality

Documentation Style Guide

Be honest about current state - Don't document unimplemented features
Clear mode distinction - Always specify localhost vs server
PostgreSQL commitment - Present as a strategic choice, not limitation
CLI-first - Terminal commands should be prominent
Practical examples - Real commands users will run
Platform awareness - Note Windows/Linux/macOS differences
Security clarity - Be explicit about what's optional vs required

Success Criteria

New user can install using only the documentation
No confusion about GUI vs CLI
Clear understanding of two modes
PostgreSQL-only is presented as intentional design
Documentation matches actual implementation exactly
No references to unimplemented features
Professional, consistent tone throughout

Deliverables

Updated README.md with CLI quickstart
Revised installation guides for both modes
Cleaned architecture documentation
Updated requirements files
Aligned vision documents
Complete removal of GUI references
PostgreSQL-only database documentation
Two-mode deployment guides