"""Independent tests for proposed, explicitly synthetic consumer boundaries."""
import copy
import json
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from f3_synthetic_consumer_oracle import (
    CATEGORIES, BoundaryDenied, outcome_fixture, bounded_context_fixture,
    source_projection_fixture, regression_fixture, benchmark_fixture,
    FixtureRateLimits, FixtureRateWindow, RunIdentity,
)

ROOT=Path(__file__).resolve().parents[3]
FIXTURE=ROOT/'packages/contracts/fixtures/f3-source-projection.synthetic.v0.json'


class EqualityProxy:
    def __init__(self, value): self.value=value
    def __hash__(self): return hash(self.value)
    def __eq__(self, other): return self.value == other

class SyntheticConsumerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=json.loads(FIXTURE.read_text(encoding='utf-8'))
        self.ids=tuple(x['id'] for x in self.fixture['sources'])
        self.rules={(c,a):{'outcome':'no_answer','disclaimer':None}
                    for c in CATEGORIES for a in (True,False)}
        # Explicit proposed fixture only; not a financial advice policy.
        self.rules['education',True]={'outcome':'answer','disclaimer':None}
        self.rules['personal_advice',True]={'outcome':'refusal','disclaimer':'fixture-personal-note'}
        self.rules['ambiguous',False]={'outcome':'clarification','disclaimer':None}
        self.identity=RunIdentity('fixture-provider','fixture-model','fixture-version','fixture-run')

    def deny(self, fn):
        with self.assertRaises(BoundaryDenied) as e: fn()
        self.assertEqual(str(e.exception),'SYNTHETIC_BOUNDARY_DENIED')

    def outcome(self,c,a, rules=None):
        return outcome_fixture({'id':'fixture-case','category':c,'answerable':a},
                    policy_version='fixture-policy-v1',rules=self.rules if rules is None else rules)

    def test_explicit_education_and_personal_labels_distinct_not_classifier(self):
        a=self.outcome('education',True); b=self.outcome('personal_advice',True)
        self.assertEqual((a['outcome'],b['outcome']),('answer','refusal'))
        self.assertFalse(a['approved'] or b['dispatch_allowed'])

    def test_ambiguous_and_out_of_source_distinct_fixture_outcomes(self):
        self.assertEqual(self.outcome('ambiguous',False)['outcome'],'clarification')
        self.assertEqual(self.outcome('out_of_source',False)['outcome'],'no_answer')

    def test_disclaimer_is_explicit_case_specific_not_global(self):
        self.assertIsNone(self.outcome('education',True)['disclaimer'])
        self.assertEqual(self.outcome('personal_advice',True)['disclaimer'],'fixture-personal-note')
        self.assertIsNone(self.outcome('out_of_source',False)['disclaimer'])

    def test_missing_rule_and_unanswerable_answer_denied(self):
        partial=dict(self.rules); del partial['education',True]
        self.deny(lambda:self.outcome('education',True,partial))
        bad=dict(self.rules); bad['out_of_source',False]={'outcome':'answer','disclaimer':None}
        self.deny(lambda:self.outcome('out_of_source',False,bad))

    def test_unknown_intent_and_bool_coercion_denied(self):
        self.deny(lambda:self.outcome('unknown',True))
        self.deny(lambda:self.outcome('education',1))
        self.deny(lambda:outcome_fixture({'id':'fixture-case','category':'education','answerable':True,'question':'private'},policy_version='fixture-policy',rules=self.rules))

    def project(self,claims=None,sources=None,ids=None):
        return source_projection_fixture(self.fixture['claims'] if claims is None else claims,
                    self.fixture['sources'] if sources is None else sources,
                    allowed_source_ids=self.ids if ids is None else ids)

    def test_four_source_projection_snapshots_and_explicit_origin(self):
        self.assertEqual(self.fixture['status'],'PROPOSED_NOT_APPROVED')
        self.assertEqual(self.project(),self.fixture['expected'])
        self.assertEqual({x['kind'] for x in self.project()['sources']}, {'book','website','transcript','unresolved'})

    def test_citation_claim_and_source_list_links_exact(self):
        r=self.project(); all_ids={s['id'] for s in r['sources']}
        self.assertEqual({x for c in r['claims'] for x in c['source_ids']},all_ids)
        self.assertTrue(all(s['href'] is None and not s['verified'] for s in r['sources']))

    def test_source_reason_preserved_not_invented(self):
        byid={s['id']:s for s in self.project()['sources']}
        self.assertEqual(byid['fixture-book']['reason'],'fixture-reason-book')
        self.assertIsNone(byid['fixture-unresolved']['reason'])
        self.assertIsNone(byid['fixture-unresolved']['locator'])

    def test_cross_scope_source_and_dangling_claim_denied(self):
        self.deny(lambda:self.project(ids=self.ids[:-1]))
        c=copy.deepcopy(self.fixture['claims']); c[0]['source_ids'].append('fixture-unknown')
        self.deny(lambda:self.project(claims=c))

    def test_duplicate_and_orphan_source_denied(self):
        self.deny(lambda:self.project(sources=self.fixture['sources']+[self.fixture['sources'][0]]))
        self.deny(lambda:self.project(claims=self.fixture['claims'][:1]))
        c=copy.deepcopy(self.fixture['claims']); c[0]['source_ids']*=2
        self.deny(lambda:self.project(claims=c))

    def test_forged_locator_or_unresolved_reason_denied(self):
        s=copy.deepcopy(self.fixture['sources']); s[0]['locator']={'url':'https://example.invalid'}
        self.deny(lambda:self.project(sources=s))
        s=copy.deepcopy(self.fixture['sources']); s[-1]['reason']='fixture-made-up'
        self.deny(lambda:self.project(sources=s))
        s=copy.deepcopy(self.fixture['sources']); s[1]['locator']={'page':True}
        self.deny(lambda:self.project(sources=s))

    def test_no_author_editor_speaker_promotion(self):
        s={x['id']:x for x in self.project()['sources']}
        self.assertIsNone(s['fixture-site']['credited_author_name'])
        self.assertIsNone(s['fixture-transcript']['credited_author_name'])
        self.assertEqual(s['fixture-book']['credited_author_name'],'fixture-author')

    def test_projection_stable_order_and_no_mutation(self):
        old=copy.deepcopy(self.fixture)
        self.assertEqual(self.project(sources=list(reversed(self.fixture['sources']))),self.project())
        self.assertEqual(old,self.fixture)

    def context(self, selected=('fixture-p1',), allowed=('fixture-p1',), limit=1):
        base={'release_id':'fixture-r1','payload_version':'fixture-v1','source_type':'book',
              'credited_author_name':'fixture-author','editorial_supervisor_name':None,
              'speaker_name':None,'content_authority_type':'fixture-direct','attribution_status':'fixture-marked'}
        points=[dict(base,id='fixture-p1'),dict(base,id='fixture-p2')]
        rows=[{'owner':o,'conversation':'fixture-conv','message':m,'seq':1}
              for o,m in [('fixture-a','fixture-msg-a'),('fixture-b','fixture-msg-b')]]
        return bounded_context_fixture(rows,points,scope={'owner':'fixture-a','conversation':'fixture-conv','current':'fixture-current','max_history':1},
            selection={'release_id':'fixture-r1','payload_version':'fixture-v1','expected_count':2,
                       'source_types':('book',),'authority_types':('fixture-direct',)},
            allowed_point_ids=allowed,context_limit=limit,selected_ids=selected)

    def test_context_history_and_retrieved_fixture_scope(self):
        r=self.context(); self.assertEqual(r['history'],('fixture-msg-a',)); self.assertEqual(r['retrieved_point_ids'],('fixture-p1',))
        self.assertFalse(r['source_verified'] or r['dispatch_allowed'])

    def test_context_foreign_and_duplicate_points_denied(self):
        self.deny(lambda:self.context(selected=('fixture-p2',)))
        self.deny(lambda:self.context(selected=('fixture-p1','fixture-p1'),limit=2))

    def test_context_bound_zero_and_unknown_point_denied(self):
        self.assertEqual(self.context(selected=(),limit=0)['retrieved_point_ids'],())
        self.deny(lambda:self.context(limit=0))
        self.deny(lambda:self.context(selected=('fixture-missing',),allowed=('fixture-missing',)))

    def test_regression_match_and_mismatch_case_ids(self):
        e={'fixture-a':'answer','fixture-b':'no_answer'}
        r=regression_fixture(e,e); self.assertEqual(r['matched'],2); self.assertFalse(r['actual_golden_set'])
        r=regression_fixture(e,{'fixture-a':'refusal','fixture-b':'no_answer'}); self.assertEqual(r['mismatch_ids'],('fixture-a',))

    def test_regression_missing_extra_invalid_case_denied(self):
        e={'fixture-a':'answer'}
        for o in ({},{'fixture-a':'answer','fixture-b':'answer'},{'fixture-a':'unknown'}):
            self.deny(lambda:regression_fixture(e,o))

    def samples(self):
        return [{'case_id':f'fixture-{i}','identity':self.identity,'latency_ms':t,'cost_units':c,'matched':m}
                for i,(t,c,m) in enumerate([(10,3,True),(40,7,False),(20,1,True)])]

    def test_benchmark_summary_only_supplied_synthetic_values(self):
        r=benchmark_fixture(self.samples(),identity=self.identity)
        self.assertEqual((r['median_fixture_latency_ms'],r['max_fixture_latency_ms'],r['total_fixture_cost_units'],r['matched']),(20,40,11,2))
        self.assertFalse(r['measured_live'] or r['provider_frozen'] or r['approved'])

    def test_benchmark_duplicate_identity_and_invalid_measure_denied(self):
        s=self.samples(); self.deny(lambda:benchmark_fixture(s+[s[0]],identity=self.identity))
        for field,value in [('latency_ms',-1),('cost_units',True),('matched',1),('identity',None)]:
            s=self.samples(); s[0][field]=value; self.deny(lambda:benchmark_fixture(s,identity=self.identity))

    def test_rate_user_cap_shared_across_ip(self):
        w=FixtureRateWindow(FixtureRateLimits(2,5,10))
        self.assertTrue(w.admit(owner='fixture-a',ip='192.0.2.1',now=0))
        self.assertTrue(w.admit(owner='fixture-a',ip='192.0.2.2',now=0))
        self.assertFalse(w.admit(owner='fixture-a',ip='192.0.2.3',now=0))
        self.assertTrue(w.admit(owner='fixture-b',ip='192.0.2.3',now=0))

    def test_rate_ip_cap_shared_across_owners_and_no_partial_consume(self):
        w=FixtureRateWindow(FixtureRateLimits(1,1,10))
        self.assertTrue(w.admit(owner='fixture-a',ip='192.0.2.1',now=0))
        self.assertFalse(w.admit(owner='fixture-b',ip='192.0.2.1',now=0))
        self.assertTrue(w.admit(owner='fixture-b',ip='192.0.2.2',now=0))

    def test_rate_window_reset_and_clock_rollback(self):
        w=FixtureRateWindow(FixtureRateLimits(1,1,10)); a=dict(owner='fixture-a',ip='192.0.2.1')
        self.assertTrue(w.admit(**a,now=0)); self.assertFalse(w.admit(**a,now=9)); self.assertTrue(w.admit(**a,now=10))
        self.deny(lambda:w.admit(**a,now=9))

    def test_rate_parallel_fixture_bound_atomic(self):
        w=FixtureRateWindow(FixtureRateLimits(3,4,10))
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:w.admit(owner='fixture-a',ip='192.0.2.1',now=0),range(32)))
        self.assertEqual(sum(results),3)

    def test_rate_ipv6_canonical_and_invalid_inputs(self):
        w=FixtureRateWindow(FixtureRateLimits(3,1,10))
        self.assertTrue(w.admit(owner='fixture-a',ip='2001:db8::1',now=0))
        self.assertFalse(w.admit(owner='fixture-b',ip='2001:0db8:0:0:0:0:0:1',now=0))
        self.deny(lambda:w.admit(owner='fixture-a',ip='127.0.0.1',now=0))
        self.deny(lambda:FixtureRateLimits(True,1,1))

    def test_selected_boundaries_never_call_network_or_subprocess(self):
        with patch('socket.create_connection',side_effect=AssertionError('NO_NETWORK')) as net, \
             patch('subprocess.Popen',side_effect=AssertionError('NO_PROCESS')) as proc:
            self.project(); self.context(); self.outcome('education',True)
            benchmark_fixture(self.samples(),identity=self.identity)
            regression_fixture({'fixture-a':'answer'},{'fixture-a':'answer'})
            net.assert_not_called(); proc.assert_not_called()

    def test_rate_ipv6_scope_suffix_cannot_bypass_ip_counter(self):
        w=FixtureRateWindow(FixtureRateLimits(3,1,10))
        self.assertTrue(w.admit(owner='fixture-a',ip='2001:db8::1',now=0))
        for ip in ('2001:db8::1%fixture-a','2001:db8::1%fixture-b'):
            self.deny(lambda:w.admit(owner='fixture-b',ip=ip,now=0))
        self.assertFalse(w.admit(owner='fixture-b',ip='2001:db8::1',now=0))

    def test_benchmark_identity_equality_proxy_denied(self):
        class Impostor:
            def __eq__(self,other): return True
        s=self.samples(); s[0]['identity']=Impostor()
        self.deny(lambda:benchmark_fixture(s,identity=self.identity))

    def test_benchmark_unrepresentable_median_is_fixed_denial(self):
        s=self.samples()[:2]
        for sample in s: sample['latency_ms']=10**1000
        self.deny(lambda:benchmark_fixture(s,identity=self.identity))

    def test_context_unexpected_selection_keyword_has_fixed_error(self):
        self.deny(lambda:bounded_context_fixture([],[],
            scope={'owner':'fixture-a','conversation':'fixture-c','current':'fixture-current','max_history':0},
            selection={'private_canary':'not-a-field'},allowed_point_ids=(),context_limit=0,selected_ids=()))

    def test_outcome_category_equality_proxy_denied(self):
        class Impostor:
            def __eq__(self,other): return True
            def __hash__(self): return hash('education')
        self.deny(lambda:self.outcome(Impostor(),True))

    def test_rule_outcome_must_be_an_exact_string(self):
        bad=copy.deepcopy(self.rules)
        bad['education',True]['outcome']=EqualityProxy('answer')
        self.deny(lambda:self.outcome('education',True,bad))

    def test_rule_category_key_must_be_an_exact_string(self):
        bad=dict(self.rules)
        bad[(EqualityProxy('education'),True)]=bad.pop(('education',True))
        self.deny(lambda:self.outcome('education',True,bad))

    def test_source_kind_must_be_an_exact_string(self):
        sources=copy.deepcopy(self.fixture['sources'])
        sources[0]['kind']=EqualityProxy(sources[0]['kind'])
        self.deny(lambda:self.project(sources=sources))

    def test_regression_observed_id_must_be_an_exact_string(self):
        self.deny(lambda:regression_fixture({'fixture-a':'answer'},
            {EqualityProxy('fixture-a'):'answer'}))

    def test_regression_outcomes_must_be_exact_strings(self):
        self.deny(lambda:regression_fixture({'fixture-a':'answer'},
            {'fixture-a':EqualityProxy('answer')}))
        self.deny(lambda:regression_fixture({'fixture-a':EqualityProxy('answer')},
            {'fixture-a':'answer'}))
