import {bootstrap} from '../../../../src/auth/server/initial-bootstrap.ts';
import {findInitForState,claimInit,digest,equals,fresh,writePending,
  activate,revokeAlias} from '../../../../src/auth/server/initial-store.ts';
import {INIT,SESSION,cookie,secureBrowser,appendCookie,noStore,
  redirectLocal} from '../../../../src/auth/server/initial-browser.ts';

export const runtime='nodejs';
export const dynamic='force-dynamic';
type Pending={attemptId:string;receiptId:string;ownerId:string;epoch:number;
  generation:number;sessionVerifier:string};
function parsePending(v:Record<string,unknown>,attemptId:string):Pending|null{
  if(v.state!=='ISSUED_PENDING_BINDING'||v.attempt_id!==attemptId||
     typeof v.receipt_id!=='string'||typeof v.owner_id!=='string'||
     typeof v.session_verifier!=='string'||
     !Number.isSafeInteger(v.epoch)||!Number.isSafeInteger(v.generation))
    return null;
  return {attemptId,receiptId:v.receipt_id,ownerId:v.owner_id,
    epoch:Number(v.epoch),generation:Number(v.generation),
    sessionVerifier:v.session_verifier};
}
function invalid():Response{return redirectLocal('/login?reason=auth_failed');}
export async function GET(request:Request):Promise<Response>{
  if(!secureBrowser(request))return new Response('Unavailable',{status:503,headers:noStore});
  const initiator=cookie(request,INIT);
  const params=new URL(request.url).searchParams;
  const code=params.getAll('code'),state=params.getAll('state'),issuer=params.getAll('iss');
  if(!initiator||code.length!==1||state.length!==1||issuer.length>1||
      !code[0]||code[0].length>2048||!state[0]||state[0].length>512||
      [...params.keys()].some(k=>!['code','state','iss','session_state'].includes(k))||
      params.getAll('session_state').length>1||params.has('error'))
    return invalid();
  try{
    const init=await findInitForState(state[0]);
    if(!init||!equals(init.initiatorHash,digest(initiator))||
       !await claimInit(init.attemptId))return invalid();
    const fields={attempt_id:init.attemptId,initiator_sha256:init.initiatorHash};
    const payload:Record<string,unknown>={...fields,
      bff_attempt_id:init.bffAttemptId,state:state[0],code:code[0]};
    if(issuer.length)payload.callback_issuer=issuer[0];
    const complete=await bootstrap('complete',payload);
    if(complete.status!==201)return new Response('Login unavailable',
      {status:complete.status===202?503:401,headers:noStore});
    const pending=parsePending(complete.data,init.attemptId);
    if(!pending)return new Response('Login unavailable',{status:503,headers:noStore});
    const alias=fresh();
    const abortPayload={...fields,receipt_id:pending.receiptId,
      owner_id:pending.ownerId,epoch:pending.epoch};
    let aliasHash:string;
    try{aliasHash=await writePending(alias,pending);}
    catch{
      // Never issue Cookie. ABORT handles PENDING, not revoke_one ACTIVE.
      await bootstrap('abort',abortPayload).catch(()=>null);
      return new Response('Login unavailable',{status:503,headers:noStore});
    }
    const ackPayload={...abortPayload,alias_sha256:aliasHash};
    let ack;
    try{ack=await bootstrap('ack',ackPayload);}catch{ack=null;}
    if(ack?.status!==200||ack.data.state!=='ACTIVE'){
      // One STATUS for a lost ACK receipt. An ACTIVE result alone is NOT
      // an ACK receipt and cannot authorize Cookie delivery.
      const status=await bootstrap('status',fields).catch(()=>null);
      if(status?.status===200&&status.data.state==='ACTIVE'){
        ack=await bootstrap('ack',ackPayload).catch(()=>null); // same receipt; fresh JTI
      }
    }
    if(ack?.status!==200||ack.data.state!=='ACTIVE'){
      await revokeAlias(alias);
      return new Response('Login unavailable',{status:503,headers:noStore});
    }
    if(!await activate(alias,pending.receiptId)){
      await revokeAlias(alias);
      return new Response('Login unavailable',{status:503,headers:noStore});
    }
    const response=redirectLocal('/history');
    appendCookie(response,SESSION,alias,500); // CI-only TTL; policy NOT approved
    appendCookie(response,INIT,'',0);
    return response;
  }catch{
    return new Response('Login unavailable',{status:503,headers:noStore});
  }
}
