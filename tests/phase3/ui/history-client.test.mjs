import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 HistoryFailure,newSend,newCreate,mergeUnique,sendMessage,createConversation,
 recoverStatus,conversations,messages,failureLabel
} from '../../../apps/web/src/history/client.ts';
import {conformsToProductV1} from '../../../apps/web/src/history/product-validation.ts';

// Every negative response is a mutation of a real POSITIVE product.v1 fixture.
const cases=JSON.parse(readFileSync(
 new URL('../../../packages/contracts/fixtures/product.v1.cases.json',import.meta.url),'utf8')).cases;
function valid(name){
 const c=cases.find(x=>x.case_id===name);
 assert.ok(c&&c.expected_valid===true,'Missing positive case '+name);
 const v=structuredClone(c.document);
 assert.ok(conformsToProductV1(v,v.kind),'Shared schema must validate '+name);
 return v;
}
const reply=(v,status=200)=>new Response(JSON.stringify(v),{status,headers:{'content-type':'application/json'}});
async function withFetch(handler,run){
 const prior=globalThis.fetch;globalThis.fetch=handler;
 try{return await run();}finally{globalThis.fetch=prior;}
}
const mutate=(source,fn)=>{const v=structuredClone(source);fn(v);return v;};
const reject=async(action,v)=>withFetch(async()=>reply(v),
 async()=>assert.rejects(action,e=>e instanceof HistoryFailure&&e.reason==='invalid'));
