import {randomUUID} from 'node:crypto';
import {bootstrap} from '../../../../src/auth/initial/index.ts';
import {digest,saveInit,fresh} from '../../../../src/auth/initial/index.ts';
import {INIT,cookie,csrf,mutationAllowed,noStore} from
  '../../../../src/auth/initial/index.ts';

export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function POST(request:Request):Promise<Response>{
  const initiator=cookie(request,INIT);
  if(!initiator)return new Response('Login denied',{status:403,headers:noStore});
  try{
    if(!request.headers.get('content-type')?.startsWith('application/x-www-form-urlencoded')||
       Number(request.headers.get('content-length')??'0')>4096)
      return new Response('Login denied',{status:403,headers:noStore});
    const form=await request.formData();
    if([...form.keys()].join(',')!=='csrf'||typeof form.get('csrf')!=='string'||
       !mutationAllowed(request,String(form.get('csrf')),csrf(initiator)))
      return new Response('Login denied',{status:403,headers:noStore});
    const attemptId=randomUUID(),bffAttemptId=randomUUID();
    const initiatorHash=digest(initiator);
    const reply=await bootstrap('start',{
      attempt_id:attemptId,initiator_sha256:initiatorHash,
      bff_attempt_id:bffAttemptId,start_key:fresh()
    });
    if(reply.status!==201||reply.data.attempt_id!==attemptId||
       typeof reply.data.state!=='string'||typeof reply.data.authorize_url!=='string')
      return new Response('Login unavailable',{status:503,headers:noStore});
    const url=new URL(reply.data.authorize_url);
    const expected=process.env.AUTH_CI_IDP_AUTHORIZATION_ORIGIN??'';
    if(url.origin!==expected||!url.pathname.endsWith('/protocol/openid-connect/auth')||
       url.searchParams.get('state')!==reply.data.state||
       url.searchParams.get('code_challenge_method')!=='S256')
      return new Response('Login unavailable',{status:503,headers:noStore});
    await saveInit({attemptId,bffAttemptId,initiatorHash,
      stateHash:digest(reply.data.state),created:Date.now(),status:'INITIATED'});
    const response=new Response(null,{status:303,headers:{...noStore,Location:url.toString()}});
    return response;
  }catch{
    return new Response('Login unavailable',{status:503,headers:noStore});
  }
}
