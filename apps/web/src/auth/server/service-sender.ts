/**
 * Node-only internal service assertion sender. Not OIDC, Login, History or
 * product authorization. Browser headers/identity/URL must never be forwarded.
 * Next server consumers import ./index.ts (server-only marker).
 */
import {constants,createHash,createPrivateKey,randomBytes,sign,type KeyObject} from 'node:crypto';
import {request as httpsRequest} from 'node:https';

export type TrustedSession=Readonly<{ownerId:string;sessionRef:string;epoch:number;generation:number}>;
export type WireOperation=Readonly<{
  method:'POST'|'GET'|'PUT'|'PATCH';rawPath:Buffer;rawQuery:Buffer;body:Buffer;
}>;
export type ServerTrustConfig=Readonly<{
  issuer:string;audience:string;kid:string;privateKeyPem:string;
  upstreamOrigin:string;allowedOrigins:readonly string[];
  caPem:string;clientCertPem:string;clientKeyPem:string;timeoutMs:number;
}>;
export type TransportResult=Readonly<{ok:boolean;code:
  'OK'|'DENIED'|'REDIRECT_REJECTED'|'TIMEOUT'|'TRANSPORT_FAILURE'|'INVALID_RESPONSE'|'UNAVAILABLE'}>;
const deny=():never=>{throw new Error('BFF_SERVICE_DENIED');};
const object=(x:unknown):x is Record<string,unknown>=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const encode=(x:string|Buffer)=>Buffer.from(x).toString('base64url');
const digest=(x:Buffer)=>createHash('sha256').update(x).digest('hex');
function checkWire(op:WireOperation):void{
  if(!op||!['POST','GET','PUT','PATCH'].includes(op.method)||
     !Buffer.isBuffer(op.rawPath)||!Buffer.isBuffer(op.rawQuery)||!Buffer.isBuffer(op.body)||
     op.rawPath.length<1||op.rawPath.length>2048||op.rawQuery.length>4096||
     op.body.length>8192)deny();
  const path=op.rawPath.toString('latin1'),query=op.rawQuery.toString('latin1');
  if(!path.startsWith('/')||!/^[\x21-\x7e]+$/.test(path)||/[?#]/.test(path)||
     !/^[\x21-\x7e]*$/.test(query)||query.includes('#'))deny();
}
function checkSession(s:TrustedSession):void{
  if(!object(s)||Object.keys(s).sort().join(',')!=='epoch,generation,ownerId,sessionRef'||
     typeof s.ownerId!=='string'||!/^[A-Za-z0-9_-]{1,128}$/.test(s.ownerId)||
     typeof s.sessionRef!=='string'||!/^[A-Za-z0-9_-]{43,256}$/.test(s.sessionRef)||
     !Number.isSafeInteger(s.epoch)||s.epoch<0||
     !Number.isSafeInteger(s.generation)||s.generation<0)deny();
}
function prepare(c:ServerTrustConfig):{key:KeyObject;target:URL}{
  if(!c||!/^urn:.{1,176}$/.test(c.issuer)||!/^urn:.{1,176}$/.test(c.audience)||
     !/^[A-Za-z0-9_.-]{1,80}$/.test(c.kid)||
     typeof c.privateKeyPem!=='string'||!c.privateKeyPem||
     !Array.isArray(c.allowedOrigins)||!c.allowedOrigins.length||
     !c.allowedOrigins.includes(c.upstreamOrigin)||
     typeof c.caPem!=='string'||!c.caPem||
     typeof c.clientCertPem!=='string'||!c.clientCertPem||
     typeof c.clientKeyPem!=='string'||!c.clientKeyPem||
     !Number.isSafeInteger(c.timeoutMs)||c.timeoutMs<1||c.timeoutMs>30000)deny();
  try{
    const target=new URL(c.upstreamOrigin);
    if(target.protocol!=='https:'||target.origin!==c.upstreamOrigin||
       target.pathname!=='/'||target.username||target.password||target.search||target.hash)deny();
    const key=createPrivateKey(c.privateKeyPem);
    if(key.asymmetricKeyType!=='rsa'||(key.asymmetricKeyDetails?.modulusLength??0)<2048)deny();
    return {key,target};
  }catch{deny();}
}
/** Called with an actual trusted server-store result, NEVER browser identity. */
export function signForTrustedAttempt(c:ServerTrustConfig,s:TrustedSession,op:WireOperation):string{
  checkSession(s);checkWire(op);
  const {key}=prepare(c),now=Math.floor(Date.now()/1000);
  const header={typ:'JWT',alg:'RS256',kid:c.kid};
  const claims={
    iss:c.issuer,aud:c.audience,iat:now,nbf:now,exp:now+20,
    jti:randomBytes(24).toString('base64url'),method:op.method,
    raw_path_sha256:digest(op.rawPath),raw_query_sha256:digest(op.rawQuery),
    body_sha256:digest(op.body),body_len:op.body.length,
    session_ref:s.sessionRef,owner_id:s.ownerId,epoch:s.epoch,generation:s.generation,
  };
  const input=encode(JSON.stringify(header))+'.'+encode(JSON.stringify(claims));
  try{
    const sig=sign('RSA-SHA256',Buffer.from(input,'ascii'),
      {key,padding:constants.RSA_PKCS1_PADDING});
    const jwt=input+'.'+encode(sig);
    if(jwt.length>4096)deny();
    return jwt;
  }catch{deny();}
}
/** No automatic retry: caller retains immutable operation/idempotency payload. */
export function createServiceSender(c:ServerTrustConfig,resolveSession:()=>Promise<TrustedSession>):
  (op:WireOperation)=>Promise<TransportResult>{
  const {target}=prepare(c);
  if(typeof resolveSession!=='function')deny();
  return async op=>{
    let token:string;
    try{checkWire(op);token=signForTrustedAttempt(c,await resolveSession(),op);}
    catch{return {ok:false,code:'UNAVAILABLE'};}
    // Literal path/query octets are sent without URL/JSON normalization.
    const path=op.rawPath.toString('latin1')+
      (op.rawQuery.length?'?'+op.rawQuery.toString('latin1'):'');
    return new Promise<TransportResult>(resolve=>{
      let finished=false,timedOut=false;
      const done=(value:TransportResult)=>{if(!finished){finished=true;resolve(value);}};
      try{
        const req=httpsRequest({
          hostname:target.hostname,port:target.port||443,path,method:op.method,
          ca:c.caPem,cert:c.clientCertPem,key:c.clientKeyPem,
          rejectUnauthorized:true,minVersion:'TLSv1.2',agent:false,
          headers:{Authorization:'BFF-Assertion '+token,'Content-Type':'application/json',
            'Content-Length':String(op.body.length)},
        },res=>{
          const status=res.statusCode??0;
          if(status>=300&&status<400){
            res.resume();done({ok:false,code:'REDIRECT_REJECTED'});return;
          }
          if(status===401||status===403){res.resume();done({ok:false,code:'DENIED'});return;}
          if(status!==200){res.resume();done({ok:false,code:'UNAVAILABLE'});return;}
          const parts:Buffer[]=[];let size=0;
          res.on('data',(part:Buffer)=>{
            size+=part.length;
            if(size>4096){req.destroy();done({ok:false,code:'INVALID_RESPONSE'});}
            else parts.push(part);
          });
          res.on('error',()=>done({ok:false,code:'INVALID_RESPONSE'}));
          res.on('aborted',()=>done({ok:false,code:'INVALID_RESPONSE'}));
          res.on('end',()=>{
            if(finished)return;
            try{
              const data:unknown=JSON.parse(Buffer.concat(parts).toString('utf8'));
              if(!object(data)||Object.keys(data).length!==1||data.ok!==true)deny();
              done({ok:true,code:'OK'});
            }catch{done({ok:false,code:'INVALID_RESPONSE'});}
          });
        });
        req.setTimeout(c.timeoutMs,()=>{timedOut=true;req.destroy();});
        req.on('error',()=>done({ok:false,code:timedOut?'TIMEOUT':'TRANSPORT_FAILURE'}));
        req.end(op.body);
      }catch{done({ok:false,code:'TRANSPORT_FAILURE'});}
    });
  };
}
