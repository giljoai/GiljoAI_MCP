#!/usr/bin/env python3
"""
start_giljo_enhanced.py - Universal launcher with validation and recovery
Phase 3 implementation with complete launch validation
"""

import sys
import os
import time
import click
import signal
import webbrowser
import requests
from pathlib import Path
from typing import Optional

# Add installer modules to path
sys.path.insert(0, str(Path(__file__).parent))

from installer.core.launch_validator import LaunchValidator
from installer.core.service_manager import ServiceManager
from installer.core.recovery import ErrorRecovery


class GiljoLauncher:
    """Enhanced launcher with validation and recovery"""

    def __init__(self):
        self.validator = LaunchValidator()
        self.manager = ServiceManager()
        self.recovery = ErrorRecovery()
        self.config = None
        self.start_time = None

    def launch(self) -> bool:
        """Main launch sequence"""
        self.print_banner()
        self.start_time = time.time()

        # Step 1: Validate installation
        if not self.validate_installation():
            return False

        click.echo("\n✅ Installation validated")

        # Step 2: Start services
        click.echo("\n🚀 Starting services...")
        if not self.manager.start_all():
            self.handle_startup_errors()
            return False

        click.echo("\n✅ All services running")

        # Step 3: Wait for services to be ready
        click.echo("\n⏳ Waiting for services to be ready...")
        if not self.wait_for_ready():
            click.echo("❌ Services failed to become ready")
            return False

        # Calculate startup time
        startup_time = time.time() - self.start_time
        click.echo(f"\n✅ Services ready (startup time: {startup_time:.1f}s)")

        # Step 4: Open browser
        self.open_dashboard()

        # Step 5: Display status
        self.print_status()

        # Step 6: Monitor services
        try:
            self.monitor_services()
        except KeyboardInterrupt:
            self.shutdown()

        return True

    def print_banner(self):
        """Display startup banner"""
        click.echo("""
╔══════════════════════════════════════════╗
║     GiljoAI MCP - Launch System         ║
║         Phase 3 Enhanced Edition         ║
╚══════════════════════════════════════════╝
""")

    def validate_installation(self) -> bool:
        """Validate installation with recovery"""
        if not self.validator.validate_all():
            return self.handle_validation_errors()

        return True

    def handle_validation_errors(self) -> bool:
        """Handle validation failures"""
        click.echo("\n❌ Installation validation failed!")
        click.echo("\nErrors found:")

        errors = self.validator.get_errors()
        for error in errors:
            click.echo(f"  • {error}")

        # Attempt recovery
        click.echo("\n🔧 Attempting automatic recovery...")

        if self.recovery.recover_all(errors):
            click.echo("\n✅ Recovery successful! Retrying validation...")

            # Clear previous errors and retry
            self.validator.errors.clear()
            if self.validator.validate_all():
                click.echo("\n✅ Validation passed after recovery!")
                return True

        click.echo("\n❌ Could not recover automatically")
        click.echo("\nSuggestions:")
        self.provide_recovery_suggestions(errors)
        return False

    def provide_recovery_suggestions(self, errors: list):
        """Provide helpful suggestions for manual recovery"""
        for error in errors:
            if "PostgreSQL" in error:
                click.echo("\n  PostgreSQL Issues:")
                click.echo("  • Ensure PostgreSQL 18 is installed")
                click.echo("  • Start PostgreSQL service manually")
                click.echo("  • Check POSTGRES_PASSWORD in .env")

            elif "Port" in error:
                click.echo("\n  Port Conflicts:")
                click.echo("  • Stop conflicting services")
                click.echo("  • Or change ports in config.yaml")

            elif "Missing" in error and "table" in error:
                click.echo("\n  Database Schema:")
                click.echo("  • Run the installer to create tables")
                click.echo("  • Check database migrations")

            elif "config" in error.lower():
                click.echo("\n  Configuration:")
                click.echo("  • Run installer to generate config files")
                click.echo("  • Check .env and config.yaml exist")

    def handle_startup_errors(self):
        """Handle service startup failures"""
        click.echo("\n❌ Service startup failed!")

        # Get service status
        status = self.manager.get_service_status()
        click.echo("\nService Status:")
        for service, is_running in status.items():
            status_icon = "✅" if is_running else "❌"
            click.echo(f"  {service}: {status_icon}")

        # Provide guidance
        click.echo("\nTroubleshooting:")
        click.echo("  • Check logs in the logs/ directory")
        click.echo("  • Ensure all dependencies are installed")
        click.echo("  • Run: pip install -r requirements.txt")

    def wait_for_ready(self, timeout: int = 30) -> bool:
        """Wait for services to be ready with health checks"""
        import yaml

        # Load config
        with open('config.yaml') as f:
            self.config = yaml.safe_load(f)

        services_to_check = []

        # API health check
        api_port = self.config['services'].get('api_port', 8000)
        protocol = 'https' if self.config.get('features', {}).get('ssl_enabled') else 'http'
        services_to_check.append(('API', f"{protocol}://localhost:{api_port}/health"))

        # Dashboard check
        dashboard_port = self.config['services'].get('dashboard_port', 3000)
        services_to_check.append(('Dashboard', f"{protocol}://localhost:{dashboard_port}"))

        start_time = time.time()
        all_ready = False

        with click.progressbar(length=timeout, label='Waiting for services') as bar:
            while time.time() - start_time < timeout:
                all_ready = True
                failed_services = []

                for name, url in services_to_check:
                    try:
                        # For SSL, disable cert verification for self-signed
                        verify = not self.config.get('features', {}).get('ssl_enabled', False)
                        response = requests.get(url, timeout=1, verify=verify)
                        if response.status_code not in [200, 404]:  # 404 ok for dashboard root
                            all_ready = False
                            failed_services.append(name)
                    except:
                        all_ready = False
                        failed_services.append(name)

                if all_ready:
                    bar.update(timeout)
                    break

                elapsed = int(time.time() - start_time)
                bar.update(elapsed - bar.pos)
                time.sleep(1)

        if not all_ready and failed_services:
            click.echo(f"\n⚠️  Services not ready: {', '.join(failed_services)}")

        return all_ready

    def open_dashboard(self):
        """Open dashboard in browser"""
        if not self.config:
            import yaml
            with open('config.yaml') as f:
                self.config = yaml.safe_load(f)

        if not self.config.get('features', {}).get('auto_start_browser', True):
            return

        mode = self.config['installation'].get('mode', 'localhost')
        dashboard_port = self.config['services'].get('dashboard_port', 3000)

        if mode == 'server' and self.config.get('features', {}).get('ssl_enabled'):
            bind_addr = self.config['services'].get('bind', '127.0.0.1')
            url = f"https://{bind_addr}:{dashboard_port}"
        else:
            url = f"http://localhost:{dashboard_port}"

        click.echo(f"\n🌐 Opening dashboard: {url}")
        try:
            webbrowser.open(url)
        except:
            click.echo("  ⚠️  Could not open browser automatically")

    def print_status(self):
        """Print running status"""
        if not self.config:
            import yaml
            with open('config.yaml') as f:
                self.config = yaml.safe_load(f)

        mode = self.config['installation'].get('mode', 'localhost')
        bind_addr = self.config['services'].get('bind', '127.0.0.1')
        ssl_enabled = self.config.get('features', {}).get('ssl_enabled', False)
        protocol = 'https' if ssl_enabled else 'http'

        # Service ports
        api_port = self.config['services'].get('api_port', 8000)
        ws_port = self.config['services'].get('websocket_port', 8001)
        dashboard_port = self.config['services'].get('dashboard_port', 3000)

        click.echo("\n" + "=" * 50)
        click.echo("   GiljoAI MCP is running!")
        click.echo("=" * 50)

        if mode == 'localhost':
            click.echo(f"   Dashboard: {protocol}://localhost:{dashboard_port}")
            click.echo(f"   API Docs: {protocol}://localhost:{api_port}/docs")
            click.echo(f"   WebSocket: {protocol.replace('http', 'ws')}://localhost:{ws_port}")
        else:
            click.echo(f"   Mode: SERVER (Network Accessible)")
            click.echo(f"   Binding: {bind_addr}")
            click.echo(f"   Dashboard: {protocol}://{bind_addr}:{dashboard_port}")
            click.echo(f"   API Docs: {protocol}://{bind_addr}:{api_port}/docs")
            click.echo(f"   WebSocket: {protocol.replace('http', 'ws')}://{bind_addr}:{ws_port}")

            if not ssl_enabled:
                click.echo("\n   ⚠️  WARNING: SSL is DISABLED - traffic is unencrypted!")

        # Performance stats
        if self.start_time:
            startup_time = time.time() - self.start_time
            click.echo(f"\n   Startup Time: {startup_time:.1f} seconds")

        # Service health
        status = self.manager.get_service_status()
        all_healthy = all(status.values())
        health_icon = "✅" if all_healthy else "⚠️"
        click.echo(f"   Health Status: {health_icon}")

        click.echo("\n   Press Ctrl+C to stop all services")
        click.echo("=" * 50)

    def monitor_services(self):
        """Monitor services and handle shutdown"""
        click.echo("\n👁️  Monitoring services (press Ctrl+C to stop)...")

        def restart_callback(service: str) -> bool:
            """Callback for service restart confirmation"""
            if click.confirm(f"\n  Restart {service}?", default=True):
                return True
            return False

        try:
            self.manager.monitor_services(callback=restart_callback)
        except KeyboardInterrupt:
            pass

    def shutdown(self):
        """Gracefully shutdown all services"""
        click.echo("\n\n🛑 Shutting down services...")
        self.manager.stop_all()
        click.echo("✅ All services stopped")

        # Display session stats
        if self.start_time:
            session_time = time.time() - self.start_time
            hours = int(session_time // 3600)
            minutes = int((session_time % 3600) // 60)
            seconds = int(session_time % 60)

            click.echo(f"\n📊 Session Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")

        click.echo("\nGoodbye! 👋")


def main():
    """Main entry point"""
    # Setup signal handlers
    def signal_handler(signum, frame):
        launcher.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run launcher
    launcher = GiljoLauncher()

    try:
        success = launcher.launch()
        sys.exit(0 if success else 1)
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}")
        import traceback
        if os.getenv('DEBUG'):
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
