# \!/usr/bin/env python3
"""
GiljoAI MCP - Unified Cross-Platform Deployment Script
Detects platform and executes appropriate installation steps
"""

import platform
import shutil
import sys
from pathlib import Path
from typing import Dict


class Colors:
    @staticmethod
    def green(text):
        return f"\x1b[0;32m{text}\x1b[0m"

    @staticmethod
    def red(text):
        return f"\x1b[0;31m{text}\x1b[0m"

    @staticmethod
    def yellow(text):
        return f"\x1b[1;33m{text}\x1b[0m"

    @staticmethod
    def cyan(text):
        return f"\x1b[0;36m{text}\x1b[0m"


class PlatformDetector:
    @staticmethod
    def detect() -> Dict[str, str]:
        system = platform.system()
        info = {"system": system, "python": platform.python_version()}
        if system == "Windows":
            info["platform"] = "windows"
            info["script"] = "install_dependencies_windows.ps1"
        elif system == "Linux":
            info["platform"] = "linux"
            info["script"] = "install_dependencies_linux.sh"
        elif system == "Darwin":
            info["platform"] = "macos"
            info["script"] = "install_dependencies_macos.sh"
        return info


class DependencyChecker:
    @staticmethod
    def check_command(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    @staticmethod
    def check_all() -> Dict[str, bool]:
        return {
            "postgresql": DependencyChecker.check_command("psql"),
            "python": sys.version_info >= (3, 11),
            "nodejs": DependencyChecker.check_command("node"),
            "npm": DependencyChecker.check_command("npm"),
        }


class Deployer:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.platform_info = PlatformDetector.detect()

    def deploy(self):
        print("=" * 60)
        print(Colors.cyan("  GiljoAI MCP - Cross-Platform Deployment"))
        print("=" * 60)
        print()
        print(Colors.green(f"Platform: {self.platform_info['system']}"))
        print(Colors.green(f"Python: {self.platform_info['python']}"))
        print()

        deps = DependencyChecker.check_all()
        print(Colors.green("Dependencies:"))
        for name, installed in deps.items():
            status = Colors.green("[OK]") if installed else Colors.yellow("[MISSING]")
            print(f"  {status} {name}")
        print()

        if not all(deps.values()):
            print(Colors.yellow("Run platform-specific installer:"))
            if self.platform_info["platform"] == "windows":
                print(rf"  powershell .\scripts\{self.platform_info['script']}")
            else:
                print(f"  bash scripts/{self.platform_info['script']}")
            print()

        print("To complete installation, run:")
        print("  python installer/cli/install.py")
        print()


def main():
    deployer = Deployer()
    deployer.deploy()


if __name__ == "__main__":
    main()
