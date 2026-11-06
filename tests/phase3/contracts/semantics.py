"""Cross-document invariants for provisional product.v1; no I/O, backend or model."""
import hashlib
import json

TERMINALS = frozenset({'completed', 'failed', 'server_cancelled', 'unknown'})


def cross_checks(document):
    """Return stable diagnostic codes; call JSON Schema validator first."""
    kind = document.get('kind')
    errors = []
    if kind == 'answer':
        claims = document['claims']
        citations = document['citations']
        claim_ids = [c['claim_id'] for c in claims]
        cite_ids = [c['citation_id'] for c in citations]
        if len(claim_ids) != len(set(claim_ids)):
            errors.append('DUPLICATE_CLAIM_ID')
        if len(cite_ids) != len(set(cite_ids)):
            errors.append('DUPLICATE_CITATION_ID')
        claim_map = {c['claim_id']: c for c in claims}
        cite_map = {c['citation_id']: c for c in citations}
        for claim in claims:
            for cid in claim['citation_ids']:
                if cid not in cite_map:
                    errors.append('MISSING_CITATION_REF')
                elif claim['claim_id'] not in cite_map[cid]['claim_ids']:
                    errors.append('ASYMMETRIC_CITATION_REF')
        for citation in citations:
            for cid in citation['claim_ids']:
                if cid not in claim_map:
                    errors.append('MISSING_CLAIM_REF')
                elif citation['citation_id'] not in claim_map[cid]['citation_ids']:
                    errors.append('ASYMMETRIC_CLAIM_REF')
        if document['provenance']['origin'] == 'SYNTHETIC':
            if any(c['source']['resolution_status'] == 'verified' or c['source']['attribution_status'] == 'verified' for c in citations):
                errors.append('SYNTHETIC_SOURCE_MARKED_REAL')
            if any(c['source'].get('display_title') is not None and c['source'].get('display_title_origin') != 'SYNTHETIC' for c in citations):
                errors.append('SYNTHETIC_DISPLAY_TITLE_CLAIMS_EXTERNAL_ORIGIN')
        if document['outcome'] == 'error' and document['error']['category'] != 'technical':
            errors.append('ERROR_OUTCOME_MUST_BE_TECHNICAL')
        if document['outcome'] in {'no_answer', 'clarification', 'refusal'} and document['error'] is not None:
            errors.append('BUSINESS_OUTCOME_WITH_TECHNICAL_ERROR')
        if document['outcome'] == 'partial' and document['answer_text'] is None:
            errors.append('PARTIAL_MUST_CONTAIN_VISIBLE_CONTENT')
        if document['outcome'] in {'unknown','cancelled'} and document['claims']:
            errors.append('UNFINALIZED_HAS_FINAL_CLAIMS')

    elif kind == 'send_message_receipt':
        # For new conversations the client requested ID stays null; the server must
        # return a non-null allocated ID on success. Existing conversations cannot
        # silently resolve to a different thread.
        if document['disposition'] in {'created', 'replayed'}:
            requested = document['requested_conversation_id']
            resolved = document['resolved_conversation_id']
            if resolved is None:
                errors.append('SUCCESS_RECEIPT_MISSING_RESOLVED_CONVERSATION')
            elif requested is not None and resolved != requested:
                errors.append('RESOLVED_CONVERSATION_MISMATCH')
        elif document['resolved_conversation_id'] is not None:
            errors.append('CONFLICT_MUST_NOT_ALLOCATE_CONVERSATION')

    elif kind == 'conversation_snapshot':
        conversation = document['conversation']
        conv_id = conversation['conversation_id']
        owner = conversation['owner_user_id']
        messages = document['messages']
        answers = document['answers']
        feedback = document['feedback']
        for key, data, field in [('message', messages,'message_id'), ('answer',answers,'answer_id'),('feedback',feedback,'feedback_id')]:
            ids = [x[field] for x in data]
            if len(set(ids)) != len(ids):
                errors.append('DUPLICATE_'+key.upper()+'_ID')
        message_by_id = {m['message_id']:m for m in messages}
        answer_by_id = {a['answer_id']:a for a in answers}
        for msg in messages:
            if msg['owner_user_id'] != owner or msg['conversation_id'] != conv_id:
                errors.append('CROSS_USER_OR_CONVERSATION_MESSAGE')
            if msg['role'] == 'user' and msg['answer_id'] is not None:
                errors.append('USER_MESSAGE_WITH_ANSWER_ID')
            if msg['answer_id'] is not None and msg['answer_id'] not in answer_by_id:
                errors.append('MESSAGE_ANSWER_NOT_FOUND')
        for answer in answers:
            if answer['conversation_id'] != conv_id:
                errors.append('ANSWER_CONVERSATION_MISMATCH')
            linked = message_by_id.get(answer['message_id'])
            if linked is None or linked['role'] != 'assistant' or linked['answer_id'] != answer['answer_id']:
                errors.append('ANSWER_MESSAGE_LINK_INVALID')
            errors.extend(cross_checks(answer))
        for item in feedback:
            if item['owner_user_id'] != owner or item['conversation_id'] != conv_id:
                errors.append('CROSS_USER_OR_CONVERSATION_FEEDBACK')
            if item['answer_id'] not in answer_by_id:
                errors.append('FEEDBACK_ANSWER_NOT_FOUND')

    elif kind == 'conversation_page':
        for conversation in document['items']:
            if conversation['owner_user_id'] != document['scope_user_id']:
                errors.append('CROSS_USER_PAGINATION')
        if len(document['items']) > document['page']['limit']:
            errors.append('PAGE_LIMIT_EXCEEDED')
        ids = [x['conversation_id'] for x in document['items']]
        if len(set(ids)) != len(ids):
            errors.append('DUPLICATE_PAGE_ITEM')

    elif kind == 'stream_session':
        events = document['events']
        if [e['seq'] for e in events] != list(range(events[0]['seq'], events[0]['seq']+len(events))):
            errors.append('NONCONTIGUOUS_EVENT_SEQUENCE')
        if events[0]['seq'] != 0:
            errors.append('EVENT_SEQUENCE_MUST_START_ZERO')
        for event in events:
            if any(event[field] != document[field] for field in ('stream_id','answer_id','request_id','trace_id')):
                errors.append('STREAM_IDENTITY_MISMATCH')
        endings = [i for i,x in enumerate(events) if x['event_type'] in TERMINALS]
        if len(endings) > 1 or (endings and endings[-1] != len(events)-1):
            errors.append('MULTIPLE_OR_NONFINAL_TERMINAL_EVENTS')
        if document['delivery_state'] == 'terminal' and (len(endings) != 1 or endings[0] != len(events)-1):
            errors.append('TERMINAL_EVENT_REQUIRED')
        if document['delivery_state'] != 'terminal' and endings:
            errors.append('TERMINAL_EVENT_WITH_OPEN_DELIVERY')
        if document['delivery_state'] == 'display_cancelled' and events[-1]['event_type'] != 'display_cancelled':
            errors.append('DISPLAY_CANCEL_TERMINATOR_REQUIRED')
        if document['delivery_state'] != 'display_cancelled' and any(x['event_type']=='display_cancelled' for x in events):
            errors.append('DISPLAY_CANCELLATION_STATE_MISMATCH')
        types = [e['event_type'] for e in events]
        if 'server_cancelled' in types and 'cancel_requested' not in types:
            errors.append('SERVER_CANCEL_WITHOUT_REQUEST')
        if 'completed' in types and events[-1]['data'].get('final_answer_id') != document['answer_id']:
            errors.append('FINAL_ANSWER_ID_MISMATCH')
        if any(x['event_type'] in {'retrieving','generating'} and x['data'].get('reported_by')!='backend' for x in events):
            errors.append('UNCONFIRMED_BACKEND_PHASE')
        if 'display_cancelled' in types and 'server_cancelled' in types:
            errors.append('DISPLAY_ONLY_MUST_NOT_CLAIM_SERVER_STOP')
    return sorted(set(errors))


