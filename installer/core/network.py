"""
Network configuration for GiljoAI MCP server mode
Handles SSL/TLS setup, network binding, and port management
"""

import os
import socket
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta


class NetworkManager:
    """Manage network configuration and SSL/TLS setup for server mode"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.mode = settings.get('mode', 'localhost')
        self.logger = logging.getLogger(self.__class__.__name__)

        # Network settings
        self.bind_address = settings.get('bind', '127.0.0.1' if self.mode == 'localhost' else '0.0.0.0')
        self.ports = {
            'api': settings.get('api_port', 8000),
            'websocket': settings.get('ws_port', 8001),
            'dashboard': settings.get('dashboard_port', 3000)
        }

        # SSL settings
        self.ssl_enabled = settings.get('features', {}).get('ssl', False)
        self.cert_dir = Path('certs')

    def configure(self) -> Dict[str, Any]:
        """Main network configuration workflow"""
        result = {'success': False, 'errors': [], 'warnings': []}

        try:
            # Step 1: Validate network binding
            self.logger.info("Validating network configuration...")
            binding_result = self.validate_network_binding()
            if not binding_result['success']:
                result['errors'].extend(binding_result.get('errors', []))
                return result

            result['warnings'].extend(binding_result.get('warnings', []))

            # Step 2: Check port availability
            self.logger.info("Checking port availability...")
            port_result = self.check_port_availability()
            if not port_result['success']:
                result['errors'].extend(port_result.get('errors', []))
                return result

            # Step 3: Setup SSL if enabled
            if self.ssl_enabled:
                self.logger.info("Configuring SSL/TLS...")
                ssl_result = self.setup_ssl()
                if not ssl_result['success']:
                    result['errors'].extend(ssl_result.get('errors', []))
                    return result

                result['ssl_cert'] = ssl_result.get('cert_path')
                result['ssl_key'] = ssl_result.get('key_path')
            else:
                # Warning about missing SSL in server mode
                if self.mode == 'server':
                    result['warnings'].append(
                        "SSL/TLS is disabled - NOT recommended for production use!"
                    )

            result['success'] = True
            result['bind_address'] = self.bind_address
            result['ports'] = self.ports

            self.logger.info("Network configuration completed successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Network configuration failed: {e}")
            return result

    def validate_network_binding(self) -> Dict[str, Any]:
        """Validate network binding configuration and warn about exposure"""
        result = {'success': False, 'errors': [], 'warnings': []}

        try:
            # Check if binding to network interface (not localhost)
            is_network_exposed = self.bind_address not in ['127.0.0.1', 'localhost']

            if is_network_exposed:
                # CRITICAL WARNING for network exposure
                result['warnings'].append(
                    f"WARNING: Server will be accessible over network at {self.bind_address}"
                )
                result['warnings'].append(
                    "SECURITY: Ensure firewall rules are properly configured"
                )

                if not self.ssl_enabled:
                    result['warnings'].append(
                        "CRITICAL: Network exposure WITHOUT SSL is a security risk!"
                    )

            # Validate bind address format
            if self.bind_address != '0.0.0.0':
                try:
                    socket.inet_aton(self.bind_address)
                except socket.error:
                    result['errors'].append(
                        f"Invalid bind address: {self.bind_address}"
                    )
                    return result

            result['success'] = True
            result['network_exposed'] = is_network_exposed
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Network binding validation failed: {e}")
            return result

    def check_port_availability(self) -> Dict[str, Any]:
        """Check if required ports are available"""
        result = {'success': False, 'errors': [], 'in_use': []}

        try:
            for service, port in self.ports.items():
                if not self._is_port_available(port):
                    result['in_use'].append({
                        'service': service,
                        'port': port
                    })
                    result['errors'].append(
                        f"Port {port} ({service}) is already in use"
                    )

            if not result['errors']:
                result['success'] = True
                self.logger.info("All required ports are available")

            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Port availability check failed: {e}")
            return result

    def _is_port_available(self, port: int) -> bool:
        """Check if a specific port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.bind_address, port))
                return True
        except OSError:
            return False

    def setup_ssl(self) -> Dict[str, Any]:
        """Configure SSL/TLS certificates"""
        result = {'success': False, 'errors': []}

        try:
            # Create certs directory if it doesn't exist
            self.cert_dir.mkdir(exist_ok=True)

            ssl_config = self.settings.get('ssl', {})
            ssl_type = ssl_config.get('type', 'self-signed')

            if ssl_type == 'self-signed':
                # Generate self-signed certificate
                cert_result = self.generate_self_signed_cert()
                if not cert_result['success']:
                    result['errors'].extend(cert_result.get('errors', []))
                    return result

                result['cert_path'] = cert_result['cert_path']
                result['key_path'] = cert_result['key_path']
                result['self_signed'] = True

                self.logger.info("Self-signed SSL certificate generated")

            elif ssl_type == 'existing':
                # Use existing certificates
                cert_path = ssl_config.get('cert_path')
                key_path = ssl_config.get('key_path')

                if not cert_path or not key_path:
                    result['errors'].append("SSL certificate and key paths must be provided")
                    return result

                cert_file = Path(cert_path)
                key_file = Path(key_path)

                if not cert_file.exists():
                    result['errors'].append(f"SSL certificate not found: {cert_path}")
                    return result

                if not key_file.exists():
                    result['errors'].append(f"SSL key not found: {key_path}")
                    return result

                result['cert_path'] = str(cert_file.absolute())
                result['key_path'] = str(key_file.absolute())
                result['self_signed'] = False

                self.logger.info("Using existing SSL certificates")

            else:
                result['errors'].append(f"Unknown SSL type: {ssl_type}")
                return result

            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"SSL setup failed: {e}")
            return result

    def generate_self_signed_cert(self) -> Dict[str, Any]:
        """Generate self-signed SSL certificate using cryptography library"""
        result = {'success': False, 'errors': []}

        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            # Generate private key
            self.logger.info("Generating 2048-bit RSA private key...")
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Get hostname for certificate
            hostname = self.settings.get('hostname', socket.gethostname())

            # Create certificate subject and issuer
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GiljoAI MCP"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])

            # Generate certificate
            self.logger.info("Generating self-signed certificate...")
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(hostname),
                    x509.DNSName('localhost'),
                    x509.DNSName('*.localhost'),
                    x509.IPAddress(socket.inet_aton('127.0.0.1')),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())

            # Save certificate
            cert_path = self.cert_dir / "server.crt"
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            # Save private key
            key_path = self.cert_dir / "server.key"
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Set restrictive permissions on Unix systems
            if platform.system() != "Windows":
                os.chmod(key_path, 0o600)
                os.chmod(cert_path, 0o644)

            result['success'] = True
            result['cert_path'] = str(cert_path.absolute())
            result['key_path'] = str(key_path.absolute())
            result['hostname'] = hostname
            result['valid_days'] = 365

            self.logger.info(f"SSL certificate created: {cert_path}")
            self.logger.info(f"SSL private key created: {key_path}")

            return result

        except ImportError as e:
            result['errors'].append(
                "cryptography library not installed. Install with: pip install cryptography"
            )
            self.logger.error("cryptography library not available")
            return result
        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Certificate generation failed: {e}")
            return result

    def get_network_info(self) -> Dict[str, Any]:
        """Get current network configuration information"""
        info = {
            'mode': self.mode,
            'bind_address': self.bind_address,
            'ports': self.ports,
            'ssl_enabled': self.ssl_enabled,
            'network_exposed': self.bind_address not in ['127.0.0.1', 'localhost'],
            'hostname': socket.gethostname(),
            'platform': platform.system()
        }

        # Add local IP addresses
        try:
            hostname = socket.gethostname()
            info['local_ips'] = socket.gethostbyname_ex(hostname)[2]
        except Exception:
            info['local_ips'] = []

        return info

    def print_network_warning(self) -> str:
        """Generate formatted network security warning"""
        if self.bind_address in ['127.0.0.1', 'localhost']:
            return ""

        warning = "\n" + "=" * 70 + "\n"
        warning += "  NETWORK SECURITY WARNING\n"
        warning += "=" * 70 + "\n\n"
        warning += f"  Server will be accessible over the network at: {self.bind_address}\n\n"

        if not self.ssl_enabled:
            warning += "  CRITICAL: SSL/TLS is DISABLED!\n"
            warning += "  - All traffic will be unencrypted\n"
            warning += "  - Passwords and API keys will be transmitted in plaintext\n"
            warning += "  - NOT RECOMMENDED for production use\n\n"
        else:
            warning += "  SSL/TLS is ENABLED (recommended)\n"
            warning += "  - Traffic will be encrypted\n\n"

        warning += "  Security Recommendations:\n"
        warning += "  1. Configure firewall rules (see firewall_rules.txt)\n"
        warning += "  2. Use strong passwords for admin users\n"
        warning += "  3. Enable API key authentication\n"
        warning += "  4. Consider using a reverse proxy (nginx/Apache)\n"
        warning += "  5. Keep SSL certificates up to date\n\n"
        warning += "=" * 70 + "\n"

        return warning


