import test from 'node:test';
import assert from 'node:assert/strict';
import {blockedCapability,selectRuntimeCapability,decodeRuntimeCapability,appOnlySendBlocked} from
  '../../../apps/web/src/ui/runtime-capability.ts';
import {GET} from '../../../apps/web/app/api/product-capabilities/route.ts';
import {forwardHistoryProxy} from '../../../apps/web/src/history/proxy.ts';

test('app-only dominates all NO_DISPATCH test/staging flags',()=>{
  const result=selectRuntimeCapability({
    appOnly:true,approvedNoDispatch:true,ciFixture:true
  });
  assert.equal(result.send_mode,'DISABLED');
  assert.equal(result.engine_available,false);
  assert.equal(result.generation_available,false);
  assert.deepEqual(decodeRuntimeCapability(result),result);
});
test('server caps are denied by default, even for a malformed runtime config',()=>{
  for(const input of [
    {appOnly:false,approvedNoDispatch:false,ciFixture:false},
    {appOnly:true,approvedNoDispatch:false,ciFixture:true},
    {appOnly:true,approvedNoDispatch:true,ciFixture:false}
  ])assert.equal(selectRuntimeCapability(input).send_mode,'DISABLED');
  assert.equal(blockedCapability().send_mode,'DISABLED');
});
test('only explicitly trusted signed NO_DISPATCH or CI fixture may show Send',()=>{
  for(const input of [
    {appOnly:false,approvedNoDispatch:true,ciFixture:false},
    {appOnly:false,approvedNoDispatch:false,ciFixture:true}
  ]){
    const result=selectRuntimeCapability(input);
    assert.equal(result.send_mode,'NO_DISPATCH_ONLY');
    assert.equal(result.generation_available,false);
    assert.equal(result.engine_available,false);
  }
});
test('unknown, forged and downgraded capability documents fail closed',()=>{
  const original=selectRuntimeCapability({appOnly:false,approvedNoDispatch:true,ciFixture:false});
  const invalids=[
    null,[],{},'NO_DISPATCH_ONLY',true,
    {...original,send_mode:'LIVE_ENGINE'},
    {...original,contract_version:'ui.runtime_capabilities.v2'},
    {...original,kind:'insecure'},
    {...original,engine_available:true},
    {...original,generation_available:true},
    {...original,owner_id:'attacker'},
    {...original,send_mode:null}
  ];
  for(const raw of invalids)assert.equal(decodeRuntimeCapability(raw),null);
});
test('app-only capability GET is public non-personal, no-store and always disabled',async()=>{
  const before=process.env.PHASE3_APP_MODE;
  const oldCI=process.env.CI,oldLogin=process.env.AUTH_CI_LOGIN_MODE;
  const oldChat=process.env.AUTH_CI_PRODUCT_CHAT_MODE;
  try{
    process.env.PHASE3_APP_MODE='APP_ONLY';
    process.env.CI='true';process.env.AUTH_CI_LOGIN_MODE='true';
    process.env.AUTH_CI_PRODUCT_CHAT_MODE='INVITED_RESULT_STUB_CI_ONLY';
    const res=GET();
    assert.equal(res.status,200);
    assert.match(res.headers.get('cache-control')??'',/no-store/);
    assert.deepEqual(decodeRuntimeCapability(await res.json()),blockedCapability());
  }finally{
    for(const [k,val] of Object.entries({
      PHASE3_APP_MODE:before,CI:oldCI,AUTH_CI_LOGIN_MODE:oldLogin,
      AUTH_CI_PRODUCT_CHAT_MODE:oldChat
    })){if(val===undefined)delete process.env[k];else process.env[k]=val;}
  }
});
test('app-only BFF Send denies before body consumption, upstream fetch or reservation',async()=>{
  const old=process.env.PHASE3_APP_MODE;
  const oldFetch=globalThis.fetch;
  let readCount=0,upstreamCalls=0;
  const body=new ReadableStream({
    pull(controller){readCount++;controller.enqueue(new TextEncoder().encode('{}'));controller.close();}
  },{highWaterMark:0});
  const request=new Request('http://127.0.0.1:3000/api/history/messages',{
    method:'POST',headers:{'content-type':'application/json'},body,duplex:'half'
  });
  globalThis.fetch=async()=>{upstreamCalls++;throw Error('FORBIDDEN_UPSTREAM');};
  process.env.PHASE3_APP_MODE='APP_ONLY';
  try{
    const res=await forwardHistoryProxy(request,['messages']);
    assert.equal(res.status,503);
    assert.equal((await res.json()).error,'ENGINE_NOT_AVAILABLE');
    assert.match(res.headers.get('cache-control')??'',/no-store/);
    assert.equal(readCount,0);
    assert.equal(upstreamCalls,0);
  }finally{
    if(old===undefined)delete process.env.PHASE3_APP_MODE;else process.env.PHASE3_APP_MODE=old;
    globalThis.fetch=oldFetch;
  }
});

test('unknown declared app profile never enables a Send endpoint',()=>{
  assert.equal(appOnlySendBlocked(undefined),false);
  assert.equal(appOnlySendBlocked('NO_DISPATCH_ONLY'),false);
  for(const value of ['APP_ONLY','APP_ONLY ','APP_ONYL','live','', 'LIVE_ENGINE']){
    assert.equal(appOnlySendBlocked(value),true,value);
  }
});
