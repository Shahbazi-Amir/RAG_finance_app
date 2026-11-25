"""Executable, synthetic-only preparation for P3M07-A01/A02/A06/A09,
P3M08-A01, P3M12-A07 and P3M17-A04/A06. Never a production acceptance test.
"""
import copy
import unittest
from unittest.mock import patch

from f3_synthetic_preflight_oracle import (
    ARTIFACTS, CACHE_SCHEMA, RELEASE_SCHEMA, DraftDenied, canonical_bytes,
    candidate_fingerprint, inspect_release, parse, same_fresh_candidate, sha256,
)


class SyntheticPreflight(unittest.TestCase):
    def setUp(self):
        self.artifacts = {name: ('synthetic-' + name).encode() for name in ARTIFACTS}
        self.release = {
            'contract_version': 'synthetic-release-binding.v0',
            'origin': 'SYNTHETIC', 'approval': 'NOT_APPROVED',
            'release_id': 'fixture-r1',
            'artifacts': {k: sha256(v) for k, v in self.artifacts.items()},
        }
        self.raw = canonical_bytes(self.release)
        self.pin = sha256(self.raw)
        self.key = {
            'contract_version': 'synthetic-cache-identity.v0',
            'origin': 'SYNTHETIC', 'approval': 'NOT_APPROVED',
            'release_id': self.release['release_id'],
            'release_manifest_sha256': self.pin, 'policy_version': 'fixture-policy-1',
            'authority_filter_sha256': sha256(b'fixture-filter'),
            'locale': 'fa-IR', 'question_sha256': sha256('سؤال آزمایشی'.encode()),
            'scope': 'synthetic_public_candidate',
        }

    def inspect(self, raw=None, artifacts=None, pin=None):
        return inspect_release(self.raw if raw is None else raw,
            expected_manifest_sha256=self.pin if pin is None else pin,
            artifacts=self.artifacts if artifacts is None else artifacts)

    def fingerprint(self, key=None, raw=None, pin=None, artifacts=None):
        return candidate_fingerprint(canonical_bytes(self.key if key is None else key),
            release_raw=self.raw if raw is None else raw,
            expected_manifest_sha256=self.pin if pin is None else pin,
            artifacts=self.artifacts if artifacts is None else artifacts)

    def deny(self, callback):
        with self.assertRaises(DraftDenied) as err:
            callback()
        self.assertEqual(str(err.exception), 'SYNTHETIC_PREFLIGHT_DENIED')

    def test_release_exact_bytes_match_without_approval(self):
        receipt = self.inspect()
        self.assertEqual(receipt['manifest_sha256'], self.pin)
        self.assertEqual(receipt['release_id'], 'fixture-r1')
        self.assertTrue(receipt['synthetic_match'])
        self.assertFalse(receipt['approved'])
        self.assertFalse(receipt['dispatch_allowed'])

    def test_manifest_byte_drift_denied_even_when_semantics_equal(self):
        self.deny(lambda: self.inspect(raw=self.raw + b' '))

    def test_each_of_five_artifact_byte_drift_denied(self):
        for name in sorted(ARTIFACTS):
            with self.subTest(name=name):
                bad = dict(self.artifacts)
                bad[name] += b'-mutated'
                self.deny(lambda: self.inspect(artifacts=bad))

    def test_missing_or_extra_artifacts_denied(self):
        for name in sorted(ARTIFACTS):
            bad = dict(self.artifacts)
            del bad[name]
            self.deny(lambda: self.inspect(artifacts=bad))
        self.deny(lambda: self.inspect(artifacts={**self.artifacts, 'extra': b'x'}))

    def test_unversioned_manifest_denied_even_with_matching_pin(self):
        for value in ('', '   ', None):
            doc = dict(self.release, release_id=value)
            raw = canonical_bytes(doc)
            self.deny(lambda: self.inspect(raw=raw, pin=sha256(raw)))
        doc = dict(self.release)
        del doc['release_id']
        raw = canonical_bytes(doc)
        self.deny(lambda: self.inspect(raw=raw, pin=sha256(raw)))

    def test_manifest_does_not_allow_live_approval_or_new_fields(self):
        for doc in (dict(self.release, origin='LIVE_VERIFIED'),
                    dict(self.release, approval='APPROVED'),
                    dict(self.release, dispatch_allowed=True),
                    dict(self.release, contract_version='other')):
            raw = canonical_bytes(doc)
            self.deny(lambda: self.inspect(raw=raw, pin=sha256(raw)))

    def test_manifest_duplicate_json_keys_denied(self):
        raw = self.raw[:-1] + b',"release_id":"fixture-r1"}'
        self.deny(lambda: self.inspect(raw=raw, pin=sha256(raw)))

    def test_invalid_utf8_and_nonfinite_json_denied(self):
        for raw in (b'\xff', b'{"data":NaN}', b'{"data":Infinity}'):
            self.deny(lambda: parse(raw, RELEASE_SCHEMA))

    def test_config_digest_binds_config_bytes_not_only_release_label(self):
        other = dict(self.artifacts, config=b'synthetic-different-config')
        self.deny(lambda: self.inspect(artifacts=other))
        manifest = copy.deepcopy(self.release)
        manifest['artifacts']['config'] = sha256(other['config'])
        new = canonical_bytes(manifest)
        self.deny(lambda: self.inspect(raw=new, artifacts=other))
        receipt = self.inspect(raw=new, artifacts=other, pin=sha256(new))
        self.assertFalse(receipt['approved'])

    def test_draft_refuses_raw_question_owner_and_token_fields(self):
        for field in ('question', 'owner_id', 'token', 'authorization'):
            self.deny(lambda: self.fingerprint(dict(self.key, **{field: 'canary'})))

    def test_private_scope_cannot_generate_public_candidate_fingerprint(self):
        for scope in ('personal', 'history'):
            self.deny(lambda: self.fingerprint(dict(self.key, scope=scope)))

    def test_missing_identity_component_denied(self):
        for field in ('release_id','release_manifest_sha256','policy_version',
                      'authority_filter_sha256','locale','question_sha256','scope'):
            doc = dict(self.key)
            del doc[field]
            self.deny(lambda: self.fingerprint(doc))

    def test_policy_version_mandatory_and_opaque(self):
        for value in ('', ' ', None, 1, True):
            self.deny(lambda: self.fingerprint(dict(self.key, policy_version=value)))
        self.assertNotEqual(self.fingerprint(), self.fingerprint(dict(self.key, policy_version='fixture-policy-2')))

    def test_key_canonical_order_but_no_semantic_normalization(self):
        reordered = dict(reversed(list(self.key.items())))
        self.assertEqual(self.fingerprint(), self.fingerprint(reordered))
        for field, value in (('authority_filter_sha256',sha256(b'other-filter')),
                             ('locale','fa'), ('question_sha256',sha256(b'other-question')),
                             ('policy_version','fixture-policy-2')):
            with self.subTest(field=field):
                self.assertNotEqual(self.fingerprint(), self.fingerprint(dict(self.key, **{field: value})))

    def test_unbound_or_mismatching_release_never_matches(self):
        for change in ({'release_id':'fixture-other'}, {'release_manifest_sha256':'0'*64}):
            self.deny(lambda: self.fingerprint(dict(self.key, **change)))

    def test_release_change_and_same_id_different_bytes_invalidate_candidate(self):
        old = self.fingerprint()
        for label in ('fixture-r2', 'fixture-r1'):
            new_bytes = dict(self.artifacts, config=b'new-synthetic-config')
            manifest = copy.deepcopy(self.release)
            manifest['release_id'] = label
            manifest['artifacts']['config'] = sha256(new_bytes['config'])
            raw = canonical_bytes(manifest)
            new_key = dict(self.key, release_id=label, release_manifest_sha256=sha256(raw))
            new = self.fingerprint(new_key, raw=raw, pin=sha256(raw), artifacts=new_bytes)
            self.assertNotEqual(old, new)
            self.assertFalse(same_fresh_candidate(stored_fingerprint=old, current_fingerprint=new,
                          created_at=10, now=11, ttl_seconds=20))

    def test_old_synthetic_binding_can_be_rechecked_but_not_authorized(self):
        old = self.inspect()
        changed = dict(self.artifacts, index=b'other-synthetic-index')
        self.deny(lambda: self.inspect(artifacts=changed))
        self.assertEqual(self.inspect(), old)
        self.assertFalse(old['approved'])
        self.assertFalse(old['dispatch_allowed'])

    def test_expiry_boundary_and_future_timestamps(self):
        f = self.fingerprint()
        def fresh(now, ttl=10, created=100):
            return same_fresh_candidate(stored_fingerprint=f, current_fingerprint=f,
                         created_at=created, now=now, ttl_seconds=ttl)
        self.assertTrue(fresh(100))
        self.assertTrue(fresh(109))
        self.assertFalse(fresh(110))
        self.assertFalse(fresh(111))
        self.assertFalse(fresh(99))
        self.assertFalse(fresh(100, created=-1))

    def test_ttl_missing_or_nonpositive_or_ambiguous_denied(self):
        f = self.fingerprint()
        for value in (None, 0, -1, True, 1.5, '10'):
            self.assertFalse(same_fresh_candidate(stored_fingerprint=f,current_fingerprint=f,
                             created_at=10,now=10,ttl_seconds=value))
        with self.assertRaises(TypeError):
            same_fresh_candidate(stored_fingerprint=f,current_fingerprint=f,created_at=10,now=10)

    def test_invalid_fingerprint_does_not_become_hit(self):
        for value in ('', 'X'*64, '0'*63, None):
            self.assertFalse(same_fresh_candidate(stored_fingerprint=value,current_fingerprint=value,
                             created_at=10,now=10,ttl_seconds=10))

    def test_only_local_schemas_and_no_network_or_subprocess(self):
        with patch('socket.create_connection',side_effect=AssertionError('NO_NETWORK')) as sock, \
             patch('urllib.request.urlopen',side_effect=AssertionError('NO_NETWORK')) as url, \
             patch('subprocess.Popen',side_effect=AssertionError('NO_SPAWN')) as proc:
            self.inspect()
            self.fingerprint()
            self.deny(lambda: parse(self.raw,'../../private.json'))
            sock.assert_not_called()
            url.assert_not_called()
            proc.assert_not_called()


    def test_invalid_local_schema_is_fixed_denial(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp, patch('f3_synthetic_preflight_oracle.DRAFTS', Path(tmp)):
            (Path(tmp)/RELEASE_SCHEMA).write_text('{"type":"not-a-json-schema-type"}')
            self.deny(lambda:parse(self.raw, RELEASE_SCHEMA))

    def test_duplicate_keys_in_local_schema_are_denied(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp, patch('f3_synthetic_preflight_oracle.DRAFTS', Path(tmp)):
            (Path(tmp)/RELEASE_SCHEMA).write_text('{"type":"string","type":"object"}')
            self.deny(lambda:parse(self.raw, RELEASE_SCHEMA))

    def test_local_schema_symlink_is_denied(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp, patch('f3_synthetic_preflight_oracle.DRAFTS', Path(tmp)):
            outside=Path(tmp)/'other.json'; outside.write_text('{"type":"object"}')
            (Path(tmp)/RELEASE_SCHEMA).symlink_to(outside)
            self.deny(lambda:parse(self.raw, RELEASE_SCHEMA))

    def test_canonical_document_never_coerces_keys_or_container(self):
        for doc in ([1,2], {1:'fixture-value'}, {'nested':{2:'fixture-value'}}, {'nested':('fixture-value',)}):
            self.deny(lambda:canonical_bytes(doc))


if __name__ == '__main__':
    unittest.main(verbosity=2)