class PortScanner:
    """Utility for scanning and managing port availability"""

    @staticmethod
    def scan_port_range(start_port: int, end_port: int, host: str = '127.0.0.1') -> Dict[int, bool]:
        """Scan a range of ports for availability"""
        results = {}
        for port in range(start_port, end_port + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((host, port))
                    results[port] = True  # Available
            except OSError:
                results[port] = False  # In use
        return results

    @staticmethod
    def find_available_port(preferred_port: int, host: str = '127.0.0.1') -> Optional[int]:
        """Find an available port, starting with the preferred port"""
        if PortScanner._check_port(preferred_port, host):
            return preferred_port

        # Try nearby ports
        for offset in range(1, 100):
            for port in [preferred_port + offset, preferred_port - offset]:
                if 1024 <= port <= 65535:
                    if PortScanner._check_port(port, host):
                        return port
        return None

    @staticmethod
    def _check_port(port: int, host: str) -> bool:
        """Check if a specific port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return True
        except OSError:
            return False


def detect_network_conflicts() -> Dict[str, Any]:
    """Detect common network configuration conflicts"""
    conflicts = {
        'has_conflicts': False,
        'issues': [],
        'recommendations': []
    }

    # Check common port conflicts
    common_ports = {
        8000: ['Django dev server', 'Alternative HTTP'],
        8001: ['Alternative HTTP', 'WebSocket servers'],
        3000: ['React dev server', 'Node.js apps'],
        5432: ['PostgreSQL']
    }

    for port, services in common_ports.items():
        if not PortScanner._check_port(port, '127.0.0.1'):
            conflicts['has_conflicts'] = True
            conflicts['issues'].append(
                f"Port {port} is in use (commonly used by: {', '.join(services)})"
            )
            # Find alternative
            alt_port = PortScanner.find_available_port(port)
            if alt_port:
                conflicts['recommendations'].append(
                    f"Use port {alt_port} instead of {port}"
                )

    return conflicts
