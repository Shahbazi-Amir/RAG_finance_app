/**
 * History UI consumer of the ORIGINAL product.v1 contract and semantic links.
 * Runtime validation loads ../../../../packages/contracts/product.v1.schema.json.
 * These small view projections are not parallel wire DTOs. No browser-selected owner.
 */
import type { SendRequest, Answer } from '../mock/transport';
import { conformsToProductV1 } from './product-validation.ts';

export type ConversationView = { id:string; title:string|null; state:string };
export type MessageView = { id:string; conversationId:string; role:'user'|'assistant'; text:string; answerId:string|null };
export type AnswerView = { id:string; conversationId:string; messageId:string; payload:Answer };
export type HistoryPage<T> = { items:T[]; next:string|null; more:boolean; owner:string };
export type MessagePage = HistoryPage<MessageView> & { answers:AnswerView[]; liveAnswers:Record<string,StagingLiveResult>; conversationId:string };
export type CreateOperation = { kind:'create_conversation_request'; contract_version:'product.v1'; client_conversation_id:string; idempotency_key:string; title:string|null };
export type PendingSend = { request:SendRequest; phase:'sending'|'unknown'|'unconfirmed'|'persisted'|'conflict'|'unauthorized'; messageId:string|null; serverId:string|null };
export type HistoryStatus = 'not_found'|'persisted'|'attempt_pending'|'attempt_unknown'|'answer_committed'|'failed'|'cancelled';
export type EnginePreflightState='NOT_STARTED'|'NOT_RECORDED'|'QUEUED'|'RUNNING'|
  'CONTEXT_READY'|'FAILED'|'UNKNOWN';
export type EngineStatus=Readonly<{state:EnginePreflightState;productStatus:HistoryStatus;
  attemptId:string|null;attemptTraceId:string|null;top10Count:number|null;
  generationCalls:number|null;questionHashMatches:boolean|null}>;
export type RetrievedRow=Readonly<{position:number;chunkId:string;sourceId:string|null;
  chunkMatch:'PASS';sourceValidation:'UNVERIFIED';
  locatorValidation:'PENDING_STRUCTURE';verifiedLocators:readonly []}>;
export type RetrievedSources=Readonly<{attemptId:string|null;attemptTraceId:string|null;
  retrievalState:'NOT_AVAILABLE'|'PARTIAL_UNVERIFIED'|'EVIDENCE_INVALID'|'EVIDENCE_NOT_AVAILABLE';
  generationCalls:0|null;rows:readonly RetrievedRow[]}>;

type Wire = Record<string,unknown>;

