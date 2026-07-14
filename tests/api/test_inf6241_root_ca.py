# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6241 regression: /root-ca serves the operator-provided cert, not mkcert.

Failing layer = ``api/endpoints/configuration.py:download_root_ca()``. INF-6241
reworks the body from a mkcert shell-out (``mkcert -CAROOT`` + read rootCA.pem)
to serving the configured server cert via ``_ssl_status_from_config()``:

  - When a cert is configured and present on disk (``has_cert=True``) the
    endpoint returns a ``FileResponse`` with the cert PEM and filename
    ``giljo-server-cert.pem`` (Global Decision 1 canonical name).
  - When no cert is configured (``has_cert=False``) it raises HTTP 404.
  - The "HTTPS disabled but cert configured" case still returns the cert
    (``has_cert`` gate, not ``ssl_enabled`` gate -- Global Decision 2).

Route path/method/auth (GET /api/v1/config/root-ca, requires auth) is unchanged
-- ``test_be6042b_app_surface.py`` pins the surface and must stay green.

Pure unit: ``_ssl_status_from_config`` is monkeypatched so no real disk I/O or
config file is needed. xdist-safe: no module-level mutable state.
"""

from __future__ import annotations

import datetime
import ipaddress
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from fastapi.responses import FileResponse

from api.endpoints import configuration as cfg


# ---------------------------------------------------------------------------
# Shared helper (mirrors _write_self_signed_pair from test_inf6236_cert_ux.py)
# ---------------------------------------------------------------------------


def _write_self_signed_pair(tmp_path: Path) -> tuple[str, str]:
    """Write a throwaway self-signed cert+key PEM pair. Returns (cert_path, key_path).

    Structurally valid self-signed pair -- enough for a FileResponse path check.
    Generated in-process so the test needs no openssl binary.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.local")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC))
        .not_valid_after(datetime.datetime(2040, 1, 1, tzinfo=datetime.UTC))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return str(cert_path), str(key_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDownloadRootCa:
    """download_root_ca() serves the operator-provided cert or 404s (INF-6241)."""

    @pytest.mark.asyncio
    async def test_serves_configured_cert_as_file_response(self, monkeypatch, tmp_path):
        """has_cert=True -> FileResponse with the cert path and canonical filename.

        This is the primary success case: an operator has configured a cert via
        Settings -> Network. The endpoint serves that exact PEM so a remote
        machine can trust this server (a private/self-signed cert is its own
        trust anchor).
        """
        cert_path, key_path = _write_self_signed_pair(tmp_path)

        import api.endpoints.configuration_ssl as ssl_mod

        monkeypatch.setattr(
            ssl_mod,
            "_ssl_status_from_config",
            lambda: (True, cert_path, key_path, True),
        )

        response = await cfg.download_root_ca()

        assert isinstance(response, FileResponse), "Expected a FileResponse when cert is configured"
        assert response.path == cert_path, "FileResponse must point at the configured cert path"
        assert response.filename == "giljo-server-cert.pem", (
            "Canonical downloaded filename must be giljo-server-cert.pem (Global Decision 1)"
        )

    @pytest.mark.asyncio
    async def test_404_when_no_cert_configured(self, monkeypatch):
        """has_cert=False -> HTTP 404 (no cert configured on this server).

        A publicly-signed cert (Let's Encrypt / corporate CA) needs no download --
        clients already trust it. The server correctly returns 404 in that case.
        """
        import api.endpoints.configuration_ssl as ssl_mod

        monkeypatch.setattr(
            ssl_mod,
            "_ssl_status_from_config",
            lambda: (False, None, None, False),
        )

        with pytest.raises(HTTPException) as exc:
            await cfg.download_root_ca()

        assert exc.value.status_code == 404, "Expected 404 when no cert is configured (has_cert=False)"

    @pytest.mark.asyncio
    async def test_404_when_https_disabled_and_no_cert(self, monkeypatch):
        """ssl_enabled=True but cert absent from disk -> has_cert=False -> 404.

        The gate is has_cert (cert configured + present), not ssl_enabled alone.
        Global Decision 2: a misconfigured state (ssl_enabled without cert) is
        a 404, not a 500.
        """
        import api.endpoints.configuration_ssl as ssl_mod

        monkeypatch.setattr(
            ssl_mod,
            "_ssl_status_from_config",
            lambda: (True, None, None, False),
        )

        with pytest.raises(HTTPException) as exc:
            await cfg.download_root_ca()

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cert_served_even_when_ssl_disabled(self, monkeypatch, tmp_path):
        """ssl_enabled=False but cert configured and present -> serves the cert.

        Global Decision 2: gate is has_cert, not ssl_enabled. A cert is its own
        trust anchor; the endpoint serves it whenever a cert is present so a
        remote client can trust it regardless of whether ssl_enabled is True.
        This is acceptable (auth-gated; cert is its own anchor).
        """
        cert_path, key_path = _write_self_signed_pair(tmp_path)

        import api.endpoints.configuration_ssl as ssl_mod

        monkeypatch.setattr(
            ssl_mod,
            "_ssl_status_from_config",
            lambda: (False, cert_path, key_path, True),
        )

        response = await cfg.download_root_ca()

        assert isinstance(response, FileResponse)
        assert response.path == cert_path
        assert response.filename == "giljo-server-cert.pem"

    @pytest.mark.asyncio
    async def test_response_media_type_is_pem(self, monkeypatch, tmp_path):
        """FileResponse must use the PEM MIME type for correct browser handling."""
        cert_path, key_path = _write_self_signed_pair(tmp_path)

        import api.endpoints.configuration_ssl as ssl_mod

        monkeypatch.setattr(
            ssl_mod,
            "_ssl_status_from_config",
            lambda: (True, cert_path, key_path, True),
        )

        response = await cfg.download_root_ca()

        assert response.media_type == "application/x-pem-file", (
            "FileResponse must use application/x-pem-file so browsers prompt a download"
        )
