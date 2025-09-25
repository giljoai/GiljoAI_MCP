@echo off
REM Manual script to sync master to release branch (Windows version)
REM This mimics what the GitHub Action does

echo ===============================================
echo Release Sync: master to release-giljoai-mcp
echo ===============================================
echo.

REM Ensure we're on master and up to date
echo Checking out master branch...
git checkout master
if %errorlevel% neq 0 exit /b 1

echo Pulling latest master...
git pull origin master
if %errorlevel% neq 0 exit /b 1

REM Get current master commit
for /f %%i in ('git rev-parse --short HEAD') do set MASTER_COMMIT=%%i

REM Create or checkout release branch
echo.
echo Preparing release branch...
git show-ref --verify --quiet refs/heads/release-giljoai-mcp
if %errorlevel% equ 0 (
    git checkout release-giljoai-mcp
    git pull origin release-giljoai-mcp 2>nul
) else (
    git checkout -b release-giljoai-mcp
)

REM Reset to master
echo Syncing with master...
git reset --hard master

REM Remove files according to .release-ignore
if exist .release-ignore (
    echo.
    echo Processing .release-ignore patterns...

    REM This is simplified - for complex patterns, use the bash script via Git Bash
    REM Remove test directories
    if exist tests rmdir /s /q tests
    git rm -rf --ignore-unmatch tests 2>nul

    REM Remove CI/CD files
    if exist .github\workflows\ci.yml del .github\workflows\ci.yml
    git rm -f --ignore-unmatch .github/workflows/ci.yml 2>nul

    REM Remove development docs
    if exist docs\Sessions rmdir /s /q docs\Sessions
    if exist docs\devlog rmdir /s /q docs\devlog
    if exist docs\Vision rmdir /s /q docs\Vision
    git rm -rf --ignore-unmatch docs/Sessions docs/devlog docs/Vision 2>nul

    REM Remove .release-ignore itself
    del .release-ignore
    git rm -f --ignore-unmatch .release-ignore 2>nul
)

REM Stage all changes
git add -A

REM Check if there are changes
git diff --staged --quiet
if %errorlevel% neq 0 (
    echo.
    echo Committing release version...
    git commit -m "Release sync from master@%MASTER_COMMIT%"

    echo.
    echo ===============================================
    echo Release branch prepared successfully!
    echo ===============================================
    echo.
    echo To push to remote, run:
    echo   git push origin release-giljoai-mcp --force-with-lease
) else (
    echo.
    echo No changes needed - release branch is already in sync
)

echo.
echo Current branch: release-giljoai-mcp
echo Latest commit: %MASTER_COMMIT%
echo.