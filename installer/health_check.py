"""
Health Check System for GiljoAI MCP Installation
Provides unified health checks for all services
"""

import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ServiceHealth:
    """Health status for a service"""
    name: str
    healthy: bool
    message: str
    details: Optional[Dict] = None


class HealthCheckSystem:
    """Unified health check for all GiljoAI services"""
    
    def __init__(self, config: Dict):
        """Initialize with configuration from GUI"""
        self.config = config
        self.profile = config.get('profile', 'developer')
        
    def check_port_availability(self, port: int, host: str = 'localhost') -> bool:
        """Check if a port is available for use"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return False
    
    def check_postgresql_health(self) -> ServiceHealth:
        """Check PostgreSQL installation and connection"""
        if self.config.get('db_type') != 'postgresql':
            return ServiceHealth(
                name="PostgreSQL",
                healthy=True,
                message="Not configured (using SQLite)"
            )
        
        try:
            from installer.dependencies.postgresql import PostgreSQLInstaller, PostgreSQLConfig
            
            pg_config = PostgreSQLConfig(
                port=int(self.config.get('pg_port', 5432)),
                data_dir="C:/PostgreSQL/16/data",
                install_dir="C:/PostgreSQL/16"
            )
            
            installer = PostgreSQLInstaller(pg_config)
            
            # Check if installed
            if not installer.is_postgresql_installed():
                return ServiceHealth(
                    name="PostgreSQL",
                    healthy=False,
                    message="PostgreSQL not installed"
                )
            
            # Test connection
            if installer.test_connection():
                return ServiceHealth(
                    name="PostgreSQL",
                    healthy=True,
                    message="PostgreSQL running and accessible",
                    details={
                        'port': pg_config.port,
                        'version': '16.0',
                        'data_dir': str(pg_config.data_dir)
                    }
                )
            else:
                return ServiceHealth(
                    name="PostgreSQL",
                    healthy=False,
                    message="PostgreSQL installed but not accessible"
                )
                
        except Exception as e:
            return ServiceHealth(
                name="PostgreSQL",
                healthy=False,
                message=f"Health check failed: {str(e)}"
            )
    
    def check_redis_health(self) -> ServiceHealth:
        """Check Redis installation and connection"""
        # Only check Redis for network profiles
        if self.profile not in ['team', 'enterprise']:
            return ServiceHealth(
                name="Redis",
                healthy=True,
                message="Not required for this profile"
            )
        
        try:
            # Check if Redis port is in use (indicates it's running)
            redis_port = int(self.config.get('redis_port', 6379))
            
            if not self.check_port_availability(redis_port):
                # Port is in use, likely Redis is running
                return ServiceHealth(
                    name="Redis",
                    healthy=True,
                    message="Redis appears to be running",
                    details={'port': redis_port}
                )
            else:
                return ServiceHealth(
                    name="Redis",
                    healthy=False,
                    message="Redis not running or not installed"
                )
                
        except Exception as e:
            return ServiceHealth(
                name="Redis",
                healthy=False,
                message=f"Health check failed: {str(e)}"
            )
    
    def check_port_conflicts(self) -> ServiceHealth:
        """Check for port conflicts across all services"""
        required_ports = {
            'API': int(self.config.get('api_port', 8000)),
            'WebSocket': int(self.config.get('websocket_port', 8001)),
            'Dashboard': int(self.config.get('dashboard_port', 3000)),
            'MCP': int(self.config.get('mcp_port', 3001))
        }
        
        if self.config.get('db_type') == 'postgresql':
            required_ports['PostgreSQL'] = int(self.config.get('pg_port', 5432))
        
        if self.profile in ['team', 'enterprise']:
            required_ports['Redis'] = int(self.config.get('redis_port', 6379))
        
        conflicts = []
        available_ports = {}
        
        for service, port in required_ports.items():
            if service in ['PostgreSQL', 'Redis']:
                # These should be in use
                if self.check_port_availability(port):
                    conflicts.append(f"{service} port {port} not in use (service may not be running)")
            else:
                # These should be available
                if not self.check_port_availability(port):
                    conflicts.append(f"{service} port {port} already in use")
                else:
                    available_ports[service] = port
        
        if conflicts:
            return ServiceHealth(
                name="Port Configuration",
                healthy=False,
                message="Port conflicts detected",
                details={'conflicts': conflicts}
            )
        else:
            return ServiceHealth(
                name="Port Configuration",
                healthy=True,
                message="All ports configured correctly",
                details={'ports': required_ports}
            )
    
    def check_file_system(self) -> ServiceHealth:
        """Check required directories and files"""
        required_paths = []
        
        # Check config files
        config_files = [
            Path('.env'),
            Path('config.yaml')
        ]
        
        # Check data directory for SQLite
        if self.config.get('db_type') == 'sqlite':
            db_path = Path(self.config.get('db_path', 'data/giljo_mcp.db'))
            required_paths.append(db_path.parent)
        
        missing = []
        for path in config_files:
            if not path.exists():
                missing.append(str(path))
        
        for path in required_paths:
            if not path.exists():
                missing.append(str(path))
        
        if missing:
            return ServiceHealth(
                name="File System",
                healthy=False,
                message="Missing required files/directories",
                details={'missing': missing}
            )
        else:
            return ServiceHealth(
                name="File System",
                healthy=True,
                message="All required files and directories present"
            )
    
    def run_all_checks(self) -> List[ServiceHealth]:
        """Run all health checks and return results"""
        checks = [
            self.check_postgresql_health(),
            self.check_redis_health(),
            self.check_port_conflicts(),
            self.check_file_system()
        ]
        
        return checks
    
    def get_summary(self) -> Tuple[bool, str]:
        """Get overall health summary"""
        results = self.run_all_checks()
        
        all_healthy = all(r.healthy for r in results)
        failed = [r.name for r in results if not r.healthy]
        
        if all_healthy:
            return True, "All systems operational"
        else:
            return False, f"Issues detected: {', '.join(failed)}"


# Integration function for GUI
def run_health_checks_for_gui(config: Dict, progress_callback=None) -> Dict:
    """Run health checks with GUI progress callback"""
    health_system = HealthCheckSystem(config)
    
    if progress_callback:
        progress_callback("Starting health checks...", 0)
    
    results = []
    checks = [
        ("PostgreSQL", health_system.check_postgresql_health),
        ("Redis", health_system.check_redis_health),
        ("Ports", health_system.check_port_conflicts),
        ("File System", health_system.check_file_system)
    ]
    
    for i, (name, check_func) in enumerate(checks):
        if progress_callback:
            progress_callback(f"Checking {name}...", int((i / len(checks)) * 100))
        
        result = check_func()
        results.append(result)
        
        time.sleep(0.2)  # Small delay for UI updates
    
    if progress_callback:
        progress_callback("Health checks complete", 100)
    
    all_healthy, summary = health_system.get_summary()
    
    return {
        'healthy': all_healthy,
        'summary': summary,
        'details': [
            {
                'name': r.name,
                'healthy': r.healthy,
                'message': r.message,
                'details': r.details
            }
            for r in results
        ]
    }