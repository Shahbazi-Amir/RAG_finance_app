"""Test-only synthetic reference boundaries, not an API, engine, policy or cache.

All limits, role labels, filters, model identities and fallback choices belong
solely to the explicit synthetic fixtures. No network, database, subprocess,
provider execution, persistence or authorization is implemented here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol
from unicodedata import category


class BoundaryDenied(ValueError):
    def __str__(self):
        return 'SYNTHETIC_BOUNDARY_DENIED'


def require(condition):
    if condition is not True:
        raise BoundaryDenied()


def ident(value):
    return (type(value) is str and value.startswith('fixture-')
            and bool(value[len('fixture-'):].strip()) and value == value.strip()
            and not any(category(c).startswith('C') for c in value))


def nonnegative(value):
    return type(value) is int and value >= 0


def exact(doc, keys):
    require(type(doc) is dict and all(type(k) is str for k in doc)
            and set(doc) == set(keys))


# M07-A04/A07: report shape/point parity only; no collection connection.
POINT_FIELDS = ('id', 'release_id', 'payload_version', 'source_type',
                'credited_author_name', 'editorial_supervisor_name',
                'speaker_name', 'content_authority_type', 'attribution_status')
SOURCE_TYPES = ('website', 'book', 'transcript')  # fixture vocabulary only
AUTHORITY_TYPES = ('fixture-direct', 'fixture-editorial', 'fixture-speaker', 'fixture-unknown')


def inspect_inventory(points, *, release_id, payload_version, expected_count):
    require(ident(release_id) and ident(payload_version) and nonnegative(expected_count))
    require(type(points) is list and len(points) == expected_count)
    seen = set()
    for point in points:
        exact(point, POINT_FIELDS)
        require(ident(point['id']) and point['id'] not in seen)
        require(all(type(point[k]) is str for k in ('release_id', 'payload_version',
                    'source_type', 'content_authority_type', 'attribution_status')))
        require(point['release_id'] == release_id and point['payload_version'] == payload_version)
        require(point['source_type'] in SOURCE_TYPES and point['content_authority_type'] in AUTHORITY_TYPES)
        require(point['attribution_status'] in ('fixture-marked', 'fixture-unknown'))
        for name in ('credited_author_name', 'editorial_supervisor_name', 'speaker_name'):
            require(point[name] is None or ident(point[name]))
        seen.add(point['id'])
    return {'origin':'SYNTHETIC', 'inventory_match':True, 'approved':False,
            'knowledge_ready':False, 'dispatch_allowed':False, 'point_count':len(seen)}


def capability_receipt(*, app_ready, inventory_match):
    require(type(app_ready) is bool and type(inventory_match) is bool)
    return {'origin':'SYNTHETIC', 'app_ready':app_ready, 'inventory_match':inventory_match,
            'retrieval':'unavailable', 'generation':'unavailable', 'knowledge_ready':False}


# M08-A03/A04: explicit fixture filters, not NLP intent or real authority rules.
def select_fixture_points(points, *, release_id, payload_version, expected_count,
                          source_types, authority_types, direct_author=None):
    inspect_inventory(points, release_id=release_id, payload_version=payload_version,
                      expected_count=expected_count)
    require(type(source_types) is tuple and bool(source_types) and all(type(x) is str and x in SOURCE_TYPES for x in source_types))
    require(type(authority_types) is tuple and bool(authority_types) and all(type(x) is str and x in AUTHORITY_TYPES for x in authority_types))
    require(direct_author is None or ident(direct_author))
    return tuple(p['id'] for p in points if p['source_type'] in source_types
                 and p['content_authority_type'] in authority_types
                 and (direct_author is None or (p['content_authority_type'] == 'fixture-direct'
                      and p['credited_author_name'] == direct_author
                      and p['attribution_status'] == 'fixture-marked')))


# M08-A10 / M09-A08: a separately supplied fixture policy, never a default.
def fallback_fixture(*, component, failed, allowed_edges, required_components):
    require(ident(component) and type(failed) is bool)
    require(type(allowed_edges) is dict and all(ident(k) and ident(v) and k != v for k,v in allowed_edges.items()))
    require(type(required_components) is tuple and all(ident(x) for x in required_components)
            and len(set(required_components)) == len(required_components))
    if not failed:
        return component
    if component in required_components or component not in allowed_edges:
        raise BoundaryDenied()
    return allowed_edges[component]  # one decision only, never a dispatch or retry


# M09-A01/A04/A05: provider-neutral *receipt* interface, no invocation method.
@dataclass(frozen=True)
class RunIdentity:
    provider: str
    model: str
    version: str
    run_id: str

    def __post_init__(self):
        require(all(ident(x) for x in (self.provider, self.model, self.version, self.run_id)))


class SyntheticReceiptReader(Protocol):
    def describe_fixture(self) -> RunIdentity: ...


def describe_fixture(reader: SyntheticReceiptReader, *, expected: RunIdentity):
    require(type(expected) is RunIdentity)
    observed = reader.describe_fixture()  # only offline fixture metadata
    require(type(observed) is RunIdentity and observed == expected)
    return observed


def minimal_fixture_payload(record, *, allow_fields):
    # Deliberately no free text, owner, token, question, history or credentials.
    # This is a typed fixture metadata allowlist, not a real PII masker.
    permitted = ('fixture_context_id', 'fixture_policy_id', 'fixture_release_id')
    require(type(record) is dict and all(type(k) is str for k in record)
            and type(allow_fields) is tuple and bool(allow_fields))
    require(all(type(k) is str and k in permitted for k in allow_fields)
            and len(set(allow_fields)) == len(allow_fields))
    require(all(k in record and ident(record[k]) for k in allow_fields))
    return {k:record[k] for k in allow_fields}


# M10-A01: bounded owner/conversation history reference, synthetic IDs only.
def context_fixture(rows, *, owner, conversation, current, max_history):
    require(ident(owner) and ident(conversation) and ident(current) and nonnegative(max_history))
    require(type(rows) is list)
    scoped = []
    seen = set()
    for row in rows:
        exact(row, ('owner','conversation','message','seq'))
        require(all(ident(row[k]) for k in ('owner','conversation','message')) and nonnegative(row['seq']))
        if row['owner'] != owner or row['conversation'] != conversation:
            continue
        require(row['message'] != current and row['message'] not in seen)
        seen.add(row['message'])
        scoped.append((row['seq'],row['message']))
    require(len({seq for seq,_ in scoped}) == len(scoped))
    selected = sorted(scoped)[-max_history:] if max_history else []
    return {'origin':'SYNTHETIC', 'current':current, 'history':tuple(msg for _,msg in selected),
            'dispatch_allowed':False}


# M09-A03 / M17-A02/A10: pure arithmetic, fixture integer units, no price/currency.
@dataclass(frozen=True)
class SyntheticLimits:
    max_tokens: int
    max_cost_units: int
    daily_requests: int
    daily_cost_units: int

    def __post_init__(self):
        require(all(nonnegative(x) for x in (self.max_tokens,self.max_cost_units,
                    self.daily_requests,self.daily_cost_units)))


def budget_fixture(*, limits, input_tokens, output_tokens, cost_units, used_requests, used_cost_units):
    require(type(limits) is SyntheticLimits)
    require(all(nonnegative(x) for x in (input_tokens,output_tokens,cost_units,used_requests,used_cost_units)))
    return (input_tokens + output_tokens <= limits.max_tokens and cost_units <= limits.max_cost_units
            and used_requests + 1 <= limits.daily_requests
            and used_cost_units + cost_units <= limits.daily_cost_units)


def cost_receipt_fixture(*, identity, outcome, input_tokens, output_tokens, cost_units, price_version):
    require(type(identity) is RunIdentity and ident(price_version))
    require(type(outcome) is str and outcome in ('completed','failed','unknown','cancelled'))
    require(all(nonnegative(x) for x in (input_tokens,output_tokens,cost_units)))
    if outcome != 'completed':
        raise BoundaryDenied()  # no fabricated successful-answer cost
    return {'origin':'SYNTHETIC', 'approved':False, 'billable':False,
            'run_id':identity.run_id, 'provider':identity.provider, 'model':identity.model,
            'model_version':identity.version, 'price_version':price_version,
            'input_tokens':input_tokens, 'output_tokens':output_tokens,
            'total_tokens':input_tokens+output_tokens,'cost_units':cost_units}
