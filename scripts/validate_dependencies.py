#!/usr/bin/env python3
"""
GiljoAI MCP Dependency Validation Script
========================================

Validates that all required dependencies are properly installed and functioning.
Can be run independently to diagnose installation issues.

Usage:
    python validate_dependencies.py
    python validate_dependencies.py --verbose
    python validate_dependencies.py --fix
"""

import argparse
import importlib
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class DependencyValidator:
    """Validates GiljoAI MCP dependencies"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Critical dependencies that must be available
        self.critical_deps = {
            "aiohttp": "WebSocket client for real-time agent communication",
            "fastapi": "REST API server and WebSocket endpoints",
            "websockets": "WebSocket protocol implementation",
            "httpx": "HTTP client for external API calls",
            "sqlalchemy": "Database ORM with async support",
            "pydantic": "Data validation and settings management",
            "uvicorn": "ASGI server for running FastAPI",
        }

        # Important but not critical dependencies
        self.important_deps = {
            "aiosqlite": "SQLite async driver (for local development)",
            "asyncpg": "PostgreSQL async driver (for production)",
            "psycopg2": "PostgreSQL sync driver (backup)",
            "click": "CLI interface framework",
            "rich": "Rich terminal output",
            "pyyaml": "YAML configuration support",
            "python_dotenv": "Environment variable loading",
        }

        # AI integration dependencies
        self.ai_deps = {
            "openai": "OpenAI API integration",
            "anthropic": "Anthropic Claude integration",
            "tiktoken": "Token counting for optimization",
        }

        # Development dependencies
        self.dev_deps = {
            "pytest": "Testing framework",
            "pytest_asyncio": "Async test support",
            "black": "Code formatter",
            "ruff": "Fast linter",
            "mypy": "Type checking",
        }

    def print_status(self, message: str, status: str = "info"):
        """Print colored status message"""
        colors = {
            "success": "\033[92m✓\033[0m",
            "error": "\033[91m✗\033[0m",
            "warning": "\033[93m!\033[0m",
            "info": "\033[94mⓘ\033[0m",
        }
        icon = colors.get(status, "")
        print(f"{icon} {message}")

    def validate_python_version(self) -> bool:
        """Validate Python version meets requirements"""
        min_version = (3, 8)
        current = sys.version_info[:2]

        if current >= min_version:
            self.print_status(f"Python {current[0]}.{current[1]} OK", "success")
            return True
        self.print_status(
            f"Python {min_version[0]}.{min_version[1]}+ required (found {current[0]}.{current[1]})", "error"
        )
        self.errors.append(f"Python version {current[0]}.{current[1]} is too old")
        return False

    def check_dependency(self, dep_name: str, purpose: str) -> Tuple[bool, Optional[str]]:
        """Check if a dependency is available and get its version"""
        try:
            module = importlib.import_module(dep_name)
            version = getattr(module, "__version__", "unknown")
            return True, version
        except ImportError as e:
            return False, str(e)

    def validate_critical_dependencies(self) -> bool:
        """Validate critical dependencies"""
        self.print_status("Checking critical dependencies...", "info")
        all_ok = True

        for dep, purpose in self.critical_deps.items():
            success, version = self.check_dependency(dep, purpose)
            if success:
                if self.verbose:
                    self.print_status(f"{dep} {version} - {purpose}", "success")
                else:
                    self.print_status(f"{dep}", "success")
            else:
                self.print_status(f"{dep} - {purpose} (MISSING)", "error")
                self.errors.append(f"Critical dependency missing: {dep}")
                all_ok = False

        return all_ok

    def validate_important_dependencies(self) -> bool:
        """Validate important dependencies"""
        self.print_status("Checking important dependencies...", "info")
        missing_count = 0

        for dep, purpose in self.important_deps.items():
            success, version = self.check_dependency(dep, purpose)
            if success:
                if self.verbose:
                    self.print_status(f"{dep} {version} - {purpose}", "success")
                else:
                    self.print_status(f"{dep}", "success")
            else:
                self.print_status(f"{dep} - {purpose} (MISSING)", "warning")
                self.warnings.append(f"Important dependency missing: {dep}")
                missing_count += 1

        if missing_count > 0:
            self.print_status(f"{missing_count} important dependencies missing", "warning")

        return missing_count == 0

    def validate_ai_dependencies(self) -> bool:
        """Validate AI integration dependencies"""
        self.print_status("Checking AI integration dependencies...", "info")
        missing_count = 0

        for dep, purpose in self.ai_deps.items():
            success, version = self.check_dependency(dep, purpose)
            if success:
                if self.verbose:
                    self.print_status(f"{dep} {version} - {purpose}", "success")
                else:
                    self.print_status(f"{dep}", "success")
            else:
                self.print_status(f"{dep} - {purpose} (OPTIONAL)", "warning")
                missing_count += 1

        if missing_count > 0:
            self.print_status(f"{missing_count} AI dependencies missing (optional)", "info")

        return True  # AI deps are optional

    def validate_dev_dependencies(self) -> bool:
        """Validate development dependencies"""
        if not self.verbose:
            return True

        self.print_status("Checking development dependencies...", "info")
        missing_count = 0

        for dep, purpose in self.dev_deps.items():
            success, version = self.check_dependency(dep, purpose)
            if success:
                self.print_status(f"{dep} {version} - {purpose}", "success")
            else:
                self.print_status(f"{dep} - {purpose} (DEV ONLY)", "warning")
                missing_count += 1

        if missing_count > 0:
            self.print_status(f"{missing_count} development dependencies missing", "info")

        return True  # Dev deps are optional

    def test_websocket_functionality(self) -> bool:
        """Test WebSocket client functionality"""
        try:
            from src.giljo_mcp.websocket_client import WebSocketEventClient

            client = WebSocketEventClient()
            self.print_status("WebSocket client import successful", "success")
            return True
        except ImportError as e:
            self.print_status(f"WebSocket client import failed: {e}", "error")
            self.errors.append("WebSocket functionality not available")
            return False

    def test_api_functionality(self) -> bool:
        """Test API functionality"""
        try:
            from fastapi import FastAPI
            from pydantic import BaseModel

            app = FastAPI()
            self.print_status("FastAPI functionality available", "success")
            return True
        except ImportError as e:
            self.print_status(f"FastAPI functionality failed: {e}", "error")
            self.errors.append("API functionality not available")
            return False

    def test_database_functionality(self) -> bool:
        """Test database functionality"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.ext.asyncio import create_async_engine

            self.print_status("Database functionality available", "success")
            return True
        except ImportError as e:
            self.print_status(f"Database functionality failed: {e}", "error")
            self.errors.append("Database functionality not available")
            return False

    def check_requirements_file(self) -> bool:
        """Check if requirements.txt exists and is readable"""
        req_file = Path("requirements.txt")
        if req_file.exists():
            self.print_status("requirements.txt found", "success")
            try:
                with open(req_file) as f:
                    lines = f.readlines()
                self.print_status(f"requirements.txt contains {len(lines)} entries", "info")
                return True
            except Exception as e:
                self.print_status(f"requirements.txt read error: {e}", "error")
                return False
        else:
            self.print_status("requirements.txt not found", "error")
            self.errors.append("requirements.txt file missing")
            return False

    def suggest_fixes(self) -> None:
        """Suggest fixes for common issues"""
        if not self.errors and not self.warnings:
            return

        print("\n" + "=" * 60)
        print("🔧 SUGGESTED FIXES")
        print("=" * 60)

        if self.errors:
            print("\n❌ Critical Issues (must fix):")
            for error in self.errors:
                print(f"   • {error}")

            print("\n💡 Solutions:")
            print("   1. Install missing dependencies:")
            print("      pip install -r requirements.txt")
            print("\n   2. If specific packages fail:")
            print("      pip install aiohttp fastapi websockets httpx sqlalchemy pydantic")
            print("\n   3. For Windows users with build issues:")
            print("      pip install --only-binary=all aiohttp")

        if self.warnings:
            print("\n⚠️  Warnings (recommended to fix):")
            for warning in self.warnings:
                print(f"   • {warning}")

            print("\n💡 Optional fixes:")
            print("   pip install asyncpg psycopg2-binary")

    def run_validation(self, test_functionality: bool = True) -> bool:
        """Run complete validation"""
        print("🔍 GiljoAI MCP Dependency Validation")
        print("=" * 60)

        # Python version check
        python_ok = self.validate_python_version()

        # Requirements file check
        req_file_ok = self.check_requirements_file()

        # Dependency checks
        critical_ok = self.validate_critical_dependencies()
        important_ok = self.validate_important_dependencies()
        ai_ok = self.validate_ai_dependencies()
        dev_ok = self.validate_dev_dependencies()

        # Functionality tests
        if test_functionality and critical_ok:
            print("\n🧪 Testing functionality...")
            websocket_ok = self.test_websocket_functionality()
            api_ok = self.test_api_functionality()
            db_ok = self.test_database_functionality()
        else:
            websocket_ok = api_ok = db_ok = True

        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        total_checks = 7 if test_functionality else 4
        passed_checks = sum(
            [
                python_ok,
                req_file_ok,
                critical_ok,
                important_ok if not self.warnings else False,
                websocket_ok if test_functionality else True,
                api_ok if test_functionality else True,
                db_ok if test_functionality else True,
            ]
        )

        if not self.errors:
            self.print_status("✅ All critical dependencies validated successfully!", "success")
            if self.warnings:
                self.print_status(f"⚠️  {len(self.warnings)} warnings (see details above)", "warning")
        else:
            self.print_status(f"❌ {len(self.errors)} critical issues found", "error")

        print(f"\n📈 Score: {passed_checks}/{total_checks} checks passed")

        # Suggest fixes if needed
        if self.errors or self.warnings:
            self.suggest_fixes()

        return len(self.errors) == 0

    def fix_dependencies(self) -> bool:
        """Attempt to fix missing dependencies"""
        print("🔧 Attempting to fix missing dependencies...")

        try:
            # Install from requirements.txt
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                self.print_status("Dependencies installed successfully", "success")
                return True
            self.print_status(f"Installation failed: {result.stderr}", "error")
            return False

        except Exception as e:
            self.print_status(f"Fix attempt failed: {e}", "error")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate GiljoAI MCP dependencies")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--fix", "-f", action="store_true", help="Attempt to fix missing dependencies")
    parser.add_argument("--no-test", action="store_true", help="Skip functionality tests")

    args = parser.parse_args()

    validator = DependencyValidator(verbose=args.verbose)

    if args.fix:
        if validator.fix_dependencies():
            print("\n✅ Dependencies fixed. Re-running validation...\n")
        else:
            print("\n❌ Could not fix dependencies automatically.\n")

    success = validator.run_validation(test_functionality=not args.no_test)

    if success:
        print("\n🎉 All validations passed! GiljoAI MCP should work correctly.")
        return 0
    print("\n💥 Validation failed. Please fix the issues above before using GiljoAI MCP.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
