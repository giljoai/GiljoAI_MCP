#!/usr/bin/env python3
"""
Complete Claude Code Uninstaller
Removes all traces of Claude Code and optionally MCP servers
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import json
import argparse

class ClaudeUninstaller:
    def __init__(self, verbose=True, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.home = Path.home()
        self.removed_items = []
        self.failed_items = []

    def log(self, message, level="INFO"):
        if self.verbose:
            print(f"[{level}] {message}")

    def remove_item(self, path, description):
        """Remove a file or directory"""
        path = Path(path)
        if not path.exists():
            return False

        try:
            if self.dry_run:
                self.log(f"[DRY RUN] Would remove: {description} ({path})")
                self.removed_items.append(str(path))
                return True

            if path.is_dir():
                shutil.rmtree(path)
                self.log(f"Removed directory: {description}")
            else:
                path.unlink()
                self.log(f"Removed file: {description}")
            self.removed_items.append(str(path))
            return True
        except Exception as e:
            self.log(f"Failed to remove {description}: {e}", "ERROR")
            self.failed_items.append((str(path), str(e)))
            return False

    def uninstall_npm_package(self):
        """Uninstall Claude CLI via npm"""
        try:
            if self.dry_run:
                self.log("[DRY RUN] Would uninstall @anthropic/claude-cli via npm")
                return True

            self.log("Uninstalling @anthropic/claude-cli via npm...")
            result = subprocess.run(
                ["npm", "uninstall", "-g", "@anthropic/claude-cli"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log("Successfully uninstalled npm package")
                return True
            else:
                self.log(f"npm uninstall completed with warnings: {result.stderr}", "WARNING")
                return True
        except FileNotFoundError:
            self.log("npm not found - skipping npm uninstall", "WARNING")
            return False
        except Exception as e:
            self.log(f"Failed to uninstall npm package: {e}", "ERROR")
            return False

    def remove_claude_files(self):
        """Remove all Claude Code files and directories"""
        locations = [
            # User home directory
            (self.home / ".claude", "Claude user directory"),
            (self.home / ".claude.json", "Claude global config"),
            (self.home / ".claude.json.backup", "Claude config backup"),
            (self.home / ".claude.json.backup-*", "Claude config backups"),
            (self.home / ".claude.json.corrupted.*", "Corrupted Claude configs"),

            # Windows specific
            (self.home / "AppData" / "Local" / "claude-cli-nodejs", "Claude cache (AppData)"),
            (self.home / "AppData" / "Roaming" / "Claude", "Claude roaming data"),
            (self.home / "AppData" / "Local" / "Claude", "Claude local data"),

            # Mac/Linux specific
            (self.home / ".config" / "claude", "Claude config directory"),
            (self.home / "Library" / "Application Support" / "Claude", "Claude support files (Mac)"),
            (self.home / ".cache" / "claude", "Claude cache (Linux)"),

            # Project-specific Claude directories (current directory)
            (Path.cwd() / ".claude", "Project Claude directory"),
        ]

        for path_pattern, description in locations:
            # Handle glob patterns
            if '*' in str(path_pattern):
                parent = path_pattern.parent
                pattern = path_pattern.name
                if parent.exists():
                    for path in parent.glob(pattern):
                        self.remove_item(path, f"{description} - {path.name}")
            else:
                self.remove_item(path_pattern, description)

    def remove_mcp_servers(self, remove_serena=True, remove_all=False):
        """Remove MCP server files"""
        if remove_all:
            self.log("Removing ALL MCP server configurations...")
            locations = [
                (Path.cwd() / ".mcp.json", "MCP configuration"),
                (Path.cwd() / ".mcp-*.json", "MCP config files"),
            ]

            for path_pattern, description in locations:
                if '*' in str(path_pattern):
                    parent = path_pattern.parent
                    pattern = path_pattern.name
                    if parent.exists():
                        for path in parent.glob(pattern):
                            self.remove_item(path, f"{description} - {path.name}")
                else:
                    self.remove_item(path_pattern, description)

        if remove_serena:
            self.log("Removing Serena MCP files...")
            serena_locations = [
                (Path.cwd() / ".serena", "Serena project directory"),
                (self.home / ".serena", "Serena user directory"),
            ]

            for path, description in serena_locations:
                self.remove_item(path, description)

    def clean_npm_cache(self):
        """Clean npm cache to ensure complete removal"""
        try:
            if self.dry_run:
                self.log("[DRY RUN] Would clean npm cache")
                return True

            self.log("Cleaning npm cache...")
            subprocess.run(["npm", "cache", "clean", "--force"],
                         capture_output=True, text=True)
            self.log("npm cache cleaned")
            return True
        except Exception as e:
            self.log(f"Failed to clean npm cache: {e}", "WARNING")
            return False

    def print_summary(self):
        """Print summary of operations"""
        print("\n" + "="*60)
        print("UNINSTALL SUMMARY")
        print("="*60)

        if self.dry_run:
            print("\n[DRY RUN MODE - No actual changes made]")

        if self.removed_items:
            print(f"\n✅ Successfully removed {len(self.removed_items)} items:")
            for item in self.removed_items[:10]:  # Show first 10
                print(f"   - {item}")
            if len(self.removed_items) > 10:
                print(f"   ... and {len(self.removed_items) - 10} more")

        if self.failed_items:
            print(f"\n❌ Failed to remove {len(self.failed_items)} items:")
            for path, error in self.failed_items:
                print(f"   - {path}: {error}")

        print("\n" + "="*60)

    def run(self, remove_serena=True, remove_all_mcp=False, skip_npm=False):
        """Run the complete uninstallation"""
        print("="*60)
        print("Claude Code Complete Uninstaller")
        print("="*60)

        if self.dry_run:
            print("\n🔍 DRY RUN MODE - Checking what would be removed...\n")
        else:
            print("\n🧹 Starting complete uninstallation...\n")

        # Step 1: Uninstall npm package
        if not skip_npm:
            self.uninstall_npm_package()

        # Step 2: Remove all Claude files
        self.remove_claude_files()

        # Step 3: Remove MCP servers if requested
        self.remove_mcp_servers(remove_serena, remove_all_mcp)

        # Step 4: Clean npm cache
        if not skip_npm:
            self.clean_npm_cache()

        # Print summary
        self.print_summary()

        if not self.dry_run:
            print("\n✨ Claude Code has been completely uninstalled!")
            print("\nTo reinstall fresh:")
            print("  npm install -g @anthropic/claude-cli")
            print("  claude")

def main():
    parser = argparse.ArgumentParser(description="Complete Claude Code Uninstaller")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be removed without actually removing")
    parser.add_argument("--remove-serena", action="store_true", default=True,
                       help="Also remove Serena MCP (default: True)")
    parser.add_argument("--remove-all-mcp", action="store_true",
                       help="Remove ALL MCP server configurations")
    parser.add_argument("--skip-npm", action="store_true",
                       help="Skip npm uninstall (if already done manually)")
    parser.add_argument("--quiet", action="store_true",
                       help="Minimal output")

    args = parser.parse_args()

    # Safety prompt unless dry-run
    if not args.dry_run:
        print("\n⚠️  WARNING: This will completely remove Claude Code and all its data!")
        print("This includes:")
        print("  - Claude CLI installation")
        print("  - All user settings and history")
        print("  - All cache and temporary files")
        if args.remove_serena or args.remove_all_mcp:
            print("  - MCP server configurations")

        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("Uninstallation cancelled.")
            sys.exit(0)

    uninstaller = ClaudeUninstaller(verbose=not args.quiet, dry_run=args.dry_run)
    uninstaller.run(
        remove_serena=args.remove_serena,
        remove_all_mcp=args.remove_all_mcp,
        skip_npm=args.skip_npm
    )

if __name__ == "__main__":
    main()
