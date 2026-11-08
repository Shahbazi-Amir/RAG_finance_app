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
export type MessagePage = HistoryPage<MessageView> & { answers:AnswerView[]; conversationId:string };
export type CreateOperation = { kind:'create_conversation_request'; contract_version:'product.v1'; client_conversation_id:string; idempotency_key:string; title:string|null };
export type PendingSend = { request:SendRequest; phase:'sending'|'unknown'|'unconfirmed'|'persisted'|'conflict'|'unauthorized'; messageId:string|null; serverId:string|null };
export type HistoryStatus = 'not_found'|'persisted'|'attempt_pending'|'attempt_unknown'|'answer_committed'|'failed'|'cancelled';
type Wire = Record<string,unknown>;

export class HistoryFailure extends Error {
  readonly status:number;
  readonly reason:'unauthorized'|'conflict'|'invalid'|'unavailable'|'unknown';
  constructor(status:number,reason:'unauthorized'|'conflict'|'invalid'|'unavailable'|'unknown') {
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
  if(answer.outcome==='error'&&answer.error?.category!=='technical')invalid();
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
    if(method==='POST'&&(response.status===503||response.status>=500))throw new HistoryFailure(response.status,'unknown');
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
  const order=raw.map(v=>[Date.parse(text(v.created_at)),text(v.conversation_id)] as const);
  for(let i=1;i<order.length;i++)
    if(order[i-1][0]<order[i][0]||
       (order[i-1][0]===order[i][0]&&order[i-1][1]<order[i][1]))invalid();
  return {...pagination(o,limit,items.length),items,owner};
}
export async function messages(conversationId:string,limit=2,cursor:string|null=null):Promise<MessagePage>{
  const o=doc(await api('conversations/'+encodeURIComponent(conversationId)+'/messages?'+
    params({limit,cursor})),'conversation_messages_page');
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
  const order=raw.map(v=>[Date.parse(text(v.created_at)),text(v.message_id)] as const);
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
  return {...pagination(o,limit,items.length),items,answers,conversationId,owner};
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
export async function recoverStatus(original:SendRequest):Promise<{
  status:HistoryStatus;id:string|null;messageId:string|null;answer:Answer|null
}>{
  let response:unknown;
  try{response=await api('message-requests/status?'+params({
    requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key
  }));}catch(e){
    if(e instanceof HistoryFailure&&e.status===404)return {status:'not_found',id:null,messageId:null,answer:null};
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
  return {status,id,messageId,answer};
}
export function failureLabel(err:unknown):string{
  if(!(err instanceof HistoryFailure))return 'خطای نامشخص؛ وضعیت ثبت تأیید نشده است.';
  if(err.reason==='unauthorized')return 'برای مشاهدهٔ تاریخچه نیاز به ورود معتبر است؛ ورود هنوز راه‌اندازی نشده است.';
  if(err.reason==='conflict')return 'تعارض درخواست؛ این پیام ثبت موفق جدید نیست.';
  if(err.reason==='unknown')return 'نتیجهٔ شبکه نامعلوم است؛ ثبت پیام تأیید نشده است.';
  if(err.reason==='unavailable')return 'ارتباط تاریخچه با API در دسترس نیست؛ به Mock منتقل نمی‌شوید.';
  return 'درخواست تاریخچه معتبر نیست یا پاسخ سرور قابل تأیید نیست.';
}
