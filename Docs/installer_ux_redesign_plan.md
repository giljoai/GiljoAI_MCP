# GiljoAI MCP Installer UX Redesign Project Plan

## Executive Summary
Transform the current configuration-only installer into a comprehensive, user-friendly installation experience that actually installs and configures all necessary dependencies based on user choices.

## Core Principles
1. **Guided Experience**: Every choice should be explained with clear use cases
2. **Complete Installation**: Actually install dependencies, don't just check for them
3. **Progressive Disclosure**: Show advanced options only when relevant
4. **Fail-Safe Design**: Always provide fallback options and recovery paths
5. **Platform Awareness**: Adapt to Windows/Mac/Linux capabilities automatically

## Installation Profiles

### 1. Local Development
- **Description**: "Single machine setup for development and testing"
- **Installs**:
  - SQLite (built-in with Python)
  - Redis (local instance)
  - Local-only configuration
- **Use Case**: Individual developers, personal projects, prototyping
- **Full Features**: Unlimited agents, complete orchestration, all MCP tools

### 2. Network Shared
- **Description**: "Multi-user setup accessible across network"
- **Installs**:
  - PostgreSQL (for concurrent access)
  - Redis (network accessible)
  - Network security configuration
  - API authentication setup
- **Use Case**: Team collaboration, office LAN deployment, shared resources
- **Full Features**: Same as Local, plus multi-user support

### 3. High Performance
- **Description**: "Optimized for heavy workloads and scale"
- **Installs**:
  - PostgreSQL (with connection pooling)
  - Redis (with persistence & clustering)
  - Performance monitoring
  - SSL/TLS security
- **Use Case**: Production deployments, cloud hosting, 100+ concurrent agents
- **Full Features**: Same as Network, plus performance optimizations

### 4. Containerized
- **Description**: "Fully containerized for portability and isolation"
- **Installs**:
  - Docker Desktop
  - Docker Compose orchestration
  - All services in containers
  - Volume persistence
- **Use Case**: Microservices architecture, Kubernetes deployment, cloud-native
- **Full Features**: Same as any above, but containerized

## Installer Flow Redesign

### Phase 1: Environment Detection
```
[Bootstrap.py starts]
  ├─> Detect OS (Windows/Mac/Linux)
  ├─> Check Python version
  ├─> Check admin/sudo availability
  ├─> Detect existing installations
  └─> Choose CLI or GUI installer
```

### Phase 2: Profile Selection
```
[Installer starts]
  ├─> Welcome & explain what GiljoAI MCP does
  ├─> Show installation profiles with descriptions
  ├─> User selects profile
  └─> Show what will be installed
```

### Phase 3: Dependency Installation

#### PostgreSQL Installation Flow
```
If PostgreSQL selected:
  ├─> Check if PostgreSQL installed
  │   ├─> If YES: Test connection, get credentials
  │   └─> If NO:
  │       ├─> Windows: Download & run PostgreSQL installer
  │       ├─> Mac: brew install postgresql OR download .dmg
  │       └─> Linux: apt/yum install postgresql
  ├─> Initialize database
  ├─> Create giljo_mcp database
  └─> Store connection details
```

#### Redis Installation Flow
```
Always install Redis (now standard):
  ├─> Check if Redis installed
  │   ├─> If YES: Test connection
  │   └─> If NO:
  │       ├─> Windows: Download Redis Windows build
  │       ├─> Mac: brew install redis
  │       └─> Linux: apt/yum install redis
  ├─> Configure Redis for persistence
  └─> Start Redis service
```

#### Docker Installation Flow
```
If Docker profile selected:
  ├─> Check if Docker installed
  │   ├─> If YES: Check Docker daemon running
  │   └─> If NO:
  │       ├─> Windows: Guide to Docker Desktop installer
  │       ├─> Mac: Guide to Docker Desktop installer
  │       └─> Linux: Run docker install script
  ├─> Generate docker-compose.yml
  ├─> Build containers
  └─> Start services
```

### Phase 4: Configuration
```
Based on profile:
  ├─> Set appropriate ports
  ├─> Configure security (API keys, JWT)
  ├─> Set CORS for network access
  ├─> Generate .env file
  └─> Create config.yaml
```

### Phase 5: Validation & Launch
```
Final steps:
  ├─> Run health checks on all services
  ├─> Show connection URLs
  ├─> Create desktop shortcuts
  ├─> Show platform integration instructions
  └─> Offer to launch dashboard
```

## Implementation Checklist

