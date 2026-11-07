"""Proposed HISTORY-01 cross-document invariants; synthetic only, NO DB/Auth/runtime."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone


def _stable_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _trusted(actor):
    return actor.get('kind') == 'trusted_actor_context' and actor.get('principal_source') == 'server_auth_context'


def canonical_create_fingerprint(request):
    """Client fields only, independently scoped from send_message idempotency."""
    if request.get('kind') != 'create_conversation_request':
        raise ValueError('NOT_CREATE_CONVERSATION_REQUEST')
    return hashlib.sha256(_stable_json({k: request[k] for k in ('client_conversation_id', 'title')})).hexdigest()


def check_create_receipt(request, receipt, actor):
    if request.get('kind') != 'create_conversation_request' or receipt.get('kind') != 'create_conversation_receipt':
        return ['HISTORY_WRONG_KIND']
    errors = []
    if not _trusted(actor) or actor['owner_user_id'] != receipt['owner_user_id'] or receipt['conversation']['owner_user_id'] != actor['owner_user_id']:
        errors.append('HISTORY_OWNER_CONTEXT_MISMATCH')
    if any(receipt[x] != actor[x] for x in ('request_id', 'trace_id')):
        errors.append('HISTORY_CURRENT_TRACE_MISMATCH')
    for x in ('client_conversation_id', 'idempotency_key'):
        if request[x] != receipt[x]:
            errors.append('HISTORY_CREATE_REQUEST_MISMATCH')
    if canonical_create_fingerprint(request) != receipt['payload_sha256']:
        errors.append('HISTORY_CREATE_FINGERPRINT_MISMATCH')
    if receipt['conversation']['state'] != 'active':
        errors.append('HISTORY_CREATE_NOT_ACTIVE')
    return sorted(set(errors))


def check_create_replay(created, replay):
    """Same scoped operation returns original persisted conversation, not a new one."""
    errors = []
    for field in ('owner_user_id','client_conversation_id','idempotency_key','payload_sha256'):
        if created[field] != replay[field]:
            errors.append('HISTORY_CREATE_REPLAY_SCOPE_MISMATCH')
    if created['disposition'] != 'created' or replay['disposition'] != 'replayed':
        errors.append('HISTORY_CREATE_REPLAY_DISPOSITION')
    if created['conversation'] != replay['conversation']:
        errors.append('HISTORY_CREATE_REPLAY_DUPLICATE_CONVERSATION')
    return sorted(set(errors))


def _instant(raw):
    return datetime.fromisoformat(raw.replace('Z', '+00:00')).astimezone(timezone.utc)


def check_conversation_page(request, page, actor):
    errors = []
    if not _trusted(actor) or actor['owner_user_id'] != page['scope_user_id']:
        errors.append('HISTORY_PAGE_OWNER_MISMATCH')
    if request.get('kind') != 'conversation_list_request' or page.get('kind') != 'conversation_page':
        errors.append('HISTORY_WRONG_KIND')
    if len(page['items']) > request['limit'] or page['page']['limit'] != request['limit']:
        errors.append('HISTORY_PAGE_LIMIT')
    seen = set()
    keys = []
    for obj in page['items']:
        if obj['conversation_id'] in seen:
            errors.append('HISTORY_DUPLICATE_CONVERSATION')
        seen.add(obj['conversation_id'])
        if obj['owner_user_id'] != actor['owner_user_id']:
            errors.append('HISTORY_CROSS_USER_CONVERSATION')
        if obj['state'] != 'active':
            errors.append('HISTORY_DELETION_REQUESTED_VISIBLE')
        keys.append((_instant(obj['created_at']), obj['conversation_id']))
    if keys != sorted(keys, reverse=True):
        errors.append('HISTORY_CONVERSATION_ORDER')
    return sorted(set(errors))


def check_messages_page(request, page, actor):
    errors = []
    if request.get('kind') != 'conversation_messages_request' or page.get('kind') != 'conversation_messages_page':
        return ['HISTORY_WRONG_KIND']
    if not _trusted(actor) or page['owner_user_id'] != actor['owner_user_id']:
        errors.append('HISTORY_MESSAGES_OWNER_MISMATCH')
    if request['conversation_id'] != page['conversation_id']:
        errors.append('HISTORY_MESSAGES_CONVERSATION_MISMATCH')
    if len(page['items']) > request['limit'] or page['page']['limit'] != request['limit']:
        errors.append('HISTORY_MESSAGES_LIMIT')
    seen = set()
    keys = []
    assistants = {}
    for obj in page['items']:
        if obj['message_id'] in seen:
            errors.append('HISTORY_DUPLICATE_MESSAGE')
        seen.add(obj['message_id'])
        if obj['owner_user_id'] != actor['owner_user_id'] or obj['conversation_id'] != page['conversation_id']:
            errors.append('HISTORY_CROSS_USER_MESSAGE')
        if obj['role'] == 'user' and obj['answer_id'] is not None:
            errors.append('HISTORY_USER_MESSAGE_HAS_ANSWER')
        if obj['role'] == 'assistant':
            if obj['answer_id'] is None:
                errors.append('HISTORY_ASSISTANT_WITHOUT_ANSWER')
            else:
                assistants[obj['answer_id']] = obj['message_id']
        keys.append((_instant(obj['created_at']), obj['message_id']))
    if keys != sorted(keys):
        errors.append('HISTORY_MESSAGES_ORDER')
    answers = set()
    for answer in page['answers']:
        if answer['answer_id'] in answers:
            errors.append('HISTORY_DUPLICATE_ANSWER')
        answers.add(answer['answer_id'])
        if answer['conversation_id'] != page['conversation_id']:
            errors.append('HISTORY_ANSWER_CONVERSATION_MISMATCH')
        if assistants.get(answer['answer_id']) != answer['message_id']:
            errors.append('HISTORY_ANSWER_MESSAGE_MISMATCH')
    if set(assistants) != answers:
        errors.append('HISTORY_MISSING_OR_UNRELATED_ANSWER')
    return sorted(set(errors))


def check_status_query(query, status, actor):
    if query.get('kind') != 'message_request_status_query' or status.get('kind') != 'message_request_status':
        return ['HISTORY_WRONG_KIND']
    errors = []
    if not _trusted(actor) or status['owner_user_id'] != actor['owner_user_id']:
        errors.append('HISTORY_STATUS_UNAUTHORIZED')
    if any(status[k] != actor[k] for k in ('request_id','trace_id')):
        errors.append('HISTORY_STATUS_CURRENT_TRACE_MISMATCH')
    for k in ('requested_conversation_id','client_message_id','idempotency_key'):
        if status[k] != query[k]:
            errors.append('HISTORY_STATUS_SCOPE_MISMATCH')
    state = status['status']
    persistence = ('resolved_conversation_id','message_id')
    attempt = ('attempt_id','attempt_request_id','attempt_trace_id','reserved_answer_id')
    result = ('answer_id','answer')
    if state == 'not_found' and any(status[f] is not None for f in (*persistence,*attempt,*result)):
        errors.append('HISTORY_NOT_FOUND_HAS_PERSISTENCE')
    if state != 'not_found' and any(status[f] is None for f in persistence):
        errors.append('HISTORY_STATUS_MISSING_T1')
    if state == 'persisted' and any(status[f] is not None for f in (*attempt,*result)):
        errors.append('HISTORY_PERSISTED_CLAIMS_ATTEMPT')
    if state in {'attempt_pending','attempt_unknown','answer_committed','failed','cancelled'}:
        if any(status[f] is None for f in attempt):
            errors.append('HISTORY_STATUS_MISSING_ATTEMPT')
    if state in {'attempt_pending','attempt_unknown','failed','cancelled'} and any(status[f] is not None for f in result):
        errors.append('HISTORY_UNCOMMITTED_ANSWER_CLAIM')
    if state == 'answer_committed':
        ans = status['answer']
        if ans is None or status['answer_id'] is None:
            errors.append('HISTORY_FINAL_ANSWER_MISSING')
        elif (ans['answer_id'] != status['answer_id'] or
              ans['answer_id'] != status['reserved_answer_id'] or
              ans['conversation_id'] != status['resolved_conversation_id'] or
              ans['request_id'] != status['attempt_request_id'] or
              ans['trace_id'] != status['attempt_trace_id']):
            errors.append('HISTORY_FINAL_ANSWER_LINKAGE')
    return sorted(set(errors))


# A server's *direct, committed* state transition is not the same thing as
# consecutive client-visible polling observations. Polls can skip committed
# intermediate states; neither validator performs a DB write or model retry.
_DIRECT_STATUS_EDGES = {
    'not_found': {'not_found', 'persisted'},
    'persisted': {'persisted', 'attempt_pending'},
    'attempt_pending': {'attempt_pending', 'attempt_unknown', 'answer_committed', 'failed', 'cancelled'},
    'attempt_unknown': {'attempt_unknown', 'answer_committed', 'failed', 'cancelled'},
    'answer_committed': {'answer_committed'},
    'failed': {'failed'},
    'cancelled': {'cancelled'},
}
_POLL_REACHABLE = {
    'not_found': set(_DIRECT_STATUS_EDGES),
    'persisted': {'persisted', 'attempt_pending', 'attempt_unknown', 'answer_committed', 'failed', 'cancelled'},
    'attempt_pending': _DIRECT_STATUS_EDGES['attempt_pending'],
    'attempt_unknown': _DIRECT_STATUS_EDGES['attempt_unknown'],
    'answer_committed': {'answer_committed'},
    'failed': {'failed'},
    'cancelled': {'cancelled'},
}


def _status_evidence_errors(status):
    """Check T1/T2/T3 claims in a single server-sourced DTO; not DB proof."""
    state = status.get('status')
    if state not in _DIRECT_STATUS_EDGES:
        return ['HISTORY_INVALID_STATUS_EVIDENCE']
    errors = []
    t1 = ('resolved_conversation_id', 'message_id')
    t2 = ('attempt_id', 'attempt_request_id', 'attempt_trace_id', 'reserved_answer_id')
    t3 = ('answer_id', 'answer')
    if state == 'not_found' and any(status.get(k) is not None for k in (*t1, *t2, *t3)):
        errors.append('HISTORY_NOT_FOUND_HAS_PERSISTENCE')
    if state != 'not_found' and any(status.get(k) is None for k in t1):
        errors.append('HISTORY_STATUS_MISSING_T1')
    if state == 'persisted' and any(status.get(k) is not None for k in (*t2, *t3)):
        errors.append('HISTORY_PERSISTED_CLAIMS_ATTEMPT')
    if state in {'attempt_pending', 'attempt_unknown', 'answer_committed', 'failed', 'cancelled'}:
        if any(status.get(k) is None for k in t2):
            errors.append('HISTORY_STATUS_MISSING_ATTEMPT')
    if state in {'not_found', 'persisted', 'attempt_pending', 'attempt_unknown', 'failed', 'cancelled'}:
        if any(status.get(k) is not None for k in t3):
            errors.append('HISTORY_UNCOMMITTED_ANSWER_CLAIM')
    if state == 'answer_committed':
        answer = status.get('answer')
        if not isinstance(answer, dict) or status.get('answer_id') is None:
            errors.append('HISTORY_FINAL_ANSWER_MISSING')
        elif (answer.get('kind') != 'answer'
              or answer.get('answer_id') != status.get('answer_id')
              or status.get('answer_id') != status.get('reserved_answer_id')
              or answer.get('conversation_id') != status.get('resolved_conversation_id')
              or answer.get('request_id') != status.get('attempt_request_id')
              or answer.get('trace_id') != status.get('attempt_trace_id')
              or answer.get('message_id') == status.get('message_id')
              or answer.get('state') in {'unknown', 'cancelled'}):
            errors.append('HISTORY_FINAL_ANSWER_LINKAGE')
    return sorted(set(errors))


def _stable_status_errors(before, after):
    """Current poll request_id/trace_id may differ; persisted IDs may not."""
    errors = []
    for field in ('owner_user_id', 'requested_conversation_id', 'client_message_id', 'idempotency_key'):
        if before.get(field) != after.get(field):
            errors.append('HISTORY_SCOPE_CHANGED_BETWEEN_POLLS')
    stable = {
        'message_id': 'HISTORY_REPLAY_DUPLICATE_MESSAGE',
        'resolved_conversation_id': 'HISTORY_REPLAY_DUPLICATE_CONVERSATION',
        'attempt_id': 'HISTORY_ATTEMPT_REPLACED_SILENTLY',
        'attempt_request_id': 'HISTORY_ATTEMPT_TRACE_CHANGED',
        'attempt_trace_id': 'HISTORY_ATTEMPT_TRACE_CHANGED',
        'reserved_answer_id': 'HISTORY_RESERVATION_CHANGED',
        'answer_id': 'HISTORY_ANSWER_ID_CHANGED',
    }
    for field, code in stable.items():
        if before.get(field) is not None and before.get(field) != after.get(field):
            errors.append(code)
    if before.get('answer') is not None and before.get('answer') != after.get('answer'):
        errors.append('HISTORY_COMMITTED_ANSWER_CHANGED')
    return sorted(set(errors))


def _has_verified_server_reconciliation(after, evidence):
    """Only API/DB code may construct this after verifying durable server rows.

    The dict below is a synthetic contract witness, NOT a bearer credential or
    a client-supplied switch. Production must independently verify its origin.
    """
    return (isinstance(evidence, dict)
            and evidence.get('source') == 'verified_server_persistence'
            and evidence.get('verified') is True
            and all(evidence.get(k) == after.get(k) for k in (
                'owner_user_id', 'attempt_id', 'reserved_answer_id', 'answer_id', 'status'))
            and after.get('attempt_id') is not None)


def _check_status_move(before, after, allowed, *, server_commit_evidence=None):
    errors = _stable_status_errors(before, after)
    errors.extend(_status_evidence_errors(before))
    errors.extend(_status_evidence_errors(after))
    source = before.get('status')
    target = after.get('status')
    if target not in allowed.get(source, set()):
        errors.append('HISTORY_ILLEGAL_STATUS_TRANSITION')
    if source == 'attempt_unknown' and target in {'answer_committed', 'failed', 'cancelled'}:
        if not _has_verified_server_reconciliation(after, server_commit_evidence):
            errors.extend(('HISTORY_SERVER_EVIDENCE_REQUIRED', 'HISTORY_ILLEGAL_STATUS_TRANSITION'))
    return sorted(set(errors))


def check_server_status_transition(before, after, *, server_commit_evidence=None):
    """Validate one *direct* DB transition; no skipped T1/T2/T3 allowed.

    Called only after server-side evidence verification, never from the UI.
    """
    return _check_status_move(before, after, _DIRECT_STATUS_EDGES,
                              server_commit_evidence=server_commit_evidence)


def check_status_progression(before, after, *, reconciled_from_db=False,
                             server_commit_evidence=None):
    """Compare two POLLED snapshots, which may skip unseen intermediate steps.

    reconciled_from_db is kept as a legacy server-side hint but is NOT proof:
    even True cannot authorize unknown -> terminal without verified DB evidence.
    No model call or database transition is performed here.
    """
    return _check_status_move(before, after, _POLL_REACHABLE,
                              server_commit_evidence=server_commit_evidence)


def classify_polled_status_response(last_applied, incoming, *,
                                    last_applied_poll_sequence, incoming_poll_sequence,
                                    server_commit_evidence=None):
    """Consumer decision using locally assigned, monotonically issued poll IDs.

    Older in-flight responses must be IGNORED, never applied to UI state. For
    newer responses, an actual backward observation is rejected. Sequence
    proves only request order, not DB commit order (requires future revision).
    """
    if (type(last_applied_poll_sequence) is not int
            or type(incoming_poll_sequence) is not int
            or min(last_applied_poll_sequence, incoming_poll_sequence) < 0):
        return 'reject', ['HISTORY_POLL_SEQUENCE_INVALID']
    current_errors = _status_evidence_errors(incoming)
    scope_errors = [
        'HISTORY_SCOPE_CHANGED_BETWEEN_POLLS'
        for field in ('owner_user_id', 'requested_conversation_id', 'client_message_id', 'idempotency_key')
        if last_applied.get(field) != incoming.get(field)
    ]
    if current_errors or scope_errors:
        return 'reject', sorted(set(current_errors + scope_errors))
    if incoming_poll_sequence < last_applied_poll_sequence:
        return 'ignore_stale', []
    errors = check_status_progression(last_applied, incoming,
                                      server_commit_evidence=server_commit_evidence)
    return ('reject', errors) if errors else ('apply', [])


def make_test_cursor(payload, secret):
    """Test-only reference; key is CALLER-SUPPLIED, NEVER a production Auth implementation."""
    data = _stable_json(payload)
    signature = hmac.new(secret, data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(data + signature).decode('ascii').rstrip('=')


def verify_test_cursor(token, secret, *, owner, resource, conversation_id, limit, now_epoch):
    """Opaque owner/query-bound integrity and expiry check; never trust cursor as Auth."""
    if not isinstance(token, str) or not (1 <= len(token) <= 512):
        return 'HISTORY_CURSOR_INVALID'
    try:
        data = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        payload, signature = data[:-32], data[-32:]
        if len(data) < 33 or not hmac.compare_digest(hmac.new(secret, payload, hashlib.sha256).digest(), signature):
            return 'HISTORY_CURSOR_INVALID'
        decoded = json.loads(payload)
        if set(decoded) != {'owner','resource','conversation_id','limit','anchor','last','exp'}:
            return 'HISTORY_CURSOR_INVALID'
        if decoded['owner'] != owner or decoded['resource'] != resource or decoded['conversation_id'] != conversation_id or decoded['limit'] != limit:
            return 'HISTORY_CURSOR_SCOPE_MISMATCH'
        if not isinstance(decoded['exp'], int) or decoded['exp'] <= now_epoch:
            return 'HISTORY_CURSOR_EXPIRED'
    except (ValueError, TypeError, UnicodeError, KeyError):
        return 'HISTORY_CURSOR_INVALID'
    return None
