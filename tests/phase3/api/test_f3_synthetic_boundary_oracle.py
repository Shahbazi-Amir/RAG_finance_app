"""Offline synthetic assertions; not a runtime or product acceptance suite."""
import copy
import unittest
from unittest.mock import patch

from f3_synthetic_boundary_oracle import (
    BoundaryDenied, RunIdentity, SyntheticLimits, inspect_inventory,
    capability_receipt, select_fixture_points, fallback_fixture,
    describe_fixture, minimal_fixture_payload, context_fixture,
    budget_fixture, cost_receipt_fixture,
)



class EqualityProxy:
    def __init__(self, value): self.value=value
    def __hash__(self): return hash(self.value)
    def __eq__(self, other): return self.value == other

class SyntheticBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.base = {'release_id':'fixture-r1','payload_version':'fixture-p1',
                     'credited_author_name':None,'editorial_supervisor_name':None,
                     'speaker_name':None,'attribution_status':'fixture-marked'}
        self.points = [
            dict(self.base,id='fixture-book',source_type='book',
                 credited_author_name='fixture-author',content_authority_type='fixture-direct'),
            dict(self.base,id='fixture-site',source_type='website',
                 editorial_supervisor_name='fixture-author',content_authority_type='fixture-editorial'),
            dict(self.base,id='fixture-talk',source_type='transcript',
                 speaker_name='fixture-author',content_authority_type='fixture-speaker'),
            dict(self.base,id='fixture-unknown',source_type='book',
                 credited_author_name='fixture-author',content_authority_type='fixture-unknown',
                 attribution_status='fixture-unknown'),
        ]
        self.args = {'release_id':'fixture-r1','payload_version':'fixture-p1','expected_count':4}
        self.run = RunIdentity('fixture-provider','fixture-model','fixture-version','fixture-run')
        self.limits = SyntheticLimits(10,8,3,12)  # arbitrary synthetic inputs, not policy

    def denied(self, f):
        with self.assertRaises(BoundaryDenied) as err:
            f()
        self.assertEqual(str(err.exception),'SYNTHETIC_BOUNDARY_DENIED')

    def test_inventory_matches_exact_count_and_schema_not_readiness(self):
        r=inspect_inventory(self.points,**self.args)
        self.assertEqual(r['point_count'],4)
        self.assertTrue(r['inventory_match'])
        self.assertFalse(r['approved'] or r['knowledge_ready'] or r['dispatch_allowed'])

    def test_inventory_count_missing_extra_duplicate(self):
        for points in (self.points[:-1],self.points+[self.points[0]],self.points[:-1]+[self.points[0]]):
            self.denied(lambda: inspect_inventory(points,**self.args))

    def test_inventory_release_and_payload_version_drift(self):
        for k in ('release_id','payload_version'):
            points=copy.deepcopy(self.points);points[0][k]='fixture-other'
            self.denied(lambda:inspect_inventory(points,**self.args))

    def test_inventory_missing_authority_and_extra_untrusted_fields(self):
        for k in self.base:
            points=copy.deepcopy(self.points);del points[0][k]
            self.denied(lambda:inspect_inventory(points,**self.args))
        points=copy.deepcopy(self.points);points[0]['system_instruction']='PRIVATE_CANARY'
        self.denied(lambda:inspect_inventory(points,**self.args))

    def test_health_app_and_knowledge_independent(self):
        for app in (False,True):
            for match in (False,True):
                receipt=capability_receipt(app_ready=app,inventory_match=match)
                self.assertEqual(receipt['app_ready'],app)
                self.assertFalse(receipt['knowledge_ready'])
                self.assertEqual(receipt['retrieval'],receipt['generation'])
                self.assertEqual(receipt['generation'],'unavailable')

    def select(self,**kwargs):
        params={'source_types':('book','website','transcript'),
                'authority_types':('fixture-direct','fixture-editorial','fixture-speaker','fixture-unknown')}
        return select_fixture_points(self.points,**self.args,**(params|kwargs))

    def test_source_filter_and_authority_intersection(self):
        self.assertEqual(self.select(source_types=('book',),authority_types=('fixture-direct',)),('fixture-book',))
        self.assertEqual(self.select(source_types=('website',),authority_types=('fixture-direct',)),())

    def test_direct_author_not_editor_speaker_or_unknown(self):
        self.assertEqual(self.select(direct_author='fixture-author'),('fixture-book',))
        self.assertEqual(self.select(direct_author='fixture-unlisted'),())

    def test_filter_missing_or_unrecognized_scope_denied(self):
        for val in ((),('unknown',),['book']):
            self.denied(lambda:self.select(source_types=val))
        self.denied(lambda:self.select(authority_types=()))

    def test_fallback_only_explicit_fixture_edge(self):
        args=dict(component='fixture-optional',allowed_edges={'fixture-optional':'fixture-secondary'},required_components=())
        self.assertEqual(fallback_fixture(**args,failed=False),'fixture-optional')
        self.assertEqual(fallback_fixture(**args,failed=True),'fixture-secondary')
        self.denied(lambda:fallback_fixture(**(args|{'allowed_edges':{}}),failed=True))

    def test_required_component_never_falls_back(self):
        self.denied(lambda:fallback_fixture(component='fixture-core',failed=True,
                    allowed_edges={'fixture-core':'fixture-secondary'},required_components=('fixture-core',)))

    def test_fallback_same_component_and_unknown_policy_denied(self):
        for policy in (None,{'fixture-a':'fixture-a'}):
            self.denied(lambda:fallback_fixture(component='fixture-a',failed=True,
                        allowed_edges=policy,required_components=()))

    def test_two_offline_receipt_readers_same_interface(self):
        identity=self.run
        class ReaderA:
            def describe_fixture(self):return identity
        class ReaderB:
            def describe_fixture(self):return RunIdentity(identity.provider,identity.model,identity.version,identity.run_id)
        for reader in (ReaderA(),ReaderB()):
            self.assertEqual(describe_fixture(reader,expected=identity),identity)

    def test_wrong_model_run_version_or_provider_denied(self):
        from dataclasses import replace
        for field in ('model','run_id','version','provider'):
            wrong=replace(self.run,**{field:'fixture-other'})
            class Reader:
                def describe_fixture(self):return wrong
            self.denied(lambda:describe_fixture(Reader(),expected=self.run))

    def test_unversioned_identity_never_valid(self):
        for invalid in ('',None,'model-without-fixture-label','fixture-','fixture-  '):
            self.denied(lambda:RunIdentity('fixture-provider','fixture-model',invalid,'fixture-run'))

    def test_minimal_metadata_drops_all_nonrequired_fields(self):
        record={'fixture_context_id':'fixture-c','fixture_policy_id':'fixture-p',
                'owner_id':'PRIVATE_OWNER','raw_history':'PRIVATE_HISTORY','token':'PRIVATE_TOKEN',
                'question':'PRIVATE_QUESTION'}
        result=minimal_fixture_payload(record,allow_fields=('fixture_context_id','fixture_policy_id'))
        self.assertEqual(result,{'fixture_context_id':'fixture-c','fixture_policy_id':'fixture-p'})
        self.assertNotIn('PRIVATE',repr(result))

    def test_data_minimization_allowlist_cannot_include_secrets(self):
        record={'fixture_context_id':'fixture-c','token':'fixture-secret'}
        for allowed in (('token',),('fixture_context_id','token'),(),('fixture_context_id','fixture_context_id'),(['fixture_context_id'],)):
            self.denied(lambda:minimal_fixture_payload(record,allow_fields=allowed))

    def history_rows(self):
        return [{'owner':'fixture-a','conversation':'fixture-c','message':f'fixture-m{i}','seq':i} for i in (3,1,2)]+[
            {'owner':'fixture-b','conversation':'fixture-c','message':'fixture-foreign','seq':99},
            {'owner':'fixture-a','conversation':'fixture-d','message':'fixture-other','seq':100}]

    def test_context_owner_conversation_order_and_bound(self):
        result=context_fixture(self.history_rows(),owner='fixture-a',conversation='fixture-c',current='fixture-current',max_history=2)
        self.assertEqual(result['history'],('fixture-m2','fixture-m3'))
        self.assertFalse(result['dispatch_allowed'])
        self.assertNotIn('foreign',repr(result))
        self.assertNotIn('other',repr(result))

    def test_context_zero_history_does_not_return_all(self):
        self.assertEqual(context_fixture(self.history_rows(),owner='fixture-a',conversation='fixture-c',current='fixture-current',max_history=0)['history'],())

    def test_context_duplicate_current_or_sequence_denied(self):
        args=dict(owner='fixture-a',conversation='fixture-c',current='fixture-current',max_history=2)
        for extra in (self.history_rows()[0],dict(self.history_rows()[0],message='fixture-current',seq=99),dict(self.history_rows()[0],message='fixture-new')):
            self.denied(lambda:context_fixture(self.history_rows()+[extra],**args))

    def budget(self,**kw):
        args=dict(limits=self.limits,input_tokens=4,output_tokens=6,cost_units=8,used_requests=2,used_cost_units=4)
        return budget_fixture(**(args|kw))

    def test_budget_inclusive_explicit_boundaries(self):
        self.assertTrue(self.budget())
        for kw in ({'output_tokens':7},{'cost_units':9},{'used_requests':3},{'used_cost_units':5}):
            self.assertFalse(self.budget(**kw))

    def test_no_default_limits_or_boolean_numeric_values(self):
        for v in (None,True,-1,1.5):
            self.denied(lambda:self.budget(cost_units=v))
        self.denied(lambda:self.budget(limits=None))
        self.denied(lambda:SyntheticLimits(True,1,1,1))

    def test_zero_limits_deny_new_request(self):
        self.assertFalse(self.budget(limits=SyntheticLimits(0,0,0,0),input_tokens=0,output_tokens=0,cost_units=0,used_requests=0,used_cost_units=0))

    def cost(self,**kw):
        args=dict(identity=self.run,outcome='completed',input_tokens=4,output_tokens=6,cost_units=8,price_version='fixture-price')
        return cost_receipt_fixture(**(args|kw))

    def test_cost_receipt_model_version_and_units_not_billable(self):
        r=self.cost()
        self.assertEqual((r['total_tokens'],r['cost_units'],r['model_version']),(10,8,self.run.version))
        self.assertFalse(r['approved'] or r['billable'])

    def test_unknown_failed_cancelled_not_successful_cost(self):
        for outcome in ('unknown','failed','cancelled'):
            self.denied(lambda:self.cost(outcome=outcome))

    def test_cost_missing_price_version_or_invalid_numbers_denied(self):
        for kw in ({'price_version':None},{'cost_units':-1},{'input_tokens':True}):
            self.denied(lambda:self.cost(**kw))

    def test_no_network_subprocess_or_provider_execution(self):
        with patch('socket.create_connection',side_effect=AssertionError('NETWORK')) as sock, \
             patch('subprocess.Popen',side_effect=AssertionError('SPAWN')) as spawn:
            self.select(direct_author='fixture-author');self.budget();self.cost()
            sock.assert_not_called();spawn.assert_not_called()


    def test_fixture_identifiers_reject_embedded_control_characters(self):
        for invalid in ('fixture-line\nbreak','fixture-tab\tvalue','fixture-\x00value','fixture-\u202evalue'):
            self.denied(lambda:RunIdentity('fixture-provider','fixture-model',invalid,'fixture-run'))

    def test_inventory_version_is_exact_string_not_equality_proxy(self):
        class Impostor:
            def __eq__(self, other): return True
        for field in ('release_id','payload_version','source_type','content_authority_type','attribution_status'):
            points=copy.deepcopy(self.points); points[0][field]=Impostor()
            self.denied(lambda:inspect_inventory(points,**self.args))

    def test_fallback_cannot_accept_duplicate_required_components(self):
        self.denied(lambda:fallback_fixture(component='fixture-optional',failed=False,
                    allowed_edges={},required_components=('fixture-core','fixture-core')))

    def test_inventory_rejects_non_string_field_key(self):
        points=copy.deepcopy(self.points)
        points[0][EqualityProxy('id')]=points[0].pop('id')
        self.denied(lambda:inspect_inventory(points,**self.args))

    def test_filter_rejects_non_string_source_selector(self):
        self.denied(lambda:self.select(source_types=(EqualityProxy('book'),)))

    def test_filter_rejects_non_string_authority_selector(self):
        self.denied(lambda:self.select(authority_types=(EqualityProxy('fixture-direct'),)))

    def test_metadata_rejects_non_string_record_key(self):
        record={EqualityProxy('fixture_context_id'):'fixture-c'}
        self.denied(lambda:minimal_fixture_payload(record,allow_fields=('fixture_context_id',)))

    def test_cost_receipt_rejects_non_string_outcome(self):
        self.denied(lambda:cost_receipt_fixture(identity=self.run,outcome=EqualityProxy('completed'),
                    input_tokens=1,output_tokens=1,cost_units=1,price_version='fixture-price'))

if __name__=='__main__':
    unittest.main(verbosity=2)