export class HistoryFailure extends Error {
  readonly status:number;
  readonly reason:'unauthorized'|'conflict'|'invalid'|'unavailable'|'unknown'|'busy';
  constructor(status:number,reason:'unauthorized'|'conflict'|'invalid'|'unavailable'|'unknown'|'busy') {
    super(reason);this.status=status;this.reason=reason;
  }
}
function invalid():never{throw new HistoryFailure(0,'invalid');}
function doc(v:unknown,kind:string):Wire {
  if(!conformsToProductV1(v,kind))invalid();
  return v as Wire;
}
function object(v:unknown):Wire{
  if(v===null||typeof v!=='object'||Array.isArray(v))invalid();
  return v as Wire;
}
function text(v:unknown):string{
  if(typeof v!=='string'||!v)invalid();
  return v;
}
function maybeText(v:unknown):string|null{
  return v===null?null:text(v);
}
function list(v:unknown):Wire[]{
  if(!Array.isArray(v))invalid();
  return v.map(object);
}
function unique(values:string[]):void{
  if(new Set(values).size!==values.length)invalid();
}
function timestampMicros(value:string):number{
  // PostgreSQL timestamps have microsecond precision. Date.parse() truncates
  // fractional seconds to milliseconds, which silently destroys the actual
  // SQL (created_at,id) sort order for rapid consecutive History messages.
  // This is critical for cursor pages of 31+ messages and real owner reads.
  const millis=Date.parse(value);
  const fractional=/\.(\d+)(?:Z|[+-]\d\d:\d\d)$/i.exec(value)?.[1]??'';
  if(!Number.isFinite(millis)||
     (fractional.length>6&&/[1-9]/.test(fractional.slice(6))))invalid();
  const submillis=Number(fractional.padEnd(6,'0').slice(3,6));
  const micros=millis*1000+submillis;
  if(!Number.isSafeInteger(micros))invalid();
  return micros;
}
function pagination(o:Wire,requestedLimit:number,numberOfItems:number):{next:string|null;more:boolean}{
  const p=object(o.page);
  if(p.limit!==requestedLimit||numberOfItems>requestedLimit)invalid();
  // The actual shared JSON Schema enforces both directions of cursor/has_more.
  return {next:maybeText(p.next_cursor),more:p.has_more as boolean};
}
function ensureAnswerRelations(answer:Answer):void{
  const claims=new Map(answer.claims.map(c=>[c.claim_id,c]));
  const citations=new Map(answer.citations.map(c=>[c.citation_id,c]));
  if(claims.size!==answer.claims.length||citations.size!==answer.citations.length)invalid();
  for(const claim of answer.claims){
    for(const id of claim.citation_ids)
      if(!citations.has(id)||!citations.get(id)!.claim_ids.includes(claim.claim_id))invalid();
  }
  for(const cite of answer.citations){
    for(const id of cite.claim_ids)
      if(!claims.has(id)||!claims.get(id)!.citation_ids.includes(cite.citation_id))invalid();
  }
  if(answer.provenance.origin==='SYNTHETIC'&&answer.citations.some(c=>
    c.source.resolution_status==='verified'||c.source.attribution_status==='verified'||
    (c.source.display_title!==null&&c.source.display_title!==undefined&&
      c.source.display_title_origin!=='SYNTHETIC')))invalid();
  if(answer.outcome==='error'&&object((answer as unknown as Wire).error).category!=='technical')invalid();
  if(answer.outcome==='partial'&&answer.answer_text===null)invalid();
  if((answer.outcome==='unknown'||answer.outcome==='cancelled')&&answer.claims.length)invalid();
}
function validatedAnswer(raw:unknown):Answer {
  const value=doc(raw,'answer') as unknown as Answer;
  ensureAnswerRelations(value);
  return value;
}
export function newSend(question:string,originalId:string|null):SendRequest {
  return {kind:'send_message_request',contract_version:'product.v1',requested_conversation_id:originalId,
    client_message_id:'uih_'+crypto.randomUUID().replaceAll('-',''),question,
    idempotency_key:'key_'+crypto.randomUUID().replaceAll('-','')};
}
export function newCreate(title:string|null):CreateOperation {
  return {kind:'create_conversation_request',contract_version:'product.v1',
    client_conversation_id:'uih_'+crypto.randomUUID().replaceAll('-',''),
    idempotency_key:'key_'+crypto.randomUUID().replaceAll('-',''),title};
}
export function mergeUnique<T>(left:T[],right:T[],key:(value:T)=>string):T[]{
  const ids=new Set(left.map(key));
  return [...left,...right.filter(value=>{const id=key(value);if(ids.has(id))return false;ids.add(id);return true;})];
}
async function api(path:string, method:'GET'|'POST'='GET',payload?:unknown):Promise<unknown>{
  let response:Response;
  try{
    response=await fetch('/api/history/'+path,{method,cache:'no-store',credentials:'same-origin',
      headers:payload===undefined?undefined:{'Content-Type':'application/json'},
      body:payload===undefined?undefined:JSON.stringify(payload)});
  }catch{throw new HistoryFailure(0,'unknown');}
  if(!response.ok){
    if(response.status===401)throw new HistoryFailure(401,'unauthorized');
    if(response.status===409)throw new HistoryFailure(409,'conflict');
    if(method==='POST'&&response.status===503){
      const body:unknown=await response.json().catch(()=>null);
      if(conformsToProductV1(body,'error_response')&&
         (body as {error:{code:string}}).error.code==='ENGINE_BUSY')
        throw new HistoryFailure(503,'busy');
    }
    if(method==='POST'&&response.status>=500)throw new HistoryFailure(response.status,'unknown');
    throw new HistoryFailure(response.status,response.status>=500?'unavailable':'invalid');
  }
  try{return await response.json();}catch{throw new HistoryFailure(0,'invalid');}
}
function params(input:Record<string,string|number|null>):string{
  const q=new URLSearchParams();
  for(const [k,v] of Object.entries(input)) if(v!==null)q.set(k,String(v));
  return q.toString();
}
export async function conversations(limit=2,cursor:string|null=null):Promise<HistoryPage<ConversationView>>{
  const o=doc(await api('conversations?'+params({limit,cursor})),'conversation_page');
  const owner=text(o.scope_user_id);
  const raw=list(o.items),seen:string[]=[];
  const items=raw.map(v=>{
    const c=doc(v,'conversation');
    if(c.owner_user_id!==owner||c.state!=='active')invalid();
    seen.push(text(c.conversation_id));
    return {id:text(c.conversation_id),title:maybeText(c.title),state:text(c.state)};
  });
  unique(seen);
  // Cross-document pagination semantics: owner, size, newest-first ordering.
  const order=raw.map(v=>[timestampMicros(text(v.created_at)),text(v.conversation_id)] as const);
  for(let i=1;i<order.length;i++)
    if(order[i-1][0]<order[i][0]||
       (order[i-1][0]===order[i][0]&&order[i-1][1]<order[i][1]))invalid();
  return {...pagination(o,limit,items.length),items,owner};
}
export async function messages(conversationId:string,limit=2,cursor:string|null=null):Promise<MessagePage>{
  const {staging_live_answers,...page}=object(await api('conversations/'+encodeURIComponent(conversationId)+'/messages?'+
    params({limit,cursor})));
  const o=doc(page,'conversation_messages_page');
  const owner=text(o.owner_user_id);
  if(o.conversation_id!==conversationId)invalid();
  const raw=list(o.items);
  const items=raw.map(v=>{
    const m=doc(v,'message');
    if(m.owner_user_id!==owner||m.conversation_id!==conversationId)invalid();
    if(m.role==='user'&&m.answer_id!==null)invalid();
    if(m.role==='assistant'&&m.answer_id===null)invalid();
    return {id:text(m.message_id),conversationId,role:m.role as 'user'|'assistant',
      text:text(m.text),answerId:maybeText(m.answer_id)};
  });
  unique(items.map(x=>x.id));
  const order=raw.map(v=>[timestampMicros(text(v.created_at)),text(v.message_id)] as const);
  for(let i=1;i<order.length;i++)
    if(order[i-1][0]>order[i][0]||
       (order[i-1][0]===order[i][0]&&order[i-1][1]>order[i][1]))invalid();
  const assistants=items.filter(x=>x.role==='assistant');
  unique(assistants.map(x=>x.answerId!));
  const byAnswer=new Map(assistants.map(x=>[x.answerId!,x.id]));
  const answers=list(o.answers).map(v=>{
    const a=validatedAnswer(v);
    if(a.conversation_id!==conversationId||byAnswer.get(a.answer_id)!==a.message_id)invalid();
    return {id:a.answer_id,conversationId,messageId:a.message_id,payload:a};
  });
  unique(answers.map(x=>x.id));
  // Exact page coverage: no missing, orphaned, duplicate or unrelated Answer.
  if(answers.length!==assistants.length)invalid();
  const visibleQuestions=new Set(items.filter(x=>x.role==='user').map(x=>x.id));
  const liveAnswers:Record<string,StagingLiveResult>=Object.create(null);
  if(staging_live_answers!==undefined){
    for(const [id,value] of Object.entries(object(staging_live_answers))){
      const result=liveResult(value);
      if(!visibleQuestions.has(id)||result.state!=='READY')invalid();
      liveAnswers[id]=result;
    }
  }
  return {...pagination(o,limit,items.length),items,answers,liveAnswers,conversationId,owner};
}
export async function createConversation(original:CreateOperation):Promise<string>{
  const o=doc(await api('conversations','POST',original),'create_conversation_receipt');
  if(o.client_conversation_id!==original.client_conversation_id||
     o.idempotency_key!==original.idempotency_key)invalid();
  const c=doc(o.conversation,'conversation');
  if(c.owner_user_id!==o.owner_user_id||c.state!=='active'||c.title!==original.title)invalid();
  return text(c.conversation_id);
}
function acceptedReceipt(payload:unknown, original:SendRequest):{id:string;messageId:string}{
  const o=doc(payload,'send_message_receipt');
  if(o.requested_conversation_id!==original.requested_conversation_id||
     o.client_message_id!==original.client_message_id||
     o.idempotency_key!==original.idempotency_key)invalid();
  if(o.disposition==='conflict')throw new HistoryFailure(409,'conflict');
  if(o.disposition!=='created'&&o.disposition!=='replayed')invalid();
  if(original.requested_conversation_id!==null&&
     o.resolved_conversation_id!==original.requested_conversation_id)invalid();
  return {id:text(o.resolved_conversation_id),messageId:text(o.message_id)};
}
export async function sendMessage(original:SendRequest):Promise<{id:string;messageId:string}>{
  return acceptedReceipt(await api('messages','POST',original),original);
}
/** Poll is a GET of the original opaque correlators; it must not need the
 * question or accept a newly created Send payload after refresh. */
