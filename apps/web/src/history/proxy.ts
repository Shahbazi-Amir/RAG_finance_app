/**
 * CI-only bounded History proxy core. Used by the actual Next route and its
 * Node regression tests; no test-only implementation of the forwarding path.
 * The core limits application-collected bytes, not upstream Node/proxy buffers.
 */
import { boundedJsonBody } from './bounded-body.ts';
import {SESSION,cookie,secureBrowser,noStore} from '../auth/server/initial-browser.ts';
import {getActive,revokeAlias} from '../auth/server/initial-store.ts';
import {productRequest} from '../auth/server/product-session.ts';
import {conformsToProductV1} from './product-validation.ts';
import {stagingRequested,stagingProfile} from '../auth/server/private-staging.ts';
const ciFixture=()=>!stagingRequested()&&process.env.CI==='true'&&
  process.env.GITHUB_ACTIONS==='true'&&
  process.env.AUTH_CI_PRODUCT_CHAT_MODE==='INVITED_RESULT_STUB_CI_ONLY';

const allowed=(parts:string[],method:string):boolean=>
  (parts.length===1&&parts[0]==='conversations'&&['GET','POST'].includes(method))||
  (parts.length===1&&parts[0]==='messages'&&method==='POST')||
  (parts.length===2&&parts[0]==='message-requests'&&
    ['status','engine-status','invited-live-result'].includes(parts[1])&&method==='GET')||
  (parts.length===3&&parts[0]==='conversations'&&/^[A-Za-z0-9_-]{1,64}$/.test(parts[1])&&
    parts[2]==='messages'&&method==='GET');

