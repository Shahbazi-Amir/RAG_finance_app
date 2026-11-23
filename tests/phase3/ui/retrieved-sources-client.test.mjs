import test from 'node:test';
import assert from 'node:assert/strict';
import {newSend,recoverRetrievedSources,HistoryFailure} from '../../../apps/web/src/history/client.ts';

const correlators=()=>{
 const request=newSend('سؤال بازیابی',null);
 return {requested_conversation_id:request.requested_conversation_id,
  client_message_id:request.client_message_id,idempotency_key:request.idempotency_key};
};
const receipt=(state='PARTIAL_UNVERIFIED')=>({
 kind:'retrieved_sources',contract_version:'api.retrieved_sources.v1',
 attempt_id:'a'.repeat(32),attempt_trace_id:'b'.repeat(32),retrieval_state:state,
 engine_sha256:'93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d',
 chunks_sha256:'3891c4ecad9332ba753cd605bbccd99da9d063f64934a30ee39e495349cffb50',
 generation_calls:0,rows:state==='PARTIAL_UNVERIFIED'?[
  {position:1,chunk_id:'observed_1',source_id:'source_1',chunk_match:'PASS',
   source_validation:'UNVERIFIED',locator_validation:'PENDING_STRUCTURE',verified_locators:[]},
  {position:2,chunk_id:'observed_2',source_id:null,chunk_match:'PASS',
   source_validation:'UNVERIFIED',locator_validation:'PENDING_STRUCTURE',verified_locators:[]}
 ]:[]
});
const reply=(doc,status=200)=>new Response(JSON.stringify(doc),{status});
const withFetch=async (handler,fn)=>{const old=globalThis.fetch;globalThis.fetch=handler;
 try{return await fn();}finally{globalThis.fetch=old;}};
const invalid=e=>e instanceof HistoryFailure&&e.reason==='invalid';

test('retrieved sources use only original GET correlators; refresh never POSTs',async()=>{
 const c=correlators(),seen=[];
 await withFetch(async(url,opts)=>{seen.push({url:String(url),method:opts.method});
  return reply(receipt());},async()=>{
  const a=await recoverRetrievedSources(c),b=await recoverRetrievedSources({...c});
  assert.deepEqual(a,b);assert.equal(a.attemptId,'a'.repeat(32));
  assert.equal(a.attemptTraceId,'b'.repeat(32));
  assert.deepEqual(a.rows.map(x=>x.position),[1,2]);
  assert.equal(a.rows[0].chunkId,'observed_1');
  assert.equal(a.rows[1].sourceId,null);
  assert.deepEqual(a.rows[0].verifiedLocators,[]);
 });
 assert.deepEqual(seen.map(x=>x.method),['GET','GET']);
 assert.equal(seen[0].url,seen[1].url);
 const parsed=new URL(seen[0].url,'http://localhost').searchParams;
 assert.deepEqual([...parsed.keys()].sort(),
  ['client_message_id','idempotency_key','requested_conversation_id'].sort());
 for(const [k,v] of Object.entries(c))assert.equal(parsed.get(k),v??'');
});

test('malformed row, locator, provenance, hash, Attempt or status fails closed',async()=>{
 const c=correlators(),mutations=[
  d=>d.rows[1].position=1,
  d=>d.rows[0].verified_locators=[{url:'https://example.org/unapproved'}],
  d=>d.rows[0].locator_validation='VERIFIED',
  d=>d.rows[0].source_validation='VERIFIED',
  d=>d.rows[0].html='<script>alert(1)</script>',
  d=>d.rows[0].chunk_id='',
  d=>d.rows[0].position=11,
  d=>d.rows[0].source_id='s'.repeat(257),
  d=>d.attempt_trace_id='wrong',
  d=>d.engine_sha256='0'.repeat(64),
  d=>d.chunks_sha256='f'.repeat(64),
  d=>d.retrieval_state='EVIDENCE_INVALID'
 ];
 for(const mutate of mutations){const d=receipt();mutate(d);
  await withFetch(async()=>reply(d),async()=>
   assert.rejects(recoverRetrievedSources(c),invalid));
 }
});
test('no evidence states never expose rows; 404 is not fabricated, 401 propagates',async()=>{
 const c=correlators();
 for(const state of ['NOT_AVAILABLE','EVIDENCE_INVALID','EVIDENCE_NOT_AVAILABLE']){
  await withFetch(async()=>reply(receipt(state)),async()=>{
   const r=await recoverRetrievedSources(c);
   assert.equal(r.retrievalState,state);assert.equal(r.rows.length,0);
  });
 }
 await withFetch(async()=>reply({error:'NOT_FOUND'},404),
  async()=>assert.equal(await recoverRetrievedSources(c),null));
 await withFetch(async()=>reply({error:'AUTH_REQUIRED'},401),
  async()=>assert.rejects(recoverRetrievedSources(c),
   e=>e instanceof HistoryFailure&&e.reason==='unauthorized'));
});