export type StatusCorrelation=Pick<SendRequest,
  'requested_conversation_id'|'client_message_id'|'idempotency_key'>;
export type StagingLiveResult=Readonly<{
  state:'PENDING'|'READY'|'UNKNOWN'|'REVIEW_REQUIRED';
  outcome:'ANSWER'|'NO_ANSWER'|null;
  claims:ReadonlyArray<Readonly<{text:string;quote:string;chunk_id:string}>>;
}>;
export async function recoverLiveResult(original:StatusCorrelation,attemptId:string,
  traceId:string|null):Promise<StagingLiveResult>{
  const value=await api('message-requests/live-result?'+params({
    requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key
  }));
  if(!value||typeof value!=='object')return invalid();
  const o=value as Record<string,unknown>;
  if(o.kind!=='arvan_staging_live_result'||o.contract_version!=='staging.arvan_live_result.v1'||
     o.attempt_id!==attemptId||
     o.attempt_trace_id!==traceId||!Array.isArray(o.claims))return invalid();
  return liveResult(o);
}
function liveResult(value:unknown):StagingLiveResult{
  const o=object(value);
  if(!Array.isArray(o.claims))return invalid();
  const {state,outcome,claims}=o;
  if(state==='READY'){
    if(outcome==='NO_ANSWER'&&claims.length===0)return {state,outcome,claims:[]};
    if(outcome!=='ANSWER'||claims.length<1||claims.length>5)return invalid();
    return {state,outcome,claims:claims.map(claim=>{
      if(!claim||typeof claim!=='object'||Array.isArray(claim))return invalid();
      const bounded=(key:string,max:number)=>{
        const value=claim[key];
        if(typeof value!=='string'||!value.trim()||[...value].length>max)return invalid();
        return value;
      };
      return {text:bounded('text',2000),quote:bounded('quote',2000),chunk_id:bounded('chunk_id',256)};
    })};
  }
  if((state!=='PENDING'&&state!=='UNKNOWN'&&state!=='REVIEW_REQUIRED')||
     outcome!==null||claims.length!==0)return invalid();
  return {state,outcome,claims:[]};
}
export async function recoverStatus(original:StatusCorrelation):Promise<{
  status:HistoryStatus;id:string|null;messageId:string|null;answer:Answer|null;
  attemptId:string|null;attemptRequestId:string|null;attemptTraceId:string|null
}>{
  let response:unknown;
  try{response=await api('message-requests/status?'+params({
    requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key
  }));}catch(e){
    if(e instanceof HistoryFailure&&e.status===404)return {status:'not_found',id:null,messageId:null,answer:null,
      attemptId:null,attemptRequestId:null,attemptTraceId:null};
    throw e;
  }
  const o=doc(response,'message_request_status');
  if(o.requested_conversation_id!==original.requested_conversation_id||
     o.client_message_id!==original.client_message_id||
     o.idempotency_key!==original.idempotency_key)invalid();
  // Full enum and required/null T1/T2/T3 constraints come from product.v1.
  const status=o.status as HistoryStatus;
  const id=maybeText(o.resolved_conversation_id);
  const messageId=maybeText(o.message_id);
  if(id!==null&&original.requested_conversation_id!==null&&
     id!==original.requested_conversation_id)invalid();
  const answer=o.answer===null?null:validatedAnswer(o.answer);
  if(status==='answer_committed'){
    if(!answer||!id||!messageId||answer.answer_id!==o.answer_id||
       answer.answer_id!==o.reserved_answer_id||
       answer.conversation_id!==id||
       answer.message_id===messageId|| // messageId is USER's persisted T1 message.
       answer.request_id!==o.attempt_request_id||
       answer.trace_id!==o.attempt_trace_id||
       answer.state==='unknown'||answer.state==='cancelled')invalid();
  }
  // The current status poll's request_id/trace_id are NOT the historical T2
  // attempt trace. Only the T2 attempt fields may link a committed Answer.
  return {status,id,messageId,answer,
    attemptId:maybeText(o.attempt_id),attemptRequestId:maybeText(o.attempt_request_id),
    attemptTraceId:maybeText(o.attempt_trace_id)};
}
/** API #53 technical GET. It is NOT a product.v1 Answer or a citation.
 * Only the original three correlators are transmitted; no POST or question.
 * Cross-check attempt identity against the independently authenticated Product
 * Status when both reads expose one. Server status is trusted only via BFF.
 */
