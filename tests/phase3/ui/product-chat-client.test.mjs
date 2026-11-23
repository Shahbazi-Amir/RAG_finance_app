import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sendMessage,recoverStatus,recoverEngineStatus,newSend,HistoryFailure} from '../../../apps/web/src/history/client.ts';
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
    const correlators={requested_conversation_id:original.requested_conversation_id,
      client_message_id:original.client_message_id,idempotency_key:original.idempotency_key};
    assert.equal((await recoverStatus(correlators)).status,'attempt_pending');
  });
  assert.deepEqual(methods,['POST','GET','GET','GET']);
  assert.equal(urls[1],urls[2]);
  assert.match(urls[1],/requested_conversation_id=&client_message_id=/);
  assert.ok(!urls.some(u=>u.includes('owner_user_id')));
});
test('network-unknown POST and refresh recovery: identical correlators, GET only',async()=>{
  const original=newSend('سؤال آزمایشی',null);
  const correlation={
    requested_conversation_id:original.requested_conversation_id,
    client_message_id:original.client_message_id,
    idempotency_key:original.idempotency_key,
  };
  const requested=[];
  await withFetch(async(url,init)=>{
    requested.push({method:init?.method??'GET',url:String(url)});
    if(init?.method==='POST')throw Error('connection drop');
    // The shared valid fixture has STATIC ids; a server Status response must
    // echo the original operation's three correlators. Keep strict validation.
    const notFound=fixture('valid_history_status_not_found');
    Object.assign(notFound,correlation);
    return response(notFound);
  },async()=>{
    await assert.rejects(sendMessage(original),e=>
      e instanceof HistoryFailure&&e.reason==='unknown');
    assert.equal((await recoverStatus(correlation)).status,'not_found');
    // Simulate page reload: only opaque correlation survives; no question.
    assert.equal((await recoverStatus({...correlation})).status,'not_found');
  });
  assert.deepEqual(requested.map(r=>r.method),['POST','GET','GET']);
  assert.equal(requested[1].url,requested[2].url);
  for(const [key,value] of Object.entries(correlation))
    assert.equal(new URL(requested[1].url,'http://localhost').searchParams.get(key),
      value??'');
});

test('API no-dispatch engine-status: original GET correlation, terminal not an Answer',async()=>{
  const original=newSend('وضعیت فنی چیست؟',null);
  const correlation={requested_conversation_id:original.requested_conversation_id,
    client_message_id:original.client_message_id,idempotency_key:original.idempotency_key};
  const seen=[];
  const technical={kind:'no_dispatch_execution_status',
    contract_version:'api.no_dispatch_status.v1',request_id:'req_poll',
    trace_id:'trace_poll',attempt_id:'a'.repeat(32),attempt_trace_id:'trace_t2',
    product_status:'attempt_pending',preflight_state:'CONTEXT_READY',
    question_sha256_matches:true,top10_count:10,generation_calls:0,
    dispatch_performed:false,answer:null};
  await withFetch(async(url,init)=>{
    seen.push({url:String(url),method:init?.method??'GET'});
    return response(technical);
  },async()=>{
    const a=await recoverEngineStatus(correlation);
    assert.equal(a.state,'CONTEXT_READY');
    assert.equal(a.generationCalls,0);
    assert.equal(a.top10Count,10);
    assert.equal((await recoverEngineStatus({...correlation})).state,'CONTEXT_READY');
  });
  assert.deepEqual(seen.map(x=>x.method),['GET','GET']);
  assert.equal(seen[0].url,seen[1].url);
  for(const [key,value] of Object.entries(correlation))
    assert.equal(new URL(seen[0].url,'http://localhost').searchParams.get(key),value??'');
  await withFetch(async()=>response({...technical,dispatch_performed:true}),async()=>{
    await assert.rejects(recoverEngineStatus(correlation),
      e=>e instanceof HistoryFailure&&e.reason==='invalid');
  });
  await withFetch(async()=>response({...technical,answer:{answer_text:'SYNTHETIC'}}),async()=>{
    await assert.rejects(recoverEngineStatus(correlation),
      e=>e instanceof HistoryFailure&&e.reason==='invalid');
  });
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
  // A valid RAG provenance flag alone is NOT permission to show an Answer
  // whose claim points to an unresolved, uncitable source.
  assert.equal(isVerifiedLiveAnswer(live),false);
  const verifiedSource={...synthetic.citations[0].source,
    source_type:'book',source_id:'source_book_verified',
    resolution_status:'verified',attribution_status:'verified',
    display_title_origin:'source_record',credited_author_name:'نویسنده',
    locator:{kind:'book_page',url:null,page:12,timestamp_ms:null}};
  const trusted={...live,citations:[{...live.citations[0],source:verifiedSource}]};
  assert.equal(isVerifiedLiveAnswer(trusted),true);
  assert.equal(isVerifiedLiveAnswer({...trusted,claims:[]}),false);
  assert.equal(isVerifiedLiveAnswer({...trusted,claims:[{...trusted.claims[0],citation_ids:[]}]}),false);
  assert.equal(isVerifiedLiveAnswer({...trusted,citations:[{...trusted.citations[0],
    claim_ids:[]}]}),false);
  assert.equal(isVerifiedLiveAnswer({...trusted,citations:[{...trusted.citations[0],
    source:{...verifiedSource,attribution_status:'unknown'}}]}),false);
});
test('verified claim gate checks all five typed locators, rejects unsafe URL and synthetic metadata',()=>{
  const original=fixture('valid_answer_unresolved_source');
  const trusted={...original,provenance:{
    ...original.provenance,origin:'LIVE_VERIFIED',
    rag_binding:{...original.provenance.rag_binding,status:'verified',adapter_verified:true}
  }};
  const template={...original.citations[0].source,
    source_type:'website',source_id:'source_site_verified',
    resolution_status:'verified',attribution_status:'verified',
    display_title_origin:'source_record',credited_author_name:'مولف'};
  const withSource=source=>({...trusted,citations:[{...trusted.citations[0],source}]});
  const known=[
    {...template,locator:{kind:'url',url:'https://example.org/trusted',page:null,timestamp_ms:null}},
    {...template,source_type:'book',locator:{kind:'book_page',url:null,page:12,timestamp_ms:null}},
    {...template,source_type:'book',locator:{kind:'book_anchor',url:null,page:null,
      timestamp_ms:null,work_id:'w1',edition_id:'e1',anchor:'section-1'}},
    {...template,source_type:'transcript',locator:{kind:'transcript_timestamp',url:null,
      page:null,timestamp_ms:1000}},
    {...template,source_type:'transcript',locator:{kind:'transcript_segment',url:null,
      page:null,timestamp_ms:null,episode_id:'ep1',segment_anchor:'seg1'}}
  ];
  for(const source of known)assert.equal(isVerifiedLiveAnswer(withSource(source)),true,
    source.locator.kind);
  assert.equal(isVerifiedLiveAnswer(withSource({...known[0],locator:{
    ...known[0].locator,url:'javascript:alert(1)'}})),false);
  assert.equal(isVerifiedLiveAnswer(withSource({...known[1],locator:{
    ...known[1].locator,page:0}})),false);
  assert.equal(isVerifiedLiveAnswer(withSource({...known[4],locator:{
    ...known[4].locator,segment_anchor:''}})),false);
  assert.equal(isVerifiedLiveAnswer(withSource({...known[2],display_title_origin:'SYNTHETIC'})),false);
  const noAnswer=fixture('valid_answer_no_answer');
  assert.equal(isVerifiedLiveAnswer({...noAnswer,provenance:trusted.provenance}),true);
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
