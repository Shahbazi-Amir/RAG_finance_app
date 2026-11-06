"""Executable synthetic-only product-contract tests; no network, secrets or runtime."""
import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from semantics import cross_checks, check_idempotency_history, canonical_request_fingerprint, check_request_receipt

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / 'packages/contracts/product.v1.schema.json'
FIXTURE_PATH = ROOT / 'packages/contracts/fixtures/product.v1.cases.json'


def read_json(path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


SCHEMA = read_json(SCHEMA_PATH)
FIXTURES = read_json(FIXTURE_PATH)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def errors_for(document):
    structural = sorted(VALIDATOR.iter_errors(document), key=lambda x: str(x.path))
    if structural:
        return ['SCHEMA:' + str(error.message) for error in structural]
    return cross_checks(document)


def fixture(case_id):
    return copy.deepcopy(next(x['document'] for x in FIXTURES['cases'] if x['case_id'] == case_id))


class TestMachineReadableContract(unittest.TestCase):
    def test_schema_is_valid_draft202012(self):
        Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(SCHEMA['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        self.assertEqual(len(SCHEMA['oneOf']), 14)

    def test_all_synthetic_positive_and_negative_cases(self):
        ids = [c['case_id'] for c in FIXTURES['cases']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(FIXTURES['origin'], 'SYNTHETIC')
        self.assertGreaterEqual(len(ids), 30)
        positives = negatives = 0
        for case in FIXTURES['cases']:
            with self.subTest(case=case['case_id']):
                self.assertEqual(case['origin'], 'SYNTHETIC')
                result = errors_for(case['document'])
                if case['expected_valid']:
                    positives += 1
                    self.assertEqual(result, [], f"Unexpected errors for {case['case_id']}: {result}")
                else:
                    negatives += 1
                    self.assertNotEqual(result, [], f"Invalid case accepted: {case['case_id']}")
        self.assertGreaterEqual(positives, 15)
        self.assertGreaterEqual(negatives, 20)

    def test_claim_citation_bidirectionality(self):
        original = fixture('valid_answer_unresolved_source')
        self.assertEqual(errors_for(original), [])
        missing = copy.deepcopy(original)
        missing['citations'][0]['claim_ids'] = ['ghost']
        self.assertTrue(any('REF' in e for e in errors_for(missing)))
        duplicated = copy.deepcopy(original)
        duplicated['citations'].append(copy.deepcopy(duplicated['citations'][0]))
        self.assertIn('DUPLICATE_CITATION_ID', errors_for(duplicated))

    def test_error_is_not_no_answer_or_unknown(self):
        err = fixture('valid_answer_technical_error')
        no_answer = fixture('valid_answer_no_answer')
        unknown = fixture('valid_answer_unknown')
        self.assertNotEqual(err['outcome'], no_answer['outcome'])
        self.assertNotEqual(err['outcome'], unknown['outcome'])
        self.assertEqual(err['error']['category'], 'technical')
        self.assertIsNone(no_answer['error'])
        self.assertEqual(unknown['state'], 'unknown')
        self.assertEqual(errors_for(err), [])

    def test_confidence_null_is_not_zero(self):
        no_measure = fixture('valid_answer_unresolved_source')
        self.assertIsNone(no_measure['confidence'])
        measured = fixture('valid_confidence_calibrated_example')
        self.assertIsInstance(measured['confidence'], dict)
        for number in (-0.1, 1.1):
            measured['confidence']['value'] = number
            self.assertTrue(errors_for(measured))
        measured['confidence']['value'] = 0
        self.assertEqual(errors_for(measured), [])  # A real measured zero would be valid, unlike null.

    def test_synthetic_citation_cannot_be_real_evidence(self):
        synthetic = fixture('valid_answer_unresolved_source')
        self.assertEqual(synthetic['provenance']['origin'], 'SYNTHETIC')
        source = synthetic['citations'][0]['source']
        self.assertIsNone(source['locator'])
        self.assertIsNone(source['speaker_name'])
        source['resolution_status'] = 'verified'
        source['source_id'] = 'source_1'
        source['locator'] = {'kind':'transcript_timestamp','url':None,'page':None,'timestamp_ms':1234}
        source['attribution_status'] = 'verified'
        self.assertIn('SYNTHETIC_SOURCE_MARKED_REAL', errors_for(synthetic))

    def test_stream_terminal_and_cancel_are_distinct(self):
        for case in ('valid_stream_completed','valid_stream_failed','valid_stream_server_cancelled','valid_stream_unknown','valid_stream_display_only_cancel'):
            self.assertEqual(errors_for(fixture(case)), [], case)
        client_cancel = fixture('valid_stream_display_only_cancel')
        self.assertEqual(client_cancel['events'][-1]['event_type'], 'display_cancelled')
        self.assertNotIn('server_stopped', client_cancel['events'][-1]['data'])
        actual_server = fixture('valid_stream_server_cancelled')
        self.assertTrue(actual_server['events'][-1]['data']['server_stopped'])
        terminal = fixture('valid_stream_completed')
        terminal['events'].append(copy.deepcopy(terminal['events'][3]))
        terminal['events'][-1]['seq'] = 5
        self.assertIn('MULTIPLE_OR_NONFINAL_TERMINAL_EVENTS', errors_for(terminal))

    def test_trusted_identity_is_not_client_input(self):
        request = fixture('valid_send_message_request')
        self.assertNotIn('owner_user_id', request)
        request['owner_user_id'] = 'user_other'
        self.assertTrue(errors_for(request))
        internal = fixture('valid_trusted_actor_context')
        self.assertEqual(internal['principal_source'], 'server_auth_context')

    def test_idempotency_replay_scope_and_conflict(self):
        original = fixture('valid_send_message_receipt')
        replay = copy.deepcopy(original)
        replay['disposition'] = 'replayed'
        replay['request_id'] = original['request_id']
        self.assertEqual(check_idempotency_history([original,replay]), [])
        bad_replay = copy.deepcopy(replay)
        bad_replay['message_id'] = 'msg_duplicate'
        self.assertIn('RETRY_MUST_REPLAY_SAME_PERSISTED_MESSAGE',check_idempotency_history([original,bad_replay]))
        diff = copy.deepcopy(replay)
        diff.update(payload_sha256='b'*64,disposition='conflict',message_id=None,error={'category':'validation','code':'IDEMPOTENCY_CONFLICT','message':'changed payload'})
        self.assertEqual(errors_for(diff), [])
        self.assertEqual(check_idempotency_history([original,diff]), [])
        wrong = copy.deepcopy(diff)
        wrong['disposition'] = 'replayed'
        wrong['message_id'] = 'msg_1'
        wrong['error'] = None
        self.assertIn('IDEMPOTENCY_KEY_PAYLOAD_CONFLICT',check_idempotency_history([original,wrong]))
        another_user = copy.deepcopy(original)
        another_user.update(owner_user_id='user_2',disposition='created')
        self.assertEqual(check_idempotency_history([original,another_user]), [])
        # This is a *storage contract*, not a guarantee the provider/model executes exactly once.

    def test_request_receipt_fingerprint_and_authenticated_scope(self):
        request = fixture('valid_send_message_request')
        receipt = fixture('valid_send_message_receipt')
        actor = fixture('valid_trusted_actor_context')
        self.assertEqual(receipt['payload_sha256'], canonical_request_fingerprint(request))
        self.assertEqual(check_request_receipt(request, receipt, actor), [])
        tampered = copy.deepcopy(request)
        tampered['question'] = 'Different question; same idempotency key'
        self.assertIn('PAYLOAD_FINGERPRINT_MISMATCH',check_request_receipt(tampered,receipt,actor))
        forged = copy.deepcopy(receipt)
        forged['owner_user_id'] = 'user_2'
        self.assertIn('UNTRUSTED_IDENTITY',check_request_receipt(request,forged,actor))

    def test_no_export_dependency_on_deletion(self):
        command = fixture('valid_delete_command_confirmed')
        self.assertEqual(errors_for(command), [])
        self.assertNotIn('export_requested', command)
        self.assertNotIn('export_required', command)
        progress = fixture('valid_delete_processing')
        self.assertFalse(progress['backend_confirmed'])
        success = copy.deepcopy(progress)
        success.update(state='succeeded',backend_confirmed=True,completed_at='2026-01-01T00:00:01Z')
        self.assertEqual(errors_for(success), [])
        success['backend_confirmed'] = False
        self.assertTrue(errors_for(success))

    def test_provisional_release_is_not_accepted_runtime(self):
        answer = fixture('valid_answer_unresolved_source')
        self.assertEqual(answer['provenance']['rag_binding']['blocked_by'], 'NB23')
        self.assertIsNone(answer['provenance']['rag_binding']['release_id'])
        answer['provenance']['rag_binding']['release_id'] = 'fake_release'
        self.assertTrue(errors_for(answer))


if __name__ == '__main__':
    unittest.main(verbosity=2)
