/**
 * Actual apps/web productRequest() source calling actual private APP_ONLY ASGI
 * via mTLS. Test-only independent synthetic server session state; no browser,
 * cookie forgery, OIDC or production admission.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {productRequest} from '../../../../apps/web/src/auth/server/product-session.ts';

assert.equal(process.env.CI,'true');
assert.equal(process.env.AUTH_CI_DEMO_MODE,'true');
assert.equal(process.env.PHASE3_APP_MODE,'APP_ONLY');
const states=JSON.parse(readFileSync('/tmp/actors.json','utf8'));
assert.deepEqual(Object.keys(states).sort(),['a','b']);
const active=(who)=>{
  const state=states[who];
  assert.match(state.owner,/^[A-Za-z0-9_-]{1,128}$/);
  assert.match(state.token,/^[A-Za-z0-9_-]{43,256}$/);
  return {ownerId:state.owner,sessionVerifier:state.token,
    epoch:state.epoch,generation:state.generation};
};
const request=async (operation,who,query,operationId='')=>{
  const result=await productRequest(operation,active(who),query,operationId);
  assert.ok([200,401,404,503].includes(result.status),'unexpected BFF upstream status '+result.status);
  let doc;
  try{doc=JSON.parse(result.body);}catch{throw Error('non-JSON BFF response status '+result.status);}
  return {status:result.status,doc};
};
const phase=process.argv[2];
assert.ok(['before','after','revoked'].includes(phase),'explicit phase required');
if(phase==='revoked'){
  assert.equal((await request('history','a','?limit=2')).status,401);
  assert.equal((await request('history','b','?limit=2')).status,200);
  console.log('REAL_BFF_RESTORED_REVOKED_A_401_B_200=PASS');
  process.exit(0);
}
for(const [who,total,messages] of [['a',5,4],['b',3,2]]){
  let cursor=null;
  const ids=[];
  do {
    const query='?limit=2'+(cursor?'&cursor='+cursor:'');
    const {status,doc}=await request('history',who,query);
    assert.equal(status,200);
    assert.equal(doc.kind,'conversation_page');
    assert.equal(doc.scope_user_id,states[who].owner);
    assert.equal(doc.page.limit,2);
    for(const item of doc.items){
      assert.equal(item.owner_user_id,states[who].owner);
      ids.push(item.conversation_id);
    }
    cursor=doc.page.next_cursor;
  }while(cursor);
  assert.deepEqual(ids,Array.from({length:total},(_,n)=>'f3-net-'+who+'-'+(total-n)));
  const refresh=await request('history',who,'?limit=2');
  assert.equal(refresh.status,200);
  assert.deepEqual(refresh.doc.items.map(item=>item.conversation_id),ids.slice(0,2));
  const thread=await request('messages',who,'?limit=2','f3-net-'+who+'-1');
  assert.equal(thread.status,200);
  assert.equal(thread.doc.kind,'conversation_messages_page');
  assert.equal(thread.doc.items.length,Math.min(messages,2));
  assert.ok(thread.doc.items.every(m=>m.owner_user_id===states[who].owner));
}
const bToA=await request('messages','b','?limit=2','f3-net-a-1');
const aToB=await request('messages','a','?limit=2','f3-net-b-1');
assert.equal(bToA.status,404);
assert.equal(aToB.status,404);
const ac=await request('history','a','?limit=2');
assert.equal(ac.status,200);
const cursor=ac.doc.page.next_cursor;
assert.ok(cursor);
const foreignCursor=await request('history','b','?limit=2&cursor='+cursor);
assert.equal(foreignCursor.status,404);
console.log('REAL_WEB_PRODUCT_REQUEST_BFF_SOURCE_SIGNED_MTLS_API_PG_AB_PAGINATION_404=PASS');
console.log('REAL_BFF_'+phase.toUpperCase()+'_OWNER_REFRESH=PASS');
console.log('REAL_WEB_PRODUCT_REQUEST_NO_BROWSER_NO_REAL_OIDC=CONFIRMED');
