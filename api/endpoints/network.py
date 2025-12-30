"""
Network detection endpoint for LAN mode configuration.

This endpoint detects the server's network configuration including
IP addresses, hostname, and network availability for LAN deployment.
"""

import logging
import socket
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)
router = APIRouter()


class NetworkDetectionResponse(BaseModel):
    """Response model for network detection"""

    primary_ip: str = Field(..., description="Primary non-loopback IP address")
    hostname: str = Field(..., description="Server hostname")
    local_ips: list[str] = Field(..., description="All local IP addresses (excluding loopback)")
    platform: str = Field(..., description="Operating system platform")


class NetworkAdapter(BaseModel):
    """Network adapter information"""

    name: str = Field(..., description="User-readable adapter name")
    interface_id: str = Field(..., description="System interface identifier")
    ip_address: str = Field(..., description="IPv4 address")
    is_active: bool = Field(..., description="Whether adapter is currently active")
    is_virtual: bool = Field(..., description="Whether adapter is virtual (Docker, VM, etc.)")
    is_loopback: bool = Field(..., description="Whether adapter is loopback interface")


class NetworkAdaptersResponse(BaseModel):
    """Response model for network adapters detection"""

    adapters: list[NetworkAdapter] = Field(..., description="List of detected network adapters")
    recommended: Optional[NetworkAdapter] = Field(None, description="Recommended adapter for LAN binding")


@router.get("/detect-ip", response_model=NetworkDetectionResponse)
async def detect_ip():
    """
    Detect server network information for LAN mode configuration.

    Uses NetworkManager from installer.core.network to gather:
    - Primary IP address (first non-loopback)
    - Hostname
    - All local IP addresses (filtered to exclude 127.x.x.x)
    - Platform information

    Returns:
        NetworkDetectionResponse with detected network info

    Raises:
        HTTPException: If network detection fails
    """
    try:
        from installer.core.network import NetworkManager

        # Create NetworkManager with minimal settings
        settings = {
            "mode": "server",  # Use server mode for network detection
            "bind": "0.0.0.0",
        }

        network_manager = NetworkManager(settings)

        # Get network information
        network_info = network_manager.get_network_info()

        logger.debug(f"Network info from NetworkManager: {network_info}")

        # Get filtered local IPs (NetworkManager already filters out virtual adapters)
        local_ips = network_info.get("local_ips", [])

        # Select primary IP (first real network interface)
        # NetworkManager filters out virtual adapters (Docker, Hyper-V, WSL, etc.)
        # based on interface names, so the first IP should be the real network
        primary_ip = local_ips[0] if local_ips else "127.0.0.1"

        logger.debug(f"Detected IPs: {local_ips}, selected primary: {primary_ip}")

        # Get hostname
        hostname = network_info.get("hostname", socket.gethostname())

        # Get platform
        platform = network_info.get("platform", "Unknown")

        logger.info(f"Network detection successful: primary_ip={primary_ip}, hostname={hostname}, ips={len(local_ips)}")

        return NetworkDetectionResponse(
            primary_ip=primary_ip, hostname=hostname, local_ips=local_ips, platform=platform
        )

    except Exception as e:
        logger.error(f"Network detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect network configuration: {e}")


@router.get("/adapters", response_model=NetworkAdaptersResponse)
async def get_network_adapters():
    """
    Detect all network adapters for LAN mode configuration.

    Uses psutil to gather detailed information about network interfaces:
    - Adapter name and interface ID
    - IPv4 address (excluding loopback)
    - Active status
    - Virtual adapter detection (Docker, VMs, etc.)
    - Loopback detection

    Recommends the best adapter for LAN binding:
    - Prefers physical over virtual adapters
    - Prefers active adapters
    - Excludes loopback adapters
    - Selects fastest/most reliable adapter

    Returns:
        NetworkAdaptersResponse with list of adapters and recommendation

    Raises:
        HTTPException: If adapter detection fails
    """
    try:
        import platform

        import psutil

        adapters = []
        virtual_patterns = [
            "docker",
            "veth",
            "br-",
            "vmnet",
            "vboxnet",
            "virbr",
            "tun",
            "tap",
            "vEthernet",
            "Hyper-V",
            "WSL",
        ]
        loopback_patterns = ["lo", "Loopback"]

        logger.debug("Detecting network adapters using psutil")

        # Get all network interfaces with their addresses
        interfaces = psutil.net_if_addrs()
        interface_stats = psutil.net_if_stats()

        for interface_name, addresses in interfaces.items():
            # Check if interface is virtual
            is_virtual = any(pattern.lower() in interface_name.lower() for pattern in virtual_patterns)

            # Check if interface is loopback
            is_loopback = any(pattern.lower() in interface_name.lower() for pattern in loopback_patterns)

            # Get interface stats (speed, is_up)
            stats = interface_stats.get(interface_name)
            is_active = stats.isup if stats else False

            # Process each address on this interface
            for addr in addresses:
                # Only process IPv4 addresses (family 2 = AF_INET)
                if addr.family == 2:
                    ip = addr.address

                    # Skip loopback IPs (127.x.x.x)
                    if ip.startswith("127."):
                        logger.debug(f"Skipping loopback IP: {interface_name} -> {ip}")
                        continue

                    # Create adapter object
                    adapter = NetworkAdapter(
                        name=interface_name,
                        interface_id=interface_name,
                        ip_address=ip,
                        is_active=is_active,
                        is_virtual=is_virtual,
                        is_loopback=is_loopback,
                    )

                    adapters.append(adapter)
                    logger.debug(
                        f"Found adapter: {interface_name} -> {ip} "
                        f"(active={is_active}, virtual={is_virtual}, loopback={is_loopback})"
                    )

        # Select recommended adapter
        recommended = _select_recommended_adapter(adapters)

        if recommended:
            logger.info(f"Recommended adapter: {recommended.interface_id} ({recommended.ip_address})")
        else:
            logger.warning("No suitable adapter found for recommendation")

        logger.info(f"Detected {len(adapters)} network adapters")

        return NetworkAdaptersResponse(adapters=adapters, recommended=recommended)

    except ImportError:
        logger.error("psutil library not available")
        raise HTTPException(
            status_code=500,
            detail="Network adapter detection requires psutil library. Install with: pip install psutil",
        )
    except Exception as e:
        logger.error(f"Network adapter detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect network adapters: {e}")


def _select_recommended_adapter(adapters: list[NetworkAdapter]) -> Optional[NetworkAdapter]:
    """
    Select the best adapter for LAN binding.

    Selection criteria (in order of priority):
    1. Must be active (is_active=True)
    2. Must not be loopback (is_loopback=False)
    3. Prefer physical over virtual (is_virtual=False)
    4. Prefer first matching adapter (stable selection)

    Args:
        adapters: List of network adapters

    Returns:
        Recommended adapter or None if no suitable adapter found
    """
    if not adapters:
        return None

    # Filter: active, non-loopback adapters only
    candidates = [a for a in adapters if a.is_active and not a.is_loopback]

    if not candidates:
        logger.warning("No active, non-loopback adapters found")
        return None

    # Prefer physical adapters
    physical = [a for a in candidates if not a.is_virtual]
    if physical:
        return physical[0]  # Return first physical adapter

    # Fallback to virtual if no physical available
    return candidates[0]
