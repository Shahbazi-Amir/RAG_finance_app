"""NONBINDING offline design for P3M09-A03 and P3M17 resource controls.

Only synthetic inputs, process-local state, integer test units and caller-
supplied monotonic time. No approved policy, authenticated peer extraction,
durable/distributed store, product admission, actual cache, provider, dispatch,
or billing. Do not import this module into a product route. The app-only
Send fence remains authoritative; all proposed numeric bounds must be supplied.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from ipaddress import ip_address
import json
import re
from threading import RLock


class OfflineContractDenied(Exception):
    def __str__(self):
        return "OFFLINE_CONTRACT_DENIED"


def _uint(value, *, positive=False):
    if type(value) is not int or value < int(positive):
        raise OfflineContractDenied()
    return value


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise OfflineContractDenied()
    return value


@dataclass(frozen=True)
class CacheScope:
    release_digest: str
    policy_digest: str
    authority_filter_digest: str
    locale: str

    def __post_init__(self):
        for value in (self.release_digest, self.policy_digest, self.authority_filter_digest):
            _digest(value)
        if not isinstance(self.locale, str) or not re.fullmatch(
                r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", self.locale):
            raise OfflineContractDenied()


@dataclass(frozen=True)
class CacheWitness:
    """Synthetic digest-only metadata, never an answer or permission."""
    key: str
    scope: CacheScope
    question_digest: str
    issued_at: int
    expires_at: int
    authorizes_product: bool = False


def draft_cache_witness(scope, *, question_digest, kind, outcome,
                        source_verified, policy_allows, ttl_seconds, now):
    """Candidate structural cache key; default deny, no answer storage."""
    if (not isinstance(scope, CacheScope) or kind != "synthetic_public_education"
            or outcome != "answer" or source_verified is not True
            or policy_allows is not True):
        raise OfflineContractDenied()
    _digest(question_digest)
    expires = _uint(now) + _uint(ttl_seconds, positive=True)
    encoded = json.dumps(["offline-cache-key.v1", scope.release_digest,
        scope.policy_digest, scope.authority_filter_digest, scope.locale,
        question_digest], separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return CacheWitness(sha256(encoded).hexdigest(), scope, question_digest, now, expires)


def draft_cache_matches(witness, *, scope, question_digest, now):
    if not isinstance(witness, CacheWitness):
        return False
    try:
        # Recompute from the requested scope, never trust a supplied key.
        expected = draft_cache_witness(scope, question_digest=question_digest,
            kind="synthetic_public_education", outcome="answer",
            source_verified=True, policy_allows=True, ttl_seconds=1, now=now)
        return (witness.authorizes_product is False
                and witness.scope == scope
                and witness.question_digest == question_digest
                and witness.key == expected.key
                and _uint(witness.issued_at) <= _uint(now) < _uint(witness.expires_at))
    except OfflineContractDenied:
        return False


@dataclass(frozen=True)
class DraftBounds:
    """Explicit fixture values only; no production defaults or currency."""
    window_seconds: int
    per_owner_window: int
    per_peer_window: int
    per_owner_day: int
    daily_cost_units: int
    request_cost_units: int
    request_tokens: int
    active_slots: int
    queue_slots: int

    def __post_init__(self):
        for name, value in vars(self).items():
            _uint(value, positive=name != "queue_slots")


@dataclass(frozen=True)
class AdmissionReceipt:
    ticket: int
    state: str
    authorizes_product: bool = False


class OfflineAdmissionLab:
    """Atomic in-memory experiment, no actual job or external side effect.

    Day is an explicit UTC epoch-day from synthetic integer time. Quota
    counts accepted tickets (including queued). Reservations are charged
    to the admission day. UNKNOWN holds the full reservation; no retry or
    implicit queue start. This is not a distributed rate limiter.
    """
    def __init__(self, bounds):
        if not isinstance(bounds, DraftBounds):
            raise OfflineContractDenied()
        self.bounds = bounds
        self._lock = RLock()
        self._last_now = 0
        self._owner_window = {}
        self._peer_window = {}
        self._daily_count = {}
        self._daily_units = {}
        self._tickets = {}
        self._queue = deque()
        self._active = set()
        self._next = 0
        self._successful_units = {}

    def _time(self, now):
        _uint(now)
        if now < self._last_now:
            raise OfflineContractDenied()
        self._last_now = now

    def admit(self, *, owner, peer, tokens, cost_units, now):
        # Reserved documentation addresses and synthetic owner IDs only.
        if not isinstance(owner, str) or not re.fullmatch(r"lab_[A-Za-z0-9_]{1,32}", owner):
            raise OfflineContractDenied()
        if not isinstance(peer, str):
            raise OfflineContractDenied()
        try:
            addr = ip_address(peer)
        except (ValueError, TypeError):
            raise OfflineContractDenied() from None
        if not str(addr).startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
            raise OfflineContractDenied()
        peer = str(addr)
        _uint(tokens, positive=True)
        _uint(cost_units, positive=True)
        with self._lock:
            self._time(now)
            b = self.bounds
            day = now // 86400
            owner_times = [t for t in self._owner_window.get(owner, [])
                           if now - t < b.window_seconds]
            peer_times = [t for t in self._peer_window.get(peer, [])
                          if now - t < b.window_seconds]
            key = (owner, day)
            if (tokens > b.request_tokens or cost_units > b.request_cost_units
                    or len(owner_times) >= b.per_owner_window
                    or len(peer_times) >= b.per_peer_window
                    or self._daily_count.get(key, 0) >= b.per_owner_day
                    or self._daily_units.get(day, 0) + cost_units > b.daily_cost_units
                    or (len(self._active) >= b.active_slots and len(self._queue) >= b.queue_slots)):
                raise OfflineContractDenied()
            # Keep FIFO ordering even if a slot is freed while tickets wait.
            if self._queue and len(self._queue) >= b.queue_slots:
                raise OfflineContractDenied()
            state = "queued" if self._queue or len(self._active) >= b.active_slots else "active"
            self._next += 1
            ticket = self._next
            self._tickets[ticket] = [day, cost_units, state]
            self._owner_window[owner] = owner_times + [now]
            self._peer_window[peer] = peer_times + [now]
            self._daily_count[key] = self._daily_count.get(key, 0) + 1
            self._daily_units[day] = self._daily_units.get(day, 0) + cost_units
            if state == "queued":
                self._queue.append(ticket)
            else:
                self._active.add(ticket)
            return AdmissionReceipt(ticket, state)

    def take_next(self):
        """Explicit lab-only dequeue; never triggers a task."""
        with self._lock:
            if not self._queue or len(self._active) >= self.bounds.active_slots:
                return None
            ticket = self._queue.popleft()
            self._tickets[ticket][2] = "active"
            self._active.add(ticket)
            return AdmissionReceipt(ticket, "active")

    def settle(self, ticket, *, outcome, actual_units=None):
        if type(ticket) is not int:
            raise OfflineContractDenied()
        with self._lock:
            row = self._tickets.get(ticket)
            if row is None or row[2] != "active" or ticket not in self._active:
                raise OfflineContractDenied()
            day, reserved, _ = row
            if outcome == "unknown":
                if actual_units is not None:
                    raise OfflineContractDenied()
                # No release of uncertain spend; no automatic repeat.
            elif outcome in ("success", "failed"):
                if _uint(actual_units) > reserved:
                    raise OfflineContractDenied()
                self._daily_units[day] -= reserved - actual_units
                if outcome == "success":
                    self._successful_units.setdefault(day, []).append(actual_units)
            else:
                raise OfflineContractDenied()
            row[2] = outcome
            self._active.remove(ticket)
            return AdmissionReceipt(ticket, outcome)

    def witness(self, day):
        """Only aggregate synthetic accounting, no provider invoice."""
        _uint(day)
        with self._lock:
            successful = self._successful_units.get(day, ())
            return {"day":day, "reserved_or_spent_test_units":self._daily_units.get(day, 0),
                    "active":len(self._active), "queued":len(self._queue),
                    "success_count":len(successful),
                    "successful_test_units":sum(successful),
                    "unit":"SYNTHETIC_TEST_UNIT", "authorizes_product":False}
