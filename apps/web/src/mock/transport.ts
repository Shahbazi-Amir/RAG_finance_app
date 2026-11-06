/**
 * AGENT-UI-01: SYNTHETIC product.v1 consumer using the shared fixture registry.
 * No Backend, real provider, database or local storage.
 */
import sharedFixtures from '../../../../packages/contracts/fixtures/product.v1.cases.json' with { type: 'json' };

export const CONTRACT_VERSION = 'product.v1' as const;
export const FIXTURE_ORIGIN = 'SYNTHETIC' as const;
export const SCENARIOS = ['answer','partial','no_answer','clarification','refusal','error','unknown','malicious'] as const;
export type Scenario = typeof SCENARIOS[number];
export type SendRequest = {
  kind:'send_message_request';contract_version:'product.v1';requested_conversation_id:string|null;
  client_message_id:string;question:string;idempotency_key:string
};
export type SendReceipt = {
  kind:'send_message_receipt';contract_version:'product.v1';requested_conversation_id:string|null;
  resolved_conversation_id:string|null;client_message_id:string;idempotency_key:string;
  disposition:'created'|'replayed'|'conflict';message_id:string|null;request_id:string;
  trace_id:string;owner_user_id:string;idempotency_scope:'trusted_user+send_message+conversation';
  payload_sha256:string;error:{category:string;code:string;message:string}|null;
};
export type Locator = {kind:string;url:string|null;page:number|null;timestamp_ms:number|null;
  work_id?:string;edition_id?:string;anchor?:string;episode_id?:string;segment_anchor?:string};
export type Source = {
  resolution_status:'unresolved'|'verified';attribution_status:'unknown'|'verified';source_type:string|null;
  source_id:string|null;locator:Locator|null;display_title?:string|null;display_title_origin?:string|null;
  credited_author_name:string|null;editorial_supervisor_name:string|null;speaker_name:string|null;
};
export type Claim = {claim_id:string;text:string;citation_ids:string[]};
export type Citation = {citation_id:string;claim_ids:string[];source:Source};
export type Answer = {
  kind:'answer';state:string;outcome:string;answer_id:string;answer_text:string|null;message_id:string;
  conversation_id:string;request_id:string;trace_id:string;claims:Claim[];citations:Citation[];
  confidence:null|{value:number;meaning:string;calibration_scope:string};
  provenance:{origin:string;rag_binding:{status:string;blocked_by:string|null;adapter_verified:boolean}};
};
export type StreamEvent = {kind:'stream_event';contract_version:'product.v1';seq:number;stream_id:string;answer_id:string;request_id:string;
  trace_id:string;event_type:string;data:Record<string,unknown>};
export type TransportUpdate = {kind:'receipt';receipt:SendReceipt}|{kind:'event';event:StreamEvent}|{kind:'answer';answer:Answer};

const registry = new Map((sharedFixtures.cases as Array<{case_id:string;document:unknown}>)
  .map(f=>[f.case_id,f.document]));
