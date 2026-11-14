/**
 * CI-only Next->API initial-OIDC bootstrap transport.
 * Matches tested API #48, SHA 1998b31c..., no "continuation" field.
 * Session-bound service sender is NOT valid before Product Session issuance.
 */
import {createHash,createPrivateKey,randomBytes,sign} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {request as httpsRequest} from 'node:https';
import type {ClientRequest,IncomingMessage} from 'node:http';

type Operation='start'|'complete'|'status'|'ack'|'abort';
export type BootstrapReply=Readonly<{status:number;data:Record<string,unknown>}>;
const sha=(x:Buffer|string)=>createHash('sha256').update(x).digest('hex');
const encoded=(x:unknown)=>Buffer.from(JSON.stringify(x),'utf8').toString('base64url');
const reject=():never=>{throw new Error('AUTH_BOOTSTRAP_UNAVAILABLE');};
function object(x:unknown):x is Record<string,unknown>{
  return x!==null&&typeof x==='object'&&!Array.isArray(x);
}
async function settings(){
  if(process.env.CI!=='true')reject();
  const origin=process.env.AUTH_CI_BOOTSTRAP_ORIGIN??'';
  let target:URL;
  try{
    target=new URL(origin);
    if(target.protocol!=='https:'||target.hostname!=='127.0.0.1'||
       !target.port||target.pathname!=='/'||target.search||target.hash)reject();
  }catch{return reject();}
  const paths=['AUTH_CI_BOOTSTRAP_SIGN_KEY','AUTH_CI_BOOTSTRAP_CA',
    'AUTH_CI_BOOTSTRAP_CERT','AUTH_CI_BOOTSTRAP_KEY'] as const;
  const values=await Promise.all(paths.map(p=>{
    const path=process.env[p]??'';
    if(!path||!path.startsWith('/tmp/'))reject();
    return readFile(path,'utf8');
  }));
  const issuer=process.env.AUTH_CI_BOOTSTRAP_ISSUER??'';
  const audience=process.env.AUTH_CI_BOOTSTRAP_AUDIENCE??'';
  const kid=process.env.AUTH_CI_BOOTSTRAP_KID??'';
  if(!issuer.startsWith('urn:')||!audience.startsWith('urn:')||
      !/^[A-Za-z0-9_.-]{1,80}$/.test(kid))reject();
  return {target,privateKey:values[0],ca:values[1],cert:values[2],
    key:values[3],issuer,audience,kid};
}
export async function bootstrap(operation:Operation,payload:Record<string,unknown>):
  Promise<BootstrapReply>{
  if(!['start','complete','status','ack','abort'].includes(operation)||
    typeof payload.attempt_id!=='string'||
    typeof payload.initiator_sha256!=='string'||
    !/^[a-f0-9]{64}$/.test(payload.initiator_sha256))reject();
  const c=await settings();
  const body=Buffer.from(JSON.stringify(payload),'utf8');
  if(body.length>8192)reject();
  const path='/internal/auth/oidc/v1/'+operation;
  const now=Math.floor(Date.now()/1000);
  const header={typ:'JWT',alg:'RS256',kid:c.kid};
  const claims={
    iss:c.issuer,aud:c.audience,iat:now,nbf:now,exp:now+20,
    jti:randomBytes(24).toString('base64url'),
    purpose:'initial-oidc-bootstrap-v1',method:'POST',
    raw_path_sha256:sha(path),raw_query_sha256:sha(Buffer.alloc(0)),
    body_sha256:sha(body),body_len:body.length,
    attempt_id:payload.attempt_id,initiator_sha256:payload.initiator_sha256
  };
  const input=encoded(header)+'.'+encoded(claims);
  const signature=sign('RSA-SHA256',Buffer.from(input,'ascii'),createPrivateKey(c.privateKey))
    .toString('base64url');
  const jwt=input+'.'+signature;
  if(jwt.length>4150)reject();
  return new Promise<BootstrapReply>((resolve,rejectPromise)=>{
    let finished=false;
    let req:ClientRequest|undefined,res:IncomingMessage|undefined;
    const settle=(result?:BootstrapReply)=>{
      if(finished)return;finished=true;clearTimeout(timer);
      req?.destroy();res?.destroy();
      if(result)resolve(result);else rejectPromise(new Error('AUTH_BOOTSTRAP_UNAVAILABLE'));
    };
    const timer=setTimeout(()=>settle(),12000); // absolute, not inactivity
    try{
      req=httpsRequest({hostname:c.target.hostname,port:c.target.port,path,
        method:'POST',ca:c.ca,cert:c.cert,key:c.key,rejectUnauthorized:true,
        agent:false,minVersion:'TLSv1.2',
        headers:{Authorization:'Bootstrap '+jwt,'Content-Type':'application/json',
          'Content-Length':String(body.length)}},response=>{
        res=response;
        if(finished){response.destroy();return;}
        if((response.statusCode??0)>=300&&(response.statusCode??0)<400){
          settle();return;
        }
        const buffers:Buffer[]=[];let bytes=0;
        response.on('data',(part:Buffer)=>{
          bytes+=part.length;if(bytes>8192)settle();else buffers.push(part);
        });
        response.on('end',()=>{
          if(finished)return;
          try{
            const data:unknown=JSON.parse(Buffer.concat(buffers).toString('utf8'));
            if(!object(data))reject();
            settle({status:response.statusCode??0,data:data as Record<string,unknown>});
          }catch{settle();}
        });
        response.on('error',()=>settle());
        response.on('aborted',()=>settle());
        response.on('close',()=>{if(!response.complete)settle();});
      });
      req.on('error',()=>settle());
      req.end(body);
    }catch{settle();}
  });
}
