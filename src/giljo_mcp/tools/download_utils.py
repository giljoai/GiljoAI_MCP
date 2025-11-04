"""
Download utility functions for MCP tools
Provides HTTP download and ZIP extraction capabilities.

Handover 0094: Token-Efficient MCP Downloads
"""

import io
import logging
import os
import zipfile
from pathlib import Path
from typing import Optional

import httpx


logger = logging.getLogger(__name__)


def get_server_url_from_config() -> str:
    """
    Get server URL from environment or default to localhost.

    Returns:
        Server URL (e.g., "http://localhost:7272")
    """
    # Check environment variable first
    server_url = os.environ.get("GILJO_SERVER_URL")
    if server_url:
        return server_url

    # Default to localhost
    return "http://localhost:7272"


async def download_file(url: str, api_key: str, timeout: int = 30) -> bytes:
    """
    Download file via HTTP with API key authentication.

    Args:
        url: Download URL
        api_key: API key for authentication
        timeout: Request timeout in seconds

    Returns:
        Downloaded file bytes

    Raises:
        Exception: If download fails

    Example:
        >>> content = await download_file(
        ...     url="http://localhost:7272/api/download/test.zip",
        ...     api_key="gk_user_key"
        ... )
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        headers = {"X-API-Key": api_key}
        
        logger.info(f"Downloading file from: {url}")
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        
        logger.info(f"Downloaded {len(response.content)} bytes")
        return response.content


def extract_zip_to_directory(zip_bytes: bytes, target_dir: Path) -> list[str]:
    """
    Extract ZIP file to target directory.

    Args:
        zip_bytes: ZIP file content as bytes
        target_dir: Target directory path (will be created if missing)

    Returns:
        List of extracted file names

    Example:
        >>> files = extract_zip_to_directory(zip_bytes, Path.cwd() / ".claude" / "agents")
        >>> print(files)
        ['orchestrator.md', 'implementor.md', 'tester.md']
    """
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract ZIP
    extracted_files = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
        zipf.extractall(target_dir)
        extracted_files = zipf.namelist()
    
    logger.info(f"Extracted {len(extracted_files)} files to {target_dir}")
    return extracted_files
