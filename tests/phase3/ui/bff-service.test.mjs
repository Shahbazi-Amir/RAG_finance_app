import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createPublicKey,verify} from 'node:crypto';
import {readFileSync,readdirSync} from 'node:fs';
import {join} from 'node:path';
import {signForTrustedAttempt,createServiceSender} from '../../../apps/web/src/auth/server/service-sender.ts';

const pair=generateKeyPairSync('rsa',{modulusLength:2048});
const pem=pair.privateKey.export({type:'pkcs8',format:'pem'});
const session={ownerId:'owner_fixture',sessionRef:'x'.repeat(43),epoch:0,generation:0};
const config={
  issuer:'urn:rag-finance:synthetic-bff',audience:'urn:rag-finance:api:internal-ci',
  kid:'ci-rsa-1',privateKeyPem:pem,upstreamOrigin:'https://127.0.0.1:8443',
  allowedOrigins:['https://127.0.0.1:8443'],caPem:'fixture',
  clientCertPem:'fixture',clientKeyPem:'fixture',timeoutMs:3000,
};
const op={method:'POST',rawPath:Buffer.from('/fixture%2Fpart'),rawQuery:Buffer.from('b=2&a=%2f'),
  body:Buffer.from('{"question":"آزمون", "idempotency_key":"original"}')};
const decode=t=>JSON.parse(Buffer.from(t.split('.')[1],'base64url').toString('utf8'));
test('RS256 Node signer: exact allowed claims and header; cryptographic RSA verification',()=>{
  const token=signForTrustedAttempt(config,session,op),[h,p,s]=token.split('.');
  assert.deepEqual(JSON.parse(Buffer.from(h,'base64url').toString()),{typ:'JWT',alg:'RS256',kid:'ci-rsa-1'});
  assert.equal(verify('RSA-SHA256',Buffer.from(h+'.'+p),createPublicKey(pair.privateKey),
    Buffer.from(s,'base64url')),true);
  const claims=decode(token);
  assert.deepEqual(Object.keys(claims).sort(),[
    'iss','aud','iat','nbf','exp','jti','method','raw_path_sha256','raw_query_sha256',
    'body_sha256','body_len','session_ref','owner_id','epoch','generation'].sort());
  assert.equal(claims.exp-claims.iat,20);
  assert.equal(claims.body_len,op.body.length);
  assert.equal(claims.owner_id,session.ownerId);
  assert.equal(claims.session_ref,session.sessionRef);
});
test('new random JTI for each network attempt but byte payload unchanged',()=>{
  const a=decode(signForTrustedAttempt(config,session,op));
  const b=decode(signForTrustedAttempt(config,session,op));
  assert.notEqual(a.jti,b.jti);
  assert.equal(a.body_sha256,b.body_sha256);
  assert.equal(a.raw_path_sha256,b.raw_path_sha256);
  assert.equal(a.raw_query_sha256,b.raw_query_sha256);
  assert.equal(a.body_len,b.body_len);
});
test('no key/default, non-RSA key, short RSA, unapproved URL and invalid session fail closed',()=>{
  for(const patch of [
    {privateKeyPem:''},{privateKeyPem:'unparseable'},
    {kid:'bad/kid'},{issuer:'https://not-urn'},
    {upstreamOrigin:'http://127.0.0.1:8443'},
    {upstreamOrigin:'https://127.0.0.1:8444'},
    {upstreamOrigin:'https://127.0.0.1:8443/extra'},
    {timeoutMs:0},{caPem:''},{clientCertPem:''},
  ])assert.throws(()=>createServiceSender({...config,...patch},async()=>session),/BFF_SERVICE_DENIED/);
  for(const patch of [
    {ownerId:''},{sessionRef:'browser-selected'},{epoch:-1},
    {generation:'1'},{role:'admin'},
  ])assert.throws(()=>signForTrustedAttempt(config,{...session,...patch},op),/BFF_SERVICE_DENIED/);
});
test('exact raw bytes: changed query order/percent, Unicode body, JSON whitespace have distinct digest',()=>{
  const first=decode(signForTrustedAttempt(config,session,op));
  for(const change of [
    {rawPath:Buffer.from('/fixture%2fpart')},
    {rawQuery:Buffer.from('a=%2f&b=2')},
    {rawQuery:Buffer.from('b=2&a=%2F')},
    {body:Buffer.from(op.body.toString().replace(' "idempotency','"idempotency'))},
    {body:Buffer.from('{"question":"آزمون","idempotency_key":"original"}')},
  ]) {
    const next=decode(signForTrustedAttempt(config,session,{...op,...change}));
    assert.ok(first.raw_path_sha256!==next.raw_path_sha256||
      first.raw_query_sha256!==next.raw_query_sha256||
      first.body_sha256!==next.body_sha256);
  }
  assert.throws(()=>signForTrustedAttempt(config,session,{...op,rawPath:Buffer.from('/bad?x=1')}),/BFF_SERVICE_DENIED/);
  assert.throws(()=>signForTrustedAttempt(config,session,{...op,body:Buffer.alloc(8193)}),/BFF_SERVICE_DENIED/);
});
test('Next server-only entrypoint and isolated client import boundary',()=>{
  const root=new URL('../../../apps/web/',import.meta.url);
  const entry=readFileSync(new URL('src/auth/server/index.ts',root),'utf8');
  assert.match(entry,/import 'server-only'/);
  function walk(dir){
    for(const file of readdirSync(dir,{withFileTypes:true})){
      const pathname=join(dir,file.name);
      if(file.isDirectory())walk(pathname);
      else if(/\.(tsx?|jsx?)$/.test(file.name)){
        const text=readFileSync(pathname,'utf8');
        assert.doesNotMatch(text,/auth\/server\/|service-sender/,pathname);
      }
    }
  }
  walk(new URL('app/',root).pathname);
});
