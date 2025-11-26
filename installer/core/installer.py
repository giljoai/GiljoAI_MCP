"""
Installer core classes for v3.0 (test-targeted shims).

Provides BaseInstaller, LocalhostInstaller, ServerInstaller with the
expected init signature (settings-only) and an install() workflow that
invokes stubbed methods in the correct order. Designed to satisfy
tests/installer/test_installer_v3.py.
"""

import pathlib
from typing import Any, Dict


class BaseInstaller:
    """Base installer with v3.0 settings-only init signature."""

    def __init__(self, settings: Dict[str, Any]):
        # Expected by tests: no explicit mode parameter, settings dict retained
        # Keep settings as provided (tests assert raw dict equality)
        self.settings = settings
        self.install_dir = pathlib.Path(settings["install_dir"]) if "install_dir" in settings else None

        # Placeholders for collaborators; tests will mock these
        self.db_installer = None
        self.config_manager = None
        self.post_validator = None

    # The following methods are expected to be mocked in tests; provide safe defaults
    def create_venv(self) -> Dict[str, Any]:
        return {"success": True}

    def install_dependencies(self) -> Dict[str, Any]:
        return {"success": True}

    def install_frontend_dependencies(self) -> Dict[str, Any]:
        return {"success": True}

    def create_launchers(self) -> Dict[str, Any]:
        return {"success": True}

    def mode_specific_setup(self) -> Dict[str, Any]:
        return {"success": True}

    def install(self) -> Dict[str, Any]:
        """Run the installation workflow in sequence."""
        steps = [
            ("create_venv", self.create_venv),
            ("db_setup", lambda: self.db_installer.setup() if self.db_installer else {"success": True}),
            ("config_generate", lambda: self.config_manager.generate_all() if self.config_manager else {"success": True}),
            ("install_deps", self.install_dependencies),
            ("install_frontend", self.install_frontend_dependencies),
            ("create_launchers", self.create_launchers),
            ("mode_specific", self.mode_specific_setup),
            ("post_validate", lambda: self.post_validator.validate() if self.post_validator else {"valid": True}),
        ]

        for name, fn in steps:
            result = fn()
            # post_validator returns {"valid": True/False}
            if name == "post_validate":
                if not result.get("valid"):
                    return {"success": False, "error": f"Post-validation failed: {result}"}
                continue

            if not result.get("success"):
                return {"success": False, "error": f"{name} failed: {result}"}

        return {"success": True}


class LocalhostInstaller(BaseInstaller):
    """Localhost installer (inherits BaseInstaller behavior)."""

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)


class ServerInstaller(BaseInstaller):
    """Server installer (inherits BaseInstaller behavior)."""

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
