"""
Windows Service Wrapper for GiljoAI MCP

This module provides a Windows service wrapper using pywin32 to run
GiljoAI MCP components as proper Windows services.
"""

import sys
import os
import time
import logging
import json
import subprocess
from pathlib import Path

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    print("pywin32 not available. Install with: pip install pywin32")
    sys.exit(1)


class GiljoServiceBase(win32serviceutil.ServiceFramework):
    """Base class for GiljoAI Windows services."""
    
    def __init__(self, args):
        """Initialize the service."""
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.logger = self._setup_logging()
        self.process = None
        self.running = False
    
    def _setup_logging(self):
        """Setup logging for the service."""
        log_dir = Path.home() / ".giljo_mcp" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger = logging.getLogger(self._svc_name_)
        logger.setLevel(logging.DEBUG)
        
        handler = logging.FileHandler(log_dir / f"{self._svc_name_}.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def SvcStop(self):
        """Stop the service."""
        self.logger.info(f"Stopping {self._svc_display_name_}")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping process: {e}")
    
    def SvcDoRun(self):
        """Run the service."""
        self.logger.info(f"Starting {self._svc_display_name_}")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.running = True
        self.main()
    
    def main(self):
        """Main service loop - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement main()")


class GiljoPostgreSQLService(GiljoServiceBase):
    """Windows service for PostgreSQL."""
    
    _svc_name_ = "GiljoPostgreSQL"
    _svc_display_name_ = "GiljoAI PostgreSQL Service"
    _svc_description_ = "PostgreSQL database service for GiljoAI MCP"
    
    def main(self):
        """Run PostgreSQL service."""
        base_path = Path.home() / ".giljo_mcp"
        data_dir = base_path / "data" / "postgresql"
        
        # Find PostgreSQL installation
        pg_paths = [
            Path("C:/Program Files/PostgreSQL/15/bin/pg_ctl.exe"),
            Path("C:/Program Files/PostgreSQL/14/bin/pg_ctl.exe"),
            Path("C:/Program Files/PostgreSQL/13/bin/pg_ctl.exe"),
        ]
        
        pg_ctl = None
        for path in pg_paths:
            if path.exists():
                pg_ctl = path
                break
        
        if not pg_ctl:
            self.logger.error("PostgreSQL installation not found")
            return
        
        try:
            # Start PostgreSQL
            cmd = [
                str(pg_ctl),
                "start",
                "-D", str(data_dir),
                "-l", str(base_path / "logs" / "postgresql.log"),
                "-w"
            ]
            
            env = os.environ.copy()
            env["PGDATA"] = str(data_dir)
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(data_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.logger.info("PostgreSQL started successfully")
            
            # Wait for stop signal
            while self.running:
                if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                    break
            
            # Stop PostgreSQL
            stop_cmd = [str(pg_ctl), "stop", "-D", str(data_dir), "-m", "fast"]
            subprocess.run(stop_cmd, env=env)
            
        except Exception as e:
            self.logger.error(f"Error running PostgreSQL: {e}")
            servicemanager.LogErrorMsg(f"PostgreSQL service error: {e}")


class GiljoRedisService(GiljoServiceBase):
    """Windows service for Redis."""
    
    _svc_name_ = "GiljoRedis"
    _svc_display_name_ = "GiljoAI Redis Service"
    _svc_description_ = "Redis cache service for GiljoAI MCP"
    
    def main(self):
        """Run Redis service."""
        base_path = Path.home() / ".giljo_mcp"
        config_file = base_path / "config" / "redis.conf"
        
        # Find Redis installation
        redis_paths = [
            Path("C:/Program Files/Redis/redis-server.exe"),
            Path("C:/Program Files (x86)/Redis/redis-server.exe"),
            Path(base_path / "redis" / "redis-server.exe"),
        ]
        
        redis_server = None
        for path in redis_paths:
            if path.exists():
                redis_server = path
                break
        
        if not redis_server:
            self.logger.error("Redis installation not found")
            return
        
        try:
            # Start Redis
            cmd = [str(redis_server)]
            if config_file.exists():
                cmd.append(str(config_file))
            
            self.process = subprocess.Popen(
                cmd,
                cwd=str(base_path / "data" / "redis"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.logger.info("Redis started successfully")
            
            # Wait for stop signal
            while self.running:
                if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                    break
            
        except Exception as e:
            self.logger.error(f"Error running Redis: {e}")
            servicemanager.LogErrorMsg(f"Redis service error: {e}")


class GiljoApplicationService(GiljoServiceBase):
    """Windows service for GiljoAI application."""
    
    _svc_name_ = "GiljoApplication"
    _svc_display_name_ = "GiljoAI MCP Application"
    _svc_description_ = "Main application service for GiljoAI MCP"
    
    def main(self):
        """Run GiljoAI application service."""
        base_path = Path.home() / ".giljo_mcp"
        
        try:
            # Start GiljoAI application
            cmd = [
                sys.executable,
                "-m", "src.giljo_mcp.server"
            ]
            
            env = os.environ.copy()
            env.update({
                "GILJO_CONFIG_DIR": str(base_path / "config"),
                "GILJO_DATA_DIR": str(base_path / "data"),
                "GILJO_LOG_DIR": str(base_path / "logs")
            })
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(base_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.logger.info("GiljoAI application started successfully")
            
            # Wait for stop signal
            while self.running:
                if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                    break
            
        except Exception as e:
            self.logger.error(f"Error running GiljoAI application: {e}")
            servicemanager.LogErrorMsg(f"GiljoAI application service error: {e}")


class GiljoWorkerService(GiljoServiceBase):
    """Windows service for GiljoAI worker."""
    
    _svc_name_ = "GiljoWorker"
    _svc_display_name_ = "GiljoAI MCP Worker"
    _svc_description_ = "Background worker service for GiljoAI MCP"
    
    def main(self):
        """Run GiljoAI worker service."""
        base_path = Path.home() / ".giljo_mcp"
        
        try:
            # Start GiljoAI worker
            cmd = [
                sys.executable,
                "-m", "src.giljo_mcp.worker"
            ]
            
            env = os.environ.copy()
            env.update({
                "GILJO_CONFIG_DIR": str(base_path / "config"),
                "GILJO_DATA_DIR": str(base_path / "data"),
                "GILJO_LOG_DIR": str(base_path / "logs")
            })
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(base_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.logger.info("GiljoAI worker started successfully")
            
            # Wait for stop signal
            while self.running:
                if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                    break
            
        except Exception as e:
            self.logger.error(f"Error running GiljoAI worker: {e}")
            servicemanager.LogErrorMsg(f"GiljoAI worker service error: {e}")


def install_service(service_class, start_type=win32service.SERVICE_AUTO_START):
    """Install a Windows service."""
    try:
        win32serviceutil.InstallService(
            service_class._svc_reg_class_,
            service_class._svc_name_,
            service_class._svc_display_name_,
            description=service_class._svc_description_,
            startType=start_type
        )
        print(f"Service {service_class._svc_name_} installed successfully")
        return True
    except Exception as e:
        print(f"Failed to install service {service_class._svc_name_}: {e}")
        return False


def uninstall_service(service_class):
    """Uninstall a Windows service."""
    try:
        win32serviceutil.RemoveService(service_class._svc_name_)
        print(f"Service {service_class._svc_name_} uninstalled successfully")
        return True
    except Exception as e:
        print(f"Failed to uninstall service {service_class._svc_name_}: {e}")
        return False


def main():
    """Main function for service management."""
    services = [
        GiljoPostgreSQLService,
        GiljoRedisService,
        GiljoApplicationService,
        GiljoWorkerService
    ]
    
    if len(sys.argv) == 1:
        # Interactive mode
        print("GiljoAI Windows Service Manager")
        print("=" * 40)
        print("1. Install all services")
        print("2. Uninstall all services")
        print("3. Install specific service")
        print("4. Uninstall specific service")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            print("\nInstalling services...")
            for service_class in services:
                install_service(service_class)
        
        elif choice == "2":
            print("\nUninstalling services...")
            for service_class in reversed(services):
                uninstall_service(service_class)
        
        elif choice == "3":
            print("\nAvailable services:")
            for i, service_class in enumerate(services, 1):
                print(f"  {i}. {service_class._svc_name_}")
            
            try:
                idx = int(input("Enter service number: ")) - 1
                if 0 <= idx < len(services):
                    install_service(services[idx])
                else:
                    print("Invalid service number")
            except ValueError:
                print("Invalid input")
        
        elif choice == "4":
            print("\nAvailable services:")
            for i, service_class in enumerate(services, 1):
                print(f"  {i}. {service_class._svc_name_}")
            
            try:
                idx = int(input("Enter service number: ")) - 1
                if 0 <= idx < len(services):
                    uninstall_service(services[idx])
                else:
                    print("Invalid service number")
            except ValueError:
                print("Invalid input")
        
        elif choice == "0":
            sys.exit(0)
        else:
            print("Invalid choice")
    
    else:
        # Command line mode - let pywin32 handle it
        service_map = {
            "postgresql": GiljoPostgreSQLService,
            "redis": GiljoRedisService,
            "application": GiljoApplicationService,
            "worker": GiljoWorkerService
        }
        
        service_name = sys.argv[1].lower() if len(sys.argv) > 1 else None
        
        if service_name in service_map:
            win32serviceutil.HandleCommandLine(service_map[service_name])
        else:
            print(f"Available services: {', '.join(service_map.keys())}")
            print(f"Usage: python {sys.argv[0]} <service_name> [install|remove|start|stop]")


if __name__ == "__main__":
    main()