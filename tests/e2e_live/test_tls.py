# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""(a) TLS reachable + certificate valid through the real edge.

This is the unique value localhost can't reproduce: it proves the deployed host
terminates TLS with a chain-valid, hostname-matching, unexpired certificate via
the real Cloudflare -> nginx -> uvicorn path.
"""

from __future__ import annotations

import socket
import ssl
import time

import pytest


@pytest.mark.network
def test_tls_handshake_and_cert_valid(target):
    """A default (verifying) TLS handshake succeeds and the cert is unexpired.

    ``ssl.create_default_context()`` verifies the certificate chain AND the
    hostname; an invalid/expired/mismatched cert raises during ``wrap_socket``,
    failing the test. The explicit ``notAfter`` check is belt-and-suspenders.
    """
    if target.scheme != "https":
        pytest.skip(reason="target is not https; TLS cert check not applicable")

    ctx = ssl.create_default_context()
    with socket.create_connection((target.host, target.port), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=target.host) as ssock:
            cert = ssock.getpeercert()

    assert cert, "no peer certificate returned by the server"
    not_after = ssl.cert_time_to_seconds(cert["notAfter"])
    assert not_after > time.time(), f"certificate already expired at {cert['notAfter']}"
