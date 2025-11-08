# GiljoAI MCP - Startup Modes

## Production Mode (Recommended for Remote Access)

### Prerequisites
```powershell
cd frontend
npm run build
cd ..
```

### Start Application
```powershell
python startup_prod.py
```

### With Verbose Console Output
```powershell
python startup_prod.py --verbose
```

### Features
- ✅ Serves **production-built** frontend from `frontend/dist/`
- ✅ Works with **network IP** for remote access
- ✅ **No hot-reload** (faster, stable)
- ✅ Proper **runtime API configuration** (not localhost-hardcoded)
- ✅ **SPA routing** support

---

## Development Mode (Local Development Only)

### Start Application
```powershell
python startup.py
```

### With Verbose Console Output
```powershell
python startup.py --verbose
```

### Features
- ✅ Hot-reload for **frontend development**
- ✅ Runs `npm run dev` automatically
- ❌ **Does NOT work with remote access** (localhost-only)
- ❌ May have **CORS issues** from remote machines

---

## Manual Production Start (Maximum Control)

### Option 1: Two PowerShell Windows

**Window 1 - Backend:**
```powershell
cd F:\GiljoAI_MCP
.\venv\Scripts\python.exe api\run_api.py --port 7272
```

**Window 2 - Frontend:**
```powershell
cd F:\GiljoAI_MCP
python serve_frontend.py
```

### Option 2: Single Command (Spawns 2 Windows)

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd F:\GiljoAI_MCP; .\venv\Scripts\python.exe api\run_api.py --port 7272"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd F:\GiljoAI_MCP; python serve_frontend.py"
```

---

## Startup Script Options

### Common Flags

| Flag | Description |
|------|-------------|
| `--verbose` or `-v` | Show console windows with output (Windows) |
| `--no-browser` | Skip automatic browser launch |
| `--no-migrations` | Skip database migrations |
| `--check-only` | Only check dependencies, don't start services |

### Examples

```powershell
# Production mode with verbose output, no browser
python startup_prod.py --verbose --no-browser

# Development mode, check dependencies only
python startup.py --check-only

# Production mode, skip migrations
python startup_prod.py --no-migrations
```

---

## When to Use Each Mode

| Scenario | Mode | Command |
|----------|------|---------|
| **Remote testing** | Production | `python startup_prod.py --verbose` |
| **Local development** | Development | `python startup.py --verbose` |
| **Debugging backend** | Manual | Two PowerShell windows (see above) |
| **Network deployment** | Production | `python startup_prod.py` |
| **Frontend hot-reload** | Development | `python startup.py` |

---

## Ports

- **Backend API**: `7272`
- **Frontend**: `7274`

Both are configured in `config.yaml`.

---

## Access URLs

### Production Mode
- **Localhost**: `http://localhost:7274`
- **Network**: `http://10.1.0.164:7274` (or your network IP)

### Development Mode
- **Localhost only**: `http://localhost:7274`
- **Network**: ❌ Will NOT work (dev server uses empty baseURL)

---

## Logs

### Production Mode
- Backend: `logs/api_stdout.log`, `logs/api_stderr.log`
- Frontend: `logs/frontend_prod.log`

### Development Mode
- Backend: `logs/api_stdout.log`, `logs/api_stderr.log`
- Frontend: `logs/frontend_stdout.log`, `logs/frontend_stderr.log`

---

## Troubleshooting

### "Production build not found"
```powershell
cd frontend
npm run build
```

### Port already in use
```powershell
# Check what's using the port
netstat -ano | findstr :7272
netstat -ano | findstr :7274

# Kill process by PID
taskkill /F /PID <PID>
```

### Frontend shows blank page
- Check browser console for errors
- Verify production build exists: `ls frontend/dist/`
- Check API is running: `http://localhost:7272/health`

---

## Quick Start (Remote Access)

```powershell
# 1. Build frontend (one time)
cd frontend
npm run build
cd ..

# 2. Start in production mode with verbose output
python startup_prod.py --verbose

# 3. Access from remote machine
# http://10.1.0.164:7274
```