function receipt(req){
 const v=valid('valid_send_message_receipt');
 v.requested_conversation_id=req.requested_conversation_id;
 v.resolved_conversation_id=req.requested_conversation_id??'conv_1';
 v.client_message_id=req.client_message_id;v.idempotency_key=req.idempotency_key;
 return v;
}
function status(req,phase='not_found'){
 const v=valid('valid_history_status_not_found');
 v.requested_conversation_id=req.requested_conversation_id;
 v.client_message_id=req.client_message_id;v.idempotency_key=req.idempotency_key;
 v.status=phase;
 if(phase!=='not_found'){
  v.resolved_conversation_id=req.requested_conversation_id??'conv_1';v.message_id='msg_1';
 }
 if(!['not_found','persisted'].includes(phase)){
  v.attempt_id='attempt_1';v.attempt_request_id='req_attempt_1';
  v.attempt_trace_id='trace_attempt_1';v.reserved_answer_id='ans_1';
 }
 if(phase==='answer_committed'){
  v.answer_id='ans_1';v.answer=valid('valid_answer_unresolved_source');
  v.answer.conversation_id=v.resolved_conversation_id;v.answer.answer_id=v.answer_id;
  v.answer.message_id='msg_2';v.answer.request_id=v.attempt_request_id;
  v.answer.trace_id=v.attempt_trace_id;
 }
 assert.ok(conformsToProductV1(v,'message_request_status'),'Derived valid status '+phase);
 return v;
}
function answeredPage(){
 const v=valid('valid_history_messages_page');
 v.page.limit=2;v.items.push(valid('valid_assistant_message'));
 v.answers.push(valid('valid_answer_unresolved_source'));
 assert.ok(conformsToProductV1(v,'conversation_messages_page'));
 return v;
}
test('wire IDs original null, contract version and replay scope',()=>{
 const first=newSend('پرسش اول',null),second=newSend('پرسش دوم','conv_1');
 assert.ok(conformsToProductV1(first,'send_message_request'));
 assert.ok(conformsToProductV1(second,'send_message_request'));
 assert.equal(first.requested_conversation_id,null);
 assert.equal(second.requested_conversation_id,'conv_1');
 assert.notEqual(first.client_message_id,second.client_message_id);
 assert.notEqual(first.idempotency_key,second.idempotency_key);
 assert.ok(conformsToProductV1(newCreate('عنوان'),'create_conversation_request'));
});
test('cursor merge retains first occurrence',()=>{
 assert.deepEqual(mergeUnique([{id:'a',text:1}],[{id:'a',text:2},{id:'b'}],x=>x.id),
   [{id:'a',text:1},{id:'b'}]);
});
test('send receipt complete required fields, owner, scope and replay',async t=>{
 const request=newSend('متن',null),good=receipt(request);
 await withFetch(async(url,opts)=>{
   assert.equal(url,'/api/history/messages');assert.deepEqual(JSON.parse(opts.body),request);
   return reply(good);
 },async()=>assert.deepEqual(await sendMessage(request),{id:'conv_1',messageId:'msg_1'}));
 await withFetch(async()=>reply({...good,disposition:'replayed'}),
   async()=>assert.deepEqual(await sendMessage(request),{id:'conv_1',messageId:'msg_1'}));
 await withFetch(async()=>reply({kind:'error_response',contract_version:'product.v1'},409),
   async()=>assert.rejects(sendMessage(request),e=>e.reason==='conflict'));
 const badCases=[
  ['missing request_id',v=>{delete v.request_id}],
  ['missing owner',v=>{delete v.owner_user_id}],
  ['malformed hash',v=>{v.payload_sha256='bad'}],
  ['wrong idempotency scope',v=>{v.idempotency_scope='wrong'}],
  ['mismatched client ID',v=>{v.client_message_id='other'}],
  ['invalid resolved ID',v=>{v.resolved_conversation_id=''}]
 ];
 for(const [name,change] of badCases)await t.test(name,()=>reject(()=>sendMessage(request),mutate(good,change)));
 const existing=newSend('متن','conv_1');
 await reject(()=>sendMessage(existing),mutate(receipt(existing),v=>{v.resolved_conversation_id='conv_other'}));
});
test('create receipt must have a matching owner, active conversation and metadata',async()=>{
 const request=newCreate('نمونه'),good=valid('valid_history_create_receipt');
 good.client_conversation_id=request.client_conversation_id;
 good.idempotency_key=request.idempotency_key;
 await withFetch(async()=>reply(good),async()=>assert.equal(await createConversation(request),'conv_1'));
 await reject(()=>createConversation(request),mutate(good,v=>{delete v.trace_id}));
 await reject(()=>createConversation(request),mutate(good,v=>{v.conversation.owner_user_id='other'}));
 await reject(()=>createConversation(request),mutate(good,v=>{v.conversation.state='deletion_requested'}));
});
test('status accepts valid stages; current poll trace does not replace T2 attempt trace',async()=>{
 const req=newSend('پرسش',null),committed=status(req,'answer_committed');
 assert.notEqual(committed.request_id,committed.attempt_request_id);
 assert.notEqual(committed.trace_id,committed.attempt_trace_id);
 for(const phase of ['not_found','persisted','attempt_pending','attempt_unknown','failed','cancelled','answer_committed']){
  let query;
  await withFetch(async(url,opts)=>{
    assert.equal(opts.method,'GET');query=new URL(url,'http://testserver');
    return reply(status(req,phase));
  },async()=>{
    const result=await recoverStatus(req);
    assert.equal(result.status,phase);
    assert.equal(result.answer===null,phase!=='answer_committed');
    if(result.answer)assert.equal(result.answer.message_id,'msg_2');
  });
  assert.equal(query.searchParams.get('requested_conversation_id'),'');
 }
});
test('unknown state and inconsistent T1/T2/T3 never confirm persistence',async t=>{
 const req=newSend('پرسش',null),persisted=status(req,'persisted');
 const committed=status(req,'answer_committed');
 const invalidCases=[
  ['unknown status enum',mutate(persisted,v=>{v.status='totally_confirmed'})],
  ['persisted with Attempt',mutate(persisted,v=>{v.attempt_id='attempt_1'})],
  ['persisted with Answer',mutate(persisted,v=>{v.answer=structuredClone(committed.answer)})],
  ['pending with final Answer',mutate(committed,v=>{v.status='attempt_pending'})],
  ['unknown with final Answer',mutate(committed,v=>{v.status='attempt_unknown'})],
  ['failed with final Answer',mutate(committed,v=>{v.status='failed'})],
  ['cancelled with final Answer',mutate(committed,v=>{v.status='cancelled'})],
  ['committed without Answer',mutate(committed,v=>{v.answer=null})],
  ['committed without Attempt ID',mutate(committed,v=>{v.attempt_id=null})],
  ['wrong final Answer ID',mutate(committed,v=>{v.answer_id='ans_wrong'})],
  ['wrong reserved Answer ID',mutate(committed,v=>{v.reserved_answer_id='ans_wrong'})],
  ['wrong Answer conversation',mutate(committed,v=>{v.answer.conversation_id='conv_other'})],
  ['Answer points at user Message',mutate(committed,v=>{v.answer.message_id='msg_1'})],
  ['Answer request uses current poll rather than Attempt',mutate(committed,v=>{v.answer.request_id=v.request_id})],
  ['Answer trace uses current poll rather than Attempt',mutate(committed,v=>{v.answer.trace_id=v.trace_id})],
  ['Answer trace mismatches Attempt',mutate(committed,v=>{v.answer.trace_id='trace_unrelated'})],
  ['status scope mismatch',mutate(persisted,v=>{v.idempotency_key='key_other1234'})],
  ['missing current trace',mutate(persisted,v=>{delete v.trace_id})],
 ];
 for(const [name,bad] of invalidCases)
  await t.test(name,()=>reject(()=>recoverStatus(req),bad));
});
test('conversation list: owner, required fields, cursor and limit',async t=>{
 const good=valid('valid_paginated_conversations');good.page.limit=2;
 await withFetch(async()=>reply(good),async()=>{
  const result=await conversations();assert.equal(result.items[0].id,'conv_1');
 });
 const badCases=[
  ['missing scope owner',v=>{delete v.scope_user_id}],
  ['cross-owner item',v=>{v.items[0].owner_user_id='other'}],
  ['invalid conversation state',v=>{v.items[0].state='invalid'}],
  ['missing created_at',v=>{delete v.items[0].created_at}],
  ['duplicate conversation',v=>{v.items.push(structuredClone(v.items[0]))}],
  ['has_more without cursor',v=>{v.page.has_more=true}],
  ['extra cursor without has_more',v=>{v.page.next_cursor='cursor'}],
  ['limit different than requested',v=>{v.page.limit=20}]
 ];
 for(const [name,change] of badCases)
  await t.test(name,()=>reject(()=>conversations(),mutate(good,change)));
});
test('message page requires exactly one related Answer for each assistant Message',async t=>{
 const good=answeredPage();
 await withFetch(async()=>reply(good),async()=>{
  const result=await messages('conv_1');
  assert.deepEqual(result.items.map(x=>x.id),['msg_1','msg_2']);
  assert.deepEqual(result.answers.map(x=>x.id),['ans_1']);
 });
 const badCases=[
  ['assistant Answer missing',v=>{v.answers=[]}],
  ['duplicate Answer',v=>{v.answers.push(structuredClone(v.answers[0]))}],
  ['duplicate Message',v=>{v.items.push(structuredClone(v.items[1]))}],
  ['unrelated assistant Message',v=>{v.answers[0].message_id='msg_wrong'}],
  ['Answer ID mismatch',v=>{v.answers[0].answer_id='ans_wrong'}],
  ['Answer wrong conversation',v=>{v.answers[0].conversation_id='conv_wrong'}],
  ['cross-owner Message',v=>{v.items[0].owner_user_id='other'}],
  ['user message with Answer',v=>{v.items[0].answer_id='ans_1'}],
  ['assistant without Answer ID',v=>{v.items[1].answer_id=null}],
  ['duplicate Claim ID',v=>{v.answers[0].claims.push({...v.answers[0].claims[0]})}],
  ['asymmetric citation',v=>{v.answers[0].citations[0].claim_ids=['other_claim']}],
  ['missing text',v=>{delete v.items[0].text}],
  ['page over requested limit',v=>{v.page.limit=1}],
  ['cursor without has_more',v=>{v.page.next_cursor='cursor'}]
 ];
 for(const [name,change] of badCases)
  await t.test(name,()=>reject(()=>messages('conv_1'),mutate(good,change)));
});
test('401 unauthorized and network unknown never become Mock success',async()=>{
 await withFetch(async()=>reply({kind:'error_response',contract_version:'product.v1'},401),
   async()=>assert.rejects(conversations(),e=>e instanceof HistoryFailure&&e.reason==='unauthorized'));
 await withFetch(async()=>{throw new TypeError('offline');},
   async()=>assert.rejects(sendMessage(newSend('متن','conv_1')),
    e=>e instanceof HistoryFailure&&e.reason==='unknown'));
 assert.match(failureLabel(new HistoryFailure(401,'unauthorized')),/ورود/);
});
