/**
 * Actual HTTPS with verified server CA/hostname and client mTLS. Node signer
 * is independent of the accepted Python verifier + PostgreSQL durable replay.
 * Only ephemeral runner files; never print tokens, keys or session references.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {request as httpsRequest} from 'node:https';
import {randomBytes} from 'node:crypto';
import {createServiceSender,signForTrustedAttempt} from '../../../apps/web/src/auth/server/service-sender.ts';

if(process.env.CI!=='true'||process.env.GITHUB_ACTIONS!=='true')throw Error('CI_ONLY');
const folder=process.env.BFF_TLS_DIR;
if(!folder||!folder.startsWith(process.env.RUNNER_TEMP+'/'))throw Error('CI_ONLY');
const load=name=>readFileSync(folder+'/'+name,'utf8');
const fixture=JSON.parse(readFileSync(process.env.BFF_TRUST_SESSION_FILE,'utf8'));
const target='https://127.0.0.1:8443';
const c={
  issuer:'urn:rag-finance:synthetic-bff',audience:'urn:rag-finance:api:internal-ci',
  kid:'ci-rsa-1',privateKeyPem:load('signer.key'),
  upstreamOrigin:target,allowedOrigins:[target],caPem:load('ca.crt'),
  clientCertPem:load('client.crt'),clientKeyPem:load('client.key'),timeoutMs:3000,
};
const marker=()=>('bff_'+randomBytes(12).toString('hex'));
const make=(id,{method='POST',path='/fixture',query='x=%2f&y=1',body}={})=>({
  method,rawPath:Buffer.from(path,'ascii'),rawQuery:Buffer.from(query,'ascii'),
  body:body??Buffer.from(JSON.stringify({marker:id,idempotency_key:'original-operation',question:'سؤال مالی'})),
});
const count=id=>Number(execFileSync('python',['tests/phase3/integration/ui/audit_bff_trust.py','count',id],
  {encoding:'utf8'}).trim());
const safe=async(cnf,session,op)=>createServiceSender(cnf,async()=>session)(op);
function raw(token,op,credentials=true,conf=c){
  return new Promise(resolve=>{
    let done=false;
    const finish=n=>{if(!done){done=true;resolve(n);}};
    const req=httpsRequest({
      hostname:'127.0.0.1',port:8443,path:op.rawPath.toString('latin1')+
        (op.rawQuery.length?'?'+op.rawQuery.toString('latin1'):''),
      method:op.method,ca:conf.caPem,
      ...(credentials?{cert:conf.clientCertPem,key:conf.clientKeyPem}:{}),
      rejectUnauthorized:true,agent:false,
      headers:{Authorization:'BFF-Assertion '+token,
        'Content-Type':'application/json','Content-Length':String(op.body.length)},
    },res=>{res.resume();res.on('end',()=>finish(res.statusCode));});
    req.on('error',()=>finish(-1));req.setTimeout(3000,()=>req.destroy());
    req.end(op.body);
  });
}
let checks=0;
async function check(label,callback){
  await callback();checks++;console.log('BFF_TLS_'+String(checks).padStart(2,'0')+' PASS '+label);
}
await check('verified real HTTPS mTLS, independent Python RSA, fenced PG write',async()=>{
  const id=marker(),op=make(id);
  assert.deepEqual(await safe(c,fixture.active,op),{ok:true,code:'OK'});
  assert.equal(count(id),1);
});
await check('same compact JWT durable replay rejected, no second SQL',async()=>{
  const id=marker(),op=make(id),token=signForTrustedAttempt(c,fixture.active,op);
  assert.equal(await raw(token,op),200);
  assert.equal(await raw(token,op),401);
  assert.equal(count(id),1);
});
await check('new JTI for Retry, immutable operation bytes/idempotency',async()=>{
  const id=marker(),op=make(id);
  const a=signForTrustedAttempt(c,fixture.active,op).split('.')[1];
  const b=signForTrustedAttempt(c,fixture.active,op).split('.')[1];
  assert.notEqual(JSON.parse(Buffer.from(a,'base64url')).jti,JSON.parse(Buffer.from(b,'base64url')).jti);
  assert.deepEqual(await safe(c,fixture.active,op),{ok:true,code:'OK'});
  assert.deepEqual(await safe(c,fixture.active,op),{ok:false,code:'DENIED'});
  assert.equal(count(id),1);
});
await check('exact method, path percent case, raw query order/percent, whitespace, Unicode',async()=>{
  const variants=[
    [{method:'POST'},{method:'GET'}],
    [{path:'/fixture%2Fpart'},{path:'/fixture%2fpart'}],
    [{query:'a=1&b=%2F'},{query:'b=%2F&a=1'}],
    [{query:'a=%2F'},{query:'a=%2f'}],
    [{body:Buffer.from('{"marker":"M","idempotency_key":"k","question":"مالی"}')},
      {body:Buffer.from('{"marker":"M", "idempotency_key":"k","question":"مالی"}')}],
    [{body:Buffer.from('{"marker":"M","idempotency_key":"k","question":"مالی"}')},
      {body:Buffer.from('{"marker":"M","idempotency_key":"k","question":"مالي"}')}],
  ];
  for(const [signed,wire] of variants){
    const id=marker(),s=make(id,signed),w=make(id,wire);
    const token=signForTrustedAttempt(c,fixture.active,s);
    assert.equal(await raw(token,w),401);
    assert.equal(count(id),0);
  }
});
await check('intact UTF-8 and percent-encoded wire accepted without normalization',async()=>{
  const id=marker();
  const op=make(id,{path:'/fixture%2Fpart',query:'b=%2f&a=%D9%85',
    body:Buffer.from('{"marker":"'+id+'", "idempotency_key":"original-operation", "question":"یک سؤال مالی"}')});
  assert.deepEqual(await safe(c,fixture.active,op),{ok:true,code:'OK'});
  assert.equal(count(id),1);
});
await check('revoked, rotated and expired DB sessions denied',async()=>{
  await new Promise(resolve=>setTimeout(resolve,1800));
  for(const key of ['revoked','rotated','expired']){
    const id=marker();
    assert.deepEqual(await safe(c,fixture[key],make(id)),{ok:false,code:'DENIED'});
    assert.equal(count(id),0);
  }
});
await check('unapproved target, keyless config fail closed',async()=>{
  assert.throws(()=>createServiceSender({...c,upstreamOrigin:'https://127.0.0.1:9443'},async()=>fixture.active));
  assert.throws(()=>createServiceSender({...c,privateKeyPem:''},async()=>fixture.active));
  assert.throws(()=>createServiceSender({...c,clientCertPem:''},async()=>fixture.active));
});
await check('missing mTLS client certificate, invalid client cert, wrong CA denied',async()=>{
  const id=marker(),op=make(id),token=signForTrustedAttempt(c,fixture.active,op);
  assert.equal(await raw(token,op,false),-1);
  const rogue={...c,clientCertPem:load('rogue-client.crt'),clientKeyPem:load('rogue-client.key')};
  assert.deepEqual(await safe(rogue,fixture.active,op),{ok:false,code:'TRANSPORT_FAILURE'});
  assert.deepEqual(await safe({...c,caPem:load('rogue-ca.crt')},fixture.active,op),
    {ok:false,code:'TRANSPORT_FAILURE'});
  assert.equal(count(id),0);
});
await check('hostname mismatch despite same trusted CA rejected',async()=>{
  const bad={...c,upstreamOrigin:'https://localhost:8443',
    allowedOrigins:['https://localhost:8443']};
  const id=marker();
  assert.deepEqual(await safe(bad,fixture.active,make(id)),{ok:false,code:'TRANSPORT_FAILURE'});
  assert.equal(count(id),0);
});
await check('no redirect follow, timeout, malformed 200, truncated stream',async()=>{
  for(const [path,expectCode,settings] of [
    ['/fixture-redirect','REDIRECT_REJECTED',c],
    ['/fixture-timeout','TIMEOUT',{...c,timeoutMs:75}],
    ['/fixture-invalid','INVALID_RESPONSE',c],
    ['/fixture-disconnect','INVALID_RESPONSE',c],
  ]){
    const id=marker(),result=await safe(settings,fixture.active,make(id,{path}));
    assert.equal(result.code,expectCode,path);
    assert.equal(result.ok,false);
    assert.equal(count(id),0);
  }
});
execFileSync('python',['tests/phase3/integration/ui/audit_bff_trust.py','role'],{stdio:'pipe'});
console.log('BFF_HTTPS_MTLS_INTEGRATION_PASS checks='+checks);
