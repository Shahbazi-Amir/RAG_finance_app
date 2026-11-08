/**
 * CI-only bounded History proxy core. Used by the actual Next route and its
 * Node regression tests; no test-only implementation of the forwarding path.
 * The core limits application-collected bytes, not upstream Node/proxy buffers.
 */
import { boundedJsonBody } from './bounded-body.ts';

const allowed=(parts:string[],method:string):boolean=>
  (parts.length===1&&parts[0]==='conversations'&&['GET','POST'].includes(method))||
  (parts.length===1&&parts[0]==='messages'&&method==='POST')||
  (parts.length===2&&parts[0]==='message-requests'&&parts[1]==='status'&&method==='GET')||
  (parts.length===3&&parts[0]==='conversations'&&/^[A-Za-z0-9_-]{1,64}$/.test(parts[1])&&
    parts[2]==='messages'&&method==='GET');

export async function forwardHistoryProxy(request:Request,path:string[]):Promise<Response>{
  if(!allowed(path,request.method))return new Response(null,{status:404});
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
