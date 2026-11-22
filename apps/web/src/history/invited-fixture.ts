/**
 * #53 staging.invited_live_result.v1 synthetic-only result consumer.
 * The exact pinned JSON Schema is copied byte-for-byte from API #53.
 * This GET never resends a question, never promotes fixture provenance to a
 * product.v1 Answer and must ONLY be displayed on a server-guarded CI page.
 */
import schema from './fixtures/staging_invited_live_result.v1.schema.json' with {type:'json'};
import {conformsToPinnedSchema} from './product-validation.ts';
import {HistoryFailure,type StatusCorrelation} from './client.ts';

export type FixtureState='PENDING'|'READY'|'FAILED'|'UNKNOWN';
export type FixtureCitation=Readonly<{citation_id:string;source_id:string;
  title:string;evidence_status:'SYNTHETIC_TEST_ONLY';
  excerpt:null;locator:null}>;
export type InvitedFixtureView=Readonly<{
  state:FixtureState;
  requestedConversationId:string|null;conversationId:string;
  clientMessageId:string;idempotencyKey:string;
  attemptId:string|null;attemptRequestId:string|null;attemptTraceId:string|null;
  requestId:string;traceId:string;warning:string;
  answer:{text:string;citations:FixtureCitation[]}|null;
}>;
export function parseInvitedFixture(raw:unknown,original:StatusCorrelation):InvitedFixtureView {
  if(!conformsToPinnedSchema(raw,schema))throw new HistoryFailure(0,'invalid');
  const v=raw as {
    result_status:FixtureState;requested_conversation_id:string|null;
    resolved_conversation_id:string;client_message_id:string;idempotency_key:string;
    attempt_id:string|null;attempt_request_id:string|null;attempt_trace_id:string|null;
    request_id:string;trace_id:string;
    provenance:{warning:string};answer:{text:string;citations:FixtureCitation[]}|null;
  };
  if(v.requested_conversation_id!==original.requested_conversation_id||
     v.client_message_id!==original.client_message_id||
     v.idempotency_key!==original.idempotency_key)
    throw new HistoryFailure(0,'invalid');
  return {state:v.result_status,requestedConversationId:v.requested_conversation_id,
    conversationId:v.resolved_conversation_id,clientMessageId:v.client_message_id,
    idempotencyKey:v.idempotency_key,attemptId:v.attempt_id,
    attemptRequestId:v.attempt_request_id,attemptTraceId:v.attempt_trace_id,
    requestId:v.request_id,traceId:v.trace_id,warning:v.provenance.warning,
    answer:v.answer};
}
export async function recoverInvitedFixture(original:StatusCorrelation):Promise<InvitedFixtureView>{
  const query=new URLSearchParams({
    requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,
    idempotency_key:original.idempotency_key,
  });
  let response:Response;
  try{response=await fetch('/api/history/message-requests/invited-live-result?'+query.toString(),
    {method:'GET',cache:'no-store',credentials:'same-origin'});}
  catch{throw new HistoryFailure(0,'unavailable');}
  if(response.status===401)throw new HistoryFailure(401,'unauthorized');
  if(!response.ok)throw new HistoryFailure(response.status,
    response.status>=500?'unavailable':'invalid');
  let value:unknown;
  try{value=await response.json();}catch{throw new HistoryFailure(0,'invalid');}
  return parseInvitedFixture(value,original);
}