def canonical_feedback_fingerprint(request):
    """Stable request-only SHA-256; no auth identity, response or retry attempt fields."""
    if request['kind'] != 'feedback_submit_request':
        raise ValueError('NOT_FEEDBACK_SUBMIT_REQUEST')
    stable = {k: request[k] for k in ('client_feedback_id','conversation_id','answer_id','rating','reason')}
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def check_feedback_request_receipt(request, receipt, actor, feedback=None, snapshot=None):
    """Semantic server-side reconciliation; does not authenticate the wire request."""
    if (request.get('kind'), receipt.get('kind'), actor.get('kind')) != (
            'feedback_submit_request','feedback_submit_receipt','trusted_actor_context'):
        return ['WRONG_CONTRACT_KIND']
    errors=[]
    if (actor['principal_source'] != 'server_auth_context' or
            receipt['owner_user_id'] != actor['owner_user_id']):
        errors.append('UNTRUSTED_FEEDBACK_OWNER')
    for key in ('client_feedback_id','conversation_id','answer_id','idempotency_key'):
        if receipt[key] != request[key]:
            errors.append('FEEDBACK_RECEIPT_MISMATCH_'+key.upper())
    if receipt['idempotency_scope'] != 'trusted_user+submit_feedback+answer':
        errors.append('FEEDBACK_IDEMPOTENCY_SCOPE_MISMATCH')
    if receipt['payload_sha256'] != canonical_feedback_fingerprint(request):
        errors.append('FEEDBACK_FINGERPRINT_MISMATCH')
    if receipt['disposition'] in {'created','replayed'}:
        if not receipt.get('feedback_id') or not receipt.get('persisted_at') or receipt.get('error') is not None:
            errors.append('FEEDBACK_UNCONFIRMED_PERSISTENCE')
    elif receipt['disposition'] == 'conflict':
        if receipt.get('feedback_id') is not None or receipt.get('persisted_at') is not None or receipt.get('error') is None:
            errors.append('FEEDBACK_CONFLICT_CANNOT_SUCCEED')
    if snapshot is not None:
        conv=snapshot.get('conversation', {})
        if (snapshot.get('kind')!='conversation_snapshot' or
                conv.get('owner_user_id')!=actor['owner_user_id'] or
                conv.get('conversation_id')!=request['conversation_id'] or
                not any(a.get('answer_id')==request['answer_id'] and
                        a.get('conversation_id')==request['conversation_id']
                        for a in snapshot.get('answers', []))):
            errors.append('FEEDBACK_TARGET_NOT_OWNED_OR_MISSING')
    if feedback is not None:
        if receipt['disposition'] not in {'created','replayed'} or feedback.get('kind') != 'feedback':
            errors.append('FEEDBACK_DOCUMENT_NOT_CONFIRMED')
        else:
            comparisons={'feedback_id':receipt['feedback_id'], 'owner_user_id':receipt['owner_user_id'],
                         'conversation_id':request['conversation_id'],'answer_id':request['answer_id'],
                         'rating':request['rating'],'reason':request['reason'], 'created_at':receipt['persisted_at']}
            if any(feedback.get(k)!=v for k,v in comparisons.items()):
                errors.append('FEEDBACK_DOCUMENT_RELATION_MISMATCH')
    return sorted(set(errors))


