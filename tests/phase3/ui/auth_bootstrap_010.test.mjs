import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomBytes,randomUUID} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {saveInit,findInitForState,claimInit,readInit,digest,fresh,
  writePending,activate,getActive,revokeAlias} from '../../../apps/web/src/auth/server/initial-store.ts';
import {csrf,mutationAllowed,secureBrowser,INIT,SESSION,cookie,
  appendCookie} from '../../../apps/web/src/auth/server/initial-browser.ts';

const dir=await mkdtemp(join(tmpdir(),'auth-ui-ci-'));
process.env.CI='true';
process.env.AUTH_CI_SHARED_STORE_DIR=dir;
process.env.AUTH_CI_ALIAS_AES_KEY=randomBytes(32).toString('base64url');
process.env.AUTH_CI_CSRF_SECRET=randomBytes(32).toString('base64url');
process.env.AUTH_CI_PUBLIC_ORIGIN='https://127.0.0.1:3443';
process.env.AUTH_CI_PROXY_SECRET=randomBytes(32).toString('base64url');
test.after(async()=>{await rm(dir,{recursive:true,force:true});});
const root=process.cwd().endsWith('/apps/web')?join(process.cwd(),'../..'):process.cwd();

test('UIAUTH01: START state and initiator persist across process and one callback claim',async()=>{
  const attemptId=randomUUID(),bffAttemptId=randomUUID(),state=fresh(),init=fresh();
  await saveInit({attemptId,bffAttemptId,initiatorHash:digest(init),
    stateHash:digest(state),created:Date.now(),status:'INITIATED'});
  const row=await findInitForState(state);
  assert.equal(row?.attemptId,attemptId);
  assert.equal(row?.initiatorHash,digest(init));
  assert.equal(await findInitForState(fresh()),null);
  const child=spawnSync(process.execPath,['--experimental-strip-types','--input-type=module',
    '-e',"import {findInitForState} from './apps/web/src/auth/server/initial-store.ts';console.log((await findInitForState(process.argv[1]))?.attemptId??'NONE')",state],
    {cwd:root,encoding:'utf8',env:process.env});
  assert.equal(child.status,0,child.stderr);
  assert.ok(child.stdout.includes(attemptId),'separate worker reads durable init');
  assert.equal(await claimInit(attemptId),true);
  assert.equal(await claimInit(attemptId),false);
  assert.equal((await readInit(attemptId))?.attemptId,attemptId);
});

test('UIAUTH02: encrypted alias NOT_SERVE until ACK, then shared across worker',async()=>{
  const alias=fresh(),secret=fresh(),receiptId=randomUUID();
  const checksum=await writePending(alias,{attemptId:randomUUID(),receiptId,
    ownerId:'synthetic_owner_A',epoch:0,generation:0,sessionVerifier:secret});
  assert.equal(checksum,digest(alias));
  assert.equal(await getActive(alias),null,'not serve before ACK');
  const files=await readdir(dir);
  const aliasFile=files.find(x=>x.startsWith('alias-'));
  assert.ok(aliasFile);
  const record=await readFile(join(dir,aliasFile),'utf8');
  assert.ok(!record.includes(secret),'verifier encrypted at rest');
  assert.ok(!record.includes(alias),'alias hashed in filename');
  assert.equal(await activate(alias,randomUUID()),false);
  assert.equal(await activate(alias,receiptId),true);
  assert.equal((await getActive(alias))?.sessionVerifier,secret);
  const child=spawnSync(process.execPath,['--experimental-strip-types','--input-type=module',
    '-e',"import {getActive} from './apps/web/src/auth/server/initial-store.ts';console.log((await getActive(process.argv[1]))?.ownerId??'NONE')",alias],
    {cwd:root,encoding:'utf8',env:process.env});
  assert.equal(child.status,0,child.stderr);
  assert.ok(child.stdout.includes('synthetic_owner_A'));
  await revokeAlias(alias);
  assert.equal(await getActive(alias),null);
});

test('UIAUTH03: same-origin HTTPS/Origin/CSRF, HttpOnly Host-only cookie',()=>{
  const initiator=fresh(),token=csrf(initiator);
  const headers={'origin':'https://127.0.0.1:3443','sec-fetch-site':'same-origin',
    'x-auth-ci-proxy-proof':process.env.AUTH_CI_PROXY_SECRET};
  const make=(patch={})=>new Request('http://127.0.0.1:3000/api/auth/login',
    {method:'POST',headers:{...headers,...patch,'cookie':INIT+'='+initiator}});
  assert.equal(secureBrowser(make()),true);
  assert.equal(mutationAllowed(make(),token,csrf(initiator)),true);
  assert.equal(mutationAllowed(make(),fresh(),csrf(initiator)),false);
  assert.equal(mutationAllowed(make({origin:'https://evil.invalid'}),token,token),false);
  assert.equal(mutationAllowed(make({'sec-fetch-site':'cross-site'}),token,token),false);
  assert.equal(secureBrowser(make({'x-auth-ci-proxy-proof':'forged'})),false);
  assert.equal(cookie(make(),INIT),initiator);
  const response=new Response(null);
  appendCookie(response,SESSION,fresh(),500);
  const cookieText=response.headers.get('set-cookie')??'';
  for(const name of ['Secure','HttpOnly','SameSite=Lax','Path=/'])
    assert.ok(cookieText.includes(name));
  assert.ok(!cookieText.includes('Domain='));
});
