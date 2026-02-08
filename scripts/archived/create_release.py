#!/usr/bin/env python3
"""
Create a clean release branch from master
This script maintains a clean release branch without development artifacts
"""

import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, check=True):
    """Run a shell command and return output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
    if result.returncode != 0 and check:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def main():
    # Ensure we're in the repo root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    print("=== GiljoAI MCP Release Branch Creator ===\n")

    # Check current branch
    current_branch = run_cmd("git branch --show-current")
    print(f"Current branch: {current_branch}")

    if current_branch != "master":
        response = input("You're not on master branch. Switch to master? [y/N]: ")
        if response.lower() == "y":
            run_cmd("git checkout master")
        else:
            print("Please switch to master branch first")
            sys.exit(1)

    # Check for uncommitted changes
    status = run_cmd("git status --porcelain")
    if status:
        print("You have uncommitted changes:")
        print(status)
        response = input("Stash changes and continue? [y/N]: ")
        if response.lower() == "y":
            run_cmd("git stash push -m 'Auto-stash before release creation'")
        else:
            print("Please commit or stash changes first")
            sys.exit(1)

    # Get version for tag
    version = input("Enter version number (e.g., 1.0.0): v").strip()
    if not version:
        print("Version required")
        sys.exit(1)
    version = f"v{version}"

    print(f"\nCreating release {version}...")

    # Create or update release branch
    print("\n1. Checking out release branch...")
    existing_release = run_cmd("git branch -r | grep origin/release-giljoai-mcp", check=False)

    if existing_release:
        # Update existing release branch
        run_cmd("git checkout release-giljoai-mcp")
        run_cmd("git reset --hard master")  # Make release identical to master
    else:
        # Create new release branch
        run_cmd("git checkout -b release-giljoai-mcp")

    # Remove development files using .gitignore.release
    print("\n2. Removing development files...")

    files_to_remove = [
        "docs/sessions",
        "docs/devlog",
        "docs/Development",
        "tests",
        ".vscode",
        "*.old",
        "TODO.md",
        "NOTES.md",
    ]

    for pattern in files_to_remove:
        run_cmd(f"git rm -rf --ignore-unmatch {pattern}", check=False)

    # Remove all .old files
    run_cmd("find . -name '*.old' -type f -delete", check=False)
    run_cmd("find . -name '*.bak' -type f -delete", check=False)
    run_cmd("find . -name 'test_*.py' -type f -delete", check=False)

    # Commit the cleaned version
    print("\n3. Committing clean release...")
    run_cmd("git add -A")

    # Check if there are changes to commit
    if run_cmd("git diff --cached --stat"):
        run_cmd(f'git commit -m "Release {version} - cleaned for distribution"')
    else:
        print("No changes to commit (already clean)")

    # Create tag
    print(f"\n4. Creating tag {version}...")
    run_cmd(f'git tag -a {version} -m "Release {version}"', check=False)

    # Push to remote
    print("\n5. Pushing to remote...")
    response = input("Push release branch and tag to remote? [y/N]: ")
    if response.lower() == "y":
        run_cmd("git push -f origin release-giljoai-mcp")
        run_cmd(f"git push origin {version}")
        print(f"\n✓ Release {version} created and pushed!")
    else:
        print(f"\n✓ Release {version} created locally")
        print("To push later, run:")
        print("  git push -f origin release-giljoai-mcp")
        print(f"  git push origin {version}")

    # Return to master
    print("\n6. Returning to master branch...")
    run_cmd("git checkout master")

    # Restore stash if any
    stash_list = run_cmd("git stash list", check=False)
    if "Auto-stash before release creation" in stash_list:
        print("\nRestoring stashed changes...")
        run_cmd("git stash pop")

    print("\n=== Release Creation Complete ===")
    print(f"Version: {version}")
    print("Branch: release-giljoai-mcp")
    print("\nNext steps:")
    print("1. Continue development on master branch")
    print("2. When ready for next release, run this script again")


if __name__ == "__main__":
    main()
