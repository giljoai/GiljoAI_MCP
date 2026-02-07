#!/usr/bin/env python3
"""Serve the Developer Panel static frontend on http://127.0.0.1:5173."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "frontend"
    Handler = SimpleHTTPRequestHandler

    class FrontendHandler(Handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 5173), FrontendHandler)
    print(f"[DevPanel] Frontend available at http://127.0.0.1:5173 (serving {root})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DevPanel] Stopping frontend server...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