export async function forwardHistoryProxy(request:Request,path:string[]):Promise<Response>{
  if(!allowed(path,request.method))return new Response(null,{status:404});
  if(path[1]==='invited-live-result'&&!ciFixture())
    return new Response(null,{status:404,headers:noStore});
  // CI-only authenticated path. No browser-selected owner, upstream, or
  // synthetic fallback. The API independently fences the signed session.
  if(process.env.AUTH_CI_LOGIN_MODE==='true'||stagingRequested()){
    if(!secureBrowser(request))return new Response(null,{status:503,headers:noStore});
    const handle=cookie(request,SESSION);
    const active=handle?await getActive(handle):null;
    if(!active)
      return Response.json({error:'AUTH_REQUIRED'},{status:401,headers:noStore});
    if(!stagingRequested()&&process.env.AUTH_CI_DEMO_MODE!=='true')
      return Response.json({error:'SIGNED_PRODUCT_API_NOT_WIRED'},
        {status:503,headers:noStore});
    const query=new URL(request.url).searchParams;
    const listed=path.length===1&&path[0]==='conversations'&&request.method==='GET';
    const thread=path.length===3&&path[0]==='conversations'&&path[2]==='messages'&&request.method==='GET';
    const status=path.length===2&&path[0]==='message-requests'&&path[1]==='status'&&request.method==='GET';
    const engineStatus=path.length===2&&path[0]==='message-requests'&&
      path[1]==='engine-status'&&request.method==='GET';
    const invited=path.length===2&&path[0]==='message-requests'&&
      path[1]==='invited-live-result'&&request.method==='GET';
    const send=path.length===1&&path[0]==='messages'&&request.method==='POST';
    // The pinned #53 signed API has no POST create-conversation endpoint.
    // A new draft becomes a server conversation only with its first Send.
    if(!(listed||thread||status||engineStatus||invited||send))
      return Response.json({error:'PRODUCT_ROUTE_NOT_AVAILABLE'},{status:503,headers:noStore});
    if(send&&(stagingRequested()?stagingProfile().send_mode!=='NO_DISPATCH_ONLY':
      process.env.AUTH_CI_PRODUCT_CHAT_MODE!=='NO_DISPATCH_ONLY'&&
      !ciFixture()))
      return Response.json({error:'LIVE_RUNNER_NOT_APPROVED'},
        {status:503,headers:noStore});
    let signedQuery='',rawBody='';
    if(listed||thread){
      if([...query.keys()].some(k=>!['limit','cursor'].includes(k)||
         query.getAll(k).length!==1))
        return new Response(null,{status:422,headers:noStore});
      const limit=query.get('limit')??'20',cursor=query.get('cursor');
      if(!/^(?:[1-9][0-9]?|100)$/.test(limit)||
         (cursor!==null&&!/^[A-Za-z0-9_-]{1,512}$/.test(cursor)))
        return new Response(null,{status:422,headers:noStore});
      signedQuery='?limit='+limit+(cursor===null?'':'&cursor='+cursor);
    }else if(status||engineStatus||invited){
      const keys=['requested_conversation_id','client_message_id','idempotency_key'];
      if([...query.keys()].some(k=>!keys.includes(k)||query.getAll(k).length!==1)||
         keys.some(k=>!query.has(k)))
        return new Response(null,{status:422,headers:noStore});
      const original=query.get('requested_conversation_id')??'';
      const client=query.get('client_message_id')??'';
      const key=query.get('idempotency_key')??'';
      if(!/^[A-Za-z0-9_-]{0,64}$/.test(original)||
         !/^[A-Za-z0-9_-]{1,64}$/.test(client)||
         !/^[A-Za-z0-9_-]{8,128}$/.test(key))
        return new Response(null,{status:422,headers:noStore});
      signedQuery='?requested_conversation_id='+original+
        '&client_message_id='+client+'&idempotency_key='+key;
    }else{
      if(query.size!==0||request.headers.get('origin')!==publicOrigin()||
         request.headers.get('sec-fetch-site')!=='same-origin'||
         !request.headers.get('content-type')?.startsWith('application/json'))
        return new Response(null,{status:403,headers:noStore});
      const bounded=await boundedJsonBody(request);
      if(!bounded.ok)return new Response(null,{status:bounded.status,headers:noStore});
      try{
        rawBody=new TextDecoder('utf-8',{fatal:true}).decode(bounded.bytes);
        const value:unknown=JSON.parse(rawBody);
        if(!conformsToProductV1(value,'send_message_request'))
          return new Response(null,{status:422,headers:noStore});
      }catch{return new Response(null,{status:422,headers:noStore});}
    }
    try{
      const operation=listed?'history':thread?'messages':
        invited?'invited-live-result':engineStatus?'engine-status':status?'status':'send';
      const actual=await productRequest(
        operation,active,signedQuery,thread?path[1]:'',rawBody);
      if(actual.status===401&&handle)await revokeAlias(handle);
      return new Response(actual.body,{
        status:actual.status,
        headers:{...noStore,'Content-Type':'application/json; charset=utf-8'},
      });
    }catch{
      return Response.json({error:'SIGNED_PRODUCT_API_UNAVAILABLE'},
        {status:503,headers:noStore});
    }
  }
  // Historical actor-selected CI proxy is not a product/staging fallback.
  // Even when Auth login is misconfigured, demo/chat mode must fail closed.
  if(stagingRequested()||process.env.AUTH_CI_DEMO_MODE==='true'||
     process.env.AUTH_CI_PRODUCT_CHAT_MODE!==undefined)
    return Response.json({error:'PRODUCT_AUTH_REQUIRED'},
      {status:503,headers:noStore});
  const fixed=process.env.HISTORY_UPSTREAM_ORIGIN;
  // No browser-specified upstream or identity. Closed outside isolated CI.
  if(process.env.CI!=='true'||!fixed||
      !/^http:\/\/127\.0\.0\.1:811[123]$/.test(fixed))
    return Response.json({error:'History unavailable: authentication not configured'},
      {status:503,headers:{'Cache-Control':'no-store'}});
  const target=new URL('/v1/'+path.map(encodeURIComponent).join('/'),fixed);
  const allowedQuery=path[0]==='message-requests'
    ?new Set(['requested_conversation_id','client_message_id','idempotency_key'])
    :new Set(['limit','cursor']);
  for(const [key,value] of new URL(request.url).searchParams){
    if(!allowedQuery.has(key))return new Response(null,{status:422});
    target.searchParams.append(key,value);
  }
  try{
    let body:string|undefined;
    if(request.method==='POST'){
      const bounded=await boundedJsonBody(request);
      if(!bounded.ok)return Response.json({error:'Invalid request body'},
        {status:bounded.status,headers:{'Cache-Control':'no-store'}});
      try{
        body=new TextDecoder('utf-8',{fatal:true}).decode(bounded.bytes);
        const document:unknown=JSON.parse(body);
        if(document===null||typeof document!=='object'||Array.isArray(document))
          throw new Error('JSON object required');
      }catch{
        return Response.json({error:'Invalid request body'},
          {status:422,headers:{'Cache-Control':'no-store'}});
      }
    }
    const upstream=await fetch(target,{
      method:request.method,
      headers:request.method==='POST'?{'content-type':'application/json'}:{},
      body,redirect:'manual',cache:'no-store',signal:request.signal,
    });
    if(upstream.status>=300&&upstream.status<400)throw new Error('Redirect refused');
    return new Response(await upstream.text(),{
      status:upstream.status,
      headers:{'content-type':'application/json; charset=utf-8','Cache-Control':'no-store'},
    });
  }catch{
    return Response.json({error:'History upstream unavailable'},
      {status:503,headers:{'Cache-Control':'no-store'}});
  }
}
