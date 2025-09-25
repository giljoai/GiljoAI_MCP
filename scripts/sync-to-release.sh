#!/bin/bash
# Manual script to sync master to release branch
# This mimics what the GitHub Action does

set -e

echo "🔄 Starting release sync from master to release-giljoai-mcp..."

# Ensure we're on master and up to date
git checkout master
git pull origin master

# Get current master commit
MASTER_COMMIT=$(git rev-parse --short HEAD)

# Create or checkout release branch
if git show-ref --verify --quiet refs/heads/release-giljoai-mcp; then
    git checkout release-giljoai-mcp
    git pull origin release-giljoai-mcp || true
else
    git checkout -b release-giljoai-mcp
fi

# Reset to master
git reset --hard master

# Remove files according to .release-ignore
if [ -f .release-ignore ]; then
    echo "📝 Processing .release-ignore patterns..."

    while IFS= read -r pattern || [ -n "$pattern" ]; do
        # Skip comments and empty lines
        [[ "$pattern" =~ ^#.*$ ]] && continue
        [ -z "$pattern" ] && continue

        echo "  Removing: $pattern"

        # Remove matching files/directories
        find . -name "$pattern" -type f -delete 2>/dev/null || true
        find . -name "$pattern" -type d -exec rm -rf {} + 2>/dev/null || true

        # Also remove from git index
        git rm -rf --ignore-unmatch "$pattern" 2>/dev/null || true
    done < .release-ignore

    # Remove .release-ignore itself
    rm -f .release-ignore
    git rm -f --ignore-unmatch .release-ignore 2>/dev/null || true
fi

# Clean up empty directories
find . -type d -empty -delete 2>/dev/null || true

# Stage all changes
git add -A

# Commit if there are changes
if ! git diff --staged --quiet; then
    git commit -m "Release sync from master@${MASTER_COMMIT}

Auto-generated production release excluding development files.
Source: master@${MASTER_COMMIT}"

    echo "✅ Release branch prepared successfully"
    echo ""
    echo "📊 Summary of excluded files:"
    git diff --name-status HEAD~1 | grep '^D' | head -20
    echo ""
    echo "To push to remote, run:"
    echo "  git push origin release-giljoai-mcp --force-with-lease"
else
    echo "ℹ️  No changes needed - release branch is already in sync"
fi

echo ""
echo "🎯 Current branch: $(git branch --show-current)"
echo "📍 Latest commit: $(git rev-parse --short HEAD)"