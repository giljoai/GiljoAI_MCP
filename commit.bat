@echo off
REM Smart commit script that handles pre-commit hook fixes
echo Committing changes...

REM First attempt
git add .
git commit %*

REM If commit failed due to pre-commit fixes, try again
if %ERRORLEVEL% NEQ 0 (
    echo Pre-commit hooks made changes, retrying...
    git add .
    git commit %*
)

if %ERRORLEVEL% EQU 0 (
    echo Commit successful!
) else (
    echo Commit failed!
)