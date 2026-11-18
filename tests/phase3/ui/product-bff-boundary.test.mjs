import test from 'node:test';
import assert from 'node:assert/strict';
import {forwardHistoryProxy} from '../../../apps/web/src/history/proxy.ts';

/** Negative tests only; never create an alias, token, actor or upstream API. */
async function withConfig(changes,run){
  const saved=Object.fromEntries(Object.keys(changes).map(k=>[k,process.env[k]]));
  const oldFetch=globalThis.fetch;
  let network=0;globalThis.fetch=async()=>{network++;throw Error('external fetch forbidden');};
  for(const [k,v] of Object.entries(changes)){
    if(v===undefined)delete process.env[k];
    else process.env[k]=v;
  }
  try{await run(()=>network);}
  finally{
    globalThis.fetch=oldFetch;
    for(const [k,v] of Object.entries(saved)){
      if(v===undefined)delete process.env[k];
      else process.env[k]=v;
    }
  }
}
test('Product staging mode cannot silently fall back to historical CI Fixture proxy',async()=>{
  await withConfig({CI:'true',AUTH_CI_LOGIN_MODE:undefined,AUTH_CI_DEMO_MODE:'true',
    AUTH_CI_PRODUCT_CHAT_MODE:'NO_DISPATCH_ONLY',
    HISTORY_UPSTREAM_ORIGIN:'http://127.0.0.1:8111'},async(network)=>{
      const request=new Request('http://127.0.0.1:3000/api/history/messages',{
        method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({question:'پرسش'})});
      const res=await forwardHistoryProxy(request,['messages']);
      assert.equal(res.status,503);
      assert.equal(network(),0);
    });
});
test('Authenticated mode denies missing browser proxy proof before any mutation',async()=>{
  await withConfig({CI:'true',AUTH_CI_LOGIN_MODE:'true',AUTH_CI_DEMO_MODE:'true',
    AUTH_CI_PRODUCT_CHAT_MODE:'NO_DISPATCH_ONLY',
    AUTH_CI_PUBLIC_ORIGIN:'https://127.0.0.1:3443',
    AUTH_CI_PROXY_SECRET:'test-proxy-secret-32-bytes-minimum-123456',
    HISTORY_UPSTREAM_ORIGIN:'http://127.0.0.1:8111'},async(network)=>{
      const request=new Request('http://127.0.0.1:3000/api/history/messages',{
        method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({question:'پرسش'})});
      const res=await forwardHistoryProxy(request,['messages']);
      assert.equal(res.status,503);
      assert.equal(network(),0);
    });
});
test('Valid private proxy proof without login cookie yields 401, no fallback',async()=>{
  const proof='test-proxy-secret-32-bytes-minimum-123456';
  await withConfig({CI:'true',AUTH_CI_LOGIN_MODE:'true',AUTH_CI_DEMO_MODE:'true',
    AUTH_CI_PRODUCT_CHAT_MODE:'NO_DISPATCH_ONLY',
    AUTH_CI_PUBLIC_ORIGIN:'https://127.0.0.1:3443',
    AUTH_CI_PROXY_SECRET:proof,
    HISTORY_UPSTREAM_ORIGIN:'http://127.0.0.1:8111'},async(network)=>{
      const request=new Request('http://127.0.0.1:3000/api/history/message-requests/status',{
        headers:{'x-auth-ci-proxy-proof':proof}});
      const res=await forwardHistoryProxy(request,['message-requests','status']);
      assert.equal(res.status,401);
      assert.equal(network(),0);
    });
});
