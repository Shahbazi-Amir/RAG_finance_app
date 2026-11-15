import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sendMessage,recoverStatus,newSend,HistoryFailure} from '../../../apps/web/src/history/client.ts';
import {conformsToProductV1} from '../../../apps/web/src/history/product-validation.ts';
import {verifiedSourceUrl} from '../../../apps/web/src/ui/source-locator.ts';
import {isVerifiedLiveAnswer,productOutcomeLabel} from '../../../apps/web/src/ui/answer-visibility.ts';

const cases=JSON.parse(readFileSync(new URL(
  '../../../packages/contracts/fixtures/product.v1.cases.json',import.meta.url),'utf8')).cases;
function fixture(name){
  const hit=cases.find(x=>x.case_id===name&&x.expected_valid);
  assert.ok(hit,'Fixture missing '+name);
  return structuredClone(hit.document);
}
const response=(data,status=200)=>new Response(JSON.stringify(data),{status,
  headers:{'content-type':'application/json'}});
const withFetch=async (handler,task)=>{
  const saved=globalThis.fetch;globalThis.fetch=handler;
  try{return await task();}finally{globalThis.fetch=saved;}
};
test('one POST creates receipt; subsequent recovery/refesh is GET only, exact original null key',async()=>{
  const original=newSend('قانون بودجه چیست؟',null);
  const r=fixture('valid_send_message_receipt');
  r.requested_conversation_id=null;r.resolved_conversation_id='conv_1';
  r.client_message_id=original.client_message_id;r.idempotency_key=original.idempotency_key;
  const s=fixture('valid_history_status_not_found');
  s.requested_conversation_id=null;s.client_message_id=original.client_message_id;
  s.idempotency_key=original.idempotency_key;s.status='attempt_pending';
  s.resolved_conversation_id='conv_1';s.message_id='msg_1';
  s.attempt_id='attempt_1';s.attempt_request_id='req_1';
  s.attempt_trace_id='trace_1';s.reserved_answer_id='ans_1';
  assert.ok(conformsToProductV1(s,'message_request_status'));
  const methods=[],urls=[];
  await withFetch(async(url,init={})=>{
    methods.push(init.method??'GET');urls.push(String(url));
    if(init.method==='POST')return response(r,202);
    return response(s);
  },async()=>{
    assert.deepEqual(await sendMessage(original),{id:'conv_1',messageId:r.message_id});
    const recovered=await recoverStatus(original);
    assert.equal(recovered.status,'attempt_pending');
    assert.equal(recovered.attemptId,'attempt_1');
    assert.equal(recovered.attemptRequestId,'req_1');
    assert.equal(recovered.attemptTraceId,'trace_1');
    await recoverStatus(original); // browser reload/poll never posts
  });
  assert.deepEqual(methods,['POST','GET','GET']);
  assert.equal(urls[1],urls[2]);
  assert.match(urls[1],/requested_conversation_id=&client_message_id=/);
  assert.ok(!urls.some(u=>u.includes('owner_user_id')));
});
test('network-unknown POST does not authorize automatic re-post',async()=>{
  const original=newSend('سؤال آزمایشی',null);
  const requested=[];
  await withFetch(async(url,init)=>{
    requested.push((init?.method??'GET')+' '+url);
    if(init?.method==='POST')throw Error('connection drop');
    return response(fixture('valid_history_status_not_found'));
  },async()=>{
    await assert.rejects(sendMessage(original),e=>e instanceof HistoryFailure&&e.reason==='unknown');
    const status=await recoverStatus(original);
    assert.equal(status.status,'not_found');
  });
  assert.equal(requested.filter(x=>x.startsWith('POST')).length,1);
});
test('a source link is offered only for a valid verified HTTPS URL locator',()=>{
  const unresolved=fixture('valid_answer_unresolved_source');
  const source=unresolved.citations[0]?.source;
  if(source){
    assert.equal(verifiedSourceUrl(source),null);
    assert.equal(verifiedSourceUrl({...source,locator:{kind:'url',url:'javascript:alert(1)',page:null,timestamp_ms:null},
      resolution_status:'verified',attribution_status:'verified'}),null);
    assert.equal(verifiedSourceUrl({...source,locator:{
      kind:'url',url:'https://example.org/verified',page:null,timestamp_ms:null},
      resolution_status:'verified',attribution_status:'verified',
      display_title_origin:'source_record'}),'https://example.org/verified');
    assert.equal(verifiedSourceUrl({...source,locator:{
      kind:'url',url:'https://user:pass@example.org',page:null,timestamp_ms:null},
      resolution_status:'verified',attribution_status:'verified',
      display_title_origin:'source_record'}),null);
  }
});

test('synthetic/provisional Answer is never user-visible even if committed',()=>{
  const synthetic=fixture('valid_answer_unresolved_source');
  assert.equal(isVerifiedLiveAnswer(synthetic),false);
  assert.equal(isVerifiedLiveAnswer(null),false);
  const fake={...synthetic,provenance:{
    ...synthetic.provenance,origin:'LIVE_VERIFIED',
    rag_binding:{...synthetic.provenance.rag_binding,status:'provisional',adapter_verified:false}
  }};
  assert.equal(isVerifiedLiveAnswer(fake),false);
  const live={...synthetic,provenance:{
    ...synthetic.provenance,origin:'LIVE_VERIFIED',
    rag_binding:{...synthetic.provenance.rag_binding,status:'verified',adapter_verified:true}
  }};
  assert.equal(isVerifiedLiveAnswer(live),true);
});
test('no evidence vs technical error vs partial vs unknown are separate',()=>{
  const noAnswer=fixture('valid_answer_no_answer');
  const technical=fixture('valid_answer_technical_error');
  const partial=fixture('valid_answer_partial');
  const unknown=fixture('valid_answer_unknown');
  assert.match(productOutcomeLabel(noAnswer),/شاهد کافی/);
  assert.match(productOutcomeLabel(technical),/خطای فنی/);
  assert.match(productOutcomeLabel(partial),/ناقص/);
  assert.match(productOutcomeLabel(unknown),/نامعلوم/);
});
