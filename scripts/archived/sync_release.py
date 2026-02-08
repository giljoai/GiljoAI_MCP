#!/usr/bin/env python3
"""
Sync specific fixes from master to release branch
Use this when you need to apply hotfixes to the release
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
        return None
    return result.stdout.strip()


def main():
    # Ensure we're in the repo root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    print("=== GiljoAI MCP Release Sync Tool ===\n")
    print("This tool helps sync specific files from master to release\n")

    # Check current branch
    current_branch = run_cmd("git branch --show-current")
    print(f"Current branch: {current_branch}")

    # Show recent commits on master
    print("\n=== Recent commits on master ===")
    commits = run_cmd("git log master --oneline -10")
    print(commits)

    # Get the specific files to sync
    print("\n=== Files to sync ===")
    print("Enter the files you want to sync from master to release")
    print("(one per line, empty line to finish):")

    files_to_sync = []
    while True:
        file_path = input("> ").strip()
        if not file_path:
            break
        if Path(file_path).exists():
            files_to_sync.append(file_path)
        else:
            print(f"Warning: {file_path} not found")

    if not files_to_sync:
        print("No files to sync")
        sys.exit(0)

    print(f"\nFiles to sync: {files_to_sync}")
    response = input("Continue? [y/N]: ")
    if response.lower() != "y":
        sys.exit(0)

    # Switch to release branch
    print("\nSwitching to release branch...")
    run_cmd("git checkout release-giljoai-mcp")

    # Copy files from master
    print("\nCopying files from master...")
    for file_path in files_to_sync:
        print(f"Syncing {file_path}...")
        # Get the file content from master
        run_cmd(f"git checkout master -- {file_path}")

    # Check what changed
    changes = run_cmd("git diff --stat")
    if not changes:
        print("No changes to commit")
        run_cmd("git checkout " + current_branch)
        sys.exit(0)

    print("\n=== Changes to be committed ===")
    print(changes)

    # Commit the changes
    commit_msg = input("\nEnter commit message: ").strip()
    if not commit_msg:
        commit_msg = "Sync fixes from master branch"

    run_cmd("git add " + " ".join(files_to_sync))
    run_cmd(f'git commit -m "{commit_msg}"')

    # Push to remote
    response = input("\nPush to remote? [y/N]: ")
    if response.lower() == "y":
        run_cmd("git push origin release-giljoai-mcp")
        print("\n✓ Changes pushed to release branch")

    # Return to original branch
    print(f"\nReturning to {current_branch}...")
    run_cmd(f"git checkout {current_branch}")

    print("\n=== Sync Complete ===")


if __name__ == "__main__":
    main()
