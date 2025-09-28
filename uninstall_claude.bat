@echo off
REM Complete Claude Code Uninstaller Launcher
REM Removes all traces of Claude Code and optionally MCP servers

title Claude Code Complete Uninstaller
color 0E

echo ============================================================
echo             Claude Code Complete Uninstaller
echo ============================================================
echo.
echo This will completely remove Claude Code and all its data!
echo.
echo Options:
echo   1. Complete uninstall (Claude + Serena MCP)
echo   2. Claude only (keep MCP configurations)
echo   3. Dry run (see what would be removed)
echo   4. Custom options
echo   5. Exit
echo.

set /p choice="Select option (1-5): "

if "%choice%"=="1" goto complete
if "%choice%"=="2" goto claude_only
if "%choice%"=="3" goto dry_run
if "%choice%"=="4" goto custom
if "%choice%"=="5" goto end

echo Invalid choice!
pause
goto end

:complete
echo.
echo Starting complete uninstall (Claude + Serena MCP)...
python uninstall_claude_complete.py --remove-serena
goto done

:claude_only
echo.
echo Starting Claude-only uninstall...
python uninstall_claude_complete.py --no-remove-serena
goto done

:dry_run
echo.
echo Running dry run (no changes will be made)...
python uninstall_claude_complete.py --dry-run --remove-serena
goto done

:custom
echo.
echo Custom Options:
echo   --dry-run         : Show what would be removed without removing
echo   --remove-serena   : Also remove Serena MCP
echo   --remove-all-mcp  : Remove ALL MCP configurations
echo   --skip-npm        : Skip npm uninstall
echo   --quiet          : Minimal output
echo.
set /p args="Enter options: "
python uninstall_claude_complete.py %args%
goto done

:done
echo.
echo ============================================================
echo                    Process Complete
echo ============================================================
echo.
pause

:end