def check_feedback_receipt_history(receipts):
    """Persist/replay consistency inside server-trusted user+answer+client id scope."""
    errors=[];grouped={}
    for receipt in receipts:
        if receipt.get('kind')!='feedback_submit_receipt':
            errors.append('NOT_A_FEEDBACK_RECEIPT');continue
        scope=(receipt['owner_user_id'],receipt['idempotency_scope'],receipt['answer_id'],
               receipt['client_feedback_id'],receipt['idempotency_key'])
        previous=grouped.get(scope)
        if previous is None:
            if receipt['disposition']!='created':
                errors.append('FIRST_FEEDBACK_RECEIPT_MUST_CREATE')
            grouped[scope]=receipt;continue
        if receipt['payload_sha256']==previous['payload_sha256']:
            if (receipt['disposition']!='replayed' or
                    receipt['feedback_id']!=previous['feedback_id'] or
                    receipt['persisted_at']!=previous['persisted_at'] or
                    receipt['conversation_id']!=previous['conversation_id']):
                errors.append('FEEDBACK_RETRY_MUST_REPLAY_SAME_RECORD')
        elif receipt['disposition']!='conflict' or receipt['feedback_id'] is not None or receipt['persisted_at'] is not None:
            errors.append('FEEDBACK_IDEMPOTENCY_KEY_PAYLOAD_CONFLICT')
    return sorted(set(errors))


def check_delete_command_status(command, status, actor):
    """Server receipt reconciliation: client action vs server trace and authenticated owner."""
    if (command.get('kind'),status.get('kind'),actor.get('kind')) != (
            'delete_command','delete_status','trusted_actor_context'):
        return ['WRONG_CONTRACT_KIND']
    errors=[]
    if actor['principal_source']!='server_auth_context' or status['owner_user_id']!=actor['owner_user_id']:
        errors.append('UNAUTHORIZED_DELETION_OWNER')
    for field in ('client_action_id','deletion_scope','conversation_id'):
        if command[field]!=status[field]:errors.append('DELETION_MISMATCH_'+field.upper())
    if status['request_id']!=actor['request_id'] or status['trace_id']!=actor['trace_id']:
        errors.append('DELETION_TRACE_NOT_SERVER_MINTED')
    return sorted(set(errors))


