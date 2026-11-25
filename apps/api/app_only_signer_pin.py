"""App-only signer continuity: a changed Ops key requires a fresh startup."""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class SignerPin:
    _digest: bytes

    @classmethod
    def capture(cls, public_key: bytes) -> SignerPin:
        if not isinstance(public_key, bytes) or not 1 <= len(public_key) <= 65536:
            raise ValueError("INVALID_SIGNER_MATERIAL")
        return cls(hashlib.sha256(public_key).digest())

    def matches(self, public_key: bytes) -> bool:
        return (isinstance(public_key, bytes) and 1 <= len(public_key) <= 65536
                and hmac.compare_digest(self._digest, hashlib.sha256(public_key).digest()))

    def current(self, load_public_key) -> bool:
        try:
            return self.matches(load_public_key())
        except Exception:
            # Configuration failure must never retain a stale authorization.
            return False