export async function recoverEngineStatus(original:StatusCorrelation):Promise<EngineStatus|null>{
  const query=params({requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key});
  let raw:unknown;
  try{raw=await api('message-requests/engine-status?'+query);}
  catch(e){if(e instanceof HistoryFailure&&e.status===404)return null;throw e;}
  const o=object(raw);
  const fields=['kind','contract_version','request_id','trace_id',
    'attempt_id','attempt_trace_id','product_status','preflight_state',
    'question_sha256_matches','top10_count','generation_calls',
    'dispatch_performed','answer'];
  if(Object.keys(o).sort().join('|')!==fields.sort().join('|')||
     o.kind!=='no_dispatch_execution_status'||
     o.contract_version!=='api.no_dispatch_status.v1'||
     o.dispatch_performed!==false||o.answer!==null)invalid();
  text(o.request_id);text(o.trace_id);
  const attemptId=maybeText(o.attempt_id),attemptTraceId=maybeText(o.attempt_trace_id);
  if(attemptId!==null&&!/^[a-f0-9]{32}$/.test(attemptId))invalid();
  if((attemptId===null)!==(attemptTraceId===null))invalid();
  const statuses:HistoryStatus[]=['not_found','persisted','attempt_pending',
    'attempt_unknown','answer_committed','failed','cancelled'];
  const states:EnginePreflightState[]=['NOT_STARTED','NOT_RECORDED','QUEUED',
    'RUNNING','CONTEXT_READY','FAILED','UNKNOWN'];
  if(!statuses.includes(o.product_status as HistoryStatus)||
     !states.includes(o.preflight_state as EnginePreflightState))invalid();
  if(o.question_sha256_matches!==null&&typeof o.question_sha256_matches!=='boolean')invalid();
  const metric=(v:unknown)=>v===null?null:
    Number.isSafeInteger(v)&&Number(v)>=0?Number(v):invalid();
  const top10Count=metric(o.top10_count),generationCalls=metric(o.generation_calls);
  if(o.preflight_state==='CONTEXT_READY'&&
     (top10Count!==10||generationCalls!==0||o.question_sha256_matches!==true))
    invalid();
  if(o.preflight_state==='NOT_STARTED'&&attemptId!==null)invalid();
  return {state:o.preflight_state as EnginePreflightState,
    productStatus:o.product_status as HistoryStatus,attemptId,attemptTraceId,
    top10Count,generationCalls,
    questionHashMatches:o.question_sha256_matches as boolean|null};
}
/** Distinct C018 retrieval observations, NEVER product.v1 citations or LIVE_VERIFIED.
 * GET uses original signed correlators and must not execute C018 or POST again.
 */
