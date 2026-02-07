#!/usr/bin/env python3
"""
CSP Hash Generator for GiljoAI MCP

Generates SHA-256 hashes for inline <script> and <style> blocks in index.html
to enable hash-based Content Security Policy (CSP).

Created in Handover 1007 - Hash-Based CSP Implementation

Usage:
    python scripts/generate_csp_hashes.py

This script:
1. Reads frontend/index.html
2. Extracts inline <style> and <script> content
3. Calculates SHA-256 hashes (base64-encoded)
4. Outputs CSP-formatted hashes for use in security middleware

For CSP compliance:
- Hash is calculated from the EXACT content between tags (not including tags)
- Content includes all whitespace, indentation, and newlines as-is
- Hash format: 'sha256-{base64_hash}'
"""

import base64
import hashlib
import re
from pathlib import Path


def calculate_csp_hash(content: str) -> str:
    """
    Calculate SHA-256 hash for CSP.

    Args:
        content: Exact content between <script> or <style> tags

    Returns:
        CSP-formatted hash: 'sha256-{base64_hash}'
    """
    # Calculate SHA-256 hash
    hash_digest = hashlib.sha256(content.encode("utf-8")).digest()
    # Base64 encode
    hash_b64 = base64.b64encode(hash_digest).decode("utf-8")
    return f"'sha256-{hash_b64}'"


def extract_inline_blocks(html_content: str):
    """
    Extract inline <script> and <style> blocks from HTML.

    Returns:
        List of tuples: (tag_type, content, line_range)
    """
    blocks = []

    # Pattern to match <style>...</style> (capturing content between tags)
    style_pattern = r"<style>(.*?)</style>"
    for match in re.finditer(style_pattern, html_content, re.DOTALL):
        content = match.group(1)
        start_line = html_content[: match.start()].count("\n") + 1
        end_line = html_content[: match.end()].count("\n") + 1
        blocks.append(("style", content, f"{start_line}-{end_line}"))

    # Pattern to match <script>...</script> (excluding <script src="...">)
    # This captures inline scripts only (no src attribute)
    script_pattern = r"<script(?![^>]*\bsrc=)(?:[^>]*)>(.*?)</script>"
    for match in re.finditer(script_pattern, html_content, re.DOTALL):
        content = match.group(1)
        start_line = html_content[: match.start()].count("\n") + 1
        end_line = html_content[: match.end()].count("\n") + 1
        blocks.append(("script", content, f"{start_line}-{end_line}"))

    return blocks


def main():
    """Generate CSP hashes for index.html inline blocks."""
    # Find index.html
    index_html_path = Path(__file__).parent.parent / "frontend" / "index.html"

    if not index_html_path.exists():
        print(f"ERROR: index.html not found at {index_html_path}")
        return 1

    print(f"Reading: {index_html_path}")
    html_content = index_html_path.read_text(encoding="utf-8")

    # Extract inline blocks
    blocks = extract_inline_blocks(html_content)

    if not blocks:
        print("WARNING: No inline <script> or <style> blocks found")
        return 0

    print(f"\nFound {len(blocks)} inline block(s)\n")

    # Calculate hashes
    style_hashes = []
    script_hashes = []

    for i, (tag_type, content, line_range) in enumerate(blocks, 1):
        hash_value = calculate_csp_hash(content)

        print(f"Block {i}: <{tag_type}> (lines {line_range})")
        print(f"  Hash: {hash_value}")
        print(f"  Content length: {len(content)} bytes")
        print()

        if tag_type == "style":
            style_hashes.append(hash_value)
        elif tag_type == "script":
            script_hashes.append(hash_value)

    # Generate CSP directives
    print("=" * 70)
    print("CSP DIRECTIVES FOR SECURITY MIDDLEWARE")
    print("=" * 70)

    if style_hashes:
        print("\nstyle-src directive:")
        print(f"  style-src 'self' {' '.join(style_hashes)}")

    if script_hashes:
        print("\nscript-src directive (PRODUCTION):")
        print(f"  script-src 'self' {' '.join(script_hashes)}")

        print("\nscript-src directive (DEVELOPMENT - with unsafe-eval for HMR):")
        print(f"  script-src 'self' {' '.join(script_hashes)} 'unsafe-eval'")

    print("\n" + "=" * 70)
    print("Copy the appropriate directives to api/middleware/security.py")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
