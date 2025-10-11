# GiljoAI MCP - Update Instructions

## When to Update Dependencies

Run the dependency updater **after pulling changes from GitHub** if:
- You get `ModuleNotFoundError` when starting services
- The `requirements.txt` file has been updated
- You're experiencing import errors

## How to Update

### Windows

Simply run:
```batch
update_dependencies.bat
```

Or manually:
```batch
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux/macOS

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Common Workflow

```bash
# 1. Pull latest changes from GitHub
git pull

# 2. Update dependencies (if requirements.txt changed)
./update_dependencies.bat  # Windows
# OR
source venv/bin/activate && pip install -r requirements.txt  # Linux/macOS

# 3. Start services
./start_giljo.bat  # Windows
# OR
./start_giljo.sh   # Linux/macOS
```

## Troubleshooting

### "No module named 'X'" Error

**Symptom**: Backend fails to start with `ModuleNotFoundError`

**Solution**: Run `update_dependencies.bat`

### Virtual Environment Not Found

**Symptom**: `venv\Scripts\python.exe` does not exist

**Solution**: Run the installer again:
```batch
python installer/cli/install.py
```

### Permission Errors

**Symptom**: Cannot write to venv directory

**Solution** (Windows): Run Command Prompt as Administrator

**Solution** (Linux/macOS): Check file permissions or recreate venv

## For Developers

After modifying `requirements.txt`:
1. Test on a fresh venv to ensure it works
2. Update this file if new dependencies have special requirements
3. Commit both `requirements.txt` and any related updates
