# Technical Architecture of Complex Serena Implementation

This document describes the technical architecture of the deprecated complex Serena MCP
integration system. This is for reference only - do not reimplement this architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                        │
│                   SerenaAttachStep.vue                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ not_detected │→ │  detected    │→ │  configured  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP API Calls
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Setup Endpoints (/api/setup/)              │  │
│  │  GET /detect-serena  POST /attach-serena             │  │
│  │  POST /detach-serena                                 │  │
│  └──────────────┬──────────────────────┬─────────────────┘  │
│                 ↓                      ↓                     │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │  SerenaDetector      │  │ ClaudeConfigManager  │        │
│  │  - detect()          │  │ - inject_serena()    │        │
│  │  - _check_uvx()      │  │ - remove_serena()    │        │
│  │  - _check_serena()   │  │ - _atomic_write()    │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                 ↓                      ↓                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ConfigService                            │  │
│  │  - get_serena_config()                               │  │
│  │  - invalidate_cache()                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  External Systems                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  subprocess │  │ ~/.claude   │  │ config.yaml│           │
│  │  uvx/serena │  │   .json     │  │            │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. SerenaDetector Service

**Purpose**: Detect if Serena MCP is installed via uvx

**File**: `src/giljo_mcp/services/serena_detector.py`

**Architecture**:
```python
class SerenaDetector:
    def detect() -> dict:
        # Returns: {installed, uvx_available, version, error}

    def _check_uvx() -> tuple[bool, str]:
        # subprocess.run(["uvx", "--version"])
        # Timeout: 5 seconds

    def _check_serena() -> tuple[bool, str, str]:
        # subprocess.run(["uvx", "serena", "--version"])
        # Timeout: 10 seconds

    def _parse_version(output: str) -> str:
        # Regex: r"v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)"
```

**Key Features**:
- Cross-platform subprocess execution (shell=False for security)
- Timeout handling for hung processes
- Version parsing with regex
- Error recovery and logging

**Flaws**:
- Can't tell if Claude Code has Serena configured
- Subprocess calls add latency and failure modes
- Version detection is nice-to-have, not need-to-have

### 2. ClaudeConfigManager Service

**Purpose**: Manage ~/.claude.json MCP server configuration

**File**: `src/giljo_mcp/services/claude_config_manager.py`

**Architecture**:
```python
class ClaudeConfigManager:
    def inject_serena(project_root: Path) -> dict:
        # 1. Load ~/.claude.json (or create new)
        # 2. Backup existing config
        # 3. Add/update Serena entry in mcpServers
        # 4. Validate configuration
        # 5. Atomic write (temp file + replace)
        # 6. Rollback on failure

    def remove_serena() -> dict:
        # 1. Load ~/.claude.json
        # 2. Backup existing config
        # 3. Remove serena from mcpServers
        # 4. Atomic write
        # 5. Rollback on failure

    def _load_config() -> dict:
        # UTF-8 encoding for unicode support
        # JSON parsing with error handling

    def _backup_claude_config() -> Path:
        # ~/.claude_backups/claude_config_backup_TIMESTAMP.json

    def _restore_backup(backup_path: Path):
        # Copy backup back to ~/.claude.json

    def _add_serena_config(config: dict, project_root: Path) -> dict:
        # config["mcpServers"]["serena"] = {
        #     "command": "uvx",
        #     "args": ["serena"],
        #     "env": {"SERENA_PROJECT_ROOT": str(project_root)}
        # }

    def _validate_serena_config(config: dict) -> bool:
        # Validate structure and required fields

    def _atomic_write(config: dict):
        # 1. Create temp file in same directory
        # 2. Write JSON to temp file
        # 3. Atomically replace original (Path.replace())
```

**Key Features**:
- Atomic writes prevent corrupted config
- Backup/restore on failure
- UTF-8 encoding for unicode characters
- Transactional semantics

**Flaws**:
- Assumes single ~/.claude.json (what about multiple projects?)
- Manipulates file outside our project scope
- Can't know if changes actually affect Claude Code
- Complex rollback logic for simple operation

### 3. ConfigService

**Purpose**: Centralized config.yaml management with caching

**File**: `src/giljo_mcp/services/config_service.py`

**Architecture**:
```python
class ConfigService:
    def __init__(config_path: Path):
        self._cache = {}
        self._cache_ttl = 60  # seconds
        self._lock = threading.RLock()

    def get_serena_config(use_cache: bool = True) -> dict:
        # Returns: features.serena_mcp from config.yaml
        # Caches for 60 seconds

    def invalidate_cache():
        # Force re-read on next access
```

