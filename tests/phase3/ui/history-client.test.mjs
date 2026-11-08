import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HistoryFailure,newSend,newCreate,mergeUnique,sendMessage,recoverStatus,
  conversations,messages,failureLabel
} from '../../../apps/web/src/history/client.ts';

function reply(body,status=200){return new Response(JSON.stringify(body),{status,
  headers:{'content-type':'application/json'}});}
async function withFetch(handler,run){
  const previous=globalThis.fetch;
  globalThis.fetch=handler;
  try{return await run();}finally{globalThis.fetch=previous;}
}
test('wire requests use product.v1, stable original null and independent local/server IDs',()=>{
  const one=newSend('پرسش اول',null),two=newSend('پرسش دوم','server_conv_01');
  assert.equal(one.kind,'send_message_request');
  assert.equal(one.contract_version,'product.v1');
  assert.equal(one.requested_conversation_id,null);
  assert.equal(two.requested_conversation_id,'server_conv_01');
  assert.notEqual(one.client_message_id,two.client_message_id);
  assert.notEqual(one.idempotency_key,two.idempotency_key);
  assert.notEqual(one.client_message_id,one.requested_conversation_id);
  assert.ok(one.idempotency_key.length>=8);
  assert.equal(newCreate('عنوان').kind,'create_conversation_request');
});
test('dedupes pages by stable server identifiers, preserving first appearance',()=>{
  const a={id:'a',text:'original'},b={id:'b',text:'other'},c={id:'a',text:'changed'};
  assert.deepEqual(mergeUnique([a],[c,b],x=>x.id),[a,b]);
});
test('POST replay uses the exact same payload/key and never reports conflict as success',async()=>{
  const req=newSend('متن',null);
  const payload={kind:'send_message_receipt',contract_version:'product.v1',requested_conversation_id:null,
    client_message_id:req.client_message_id,idempotency_key:req.idempotency_key,
    disposition:'replayed',resolved_conversation_id:'db_conv',message_id:'db_message',error:null};
  let seen;
  await withFetch(async (url,options)=>{
    seen={url,body:JSON.parse(options.body)};
    return reply(payload);
  },async()=>{
    const result=await sendMessage(req);
    assert.deepEqual(result,{id:'db_conv',messageId:'db_message'});
  });
  assert.deepEqual(seen.body,req);
  assert.equal(seen.url,'/api/history/messages');
  await withFetch(async()=>reply({kind:'error_response',contract_version:'product.v1',
      error:{code:'IDEMPOTENCY_CONFLICT'}},409),
    async()=>assert.rejects(sendMessage(req),e=>e instanceof HistoryFailure&&e.reason==='conflict'));
});
test('Status only issues a GET and keeps requested_conversation_id=null encoded as empty',async()=>{
  const req=newSend('متن',null);
  let query;
  await withFetch(async (url,opts)=>{
    query=new URL(url,'http://testserver');
    assert.equal(opts.method,'GET');
    return reply({kind:'message_request_status',contract_version:'product.v1',status:'persisted',
      requested_conversation_id:null,client_message_id:req.client_message_id,
      idempotency_key:req.idempotency_key,resolved_conversation_id:'db_conv',
      message_id:'db_msg',answer:null});
  },async()=>{
    const result=await recoverStatus(req);
    assert.equal(result.status,'persisted');
    assert.equal(result.answer,null);
  });
  assert.equal(query.searchParams.get('requested_conversation_id'),'');
  assert.equal(query.searchParams.get('client_message_id'),req.client_message_id);
});
test('401 stays unauthorized; network error stays unknown without mock fallback',async()=>{
  await withFetch(async()=>reply({kind:'error_response',contract_version:'product.v1'},401),
    async()=>assert.rejects(conversations(),e=>e instanceof HistoryFailure&&e.reason==='unauthorized'));
  const req=newSend('متن','db_conv');
  await withFetch(async()=>{throw new TypeError('network')},
    async()=>assert.rejects(sendMessage(req),e=>e instanceof HistoryFailure&&e.reason==='unknown'));
  assert.match(failureLabel(new HistoryFailure(401,'unauthorized')),/ورود/);
});
test('rejects unrelated Answer payloads rather than attaching them to another chat',async()=>{
  const list={kind:'conversation_messages_page',contract_version:'product.v1',conversation_id:'db_a',
    owner_user_id:'actor_a',items:[{kind:'message',contract_version:'product.v1',owner_user_id:'actor_a',
      conversation_id:'db_a',message_id:'msg_a',text:'سؤال',role:'user',answer_id:null}],
    answers:[{kind:'answer',contract_version:'product.v1',answer_id:'ans_x',conversation_id:'db_other',
      message_id:'assistant_x'}],page:{next_cursor:null,has_more:false}};
  await withFetch(async()=>reply(list),
    async()=>assert.rejects(messages('db_a'),e=>e instanceof HistoryFailure&&e.reason==='invalid'));
});
