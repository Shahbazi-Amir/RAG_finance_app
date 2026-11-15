import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,chmodSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {stagingProfile,stagingSecret} from '../../../apps/web/src/auth/server/private-staging.ts';
import {publicOrigin,secureBrowser,csrf} from '../../../apps/web/src/auth/server/initial-browser.ts';
import {forwardHistoryProxy} from '../../../apps/web/src/history/proxy.ts';

const envKeys=['CI','GITHUB_ACTIONS','AUTH_RUNTIME_PROFILE','AUTH_STAGING_CONFIG_FILE',
  'AUTH_CI_LOGIN_MODE','AUTH_CI_DEMO_MODE','AUTH_CI_PRODUCT_CHAT_MODE'];
test('standalone staging trust: only Ops-owned file, HTTPS ragfinance.ir and proxy evidence',async()=>{
  const saved=Object.fromEntries(envKeys.map(k=>[k,process.env[k]]));
  const root=mkdtempSync(join(tmpdir(),'rag-stage-auth-'));
  chmodSync(root,0o700);
  const put=(name,data)=>{
    const p=join(root,name);writeFileSync(p,data,{mode:0o600});return p;
  };
  const store=join(root,'store');mkdirSync(store,{mode:0o700});
  const proxy='private-tls-ingress-proof-must-not-be-forwarded-by-client';
  const common={
    public_origin:'https://ragfinance.ir',
    idp_authorization_origin:'https://idp.staging.example',
    bootstrap_origin:'https://127.0.0.1:9843',
    product_origin:'https://127.0.0.1:9844',
    store_dir:store,
    proxy_proof_file:put('proxy',proxy),
    csrf_secret_file:put('csrf','staging-csrf-secret-at-least-32-chars-only-server'),
    alias_key_file:put('alias',Buffer.alloc(32,7).toString('base64url')),
    bootstrap_sign_key_file:put('boot-key','test-no-real-key'),
    product_sign_key_file:put('product-key','test-no-real-key'),
    tls_ca_file:put('ca','test-no-real-ca'),
    tls_client_cert_file:put('cert','test-no-real-cert'),
    tls_client_key_file:put('tls-key','test-no-real-key'),
    bootstrap_issuer:'urn:staging:bootstrap',bootstrap_audience:'urn:staging:bootstrap-api',
    bootstrap_kid:'bootstrap-staging',product_issuer:'urn:staging:product',
    product_audience:'urn:staging:product-api',product_kid:'product-staging',
    send_mode:'DISABLED'
  };
  const config=put('profile.json',JSON.stringify(common));
  try{
    for(const key of envKeys)delete process.env[key];
    process.env.AUTH_RUNTIME_PROFILE='private-staging';
    process.env.AUTH_STAGING_CONFIG_FILE=config;
    assert.equal(stagingProfile().send_mode,'DISABLED');
    assert.equal(publicOrigin(),'https://ragfinance.ir');
    const headers={
      'x-forwarded-proto':'https','x-forwarded-host':'ragfinance.ir',
      'x-auth-staging-proxy-proof':proxy
    };
    const request=new Request('http://127.0.0.1:3000/login',{headers});
    assert.equal(secureBrowser(request),true);
    assert.ok(csrf('a'.repeat(43)).length>20);
    assert.equal(secureBrowser(new Request(request.url,{headers:{
      ...headers,'x-auth-staging-proxy-proof':'forged-browser-header'}})),false);
    assert.equal(secureBrowser(new Request(request.url,{headers:{
      ...headers,'x-forwarded-proto':'http'}})),false);
    // A missing browser cookie MUST prevent any engine-status BFF action.
    const result=await forwardHistoryProxy(new Request(
      'http://127.0.0.1:3000/api/history/message-requests/engine-status?'+
      'requested_conversation_id=&client_message_id=cmsg_1&idempotency_key=key_12345678',
      {headers}),['message-requests','engine-status']);
    assert.equal(result.status,401);
    process.env.CI='true';
    assert.throws(()=>stagingProfile(),/PRIVATE_STAGING_DENIED/);
    assert.equal(secureBrowser(request),false);
    delete process.env.CI;
    process.env.AUTH_CI_DEMO_MODE='true';
    assert.throws(()=>stagingProfile(),/PRIVATE_STAGING_DENIED/);
    delete process.env.AUTH_CI_DEMO_MODE;
    chmodSync(common.proxy_proof_file,0o644);
    assert.throws(()=>stagingSecret(common.proxy_proof_file),/PRIVATE_STAGING_DENIED/);
    assert.throws(()=>stagingProfile(),/PRIVATE_STAGING_DENIED/);
  }finally{
    for(const key of envKeys){
      const prev=saved[key];
      if(prev===undefined)delete process.env[key];else process.env[key]=prev;
    }
    rmSync(root,{recursive:true,force:true});
  }
});
