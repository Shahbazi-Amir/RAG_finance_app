"""Deterministic offline contract tests; no policy is approved by these."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import unittest

from src.phase3.rag_runtime.offline_resource_contract import (
    CacheScope, DraftBounds, OfflineAdmissionLab, OfflineContractDenied,
    draft_cache_matches, draft_cache_witness,
)


class OfflineResourceContractTests(unittest.TestCase):
    def setUp(self):
        self.scope = CacheScope("a"*64, "b"*64, "c"*64, "fa")
        self.bounds = DraftBounds(10, 2, 3, 4, 30, 10, 100, 2, 2)

    def cache(self, **overrides):
        kwargs = dict(scope=self.scope, question_digest="d"*64,
                      kind="synthetic_public_education", outcome="answer",
                      source_verified=True, policy_allows=True, ttl_seconds=5, now=10)
        return draft_cache_witness(**{**kwargs, **overrides})

    def admit(self, lab, **overrides):
        return lab.admit(**{**dict(owner="lab_A", peer="192.0.2.1",
                                   tokens=10, cost_units=5, now=10), **overrides})

    def test_cache_allowlist_is_explicit_and_private_history_never_eligible(self):
        w = self.cache()
        self.assertFalse(w.authorizes_product)
        for changes in ({"kind":"history"}, {"kind":"personal"},
                        {"kind":"public_education"}, {"outcome":"partial"},
                        {"outcome":"refusal"}, {"source_verified":False},
                        {"source_verified":1}, {"policy_allows":False},
                        {"policy_allows":None}, {"ttl_seconds":0},
                        {"question_digest":"raw question"}):
            with self.subTest(changes=changes), self.assertRaises(OfflineContractDenied):
                self.cache(**changes)

    def test_cache_key_changes_for_release_policy_authority_locale_question(self):
        original = self.cache()
        for field, value in (("release_digest","e"*64), ("policy_digest","e"*64),
                             ("authority_filter_digest","e"*64), ("locale","en")):
            scope = replace(self.scope, **{field:value})
            self.assertNotEqual(self.cache(scope=scope).key, original.key)
            self.assertFalse(draft_cache_matches(original, scope=scope,
                              question_digest="d"*64, now=11))
        self.assertNotEqual(self.cache(question_digest="e"*64).key, original.key)
        self.assertEqual(self.cache(now=12).key, original.key)

    def test_cache_expiry_exact_boundary_and_tampering(self):
        w = self.cache()
        for now, expected in ((9,False),(10,True),(14,True),(15,False),(16,False)):
            self.assertEqual(draft_cache_matches(w, scope=self.scope,
                             question_digest="d"*64, now=now), expected)
        self.assertFalse(draft_cache_matches(replace(w,key="f"*64), scope=self.scope,
                         question_digest="d"*64, now=11))
        self.assertFalse(draft_cache_matches(w, scope=self.scope,
                         question_digest="e"*64, now=11))

    def test_no_policy_defaults_or_untyped_numeric_bounds(self):
        for field, value in (("request_tokens",True),("daily_cost_units",-1),
                             ("per_owner_window",0),("queue_slots",-1),
                             ("active_slots",1.5)):
            with self.assertRaises(OfflineContractDenied):
                replace(self.bounds, **{field:value})
        lab = OfflineAdmissionLab(self.bounds)
        for changes in ({"owner":"real_owner"},{"peer":"8.8.8.8"},
                        {"tokens":101},{"cost_units":11},{"tokens":True}):
            with self.assertRaises(OfflineContractDenied):
                self.admit(lab, **changes)
        self.assertEqual(lab.witness(0)["reserved_or_spent_test_units"],0)

    def test_rate_owner_and_peer_independent_no_rotation_bypass(self):
        lab = OfflineAdmissionLab(replace(self.bounds, active_slots=10))
        self.admit(lab)
        self.admit(lab, peer="192.0.2.2")
        with self.assertRaises(OfflineContractDenied):
            self.admit(lab, peer="192.0.2.3")
        self.admit(lab, owner="lab_B")
        self.admit(lab, owner="lab_C")
        with self.assertRaises(OfflineContractDenied):
            self.admit(lab, owner="lab_D")
        self.admit(lab, now=20)
        with self.assertRaises(OfflineContractDenied):
            self.admit(lab, now=19)

    def test_daily_quota_and_reserved_budget_atomic_denial(self):
        lab = OfflineAdmissionLab(replace(self.bounds, per_owner_window=20,
                 per_peer_window=20, active_slots=20, per_owner_day=2, daily_cost_units=15))
        one = self.admit(lab)
        two = self.admit(lab)
        with self.assertRaises(OfflineContractDenied):
            self.admit(lab)
        self.admit(lab, owner="lab_B")
        before = lab.witness(0)
        with self.assertRaises(OfflineContractDenied):
            self.admit(lab, owner="lab_C")
        self.assertEqual(lab.witness(0),before)
        lab.settle(one.ticket,outcome="success",actual_units=1)
        self.admit(lab,owner="lab_C",cost_units=4)
        lab.settle(two.ticket,outcome="unknown")
        self.assertEqual(lab.witness(0)["reserved_or_spent_test_units"],15)
        self.admit(lab,now=86400)
        self.assertEqual(lab.witness(1)["reserved_or_spent_test_units"],5)

    def test_queue_fifo_and_backpressure_no_auto_dispatch(self):
        lab = OfflineAdmissionLab(replace(self.bounds, per_owner_window=20,
                 per_peer_window=20, per_owner_day=20, active_slots=1, queue_slots=2))
        one,two,three = [self.admit(lab) for _ in range(3)]
        self.assertEqual([one.state,two.state,three.state],["active","queued","queued"])
        self.assertIsNone(lab.take_next())
        with self.assertRaises(OfflineContractDenied):
            self.admit(lab)
        lab.settle(one.ticket,outcome="success",actual_units=2)
        self.assertEqual(lab.witness(0)["active"],0)
        self.assertEqual(lab.take_next().ticket,two.ticket)
        lab.settle(two.ticket,outcome="unknown")
        self.assertEqual(lab.take_next().ticket,three.ticket)
        self.assertFalse(three.authorizes_product)

    def test_concurrent_reservation_never_overshoots_budget_or_capacity(self):
        lab = OfflineAdmissionLab(replace(self.bounds, per_owner_window=100,
                 per_peer_window=100, per_owner_day=100, daily_cost_units=15,
                 active_slots=2, queue_slots=1))
        def compete(_):
            try:
                return self.admit(lab)
            except OfflineContractDenied:
                return None
        with ThreadPoolExecutor(max_workers=16) as pool:
            receipts = [r for r in pool.map(compete, range(64)) if r is not None]
        self.assertEqual(len(receipts),3)
        self.assertEqual(len({r.ticket for r in receipts}),3)
        self.assertEqual(lab.witness(0)["reserved_or_spent_test_units"],15)
        self.assertEqual((lab.witness(0)["active"],lab.witness(0)["queued"]),(2,1))

    def test_unknown_and_duplicate_settlement_cannot_refund_or_retry(self):
        lab=OfflineAdmissionLab(self.bounds)
        a=self.admit(lab)
        with self.assertRaises(OfflineContractDenied):
            lab.settle(a.ticket,outcome="success",actual_units=6)
        lab.settle(a.ticket,outcome="unknown")
        for outcome in ("success","failed","unknown"):
            with self.assertRaises(OfflineContractDenied):
                lab.settle(a.ticket,outcome=outcome,actual_units=0)
        self.assertEqual(lab.witness(0)["reserved_or_spent_test_units"],5)

    def test_successful_response_cost_excludes_failed_and_unknown(self):
        lab=OfflineAdmissionLab(replace(self.bounds, active_slots=3, per_owner_window=4))
        one,two,three=[self.admit(lab) for _ in range(3)]
        lab.settle(one.ticket,outcome="success",actual_units=2)
        lab.settle(two.ticket,outcome="failed",actual_units=1)
        lab.settle(three.ticket,outcome="unknown")
        report=lab.witness(0)
        self.assertEqual(report["success_count"],1)
        self.assertEqual(report["successful_test_units"],2)
        self.assertEqual(report["reserved_or_spent_test_units"],8)
        self.assertEqual(report["unit"],"SYNTHETIC_TEST_UNIT")
        self.assertFalse(report["authorizes_product"])

    def test_daily_report_is_scoped_to_original_reservation_day(self):
        lab = OfflineAdmissionLab(self.bounds)
        first = self.admit(lab, now=86399)
        second = self.admit(lab, now=86400)
        lab.settle(first.ticket, outcome="success", actual_units=3)
        lab.settle(second.ticket, outcome="success", actual_units=4)
        self.assertEqual(lab.witness(0)["successful_test_units"], 3)
        self.assertEqual(lab.witness(1)["successful_test_units"], 4)
        self.assertEqual(lab.witness(2)["success_count"], 0)
        self.assertEqual(lab.witness(0)["success_count"], 1)
        self.assertEqual(lab.witness(1)["success_count"], 1)


if __name__ == "__main__":
    unittest.main()