function fixture<T>(id:string):T {
  const found=registry.get(id);
  if(!found) throw new Error('Missing shared fixture: '+id);
  return structuredClone(found) as T;
}
export async function requestFingerprint(req:SendRequest):Promise<string>{
  // The product.v1 canonical payload is sorted compact UTF-8 JSON; do not normalize Unicode/whitespace.
  const stable=JSON.stringify({client_message_id:req.client_message_id,question:req.question,
    requested_conversation_id:req.requested_conversation_id});
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(stable));
  return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
}
export function newRequest(text:string,requestedConversationId:string|null,suffix:string):SendRequest{
  return {kind:'send_message_request',contract_version:CONTRACT_VERSION,
    requested_conversation_id:requestedConversationId,client_message_id:'cmsg_'+suffix,
    question:text,idempotency_key:'idem_'+suffix};
}
export function safeSourceHref(source:Source):string|null{
  if(source.resolution_status!=='verified'||source.locator?.kind!=='url'||!source.locator.url) return null;
  if(source.display_title_origin==='SYNTHETIC') return null;
  try{const url=new URL(source.locator.url);return url.protocol==='https:'?url.href:null}
  catch{return null}
}
export function isRealSourceClaim(source:Source):boolean{
  return source.resolution_status==='verified'&&source.attribution_status==='verified'&&source.display_title_origin!=='SYNTHETIC';
}
export function terminalDisplay(event:StreamEvent):'complete'|'partial'|'failed'|'unknown'|'server-cancelled'|null{
  switch(event.event_type){
    case 'completed':return event.data.final_state==='partial'?'partial':'complete';
    case 'failed':return 'failed';
    case 'unknown':return 'unknown';
    case 'server_cancelled':return event.data.server_stopped===true&&typeof event.data.confirmation_ref==='string'?'server-cancelled':'unknown';
    default:return null;
  }
}
type Saved={hash:string;conversation:string;message:string};
export class MockTransport{
  private receipts=new Map<string,Saved>();
  private cancelRequested=new Set<string>();
  private serial=0;
  requestServerCancellation(requestId:string):void{this.cancelRequested.add(requestId)}
  hasRequestedServerCancellation(requestId:string):boolean{return this.cancelRequested.has(requestId)}
  async *send(req:SendRequest,scenario:Scenario='answer'):AsyncGenerator<TransportUpdate>{
    if(req.kind!=='send_message_request'||req.contract_version!==CONTRACT_VERSION||!req.question.trim())
      throw new Error('Invalid synthetic input');
    const hash=await requestFingerprint(req);
    const scope=['mock_actor','send_message',req.requested_conversation_id??'null',
      req.client_message_id,req.idempotency_key].join('|');
    const previous=this.receipts.get(scope);
    const conflict=!!previous&&previous.hash!==hash;
    this.serial++;
    const requestId='req_mock_'+this.serial;
    const traceId='trace_mock_'+this.serial;
    const conversation=conflict?null:(previous?.conversation??req.requested_conversation_id??'conv_mock_'+this.serial);
    const message=conflict?null:(previous?.message??'msg_mock_'+this.serial);
    if(!previous&&conversation&&message)this.receipts.set(scope,{hash,conversation,message});
    const receipt:SendReceipt={
      kind:'send_message_receipt',contract_version:CONTRACT_VERSION,
      requested_conversation_id:req.requested_conversation_id,resolved_conversation_id:conversation,
      client_message_id:req.client_message_id,idempotency_key:req.idempotency_key,
      disposition:conflict?'conflict':previous?'replayed':'created',
      message_id:message,request_id:requestId,trace_id:traceId,
      owner_user_id:'mock_actor',idempotency_scope:'trusted_user+send_message+conversation',
      payload_sha256:hash,error:conflict?{category:'validation',code:'IDEMPOTENCY_CONFLICT',message:'synthetic conflict'}:null};
    yield {kind:'receipt',receipt};
    if(conflict||!conversation||!message)return;
    const answerId='ans_'+message, streamId='stream_'+requestId;
    let seq=0;
    const makeEvent=(event_type:string,data:Record<string,unknown>):StreamEvent=>({
      kind:'stream_event',contract_version:CONTRACT_VERSION,seq:seq++,stream_id:streamId,answer_id:answerId,
      request_id:requestId,trace_id:traceId,event_type,data});
    const pause=()=>new Promise<void>(resolve=>setTimeout(resolve,65));
    yield {kind:'event',event:makeEvent('connected',{})};
    await pause();
    yield {kind:'event',event:makeEvent('retrieving',{reported_by:'backend'})};
    await pause();
    yield {kind:'event',event:makeEvent('generating',{reported_by:'backend'})};
    await pause();
    const texts:Record<Scenario,string>={
      answer:'این یک پاسخ آزمایشی است،',partial:'این پاسخ آزمایشی ناقص مانده است،',
      no_answer:'برای این پرسش شاهد کافی در نمونه وجود ندارد.',
      clarification:'لطفاً پرسش خود را دقیق‌تر بیان کنید.',
      refusal:'در این نمونه امکان پاسخگویی وجود ندارد.',
      error:'',unknown:'',malicious:'<img src=x onerror=alert(1)> <script>alert(1)</script>'};
    const chunks=scenario==='answer'?['این یک پاسخ',' ','آزمایشی است،','\n','نه پاسخ موتور واقعی.']:
      scenario==='partial'?['این پاسخ',' ','آزمایشی ناقص مانده است،','\n']:
      scenario==='error'||scenario==='unknown'?[]:[texts[scenario]];
    for(const chunk of chunks){
      if(this.cancelRequested.has(requestId))break;
      yield {kind:'event',event:makeEvent('delta',{text:chunk})};
      await pause();
    }
    if(this.cancelRequested.delete(requestId)){
      yield {kind:'event',event:makeEvent('cancel_requested',{effect:'server_requested'})};
      await pause();
      yield {kind:'event',event:makeEvent('server_cancelled',{server_stopped:true,confirmation_ref:'ack_'+requestId})};
      return;
    }
    if(scenario==='error'){
      yield {kind:'event',event:makeEvent('failed',{error:{category:'technical',code:'MOCK_FAILURE',message:'DO_NOT_RENDER_STACK_TRACE'}})};
      return;
    }
    if(scenario==='unknown'){
      yield {kind:'event',event:makeEvent('unknown',{reason:'synthetic transport uncertainty'})};
      return;
    }
    const source=fixture<Answer>('valid_unresolved_source_with_synthetic_display_title');
    const base=scenario==='no_answer'||scenario==='clarification'||scenario==='refusal'
      ?fixture<Answer>('valid_answer_no_answer')
      :scenario==='partial'?fixture<Answer>('valid_answer_partial'):source;
    base.answer_id=answerId;base.conversation_id=conversation;base.message_id=message;
    base.request_id=requestId;base.trace_id=traceId;base.answer_text=chunks.join('');
    base.outcome=scenario==='malicious'?'answer':scenario;
    base.state=scenario==='partial'?'partial':'completed';
    if(scenario==='malicious'&&base.citations[0]){
      base.citations[0].source.display_title='<svg/onload=alert(1)> عنوان ساختگی آزمایشی';
      base.citations[0].source.display_title_origin='SYNTHETIC';
      base.citations[0].source.credited_author_name='<img src=x onerror=alert(1)>';
    }
    yield {kind:'event',event:makeEvent('completed',{final_answer_id:answerId,final_state:base.state==='partial'?'partial':'completed'})};
    yield {kind:'answer',answer:base};
  }
}
