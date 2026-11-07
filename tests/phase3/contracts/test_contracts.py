"""Executable synthetic-only product-contract tests; no network, secrets or runtime."""
import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from semantics import (cross_checks, check_idempotency_history, canonical_request_fingerprint,
    check_request_receipt, canonical_feedback_fingerprint, check_feedback_request_receipt,
    check_feedback_receipt_history, check_delete_command_status, check_delete_status_query)

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
        self.assertEqual(len(SCHEMA['oneOf']), 24)  # 17 historical + 7 additive history operations; old payload rules unchanged

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
        source['source_type'] = 'transcript'
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
        diff.update(payload_sha256='b'*64,disposition='conflict',resolved_conversation_id=None,message_id=None,error={'category':'validation','code':'IDEMPOTENCY_CONFLICT','message':'changed payload'})
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

    def test_delta_space_newline_empty_and_exact_text_reconstruction(self):
        for name in ('valid_delta_space', 'valid_delta_newline'):
            self.assertEqual(errors_for(fixture(name)), [], name)
        self.assertTrue(errors_for(fixture('invalid_delta_empty')))
        session = fixture('valid_stream_reconstruct_preserves_whitespace')
        self.assertEqual(errors_for(session), [])
        chunks = [e['data']['text'] for e in session['events'] if e['event_type'] == 'delta']
        self.assertEqual(chunks, ['سلام', ' ', 'دنیا', '\n', 'خط دوم'])
        self.assertEqual(''.join(chunks), 'سلام دنیا\nخط دوم')
        self.assertEqual(session['events'][-1]['event_type'], 'completed')
        invalid_final = fixture('valid_answer_unresolved_source')
        invalid_final['answer_text'] = '  \n '
        self.assertTrue(errors_for(invalid_final), 'Only delta text accepts whitespace-only, not final answer')
        reordered = copy.deepcopy(session)
        reordered['events'][4]['seq'] = 99
        self.assertIn('NONCONTIGUOUS_EVENT_SEQUENCE', errors_for(reordered))

    def test_new_conversation_idempotency_and_stable_allocation(self):
        request = fixture('valid_request_new_conversation')
        receipt = fixture('valid_receipt_new_conversation_allocated')
        actor = fixture('valid_trusted_actor_context')
        self.assertIsNone(request['requested_conversation_id'])
        self.assertEqual(receipt['resolved_conversation_id'], 'conv_alloc_01')
        self.assertEqual(errors_for(request), [])
        self.assertEqual(errors_for(receipt), [])
        self.assertEqual(check_request_receipt(request, receipt, actor), [])
        self.assertEqual(receipt['payload_sha256'], canonical_request_fingerprint(request))
        replay = copy.deepcopy(receipt)
        replay['disposition'] = 'replayed'
        self.assertEqual(check_idempotency_history([receipt, replay]), [])
        self.assertEqual(check_request_receipt(request, replay, actor), [])
        bad_replay = copy.deepcopy(replay)
        bad_replay['resolved_conversation_id'] = 'conv_wrong'
        self.assertIn('RETRY_MUST_REPLAY_SAME_RESOLVED_CONVERSATION', check_idempotency_history([receipt, bad_replay]))
        bad_replay['resolved_conversation_id'] = receipt['resolved_conversation_id']
        bad_replay['message_id'] = 'msg_other'
        self.assertIn('RETRY_MUST_REPLAY_SAME_PERSISTED_MESSAGE', check_idempotency_history([receipt, bad_replay]))
        changed = copy.deepcopy(request)
        changed['question'] = 'پیام دیگر با کلید تکراری'
        self.assertNotEqual(canonical_request_fingerprint(request), canonical_request_fingerprint(changed))
        conflict = copy.deepcopy(receipt)
        conflict.update(disposition='conflict', message_id=None, resolved_conversation_id=None,
                        payload_sha256=canonical_request_fingerprint(changed),
                        error={'category':'validation','code':'IDEMPOTENCY_CONFLICT','message':'different payload'})
        self.assertEqual(errors_for(conflict), [])
        self.assertEqual(check_idempotency_history([receipt, conflict]), [])
        self.assertEqual(check_request_receipt(changed, conflict, actor), [])
        same_other_user = copy.deepcopy(receipt)
        same_other_user['owner_user_id'] = 'user_other'
        self.assertEqual(check_idempotency_history([receipt, same_other_user]), [])
        self.assertIn('UNTRUSTED_IDENTITY', check_request_receipt(request, same_other_user, actor))

        existing = fixture('valid_send_message_request')
        existing_receipt = fixture('valid_send_message_receipt')
        self.assertEqual(existing['requested_conversation_id'], 'conv_1')
        self.assertEqual(existing_receipt['resolved_conversation_id'], 'conv_1')
        self.assertEqual(check_request_receipt(existing, existing_receipt, actor), [])
        wrong_thread = copy.deepcopy(existing_receipt)
        wrong_thread['resolved_conversation_id'] = 'conv_other'
        self.assertIn('RESOLVED_CONVERSATION_MISMATCH', errors_for(wrong_thread))
        self.assertIn('RESOLVED_CONVERSATION_MISMATCH', check_request_receipt(existing, wrong_thread, actor))
        missing_resolved = copy.deepcopy(receipt)
        missing_resolved['resolved_conversation_id'] = None
        self.assertTrue(errors_for(missing_resolved))
        self.assertIn('SUCCESS_RECEIPT_MISSING_RESOLVED_CONVERSATION', check_request_receipt(request, missing_resolved, actor))

    def test_locator_variants_and_source_type_compatibility(self):
        source_validator = Draft202012Validator({
            '$schema': SCHEMA['$schema'], '$defs': SCHEMA['$defs'], '$ref': '#/$defs/source_attribution'
        }, format_checker=FormatChecker())
        def source_errors(source):
            return list(source_validator.iter_errors(source))
        def source_for(source_type, locator):
            return {
                'resolution_status': 'verified', 'source_type': source_type,
                'source_id': 'source_fixture_only', 'locator': locator,
                'credited_author_name': None, 'editorial_supervisor_name': None,
                'speaker_name': None, 'content_authority_type': None,
                'attribution_status': 'unknown'
            }
        book_anchor = {'kind':'book_anchor','url':None,'page':None,'timestamp_ms':None,
                       'work_id':'work_edition_test','edition_id':'ed1','anchor':'chapter_3_p4'}
        transcript_segment = {'kind':'transcript_segment','url':None,'page':None,
                              'timestamp_ms':None,'episode_id':'episode_test','segment_anchor':'segment_17'}
        website = {'kind':'url','url':'https://example.invalid/test','page':None,'timestamp_ms':None}
        old_book_page = {'kind':'book_page','url':None,'page':7,'timestamp_ms':None}
        old_time = {'kind':'transcript_timestamp','url':None,'page':None,'timestamp_ms':2000}
        for typ,loc in [('book',book_anchor),('transcript',transcript_segment),
                        ('website',website),('book',old_book_page),('transcript',old_time)]:
            self.assertEqual(source_errors(source_for(typ,loc)), [], (typ,loc))
        self.assertTrue(source_errors(source_for('website',book_anchor)))
        self.assertTrue(source_errors(source_for('transcript',old_book_page)))
        self.assertTrue(source_errors(source_for('book',transcript_segment)))
        bad_book = copy.deepcopy(book_anchor)
        del bad_book['edition_id']
        self.assertTrue(source_errors(source_for('book',bad_book)))
        bad_episode = copy.deepcopy(transcript_segment)
        bad_episode['timestamp_ms'] = 0
        self.assertTrue(source_errors(source_for('transcript',bad_episode)))

        for cid in ('valid_source_metadata_unresolved_book','valid_source_metadata_unresolved_transcript','valid_unresolved_hypothetical_author'):
            answer = fixture(cid)
            self.assertEqual(errors_for(answer), [], cid)
            meta = answer['citations'][0]['source']
            self.assertIsNone(meta['locator'])
            self.assertEqual(meta['attribution_status'], 'unknown')
            self.assertTrue(meta['credited_author_name'])
        forged = fixture('valid_source_metadata_unresolved_book')
        forged['citations'][0]['source']['attribution_status'] = 'verified'
        self.assertIn('SYNTHETIC_SOURCE_MARKED_REAL', errors_for(forged))
        forged = fixture('valid_source_metadata_unresolved_book')
        source = forged['citations'][0]['source']
        source.update(resolution_status='verified', locator=book_anchor)
        self.assertIn('SYNTHETIC_SOURCE_MARKED_REAL', errors_for(forged))
        # A structurally valid locator is NOT real source evidence in a SYNTHETIC envelope.

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


    def test_feedback_request_acknowledgement_and_trusted_owner(self):
        request=fixture('valid_feedback_submit_request')
        receipt=fixture('valid_feedback_submit_receipt')
        actor=fixture('valid_trusted_actor_context')
        record=fixture('valid_feedback')
        self.assertEqual(errors_for(request), [])
        self.assertEqual(errors_for(receipt), [])
        self.assertEqual(receipt['payload_sha256'],canonical_feedback_fingerprint(request))
        snapshot=fixture('valid_snapshot_relations')
        self.assertEqual(check_feedback_request_receipt(request,receipt,actor,record,snapshot),[])
        wrong_snapshot=copy.deepcopy(snapshot)
        wrong_snapshot['conversation']['owner_user_id']='user_other'
        self.assertIn('FEEDBACK_TARGET_NOT_OWNED_OR_MISSING',check_feedback_request_receipt(request,receipt,actor,record,wrong_snapshot))
        wrong_snapshot=copy.deepcopy(snapshot)
        wrong_snapshot['answers']=[]
        self.assertIn('FEEDBACK_TARGET_NOT_OWNED_OR_MISSING',check_feedback_request_receipt(request,receipt,actor,record,wrong_snapshot))
        self.assertNotIn('owner_user_id',request)
        self.assertNotIn('trace_id',request)
        self.assertNotIn('request_id',request)
        fake_owner=copy.deepcopy(receipt)
        fake_owner['owner_user_id']='user_other'
        self.assertIn('UNTRUSTED_FEEDBACK_OWNER',check_feedback_request_receipt(request,fake_owner,actor))
        foreign_actor=copy.deepcopy(actor)
        foreign_actor['owner_user_id']='user_other'
        self.assertIn('UNTRUSTED_FEEDBACK_OWNER',check_feedback_request_receipt(request,receipt,foreign_actor))
        wrong_answer=copy.deepcopy(receipt)
        wrong_answer['answer_id']='ans_other'
        self.assertIn('FEEDBACK_RECEIPT_MISMATCH_ANSWER_ID',check_feedback_request_receipt(request,wrong_answer,actor))
        wrong_record=copy.deepcopy(record)
        wrong_record['answer_id']='ans_else'
        self.assertIn('FEEDBACK_DOCUMENT_RELATION_MISMATCH',check_feedback_request_receipt(request,receipt,actor,wrong_record))
        wrong_record=copy.deepcopy(record)
        wrong_record['owner_user_id']='user_other'
        self.assertIn('FEEDBACK_DOCUMENT_RELATION_MISMATCH',check_feedback_request_receipt(request,receipt,actor,wrong_record))

    def test_feedback_retry_replay_conflict_and_network_unknown(self):
        req=fixture('valid_feedback_submit_request')
        original=fixture('valid_feedback_submit_receipt')
        actor=fixture('valid_trusted_actor_context')
        replay=fixture('valid_feedback_replayed_receipt')
        self.assertEqual(check_feedback_receipt_history([original,replay]),[])
        self.assertEqual(check_feedback_request_receipt(req,replay,actor),[])
        duplicate=copy.deepcopy(replay)
        duplicate['feedback_id']='fb_double'
        self.assertIn('FEEDBACK_RETRY_MUST_REPLAY_SAME_RECORD',check_feedback_receipt_history([original,duplicate]))
        replaced_time=copy.deepcopy(replay)
        replaced_time['persisted_at']='2026-01-02T00:00:00Z'
        self.assertIn('FEEDBACK_RETRY_MUST_REPLAY_SAME_RECORD',check_feedback_receipt_history([original,replaced_time]))
        different_req=copy.deepcopy(req)
        different_req['rating']='negative'
        conflict=fixture('valid_feedback_conflict_receipt')
        conflict['payload_sha256']=canonical_feedback_fingerprint(different_req)
        self.assertEqual(check_feedback_request_receipt(different_req,conflict,actor),[])
        self.assertEqual(check_feedback_receipt_history([original,conflict]),[])
        illicit_replay=copy.deepcopy(replay)
        illicit_replay['payload_sha256']=conflict['payload_sha256']
        self.assertIn('FEEDBACK_IDEMPOTENCY_KEY_PAYLOAD_CONFLICT',check_feedback_receipt_history([original,illicit_replay]))
        other_user=copy.deepcopy(original)
        other_user['owner_user_id']='user_other'
        self.assertEqual(check_feedback_receipt_history([original,other_user]),[])
        self.assertIn('UNTRUSTED_FEEDBACK_OWNER',check_feedback_request_receipt(req,other_user,actor))
        self.assertTrue(errors_for(fixture('invalid_feedback_server_transport_unknown')))
        self.assertTrue(errors_for(fixture('invalid_feedback_success_without_persistence_time')))
        # Disconnected browser == local pending/unknown; never claim a server-confirmed record.

    def test_feedback_created_trace_is_bound_to_current_server_context(self):
        request=fixture('valid_feedback_submit_request')
        receipt=fixture('valid_feedback_submit_receipt')
        actor=fixture('valid_trusted_actor_context')
        self.assertEqual(check_feedback_request_receipt(request,receipt,actor),[])
        forged_request_id=copy.deepcopy(receipt)
        forged_request_id['request_id']='req_unrelated'
        self.assertIn('FEEDBACK_TRACE_CONTEXT_MISMATCH_REQUEST_ID',
                      check_feedback_request_receipt(request,forged_request_id,actor))
        forged_trace_id=copy.deepcopy(receipt)
        forged_trace_id['trace_id']='trace_unrelated'
        self.assertIn('FEEDBACK_TRACE_CONTEXT_MISMATCH_TRACE_ID',
                      check_feedback_request_receipt(request,forged_trace_id,actor))
        # Either server identifier may be forged independently of authenticated owner.
        self.assertEqual(forged_trace_id['owner_user_id'],actor['owner_user_id'])

    def test_feedback_replay_trace_identifies_current_attempt_not_initial_persistence(self):
        request=fixture('valid_feedback_submit_request')
        created=fixture('valid_feedback_submit_receipt')
        initial_actor=fixture('valid_trusted_actor_context')
        replay=fixture('valid_feedback_replayed_receipt')
        current_actor=copy.deepcopy(initial_actor)
        current_actor['request_id']='req_feedback_retry_2'
        current_actor['trace_id']='trace_feedback_retry_2'
        replay['request_id']=current_actor['request_id']
        replay['trace_id']=current_actor['trace_id']
        self.assertEqual(check_feedback_request_receipt(request,replay,current_actor),[])
        self.assertEqual(check_feedback_receipt_history([created,replay]),[])
        self.assertEqual(replay['feedback_id'],created['feedback_id'])
        self.assertEqual(replay['persisted_at'],created['persisted_at'])
        self.assertNotEqual(replay['request_id'],created['request_id'])
        self.assertNotEqual(replay['trace_id'],created['trace_id'])
        self.assertIn('FEEDBACK_TRACE_CONTEXT_MISMATCH_REQUEST_ID',
                      check_feedback_request_receipt(request,replay,initial_actor))
        self.assertIn('FEEDBACK_TRACE_CONTEXT_MISMATCH_TRACE_ID',
                      check_feedback_request_receipt(request,replay,initial_actor))
        wrong_request=copy.deepcopy(replay)
        wrong_request['request_id']=created['request_id']
        self.assertIn('FEEDBACK_TRACE_CONTEXT_MISMATCH_REQUEST_ID',
                      check_feedback_request_receipt(request,wrong_request,current_actor))
        wrong_trace=copy.deepcopy(replay)
        wrong_trace['trace_id']=created['trace_id']
        self.assertIn('FEEDBACK_TRACE_CONTEXT_MISMATCH_TRACE_ID',
                      check_feedback_request_receipt(request,wrong_trace,current_actor))
        # A replay must not rewrite persisted identity/time to match its new network trace.
        changed_persistence=copy.deepcopy(replay)
        changed_persistence['persisted_at']='2026-01-02T00:00:00Z'
        self.assertIn('FEEDBACK_RETRY_MUST_REPLAY_SAME_RECORD',
                      check_feedback_receipt_history([created,changed_persistence]))

    def test_deletion_server_context_and_secure_status_polling(self):
        command=fixture('valid_delete_command_confirmed')
        status=fixture('valid_delete_processing')
        query=fixture('valid_delete_status_query')
        actor=fixture('valid_trusted_actor_context')
        actor['request_id']=status['request_id']
        actor['trace_id']=status['trace_id']
        self.assertEqual(errors_for(command),[])
        self.assertEqual(errors_for(status),[])
        self.assertEqual(errors_for(query),[])
        self.assertNotIn('request_id',command)
        self.assertNotIn('trace_id',command)
        self.assertNotIn('owner_user_id',command)
        self.assertEqual(check_delete_command_status(command,status,actor),[])
        self.assertEqual(check_delete_status_query(query,status,actor),[])
        mismatch=copy.deepcopy(status)
        mismatch['client_action_id']='act_other'
        self.assertIn('DELETION_MISMATCH_CLIENT_ACTION_ID',check_delete_command_status(command,mismatch,actor))
        self.assertIn('DELETION_STATUS_QUERY_MISMATCH',check_delete_status_query(query,mismatch,actor))
        mismatch=copy.deepcopy(status)
        mismatch['owner_user_id']='user_other'
        self.assertIn('UNAUTHORIZED_DELETION_OWNER',check_delete_command_status(command,mismatch,actor))
        self.assertIn('UNAUTHORIZED_DELETION_STATUS_ACCESS',check_delete_status_query(query,mismatch,actor))
        other_actor=copy.deepcopy(actor)
        other_actor['owner_user_id']='user_other'
        self.assertIn('UNAUTHORIZED_DELETION_STATUS_ACCESS',check_delete_status_query(query,status,other_actor))
        unauthorized=copy.deepcopy(query)
        unauthorized['owner_user_id']='user_1'
        self.assertTrue(errors_for(unauthorized))
        another_query=copy.deepcopy(query)
        another_query['deletion_request_id']='del_other'
        self.assertIn('DELETION_STATUS_QUERY_MISMATCH',check_delete_status_query(another_query,status,actor))
        polling_actor=copy.deepcopy(actor)
        polling_actor['request_id']='req_status_poll_new'
        polling_actor['trace_id']='trace_status_poll_new'
        self.assertEqual(check_delete_status_query(query,status,polling_actor),[])
        succeeded=copy.deepcopy(status)
        succeeded.update(state='succeeded',backend_confirmed=True,completed_at='2026-01-01T00:00:01Z')
        self.assertEqual(errors_for(succeeded),[])
        succeeded['backend_confirmed']=False
        self.assertTrue(errors_for(succeeded))
        self.assertTrue(errors_for(fixture('invalid_delete_server_unknown_transport')))
        self.assertFalse(any(k in command for k in ('export_required','export_requested')))
        # After account deletion, the polling principal's validity is an unresolved Auth policy, never operation-ID-only access.

    def test_source_title_known_without_locator_not_verified_or_linkable(self):
        original=fixture('valid_unresolved_source_with_synthetic_display_title')
        self.assertEqual(errors_for(original),[])
        source=original['citations'][0]['source']
        self.assertEqual(source['display_title_origin'],'SYNTHETIC')
        self.assertIsNone(source['locator'])
        self.assertEqual(source['resolution_status'],'unresolved')
        self.assertEqual(source['attribution_status'],'unknown')
        self.assertNotIn('url',source)
        spoof=copy.deepcopy(original)
        spoof['citations'][0]['source']['display_title_origin']='source_record'
        self.assertIn('SYNTHETIC_DISPLAY_TITLE_CLAIMS_EXTERNAL_ORIGIN',errors_for(spoof))
        without_origin=copy.deepcopy(original)
        without_origin['citations'][0]['source'].pop('display_title_origin')
        self.assertTrue(errors_for(without_origin))
        blank=copy.deepcopy(original)
        blank['citations'][0]['source']['display_title']='   '
        self.assertTrue(errors_for(blank))
        anchor=fixture('valid_source_metadata_unresolved_book')
        self.assertIsNone(anchor['citations'][0]['source']['locator'])
        self.assertEqual(errors_for(anchor),[])
        # No conversion of book/transcript anchor to fabricated URL or guaranteed open action.



if __name__ == '__main__':
    unittest.main(verbosity=2)
