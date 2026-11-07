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


def check_status_progression(before, after, *, reconciled_from_db=False):
    """Local contract state machine; no automatic attempt/model re-execution."""
    legal = {
        'not_found': {'not_found','persisted'},
        'persisted': {'persisted','attempt_pending'},
        'attempt_pending': {'attempt_pending','attempt_unknown','answer_committed','failed','cancelled'},
        'attempt_unknown': {'attempt_unknown', 'answer_committed'} if reconciled_from_db else {'attempt_unknown'},  # only with authoritative T3 DB evidence
        'answer_committed': {'answer_committed'},
        'failed': {'failed'},
        'cancelled': {'cancelled'},
    }
    errors = []
    if after['status'] not in legal[before['status']]:
        errors.append('HISTORY_ILLEGAL_STATUS_TRANSITION')
    for k in ('owner_user_id','requested_conversation_id','client_message_id','idempotency_key'):
        if before[k] != after[k]:
            errors.append('HISTORY_SCOPE_CHANGED_BETWEEN_POLLS')
    if before['message_id'] is not None and before['message_id'] != after['message_id']:
        errors.append('HISTORY_REPLAY_DUPLICATE_MESSAGE')
    if before['resolved_conversation_id'] is not None and before['resolved_conversation_id'] != after['resolved_conversation_id']:
        errors.append('HISTORY_REPLAY_DUPLICATE_CONVERSATION')
    if before['attempt_id'] is not None and before['attempt_id'] != after['attempt_id']:
        errors.append('HISTORY_ATTEMPT_REPLACED_SILENTLY')
    if before['reserved_answer_id'] is not None and before['reserved_answer_id'] != after['reserved_answer_id']:
        errors.append('HISTORY_RESERVATION_CHANGED')
    return sorted(set(errors))


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