def check_delete_status_query(query, status, actor):
    """Polling ID is merely a locator; actual access requires a new trusted actor check."""
    if (query.get('kind'),status.get('kind'),actor.get('kind')) != (
            'delete_status_query','delete_status','trusted_actor_context'):
        return ['WRONG_CONTRACT_KIND']
    errors=[]
    if actor['principal_source']!='server_auth_context' or status['owner_user_id']!=actor['owner_user_id']:
        errors.append('UNAUTHORIZED_DELETION_STATUS_ACCESS')
    if query['deletion_request_id']!=status['deletion_request_id'] or query['client_action_id']!=status['client_action_id']:
        errors.append('DELETION_STATUS_QUERY_MISMATCH')
    # Status request_id/trace_id belong to the original server operation; polling can have a new trusted request trace.
    return sorted(set(errors))


def check_idempotency_history(receipts):
    """Receipts are SERVER generated. Prevent duplicate persistence claims, not provider exactly-once."""
    errors = []
    grouped = {}
    for r in receipts:
        if r['kind'] != 'send_message_receipt':
            errors.append('NOT_A_RECEIPT')
            continue
        scope = (r['owner_user_id'], r['idempotency_scope'], r['requested_conversation_id'], r['client_message_id'], r['idempotency_key'])
        old = grouped.get(scope)
        if old is None:
            if r['disposition'] != 'created':
                errors.append('FIRST_RECEIPT_MUST_CREATE')
            grouped[scope] = r
            continue
        same_payload = r['payload_sha256'] == old['payload_sha256']
        if same_payload:
            if r['disposition'] != 'replayed' or r['message_id'] != old['message_id']:
                errors.append('RETRY_MUST_REPLAY_SAME_PERSISTED_MESSAGE')
            if r['resolved_conversation_id'] != old['resolved_conversation_id']:
                errors.append('RETRY_MUST_REPLAY_SAME_RESOLVED_CONVERSATION')
        else:
            if r['disposition'] != 'conflict' or r['message_id'] is not None or r['resolved_conversation_id'] is not None:
                errors.append('IDEMPOTENCY_KEY_PAYLOAD_CONFLICT')
    return sorted(set(errors))


def canonical_request_fingerprint(request):
    """Compute server-side fingerprint of exactly the stable client payload keys."""
    if request['kind'] != 'send_message_request':
        raise ValueError('NOT_SEND_MESSAGE_REQUEST')
    stable = {k: request[k] for k in ('client_message_id','requested_conversation_id','question')}
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def check_request_receipt(request, receipt, actor):
    """A server-only consistency check; authentication provider is not selected."""
    errors = []
    if request['kind'] != 'send_message_request' or receipt['kind'] != 'send_message_receipt' or actor['kind'] != 'trusted_actor_context':
        return ['WRONG_CONTRACT_KIND']
    if actor['principal_source'] != 'server_auth_context' or receipt['owner_user_id'] != actor['owner_user_id']:
        errors.append('UNTRUSTED_IDENTITY')
    for key in ('requested_conversation_id','client_message_id','idempotency_key'):
        if receipt[key] != request[key]:
            errors.append('RECEIPT_REQUEST_MISMATCH_' + key.upper())
    requested = request['requested_conversation_id']
    resolved = receipt['resolved_conversation_id']
    if receipt['disposition'] in {'created', 'replayed'}:
        if resolved is None:
            errors.append('SUCCESS_RECEIPT_MISSING_RESOLVED_CONVERSATION')
        elif requested is not None and resolved != requested:
            errors.append('RESOLVED_CONVERSATION_MISMATCH')
    elif resolved is not None:
        errors.append('CONFLICT_MUST_NOT_ALLOCATE_CONVERSATION')
    if receipt['payload_sha256'] != canonical_request_fingerprint(request):
        errors.append('PAYLOAD_FINGERPRINT_MISMATCH')
    if receipt['request_id'] != actor['request_id'] or receipt['trace_id'] != actor['trace_id']:
        errors.append('TRACE_CONTEXT_MISMATCH')
    return sorted(set(errors))
