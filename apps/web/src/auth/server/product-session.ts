/**
 * CI-only private Product session -> real API #50. Never a browser route.
 * Service-bound RS256 JWT + mTLS; exact raw method/path/query/body. No actor
 * sourced from the URL, request headers, or a user-selected fixture.
 */
import {createHash,createPrivateKey,randomBytes,sign} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {request as httpsRequest} from 'node:https';
import type {IncomingMessage,ClientRequest} from 'node:http';

export type TrustedActive=Readonly<{ownerId:string;epoch:number;generation:number;
  sessionVerifier:string}>;
export type ProductReply=Readonly<{status:number;body:string}>;
const sha=(data:Buffer|string)=>createHash('sha256').update(data).digest('hex');
const b64=(x:unknown)=>Buffer.from(JSON.stringify(x),'utf8').toString('base64url');
function deny():never{throw new Error('DEMO_PRODUCT_PRIVATE_API_UNAVAILABLE');}
async function privateConfig(){
  if(process.env.CI!=='true'||process.env.AUTH_CI_DEMO_MODE!=='true')deny();
  let endpoint:URL;
  try{
    endpoint=new URL(process.env.AUTH_CI_PRODUCT_ORIGIN??'');
    if(endpoint.protocol!=='https:'||endpoint.hostname!=='127.0.0.1'||
       !endpoint.port||endpoint.pathname!=='/'||endpoint.search||endpoint.hash)deny();
  }catch{return deny();}
  const paths=['AUTH_CI_PRODUCT_SIGN_KEY','AUTH_CI_BOOTSTRAP_CA',
    'AUTH_CI_BOOTSTRAP_CERT','AUTH_CI_BOOTSTRAP_KEY'] as const;
  const contents=await Promise.all(paths.map(async k=>{
    const path=process.env[k]??'';
    if(!path.startsWith('/tmp/')||path.includes('..'))deny();
    return readFile(path,'utf8');
  }));
  const issuer=process.env.AUTH_CI_PRODUCT_ISSUER??'';
  const audience=process.env.AUTH_CI_PRODUCT_AUDIENCE??'';
  const kid=process.env.AUTH_CI_PRODUCT_KID??'';
  if(!issuer.startsWith('urn:')||!audience.startsWith('urn:')||
      !/^[A-Za-z0-9_.-]{1,80}$/.test(kid))deny();
  return {endpoint,signKey:contents[0],ca:contents[1],cert:contents[2],
    key:contents[3],issuer,audience,kid};
}
export async function productRequest(
  operation:'history'|'revoke',active:TrustedActive,
  query='' ,operationId=''):Promise<ProductReply>{
  if(!/^[A-Za-z0-9_-]{43,256}$/.test(active.sessionVerifier)||
     !/^[A-Za-z0-9_-]{1,128}$/.test(active.ownerId)||
     !Number.isSafeInteger(active.epoch)||active.epoch<0||
     !Number.isSafeInteger(active.generation)||active.generation<0)deny();
  const isList=operation==='history';
  if((isList&&operationId)||(isList&&!/^\?(?:limit=[0-9]+)(?:&cursor=[A-Za-z0-9_-]+)?$/.test(query))||
     (!isList&&(query||!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(operationId))))deny();
  const c=await privateConfig();
  const rawPath=isList?'/v1/conversations':'/internal/auth/session/v1/revoke-one';
  const rawQuery=isList?query.slice(1):'';
  const method=isList?'GET':'POST';
  const body=isList?Buffer.alloc(0):Buffer.from(JSON.stringify({operation_id:operationId}));
  const now=Math.floor(Date.now()/1000);
  const claims={
    iss:c.issuer,aud:c.audience,iat:now,nbf:now,exp:now+25,
    jti:randomBytes(24).toString('base64url'),method,
    raw_path_sha256:sha(rawPath),raw_query_sha256:sha(rawQuery),
    body_sha256:sha(body),body_len:body.length,
    session_ref:active.sessionVerifier,owner_id:active.ownerId,
    epoch:active.epoch,generation:active.generation,
  };
  const tokenInput=b64({typ:'JWT',alg:'RS256',kid:c.kid})+'.'+b64(claims);
  const token=tokenInput+'.'+sign('RSA-SHA256',
    Buffer.from(tokenInput,'ascii'),createPrivateKey(c.signKey)).toString('base64url');
  if(token.length>4096)deny();
  return new Promise<ProductReply>((resolve,reject)=>{
    let finished=false;
    let req:ClientRequest|undefined,res:IncomingMessage|undefined;
    const settle=(value?:ProductReply)=>{
      if(finished)return;
      finished=true;clearTimeout(timer);
      req?.destroy();res?.destroy();
      if(value)resolve(value);else reject(new Error('DEMO_PRODUCT_PRIVATE_API_UNAVAILABLE'));
    };
    const timer=setTimeout(()=>settle(),12000);
    try{
      req=httpsRequest({hostname:c.endpoint.hostname,port:c.endpoint.port,
        method,path:rawPath+query,ca:c.ca,cert:c.cert,key:c.key,
        rejectUnauthorized:true,agent:false,minVersion:'TLSv1.2',
        headers:{
          Authorization:'BFF-Assertion '+token,
          ...(isList?{}:{'Content-Type':'application/json'}),
          'Content-Length':String(body.length),
        }},response=>{
        res=response;
        if(finished){response.destroy();return;}
        if((response.statusCode??0)>=300&&(response.statusCode??0)<400){settle();return;}
        const chunks:Buffer[]=[];
        let size=0;
        response.on('data',(chunk:Buffer)=>{
          size+=chunk.length;
          if(size>65536)settle();else chunks.push(chunk);
        });
        response.on('end',()=>{if(!finished)settle({
          status:response.statusCode??0,body:Buffer.concat(chunks).toString('utf8'),
        });});
        response.on('error',()=>settle());
        response.on('aborted',()=>settle());
        response.on('close',()=>{if(!response.complete)settle();});
      });
      req.on('error',()=>settle());
      req.end(body);
    }catch{settle();}
  });
}