export async function recoverRetrievedSources(original:StatusCorrelation):Promise<RetrievedSources|null>{
  const query=params({requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key});
  let raw:unknown;
  try{raw=await api('message-requests/retrieved-sources?'+query);}
  catch(e){if(e instanceof HistoryFailure&&e.status===404)return null;throw e;}
  const o=object(raw);
  const fields=['kind','contract_version','attempt_id','attempt_trace_id',
    'retrieval_state','engine_sha256','chunks_sha256','generation_calls','rows'];
  if(Object.keys(o).sort().join('|')!==fields.sort().join('|')||
     o.kind!=='retrieved_sources'||o.contract_version!=='api.retrieved_sources.v1'||
     o.engine_sha256!=='93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d'||
     o.chunks_sha256!=='3891c4ecad9332ba753cd605bbccd99da9d063f64934a30ee39e495349cffb50')invalid();
  const attemptId=maybeText(o.attempt_id),attemptTraceId=maybeText(o.attempt_trace_id);
  if((attemptId===null)!==(attemptTraceId===null)||
     (attemptId!==null&&!/^[0-9a-f]{32}$/.test(attemptId))||
     (attemptTraceId!==null&&!/^[0-9a-f]{32}$/.test(attemptTraceId)))invalid();
  const states=['NOT_AVAILABLE','PARTIAL_UNVERIFIED','EVIDENCE_INVALID',
    'EVIDENCE_NOT_AVAILABLE'] as const;
  if(!states.includes(o.retrieval_state as typeof states[number])||
     (o.generation_calls!==0&&o.generation_calls!==null)||
     !Array.isArray(o.rows)||o.rows.length>10)invalid();
  const rows:RetrievedRow[]=o.rows.map((rawRow:unknown,index:number)=>{
    const r=object(rawRow);
    const rowFields=['position','chunk_id','chunk_match','source_id','source_validation',
      'locator_validation','verified_locators'];
    if(Object.keys(r).sort().join('|')!==rowFields.sort().join('|')||
       r.position!==index+1||r.chunk_match!=='PASS'||
       r.source_validation!=='UNVERIFIED'||
       r.locator_validation!=='PENDING_STRUCTURE'||
       !Array.isArray(r.verified_locators)||r.verified_locators.length!==0)invalid();
    const chunkId=text(r.chunk_id);
    const sourceId=maybeText(r.source_id);
    if(chunkId.length>256||(sourceId!==null&&sourceId.length>256))invalid();
    return {position:index+1,chunkId,sourceId,chunkMatch:'PASS',
      sourceValidation:'UNVERIFIED',locatorValidation:'PENDING_STRUCTURE',
      verifiedLocators:[]};
  });
  if(o.retrieval_state!=='PARTIAL_UNVERIFIED'&&rows.length>0)invalid();
  if(o.retrieval_state==='PARTIAL_UNVERIFIED'&&
     (attemptId===null||o.generation_calls!==0))invalid();
  return {attemptId,attemptTraceId,
    retrievalState:o.retrieval_state as RetrievedSources['retrievalState'],
    generationCalls:o.generation_calls as 0|null,rows};
}

export function failureLabel(err:unknown):string{
  if(!(err instanceof HistoryFailure))return 'خطای نامشخص؛ وضعیت ثبت تأیید نشده است.';
  if(err.reason==='unauthorized')return 'نشست شما معتبر نیست؛ دوباره از صفحهٔ ورود وارد شوید.';
  if(err.reason==='conflict')return 'تعارض درخواست؛ این پیام ثبت موفق جدید نیست.';
  if(err.reason==='unknown')return 'نتیجهٔ شبکه نامعلوم است؛ ثبت پیام تأیید نشده است.';
  if(err.reason==='unavailable')return 'ارتباط تاریخچه با API در دسترس نیست؛ به Mock منتقل نمی‌شوید.';
  return 'درخواست تاریخچه معتبر نیست یا پاسخ سرور قابل تأیید نیست.';
}
