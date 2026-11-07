/**
 * UI-only, volatile tabs. localId never enters product.v1 wire requests.
 * Browser refresh loses all threads; there is no server history or model memory.
 */
import type { Answer, Scenario, SendReceipt, SendRequest } from '../mock/transport';

export type ChatItem = {
  key:string; request:SendRequest; scenario:Scenario; receipt?:SendReceipt;
  text:string; answer?:Answer; phase:string; terminal?:string; isRunning:boolean;
  cancelRequested:boolean; displayStopped?:boolean; warning?:string;
};
export type LocalThread = {
  localId:string; draft:string; scenario:Scenario;
  resolvedConversationId:string|null; items:ChatItem[];
};
export type WorkspaceState = { threads:LocalThread[]; activeId:string };

export function newLocalThread(localId:string):LocalThread {
  if(!localId.startsWith('local_ui_')) throw new Error('Local thread ID must be UI-only');
  return {localId,draft:'',scenario:'answer',resolvedConversationId:null,items:[]};
}
export function freshLocalId():string {
  return 'local_ui_'+crypto.randomUUID();
}
export function createWorkspace(makeId:()=>string=freshLocalId):WorkspaceState {
  const thread=newLocalThread(makeId());
  return {threads:[thread],activeId:thread.localId};
}
export function activeThread(state:WorkspaceState):LocalThread {
  const thread=state.threads.find(t=>t.localId===state.activeId);
  if(!thread)throw new Error('UI local thread missing');
  return thread;
}
export function updateThread(
  state:WorkspaceState,localId:string,update:(thread:LocalThread)=>LocalThread
):WorkspaceState {
  if(!state.threads.some(t=>t.localId===localId))return state;
  return {...state,threads:state.threads.map(t=>t.localId===localId?update(t):t)};
}
export function selectThread(state:WorkspaceState,localId:string):WorkspaceState {
  return state.threads.some(t=>t.localId===localId)
    ? {...state,activeId:localId}:state;
}
export function openFreshThread(state:WorkspaceState,makeId:()=>string=freshLocalId):WorkspaceState {
  const current=activeThread(state);
  // An unused empty tab is reused. An UNSENT draft is real state and must survive New Chat.
  if(!current.items.length&&current.draft.length===0)return state;
  // Reuse only a truly empty tab (never overwrite or impersonate an unsent draft).
  const empty=state.threads.find(t=>t.items.length===0&&t.draft.length===0);
  if(empty)return {...state,activeId:empty.localId};
  const id=makeId();
  if(state.threads.some(t=>t.localId===id))throw new Error('Duplicate local ID');
  return {...state,threads:[...state.threads,newLocalThread(id)],activeId:id};
}
export function setThreadDraft(state:WorkspaceState,localId:string,draft:string):WorkspaceState {
  return updateThread(state,localId,t=>({...t,draft}));
}
export function setThreadScenario(state:WorkspaceState,localId:string,scenario:Scenario):WorkspaceState {
  return updateThread(state,localId,t=>({...t,scenario}));
}
export function startItem(state:WorkspaceState,localId:string,request:SendRequest,scenario:Scenario):WorkspaceState {
  return updateThread(state,localId,t=>{
    const next:ChatItem={key:request.client_message_id,request,scenario,
      phase:'submitting',text:'',isRunning:true,cancelRequested:false};
    const existing=t.items.findIndex(i=>i.key===next.key);
    const items=existing<0?[...t.items,next]
      :t.items.map(i=>i.key===next.key?next:i);
    return {...t,items};
  });
}
export function patchItem(
  state:WorkspaceState,localId:string,key:string,patch:Partial<ChatItem>
):WorkspaceState {
  return updateThread(state,localId,t=>({...t,items:t.items.map(i=>
    i.key===key?{...i,...patch}:i)}));
}
export function attachResolvedConversation(
  state:WorkspaceState,localId:string,resolvedId:string
):WorkspaceState {
  return updateThread(state,localId,t=>{
    // A replayed receipt must not overwrite an already-confirmed different ID.
    if(t.resolvedConversationId&&t.resolvedConversationId!==resolvedId)return t;
    return {...t,resolvedConversationId:resolvedId};
  });
}
export function threadPreview(thread:LocalThread):string {
  return thread.items[0]?.request.question??thread.draft.trim()??'';
}
