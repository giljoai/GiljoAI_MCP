# Installer Flow Visual Comparison

## GUI Installer Flow (setup_gui.py) - REFERENCE

```mermaid
graph TD
    Start([Start GUI])
    Start --> Welcome[Welcome Page<br/>Logo & Introduction]
    Welcome --> ModeSelect[Profile Selection Page<br/>- Localhost Mode<br/>- Server Mode]
    ModeSelect --> Database[Database Page<br/>- PostgreSQL Config<br/>- Test Connection<br/>- Create Database]
    Database --> Ports[Ports Page<br/>- Server Port<br/>- Network Mode<br/>localhost vs network]
    Ports --> Security{Server Mode?}
    Security -->|Yes| SecurityPage[Security Page<br/>- API Key Gen<br/>- CORS Config]
    Security -->|No| Review
    SecurityPage --> Review[Review Page<br/>- Show All Config<br/>- Allow Edits]
    Review --> Install[Progress Page<br/>- Package-level tracking<br/>- Real-time status<br/>- Error recovery]
    Install --> Complete[Complete<br/>- Summary<br/>- Next Steps]

    Review -.->|Back| Ports
    Ports -.->|Back| Database
    Database -.->|Back| ModeSelect
    SecurityPage -.->|Back| Ports
```

## CLI Installer Flow (setup_cli.py) - CURRENT

```mermaid
graph TD
    Start([Start CLI])
    Start --> Welcome[ASCII Welcome<br/>Logo Display]
    Welcome --> PGCheck{PostgreSQL<br/>Installed?}
    PGCheck -->|No| PGInstall[Install PostgreSQL<br/>Inline Process]
    PGCheck -->|Yes| ModeSelect
    PGInstall --> ModeSelect[Mode Selection<br/>1. Local Development<br/>2. Server Deployment]
    ModeSelect --> PGConfig[PostgreSQL Config<br/>- Connection params<br/>- Database creation]
    PGConfig --> PortConfig[Port Configuration<br/>Simple prompt]
    PortConfig --> InstallDeps[Install Dependencies<br/>Basic progress]
    InstallDeps --> Summary[Summary Display<br/>Configuration shown]

    style PGInstall fill:#ffcccc
    style PortConfig fill:#ffffcc
    style InstallDeps fill:#ffffcc
```

## CLI Installer Flow - PROPOSED ALIGNED

```mermaid
graph TD
    Start([Start CLI])
    Start --> Welcome[ASCII Welcome<br/>Logo Display]
    Welcome --> ModeSelect[Mode Selection<br/>1. Localhost Mode<br/>2. Server Mode]
    ModeSelect --> PGCheck{PostgreSQL<br/>Installed?}
    PGCheck -->|No| PGInstall[Install PostgreSQL<br/>Guided Process]
    PGCheck -->|Yes| PGConfig
    PGInstall --> PGConfig[PostgreSQL Config<br/>- Connection test<br/>- Database creation]
    PGConfig --> NetworkMode[Network Mode<br/>- Localhost only<br/>- Network accessible]
    NetworkMode --> PortConfig[Port Configuration<br/>- Server port<br/>- Validation]
    PortConfig --> Security{Server Mode?}
    Security -->|Yes| SecurityConfig[Security Config<br/>- API Key Gen<br/>- CORS Settings]
    Security -->|No| Review
    SecurityConfig --> Review[Review Config<br/>- Show all settings<br/>- Option to modify]
    Review --> InstallDeps[Install Dependencies<br/>- Package tracking<br/>- Progress display]
    InstallDeps --> Complete[Complete<br/>- Summary<br/>- Logs location<br/>- Next steps]

    Review -.->|Modify| ModeSelect

    style ModeSelect fill:#ccffcc
    style NetworkMode fill:#ccffcc
    style SecurityConfig fill:#ccffcc
    style Review fill:#ccffcc
```

## Key Visual Differences

### Current Gaps (Red/Yellow items in Current CLI)
- 🔴 **PostgreSQL First**: CLI checks PostgreSQL before mode selection (wrong order)
- 🟡 **No Network Mode**: CLI doesn't explicitly set network binding
- 🟡 **Basic Port Config**: No validation or network mode consideration
- 🟡 **No Security Page**: CORS configuration missing
- 🔴 **No Review Step**: Can't review before installation
- 🟡 **Basic Progress**: No package-level tracking

### Proposed Improvements (Green items)
- ✅ **Aligned Mode Names**: "localhost" and "server"
- ✅ **Mode Selection First**: Matches GUI flow order
- ✅ **Network Mode Selection**: Explicit binding configuration
- ✅ **Security Configuration**: API key and CORS for server mode
- ✅ **Review Step**: See all config before installing
- ✅ **Navigation**: Can modify configuration before commit

## Side-by-Side Comparison Table

| Step | GUI Page | Current CLI | Proposed CLI | Status |
|------|----------|-------------|--------------|--------|
| 1 | Welcome with Logo | ASCII Welcome | ASCII Welcome | ✅ OK |
| 2 | Mode Selection (localhost/server) | PostgreSQL Check | Mode Selection | 🔴 Fix Order |
| 3 | PostgreSQL Config | Mode Selection | PostgreSQL Check | 🔴 Fix Order |
| 4 | Port + Network Config | PostgreSQL Config | PostgreSQL Config | ✅ OK |
| 5 | Security (if server) | Port Config (basic) | Network Mode | 🆕 Add |
| 6 | Review Page | Install Dependencies | Port Config | ⚡ Enhance |
| 7 | Progress Install | Summary | Security (if server) | 🆕 Add |
| 8 | Complete | - | Review | 🆕 Add |
| 9 | - | - | Install with Progress | ⚡ Enhance |
| 10 | - | - | Complete | ✅ OK |

## User Decision Points Comparison

### GUI Decision Points
1. **Mode**: Radio button selection with descriptions
2. **PostgreSQL**: Multiple fields, test button
3. **Ports**: Spinner control with validation
4. **Network**: Dropdown (localhost/network)
5. **CORS**: Text field for origins (server only)
6. **Review**: Next/Back/Cancel buttons

### CLI Current Decision Points
1. **PostgreSQL Install**: Y/N prompt
2. **Mode**: Menu 1/2 selection
3. **PostgreSQL Config**: Sequential prompts
4. **Port**: Simple number input
5. **Continue**: Y/N at errors only

### CLI Proposed Decision Points
1. **Mode**: Menu 1/2 selection (FIRST)
2. **PostgreSQL Install**: Y/N if needed
3. **PostgreSQL Config**: Sequential with validation
4. **Network Mode**: Menu 1/2 (server only)
5. **Port**: Number with validation
6. **CORS**: Multi-line input (server only)
7. **Review**: 1=Continue/2=Modify/3=Cancel

## Implementation Effort Estimate

| Component | LOC Estimate | Complexity | Time |
|-----------|-------------|------------|------|
| Mode Name Alignment | ~20 lines | Low | 30 min |
| CORS Configuration | ~50 lines | Medium | 2 hours |
| Network Mode Selection | ~40 lines | Medium | 1.5 hours |
| Review Step | ~80 lines | Medium | 2 hours |
| Enhanced Progress | ~100 lines | Medium | 3 hours |
| Improved Error Handling | ~150 lines | High | 4 hours |
| Logging System | ~60 lines | Low | 1.5 hours |
| **Total Estimate** | **~500 lines** | **Medium** | **~14 hours** |

---

*Visual comparison for quick reference during implementation*