**Key Features**:
- Thread-safe caching with RLock
- TTL-based cache invalidation
- Graceful degradation on missing config

**Flaws**:
- Caching adds complexity for rarely-changing config
- Thread safety is overkill for single-process app
- Could just read YAML file directly each time

### 4. Frontend State Machine

**Purpose**: UI flow for detection → attachment → configuration

**File**: `frontend/src/components/setup/SerenaAttachStep.vue`

**Architecture**:
```javascript
// State transitions:
// not_detected → detected → configured

const state = ref('not_detected')

// Methods:
detectSerena()
  → GET /api/setup/detect-serena
  → state = 'detected' or 'not_detected'

attachSerena()
  → POST /api/setup/attach-serena
  → state = 'configured'

// UI Elements:
- not_detected: "Serena Not Detected" + "How to Install" button
- detected: "Serena Detected" + "Attach to Claude Code" button
- configured: "Serena Configured" + success message
```

**Key Features**:
- Three-state machine for linear flow
- Installation dialog with uvx/local tabs
- Error handling and retry
- Progress indicators

**Flaws**:
- Three states for what is essentially ON/OFF
- Detection state doesn't guarantee usability
- Configured state misleading (user might not have restarted Claude Code)

### 5. API Endpoints

**Purpose**: HTTP interface for Serena operations

**File**: `api/endpoints/setup.py` (hypothetical - not yet implemented)

**Architecture**:
```python
# GET /api/setup/detect-serena
async def detect_serena():
    detector = SerenaDetector()
    result = detector.detect()
    return {
        "installed": result["installed"],
        "uvx_available": result["uvx_available"],
        "version": result["version"],
        "error": result["error"]
    }

# POST /api/setup/attach-serena
async def attach_serena():
    project_root = Path.cwd()
    manager = ClaudeConfigManager()
    result = manager.inject_serena(project_root)
    return {
        "success": result["success"],
        "backup_path": result["backup_path"],
        "error": result["error"]
    }

# POST /api/setup/detach-serena
async def detach_serena():
    manager = ClaudeConfigManager()
    result = manager.remove_serena()
    return {
        "success": result["success"],
        "message": result["message"],
        "error": result["error"]
    }
```

**Key Features**:
- RESTful design
- Async/await for non-blocking I/O
- Consistent response format

**Flaws**:
- Endpoints for operations we shouldn't do
- No authentication/authorization
- No rate limiting for subprocess calls

## Data Flow

### Detection Flow

```
User clicks "Check Again"
  ↓
Frontend calls GET /api/setup/detect-serena
  ↓
API instantiates SerenaDetector
  ↓
detector._check_uvx()
  ↓ subprocess.run(["uvx", "--version"], timeout=5)
  ↓ uvx available?
  ↓
detector._check_serena()
  ↓ subprocess.run(["uvx", "serena", "--version"], timeout=10)
  ↓ serena available?
  ↓
detector._parse_version(output)
  ↓ regex match version number
  ↓
Return {installed: true/false, version: "x.y.z", error: null}
  ↓
Frontend updates state = 'detected' or 'not_detected'
```

### Attachment Flow

```
User clicks "Attach to Claude Code"
  ↓
Frontend calls POST /api/setup/attach-serena
  ↓
API instantiates ClaudeConfigManager
  ↓
manager._load_config()
  ↓ Read ~/.claude.json (UTF-8)
  ↓
manager._backup_claude_config()
  ↓ Copy to ~/.claude_backups/backup_TIMESTAMP.json
  ↓
manager._add_serena_config(config, project_root)
  ↓ config["mcpServers"]["serena"] = {...}
  ↓
manager._validate_serena_config(config)
  ↓ Check structure and required fields
  ↓
manager._atomic_write(config)
  ↓ Create temp file
  ↓ Write JSON
  ↓ Atomically replace original
  ↓
Return {success: true, backup_path: "...", error: null}
  ↓
Frontend updates state = 'configured'
```

### Error Recovery Flow

```
Any failure in attachment flow
  ↓
manager._restore_backup(backup_path)
  ↓ Copy backup back to ~/.claude.json
  ↓
Return {success: false, error: "..."}
  ↓
Frontend displays error alert
  ↓
State remains 'detected' (can retry)
```

## Security Considerations

### Subprocess Security
- **shell=False**: Prevents shell injection attacks
- **Timeout**: Prevents hung processes
- **No user input**: Commands are hardcoded

