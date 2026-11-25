"""Review-only pure oracle. Not imported by product runtime; no engine/network/cache.

Names, formats and candidate scopes are proposals, not approved contracts. A
matching fingerprint proves synthetic bytes/identity only; it never grants an
operation. Keep all outputs local to the test suite, not logs or product DTOs.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry
from referencing.exceptions import Unresolvable

DRAFTS = Path(__file__).resolve().parents[3] / 'packages/contracts/drafts'
RELEASE_SCHEMA = 'f3-release-binding.synthetic.v0.schema.json'
CACHE_SCHEMA = 'f3-cache-identity.synthetic.v0.schema.json'
ARTIFACTS = frozenset(('data', 'chunks', 'embeddings', 'index', 'config'))


class DraftDenied(ValueError):
    """Constant message; never reflect user or manifest data."""
    def __str__(self):
        return 'SYNTHETIC_PREFLIGHT_DENIED'


def sha256(raw: bytes) -> str:
    if type(raw) is not bytes:
        raise DraftDenied()
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DraftDenied()
        result[key] = value
    return result


def _nonfinite(_):
    raise DraftDenied()


def parse(raw: bytes, schema_name: str) -> dict:
    # Only local, named draft schemas; never dereference user-controlled paths.
    if type(raw) is not bytes or schema_name not in (RELEASE_SCHEMA, CACHE_SCHEMA):
        raise DraftDenied()
    try:
        doc = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                         parse_constant=_nonfinite)
        schema_path = DRAFTS / schema_name
        if schema_path.is_symlink() or not schema_path.is_file():
            raise DraftDenied()
        schema = json.loads(schema_path.read_text(encoding='utf-8'),
                            object_pairs_hook=_unique, parse_constant=_nonfinite)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, registry=Registry()).validate(doc)
        if type(doc) is not dict:
            raise DraftDenied()
        return doc
    except (ValueError, TypeError, UnicodeError, OSError, RecursionError,
            SchemaError, ValidationError, Unresolvable):
        raise DraftDenied() from None


def _strict_json_tree(value):
    # Do not silently coerce tuples, non-string keys, or Python subclasses.
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            raise DraftDenied()
        for item in value.values():
            _strict_json_tree(item)
    elif type(value) is list:
        for item in value:
            _strict_json_tree(item)
    elif value is not None and type(value) not in (str, bool, int, float):
        raise DraftDenied()


def canonical_bytes(doc: dict) -> bytes:
    try:
        if type(doc) is not dict:
            raise DraftDenied()
        _strict_json_tree(doc)
        return json.dumps(doc, ensure_ascii=True, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('ascii')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DraftDenied() from None


def inspect_release(raw: bytes, *, expected_manifest_sha256: str,
                    artifacts: dict[str, bytes]) -> dict:
    """Test local synthetic bytes against a separately supplied exact manifest pin."""
    if (type(expected_manifest_sha256) is not str
            or not expected_manifest_sha256.isascii()
            or not hmac.compare_digest(sha256(raw), expected_manifest_sha256)):
        raise DraftDenied()
    doc = parse(raw, RELEASE_SCHEMA)
    if type(artifacts) is not dict or set(artifacts) != ARTIFACTS:
        raise DraftDenied()
    for name in ARTIFACTS:
        if not hmac.compare_digest(sha256(artifacts[name]), doc['artifacts'][name]):
            raise DraftDenied()
    return {'release_id': doc['release_id'], 'manifest_sha256': sha256(raw),
            'synthetic_match': True, 'approved': False, 'dispatch_allowed': False}


def candidate_fingerprint(raw: bytes, *, release_raw: bytes,
                          expected_manifest_sha256: str,
                          artifacts: dict[str, bytes]) -> str:
    """No real cache key or cache access. Fail closed for private scopes."""
    doc = parse(raw, CACHE_SCHEMA)
    if doc['scope'] != 'synthetic_public_candidate':
        raise DraftDenied()
    receipt = inspect_release(release_raw, expected_manifest_sha256=expected_manifest_sha256,
                              artifacts=artifacts)
    if (doc['release_id'] != receipt['release_id']
            or doc['release_manifest_sha256'] != receipt['manifest_sha256']):
        raise DraftDenied()
    return sha256(canonical_bytes(doc))


def same_fresh_candidate(*, stored_fingerprint: str, current_fingerprint: str,
                         created_at: int, now: int, ttl_seconds: int) -> bool:
    """Pure comparison. TTL is caller-provided synthetic test input, never a default.

    A True result is not runtime authorization; no cache is read or written.
    """
    for value in (stored_fingerprint, current_fingerprint):
        if (type(value) is not str or len(value) != 64
                or any(c not in '0123456789abcdef' for c in value)):
            return False
    if (any(type(x) is not int for x in (created_at, now, ttl_seconds))
            or created_at < 0 or now < created_at or ttl_seconds <= 0):
        return False
    return (hmac.compare_digest(stored_fingerprint, current_fingerprint)
            and now - created_at < ttl_seconds)
