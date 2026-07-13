# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared trusted-proxy-aware client IP resolution (SEC-6001, SEC-6010).

Both the auth rate limiter (``auth_rate_limiter.py``) and the generic rate
limiter (``rate_limiter.py``) need to derive a per-IP rate-limit key from a
request. Behind a reverse proxy (Railway, nginx) the TCP peer
(``request.client.host``) is the proxy's shared IP, so naive per-IP keying
collapses every caller into one bucket. The fix is to honor the FIRST-HOP
``X-Forwarded-For`` entry ONLY when the immediate peer is in the
operator-configured trusted-proxy allowlist (``GILJO_TRUSTED_PROXIES``,
comma-separated CIDR or exact IPs).

When the peer is untrusted, XFF (and any other forwarding header) is a
forgeable client header and is ignored entirely — the allowlist gate IS the
spoofing protection. Default (empty allowlist) keys on ``request.client.host``,
the safe pre-proxy behavior.

This module is the single source of truth so the gate cannot drift between the
two limiters. SEC-6010 extracted it from ``auth_rate_limiter.py``.

Edition Scope: Both.
"""

import ipaddress
import logging
import os
from typing import Protocol


logger = logging.getLogger(__name__)


TRUSTED_PROXIES_ENV = "GILJO_TRUSTED_PROXIES"

_TrustedNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class _PeerLike(Protocol):
    host: str


class _HeadersLike(Protocol):
    def get(self, key: str) -> str | None: ...


class _RequestLike(Protocol):
    """The minimal request surface the resolver touches.

    Both Starlette ``Request`` and the duck-typed stubs the security tests use
    satisfy this: a ``client`` with a ``host`` (or ``None``) and a
    ``headers.get`` accessor.
    """

    @property
    def client(self) -> _PeerLike | None: ...

    @property
    def headers(self) -> _HeadersLike: ...


def parse_trusted_proxies(raw: str | None) -> list[_TrustedNetwork]:
    """Parse the trusted-proxy allowlist env value into networks.

    Accepts comma-separated exact IPs (``192.0.2.5``) or CIDR blocks
    (``192.0.2.0/24``). Exact IPs are normalized to /32 (v4) or /128 (v6)
    networks. Malformed entries are skipped with a warning rather than
    crashing startup — a typo in one entry must not disable rate limiting
    entirely.
    """
    if not raw:
        return []
    networks: list[_TrustedNetwork] = []
    for entry in raw.split(","):
        candidate = entry.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            logger.warning("Ignoring malformed %s entry: %r", TRUSTED_PROXIES_ENV, candidate)
    return networks


class ProxyAwareIpResolver:
    """Resolves a request's client IP, gated on a trusted-proxy allowlist.

    Trusted proxies are resolved once at construction from
    ``GILJO_TRUSTED_PROXIES``. Instances are expected to live for the process
    lifetime (the limiters are singletons / middleware constructed at app
    startup), so a deploy-time env change is picked up on the next boot — the
    expected lifecycle for an infrastructure setting.
    """

    def __init__(self) -> None:
        self._trusted_proxies = parse_trusted_proxies(os.getenv(TRUSTED_PROXIES_ENV))

    @property
    def trusted_proxy_count(self) -> int:
        return len(self._trusted_proxies)

    def peer_is_trusted_proxy(self, peer_ip: str) -> bool:
        if not self._trusted_proxies:
            return False
        try:
            addr = ipaddress.ip_address(peer_ip)
        except ValueError:
            return False
        return any(addr in network for network in self._trusted_proxies)

    def resolve(self, request: _RequestLike) -> str:
        """Resolve the client IP used for rate-limit keying.

        When the immediate peer is a trusted proxy, the real client is taken
        from the forwarding headers, preferring Cloudflare's authoritative
        ``CF-Connecting-IP`` (a single, unambiguous value) and falling back to
        the first ``X-Forwarded-For`` hop (left-most entry, the original
        client) for non-Cloudflare proxies (e.g. nginx, Railway-only paths).

        When the peer is NOT a trusted proxy, ALL forwarding headers are
        ignored — they are spoofable client-supplied headers and the
        trusted-proxy gate IS the spoofing protection — and the direct peer IP
        is used.

        Why ``CF-Connecting-IP`` matters (perf-findings 2026-06-11): behind
        Cloudflare → Railway, the XFF first hop the app sees is a *Cloudflare*
        edge IP, not the real client, so XFF-only keying collapses every user
        into a handful of shared Cloudflare-IP buckets → platform-wide 429
        storms. ``CF-Connecting-IP`` carries the true client, so per-user
        buckets are restored. It is only honored once ``peer_is_trusted_proxy``
        has passed, so an untrusted caller cannot forge it (same threat model
        that already protects XFF here).
        """
        client = request.client
        if client is None:
            return "unknown"
        peer_ip = client.host

        if self.peer_is_trusted_proxy(peer_ip):
            cf_ip = request.headers.get("CF-Connecting-IP")
            if cf_ip and cf_ip.strip():
                return cf_ip.strip()
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                first_hop = forwarded.split(",")[0].strip()
                if first_hop:
                    return first_hop
        return peer_ip
