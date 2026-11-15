import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createPublicKey,verify} from 'node:crypto';
import {readFileSync,readdirSync,existsSync,statSync,mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {join,resolve,dirname,extname,sep} from 'node:path';
import {tmpdir} from 'node:os';
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
/**
 * Next API route handlers under app/api/ are server entry points, not browser code.
 * Only 'use client' files and their transitive runtime import graph become
 * browser code. Follow static imports/exports and literal dynamic imports,
 * explicitly excluding erased TypeScript type-only imports.
 */
function runtimeImports(source){
  const staticImports=/(?:^|\n)\s*(?:import|export)\s+(?!type\b)(?:[^;]*?\s+from\s+)?['"]([^'"]+)['"]/g;
  const dynamicImports=/\b(?:import|require)\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
  return [...source.matchAll(staticImports),...source.matchAll(dynamicImports)]
    .map(match=>match[1]);
}
function clientBoundary(root,entry){
  const visited=new Set();
  const rootPath=resolve(root);
  function visit(file){
    const full=resolve(file);
    assert.ok(full.startsWith(rootPath+sep),'CLIENT_IMPORT_OUTSIDE_APP: '+full);
    if(visited.has(full))return;
    visited.add(full);
    const source=readFileSync(full,'utf8');
    assert.doesNotMatch(source,/(?:^|\n)\s*['"]use server['"]\s*;?/,
      'CLIENT_SERVER_MODULE: '+full);
    for(const spec of runtimeImports(source)){
      assert.ok(!/^(?:node:|server-only$|fs$|crypto$|child_process$|module$|net$|tls$)/.test(spec)&&
        !/(?:^|\/)auth\/(?:server|initial)(?:\/|$)/.test(spec)&&
        !/(?:^|\/)history\/proxy(?:\.|\/|$)/.test(spec),
        'CLIENT_SERVER_IMPORT: '+full+' -> '+spec);
      if(!spec.startsWith('.'))continue;
      if(/\.(?:css|scss|sass)$/.test(spec))continue;
      const target=resolve(dirname(full),spec);
      const possible=[target,target+'.ts',target+'.tsx',target+'.js',target+'.jsx',
        join(target,'index.ts'),join(target,'index.tsx'),join(target,'index.js')];
      const resolved=possible.find(candidate=>existsSync(candidate)&&statSync(candidate).isFile());
      assert.ok(resolved,'CLIENT_UNRESOLVED_IMPORT: '+full+' -> '+spec);
      visit(resolved);
    }
  }
  visit(entry);
  return visited;
}
function allSources(dir){
  const found=[];
  for(const item of readdirSync(dir,{withFileTypes:true})){
    const pathname=join(dir,item.name);
    if(item.isDirectory())found.push(...allSources(pathname));
    else if(item.isFile()&&/\.(?:tsx?|jsx?)$/.test(item.name))found.push(pathname);
  }
  return found;
}
test('Next server-only entrypoint; browser client import closure excludes server modules',()=>{
  const root=new URL('../../../apps/web/',import.meta.url).pathname;
  const entry=readFileSync(join(root,'src/auth/server/index.ts'),'utf8');
  assert.match(entry,/import 'server-only'/);
  const route=readFileSync(join(root,'app/api/auth/login/route.ts'),'utf8');
  assert.match(route,/auth\/server\/private-staging/);
  assert.doesNotMatch(route,/^\s*['"]use client['"]/m,
    'API login route must remain server-only');
  const entries=[...allSources(join(root,'app')),...allSources(join(root,'src'))]
    .filter(file=>/^\s*['"]use client['"]\s*;?/m.test(readFileSync(file,'utf8')));
  assert.ok(entries.some(file=>file.endsWith('/src/ui/product-chat.tsx')),
    'product chat must be guarded as a browser client root');
  for(const file of entries)clientBoundary(root,file);
});
test('client boundary rejects a transitive import of server-only code',()=>{
  const root=mkdtempSync(join(tmpdir(),'rag-client-import-'));
  try{
    writeFileSync(join(root,'client.tsx'),"'use client';\nimport './bridge';");
    writeFileSync(join(root,'bridge.ts'),"export {secret} from './secret';");
    writeFileSync(join(root,'secret.ts'),"import 'server-only';\nexport const secret='must-not-bundle';");
    assert.throws(()=>clientBoundary(root,join(root,'client.tsx')),
      /CLIENT_SERVER_IMPORT/);
    writeFileSync(join(root,'client.tsx'),
      "'use client';\nimport './bridge';\nimport '../auth/server/key';");
    assert.throws(()=>clientBoundary(root,join(root,'client.tsx')),
      /CLIENT_SERVER_IMPORT/);
  }finally{rmSync(root,{recursive:true,force:true});}
});