### Core Installer Tasks
- [ ] Create profile selection UI/CLI interface
- [ ] Implement OS-specific package detection
- [ ] Write dependency installation modules
- [ ] Create rollback mechanism for failed installs
- [ ] Add progress reporting with time estimates
- [ ] Implement health check system

### Dependency Installers

#### PostgreSQL Installer Module
- [ ] Windows: PowerShell script to download & install PostgreSQL
- [ ] Mac: Homebrew integration OR DMG downloader
- [ ] Linux: Package manager detection (apt/yum/dnf)
- [ ] Database initialization script
- [ ] User creation and permissions
- [ ] Connection testing

#### Redis Installer Module
- [ ] Windows: Download and extract Redis
- [ ] Mac: Homebrew integration
- [ ] Linux: Package manager integration
- [ ] Configuration file generation
- [ ] Service registration
- [ ] Persistence configuration

#### Docker Module
- [ ] Docker Desktop detection
- [ ] Installation guide/automation
- [ ] docker-compose.yml generator
- [ ] Container builder
- [ ] Network configuration
- [ ] Volume mapping setup

### Configuration Management
- [ ] Profile-based config templates
- [ ] Dynamic .env generation
- [ ] config.yaml templates
- [ ] Service discovery
- [ ] Port conflict resolution
- [ ] Security configuration

### Post-Installation
- [ ] Service health dashboard
- [ ] Upgrade command: `giljo-mcp upgrade`
- [ ] Reconfigure command: `giljo-mcp reconfigure`
- [ ] Backup command: `giljo-mcp backup`
- [ ] Migration tools for profile changes

### Documentation
- [ ] Installation guide per profile
- [ ] Troubleshooting guide
- [ ] Migration guides between profiles
- [ ] Platform integration guides
- [ ] Video tutorials

## User Experience Improvements

### 1. Smart Defaults
- Auto-select profile based on detected environment
- Pre-fill configuration with sensible defaults
- One-click installation for common setups

### 2. Clear Communication
- Explain what each component does
- Show time estimates for installation
- Provide clear error messages with solutions
- Success confirmation at each step

### 3. Recovery Options
- Rollback on failure
- Save installation state for resume
- Offline installation support
- Manual override options

### 4. Post-Install Support
- Built-in diagnostic tools
- Update notifications
- Performance recommendations
- Configuration validation

## Technical Implementation Details

### Installer Architecture
```
bootstrap.py
├── installer/
│   ├── core/
│   │   ├── detector.py      # OS & environment detection
│   │   ├── profile.py       # Profile definitions
│   │   └── health.py        # Health checks
│   ├── dependencies/
│   │   ├── postgresql.py    # PostgreSQL installer
│   │   ├── redis.py         # Redis installer
│   │   ├── docker.py        # Docker installer
│   │   └── python_deps.py   # Python packages
│   ├── ui/
│   │   ├── gui_installer.py # Tkinter GUI
│   │   └── cli_installer.py # Terminal UI
│   └── utils/
│       ├── download.py      # Download helpers
│       ├── service.py       # Service management
│       └── rollback.py      # Rollback mechanism
```

### Platform-Specific Handlers

#### Windows
- Use PowerShell for installations
- Register Windows services
- Create Start Menu entries
- Handle UAC elevation

#### macOS
- Homebrew integration
- launchd service management
- Application bundle creation
- Gatekeeper handling

#### Linux
- Package manager detection
- systemd service files
- Desktop entry creation
- Sudo handling

## Success Metrics
1. **Installation Success Rate**: >95% successful installs
2. **Time to Complete**: <10 minutes for basic, <20 minutes for full
3. **User Errors**: <5% require support
4. **Dependency Success**: 100% of selected dependencies working
5. **Rollback Success**: 100% clean rollback on failure

## Timeline
- **Week 1**: Core installer refactor, profile system
- **Week 2**: PostgreSQL & Redis installers
- **Week 3**: Docker support, service management
- **Week 4**: Testing, documentation, polish

## Next Steps
1. Review and approve this plan
2. Create detailed technical specifications
3. Build dependency installer modules
4. Test on all target platforms
5. Create user documentation
6. Beta test with real users

---

## Notes for Implementation

### Critical Decisions Needed
1. Should we bundle Redis for Windows or download at install time?
2. Should Docker be a separate installer or integrated?
3. How much automation vs user control for enterprise installs?
4. Should we support air-gapped installations?

### Risk Mitigation
- Always provide SQLite fallback
- Test all dependency URLs regularly
- Maintain compatibility with manual installations
- Provide uninstaller for clean removal

This plan transforms the installer from a simple configurator into a comprehensive installation experience that actually delivers on the promise of "quick start".