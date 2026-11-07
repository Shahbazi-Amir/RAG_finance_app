"""HISTORY-01 synthetic contract checks: additive product.v1 DTOs, no DB/Auth/API."""
import copy
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from test_contracts import SCHEMA, FIXTURES, fixture, errors_for
from semantics import canonical_request_fingerprint, check_request_receipt, check_idempotency_history
from history_semantics import (
    canonical_create_fingerprint, check_create_receipt, check_create_replay,
    check_conversation_page, check_messages_page, check_status_query,
    check_status_progression, make_test_cursor, verify_test_cursor,
)


class HistoryContractTests(unittest.TestCase):
    def setUp(self):
        self.actor = fixture('valid_trusted_actor_context')
        self.actor['request_id'] = 'req_status'
        self.actor['trace_id'] = 'trace_status'

    def status(self, state='not_found'):
        value = fixture('valid_history_status_not_found')
        value['status'] = state
        if state != 'not_found':
            value['resolved_conversation_id'] = 'conv_1'
            value['message_id'] = 'msg_1'
        if state in ('attempt_pending', 'attempt_unknown', 'answer_committed', 'failed', 'cancelled'):
            value.update(attempt_id='attempt_1', attempt_request_id='req_1',
                         attempt_trace_id='trace_1', reserved_answer_id='ans_1')
        if state == 'answer_committed':
            value.update(answer_id='ans_1', answer=fixture('valid_answer_unresolved_source'))
        return value

    def test_historical_cases_unchanged_and_schema_additive(self):
        self.assertEqual(len(SCHEMA['oneOf']), 24)
        self.assertEqual(FIXTURES['fixture_set_version'], 'product.v1.regression.3')
        self.assertEqual(len(FIXTURES['cases']), 112)
        self.assertEqual(len([x for x in FIXTURES['cases'] if x['case_id'].startswith('valid_history')]), 7)
        self.assertEqual(len([x for x in FIXTURES['cases'] if x['case_id'].startswith('invalid_history')]), 7)
        Draft202012Validator.check_schema(SCHEMA)
        for case in FIXTURES['cases']:
            with self.subTest(case=case['case_id']):
                self.assertEqual(errors_for(case['document']) == [], case['expected_valid'])

    def test_create_empty_conversation_actor_fingerprint_and_replay(self):
        req = fixture('valid_history_create_request')
        created = fixture('valid_history_create_receipt')
        created.update(request_id=self.actor['request_id'], trace_id=self.actor['trace_id'])
        created['payload_sha256'] = canonical_create_fingerprint(req)
        self.assertEqual(errors_for(req), [])
        self.assertEqual(errors_for(created), [])
        self.assertEqual(check_create_receipt(req, created, self.actor), [])
        replay = copy.deepcopy(created)
        replay.update(disposition='replayed', request_id='req_retry', trace_id='trace_retry')
        actor = {**self.actor, 'request_id':'req_retry','trace_id':'trace_retry'}
        self.assertEqual(check_create_receipt(req, replay, actor), [])
        self.assertEqual(check_create_replay(created, replay), [])
        bad = copy.deepcopy(replay)
        bad['conversation']['conversation_id'] = 'conv_new_unauthorized'
        self.assertIn('HISTORY_CREATE_REPLAY_DUPLICATE_CONVERSATION',check_create_replay(created,bad))
        changed = copy.deepcopy(req)
        changed['title'] = 'different'
        self.assertIn('HISTORY_CREATE_FINGERPRINT_MISMATCH',check_create_receipt(changed, created,self.actor))

    def test_create_identity_spoof_and_trace_and_keys(self):
        req = fixture('valid_history_create_request')
        rec = fixture('valid_history_create_receipt')
        rec.update(request_id=self.actor['request_id'], trace_id=self.actor['trace_id'])
        rec['payload_sha256'] = canonical_create_fingerprint(req)
        other = {**self.actor, 'owner_user_id':'another_user'}
        self.assertIn('HISTORY_OWNER_CONTEXT_MISMATCH',check_create_receipt(req,rec,other))
        rec['trace_id']='wrong_trace'
        self.assertIn('HISTORY_CURRENT_TRACE_MISMATCH',check_create_receipt(req,rec,self.actor))
        req['idempotency_key']='other_key_12345'
        self.assertIn('HISTORY_CREATE_REQUEST_MISMATCH',check_create_receipt(req,rec,self.actor))
        req['owner_user_id']='user_1'  # forged client identity rejected by schema
        self.assertNotEqual(errors_for(req),[])

    def test_owner_bounded_conversation_list_and_total_order(self):
        query = fixture('valid_history_list_query')
        one = fixture('valid_conversation')
        two = copy.deepcopy(one)
        two.update(conversation_id='conv_2',created_at='2026-01-02T00:00:00Z',updated_at='2026-01-02T00:00:00Z')
        page = {'kind':'conversation_page','contract_version':'product.v1','scope_user_id':'user_1',
                'items':[two,one],'page':{'limit':20,'has_more':False,'next_cursor':None}}
        self.assertEqual(errors_for(page), [])
        self.assertEqual(check_conversation_page(query,page,self.actor),[])
        self.assertIn('HISTORY_CONVERSATION_ORDER',check_conversation_page(query,{**page,'items':[one,two]},self.actor))
        cross = copy.deepcopy(page);cross['items'][0]['owner_user_id']='user_other'
        self.assertIn('HISTORY_CROSS_USER_CONVERSATION',check_conversation_page(query,cross,self.actor))
        dup=copy.deepcopy(page);dup['items'][0]['conversation_id']=one['conversation_id']
        self.assertIn('HISTORY_DUPLICATE_CONVERSATION',check_conversation_page(query,dup,self.actor))
        hidden=copy.deepcopy(page);hidden['items'][0]['state']='deletion_requested'
        self.assertIn('HISTORY_DELETION_REQUESTED_VISIBLE',check_conversation_page(query,hidden,self.actor))
        self.assertIn('HISTORY_PAGE_OWNER_MISMATCH',check_conversation_page(query,page,{**self.actor,'owner_user_id':'user_other'}))

    def test_message_page_links_answer_user_and_sort_order(self):
        query=fixture('valid_history_messages_query')
        user=fixture('valid_user_message')
        assistant=fixture('valid_assistant_message')
        answer=fixture('valid_answer_unresolved_source')
        assistant['created_at']='2026-01-01T00:00:02Z'
        page=fixture('valid_history_messages_page');page.update(items=[user,assistant],answers=[answer])
        self.assertEqual(errors_for(page), [])
        self.assertEqual(check_messages_page(query,page,self.actor), [])
        reverse=copy.deepcopy(page);reverse['items'].reverse()
        self.assertIn('HISTORY_MESSAGES_ORDER',check_messages_page(query,reverse,self.actor))
        cross=copy.deepcopy(page);cross['items'][0]['owner_user_id']='user_other'
        self.assertIn('HISTORY_CROSS_USER_MESSAGE',check_messages_page(query,cross,self.actor))
        missing=copy.deepcopy(page);missing['answers']=[]
        self.assertIn('HISTORY_MISSING_OR_UNRELATED_ANSWER',check_messages_page(query,missing,self.actor))
        bad=copy.deepcopy(page);bad['answers'][0]['message_id']='msg_other'
        self.assertIn('HISTORY_ANSWER_MESSAGE_MISMATCH',check_messages_page(query,bad,self.actor))
        other_actor={**self.actor,'owner_user_id':'user_other'}
        self.assertIn('HISTORY_MESSAGES_OWNER_MISMATCH',check_messages_page(query,page,other_actor))
        wrong_query=copy.deepcopy(query);wrong_query['conversation_id']='conv_other'
        self.assertIn('HISTORY_MESSAGES_CONVERSATION_MISMATCH',check_messages_page(wrong_query,page,self.actor))

    def test_status_all_t1_t2_t3_cases_and_unknown_not_answer(self):
        query=fixture('valid_history_status_query')
        for state in ('not_found','persisted','attempt_pending','attempt_unknown','answer_committed','failed','cancelled'):
            with self.subTest(state=state):
                obj=self.status(state)
                self.assertEqual(errors_for(obj),[])
                self.assertEqual(check_status_query(query,obj,self.actor),[])
        obj=self.status('attempt_unknown'); obj['answer_id']='ans_fake'
        self.assertNotEqual(errors_for(obj),[])
        self.assertIn('HISTORY_UNCOMMITTED_ANSWER_CLAIM',check_status_query(query,obj,self.actor))
        committed=self.status('answer_committed');committed['answer']['trace_id']='another_attempt_trace'
        self.assertIn('HISTORY_FINAL_ANSWER_LINKAGE',check_status_query(query,committed,self.actor))
        obj=self.status('not_found');obj['message_id']='msg_leaked'
        self.assertIn('HISTORY_NOT_FOUND_HAS_PERSISTENCE',check_status_query(query,obj,self.actor))

    def test_status_scope_crossuser_enumeration_and_attempt_trace(self):
        query=fixture('valid_history_status_query')
        obj=self.status('attempt_pending')
        self.assertEqual(check_status_query(query,obj,self.actor),[])
        self.assertNotEqual(obj['request_id'],obj['attempt_request_id'])
        other={**self.actor,'owner_user_id':'user_other'}
        self.assertIn('HISTORY_STATUS_UNAUTHORIZED',check_status_query(query,obj,other))
        obj2=copy.deepcopy(obj);obj2['trace_id']='req_unknown'
        self.assertIn('HISTORY_STATUS_CURRENT_TRACE_MISMATCH',check_status_query(query,obj2,self.actor))
        different=copy.deepcopy(query);different['idempotency_key']='another_key_123'
        self.assertIn('HISTORY_STATUS_SCOPE_MISMATCH',check_status_query(different,obj,self.actor))
        forged=copy.deepcopy(query);forged['owner_user_id']='user_1'
        self.assertNotEqual(errors_for(forged),[])
        forged['requested_conversation_id']='conv_other'
        self.assertNotEqual(errors_for(forged),[])

    def test_crash_t1_t2_t3_recovery_and_no_implicit_model_retry(self):
        not_found=self.status()
        persisted=self.status('persisted')
        pending=self.status('attempt_pending')
        unknown=self.status('attempt_unknown')
        committed=self.status('answer_committed')
        self.assertEqual(check_status_progression(not_found,persisted),[])
        self.assertEqual(check_status_progression(persisted,pending),[])
        self.assertEqual(check_status_progression(pending,unknown),[])
        self.assertEqual(check_status_progression(pending,committed),[])
        self.assertIn('HISTORY_ILLEGAL_STATUS_TRANSITION',check_status_progression(unknown,pending))
        self.assertIn('HISTORY_ILLEGAL_STATUS_TRANSITION',check_status_progression(unknown,committed))
        self.assertEqual(check_status_progression(unknown,committed,reconciled_from_db=True),[])
        self.assertIn('HISTORY_ILLEGAL_STATUS_TRANSITION',check_status_progression(committed,pending))
        changed=copy.deepcopy(committed);changed['message_id']='new_msg'
        self.assertIn('HISTORY_REPLAY_DUPLICATE_MESSAGE',check_status_progression(pending,changed))
        changed=copy.deepcopy(unknown);changed['attempt_id']='attempt_2'
        self.assertIn('HISTORY_ATTEMPT_REPLACED_SILENTLY',check_status_progression(pending,changed))
        changed=copy.deepcopy(unknown);changed['reserved_answer_id']='ans_2'
        self.assertIn('HISTORY_RESERVATION_CHANGED',check_status_progression(pending,changed))

    def test_pagination_cursor_tamper_owner_resource_expiry_and_query(self):
        secret=b'local-test-only-cursor-key-not-production'
        payload={'owner':'user_1','resource':'conversations','conversation_id':None,'limit':20,
                 'anchor':['2026-01-02T00:00:00Z','conv_2'],
                 'last':['2026-01-01T00:00:00Z','conv_1'],'exp':2000000000}
        token=make_test_cursor(payload,secret)
        ctx={'owner':'user_1','resource':'conversations','conversation_id':None,'limit':20,'now_epoch':1999999999}
        self.assertIsNone(verify_test_cursor(token,secret,**ctx))
        self.assertEqual(verify_test_cursor(token,secret,**{**ctx,'owner':'user_other'}),'HISTORY_CURSOR_SCOPE_MISMATCH')
        self.assertEqual(verify_test_cursor(token,secret,**{**ctx,'resource':'messages'}),'HISTORY_CURSOR_SCOPE_MISMATCH')
        self.assertEqual(verify_test_cursor(token,secret,**{**ctx,'limit':100}),'HISTORY_CURSOR_SCOPE_MISMATCH')
        self.assertEqual(verify_test_cursor(token,secret,**{**ctx,'now_epoch':2000000000}),'HISTORY_CURSOR_EXPIRED')
        self.assertEqual(verify_test_cursor(token[:-2]+'AB',secret,**ctx),'HISTORY_CURSOR_INVALID')
        self.assertEqual(verify_test_cursor(token,secret+b'other',**ctx),'HISTORY_CURSOR_INVALID')
        msg_payload={**payload,'resource':'messages','conversation_id':'conv_1'}
        msg_token=make_test_cursor(msg_payload,secret)
        self.assertIsNone(verify_test_cursor(msg_token,secret,**{**ctx,'resource':'messages','conversation_id':'conv_1'}))
        self.assertEqual(verify_test_cursor(msg_token,secret,**{**ctx,'resource':'messages','conversation_id':'conv_other'}),'HISTORY_CURSOR_SCOPE_MISMATCH')

    def test_existing_send_receipt_idempotency_and_t1_are_preserved(self):
        request=fixture('valid_request_new_conversation')
        created=fixture('valid_receipt_new_conversation_allocated')
        actor=fixture('valid_trusted_actor_context')
        self.assertEqual(created['payload_sha256'],canonical_request_fingerprint(request))
        self.assertEqual(check_request_receipt(request,created,actor),[])
        replay=copy.deepcopy(created)
        replay.update(disposition='replayed',request_id='req_retry',trace_id='trace_retry')
        self.assertEqual(check_request_receipt(request,replay,{**actor,'request_id':'req_retry','trace_id':'trace_retry'}),[])
        self.assertEqual(check_idempotency_history([created,replay]),[])
        bad=copy.deepcopy(created);bad.update(disposition='created',message_id='msg_duplicate')
        self.assertIn('RETRY_MUST_REPLAY_SAME_PERSISTED_MESSAGE',check_idempotency_history([created,bad]))
        conflict=copy.deepcopy(created);conflict.update(disposition='conflict',message_id=None,
                      resolved_conversation_id=None,payload_sha256='f'*64,
                      error={'category':'validation','code':'IDEMPOTENCY_CONFLICT','message':'Conflict'})
        self.assertEqual(check_idempotency_history([created,conflict]),[])
        self.assertEqual(errors_for(conflict),[])


if __name__=='__main__':
    unittest.main(verbosity=2)