### File System Security
- **Path validation**: No path traversal (would be needed if taking user input)
- **UTF-8 encoding**: Handles unicode characters
- **Atomic writes**: Prevents partial writes

### API Security
- **CORS**: Would need to validate origins
- **Rate limiting**: Would need to prevent DoS via subprocess calls
- **Authentication**: Would need API keys for public deployment

**Flaw**: All this security is for operations we shouldn't do in the first place

## Testing Strategy

### Unit Tests
- `test_serena_detector.py`: Test detection logic
- `test_claude_config_manager.py`: Test config manipulation
- `test_config_service.py`: Test caching

### Integration Tests (2054 lines total)
- `test_setup_serena_api.py`: API endpoint testing (456 lines)
- `test_serena_services_integration.py`: Service integration (475 lines)
- `test_serena_cross_platform.py`: Platform compatibility (330 lines)
- `test_serena_error_recovery.py`: Error handling (380 lines)
- `test_serena_security.py`: Security validation (413 lines)

### Coverage
- Target: 95%+
- Achieved: ~95% for services
- Cost: 2054 lines of test code

**Flaw**: High coverage of the wrong functionality

## Performance Characteristics

### Detection Performance
- **Best case**: 2-3 seconds (uvx + serena both succeed quickly)
- **Worst case**: 15+ seconds (timeouts on both checks)
- **Average**: 5-7 seconds

### Attachment Performance
- **Best case**: 50-100ms (small .claude.json)
- **Worst case**: 500ms+ (large config, slow disk)
- **Average**: 100-200ms

### Memory Usage
- **SerenaDetector**: ~1MB (subprocess overhead)
- **ClaudeConfigManager**: ~5-10MB (JSON parsing, temp files)
- **ConfigService**: ~100KB (cached config)

**Comparison to Simple Approach**:
- Detection: 0ms (no detection)
- Config read: 5-10ms (read YAML once)
- Memory: ~50KB (config in memory)

## Deployment Considerations

### Dependencies
- `subprocess` (Python stdlib)
- `json` (Python stdlib)
- `pathlib` (Python stdlib)
- `tempfile` (Python stdlib)
- `shutil` (Python stdlib)
- `yaml` (PyYAML package)

### Platform Support
- Windows: ✅ Tested
- macOS: ⚠️ Assumed working (not tested)
- Linux: ⚠️ Assumed working (not tested)

### Error Modes
1. **uvx not installed**: User must install uvx first
2. **Serena not found**: User must install Serena
3. **.claude.json invalid**: Backup and restore mechanism
4. **.claude.json missing**: Create new file
5. **Permissions error**: User must fix permissions
6. **Subprocess timeout**: User must debug environment

**Flaw**: Many failure modes, all preventable by not doing this

## Why This Architecture Failed

### 1. Wrong Abstraction Layer
We built infrastructure to manage Claude Code's configuration, but we're not Claude Code.

### 2. Assumed Single Source of Truth
We assumed ~/.claude.json is the only config, but users might have project-specific configs.

### 3. Complex Solution to Simple Problem
We built a distributed system (subprocess, file I/O, state machine) for "include text in prompt or not".

### 4. Testing the Wrong Thing
We tested subprocess calls, file manipulation, and error recovery instead of prompt injection.

### 5. Ignored User Boundaries
We manipulated files outside our project scope, violating separation of concerns.

## The Correct Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                        │
│                  Settings Toggle                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  [✓] Use Serena MCP tools in agent prompts          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ Update config.yaml
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   config.yaml                                │
│  features:                                                   │
│    serena_mcp:                                              │
│      use_in_prompts: true/false                             │
└────────────────────────┬────────────────────────────────────┘
                         │ Read on prompt generation
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                TemplateManager                               │
│  if config['features']['serena_mcp']['use_in_prompts']:     │
│      prompt += SERENA_INSTRUCTIONS                          │
└─────────────────────────────────────────────────────────────┘
```

**Lines of code**: ~50 vs ~5000
**Complexity**: Low vs Very High
**Failure modes**: 1 vs 8
**User control**: Clear vs Obscured

## Conclusion

This architecture demonstrates how to over-engineer a simple feature by:
1. Adding unnecessary abstraction layers
2. Managing systems outside our control
3. Testing implementation details instead of behavior
4. Ignoring the user's actual mental model

The correct architecture is 100x simpler because it respects boundaries and solves the actual problem (prompt inclusion) rather than an imagined problem (Claude Code configuration).

---

**Date**: October 6, 2025
**Author**: Documentation Manager Agent
**Purpose**: Technical reference for deprecated architecture
**Status**: For learning purposes only - do not reimplement
