import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {newSend,HistoryFailure} from '../../../apps/web/src/history/client.ts';
import {parseInvitedFixture,recoverInvitedFixture} from '../../../apps/web/src/history/invited-fixture.ts';
import {conformsToPinnedSchema} from '../../../apps/web/src/history/product-validation.ts';

const schemaUrl=new URL('../../../apps/web/src/history/fixtures/staging_invited_live_result.v1.schema.json',import.meta.url);
const sampleUrl=new URL('./fixtures/staging_invited_live_result_ready.example.json',import.meta.url);
const source=(url)=>readFileSync(url);
const schema=JSON.parse(source(schemaUrl));
const ready=JSON.parse(source(sampleUrl));
const gitBlobHash=(bytes)=>createHash('sha1')
  .update('blob '+bytes.length+'\0').update(bytes).digest('hex');
const copy=()=>structuredClone(ready);
const binding=()=>({
  requested_conversation_id:ready.requested_conversation_id,
  client_message_id:ready.client_message_id,
  idempotency_key:ready.idempotency_key
});
const response=(data)=>new Response(JSON.stringify(data),{status:200,
  headers:{'content-type':'application/json'}});

test('exact API #53 Schema and READY example blobs copied, not hand-invented',()=>{
  assert.equal(gitBlobHash(source(schemaUrl)),'dfc0ea520e6333491d01cab48831eb2a7508b428');
  assert.equal(gitBlobHash(source(sampleUrl)),'967d9943406159186a408db69820fc601592f32c');
  assert.equal(schema.$id,'urn:ragfinance:staging:invited_live_result:v1:ci_fixture');
  assert.equal(conformsToPinnedSchema(ready,schema),true);
  assert.equal(ready.provenance.product_live_verified,false);
  assert.equal(ready.answer.citations[0].locator,null);
  assert.equal(ready.answer.citations[0].excerpt,null);
});

test('READY is clearly synthetic; citation has source ID but NO locator or quote',()=>{
  const r=parseInvitedFixture(copy(),binding());
  assert.equal(r.state,'READY');
  assert.match(r.answer.text,/نمونهٔ آزمایشی/);
  assert.equal(r.answer.citations[0].source_id,'fixture:budget-example-001');
  assert.equal(r.answer.citations[0].citation_id,'fixture-cite-budget-01');
  assert.equal(r.answer.citations[0].locator,null);
  assert.equal(r.answer.citations[0].excerpt,null);
  assert.match(r.warning,/استناد تأییدشدهٔ محصول نیستند/);
});

test('PENDING FAILED UNKNOWN all reject an Answer and retain immutable Attempt',()=>{
  for(const state of ['PENDING','FAILED','UNKNOWN']){
    const x=copy();x.result_status=state;x.answer=null;x.retention_expires_at_unix=null;
    assert.equal(conformsToPinnedSchema(x,schema),true,state);
    const parsed=parseInvitedFixture(x,binding());
    assert.equal(parsed.state,state);
    assert.equal(parsed.answer,null);
    assert.equal(parsed.attemptId,ready.attempt_id);
    x.answer=ready.answer;
    assert.equal(conformsToPinnedSchema(x,schema),false,state+' cannot contain Answer');
    assert.throws(()=>parseInvitedFixture(x,binding()),e=>
      e instanceof HistoryFailure&&e.reason==='invalid');
  }
});

test('fixture source, provenance, locator, quote, cross-Attempt and extra fields fail closed',()=>{
  const bad=[
    x=>{x.provenance.product_live_verified=true;},
    x=>{x.provenance.state='LIVE_VERIFIED';},
    x=>{x.answer.citations[0].locator='https://not-real.example';},
    x=>{x.answer.citations[0].excerpt='ساختگی';},
    x=>{x.answer.citations[0].source_id='real:forged';},
    x=>{x.attempt_id='not-an-attempt';},
    x=>{x.unexpected=true;},
    x=>{x.client_message_id='other_attempt';},
    x=>{x.idempotency_key='other-original';},
  ];
  for(const mutate of bad){
    const x=copy();mutate(x);
    assert.throws(()=>parseInvitedFixture(x,binding()),e=>
      e instanceof HistoryFailure&&e.reason==='invalid');
  }
});

test('two recovery GETs after refresh use only the original three IDs, never POST',async()=>{
  const original=newSend('پرسش فارسی مصنوعی',null);
  const ids={requested_conversation_id:original.requested_conversation_id,
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key};
  const requested=[];
  const oldFetch=globalThis.fetch;
  globalThis.fetch=async(url,init)=>{
    requested.push({url:String(url),method:init?.method??'GET',body:init?.body});
    const x=copy();Object.assign(x,ids);
    return response(x);
  };
  try{
    assert.equal((await recoverInvitedFixture(ids)).state,'READY');
    assert.equal((await recoverInvitedFixture({...ids})).attemptId,ready.attempt_id);
  }finally{globalThis.fetch=oldFetch;}
  assert.deepEqual(requested.map(x=>x.method),['GET','GET']);
  assert.equal(requested[0].url,requested[1].url);
  assert.ok(requested.every(x=>x.body===undefined));
  const params=new URL(requested[0].url,'http://127.0.0.1').searchParams;
  assert.deepEqual([...params.keys()],
    ['requested_conversation_id','client_message_id','idempotency_key']);
  for(const [key,value] of Object.entries(ids))assert.equal(params.get(key),value??'');
  assert.ok(!requested[0].url.includes('owner_user_id'));
});
