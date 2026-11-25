"""Local test-only consumer/evaluation examples. Not a product contract or policy.
No provider, retrieval, actual source, network, DB, or user data is consulted.
All labels, bounds, timings and decisions are explicit fixture inputs.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from ipaddress import ip_address
from statistics import median
from f3_synthetic_boundary_oracle import (
    BoundaryDenied, require, ident, exact, nonnegative, context_fixture,
    select_fixture_points, RunIdentity,
)

# A fixture annotation is not a classifier; do not infer policy from free text.
CATEGORIES = ('education', 'personal_advice', 'out_of_source', 'ambiguous')
OUTCOMES = ('answer', 'no_answer', 'clarification', 'refusal')


def outcome_fixture(case, *, policy_version, rules):
    exact(case, ('id', 'category', 'answerable'))
    require(ident(case['id']) and type(case['category']) is str and case['category'] in CATEGORIES
            and type(case['answerable']) is bool and ident(policy_version))
    require(type(rules) is dict)
    # Caller must explicitly provide the whole finite decision table. No default.
    require(set(rules) == {(c, a) for c in CATEGORIES for a in (True, False)})
    for key, value in rules.items():
        require(type(key) is tuple and len(key) == 2 and type(key[0]) is str
                and type(key[1]) is bool)
        exact(value, ('outcome', 'disclaimer'))
        require(type(value['outcome']) is str and value['outcome'] in OUTCOMES)
        require(value['disclaimer'] is None or ident(value['disclaimer']))
        require(key[1] or value['outcome'] != 'answer')
    chosen = rules[(case['category'], case['answerable'])]
    return {'origin':'SYNTHETIC', 'approved':False, 'dispatch_allowed':False,
            'case_id':case['id'], 'policy_version':policy_version, **chosen}


def bounded_context_fixture(rows, points, *, scope, selection, allowed_point_ids,
                            context_limit, selected_ids):
    """Bind an already supplied fixture selection; never run retrieval."""
    exact(scope, ('owner','conversation','current','max_history'))
    require(type(selection) is dict and type(allowed_point_ids) is tuple
            and all(ident(x) for x in allowed_point_ids)
            and len(set(allowed_point_ids)) == len(allowed_point_ids))
    require(nonnegative(context_limit) and type(selected_ids) is tuple
            and all(ident(x) for x in selected_ids)
            and len(set(selected_ids)) == len(selected_ids)
            and len(selected_ids) <= context_limit)
    required_selection = {'release_id', 'payload_version', 'expected_count',
                          'source_types', 'authority_types'}
    require(required_selection <= set(selection) <= required_selection | {'direct_author'})
    permitted = set(select_fixture_points(points, **selection)) & set(allowed_point_ids)
    require(set(selected_ids) <= permitted)
    context = context_fixture(rows, **scope)
    return {**context, 'retrieved_point_ids':selected_ids, 'source_verified':False}


# Consumer-facing synthetic presentation projections. No source URLs are made
# clickable: an asserted locator in a fixture is not an authenticated source.
KINDS = ('website','book','transcript','unresolved')


def source_projection_fixture(claims, sources, *, allowed_source_ids):
    require(type(claims) is list and type(sources) is list
            and type(allowed_source_ids) is tuple
            and all(ident(x) for x in allowed_source_ids)
            and len(set(allowed_source_ids)) == len(allowed_source_ids))
    by_id = {}
    for source in sources:
        exact(source, ('id','kind','locator','credited_author_name',
                       'editorial_supervisor_name','speaker_name','reason'))
        sid = source['id']
        require(ident(sid) and sid not in by_id and sid in allowed_source_ids
                and type(source['kind']) is str and source['kind'] in KINDS)
        require(all(source[k] is None or ident(source[k]) for k in
                    ('credited_author_name','editorial_supervisor_name','speaker_name','reason')))
        loc = source['locator']
        kind = source['kind']
        if kind == 'website':
            # Fixture locator is a symbolic ID, never an external URL.
            exact(loc, ('url_fixture_id',)); require(ident(loc['url_fixture_id']))
        elif kind == 'book':
            exact(loc, ('page',)); require(type(loc['page']) is int and loc['page'] > 0)
        elif kind == 'transcript':
            exact(loc, ('timestamp_ms',)); require(nonnegative(loc['timestamp_ms']))
        else:
            require(loc is None and source['reason'] is None)
        by_id[sid] = {**source, 'locator':None if loc is None else dict(loc),
                      'href':None, 'verified':False, 'origin':'SYNTHETIC'}
    projected_claims = []
    used = set()
    claim_ids = set()
    for claim in claims:
        exact(claim, ('id','source_ids'))
        require(ident(claim['id']) and claim['id'] not in claim_ids)
        ids = claim['source_ids']
        require(type(ids) is list and bool(ids) and all(ident(x) for x in ids)
                and len(set(ids)) == len(ids) and set(ids) <= set(by_id))
        claim_ids.add(claim['id']); used.update(ids)
        projected_claims.append({'id':claim['id'], 'source_ids':list(ids)})
    require(used == set(by_id))  # no orphan source displayed
    return {'origin':'SYNTHETIC', 'approved':False, 'claims':projected_claims,
            'sources':[by_id[x] for x in sorted(by_id)]}


def regression_fixture(expected, observed):
    """Compare pre-labelled synthetic case IDs; never call an engine."""
    require(type(expected) is dict and bool(expected) and type(observed) is dict)
    require(all(ident(k) for k in expected) and all(ident(k) for k in observed)
            and set(expected) == set(observed))
    require(all(type(v) is str and v in OUTCOMES for v in expected.values())
            and all(type(v) is str and v in OUTCOMES for v in observed.values()))
    mismatch = tuple(sorted(k for k in expected if expected[k] != observed[k]))
    return {'origin':'SYNTHETIC','approved':False,'cases':len(expected),
            'matched':len(expected)-len(mismatch),'mismatch_ids':mismatch,
            'actual_golden_set':False}


def benchmark_fixture(samples, *, identity):
    """Summarize supplied synthetic samples. Does not time or rank providers."""
    require(type(identity) is RunIdentity and type(samples) is list and bool(samples))
    seen=set(); times=[]; cost=0; matched=0
    for sample in samples:
        exact(sample, ('case_id','identity','latency_ms','cost_units','matched'))
        require(ident(sample['case_id']) and sample['case_id'] not in seen
                and type(sample['identity']) is RunIdentity and sample['identity'] == identity
                and nonnegative(sample['latency_ms'])
                and nonnegative(sample['cost_units']) and type(sample['matched']) is bool)
        seen.add(sample['case_id']); times.append(sample['latency_ms'])
        cost += sample['cost_units']; matched += int(sample['matched'])
    try:
        median_latency = median(times)
    except OverflowError:
        raise BoundaryDenied() from None
    return {'origin':'SYNTHETIC','approved':False,'provider_frozen':False,
            'measured_live':False,'cases':len(seen),'matched':matched,
            'median_fixture_latency_ms':median_latency,'max_fixture_latency_ms':max(times),
            'total_fixture_cost_units':cost}


@dataclass(frozen=True)
class FixtureRateLimits:
    user: int
    ip: int
    window_seconds: int

    def __post_init__(self):
        require(all(type(x) is int and x > 0 for x in
                    (self.user,self.ip,self.window_seconds)))


class FixtureRateWindow:
    """Atomic in-process fixture counter, no HTTP middleware or durable storage.
    Test-only actor/IP inputs are not trusted real identity or proxy headers.
    Explicit monotonically increasing integer clock, no implicit wall time.
    """
    def __init__(self, limits):
        require(type(limits) is FixtureRateLimits)
        self._limits=limits
        self._lock=Lock(); self._users=Counter(); self._ips=Counter()
        self._window=None; self._last=None

    def admit(self, *, owner, ip, now):
        # Scope suffixes are local-interface identifiers, not separate IPs.
        require(ident(owner) and type(ip) is str and "%" not in ip and nonnegative(now))
        try:
            addr=ip_address(ip)
            # Only RFC 5737 examples and the IPv6 documentation prefix are
            # used by fixtures; no real user addresses accepted here.
            from ipaddress import ip_network
            require(any(addr in ip_network(n) for n in
                        ('192.0.2.0/24','198.51.100.0/24','203.0.113.0/24','2001:db8::/32')))
            address=str(addr)
        except ValueError:
            raise BoundaryDenied() from None
        with self._lock:
            require(self._last is None or now >= self._last)
            window=now // self._limits.window_seconds
            if window != self._window:
                self._users.clear(); self._ips.clear(); self._window=window
            self._last=now
            if self._users[owner] >= self._limits.user or self._ips[address] >= self._limits.ip:
                return False
            self._users[owner] += 1; self._ips[address] += 1
            return True
