"""
API Key utilities for hashing, validation, and generation.

This module provides utilities for secure API key management in LAN/WAN modes:
- Generate cryptographically secure API keys with gk_ prefix
- Hash API keys using bcrypt for secure storage
- Verify API keys against stored hashes
- Extract display prefixes for UI purposes

Security Notes:
- API keys are hashed using bcrypt (same algorithm as passwords)
- Original keys are NEVER stored in plaintext
- Keys are only shown once at generation time
- Display prefixes show first 12 characters for user reference

Usage Example:
    from giljo_mcp.api_key_utils import generate_api_key, hash_api_key, verify_api_key

    # Generate new key
    api_key = generate_api_key()  # Returns: "gk_abc123..."

    # Hash for storage
    key_hash = hash_api_key(api_key)

    # Later, verify incoming key
    if verify_api_key(api_key, key_hash):
        # Valid key
        pass
"""

import secrets

from passlib.hash import bcrypt


def generate_api_key() -> str:
    """
    Generate a new cryptographically secure API key.

    The key format is: gk_<32-byte-urlsafe-token>
    - gk_ prefix identifies it as a GiljoAI key
    - 32-byte token provides ~256 bits of entropy
    - URL-safe encoding (no special chars that need escaping)

    Returns:
        API key string (e.g., "gk_xyzABC123...")

    Example:
        >>> api_key = generate_api_key()
        >>> api_key.startswith("gk_")
        True
        >>> len(api_key) > 40  # gk_ (3) + token (~43 chars)
        True
    """
    random_part = secrets.token_urlsafe(32)
    return f"gk_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage using bcrypt.

    Bcrypt provides:
    - Automatic salting (different hash each time)
    - Adaptive cost factor (can be increased over time)
    - Built-in protection against timing attacks

    Args:
        api_key: The plaintext API key to hash

    Returns:
        Bcrypt hash string (60 characters, bcrypt format)

    Example:
        >>> api_key = "gk_abc123"
        >>> key_hash = hash_api_key(api_key)
        >>> len(key_hash)
        60
        >>> key_hash.startswith("$2b$")  # Bcrypt format
        True
    """
    return bcrypt.hash(api_key)


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """
    Verify an API key against a stored hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        api_key: The plaintext API key to verify
        key_hash: The stored bcrypt hash

    Returns:
        True if key matches hash, False otherwise

    Example:
        >>> api_key = generate_api_key()
        >>> key_hash = hash_api_key(api_key)
        >>> verify_api_key(api_key, key_hash)
        True
        >>> verify_api_key("gk_wrong", key_hash)
        False
    """
    return bcrypt.verify(api_key, key_hash)


def get_key_prefix(api_key: str, length: int = 12) -> str:
    """
    Get display-friendly prefix of an API key.

    Shows only the first N characters followed by ellipsis.
    Safe to display in logs, UI, etc.

    Args:
        api_key: The full API key
        length: Number of characters to include (default: 12)

    Returns:
        Display string (e.g., "gk_abc12345...")

    Example:
        >>> api_key = "gk_verylongtoken123456789"
        >>> get_key_prefix(api_key)
        'gk_verylongt...'
        >>> get_key_prefix(api_key, 8)
        'gk_veryl...'
    """
    if len(api_key) <= length:
        return api_key
    return f"{api_key[:length]}..."
