#!/usr/bin/env python3
"""Isolated, synthetic-only tests for offline L2 receipt evaluator.

No real Mac, browser, signed BFF, PG, OS child or provider is contacted.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).with_name('l2_no_dispatch_receipt_gate.py')
spec = importlib.util.spec_from_file_location('ui_f3_l2_gate', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
C = {
    't2_id': 't2_mock_fixture',
    'attempt_id': 'attempt_mock_fixture',
    'attempt_trace_id': 'attempt_trace_mock_fixture',
    'client_message_id': 'uih_mock_fixture',
    'idempotency_key': 'key_mock_fixture',
    'question_sha256': 'f' * 64,
}


def event(seq, phase, actor, layer, method, path, status):
    return {**{k: C[k] for k in ('t2_id', 'attempt_id', 'attempt_trace_id',
                                 'client_message_id', 'idempotency_key')},
            'seq': seq, 'phase': phase, 'actor': actor, 'layer': layer,
            'method': method, 'path': path, 'status': status}


def synthetic_receipt(root):
    (root / 'evidence').mkdir()
    witnesses = {}
    for name in module.REQUIRED_FILES:
        path = root / 'evidence' / (name + '.txt')
        path.write_text('SYNTHETIC TEST ONLY / ' + name + '\n', encoding='utf-8')
        witnesses[name] = {'path': 'evidence/' + name + '.txt',
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    records = [
        event(1, 'initial', 'A', 'browser', 'POST', '/api/history/messages', 202),
        event(2, 'initial', 'A', 'api', 'POST', '/api/history/messages', 202),
        event(3, 'initial', 'A', 'api', 'GET', module.STATUS_PATH, 200),
        event(4, 'outage', 'A', 'api', 'GET', module.CONVERSATIONS_PATH, 503),
        event(5, 'recovery', 'A', 'api', 'GET', module.CONVERSATIONS_PATH, 200),
        event(6, 'refresh', 'A', 'browser', 'GET', module.CONVERSATIONS_PATH, 200),
        event(7, 'refresh', 'A', 'api', 'GET', module.STATUS_PATH, 200),
        event(8, 'cross_owner', 'B', 'api', 'GET', module.STATUS_PATH, 404),
        event(9, 'revoked', 'A', 'api', 'GET', module.CONVERSATIONS_PATH, 401),
    ]
    return {
        'kind': module.KIND,
        'schema_version': module.SCHEMA,
        'fixture_only': True,
        'environment': 'isolated_mac_https_oidc',
        'provenance': {
            'integrated_sha': '1' * 40,
            'ui_sha': '2' * 40,
            'api_sha': '3' * 40,
            'db_sha': '4' * 40,
            'engine_sha': '5' * 40,
            'ops_approval_ref': 'SYNTHETIC_NOT_AN_APPROVAL',
            'runner_mode': 'NO_DISPATCH_ONLY',
        },
        'browser': {
            'https_origin': 'https://staging.example.org',
            'actor_a_session_alias': 'actor_a_synthetic',
            'actor_b_session_alias': 'actor_b_synthetic',
            'oidc_a_validated': True,
            'oidc_b_validated': True,
            'logout_navigated': True,
            'owner_switch_clears_ui': True,
            'revocation_clears_ui': True,
            'late_get_cannot_restore': True,
            'mobile_rtl_a11y_pass': True,
            'owner_a_revalidated_same': True,
            'tab_b_a_data_visible': False,
            'stale_thread_after_recovery_visible': False,
        },
        'correlation': C.copy(),
        'http_events': records,
        'database': {
            't2_id': C['t2_id'],
            'attempt_id': C['attempt_id'],
            'attempt_trace_id': C['attempt_trace_id'],
            'owner_a_history_rows': 1,
            'owner_b_cross_history_rows': 0,
            'new_attempt_rows_after_refresh': 0,
            'new_user_messages_after_refresh': 0,
            'new_answer_rows_after_refresh': 0,
            'original_request_unique': True,
        },
        'runner': {
            'attempt_id': C['attempt_id'],
            'attempt_trace_id': C['attempt_trace_id'],
            'c018_child_count_before_refresh': 1,
            'c018_child_count_after_refresh': 1,
            'top10_before': 10,
            'top10_after': 10,
            'generation_calls_before': 0,
            'generation_calls_after': 0,
            'dispatch_performed': False,
            'c018_artifact_sha256': 'e' * 64,
        },
        'witnesses': witnesses,
    }


class ReceiptGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.doc = synthetic_receipt(self.root)

    def failures(self, doc=None, *, allow_synthetic=True):
        return module.evaluate(self.doc if doc is None else doc, self.root,
                               allow_synthetic=allow_synthetic)

    def assert_failure(self, expected, doc=None, **kw):
        result = self.failures(doc, **kw)
        self.assertIn(expected, result, result)

    def test_self_fixture_is_consistent_only_with_explicit_unit_test_override(self):
        self.assertEqual(self.failures(), [])

    def test_fixture_never_qualifies_at_real_cli(self):
        self.assert_failure('NO_SYNTHETIC_L2_ACCEPTANCE', allow_synthetic=False)
        sample = self.root / 'sample.json'
        sample.write_text(json.dumps(self.doc), encoding='utf-8')
        cli = subprocess.run([sys.executable, str(MODULE), str(sample)],
                             text=True, capture_output=True, check=False)
        self.assertEqual(cli.returncode, 1)
        report = json.loads(cli.stdout)
        self.assertFalse(report['gate_accepted'])
        self.assertEqual(report['status'], 'NOT_VERIFIED')

    def test_provenance_missing(self):
        self.doc['provenance']['ui_sha'] = 'not SHA'
        self.assert_failure('EXACT_SHA_MISSING_ui_sha')

    def test_no_integration_approval(self):
        self.doc['provenance']['ops_approval_ref'] = ''
        self.assert_failure('OPS_SCOPE_AUTHORIZATION_MISSING')

    def test_no_dispatch_strict(self):
        self.doc['provenance']['runner_mode'] = 'LIVE_GENERATE'
        self.assert_failure('RUNNER_MODE_NOT_NO_DISPATCH')

    def test_http_or_loopback_does_not_count_as_real_private_https(self):
        for url in ['http://staging.example.org', 'https://127.0.0.1',
                    'https://localhost:3000', 'https://user:pass@staging.example.org',
                    'https://staging.example.org/private']:
            with self.subTest(url=url):
                self.doc['browser']['https_origin'] = url
                self.assert_failure('BROWSER_HTTPS_OIDC_ORIGIN_MISSING')

    def test_two_separate_owner_sessions_required(self):
        self.doc['browser']['actor_b_session_alias'] = 'actor_a_synthetic'
        self.assert_failure('DISTINCT_SANITIZED_A_B_SESSIONS_MISSING')

    def test_browser_revocation_must_purge(self):
        self.doc['browser']['revocation_clears_ui'] = False
        self.assert_failure('BROWSER_REVOCATION_CLEARS_UI_NOT_PROVEN')

    def test_cross_tab_exposure_is_never_acceptable(self):
        self.doc['browser']['tab_b_a_data_visible'] = True
        self.assert_failure('CROSS_TAB_ACCOUNT_LEAK')

    def test_503_must_have_real_api_witness(self):
        self.doc['http_events'][3]['status'] = 200
        self.assert_failure('OWNER_LIST_503_RECOVERY_GET_NOT_PROVEN')

    def test_503_owner_revalidation_must_be_same_actor(self):
        self.doc['browser']['owner_a_revalidated_same'] = False
        self.assert_failure('BROWSER_OWNER_A_REVALIDATED_SAME_NOT_PROVEN')

    def test_stale_thread_data_must_not_be_visible_after_recovery(self):
        self.doc['browser']['stale_thread_after_recovery_visible'] = True
        self.assert_failure('STALE_HISTORY_RESURRECTED_AFTER_RECOVERY')

    def test_http_event_out_of_order_recovery_is_rejected(self):
        self.doc['http_events'][4]['phase'] = 'refresh'
        self.assert_failure('OPERATION_503_RECOVERY_ORDER_INVALID')

    def test_status_wrong_attempt_disallowed(self):
        self.doc['http_events'][6]['attempt_id'] = 'forged_other_attempt'
        self.assert_failure('CROSS_LAYER_CORRELATION_MISMATCH_attempt_id')

    def test_status_wrong_t2_disallowed(self):
        self.doc['database']['t2_id'] = 'forged_wrong_t2'
        self.assert_failure('DB_T2_MISMATCH_t2_id')

    def test_duplicate_initial_browser_send_is_rejected(self):
        x = copy.deepcopy(self.doc['http_events'][0]); x['seq'] = 10
        self.doc['http_events'].append(x)
        self.assert_failure('EXACTLY_ONE_INITIAL_SEND_POST_PER_LAYER')

    def test_duplicate_send_after_refresh_is_rejected(self):
        x = copy.deepcopy(self.doc['http_events'][0]); x['seq'] = 10; x['phase'] = 'refresh'
        self.doc['http_events'].append(x)
        self.assert_failure('NO_POST_ON_REFRESH_OR_RECOVERY')

    def test_refreshed_browser_must_read_owner_list(self):
        self.doc['http_events'] = [x for x in self.doc['http_events'] if x['seq'] != 6]
        self.assert_failure('REFRESH_DOES_NOT_READ_ORIGINAL_STATUS')

    def test_owner_b_404_required(self):
        self.doc['http_events'][7]['status'] = 200
        self.assert_failure('CROSS_OWNER_NOT_PROVED_404')

    def test_owner_a_revoke_401_required(self):
        self.doc['http_events'][8]['status'] = 200
        self.assert_failure('REVOKE_NOT_PROVED_401')

    def test_db_new_write_after_refresh_forbidden(self):
        self.doc['database']['new_attempt_rows_after_refresh'] = 1
        self.assert_failure('DB_NEW_ATTEMPT_ROWS_AFTER_REFRESH_INVALID')

    def test_os_second_c018_child_forbidden(self):
        self.doc['runner']['c018_child_count_after_refresh'] = 2
        self.assert_failure('OS_C018_CHILD_COUNT_AFTER_REFRESH_INVALID')

    def test_os_top10_count_cannot_be_invented(self):
        self.doc['runner']['top10_after'] = 9
        self.assert_failure('OS_TOP10_AFTER_INVALID')

    def test_model_generation_forbidden(self):
        self.doc['runner']['generation_calls_after'] = 1
        self.assert_failure('OS_GENERATION_CALLS_AFTER_INVALID')

    def test_boolean_not_integer_count(self):
        self.doc['runner']['top10_before'] = True
        self.assert_failure('OS_TOP10_BEFORE_INVALID')

    def test_no_witnesses_is_not_evidence(self):
        self.doc.pop('witnesses')
        self.assert_failure('WITNESS_FILE_ABSENT_OR_OUTSIDE_ROOT_browser')

    def test_witness_tampering_detected(self):
        (self.root / 'evidence/browser.txt').write_text('tampered evidence')
        self.assert_failure('WITNESS_HASH_MISMATCH_browser')

    def test_path_traversal_detected(self):
        self.doc['witnesses']['browser']['path'] = '../../outside.txt'
        self.assert_failure('WITNESS_FILE_ABSENT_OR_OUTSIDE_ROOT_browser')

    def test_reused_layer_witness_detected(self):
        self.doc['witnesses']['os'] = self.doc['witnesses']['api'].copy()
        self.assert_failure('INDEPENDENT_WITNESS_FILES_REUSED')

    def test_http_event_sequence_unique_and_monotonic(self):
        self.doc['http_events'][8]['seq'] = 4
        self.assert_failure('HTTP_EVENT_SEQUENCE_INVALID')

    def test_never_accepts_even_a_non_fixture_structurally_consistent_document(self):
        self.doc['fixture_only'] = False
        self.assertEqual(self.failures(allow_synthetic=False), [])
        sample = self.root / 'report.json'; sample.write_text(json.dumps(self.doc))
        cli = subprocess.run([sys.executable, str(MODULE), str(sample)],
                             text=True, capture_output=True, check=False)
        self.assertEqual(cli.returncode, 0)
        report = json.loads(cli.stdout)
        self.assertEqual(report['status'], 'RECEIPT_INTERNALLY_CONSISTENT_NOT_GATE_ACCEPTED')
        self.assertFalse(report['gate_accepted'])
        self.assertTrue(report['independent_owner_review_required'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
