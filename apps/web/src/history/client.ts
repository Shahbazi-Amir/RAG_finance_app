/**
 * History UI consumer of the existing product.v1 wire contract.
 * View projections below are NOT alternative request/response DTOs.
 * No mock fixture or source of client-selected owner is imported at runtime.
 */
import type { SendRequest, SendReceipt, Answer } from '../mock/transport';

export type ConversationView = { id:string; title:string|null; state:string };
export type MessageView = { id:string; conversationId:string; role:'user'|'assistant'; text:string; answerId:string|null };
export type AnswerView = { id:string; conversationId:string; messageId:string; payload:Answer };
export type HistoryPage<T> = { items:T[]; next:string|null; more:boolean; owner:string };
export type MessagePage = HistoryPage<MessageView> & { answers:AnswerView[]; conversationId:string };
export type CreateOperation = { kind:'create_conversation_request'; contract_version:'product.v1'; client_conversation_id:string; idempotency_key:string; title:string|null };
export type PendingSend = { request:SendRequest; phase:'sending'|'unknown'|'unconfirmed'|'persisted'|'conflict'|'unauthorized'; messageId:string|null; serverId:string|null };
type Wire = Record<string,unknown>;

export class HistoryFailure extends Error {
  readonly status:number;
  readonly reason:'unauthorized'|'conflict'|'invalid'|'unavailable'|'unknown';
  constructor(status:number,reason:'unauthorized'|'conflict'|'invalid'|'unavailable'|'unknown') {
    super(reason);this.status=status;this.reason=reason;
  }
}
function record(v:unknown):Wire{
  if(v===null||typeof v!=='object'||Array.isArray(v)) throw new HistoryFailure(0,'invalid');
  return v as Wire;
}
function field(v:unknown):string{
  if(typeof v!=='string'||!v) throw new HistoryFailure(0,'invalid');
  return v;
}
function optional(v:unknown):string|null{
  return v===null?null:field(v);
}
function wire(v:unknown,kind:string):Wire {
  const o=record(v);
  if(o.kind!==kind||o.contract_version!=='product.v1') throw new HistoryFailure(0,'invalid');
  return o;
}
function page(o:Wire):{next:string|null;more:boolean}{
  const p=record(o.page);
  if(typeof p.has_more!=='boolean')throw new HistoryFailure(0,'invalid');
  const next=optional(p.next_cursor);
  if(p.has_more&&!next)throw new HistoryFailure(0,'invalid');
  return {next,more:p.has_more};
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
  }catch{
    throw new HistoryFailure(0,'unknown');
  }
  if(!response.ok){
    if(response.status===401)throw new HistoryFailure(401,'unauthorized');
    if(response.status===409)throw new HistoryFailure(409,'conflict');
    if(method==='POST'&&(response.status===503||response.status>=500))throw new HistoryFailure(response.status,'unknown');
    throw new HistoryFailure(response.status,response.status>=500?'unavailable':'invalid');
  }
  try{return await response.json();}catch{throw new HistoryFailure(0,'unknown');}
}
function params(input:Record<string,string|number|null>):string{
  const q=new URLSearchParams();
  for(const [k,v] of Object.entries(input)) if(v!==null)q.set(k,String(v));
  return q.toString();
}
export async function conversations(limit=2,cursor:string|null=null):Promise<HistoryPage<ConversationView>>{
  const o=wire(await api('conversations?'+params({limit,cursor})),'conversation_page');
  const owner=field(o.scope_user_id);
  const items=(o.items as unknown[]).map(v=>{
    const c=wire(v,'conversation');
    if(c.owner_user_id!==owner)throw new HistoryFailure(0,'invalid');
    return {id:field(c.conversation_id),title:optional(c.title),state:field(c.state)};
  });
  return {...page(o),items,owner};
}
export async function messages(conversationId:string,limit=2,cursor:string|null=null):Promise<MessagePage>{
  const o=wire(await api('conversations/'+encodeURIComponent(conversationId)+'/messages?'+
    params({limit,cursor})),'conversation_messages_page');
  const owner=field(o.owner_user_id);
  if(o.conversation_id!==conversationId)throw new HistoryFailure(0,'invalid');
  const items=(o.items as unknown[]).map(v=>{
    const m=wire(v,'message');
    if(m.owner_user_id!==owner||m.conversation_id!==conversationId)throw new HistoryFailure(0,'invalid');
    if(m.role!=='user'&&m.role!=='assistant')throw new HistoryFailure(0,'invalid');
    return {id:field(m.message_id),conversationId,role:m.role,text:field(m.text),answerId:optional(m.answer_id)};
  });
  const linked=new Map(items.filter(m=>m.role==='assistant'&&m.answerId).map(m=>[m.answerId,m.id]));
  const answers=(o.answers as unknown[]).map(v=>{
    const a=wire(v,'answer') as unknown as Answer;
    if(a.conversation_id!==conversationId||linked.get(a.answer_id)!==a.message_id)
      throw new HistoryFailure(0,'invalid');
    return {id:a.answer_id,conversationId,messageId:a.message_id,payload:a};
  });
  return {...page(o),items,answers,conversationId,owner};
}
export async function createConversation(original:CreateOperation):Promise<string>{
  const o=wire(await api('conversations','POST',original),'create_conversation_receipt');
  if(o.client_conversation_id!==original.client_conversation_id||
     o.idempotency_key!==original.idempotency_key||
     !['created','replayed'].includes(String(o.disposition)))throw new HistoryFailure(0,'invalid');
  const c=wire(o.conversation,'conversation');
  if(c.owner_user_id!==o.owner_user_id)throw new HistoryFailure(0,'invalid');
  return field(c.conversation_id);
}
function acceptedReceipt(payload:unknown, original:SendRequest):{id:string;messageId:string}{
  const o=wire(payload,'send_message_receipt') as unknown as SendReceipt;
  if(o.requested_conversation_id!==original.requested_conversation_id||
     o.client_message_id!==original.client_message_id||
     o.idempotency_key!==original.idempotency_key)throw new HistoryFailure(0,'invalid');
  if(o.disposition==='conflict')throw new HistoryFailure(409,'conflict');
  if(!['created','replayed'].includes(o.disposition)||o.error!==null||
     !o.message_id||!o.resolved_conversation_id)throw new HistoryFailure(0,'invalid');
  return {id:o.resolved_conversation_id,messageId:o.message_id};
}
export async function sendMessage(original:SendRequest):Promise<{id:string;messageId:string}>{
  return acceptedReceipt(await api('messages','POST',original),original);
}
export async function recoverStatus(original:SendRequest):Promise<{status:string;id:string|null;messageId:string|null;answer:Answer|null}>{
  let response:unknown;
  try{response=await api('message-requests/status?'+params({
    requested_conversation_id:original.requested_conversation_id??'',
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key
  }));}catch(e){
    if(e instanceof HistoryFailure&&e.status===404)return {status:'not_found',id:null,messageId:null,answer:null};
    throw e;
  }
  const o=wire(response,'message_request_status');
  if(o.requested_conversation_id!==original.requested_conversation_id||
     o.client_message_id!==original.client_message_id||
     o.idempotency_key!==original.idempotency_key)throw new HistoryFailure(0,'invalid');
  const status=field(o.status);
  const id=optional(o.resolved_conversation_id),messageId=optional(o.message_id);
  const answer=o.answer===null?null:wire(o.answer,'answer') as unknown as Answer;
  if(answer&&(answer.conversation_id!==id||answer.message_id===messageId))throw new HistoryFailure(0,'invalid');
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
