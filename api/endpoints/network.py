"""
Network detection endpoint for LAN mode configuration.

This endpoint detects the server's network configuration including
IP addresses, hostname, and network availability for LAN deployment.
"""

import logging
import socket

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
