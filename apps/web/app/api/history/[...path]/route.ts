import { NextRequest, NextResponse } from 'next/server';
import { boundedJsonBody } from '../../../../src/history/bounded-body.ts';

/**
 * CI-only same-origin boundary. A normal deployment has no Auth and fails
 * closed; this route is NOT a publicly usable test mode or an open proxy.
 * No request header/body/query may select the upstream or a user identity.
 */
const allowed = (parts:string[],method:string):boolean=>
  (parts.length===1&&parts[0]==='conversations'&&['GET','POST'].includes(method))||
  (parts.length===1&&parts[0]==='messages'&&method==='POST')||
  (parts.length===2&&parts[0]==='message-requests'&&parts[1]==='status'&&method==='GET')||
  (parts.length===3&&parts[0]==='conversations'&&/^[A-Za-z0-9_-]{1,64}$/.test(parts[1])&&
    parts[2]==='messages'&&method==='GET');

async function forward(request:NextRequest,context:{params:Promise<{path:string[]}>}) {
  const {path}=await context.params;
  if(!allowed(path,request.method))return new NextResponse(null,{status:404});
  const fixed=process.env.HISTORY_UPSTREAM_ORIGIN;
  // Hard allowlist: no external host, no caller-selected URL, no production Auth.
  if(process.env.CI!=='true'||!fixed||
      !/^http:\/\/127\.0\.0\.1:811[123]$/.test(fixed))
    return NextResponse.json({error:'History unavailable: authentication not configured'},
      {status:503,headers:{'Cache-Control':'no-store'}});
  const target=new URL('/v1/'+path.map(encodeURIComponent).join('/'),fixed);
  const allowedQuery=path[0]==='message-requests'
    ?new Set(['requested_conversation_id','client_message_id','idempotency_key'])
    :new Set(['limit','cursor']);
  for(const [k,v] of request.nextUrl.searchParams){
    if(!allowedQuery.has(k))return new NextResponse(null,{status:422});
    target.searchParams.append(k,v);
  }
  try{
    let body:string|undefined;
    if(request.method==='POST'){
      const bounded=await boundedJsonBody(request);
      if(!bounded.ok)return NextResponse.json({error:'Invalid request body'},
        {status:bounded.status,headers:{'Cache-Control':'no-store'}});
      try{
        body=new TextDecoder('utf-8',{fatal:true}).decode(bounded.bytes);
        const document:unknown=JSON.parse(body);
        if(document===null||typeof document!=='object'||Array.isArray(document))
          throw new Error('JSON object required');
      }catch{
        // A truncated/malformed JSON upload never reaches the upstream or DB.
        return NextResponse.json({error:'Invalid request body'},
          {status:422,headers:{'Cache-Control':'no-store'}});
      }
    }
    const upstream=await fetch(target,{
      method:request.method,
      headers:request.method==='POST'?{'content-type':'application/json'}:{},
      body,
      redirect:'manual',cache:'no-store',signal:request.signal,
    });
    if(upstream.status>=300&&upstream.status<400)throw new Error('Redirect refused');
    return new NextResponse(await upstream.text(),{
      status:upstream.status,
      headers:{'content-type':'application/json; charset=utf-8','Cache-Control':'no-store'},
    });
  }catch{
    return NextResponse.json({error:'History upstream unavailable'},
      {status:503,headers:{'Cache-Control':'no-store'}});
  }
}
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){
  return forward(request,ctx);
}
export async function POST(request:NextRequest,ctx:{params:Promise<{path:string[]}>}){
  return forward(request,ctx);
}
