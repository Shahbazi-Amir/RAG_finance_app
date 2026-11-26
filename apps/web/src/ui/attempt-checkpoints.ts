/**
 * Per-tab, non-secret correlation only. No question, answer, account identity,
 * session cookie, tokens, or engine payload in browser storage.
 * A Refresh may ONLY GET status for the original operation; never resend POST.
 */
import type {SendRequest} from '../mock/transport';

export const CHECKPOINT_KEY='rag-finance-attempt-correlation-v1';
export type AttemptCheckpoint=Pick<SendRequest,
  'requested_conversation_id'|'client_message_id'|'idempotency_key'> & {
    created_at:number;resolved_conversation_id:string|null
  };
type StoragePort=Pick<Storage,'getItem'|'setItem'|'removeItem'>;
const id=(x:unknown):x is string=>
  typeof x==='string'&&/^[A-Za-z0-9_-]{1,64}$/.test(x);
const key=(x:unknown):x is string=>
  typeof x==='string'&&/^[A-Za-z0-9_-]{8,128}$/.test(x);
function valid(x:unknown):x is AttemptCheckpoint {
  if(!x||typeof x!=='object'||Array.isArray(x))return false;
  const r=x as Record<string,unknown>;
  return (r.requested_conversation_id===null||id(r.requested_conversation_id))&&
    id(r.client_message_id)&&key(r.idempotency_key)&&
    (r.resolved_conversation_id===null||id(r.resolved_conversation_id))&&
    Number.isSafeInteger(r.created_at)&&Number(r.created_at)>0;
}
export function readCheckpoints(storage:StoragePort):AttemptCheckpoint[]{
  try{
    const raw=storage.getItem(CHECKPOINT_KEY);
    if(raw===null)return [];
    const parsed:unknown=JSON.parse(raw);
    if(!Array.isArray(parsed)||parsed.length>48||!parsed.every(valid))return [];
    if(new Set(parsed.map(x=>x.client_message_id)).size!==parsed.length)return [];
    return parsed;
  }catch{return [];}
}
export function retainCheckpoint(storage:StoragePort,record:AttemptCheckpoint):boolean{
  if(!valid(record))return false;
  try{
    const previous=readCheckpoints(storage);
    if(previous.some(p=>p.client_message_id===record.client_message_id&&
      (p.idempotency_key!==record.idempotency_key||
       p.requested_conversation_id!==record.requested_conversation_id)))return false;
    if(previous.length>=48&&!previous.some(p=>p.client_message_id===record.client_message_id))
      return false;
    const next=[...previous.filter(p=>p.client_message_id!==record.client_message_id),record];
    storage.setItem(CHECKPOINT_KEY,JSON.stringify(next));
    // Never dispatch if browser rejected persistence or the operation changed.
    return readCheckpoints(storage).some(p=>p.client_message_id===record.client_message_id&&
      p.idempotency_key===record.idempotency_key);
  }catch{return false;}
}
export function forgetCheckpoint(storage:StoragePort,id:string):void{
  try{
    storage.setItem(CHECKPOINT_KEY,JSON.stringify(
      readCheckpoints(storage).filter(record=>record.client_message_id!==id)));
  }catch{/* session might already be gone */}
}
export function forgetCheckpoints(storage:StoragePort):void{
  try{storage.removeItem(CHECKPOINT_KEY);}catch{/* session might already be gone */}
}
export function statusCorrelators(record:AttemptCheckpoint):Pick<SendRequest,
  'requested_conversation_id'|'client_message_id'|'idempotency_key'> {
  return {requested_conversation_id:record.requested_conversation_id,
    client_message_id:record.client_message_id,idempotency_key:record.idempotency_key};
}
