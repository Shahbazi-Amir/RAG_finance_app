"""Trusted TLS transport peer identity for the NO_DISPATCH private API.

Direct client-certificate TLS, not forwarded HTTP headers, determines admission.
Uvicorn's H11Protocol currently does NOT expose the SSL peer to the ASGI scope.
The protocol wrapper below reads the real SSLObject after handshake and
transfers a process-local opaque capability ONLY for an exact pinned BFF leaf.

PINNED implementation contract: uvicorn==0.48.0, HTTP/1.1, one worker, no
proxy_headers, ssl.CERT_REQUIRED and Ops-supplied client CA. A different
server/protocol/version must fail closed until separately reviewed.
"""
from __future__ import annotations

from hashlib import sha256
import re
import ssl
from typing import Mapping

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CAPABILITY_SCOPE_KEY = "ragfinance.private_staging.verified_bff_capability"


class VerifiedPeerUnavailable(Exception):
    def __str__(self):
        return "PRIVATE_MTLS_PEER_DENIED"


class TrustedBFFTLSBoundary:
    """A capability bound to a real CA-verified+fingerprint-pinned connection."""

    def __init__(self, leaf_sha256: str):
        if not isinstance(leaf_sha256, str) or not _HEX64.fullmatch(leaf_sha256):
            raise VerifiedPeerUnavailable()
        self._expected_fingerprint = leaf_sha256
        self.__capability = object()

    def approved_tls_peer(self, ssl_object) -> bool:
        """Called only on a transport-owned SSLObject after OpenSSL handshake.

        The TLS context must have verified the chain against the configured
        client CA with CERT_REQUIRED. A DER leaf fingerprint additionally pins
        WHICH client cert is the BFF, not merely any certificate from that CA.
        """
        try:
            if (ssl_object is None
                    or ssl_object.context.verify_mode != ssl.CERT_REQUIRED
                    or ssl_object.version() not in ("TLSv1.3", "TLSv1.2")):
                return False
            der = ssl_object.getpeercert(binary_form=True)
            return (isinstance(der, bytes) and bool(der)
                    and sha256(der).hexdigest() == self._expected_fingerprint)
        except (AttributeError, OSError, ssl.SSLError, ValueError):
            return False

    def scope_is_verified(self, scope: Mapping) -> bool:
        """Used by PrivateStagingProfile.allowed_peer on every signed call."""
        return (isinstance(scope, Mapping)
                and scope.get("type") == "http"
                and scope.get("scheme") == "https"
                and scope.get(_CAPABILITY_SCOPE_KEY) is self.__capability)

    def wrap_real_verified_connection(self, app, ssl_object):
        """Only protocol code may invoke after a real TLS connection is verified."""
        if not self.approved_tls_peer(ssl_object):
            raise VerifiedPeerUnavailable()
        private_capability = self.__capability

        async def transport_verified_app(scope, receive, send):
            if scope.get("type") != "http" or scope.get("scheme") != "https":
                raise VerifiedPeerUnavailable()
            # Never mutate shared scope; overwrite any injected/caller field.
            protected = dict(scope)
            protected[_CAPABILITY_SCOPE_KEY] = private_capability
            await app(protected, receive, send)

        return transport_verified_app


def make_verified_h11_protocol(boundary: TrustedBFFTLSBoundary):
    """A Uvicorn HTTP/1.1 protocol, with transport-derived BFF capability.

    A failed certificate check closes the connection before any request can be
    passed to the application. The TLS handshake itself must have verified the
    certificate chain; invalid or absent client certificates never reach here.
    """
    if not isinstance(boundary, TrustedBFFTLSBoundary):
        raise VerifiedPeerUnavailable()
    import uvicorn
    from uvicorn.protocols.http.h11_impl import H11Protocol
    if uvicorn.__version__ != "0.48.0":
        raise VerifiedPeerUnavailable()

    class VerifiedH11Protocol(H11Protocol):
        def connection_made(self, transport):
            super().connection_made(transport)
            ssl_object = transport.get_extra_info("ssl_object")
            try:
                self.app = boundary.wrap_real_verified_connection(
                    self.app, ssl_object)
            except VerifiedPeerUnavailable:
                transport.close()  # no application call or fallback
                return

    return VerifiedH11Protocol
