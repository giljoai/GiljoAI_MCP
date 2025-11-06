"""
Cross-platform network utilities for IP address detection.

This module provides network interface and IP address discovery across platforms,
with graceful fallback when optional dependencies (like psutil) are unavailable.
"""

import socket
import logging
from typing import List, Optional, Any


logger = logging.getLogger(__name__)


def get_network_ips(platform_handler: Optional[Any] = None) -> List[str]:
    """
    Get non-localhost IPv4 addresses from all network interfaces.

    Strategy:
    1. Try psutil for comprehensive interface scanning (preferred)
    2. Fall back to socket.gethostbyname() for single IP
    3. Use platform handler if provided
    4. Return empty list if all methods fail

    Args:
        platform_handler: Optional platform-specific handler

    Returns:
        List of IPv4 addresses (excluding 127.0.0.1 and loopback addresses)
    """
    ips = []

    # Strategy 1: Use psutil if available
    try:
        import psutil

        logger.debug("Using psutil for network IP detection")
        addresses = psutil.net_if_addrs()

        for interface_name, interface_addresses in addresses.items():
            for address in interface_addresses:
                # Filter for IPv4 (AF_INET) only
                if address.family == socket.AF_INET:
                    ip = address.address
                    # Exclude loopback addresses
                    if ip and ip != "127.0.0.1" and not ip.startswith("127."):
                        ips.append(ip)

        if ips:
            logger.info(f"Found {len(ips)} network IP(s) via psutil: {ips}")
            return ips

    except ImportError:
        logger.debug("psutil not available, trying fallback methods")
    except Exception as e:
        logger.warning(f"psutil IP detection failed: {e}")

    # Strategy 2: Use socket.gethostbyname() fallback
    try:
        logger.debug("Using socket.gethostbyname() fallback")
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        if ip and ip != "127.0.0.1" and not ip.startswith("127."):
            ips.append(ip)
            logger.info(f"Found network IP via socket: {ip}")
            return ips

    except Exception as e:
        logger.warning(f"socket IP detection failed: {e}")

    # Strategy 3: Use platform handler if available
    if platform_handler and hasattr(platform_handler, "get_network_ips"):
        try:
            logger.debug("Using platform handler for network IP detection")
            handler_ips = platform_handler.get_network_ips()
            if handler_ips:
                logger.info(f"Found {len(handler_ips)} IP(s) via platform handler")
                return handler_ips
        except Exception as e:
            logger.warning(f"Platform handler IP detection failed: {e}")

    # No IPs found
    logger.warning("No network IPs detected - all methods failed")
    return []


def get_primary_ip() -> Optional[str]:
    """
    Get the primary/preferred outbound IPv4 address.

    Uses a UDP socket trick to determine which interface would be used
    for external connections (doesn't actually send any data).

    Returns:
        Primary IPv4 address or None if detection fails
    """
    try:
        # Create a UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)

        # Connect to an external address (doesn't actually send data)
        # Using Google's public DNS as target
        s.connect(("8.8.8.8", 80))

        # Get the socket's own address
        ip = s.getsockname()[0]
        s.close()

        if ip and ip != "127.0.0.1":
            logger.info(f"Primary IP detected: {ip}")
            return ip

    except Exception as e:
        logger.debug(f"Primary IP detection failed: {e}")

    return None


def validate_ip_address(ip: str) -> bool:
    """
    Validate if a string is a valid IPv4 address.

    Args:
        ip: IP address string to validate

    Returns:
        True if valid IPv4 address, False otherwise
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """
    Check if a port is available for binding.

    Args:
        port: Port number to check
        host: Host address to bind to (default: all interfaces)

    Returns:
        True if port is available, False if in use
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()

        # Port is available if connection failed
        return result != 0

    except Exception as e:
        logger.warning(f"Port availability check failed for {host}:{port}: {e}")
        return False


def get_hostname() -> str:
    """
    Get the system hostname.

    Returns:
        Hostname string or 'localhost' if detection fails
    """
    try:
        return socket.gethostname()
    except Exception as e:
        logger.warning(f"Hostname detection failed: {e}")
        return "localhost"


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve a hostname to an IP address.

    Args:
        hostname: Hostname to resolve

    Returns:
        IPv4 address or None if resolution fails
    """
    try:
        return socket.gethostbyname(hostname)
    except Exception as e:
        logger.warning(f"Hostname resolution failed for {hostname}: {e}")
        return None
