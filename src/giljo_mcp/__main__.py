#!/usr/bin/env python
"""
DEPRECATED: stdio entrypoint for giljo_mcp

Use HTTP JSON-RPC endpoint instead. This module exits with guidance.
"""

from .mcp_adapter import main as _main


def main() -> None:
    _main()


if __name__ == "__main__":
    main()

